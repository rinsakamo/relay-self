"""W4 saved evidence -> two read-only SelfWorld epochs (offline DEV only).

Never launches a World or a process, issues Action, updates Memory/S10 or
authenticates physical World truth. An operator pins the original report SHA256;
the source remains locally captured Node stdout and Java collector bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyRawWorldMarker,
    review_observation_only_dev_offline,
)
from adapters.mineflayer.self_world_observation_only_entry import (
    ObservationOnlyEntryInventory,
)
from adapters.mineflayer.self_world_observation_only_lifetime import (
    join_observation_only_local_lifetime,
)
from adapters.mineflayer.self_world_observation_only_native_boundary import (
    NativeLocalDisposalReadback,
)
from adapters.mineflayer.self_world_projection import project_self_world_present
from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout
from relay_self.attention import AttentionCriterion, AttentionSelection
from relay_self.prediction import (
    PredictionState,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import (
    SelfWorldView,
    WorldForecast,
    WorldPredictionReview,
    WorldScenario,
    compose_self_world_view,
    review_self_world_prediction,
    select_self_world_attention,
)


class W4OfflineEpochBlocked(ValueError):
    """Evidence or same-session epoch continuity is not established."""


@dataclass(frozen=True, slots=True)
class W4OfflineEpochReplay:
    """Nonexecuting earlier and later cognition reads, not physical authority."""

    source_head: str
    run_id: str
    report_sha256: str
    node_stdout_sha256: str
    prior: SelfWorldView
    following: SelfWorldView
    prior_attention: AttentionSelection
    following_attention: AttentionSelection
    prediction_review: WorldPredictionReview | None
    source_scope: str = "LOCAL_DEV_SAVED_NODE_JSONL_NOT_MINECRAFT_TCP"
    classification: str = "DEV_ONLY_OFFLINE_SELF_WORLD_EPOCH_REPLAY"
    physical_action_count: int = 0
    outcome_count: int = 0
    s10_update_count: int = 0
    retained_memory_written: bool = False
    cognition_route_executed: bool = False
    world_qualification: bool = False
    science_qualified: bool = False


def _source_file(root: Path, name: str, maximum: int) -> bytes:
    path = root / name
    if (
        path.parent != root or path.is_symlink() or not path.is_file()
        or stat.S_ISREG(path.lstat().st_mode) is not True
        or path.stat().st_size > maximum
    ):
        raise W4OfflineEpochBlocked(f"missing/unsafe {name}")
    return path.read_bytes()


def _typed_source_frames(raw: bytes):
    decoder = MineflayerStreamDecoder()
    try:
        frames = tuple(
            decoder.decode(line.decode("utf-8"))
            for line in raw.splitlines(keepends=True)
        )
    except (UnicodeError, ValueError) as exc:
        raise W4OfflineEpochBlocked("saved W3 stream cannot be decoded") from exc
    return frames


def _exact_frame(frames, report: dict, name: str, frame_type):
    candidates = [
        item for item in frames
        if type(item) is frame_type and json.loads(json.dumps(asdict(item))) == report.get(name)
    ]
    if len(candidates) != 1:
        raise W4OfflineEpochBlocked(f"missing or ambiguous saved {name} frame")
    return candidates[0]


def replay_w4_saved_self_world_epochs(
    *,
    evidence_root: Path,
    expected_report_sha256: str,
    expected_source_head: str,
    expected_run_id: str,
    self_id: str,
    max_native_seq_gap: int = 8,
) -> W4OfflineEpochReplay:
    """Replay ONLY an operator-pinned W4 saved DEV report and original raw data.

    Returned immutable views are not persistent memory: the following epoch
    reuses the earlier typed source only as a review reference. No L0/S14
    route, S17 feedback or S10 authority is created.
    """
    if (
        not isinstance(evidence_root, Path)
        or not evidence_root.is_absolute()
        or not evidence_root.is_dir() or evidence_root.is_symlink()
        or any(p.is_symlink() for p in evidence_root.parents)
        or re.fullmatch(r"[0-9a-f]{64}", expected_report_sha256) is None
        or re.fullmatch(r"[0-9a-f]{40}", expected_source_head) is None
        or re.fullmatch(r"[0-9a-f]{16}", expected_run_id) is None
        or type(self_id) is not str or not self_id or self_id.strip() != self_id
        or type(max_native_seq_gap) is not int or max_native_seq_gap <= 0
    ):
        raise W4OfflineEpochBlocked("absolute local root and exact operator pins required")
    raw_report = _source_file(evidence_root, "report.json", 2_000_000)
    if hashlib.sha256(raw_report).hexdigest() != expected_report_sha256:
        raise W4OfflineEpochBlocked("report bytes differ from pinned DEV original")
    try:
        report = json.loads(raw_report)
    except (ValueError, UnicodeError) as exc:
        raise W4OfflineEpochBlocked("invalid saved report") from exc
    if (
        type(report) is not dict
        or report.get("schema") != "W4_OBSERVATION_ONLY_REAL_DEV_V1"
        or report.get("head") != expected_source_head
        or report.get("run_id") != expected_run_id
        or report.get("status") != "PASS"
        or report.get("verdict") != "DEV_LOCAL_OBSERVATION_ONLY_PASS"
        or report.get("classification") != "DEV_LOCAL_OBSERVATION_ONLY_PASS"
        or report.get("cleanup_confirmed") is not True
        or report.get("world_root_removed") is not True
        or report.get("collector_settled_normally") is not True
        or report.get("port_released") is not True
        or report.get("qualification_approved") is not False
        or report.get("science_qualified") is not False
        or report.get("external_grant_qualified") is not False
        or any(type(report.get(k)) is not int or report[k] != 0
               for k in ("action_count", "outcome_count", "s10_update_count"))
    ):
        raise W4OfflineEpochBlocked("not an exactly scoped completed W4 DEV record")
    try:
        _source_file(evidence_root, "w3-node-stdout-receipt.json", 2_000_000)
        raw_node = _source_file(evidence_root, "w3-node-stdout.raw.jsonl", 32 * 1024 * 1024)
        receipt = audit_w3_sealed_stdout(evidence_root)
        frames = _typed_source_frames(raw_node)
        started = _exact_frame(frames, report, "adapter_started", MineflayerAdapterStarted)
        spawn = _exact_frame(frames, report, "spawn", MineflayerObservation)
        before = _exact_frame(frames, report, "before", MineflayerObservation)
        after = _exact_frame(frames, report, "after", MineflayerObservation)
        if (
            spawn.kind != "spawn" or before.kind != "probe" or after.kind != "probe"
            or receipt.get("session_id") != started.session_id
        ):
            raise W4OfflineEpochBlocked("original correlated observation phases absent")
        marker = ObservationOnlyRawWorldMarker(**report["marker"])
        java_raw = _source_file(evidence_root, "java-collector.raw", 8 * 1024 * 1024)
        if not (0 <= marker.raw_start_byte < marker.raw_end_byte <= len(java_raw)):
            raise W4OfflineEpochBlocked("Java raw marker outside saved original")
        raw_marker = java_raw[marker.raw_start_byte:marker.raw_end_byte]
        readback = review_observation_only_dev_offline(
            started=started, spawn=spawn, before=before, after=after,
            before_request=before.request_id,
            after_request=after.request_id,
            raw_marker_line=raw_marker, marker_sha256=marker.raw_sha256,
            marker_after_before=True, after_marker=True,
        )
        if asdict(readback) != report.get("readback"):
            raise W4OfflineEpochBlocked("original typed review differs from saved report")
        lifetime = join_observation_only_local_lifetime(
            inventory=ObservationOnlyEntryInventory(**report["inventory"]),
            readback=readback, marker=marker, close=report["close"],
            node_raw_root=evidence_root,
        )
        if (asdict(lifetime) != report.get("local_lifetime")
                or lifetime.exact_head != expected_source_head):
            raise W4OfflineEpochBlocked("local Node/Java lifetime does not match")
        disposal = NativeLocalDisposalReadback(**report["local_disposal"])
        if (
            disposal.schema != "W4_OBSERVATION_ONLY_NATIVE_LOCAL_DISPOSAL_V1"
            or disposal.java_pid != report.get("server_pid")
            or disposal.node_pid != report.get("node_pid")
            or report.get("pid_absent") != {
                str(disposal.java_pid): True, str(disposal.node_pid): True,
            }
            or any(report.get(k) for k in (
                "native_inspection_error", "cleanup_error", "world_disposal_error",
                "startup_cleanup_unconfirmed",
            ))
            or disposal.port != 25565
            or disposal.world_dir_name != f"w4-observe-{expected_run_id}"
            or any(getattr(disposal, k) is not True for k in (
                "java_pid_absent", "node_pid_absent",
                "loopback_bind_probe_available", "disposable_world_dir_absent",
            ))
            or disposal.classification != "LOCAL_OS_POSTCLOSE_SNAPSHOT_ONLY"
            or any(getattr(disposal, k) is not False for k in (
                "independent_pid_owner_attested", "independent_port_lease_attested",
                "independent_world_disposal_attested", "external_grant_verified",
                "physical_run_permitted", "qualification_approved", "science_qualified",
            ))
        ):
            raise W4OfflineEpochBlocked("local-only disposal report invalid")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        if isinstance(exc, W4OfflineEpochBlocked):
            raise
        raise W4OfflineEpochBlocked("saved source or typed custody join rejected") from exc

    # Only existing projection, ATT and PRD owners; no mutable World store.
    before_observation = project_self_world_present(
        project_mineflayer_present(before), observer_id=self_id,
    )
    after_observation = project_self_world_present(
        project_mineflayer_present(after), observer_id=self_id,
    )
    prior = compose_self_world_view(
        self_id=self_id, session_id=started.session_id,
        epoch_id=f"w4-{expected_run_id}-before-{before.seq}",
        observation=before_observation,
    )
    following = compose_self_world_view(
        self_id=self_id, session_id=started.session_id,
        epoch_id=f"w4-{expected_run_id}-after-{after.seq}",
        observation=after_observation, minimum_native_seq=before.seq + 1,
        seen_observation_refs=(before_observation.source_ref,),
    )
    criterion = AttentionCriterion(
        criterion_id="w4-offline-first-positive-source", top_k=1,
    )
    prior_attention = select_self_world_attention(prior, criterion)
    following_attention = select_self_world_attention(following, criterion)
    review = None
    if prior_attention.selected:
        target = prior_attention.selected[0].payload_ref
        fact = prior.observed_entity(target).value
        if fact is not None and fact.label is not None:
            state = PredictionState(
                f"w4-local-{expected_run_id}-{before.seq}", (
                    StateVariable("entity_label", fact.label),
                ),
                Provenance("w4-offline-dev-forecast", before_observation.source_ref),
                source_refs=(before_observation.source_ref, f"target:{target}"),
                source_provenance=(before_observation.provenance,),
            )
            rule = TransitionRule(
                "hypothetical-label-persistence",
                (StateVariable("entity_label", fact.label),),
                (StateVariable("entity_label", fact.label),),
                Provenance("w4-offline-hypothesis", "not-a-learned-world-law"),
            )
            scenario = WorldScenario(
                f"w4-{expected_run_id}-label", self_id, target, state,
            )
            prior = replace(
                prior, scenarios=(scenario,),
                forecasts=(WorldForecast(scenario.scenario_id,
                                         predict_transition(state, rule)),),
            )
            review = review_self_world_prediction(
                prior, following, scenario_id=scenario.scenario_id,
                variable_key="entity_label",
                max_native_seq_gap=max_native_seq_gap,
            )
    return W4OfflineEpochReplay(
        source_head=expected_source_head,
        run_id=expected_run_id,
        report_sha256=expected_report_sha256,
        node_stdout_sha256=receipt["stdout_sha256"],
        prior=prior, following=following,
        prior_attention=prior_attention,
        following_attention=following_attention,
        prediction_review=review,
    )
