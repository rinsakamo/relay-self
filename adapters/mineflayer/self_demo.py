"""Single-command RelaySelf *demo*, not a new cognition owner or scientific gate.

--smoke runs a three-epoch synthetic, typed S10/S11 continuity example.
--run-disposable invokes the ALREADY IMPLEMENTED S49 native 3-decision/two-Action
World host, under explicit consent, and converts its actual receipt into JSONL.

In particular, a S49 native Action OUTCOME is not verified goal success,
learned native Habit, L2 counterfactual competence or backend STOP ACK.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)
from adapters.mineflayer.self_world_projection import (
    review_saved_s16_action_self_world,
    review_self_world_s15_action_frames,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance

CONFIRM = "SELF-DEMO-I-OWN-DISPOSABLE-WORLD"
SOURCE_SMOKE = "SYNTHETIC_SMOKE_ONLY"
SOURCE_NATIVE = "S49_REAL_MINEFLAYER_RECEIPT"
EXPECTED_DECISIONS = ("WAIT", "MOVE_AWAY", "MOVE_AWAY")


class DemoRejected(ValueError):
    """No fabricated physical, cognitive, or retained authority is allowed."""


def _row(kind: str, source: str, **fields: object) -> dict[str, object]:
    return {"kind": kind, "source_type": source, **fields}


def smoke_trace() -> tuple[dict[str, object], ...]:
    """Exercise existing S10 owner + S11 read over three *synthetic* epochs."""
    p = Provenance("self-demo-smoke-operator", "fixed-offline-cues")
    state = LearningPreferenceState(
        "risk_weight", 3, 0, 10, 0, p,
    )
    repertoire = HabitRepertoire(
        "self-demo-preconfigured-safe-only", 0,
        (HabitRule(
            "preconfigured-safe-wait",
            (CueFeature("safety", "safe"),),
            "WAIT", 1, p,
        ),),
        p,
    )
    rows: list[dict[str, object]] = [
        _row("start", SOURCE_SMOKE, session="synthetic-session-1",
             retained_revision=state.revision, habit_origin="PRECONFIGURED_NOT_LEARNED",
             real_actions=0, model_calls=0)
    ]
    # Fixed, clearly synthetic World source: none of these observations attest
    # an actual Minecraft move or independently proven real-world goal.
    for epoch, witness in enumerate(("safe", "threat", "safe"), start=1):
        cue = HabitCue(
            f"smoke-cue-{epoch}", (CueFeature("safety", witness),), p
        )
        selection = select_habit(repertoire, cue)
        chosen = (
            selection.selected_candidate_ref
            if selection.status is HabitSelectionStatus.SELECTED
            else "FLEE" if witness == "threat" else "ABSTAIN"
        )
        path = (
            "PRECONFIGURED_HABIT" if selection.status is HabitSelectionStatus.SELECTED
            else "CHEAP_L0_TEST_CHOICE" if witness == "threat"
            else "DEFER"
        )
        rows.append(_row(
            "epoch", SOURCE_SMOKE, epoch=epoch, present=witness,
            cognition_path=path, choice=chosen, retained_revision=state.revision,
            actual_world_action="NONE", issued_action=False,
        ))
        if epoch == 2:
            # Synthetic feedback is explicitly marked as a fixture and a
            # separately given owner authority is needed even in this smoke.
            feedback = LearningFeedback(
                "smoke-test-feedback-2", state.target_id,
                FeedbackDirection.INCREASE, p,
                consequence_ref="synthetic-escape-fixture-2",
            )
            proposal = propose_learning_update(
                state, feedback, LearningUpdateRule("smoke-step", 1, 1),
            )
            grant = LearningUpdateAuthority(
                "smoke-local-update-grant", state.target_id, p,
            )
            committed = commit_learning_update(
                state, proposal, grant, provenance=p,
            )
            if committed.new_state.revision != state.revision + 1:
                raise DemoRejected("S10 owner revision did not advance")
            rows.append(_row(
                "synthetic_feedback", SOURCE_SMOKE, epoch=epoch,
                observed_outcome="FIXTURE_ONLY_NOT_PHYSICAL",
                update_issued_by="EXPLICIT_SMOKE_OWNER_GRANT",
                prior_revision=state.revision,
                new_revision=committed.new_state.revision,
                prior_value=state.value, new_value=committed.new_state.value,
                production_habit_granted=False,
            ))
            state = committed.new_state
    rows.append(_row(
        "summary", SOURCE_SMOKE, decisions=3, actual_world_actions=0,
        real_model_calls=0, retained_revision=state.revision,
        synthetic_learning_updates=1, native_goal_attested=False,
        production_habit_granted=False,
    ))
    return tuple(rows)


def project_native_report(report: dict[str, object]) -> tuple[dict[str, object], ...]:
    """Normalize a completed real S49 run; cannot mint absent source receipts."""
    if not isinstance(report, dict):
        raise DemoRejected("typed native report required")
    decisions = report.get("decisions")
    actions = report.get("actual_native_actions")
    probes = report.get("source_pair_trace")
    session = report.get("session_id")
    if (report.get("milestone") != "S49" or report.get("status") != "PASS"
            or report.get("classification")
            != "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
            or not isinstance(session, str) or not session
            or not isinstance(decisions, list) or len(decisions) != 3
            or not isinstance(actions, list) or len(actions) != 2
            or not isinstance(probes, list) or len(probes) != 3
            or report.get("real_model_calls") != 0
            or report.get("learning_in_world") is not False):
        raise DemoRejected("source run not complete or mixed with new evidence")
    if tuple(d.get("selected") for d in decisions if isinstance(d, dict)) != EXPECTED_DECISIONS:
        raise DemoRejected("actual native decisions do not match S49 owner")
    if any(not isinstance(d, dict) for d in decisions):
        raise DemoRejected("missing typed native decision")
    if any(not isinstance(a, dict) for a in actions):
        raise DemoRejected("missing typed native Action closure")
    if any(not isinstance(v, dict) for v in probes):
        raise DemoRejected("missing paired native probe source")

    outcome_for_event = {a.get("event_seq"): a for a in actions}
    if (len(outcome_for_event) != 2
            or any(a.get("terminal") != "outcome"
                   or a.get("source") != session
                   or not isinstance(a.get("movement_m"), (int, float))
                   or isinstance(a.get("movement_m"), bool)
                   or not 0.05 <= a["movement_m"] < 16
                   or not isinstance(a.get("action"), str)
                   or not a["action"]
                   for a in actions)):
        raise DemoRejected("invalid native issued Action OUTCOME")
    # Reports written before the S49 fix are intentionally preserved as
    # evidence-PARTIAL: never backfill their missing native frames.
    has_evidence = ["execution_evidence" in a for a in actions]
    if any(has_evidence) and not all(has_evidence):
        raise DemoRejected("partial/inconsistent original Action frame retention")
    evidence_complete = all(has_evidence)
    if evidence_complete:
        try:
            for a in actions:
                verify_native_action_evidence(
                    a["execution_evidence"],
                    action_id=a["action"], session_id=session,
                    movement_m=a["movement_m"],
                )
        except NativeEvidenceRejected as exc:
            raise DemoRejected("Action evidence cannot be independently replayed") from exc
    event_seq = [d.get("event_seq") for d in decisions]
    if (any(type(v) is not int or v < 0 for v in event_seq)
            or len(set(event_seq)) != 3 or event_seq != sorted(event_seq)
            or set(outcome_for_event) != set(event_seq[1:])
            or len({a["action"] for a in actions}) != 2):
        raise DemoRejected("stale, foreign or duplicate native Action event")
    if (any(p.get("event_seq") != d.get("event_seq")
            or p.get("probe_seq") != d.get("probe_seq")
            or type(d.get("probe_seq")) is not int
            or d.get("probe_seq") <= d["event_seq"]
            for p, d in zip(probes, decisions, strict=True))
            or any(d.get("issued") is not (i > 0)
                   for i, d in enumerate(decisions))):
        raise DemoRejected("uncorrelated native Present source or Action")

    rows = [_row(
        "start", SOURCE_NATIVE, session=session, minecraft_version=report.get("minecraft_version"),
        mineflayer_version=report.get("mineflayer_version"), retained_origin=report.get("retained_origin"),
        retained_learning_during_live_run=False,
        action_frames_complete=evidence_complete,
        frame_format=(
            "DECODED_NATIVE_TYPED_FRAMES_NOT_RAW_WIRE"
            if evidence_complete else "LEGACY_ACTION_FRAMES_NOT_RETAINED"
        ),
    )]
    for i, (d, evidence) in enumerate(zip(decisions, probes, strict=True), start=1):
        rows.append(_row(
            "native_observation", SOURCE_NATIVE, epoch=i, session=session,
            event_seq=d["event_seq"], probe_seq=d["probe_seq"],
            target_entity_id=d["entity_id"], target_distance_m=d["distance_m"],
            native_probe_entities=evidence.get("probe_entities"),
        ))
        rows.append(_row(
            "decision", SOURCE_NATIVE, epoch=i, cognition_path="L0_WORLD",
            selected=d["selected"], real_model_calls=0,
            issued_native_action=d["issued"], retained_origin=report.get("retained_origin"),
        ))
        if d["issued"]:
            a = outcome_for_event[d["event_seq"]]
            rows.append(_row(
                "native_action_outcome", SOURCE_NATIVE, epoch=i,
                action_id=a["action"], terminal=a["terminal"],
                world_source_session=a["source"],
                movement_m=a["movement_m"],
                decoded_execution_evidence=a.get("execution_evidence"),
                execution_evidence_sha256=(
                    hashlib.sha256(json.dumps(
                        a["execution_evidence"], sort_keys=True,
                        separators=(",", ":"), ensure_ascii=False,
                    ).encode("utf-8")).hexdigest()
                    if evidence_complete else None
                ),
                action_frames_complete=evidence_complete,
                goal_success_attested=False, signed_negative_z=False,
                retained_update=False,
            ))
    rows.append(_row(
        "summary", SOURCE_NATIVE, decisions=3, native_terminal_actions=2,
        real_model_calls=0, in_world_learning_updates=0,
        production_habit_granted=False, signed_goal_labels=0,
        action_frames_complete=evidence_complete,
        server_exit=report.get("server_exit"),
    ))
    return tuple(rows)



def review_s49_action_self_world_report(
    report: dict[str, object],
) -> tuple[dict[str, object], ...]:
    """Read-only Stage K review of existing S49 CLOSED Action native frames.

    Require the actual decoded S16 witness, original S49 action/target link
    and positive pre-action entity source. Do not invent an earlier prediction
    or infer prediction caused movement. This is a retrospective baseline.
    """
    project_native_report(report)
    decisions = {
        decision["event_seq"]: decision
        for decision in report["decisions"]
    }
    items = []
    for action in report["actual_native_actions"]:
        if "execution_evidence" not in action:
            raise DemoRejected("Stage K requires original S16 decoded Action frames")
        decision = decisions[action["event_seq"]]
        if (decision["probe_seq"] != action["probe_seq"]
                or decision["selected"] != "MOVE_AWAY"
                or decision["issued"] is not True):
            raise DemoRejected("Stage K Action lacks original native decision")
        evidence = action["execution_evidence"]
        before = evidence["before_observation"]
        if before["seq"] <= action["probe_seq"]:
            raise DemoRejected("Stage K pre-action snapshot not after S49 decision")
        from relay_self.self_world import InvalidSelfWorldData

        try:
            review = review_saved_s16_action_self_world(
                evidence, action_id=action["action"],
                session_id=report["session_id"],
                movement_m=action["movement_m"],
                target_entity_id=decision["entity_id"],
            )
        except (InvalidSelfWorldData, TypeError, KeyError, ValueError) as exc:
            raise DemoRejected("Stage K S16 target source unavailable/invalid") from exc
        items.append({
            "kind": "s16_saved_world_review",
            "classification": "DEV_ONLY_RETROSPECTIVE_NOT_PRIOR_LIVE_PREDICTION",
            "session": review.session_id,
            "action_id": action["action"],
            "target_ref": review.target_ref,
            "status": review.status.value,
            "reason_code": review.reason_code,
            "predicted_value": review.predicted_value,
            "observed_value": review.observed_value,
            "prior_source": review.prior_observation_ref,
            "later_source": review.later_observation_ref,
            "actual_native_actions_added": 0,
            "s17_feedback_created": False,
            "s10_learning_committed": False,
            "habit_learned": False,
        })
    return tuple(items)


def retain_native_observations(
    rows: tuple[dict[str, object], ...],
) -> PersistentCognition:
    """Use original owner-local PersistentCognition for *observed* receipts.

    This records S49 reported movement, NOT World goal correctness,
    negative-z feedback, inferred S10 learning or S11 Habit acquisition.
    A caller that did not obtain rows via project_native_report has no
    independent physical trust root; do not treat snapshot as attestation.
    """
    if (not isinstance(rows, tuple) or len(rows) != 10
            or rows[0].get("source_type") != SOURCE_NATIVE
            or rows[-1].get("kind") != "summary"
            or rows[-1].get("in_world_learning_updates") != 0):
        raise DemoRejected("validated native trace required before Memory projection")
    session = rows[0].get("session")
    actions = [r for r in rows if r.get("kind") == "native_action_outcome"]
    if (not isinstance(session, str) or not session
            or len(actions) != 2
            or any(a.get("terminal") != "outcome"
                   or a.get("world_source_session") != session
                   or a.get("goal_success_attested") is not False
                   or a.get("signed_negative_z") is not False
                   or a.get("retained_update") is not False
                   for a in actions)):
        raise DemoRejected("non-observed or promoted Action cannot become Memory")
    operator = Provenance("self-demo-operator", "explicit-observation-retention")
    identity = IdentitySpecification(
        "self-demo-" + session,
        ("Keep observed movement distinct from goal success and signed feedback.",),
        operator,
    )
    snapshot = PersistentCognition(identity)
    for entry in actions:
        action_id = entry.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise DemoRejected("source Action identity missing")
        content = json.dumps({
            "type": "S49_OBSERVED_ACTION_OUTCOME",
            "session": session,
            "action_id": action_id,
            "terminal": entry["terminal"],
            "movement_m": entry["movement_m"],
            "action_frames_complete": entry.get("action_frames_complete", False),
            "execution_evidence_sha256": entry.get("execution_evidence_sha256"),
            "goal_success_attested": False,
            "learning_feedback_qualified": False,
        }, sort_keys=True)
        memory = Memory(
            f"observed:{session}:{action_id}", content,
            Provenance("self-demo-projected-S49-report", f"{session}:{action_id}"),
            operator,
        )
        snapshot = snapshot.retain_memory(memory)
    if len(snapshot.memories) != 2:
        raise DemoRejected("retained native episode count mismatch")
    return snapshot


def _write_trace(path: Path | None, rows: tuple[dict[str, object], ...]) -> None:
    encoded = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                      for row in rows)
    if path is None:
        sys.stdout.write(encoded)
        return
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise DemoRejected("trace destination must be a regular file")
    if not path.parent.is_dir():
        raise DemoRejected("trace parent directory must already exist")
    # Refuse to overwrite retained evidence from a previous owned run.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    sys.stdout.write(encoded)


async def _run_disposable(
    report_path: Path, server_log: Path, *,
    live_model: tuple[str, int, float] | None = None,
    self_world_live: bool = False,
    self_world_prospective: bool = False,
    self_world_typed_closure: bool = False,
    self_world_retained_handoff: bool = False,
    stage_r_dev: bool = False,
) -> int:
    # Existing exact S49 host is the *only* issuer. No duplicated event loop,
    # no new Game Action code or arbitrary LLM output -> Action mapping.
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    live_observer = None
    if live_model is not None:
        from adapters.mineflayer.self_live_think import LiveL2Observer

        live_observer = LiveL2Observer(
            model=live_model[0], port=live_model[1], timeout_s=live_model[2],
            self_world_live=self_world_live,
        )
    stage_n = None
    if self_world_typed_closure:
        if not self_world_prospective:
            raise DemoRejected("Stage N requires pre-Action Stage L witness")
        from adapters.mineflayer.self_world_native_feedback import (
            StageNDeclaredPolicy,
            StageNNativeClosureObserver,
        )
        stage_n = StageNNativeClosureObserver(StageNDeclaredPolicy())
    stage_o = None
    if stage_r_dev and (
        live_model is not None or self_world_live or self_world_prospective
        or self_world_typed_closure or self_world_retained_handoff
    ):
        raise DemoRejected("Stage R original S49 owner DEV uses model-free native only")
    if self_world_retained_handoff:
        if not self_world_typed_closure:
            raise DemoRejected("Stage O requires Stage N typed S17 source")
        from adapters.mineflayer.self_world_owner_handoff import StageOOwnerReadback
        stage_o = StageOOwnerReadback()
    witness = None
    if self_world_prospective:
        if live_observer is None or not self_world_live:
            raise DemoRejected("Stage L requires existing SelfWorld live observer")
        from adapters.mineflayer.self_world_prospective import ProspectiveWitnessWriter
        witness = ProspectiveWitnessWriter(report_path.parent / "stage_l_prospective.jsonl")

    async def observed_source(reading):
        if stage_o is not None:
            try:
                stage_o.observe_existing_probe(reading)
            except (TypeError, ValueError) as exc:
                stage_o.record_error("source", exc)
        if stage_n is not None:
            try:
                stage_n.observe_existing_probe(reading)
            except (TypeError, ValueError) as exc:
                # Failed advisory tap is evidence, never L0 admission failure.
                stage_n.record_observer_error("source", exc)
        if witness is not None:
            try:
                # Source is sealed on disk before original S49 can select/issue.
                witness.record(reading)
            except (OSError, ValueError, TypeError) as exc:
                # Advisory record failure must NEVER veto sole L0/Action owner.
                witness.error = type(exc).__name__
        await live_observer.observe(reading)

    previous = os.environ.get("S49_REAL_SERVER_CI")
    previous_r = os.environ.get("S49_STAGE_R_DEV_ONLY")
    os.environ["S49_REAL_SERVER_CI"] = "1"
    if stage_r_dev:
        os.environ["S49_STAGE_R_DEV_ONLY"] = "1"
    try:
        if live_observer is None:
            if stage_r_dev:
                return await qualify(
                    report_path, server_log, stage_r_dev=True,
                )
            return await qualify(report_path, server_log)
        if stage_n is None:
            return await qualify(report_path, server_log, live_probe=observed_source)
        from adapters.mineflayer.normal_action import (
            observe_closed_native_actions,
            observe_original_retained_owner,
        )

        def on_closed(original):
            try:
                typed_feedback = stage_n.observe_closed(original)
            except (TypeError, ValueError) as exc:
                # Keep real terminal; retain observer rejection for DEV receipt.
                stage_n.record_observer_error("closed", exc)
                return
            if stage_o is not None:
                try:
                    from relay_self.learning import LearningUpdateRule

                    # HOLD-only *proposal*: no authority, S10 commit or owner
                    # reassignment; original S49 retains the exact rev1 object.
                    stage_o.prepare_original_hold(
                        typed_feedback,
                        LearningUpdateRule("stage-o-dev-hold-preview", 1, 1),
                    )
                except (TypeError, ValueError) as exc:
                    stage_o.record_error("s17-to-s10-proposal", exc)

        # Same event-loop context, original S49 issuer; callback receives only
        # an already-closed Action and never controls the physical outcome.
        if stage_o is None:
            with observe_closed_native_actions(on_closed):
                return await qualify(report_path, server_log, live_probe=observed_source)
        # Readback only: L0 retains original owner object; callback never
        # supplies S10 authority and cannot mutate the original owner.
        with observe_original_retained_owner(stage_o.receive_original_owner):
            with observe_closed_native_actions(on_closed):
                return await qualify(report_path, server_log, live_probe=observed_source)
    finally:
        if stage_o is not None:
            _write_trace(
                report_path.parent / "stage_o_retained_owner.jsonl",
                (stage_o.summary(),),
            )
        if stage_n is not None:
            _write_trace(
                report_path.parent / "stage_n_native_feedback.jsonl",
                (stage_n.summary(),),
            )
        if witness is not None:
            witness.close()
        if live_observer is not None:
            # Separate product-side L2 receipt, never misstate original S49
            # host model calls=0 or infer a new native Action permission.
            live_row = await live_observer.close()
            _write_trace(report_path.parent / "live_l2.jsonl", (live_row,))
        if previous_r is None:
            os.environ.pop("S49_STAGE_R_DEV_ONLY", None)
        else:
            os.environ["S49_STAGE_R_DEV_ONLY"] = previous_r
        if previous is None:
            os.environ.pop("S49_REAL_SERVER_CI", None)
        else:
            os.environ["S49_REAL_SERVER_CI"] = previous


async def _run_b1_local_dev(
    report_path: Path, server_log: Path, *, retention: bool = True,
) -> int:
    """Delegate B1 only to existing S51 DEV World owner."""
    from adapters.mineflayer.s51_eat_real_ci import qualify as s51_qualify

    previous = os.environ.get("S51_REAL_SERVER_CI")
    os.environ["S51_REAL_SERVER_CI"] = "1"
    try:
        return await s51_qualify(
            report_path, server_log, food_item="rotten_flesh",
            food_source="ground2", dev_only=True,
            b1_local_adaptation=True, b1_retention=retention,
        )
    finally:
        if previous is None:
            os.environ.pop("S51_REAL_SERVER_CI", None)
        else:
            os.environ["S51_REAL_SERVER_CI"] = previous


async def _run_b0_ground_dev(report_path: Path, server_log: Path) -> int:
    """Run the EXISTING S51 owner with fresh DEV World, not the RSEE/V runner."""
    from adapters.mineflayer.s51_eat_real_ci import qualify as s51_qualify

    previous = os.environ.get("S51_REAL_SERVER_CI")
    os.environ["S51_REAL_SERVER_CI"] = "1"
    try:
        return await s51_qualify(
            report_path, server_log, food_item="rotten_flesh",
            food_source="ground", dev_only=True,
        )
    finally:
        if previous is None:
            os.environ.pop("S51_REAL_SERVER_CI", None)
        else:
            os.environ["S51_REAL_SERVER_CI"] = previous


def _dev_run(args: argparse.Namespace) -> int:
    """Existing S49/S51 disposable owners; all output remains DEV_ONLY."""
    scenario = getattr(args, "dev_scenario", "native")
    receipt = {
        "mode": "DEV", "classification": "DEV_ONLY", "status": "NOT_RUN",
        "scenario": scenario,
        "run_id": uuid.uuid4().hex, "retry_of": args.retry_of,
        "intent": (
            "S49 disposable L0 development; Java/Node, Mojang download and EULA"
            if scenario in ("native", "native-selfworld") else
            "S51 disposable B0 ground/EAT/M0 development; Java/Node, Mojang download and EULA"
        ),
        "world_source": (
            "NEW_S49_FLAT_WORLD_NOT_GOLDEN" if scenario in ("native", "native-selfworld")
            else "NEW_S51_DEV_WORLD_NOT_GOLDEN"
        ),
        "seed": "SERVER_GENERATED_NOT_ATTESTED",
        "minecraft_version": "1.21.8", "mineflayer_version": "4.39.0",
        "world_launch_attempted": False,
        "engineering_qualified": False, "science_success": False,
        "g3_go": False, "m_energy_credited": False,
    }
    root = args.output_dir
    try:
        if scenario not in ("native", "native-selfworld", "b0-ground", "b1-local-adaptation"):
            raise DemoRejected("DEV requires one S49/S51 owner route")
        if getattr(args, "b1_retention", "on") not in ("on", "off"):
            raise DemoRejected("B1 retention must be on or off")
        if scenario != "b1-local-adaptation" and getattr(args, "b1_retention", "on") != "on":
            raise DemoRejected("retention OFF is B1 scenario only")
        if args.confirm != CONFIRM or not args.run_disposable:
            raise DemoRejected("DEV requires disposable opt-in and exact confirmation")
        live_selfworld = scenario == "native-selfworld"
        prospective = getattr(args, "self_world_prospective", False)
        typed_closure = getattr(args, "self_world_typed_closure", False)
        retained_handoff = getattr(args, "self_world_retained_handoff", False)
        stage_r = getattr(args, "self_world_stage_r_dev", False)
        if type(stage_r) is not bool or (
            stage_r and (
                scenario != "native" or prospective or typed_closure
                or retained_handoff or args.live_think or args.think
                or getattr(args, "self_world_live", False)
            )
        ):
            raise DemoRejected("Stage R requires exclusive model-free native DEV scenario")
        if type(retained_handoff) is not bool or (
            retained_handoff and (not typed_closure or not live_selfworld)
        ):
            raise DemoRejected("Stage O retained source requires Stage N DEV")
        if type(typed_closure) is not bool or (
            typed_closure and (not prospective or not live_selfworld)
        ):
            raise DemoRejected("Stage N typed readback requires prospective SelfWorld DEV")
        if prospective and (not live_selfworld or type(prospective) is not bool):
            raise DemoRejected("Stage L prospective forecast requires SelfWorld DEV")
        if live_selfworld:
            if (args.think or args.reflect_report or args.smoke
                    or not getattr(args, "self_world_live", False)
                    or not args.live_think):
                raise DemoRejected("native-selfworld DEV requires explicit live flags")
            from adapters.mineflayer.s60b1_loopback_adapter import (
                LoopbackTransportConfig,
            )
            # A reachable model is NOT assumed or certified. The DEV can
            # retain source/PRD/L1/L2 input receipts even if backend is absent.
            try:
                LoopbackTransportConfig(
                    model=args.model_alias, port=args.model_port, slots=1,
                    max_tokens=96, connect_s=min(3.0, args.model_timeout),
                    read_s=args.model_timeout, whole_s=args.model_timeout,
                )
            except (TypeError, ValueError, AttributeError) as exc:
                raise DemoRejected("invalid explicit SelfWorld loopback bounds") from exc
        elif (args.think or args.live_think or args.reflect_report or args.smoke
                or getattr(args, "self_world_live", False)):
            raise DemoRejected("ordinary DEV accepts only existing model-free routes")
        if args.retry_of is not None and (
            len(args.retry_of) != 32 or any(c not in "0123456789abcdef" for c in args.retry_of)
        ):
            raise DemoRejected("retry lineage must be a prior DEV run ID")
        if root is None or not root.is_absolute() or ".." in root.parts:
            raise DemoRejected("DEV requires a fresh absolute output directory")
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise DemoRejected("symlink output ancestry denied")
        protected_markers = (
            ".git", "level.dat", "server.properties", "SHA256SUMS", "FINAL_SHA256SUMS",
            "grant-consumed.json", "dev_receipt.json",
        )
        if any((ancestor / marker).exists()
               for ancestor in root.parents for marker in protected_markers):
            raise DemoRejected("output inside repository, existing World or evidence root denied")
        # Exclusive creation in a preexisting parent: never adopt an old World/evidence root.
        if not root.parent.is_dir():
            raise DemoRejected("DEV parent must already exist")
        root.mkdir(mode=0o700)
    except (DemoRejected, OSError) as exc:
        print(json.dumps({**receipt, "reason": str(exc)}, sort_keys=True))
        return 2

    code = 2
    dev_started_monotonic = time.monotonic()
    previous_temp = tempfile.tempdir
    try:
        receipt["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2], text=True,
        ).strip()
        receipt["git_dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parents[2], text=True,
        ).strip())
        if os.environ.get("NODE_OPTIONS"):
            raise DemoRejected("NODE_OPTIONS denied")
        for tool, flag in (("java", "-version"), ("node", "--version")):
            executable = shutil.which(tool)
            if executable is None:
                raise DemoRejected(tool + " unavailable")
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=10)
            if result.returncode:
                raise DemoRejected(tool + " version probe failed")
            receipt[tool + "_version"] = (result.stdout + result.stderr).strip()
        # Check both a listener and reserved/busy socket before the original fixed-port host.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 25565))
        from adapters.mineflayer import s49_normal_session_real_ci  # noqa: F401

        bridge = Path(__file__).with_name("bridge.mjs")
        subprocess.run([
            "node", "--input-type=module", "-e",
            "import {createRequire} from 'node:module'; "
            "const r=createRequire(process.argv[1]); "
            "r('mineflayer'); r('minecraft-protocol');", str(bridge),
        ], check=True, capture_output=True, timeout=15)
        world_parent = root / "owned-worlds"
        world_parent.mkdir()
        receipt["world_namespace"] = str(world_parent)
        tempfile.tempdir = str(world_parent)
        with (root / "dev_receipt.json").open("x") as stream:
            json.dump({**receipt, "status": "RUNNING"}, stream, indent=2)
        receipt["world_launch_attempted"] = True
        with (root / "host_stdout.log").open("x") as stdout, (
            root / "host_stderr.log"
        ).open("x") as stderr, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            if scenario == "b0-ground":
                code = asyncio.run(_run_b0_ground_dev(
                    root / "native_report.json", root / "minecraft_server.log",
                ))
            elif scenario == "b1-local-adaptation":
                code = asyncio.run(_run_b1_local_dev(
                    root / "native_report.json", root / "minecraft_server.log",
                    retention=getattr(args, "b1_retention", "on") == "on",
                ))
            elif scenario == "native-selfworld":
                extra = {}
                if prospective:
                    extra["self_world_prospective"] = True
                if typed_closure:
                    extra["self_world_typed_closure"] = True
                if retained_handoff:
                    extra["self_world_retained_handoff"] = True
                code = asyncio.run(_run_disposable(
                    root / "native_report.json", root / "minecraft_server.log",
                    live_model=(args.model_alias, args.model_port, args.model_timeout),
                    self_world_live=True,
                    **extra,
                ))
            else:
                if stage_r:
                    code = asyncio.run(_run_disposable(
                        root / "native_report.json", root / "minecraft_server.log",
                        stage_r_dev=True,
                    ))
                else:
                    code = asyncio.run(_run_disposable(
                        root / "native_report.json", root / "minecraft_server.log",
                    ))
        native = json.loads((root / "native_report.json").read_text())
        if scenario == "b1-local-adaptation":
            receipt["dev_b1_fixture_seed"] = native.get("b1_fixture_seed")
            if native.get("b1_fixture_seed") is not None:
                receipt["seed"] = "FIXED_DEV_SEED_NOT_QUALIFIED"
            receipt["dev_b1_m0_credit_count"] = native.get("dev_m0_credit_count")
            epochs = native.get("two_ground_epochs", [])
            receipt["dev_b1_epoch_count"] = len(epochs)
            terminal = native.get("metabolism_terminal")
            receipt["dev_b1_meals"] = (
                terminal.get("meals") if isinstance(terminal, dict) else None
            )
            receipt["dev_b1_l1_source"] = native.get("b1_local_final", "NOT_ESTABLISHED")
            receipt["dev_b1_retention_enabled"] = getattr(args, "b1_retention", "on") == "on"
            receipt["dev_b1_source_status"] = native.get("owner_status")
            # Include issued/closed source outcomes retained on failed attempts;
            # a failed acquisition cannot be reported as a successful pickup.
            pickups = [
                (e.get("ground_pickup") if isinstance(e.get("ground_pickup"), dict)
                 else e.get("ground_pickup_attempt"))
                for e in epochs if isinstance(e, dict)
            ]
            move_rows = [
                move for pickup in pickups if isinstance(pickup, dict)
                for move in pickup.get("movement_outcomes", [])
                if isinstance(move, dict)
            ]
            choice_rows = [
                choice for pickup in pickups if isinstance(pickup, dict)
                for choice in pickup.get("b1_local_decisions", [])
                if isinstance(choice, dict)
            ]
            receipt["dev_b1_move_outcomes"] = len(move_rows)
            receipt["dev_b1_blocked_outcomes"] = sum(
                move.get("kind") == "BLOCKED" for move in move_rows
            )
            receipt["dev_b1_lateral_choices"] = sum(
                choice.get("waypoint_id") == "b1-local-lateral" for choice in choice_rows
            )
            receipt["dev_b1_lateral_progressed"] = sum(
                move.get("waypoint_id") == "b1-local-lateral"
                and move.get("kind") in ("PROGRESSED", "ARRIVED")
                for move in move_rows
            )
            receipt["dev_b1_m0_energy_final"] = (
                terminal.get("energy") if isinstance(terminal, dict) else None
            )
            receipt["dev_b1_m0_tick_final"] = (
                terminal.get("tick") if isinstance(terminal, dict) else None
            )
            receipt["dev_b1_eat_outcomes"] = sum(
                e.get("eat_action_terminal") == "outcome"
                for e in epochs if isinstance(e, dict)
            )
            receipt["dev_b1_action_outcomes"] = (
                receipt["dev_b1_move_outcomes"] + receipt["dev_b1_eat_outcomes"]
            )
            receipt["dev_b1_decisions"] = sum(
                len(e.get("hunger_trace", [])) + len(e.get("eat_gate_trace", []))
                + (len(pickup.get("l0_ground_seek_trace", []))
                   if isinstance(pickup, dict) else 0)
                + int(isinstance(e.get("next_l0"), dict))
                for e, pickup in zip(epochs, pickups)
                if isinstance(e, dict)
            )
        if stage_r:
            owner = native.get("stage_r_owner")
            trace = native.get("stage_r_decision_revisions")
            sources = native.get("source_pair_trace")
            actions = native.get("actual_native_actions")
            commit = owner.get("commit_source") if isinstance(owner, dict) else None
            original = (
                actions[0] if isinstance(actions, list) and len(actions) == 2
                else None
            )
            next_source = (
                sources[2] if isinstance(sources, list) and len(sources) == 3
                else None
            )
            certified = (
                code == 0
                and native.get("status") == "PASS"
                and native.get("classification") == "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
                and native.get("learning_in_world") is True
                and isinstance(owner, dict)
                and owner.get("original_session_id") == native.get("session_id")
                and owner.get("initial_revision") == 1
                and owner.get("current_revision") == 2
                and owner.get("current_value") == 4
                and owner.get("joint_l0_s14_owner_identity") is True
                and owner.get("operator_s10_grants") == 1
                and owner.get("s10_hold_commits") == 1
                and isinstance(commit, dict)
                and isinstance(original, dict)
                and isinstance(next_source, dict)
                and commit.get("terminal_action_id") == original.get("action")
                and commit.get("terminal_after_native_seq") ==
                original.get("execution_evidence", {}).get(
                    "after_observation", {},
                ).get("seq")
                and commit.get("next_source_probe_seq") == next_source.get("probe_seq")
                and commit.get("next_source_request_id") ==
                f"s49-actual:{native.get('session_id')}:event-{next_source.get('event_seq')}"
                and commit.get("s10_commit_revision") == 2
                and commit.get("s10_authority_source") == "s49-dev-learning-owner"
                and isinstance(commit.get("feedback_id"), str)
                and commit["feedback_id"] != ""
                and owner.get("original_action_closures") == 2
                and owner.get("pending_unsealed_or_unknown") is False
                and owner.get("grant_independent_external_attestation") is False
                and owner.get("hold_reward_or_policy_gain") is False
                and owner.get("additional_action_issuer") is False
                and isinstance(trace, list)
                and [r.get("retained_revision") for r in trace] == [1, 1, 2]
                and [r.get("retained_value") for r in trace] == [4, 4, 4]
                and [r.get("selected") for r in trace] == ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
            )
            receipt["dev_stage_r_owner"] = (
                "S49_ONE_WRITER_HOLD_REV2" if certified else "NOT_CERTIFIED"
            )
            receipt["dev_stage_r_s10_commits"] = (
                owner.get("s10_hold_commits") if isinstance(owner, dict) else None
            )
            receipt["dev_stage_r_issuer_independently_attested"] = False
            receipt["dev_stage_r_policy_adaptation_proven"] = False
            receipt["dev_stage_r_native_trace"] = "native_report.json"
            if not certified:
                code = 1
        if scenario == "b0-ground":
            # Read-only projection of source; NOT independent R qualification.
            acquisition = native.get("ground_pickup")
            metabolism = native.get("metabolism_after_eat")
            next_l0 = native.get("next_l0")
            receipt["dev_b0_source_status"] = native.get("owner_status")
            receipt["dev_b0_pickup"] = (
                acquisition.get("status") if isinstance(acquisition, dict) else "UNKNOWN"
            )
            receipt["dev_b0_move_outcomes"] = (
                len(acquisition.get("movement_outcomes", []))
                if isinstance(acquisition, dict) else 0
            )
            receipt["dev_b0_eat_outcome"] = native.get("action_terminal", "UNKNOWN")
            receipt["dev_b0_m0_credit_source_claim"] = bool(native.get("m_energy_credited"))
            receipt["dev_b0_m0_credit_count"] = (
                metabolism.get("credit_count") if isinstance(metabolism, dict) else None
            )
            receipt["dev_b0_next_l0_kind"] = (
                next_l0.get("kind") if isinstance(next_l0, dict) else None
            )
            receipt["dev_b0_decisions"] = (
                len(native.get("ground_appetite_trace", []))
                + (len(acquisition.get("l0_ground_seek_trace", []))
                   if isinstance(acquisition, dict) else 0)
                + len(native.get("hunger_l0_trace", []))
                + int(isinstance(next_l0, dict) and bool(next_l0))
            )
            receipt["dev_b0_action_outcomes"] = (
                receipt["dev_b0_move_outcomes"]
                + int(native.get("action_terminal") == "outcome")
            )
            # Qualified M0 energy stays false in DEV; these are owner-local
            # measurements on a disposable, non-R-qualified World.
        if scenario == "native-selfworld":
            sidecar_file = root / "live_l2.jsonl"
            if (not sidecar_file.is_file() or sidecar_file.is_symlink()
                    or sidecar_file.stat().st_size > 65536):
                raise DemoRejected("native-selfworld DEV sidecar missing/invalid")
            rows = sidecar_file.read_text(encoding="utf-8").splitlines()
            if len(rows) != 1:
                raise DemoRejected("native-selfworld DEV requires one sidecar record")
            sidecar = json.loads(rows[0])
            if (sidecar.get("kind") != "l2_live_observer"
                    or sidecar.get("session") != native.get("session_id")
                    or sidecar.get("self_world_live") is not True
                    or sidecar.get("native_l0_action_owner") != "S49_NATIVE_EXISTING"
                    or sidecar.get("authorized_actions") != 0
                    or sidecar.get("l2_used_as_action") is not False
                    or sidecar.get("learning_updates") != 0
                    or sidecar.get("habit_grants") != 0
                    or sidecar.get("l0_blocked_on_l2") is not False
                    or sidecar.get("model_attempts") not in (0, 1)):
                raise DemoRejected("native-selfworld DEV sidecar violates owner boundary")
            # Cross-check the observer-local refs against the ORIGINAL S49
            # correlated native probes, not only against the sidecar's claims.
            # Native event seq, probe seq and logical decision epoch differ.
            paired = native.get("source_pair_trace")
            valid_pair_refs: list[str] = []
            if isinstance(paired, list):
                for pair in paired:
                    if not isinstance(pair, dict):
                        continue
                    event, seq = pair.get("event_seq"), pair.get("probe_seq")
                    if (type(event) is int and event >= 0
                            and type(seq) is int and seq >= 0):
                        valid_pair_refs.append(
                            f"present:{native['session_id']}:{seq}:"
                            f"s49-actual:{native['session_id']}:event-{event}"
                        )
            prior_ref = sidecar.get("self_world_prior_source")
            after_ref = sidecar.get("self_world_after_source")
            actual_source_pair = (
                prior_ref in valid_pair_refs
                and after_ref in valid_pair_refs
                and valid_pair_refs.index(prior_ref) < valid_pair_refs.index(after_ref)
                and len(set(valid_pair_refs)) == len(valid_pair_refs)
            )
            receipt["dev_self_world_native_pair_verified"] = actual_source_pair
            qualified_input = (
                actual_source_pair
                and sidecar.get("self_world_l2_input_bound") is True
                and sidecar.get("self_world_review_status")
                in ("match", "mismatch", "undetermined")
                and isinstance(sidecar.get("self_world_prior_source"), str)
                and isinstance(sidecar.get("self_world_after_source"), str)
                and sidecar["self_world_prior_source"] != sidecar["self_world_after_source"]
                and sidecar.get("model_attempts") == 1
            )
            receipt.update(
                dev_self_world_input="SOURCE_BOUND" if qualified_input else "NOT_OBSERVED",
                dev_self_world_review=sidecar.get("self_world_review_status"),
                dev_self_world_review_reason=sidecar.get("self_world_review_reason"),
                dev_self_world_prior_source=sidecar.get("self_world_prior_source"),
                dev_self_world_after_source=sidecar.get("self_world_after_source"),
                dev_self_world_l1_cognitive_candidate=sidecar.get(
                    "preconfigured_l1_cognitive_candidate"
                ),
                dev_self_world_provider_status=sidecar.get("status"),
                dev_self_world_model_attempts=sidecar.get("model_attempts"),
                dev_self_world_model_identity_verified=False,
                dev_self_world_sidecar="live_l2.jsonl",
            )
            # Stage K reuses the already CLOSED S15/S16 native before/after
            # frames from each Action. No new probe, L2 lease or movement.
            # This differs from S49's intentionally different zombies across
            # decision epochs and does not imply learning or Action causality.
            action_reviews: list[dict[str, object]] = []
            decisions_by_event = {
                d["event_seq"]: d for d in native.get("decisions", [])
                if isinstance(d, dict) and type(d.get("event_seq")) is int
            }
            for action in native.get("actual_native_actions", []):
                evidence = action.get("execution_evidence")
                if evidence is None:
                    # Legacy/mock reports have no original S16 frames. Do
                    # not certify them, but do not break the Stage J test
                    # whose purpose is only to gate the live sidecar.
                    action_reviews.append({
                        "action_id": action.get("action"),
                        "status": "unavailable", "reason": "original_frames_not_saved",
                    })
                    continue
                decision = decisions_by_event.get(action.get("event_seq"))
                if (decision is None
                        or decision.get("probe_seq") != action.get("probe_seq")
                        or decision.get("entity_id") is None):
                    raise DemoRejected("S15 Action missing S49 source-decision lineage")
                reviewed = review_self_world_s15_action_frames(
                    evidence, action_id=action["action"],
                    session_id=native["session_id"],
                    movement_m=action["movement_m"],
                    target_entity_id=decision["entity_id"],
                    preceding_s49_probe_seq=decision["probe_seq"],
                )
                if reviewed is None:
                    action_reviews.append({
                        "action_id": action["action"],
                        "status": "unavailable",
                        "reason": "initial_target_not_positive",
                    })
                else:
                    action_reviews.append({
                        "action_id": action["action"],
                        "status": reviewed.status.value,
                        "reason": reviewed.reason_code,
                        "target_ref": reviewed.target_ref,
                        "before_source_ref": reviewed.prior_observation_ref,
                        "after_source_ref": reviewed.later_observation_ref,
                        "predicted": reviewed.predicted_value,
                        "observed": reviewed.observed_value,
                    })
            receipt["dev_self_world_s15_action_reviews"] = action_reviews
            receipt["dev_self_world_s15_positive_comparisons"] = sum(
                row["status"] in ("match", "mismatch") for row in action_reviews
            )
            receipt["dev_self_world_s15_positive_source_certified"] = (
                len(action_reviews) == 2
                and receipt["dev_self_world_s15_positive_comparisons"] >= 1
            )
            if prospective:
                from adapters.mineflayer.self_world_prospective import (
                    verify_prospective_native_reviews,
                )
                path = root / "stage_l_prospective.jsonl"
                if (not path.is_file() or path.is_symlink()
                        or path.stat().st_size > 65536):
                    raise DemoRejected("Stage L pre-Action forecast file missing")
                # This read happens only after S49 has completed: original
                # fsynced pre-Action lines + independent typed S16 readback.
                prospective_reviews = verify_prospective_native_reviews(
                    native, path.read_bytes(),
                )
                positive_count = sum(
                    r["status"] in ("match", "mismatch")
                    for r in prospective_reviews
                )
                receipt.update(
                    dev_self_world_prospective="SOURCE_BOUND"
                    if positive_count > 0 else "UNDETERMINED",
                    dev_self_world_prospective_witness="stage_l_prospective.jsonl",
                    dev_self_world_prospective_reviews=prospective_reviews,
                    dev_self_world_prospective_positive_count=positive_count,
                    dev_self_world_prospective_s17_feedback=0,
                    dev_self_world_prospective_s10_commits=0,
                    dev_self_world_prospective_actions_issued=0,
                )
                if code == 0 and positive_count == 0:
                    code = 1
                    receipt["dev_self_world_prospective_incomplete"] = (
                        "NO_POSITIVE_SAME_TARGET_SUCCESSOR_SOURCE"
                    )
            if typed_closure:
                stage_n_path = root / "stage_n_native_feedback.jsonl"
                if (not stage_n_path.is_file() or stage_n_path.is_symlink()
                        or stage_n_path.stat().st_size > 65536):
                    raise DemoRejected("Stage N original typed closure sidecar missing")
                stage_n_rows = stage_n_path.read_text(encoding="utf-8").splitlines()
                if len(stage_n_rows) != 1:
                    raise DemoRejected("Stage N expects one typed closure summary")
                stage_n = json.loads(stage_n_rows[0])
                closures = stage_n.get("source_closures")
                subsequent = stage_n.get("post_closure_source_observations")
                if (stage_n.get("kind") != "stage_n_typed_s16_closed_readback"
                        or stage_n.get("source_session") != native["session_id"]
                        or stage_n.get("declared_policy") != "actual-move-execution-only"
                        or stage_n.get("declared_feedback_direction") != "hold"
                        or stage_n.get("s10_authority_attested") is not False
                        or stage_n.get("s10_learning_commits") != 0
                        or stage_n.get("native_actions_added") != 0
                        or not isinstance(closures, list)
                        or not isinstance(subsequent, list)):
                    raise DemoRejected("Stage N must not mint S10 or Action authority")
                actions = native.get("actual_native_actions", [])
                original = {a["action"]: a for a in actions}
                native_source_probes = {
                    p["probe_seq"]: (
                        p["event_seq"],
                        f"s49-actual:{native['session_id']}:event-{p['event_seq']}",
                    )
                    for p in native.get("source_pair_trace", [])
                }
                certified = (
                    stage_n.get("observer_errors") == []
                    and len(closures) == stage_n.get("typed_s17_feedback_count") == 2
                    and len(original) == 2
                    and len(subsequent) >= 1
                    and all(
                        c.get("action_id") in original
                        and c.get("source_probe_seq") ==
                        original[c["action_id"]]["probe_seq"]
                        and c.get("source_probe_seq") in native_source_probes
                        and c.get("source_probe_request_id") ==
                        native_source_probes[c["source_probe_seq"]][1]
                        and c.get("after_native_seq") ==
                        original[c["action_id"]]["execution_evidence"][
                            "after_observation"]["seq"]
                        and c.get("original_terminal") == "outcome"
                        and c.get("original_outcome_reason") == "observed_execution"
                        and c.get("feedback_direction") == "hold"
                        and c.get("s17_interpretation") == "produced"
                        and c.get("s10_update_committed") is False
                        and c.get("action_issued_by_stage_n") is False
                        for c in closures
                    )
                    and all(
                        row.get("after_action_id") in original
                        and row.get("next_native_seq") in native_source_probes
                        and row.get("next_native_seq") >
                        original[row["after_action_id"]]["execution_evidence"][
                            "after_observation"]["seq"]
                        and row.get("next_native_request_id") ==
                        native_source_probes[row["next_native_seq"]][1]
                        and row.get("same_native_session") is True
                        and row.get("action_issued_from_feedback") is False
                        for row in subsequent
                    )
                )
                receipt.update(
                    dev_self_world_stage_n="TYPED_S17_READ_ONLY"
                    if certified else "NOT_CERTIFIED",
                    dev_self_world_stage_n_closures=len(closures),
                    dev_self_world_stage_n_observer_errors=stage_n.get("observer_errors"),
                    dev_self_world_stage_n_future_sources=len(subsequent),
                    dev_self_world_stage_n_s10_authorized=False,
                    dev_self_world_stage_n_s10_commits=0,
                    dev_self_world_stage_n_source="stage_n_native_feedback.jsonl",
                )
                if code == 0 and not certified:
                    code = 1
                    receipt["dev_self_world_stage_n_incomplete"] = (
                        "TYPED_ACTION_READBACK_NOT_PROVEN"
                    )
            if retained_handoff:
                owner_path = root / "stage_o_retained_owner.jsonl"
                if (not owner_path.is_file() or owner_path.is_symlink()
                        or owner_path.stat().st_size > 65536):
                    raise DemoRejected("Stage O original L0 owner readback missing")
                owner_lines = owner_path.read_text(encoding="utf-8").splitlines()
                if len(owner_lines) != 1:
                    raise DemoRejected("Stage O expects one owner readback summary")
                owner = json.loads(owner_lines[0])
                actual = native.get("source_pair_trace", [])
                reads = owner.get("same_owner_source_reads")
                certified = (
                    owner.get("kind") == "stage_o_original_owner_readback"
                    and owner.get("session_id") == native["session_id"]
                    and owner.get("intent_id") == "escape-threat"
                    and owner.get("captured_original_l0_retained_identity") is True
                    and owner.get("original_owner_target") == "risk_weight"
                    and owner.get("original_owner_value") == 4
                    and owner.get("original_owner_revision") == 1
                    and owner.get("source_read_count") == 3
                    and isinstance(reads, list) and len(reads) == len(actual) == 3
                    and all(
                        x.get("source_probe_seq") == y.get("probe_seq")
                        and x.get("source_request_id") ==
                        f"s49-actual:{native['session_id']}:event-{y['event_seq']}"
                        and x.get("source_session") == native["session_id"]
                        and x.get("retained_target") == "risk_weight"
                        and x.get("retained_revision") == 1
                        and x.get("retained_value") == 4
                        and x.get("exact_original_owner_identity") is True
                        and x.get("read_only") is True
                        for x, y in zip(reads, actual, strict=True)
                    )
                    and owner.get("observer_errors") == []
                    and owner.get("s10_update_authority") is False
                    and owner.get("s10_commits") == 0
                    and owner.get("s49_l0_retained_mutated") is False
                    and owner.get("next_epoch_learned_action") is False
                    and owner.get("additional_native_actions") == 0
                )
                receipt.update(
                    dev_self_world_stage_o="ORIGINAL_OWNER_READ_ONLY"
                    if certified else "NOT_CERTIFIED",
                    dev_self_world_stage_o_read_count=len(reads)
                    if isinstance(reads, list) else 0,
                    dev_self_world_stage_o_s10_authorized=False,
                    dev_self_world_stage_o_s10_commits=0,
                    dev_self_world_stage_o_source="stage_o_retained_owner.jsonl",
                )
                if code == 0 and not certified:
                    code = 1
                    receipt["dev_self_world_stage_o_incomplete"] = (
                        "EXACT_L0_OWNER_SOURCE_HANDOFF_NOT_PROVEN"
                    )
            # Existing S49 may finish without enough positive target probes.
            # Preserve its raw source report but do not certify Stage J input.
            if code == 0 and not qualified_input:
                code = 1
                receipt["dev_self_world_incomplete"] = (
                    "NATIVE_OWNER_FINISHED_BUT_TWO_SOURCE_COGNITION_NOT_ESTABLISHED"
                )
        receipt.update(
            status="COMPLETED" if code == 0 else "FAILED",
            reason=native.get("error"), session_id=native.get("session_id"),
            server_exit=native.get("server_exit"), node_exit=native.get("node_exit"),
            native_owner_status=native.get("status"),
            decisions=(receipt["dev_b0_decisions"] if scenario == "b0-ground"
                       else receipt["dev_b1_decisions"] if scenario == "b1-local-adaptation"
                       else len(native.get("decisions", []))),
            native_actions=(receipt["dev_b0_action_outcomes"] if scenario == "b0-ground"
                            else receipt["dev_b1_action_outcomes"] if scenario == "b1-local-adaptation"
                            else len(native.get("actual_native_actions", []))),
            cleanup_error=native.get("server_cleanup_error") or native.get("node_cleanup_error"),
            stop_ack="UNATTESTED",
            stop_ack_scope="NO_INDEPENDENT_NATIVE_STOP_ATTESTATION",
            source_report="native_report.json",
            source_scope=("S51_OWNER_B0_NOT_DEV_QUALIFICATION" if scenario == "b0-ground"
                          else "S51_OWNER_B1_DEV_NOT_QUALIFIED" if scenario == "b1-local-adaptation"
                          else "S49_OWNER_DIAGNOSTIC_NOT_DEV_QUALIFICATION"),
        )
    except Exception as exc:
        code = 2 if not receipt["world_launch_attempted"] else 1
        receipt.update(status="NOT_RUN" if not receipt["world_launch_attempted"]
                       else "FAILED", reason=f"{type(exc).__name__}: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            receipt["preflight_stderr"] = str(exc.stderr)[-8192:]
            receipt["preflight_stdout"] = str(exc.stdout)[-8192:]
    finally:
        tempfile.tempdir = previous_temp
        receipt["exit_code"] = code
        # Host-side diagnostic duration, not a qualified Minecraft time source.
        receipt["dev_host_elapsed_seconds"] = round(
            time.monotonic() - dev_started_monotonic, 3,
        )
        # Only this run's own mutable receipt is finalized; originals are never rewritten.
        (root / "dev_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        with (root / "SHA256SUMS").open("x") as index:
            for evidence in sorted(root.iterdir()):
                if evidence.is_file() and evidence.name != "SHA256SUMS":
                    index.write(hashlib.sha256(evidence.read_bytes()).hexdigest()
                                + "  " + evidence.name + "\n")
        print(json.dumps(receipt, sort_keys=True))
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RelaySelf one-command demo: 3 native L0 decisions or an offline S10/S11 smoke",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="synthetic 3-epoch S10/S11 demo")
    mode.add_argument("--run-disposable", action="store_true",
                      help="explicitly start owned disposable Mojang server and S49 bot")
    mode.add_argument("--reflect-report", type=Path,
                      help="read an EXISTING S49 native_report.json, never run Minecraft")
    parser.add_argument("--confirm", help="required exact consent for disposable world")
    parser.add_argument("--output-dir", type=Path, help="pre-existing output directory")
    parser.add_argument("--think", action="store_true",
                        help="one L2 commentary AFTER a completed real native run, never an Action")
    parser.add_argument("--live-think", action="store_true",
                        help="one L2 model attempt DURING native World; L0 remains independent")
    parser.add_argument("--self-world-live", action="store_true",
                        help="opt-in two-source SelfWorld L1/L2 read-only live sidecar")
    parser.add_argument("--self-world-prospective", action="store_true",
                        help="DEV-only pre-Action sealed SelfWorld forecast, no new Action owner")
    parser.add_argument("--self-world-typed-closure", action="store_true",
                        help="DEV-only S49 original S16 typed terminal readback and S17 HOLD")
    parser.add_argument("--self-world-retained-handoff", action="store_true",
                        help="DEV-only original S49 L0 retained owner identity readback")
    parser.add_argument("--self-world-stage-r-dev", action="store_true",
                        help="model-free native DEV ONLY: original S49 single-writer S10 HOLD")
    parser.add_argument("--model-alias", help="explicit pre-existing loopback model alias")
    parser.add_argument("--model-port", type=int, help="existing localhost OpenAI-compatible port")
    parser.add_argument("--model-timeout", type=float, default=12.0)
    parser.add_argument("--mode", choices=("DEV",),
                        help="DEV_ONLY; never delegates to QUALIFICATION or SCIENCE")
    parser.add_argument(
        "--dev-scenario", choices=("native", "native-selfworld", "b0-ground", "b1-local-adaptation"),
        default="native", help="DEV S49 native, S51 B0 or S51 B1 local candidate",
    )
    parser.add_argument(
        "--b1-retention", choices=("on", "off"), default="on",
        help="B1 only: observational Memory ON or fixed-turn OFF",
    )
    parser.add_argument("--retry-of", help="prior DEV run ID, informational lineage only")
    args = parser.parse_args(argv)
    if args.mode == "DEV":
        return _dev_run(args)
    if args.retry_of is not None:
        parser.error("--retry-of requires --mode DEV")
    if args.dev_scenario != "native" or args.b1_retention != "on":
        parser.error("--dev-scenario/--b1-retention require --mode DEV")

    if (args.self_world_prospective or args.self_world_typed_closure
            or args.self_world_retained_handoff or args.self_world_stage_r_dev
    ) and not args.mode:
        print(json.dumps(_row(
            "blocked", "NO_WORLD_USED", reason="PROSPECTIVE_REQUIRES_EXPLICIT_DEV",
            model_calls=0, actual_actions=0,
        ), sort_keys=True))
        return 2
    if args.self_world_live and not args.live_think:
        print(json.dumps(_row(
            "blocked", "NO_WORLD_USED", reason="SELF_WORLD_REQUIRES_LIVE_L2",
            model_calls=0, actual_actions=0,
        ), sort_keys=True))
        return 2
    if args.think and args.live_think:
        print(json.dumps(_row(
            "blocked", "NO_WORLD_USED", reason="TWO_MODEL_ATTEMPTS_DENIED",
            model_calls=0, actual_actions=0,
        ), sort_keys=True))
        return 2
    if args.live_think and not args.run_disposable:
        print(json.dumps(_row(
            "blocked", "NO_WORLD_USED", reason="LIVE_L2_REQUIRES_NATIVE_WORLD",
            model_calls=0, actual_actions=0,
        ), sort_keys=True))
        return 2
    if args.think and not (args.run_disposable or args.reflect_report):
        print(json.dumps(_row(
            "blocked", "NO_WORLD_USED", reason="L2_REQUIRES_REAL_NATIVE_SOURCE",
            model_calls=0, actual_actions=0,
        ), sort_keys=True))
        return 2
    if args.reflect_report is not None:
        # Reflect on an existing physical receipt WITHOUT replaying any World
        # Action, starting Java/Node, loading a new world, or overwriting it.
        from adapters.mineflayer.s60b1_loopback_adapter import (
            LoopbackTransportConfig,
            TransportUnconfirmed,
        )

        if not args.think:
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="REFLECTION_REQUIRES_EXPLICIT_THINK",
                actual_actions=0, model_calls=0,
            ), sort_keys=True))
            return 2
        try:
            LoopbackTransportConfig(
                model=args.model_alias, port=args.model_port, slots=1,
                max_tokens=96, connect_s=3.0,
                read_s=args.model_timeout, whole_s=args.model_timeout,
            )
        except (TransportUnconfirmed, TypeError, ValueError):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED",
                reason="INVALID_EXPLICIT_L2_LOOPBACK_CONFIG",
                model_calls=0, actual_actions=0,
            ), sort_keys=True))
            return 2
        if (args.output_dir is None or not args.output_dir.is_dir()
                or args.output_dir.is_symlink()
                or args.reflect_report.is_symlink()
                or not args.reflect_report.is_file()
                or args.reflect_report.stat().st_size > 2_000_000):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED",
                reason="REFLECTION_SOURCE_OR_OUTPUT_UNVERIFIED",
                model_calls=0, actual_actions=0,
            ), sort_keys=True))
            return 2
        dest = args.output_dir / "l2_reflection.jsonl"
        if dest.exists() or dest.is_symlink():
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="REFLECTION_OUTPUT_EXISTS",
                model_calls=0, actual_actions=0,
            ), sort_keys=True))
            return 2
        try:
            report = json.loads(args.reflect_report.read_text(encoding="utf-8"))
            trace = project_native_report(report)
        except (OSError, UnicodeError, ValueError, TypeError, DemoRejected):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="INVALID_NATIVE_SOURCE_REPORT",
                model_calls=0, actual_actions=0,
            ), sort_keys=True))
            return 2
        from adapters.mineflayer.self_think import bounded_native_commentary

        try:
            reflection = asyncio.run(bounded_native_commentary(
                trace, model=args.model_alias, port=args.model_port,
                timeout_s=args.model_timeout,
            ))
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            reflection = _row(
                "l2_commentary", "SELF_DEMO_S60B1_L2_ADVISORY",
                status="UNCONFIRMED", reason=type(exc).__name__,
                authorized_actions=0, used_as_action=False,
                learning_feedback_created=False, habit_updated=False,
                backend_stop_ack=False, gpu_release_claimed=False,
            )
        _write_trace(dest, (_row(
            "source", SOURCE_NATIVE, session=trace[0]["session"],
            origin="OPERATOR_PROVIDED_REPORT_NOT_INDEPENDENTLY_ATTESTED",
            minecraft_launched=False, replayed_actions=0,
        ), reflection, _row(
            "summary", "READ_ONLY_REFLECTION",
            input_decisions=3, observed_actions=2,
            replayed_actions=0, minecraft_launched=False,
            learning_updates=0, production_habit_granted=False,
        )))
        return 0
    if args.run_disposable:
        if args.confirm != CONFIRM:
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="OPERATOR_CONSENT_REQUIRED",
                expected_confirmation=CONFIRM, actual_actions=0,
            ), sort_keys=True))
            return 2
        if args.output_dir is None or not args.output_dir.is_dir() or args.output_dir.is_symlink():
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="OUTPUT_DIRECTORY_NOT_PREPARED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        if not shutil.which("java") or not shutil.which("node"):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="JAVA_AND_NODE_REQUIRED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        if os.environ.get("NODE_OPTIONS"):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="NODE_SHIM_NOT_ALLOWED",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        if args.think or args.live_think:
            from adapters.mineflayer.s60b1_loopback_adapter import (
                LoopbackTransportConfig,
                TransportUnconfirmed,
            )

            try:
                LoopbackTransportConfig(
                    model=args.model_alias, port=args.model_port,
                    slots=1, max_tokens=96, connect_s=3.0,
                    read_s=args.model_timeout, whole_s=args.model_timeout,
                )
            except (TransportUnconfirmed, TypeError, ValueError):
                print(json.dumps(_row(
                    "blocked", "NO_WORLD_USED", reason="INVALID_EXPLICIT_L2_LOOPBACK_CONFIG",
                    model_calls=0, actual_actions=0,
                ), sort_keys=True))
                return 2
        report_file = args.output_dir / "native_report.json"
        server_log = args.output_dir / "minecraft_server.log"
        trace_file = args.output_dir / "self_trace.jsonl"
        memory_file = args.output_dir / "observed_memory.json"
        live_file = args.output_dir / "live_l2.jsonl"
        if any(path.exists() or path.is_symlink()
               for path in (report_file, server_log, trace_file, memory_file, live_file)):
            print(json.dumps(_row(
                "blocked", "NO_WORLD_USED", reason="EVIDENCE_ALREADY_EXISTS",
                actual_actions=0,
            ), sort_keys=True))
            return 2
        try:
            if args.live_think:
                code = asyncio.run(_run_disposable(
                    report_file, server_log,
                    live_model=(args.model_alias, args.model_port, args.model_timeout),
                    self_world_live=args.self_world_live,
                ))
            else:
                code = asyncio.run(_run_disposable(report_file, server_log))
            if code != 0:
                print(json.dumps(_row(
                    "unknown", SOURCE_NATIVE, reason="NATIVE_OWNER_DID_NOT_QUALIFY",
                    native_report=str(report_file), action_outcome="UNKNOWN",
                ), sort_keys=True))
                return code
            result = json.loads(report_file.read_text(encoding="utf-8"))
            trace = project_native_report(result)
            memory = retain_native_observations(trace)
            save_persistent_cognition(memory_file, memory)
            if args.live_think:
                if not live_file.is_file() or live_file.is_symlink():
                    raise DemoRejected("live L2 sidecar receipt missing")
                lines = live_file.read_text(encoding="utf-8").splitlines()
                if len(lines) != 1:
                    raise DemoRejected("one live L2 attempt receipt required")
                row = json.loads(lines[0])
                if (row.get("kind") != "l2_live_observer"
                        or row.get("session") != trace[0]["session"]
                        or row.get("model_attempts") not in (0, 1)
                        or row.get("authorized_actions") != 0
                        or row.get("l2_used_as_action") is not False
                        or row.get("self_world_live") is not args.self_world_live
                        or (args.self_world_live and (
                            row.get("self_world_l2_input_bound") is True
                            and row.get("model_attempts") != 1
                        ))):
                    raise DemoRejected("live L2 receipt contradicts original S49")
                trace = (*trace, row)
            if args.think:
                # L2 sees only the completed native trace, not an invented
                # goal or new Action admission. The World host has finished.
                from adapters.mineflayer.self_think import bounded_native_commentary

                try:
                    advisory = asyncio.run(bounded_native_commentary(
                        trace, model=args.model_alias, port=args.model_port,
                        timeout_s=args.model_timeout,
                    ))
                except (OSError, ValueError, RuntimeError) as exc:
                    advisory = _row(
                        "l2_commentary", "SELF_DEMO_S60B1_L2_ADVISORY",
                        status="UNCONFIRMED", reason=type(exc).__name__,
                        authorized_actions=0, used_as_action=False,
                        learning_feedback_created=False,
                        habit_updated=False,
                        backend_stop_ack=False, gpu_release_claimed=False,
                    )
                trace = (*trace, advisory)
            _write_trace(trace_file, trace + (_row(
                "observed_memory", SOURCE_NATIVE,
                retained_episodes=len(memory.memories),
                learning_preference_changed=False,
                habit_auto_granted=False,
                durable_file=memory_file.name,
            ),))
            return 0
        except (DemoRejected, OSError, RuntimeError, ValueError) as exc:
            print(json.dumps(_row(
                "unknown", SOURCE_NATIVE, reason=type(exc).__name__,
                signed_goal_labels=0, production_habit_granted=False,
            ), sort_keys=True))
            return 1

    if args.smoke:
        _write_trace(None, smoke_trace())
        return 0
    print(json.dumps(_row(
        "ready", "NO_WORLD_USED", mode="DRY_RUN",
        actions_issued=0, model_calls=0,
        next="--smoke, --run-disposable (--live-think optional), or --reflect-report",
        warning="Native is existing S49 three-event test-world behavior, not a full autonomous Self 1.0",
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
