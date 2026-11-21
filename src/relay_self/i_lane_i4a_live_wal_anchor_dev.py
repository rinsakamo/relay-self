"""I4a DEV: volatile original-Owner witness for one completed Stage27h run.

NOT a durable checkpoint, run resume token, physical grant or historical
proof against process-memory compromise. Anchors only the same live S1 Owner.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillState


class I4ALiveAnchorHold(RuntimeError):
    """Current source or historical Owner witness does not qualify."""


@dataclass(frozen=True, slots=True, eq=False)
class LiveWalHistoryAnchor:
    self_id: str
    native_session_id: str
    world_epoch: int
    intent_id: str
    skill_execution_id: str
    action_ids: tuple[str, ...]
    wal_sha256: str
    wal_row_count: int


def _scoped_owner(
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    *,
    native_session_id: str,
    world_epoch: int,
) -> None:
    if (
        not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or owner.cohort is None
        or owner.cohort is not lane.cognitive_work
        or lane.cognitive_work.owners.get(owner.self_id) is not owner
        or owner.native_session_id != native_session_id
        or owner.fresh_native_observation_required
        or owner.supervisor.open_actions
    ):
        raise I4ALiveAnchorHold("current original Owner/physical scope unavailable")
    try:
        scope = lane.cognitive_work.current_scope(owner.self_id)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise I4ALiveAnchorHold("resident Self fenced") from exc
    if scope[1:] != (native_session_id, world_epoch):
        raise I4ALiveAnchorHold("native/World epoch changed")


def _read_quiescent(owner: CheckpointedCognitiveOwner) -> PhysicalActionJournal:
    try:
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        return journal
    except PhysicalJournalError as exc:
        raise I4ALiveAnchorHold("canonical WAL not clear or valid") from exc


def capture_live_wal_history_anchor(
    loop: Stage27hBoundedMoveLoop,
    *,
    lane: ResidentLlamaInferenceLane,
) -> LiveWalHistoryAnchor:
    """Seal S1 under Owner -> physical admission -> canonical WAL lock order.

    Participating physical writers use the original admission lease. Direct
    unguarded file rewrites are detected on subsequent verification, but are
    outside the limited atomicity promise during this capture.
    """
    if not isinstance(loop, Stage27hBoundedMoveLoop):
        raise I4ALiveAnchorHold("original Stage27h run required")
    owner, physical = loop.owner, loop.physical
    if owner.cohort is None:
        raise I4ALiveAnchorHold("original Owner not attached")
    with owner.cohort.lock:
        _scoped_owner(
            owner, physical, lane,
            native_session_id=loop.prepared.native_session,
            world_epoch=loop.world_epoch,
        )
        if (
            getattr(owner, "_i4a_live_wal_anchor", None) is not None
            or loop.prepared.original_owner is not owner
            or loop.handoff.self_id != owner.self_id
            or loop.terminal_status is None
            or loop.action_count < 1
            or loop._settlement_reserved != 0
            or loop._reserved_source_seq is not None
            or owner.intent.current_intent is not None
        ):
            raise I4ALiveAnchorHold("S1 not an ended, unanchored original run")
        skill = owner.skills.get(loop.handoff.skill_execution_id)
        if (
            skill is None
            or skill.state not in (
                SkillState.CANCELLED, SkillState.FAILED, SkillState.SUCCEEDED,
            )
            or skill.intent_id != loop.handoff.intent_id
            or skill.skill_id != loop.invocation.skill_id
        ):
            raise I4ALiveAnchorHold("S1 terminal Skill not witnessed by original Owner")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=owner.native_session_id,
            ):
                journal = _read_quiescent(owner)
                rows = journal.records
                ids = tuple(row["action_id"] for row in rows)
                if (
                    len(rows) != loop.action_count
                    or journal.digest != loop.last_wal_digest
                    or ids[-1:] != (loop.last_action_id,)
                    or len(ids) != len(set(ids))
                    or set(ids) != loop._seen_action_ids
                    or any(
                        row["capability"] != "MOVE_PLACE"
                        or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                        or row["skill_execution_id"] != skill.execution_id
                        or row["intent_id"] != loop.handoff.intent_id
                        or row["session_id"] != owner.native_session_id
                        or row["invocation_ref"] != loop.invocation.invocation_ref
                        or row["preset_ref"] != loop.invocation.parameter_preset_ref
                        or row["target_contract_ref"]
                        != loop.invocation.target.contract.contract_ref
                        or owner.supervisor.get(row["action_id"]).state
                        is not ActionState.OUTCOME
                        for row in rows
                    )
                ):
                    raise I4ALiveAnchorHold("original S1 WAL/supervisor lineage changed")
                anchor = LiveWalHistoryAnchor(
                    owner.self_id, owner.native_session_id, loop.world_epoch,
                    loop.handoff.intent_id, skill.execution_id, ids,
                    journal.digest, len(rows),
                )
                # The witness remains in the same original Owner instance.
                # Rereading an arbitrary future WAL cannot manufacture it.
                owner._i4a_live_wal_anchor = anchor
                return anchor
        except PhysicalIssueFenceError as exc:
            raise I4ALiveAnchorHold("physical issuer not quiescent") from exc


def finish_and_anchor_live_stage27_run(
    loop: Stage27hBoundedMoveLoop,
    *,
    lane: ResidentLlamaInferenceLane,
    outcome: SkillState,
    reason: str,
    at_ns: int,
    provenance: Provenance,
) -> LiveWalHistoryAnchor:
    """Explicit DEV terminal transition + anchor in one participating lock window.

    This is not an inference/approval engine. Only the caller's already
    reviewed explicit cancellation/failure is accepted; no Goal success is
    inferred from settlement or from any L1 evaluation recommendation.
    """
    if (
        not isinstance(loop, Stage27hBoundedMoveLoop)
        or outcome not in (SkillState.CANCELLED, SkillState.FAILED)
        or type(reason) is not str or not reason.strip()
        or type(at_ns) is not int or at_ns <= 1
        or not isinstance(provenance, Provenance)
    ):
        raise I4ALiveAnchorHold("explicit reviewed non-success terminal required")
    owner, physical = loop.owner, loop.physical
    if owner.cohort is None:
        raise I4ALiveAnchorHold("live original Owner cohort absent")
    with owner.cohort.lock:
        _scoped_owner(
            owner, physical, lane,
            native_session_id=loop.prepared.native_session,
            world_epoch=loop.world_epoch,
        )
        if (
            getattr(owner, "_i4a_live_wal_anchor", None) is not None
            or loop.terminal_status is None
            or loop.action_count < 1
            or loop._settlement_reserved != 0
            or loop._reserved_source_seq is not None
            or owner.intent.current_intent is None
            or owner.intent.current_intent.intent_id != loop.handoff.intent_id
            or owner.intent.pending_reconsideration is not None
        ):
            raise I4ALiveAnchorHold("original S1 not eligible for explicit terminal")
        skill = owner.skills.get(loop.handoff.skill_execution_id)
        if (
            skill is None or skill.state is not SkillState.STARTED
            or skill.intent_id != loop.handoff.intent_id
            or skill.skill_id != loop.invocation.skill_id
            or not skill.is_current_snapshot
            or at_ns < skill.events[-1].at_ns
        ):
            raise I4ALiveAnchorHold("current original S1 Skill not eligible")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=owner.native_session_id,
            ):
                journal = _read_quiescent(owner)
                rows = journal.records
                if (
                    not rows or len(rows) != loop.action_count
                    or journal.digest != loop.last_wal_digest
                    or len(set(row["action_id"] for row in rows)) != len(rows)
                    or {row["action_id"] for row in rows} != loop._seen_action_ids
                    or rows[-1]["action_id"] != loop.last_action_id
                    or any(
                        row["capability"] != "MOVE_PLACE"
                        or row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                        or row["skill_execution_id"] != skill.execution_id
                        or row["intent_id"] != loop.handoff.intent_id
                        or row["session_id"] != owner.native_session_id
                        or row["invocation_ref"] != loop.invocation.invocation_ref
                        or row["preset_ref"] != loop.invocation.parameter_preset_ref
                        or row["target_contract_ref"]
                        != loop.invocation.target.contract.contract_ref
                        or owner.supervisor.get(row["action_id"]).state
                        is not ActionState.OUTCOME
                        for row in rows
                    )
                ):
                    raise I4ALiveAnchorHold("unqualified original S1 terminal WAL")
                # Both existing Owner API mutations are under the *same*
                # cohort+physical lock window. The subsequent anchor uses
                # the same reentrant locks and original WAL flock.
                owner.finish_reviewed_skill(
                    skill.execution_id, outcome=outcome, reason=reason,
                    at_ns=at_ns, provenance=provenance,
                )
                owner.complete_intent(
                    loop.handoff.intent_id,
                    reason="explicit S1 terminal release: " + reason,
                    at_ns=at_ns + 1, provenance=provenance,
                )
                return capture_live_wal_history_anchor(loop, lane=lane)
        except PhysicalIssueFenceError as exc:
            raise I4ALiveAnchorHold("physical S1 terminal window not quiescent") from exc


@dataclass(frozen=True, slots=True, eq=False)
class LiveS2Readiness:
    """Read-only current-Owner evidence, NOT a handoff/Action capability."""

    anchor: LiveWalHistoryAnchor
    self_id: str
    native_session_id: str
    world_epoch: int
    request_id: str
    probe_seq: int
    wal_sha256: str
    retained: object
    registry: object
    skills: tuple[tuple[str, object], ...]
    intent_events: tuple[object, ...]


def qualify_live_s2_readiness(
    owner: CheckpointedCognitiveOwner,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    anchor: LiveWalHistoryAnchor,
    first_probe: MineflayerObservation,
) -> LiveS2Readiness:
    """S2 preflight from fresh original Native CURRENT and sealed S1.

    The readiness cannot issue a Skill, Action or GPU task; it is a scoped
    source for a future new-current-Owner L1 selection implementation.
    """
    if (
        not isinstance(first_probe, MineflayerObservation)
        or first_probe.kind != "probe" or not first_probe.request_id
        or first_probe.snapshot.time is None
        or first_probe.snapshot.health <= 0
    ):
        raise I4ALiveAnchorHold("fresh Native CURRENT source required")
    if owner.cohort is None:
        raise I4ALiveAnchorHold("original cohort missing")
    with owner.cohort.lock:
        # Both this read and the original physical lease remain serialized.
        verify_live_wal_history_anchor(
            owner, physical=physical, lane=lane, anchor=anchor,
        )
        current = getattr(owner, "current_worldbody_observation", None)
        if (
            first_probe is not current
            or first_probe.session_id != anchor.native_session_id
            or first_probe.provenance.source != "mineflayer"
            or first_probe.provenance.reference
            != f"{first_probe.session_id}:{first_probe.seq}"
            or owner.intent.current_intent is not None
            or owner.intent.pending_reconsideration is not None
            or any(skill.state is SkillState.STARTED
                   for skill in owner.skills.values())
            or owner.pattern_registry != owner.retained.pattern_registry
        ):
            raise I4ALiveAnchorHold("new current Owner/Native S2 source not qualified")
        with physical.quiescent_wal_history_window(
            self_id=owner.self_id,
            native_session_id=owner.native_session_id,
        ):
            journal = _read_quiescent(owner)
            if (
                journal.digest != anchor.wal_sha256
                or len(journal.records) != anchor.wal_row_count
                or first_probe.seq <= journal.records[-1]["after_seq"]
            ):
                raise I4ALiveAnchorHold("S2 source is not newer than sealed S1")
            return LiveS2Readiness(
                anchor, owner.self_id, owner.native_session_id,
                anchor.world_epoch, first_probe.request_id, first_probe.seq,
                journal.digest, owner.retained, owner.pattern_registry,
                tuple(sorted(owner.skills.items())), owner.intent.events,
            )


def verify_live_wal_history_anchor(
    owner: CheckpointedCognitiveOwner,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    anchor: LiveWalHistoryAnchor,
) -> None:
    """Read-only historical comparison; grants no issue, handoff or GPU rights."""
    if (
        not isinstance(owner, CheckpointedCognitiveOwner)
        or owner.cohort is None
        or not isinstance(anchor, LiveWalHistoryAnchor)
    ):
        raise I4ALiveAnchorHold("live original Owner and anchor required")
    with owner.cohort.lock:
        if (
            getattr(owner, "_i4a_live_wal_anchor", None) is not anchor
            or anchor.self_id != owner.self_id
        ):
            raise I4ALiveAnchorHold("missing, foreign or replayed live Owner anchor")
        _scoped_owner(
            owner, physical, lane,
            native_session_id=anchor.native_session_id,
            world_epoch=anchor.world_epoch,
        )
        skill = owner.skills.get(anchor.skill_execution_id)
        if (
            skill is None
            or skill.state not in (
                SkillState.CANCELLED, SkillState.FAILED, SkillState.SUCCEEDED,
            )
            or skill.intent_id != anchor.intent_id
        ):
            raise I4ALiveAnchorHold("original terminal Skill history changed")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=anchor.native_session_id,
            ):
                journal = _read_quiescent(owner)
                if (
                    len(journal.records) != anchor.wal_row_count
                    or journal.digest != anchor.wal_sha256
                    or tuple(row["action_id"] for row in journal.records)
                    != anchor.action_ids
                    or any(
                        row["skill_execution_id"] != anchor.skill_execution_id
                        or row["intent_id"] != anchor.intent_id
                        or owner.supervisor.get(row["action_id"]).state
                        is not ActionState.OUTCOME
                        for row in journal.records
                    )
                ):
                    raise I4ALiveAnchorHold("S1 history differs from Owner-held witness")
        except PhysicalIssueFenceError as exc:
            raise I4ALiveAnchorHold("physical issuer not quiescent") from exc
