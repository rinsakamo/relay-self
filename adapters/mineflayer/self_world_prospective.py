"""Stage L: pre-Action source-sealed, read-only SelfWorld forecast.

Only S49's ALREADY correlated native probe is consumed. The immutable
forecast is appended and fsynced before the callback returns to S49 L0.
The Action issuer, S15 source of the later observation and S17/LRN owners
are never modified or called. This is DEV_ONLY, not scientific attestation.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation, _decode_snapshot
from adapters.mineflayer.self_action_evidence import verify_native_action_evidence
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldEntityObservation,
    WorldForecast,
    WorldObservation,
    WorldScenario,
    compose_self_world_view,
    review_self_world_prediction,
)

SCHEMA = "SELF_WORLD_PROSPECTIVE_S49_NATIVE_V1"
OBSERVER = "self-demo-live-observer"


class ProspectiveSourceRejected(ValueError):
    """No prediction or World effect can be manufactured after an Action."""


def _canonical(row: dict) -> bytes:
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _forecast(observation: WorldObservation, target_ref: str):
    observed = next((x for x in observation.entities if x.entity_ref == target_ref), None)
    if observed is None or observed.label != "zombie":
        raise ProspectiveSourceRejected("one positively observed zombie target required")
    state = PredictionState(
        f"s49-prospective-{observation.native_seq}",
        (StateVariable("entity_label", observed.label),),
        Provenance("selfworld-stage-l-pre-action-source", observation.source_ref),
        source_refs=(observation.source_ref, f"target:{target_ref}"),
        source_provenance=(observation.provenance,),
    )
    rule = TransitionRule(
        "fixed-label-persistence-before-action",
        (StateVariable("entity_label", observed.label),),
        (StateVariable("entity_label", observed.label),),
        Provenance("selfworld-stage-l-fixed-baseline", "not-a-learned-world-law"),
    )
    scenario = WorldScenario("stage-l-label", observation.observer_id, target_ref, state)
    prior = compose_self_world_view(
        self_id=observation.observer_id, session_id=observation.session_id,
        epoch_id=f"native-{observation.native_seq}", observation=observation,
    )
    result = predict_transition(state, rule)
    prior = replace(prior, scenarios=(scenario,),
                    forecasts=(WorldForecast(scenario.scenario_id, result),))
    return prior, observed.label


class ProspectiveWitnessWriter:
    """One append-only new DEV file; fsync before original S49 may select Action."""

    def __init__(self, path: Path):
        if not isinstance(path, Path) or not path.parent.is_dir() or path.is_symlink():
            raise ProspectiveSourceRejected("new isolated DEV file required")
        self._file = path.open("x", encoding="utf-8")
        self._prev = "0" * 64
        self._index = 0
        self.error: str | None = None

    def record(self, reading: MineflayerObservation) -> None:
        if self.error is not None:
            return
        if not isinstance(reading, MineflayerObservation) or reading.kind != "probe":
            raise ProspectiveSourceRejected("S49 original correlated native probe required")
        prefix = f"s49-actual:{reading.session_id}:event-"
        if not isinstance(reading.request_id, str) or not reading.request_id.startswith(prefix):
            raise ProspectiveSourceRejected("S49 request/action event provenance missing")
        suffix = reading.request_id[len(prefix):]
        if not suffix.isdigit() or int(suffix) < 0:
            raise ProspectiveSourceRejected("invalid S49 event sequence")
        native = project_self_world_present(
            project_mineflayer_present(reading), observer_id=OBSERVER,
        )
        zombies = [x for x in native.entities if x.label == "zombie"]
        if len(zombies) != 1:
            # No forecast without a single source-positive subject.
            return
        target = zombies[0]
        prior, predicted = _forecast(native, target.entity_ref)
        claim = prior.predicted("stage-l-label", "entity_label")
        if claim.value != predicted:
            raise ProspectiveSourceRejected("fixed baseline PRD did not predict")
        row = {
            "schema": SCHEMA, "index": self._index, "prev_sha256": self._prev,
            "session_id": reading.session_id, "observer_id": OBSERVER,
            "event_seq": int(suffix), "native_seq": reading.seq,
            "request_id": reading.request_id, "source_ref": native.source_ref,
            "target_ref": target.entity_ref, "variable_key": "entity_label",
            "predicted_value": predicted,
            "coverage_scope": native.coverage_scope,
            "coverage_radius_m": native.coverage_radius_m,
            "coverage_cap": native.coverage_cap,
            "coverage_candidates": native.coverage_candidates,
            "coverage_truncated": native.coverage_truncated,
            "entities": [
                {"entity_ref": e.entity_ref, "label": e.label,
                 "position": e.position, "distance_m": e.distance_m}
                for e in native.entities
            ],
            "forecaster": "fixed-label-persistence-before-action",
            "learning_authority": False,
        }
        digest = hashlib.sha256(_canonical(row)).hexdigest()
        self._file.write(json.dumps({**row, "sha256": digest},
                                    sort_keys=True, allow_nan=False) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        self._prev = digest
        self._index += 1

    def close(self):
        self._file.close()


def _prior_from_record(row: dict):
    entities = tuple(WorldEntityObservation(
        entity_ref=e["entity_ref"], label=e["label"],
        position=tuple(e["position"]) if e["position"] is not None else None,
        distance_m=e["distance_m"],
    ) for e in row["entities"])
    observed = WorldObservation(
        observer_id=row["observer_id"], session_id=row["session_id"],
        native_seq=row["native_seq"], request_id=row["request_id"],
        entities=entities,
        coverage_scope=row["coverage_scope"],
        coverage_radius_m=row["coverage_radius_m"],
        coverage_cap=row["coverage_cap"],
        coverage_candidates=row["coverage_candidates"],
        coverage_truncated=row["coverage_truncated"],
        provenance=Provenance("mineflayer",
                              f"{row['session_id']}:{row['native_seq']}"),
    )
    if observed.source_ref != row["source_ref"]:
        raise ProspectiveSourceRejected("prior source ref not original native probe")
    prior, value = _forecast(observed, row["target_ref"])
    if (value != row["predicted_value"] or row["forecaster"] !=
            "fixed-label-persistence-before-action"):
        raise ProspectiveSourceRejected("pre-action PRD source/rule modified")
    return prior


def _after_from_s16(evidence: dict, session: str, action_id: str):
    frame = evidence["after_observation"]
    raw = frame["snapshot"]
    snapshot = _decode_snapshot({
        **raw, "nearby_entities": [
            {"id": e["entity_id"], "name": e["name"], "type": e["entity_type"],
             "distance": e["distance"], "position": e["position"]}
            for e in raw["nearby_entities"]
        ],
    })
    cover = snapshot.nearby_entities_coverage
    obs = WorldObservation(
        observer_id=OBSERVER, session_id=session, native_seq=frame["seq"],
        request_id=f"s16-evidence-{action_id}-after_observation",
        entities=tuple(WorldEntityObservation(
            entity_ref=f"entity-{e.entity_id}", label=e.name,
            position=(e.position.x, e.position.y, e.position.z),
            distance_m=e.distance,
        ) for e in snapshot.nearby_entities),
        coverage_scope=cover.source_scope, coverage_radius_m=cover.max_distance,
        coverage_cap=cover.max_entities, coverage_candidates=cover.candidate_count,
        coverage_truncated=cover.truncated,
        provenance=Provenance("mineflayer", f"{session}:{frame['seq']}"),
    )
    return compose_self_world_view(
        self_id=OBSERVER, session_id=session,
        epoch_id=f"s16-{action_id}-after-{frame['seq']}", observation=obs,
    )


def verify_prospective_native_reviews(report: dict, witness: bytes) -> tuple[dict, ...]:
    """Independent source join: pre-Action persisted PRD + original S49/S16.

    Verify hash-chain, event/seq/source, pre-Action S16 ordering, and exact
    native target. An unseen later target is UNDETERMINED, not absent.
    """
    try:
        if not isinstance(witness, bytes) or not 0 < len(witness) < 65536:
            raise ProspectiveSourceRejected("missing or oversized forecast witness")
        raw_rows = witness.decode("utf-8").splitlines()
        rows = [json.loads(line) for line in raw_rows]
        if len(rows) != len(report["source_pair_trace"]) or not rows:
            raise ProspectiveSourceRejected("one sealed record per S49 source required")
        previous = "0" * 64
        by_event = {}
        for index, (row, original) in enumerate(zip(rows, report["source_pair_trace"],
                                                     strict=True)):
            check = {k: v for k, v in row.items() if k != "sha256"}
            digest = hashlib.sha256(_canonical(check)).hexdigest()
            if (row["schema"] != SCHEMA or row["index"] != index
                    or row["prev_sha256"] != previous or row["sha256"] != digest
                    or row["learning_authority"] is not False):
                raise ProspectiveSourceRejected("sealed pre-Action hash-chain mismatch")
            previous = digest
            if (row["session_id"] != report["session_id"]
                    or row["observer_id"] != OBSERVER
                    or row["event_seq"] != original["event_seq"]
                    or row["native_seq"] != original["probe_seq"]
                    or row["request_id"] !=
                    f"s49-actual:{report['session_id']}:event-{original['event_seq']}"
                    or row["target_ref"].removeprefix("entity-") not in
                    [str(e["id"]) for e in original["probe_entities"]
                     if e["name"] == row["predicted_value"]]):
                raise ProspectiveSourceRejected("witness is not this original S49 source")
            _prior_from_record(row)
            if row["event_seq"] in by_event:
                raise ProspectiveSourceRejected("duplicate pre-Action event")
            by_event[row["event_seq"]] = row
        output = []
        for action in report["actual_native_actions"]:
            event_seq = action["event_seq"]
            decision = next((x for x in report["decisions"]
                             if x["event_seq"] == event_seq), None)
            prior_record = by_event.get(event_seq)
            if (decision is None or prior_record is None
                    or decision["entity_id"] !=
                    int(prior_record["target_ref"].removeprefix("entity-"))
                    or decision["probe_seq"] != prior_record["native_seq"]
                    or not decision["issued"]):
                raise ProspectiveSourceRejected("Action not bound to sealed prior PRD")
            evidence = action["execution_evidence"]
            verify_native_action_evidence(
                evidence, action_id=action["action"],
                session_id=report["session_id"], movement_m=action["movement_m"],
            )
            before = evidence["before_observation"]
            if (before["seq"] <= prior_record["native_seq"]
                    or evidence["dispatch_receipt"]["seq"] <= before["seq"]
                    or evidence["after_observation"]["seq"] <=
                    evidence["dispatch_receipt"]["seq"]):
                raise ProspectiveSourceRejected("prediction not before S16 Action")
            # Before Action must independently re-observe the same target and
            # label. Otherwise no verified continuity into the Action.
            before_entities = before["snapshot"]["nearby_entities"]
            matching = [e for e in before_entities
                        if f"entity-{e['entity_id']}" == prior_record["target_ref"]]
            if (len(matching) != 1 or
                    matching[0]["name"] != prior_record["predicted_value"]):
                raise ProspectiveSourceRejected("S16 before frame is not prior target")
            prior = _prior_from_record(prior_record)
            later = _after_from_s16(evidence, report["session_id"], action["action"])
            review = review_self_world_prediction(
                prior, later, scenario_id="stage-l-label",
                variable_key="entity_label", max_native_seq_gap=64,
            )
            output.append({
                "action_id": action["action"], "event_seq": event_seq,
                "target_ref": review.target_ref, "status": review.status.value,
                "reason": review.reason_code,
                "prior_source": review.prior_observation_ref,
                "later_source": review.later_observation_ref,
                "predicted_value": review.predicted_value,
                "observed_value": review.observed_value,
                "forecast_was_sealed_in_s49_probe_callback": True,
                "s17_feedback_created": False, "s10_learning_committed": False,
                "action_authorizations_from_forecast": 0,
            })
        if len(output) != 2:
            raise ProspectiveSourceRejected("two original S49 MOVE outcomes required")
        return tuple(output)
    except (KeyError, TypeError, AttributeError, IndexError, ValueError,
            UnicodeError, InvalidSelfWorldData) as exc:
        raise ProspectiveSourceRejected("prospective witness/native Action mismatch") from exc
