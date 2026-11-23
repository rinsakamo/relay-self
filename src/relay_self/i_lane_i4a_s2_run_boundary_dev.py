"""I4a DEV: authenticated empty S2 run boundary on the original live Owner.

Read-only eligibility. It NEVER grants a physical Action, constructs a
Stage27h parent or changes the old whole-WAL issuer/C evidence contracts.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionState
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    I4ALiveAnchorHold,
    LiveWalHistoryAnchor,
    _read_quiescent,
    _scoped_owner,
    verify_live_wal_history_anchor,
)
from relay_self.i_lane_i4a_s2_owner_handoff_dev import I4ANextWitness
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillState


class I4AS2RunBoundaryHold(RuntimeError):
    """S1 original history or S2 new-run Owner scope is not qualified."""


@dataclass(frozen=True, slots=True, eq=False)
class I4AS2EmptyRunBoundary:
    """An Owner-held S1 prefix and a *zero-Action* S2 scope, not a grant."""

    owner: CheckpointedCognitiveOwner
    anchor: LiveWalHistoryAnchor
    self_id: str
    native_session_id: str
    world_epoch: int
    decision_request_id: str
    post_model_probe_id: str
    post_model_probe_seq: int
    old_skill_id: str
    old_intent_id: str
    new_skill_id: str
    new_intent_id: str
    invocation_ref: str
    preset_ref: str
    target_ref: str
    prefix_count: int
    prefix_digest: str
    prefix_action_ids: tuple[str, ...]
    memory_snapshot: object
    registry_snapshot: object
    intent_events_snapshot: tuple[object, ...]
    skills_snapshot: tuple[tuple[str, object], ...]
    new_action_authorized: bool = False


def _require_original_empty_boundary(
    owner: CheckpointedCognitiveOwner,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    boundary: I4AS2EmptyRunBoundary,
    *,
    current_probe_id: str,
    current_probe_seq: int,
) -> None:
    _scoped_owner(
        owner, physical, lane,
        native_session_id=boundary.native_session_id,
        world_epoch=boundary.world_epoch,
    )
    verify_live_wal_history_anchor(
        owner, physical=physical, lane=lane, anchor=boundary.anchor,
    )
    skill = owner.skills.get(boundary.new_skill_id)
    previous = owner.skills.get(boundary.old_skill_id)
    current = owner.intent.current_intent
    probe = getattr(owner, "current_worldbody_observation", None)
    if (
        boundary.owner is not owner
        or getattr(owner, "_i4a_s2_empty_run_boundary", None) is not boundary
        or boundary.anchor is not getattr(owner, "_i4a_live_wal_anchor", None)
        or current is None or current.intent_id != boundary.new_intent_id
        or current.objective != "EXPLORE_WORLD"
        or skill is None or skill.state is not SkillState.STARTED
        or not skill.is_current_snapshot
        or skill.intent_id != boundary.new_intent_id
        or skill.skill_id != "MOVE"
        or previous is None
        or previous.state not in (
            SkillState.CANCELLED, SkillState.FAILED, SkillState.SUCCEEDED,
        )
        or previous.intent_id != boundary.old_intent_id
        or owner.intent.pending_reconsideration is not None
        or owner.supervisor.open_actions
        or owner.retained != boundary.memory_snapshot
        or owner.pattern_registry != boundary.registry_snapshot
        or owner.intent.events != boundary.intent_events_snapshot
        or tuple(sorted(owner.skills.items())) != boundary.skills_snapshot
        or probe is None or probe.kind != "probe"
        or probe.session_id != boundary.native_session_id
        or probe.request_id != current_probe_id
        or probe.seq != current_probe_seq
        or current_probe_id != boundary.post_model_probe_id
        or current_probe_seq != boundary.post_model_probe_seq
    ):
        raise I4AS2RunBoundaryHold("original S2 Owner/current cognition changed")

    journal = _read_quiescent(owner)
    actions = owner.supervisor.recorded_actions
    rows = journal.records
    if (
        len(rows) != boundary.prefix_count
        or journal.digest != boundary.prefix_digest
        or len(actions) != boundary.prefix_count
        or tuple(row["action_id"] for row in rows) != boundary.prefix_action_ids
        or len(set(boundary.prefix_action_ids)) != len(boundary.prefix_action_ids)
        or {action.action_id for action in actions} != set(boundary.prefix_action_ids)
        or any(
            action.state is not ActionState.OUTCOME
            or not action.is_current_snapshot
            or action.intent_id != boundary.old_intent_id
            or action.skill_execution_id != boundary.old_skill_id
            for action in actions
        )
        or any(
            row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
            or row["capability"] != "MOVE_PLACE"
            or row["intent_id"] != boundary.old_intent_id
            or row["skill_execution_id"] != boundary.old_skill_id
            or row["session_id"] != boundary.native_session_id
            for row in rows
        )
    ):
        raise I4AS2RunBoundaryHold("canonical S1 prefix or S2 empty suffix altered")


def attest_i4a_s2_empty_run_boundary(
    witness: I4ANextWitness,
    handoff: Stage27OwnedMoveIntent,
) -> I4AS2EmptyRunBoundary:
    """Bind a uniquely finished new Owner handoff to an intact S1 prefix.

    Called after the original S2 Owner-only handoff. Requires no Action yet,
    so cannot be confused with a second physical permission.
    """
    if (
        not isinstance(witness, I4ANextWitness)
        or not isinstance(handoff, Stage27OwnedMoveIntent)
        or handoff.physical_action_issued
        or handoff.physical_proposal_authorized
        or handoff.wal_modified
        or handoff.self_id != witness.prepared.owner.self_id
        or handoff.decision_request_id != witness.ticket.request_id
        or handoff.rechecked_native_seq != witness.after_probe.seq
        or handoff.native_session_id != witness.after_probe.session_id
        or handoff.world_epoch != witness.prepared.readiness.world_epoch
        or handoff.skill_execution_id
        != "stage27-skill-" + witness.ticket.request_id
        or handoff.intent_id != "stage27-intent-" + witness.ticket.request_id
    ):
        raise I4AS2RunBoundaryHold("S2 original new-owner handoff source unavailable")
    prepared = witness.prepared
    owner, physical, lane = prepared.owner, prepared.physical, prepared.lane
    anchor = prepared.readiness.anchor
    if owner.cohort is None:
        raise I4AS2RunBoundaryHold("original Owner cohort absent")
    with owner.cohort.lock:
        if getattr(owner, "_i4a_s2_empty_run_boundary", None) is not None:
            raise I4AS2RunBoundaryHold("replayed S2 empty boundary")
        try:
            verify_live_wal_history_anchor(
                owner, physical=physical, lane=lane, anchor=anchor,
            )
        except I4ALiveAnchorHold as exc:
            raise I4AS2RunBoundaryHold("S1 live history anchor stale") from exc
        opt = prepared.round.frame.options[0]
        inv = opt.invocation
        if (
            inv is None
            or inv.invocation_ref != handoff.invocation_ref
            or inv.parameter_preset_ref != handoff.preset_ref
            or opt.target_ref != handoff.target_ref
            or inv.target.contract is None
            or inv.target.contract.contract_ref
            != prepared.target.arrival_contract.contract_ref
            or owner.retained != prepared.readiness.retained
            or owner.pattern_registry != prepared.readiness.registry
        ):
            raise I4AS2RunBoundaryHold("S2 preset/target or current Memory changed")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=owner.native_session_id,
            ):
                journal = _read_quiescent(owner)
                if (
                    len(journal.records) != anchor.wal_row_count
                    or journal.digest != anchor.wal_sha256
                    or tuple(row["action_id"] for row in journal.records)
                    != anchor.action_ids
                ):
                    raise I4AS2RunBoundaryHold("S1 authenticated WAL prefix changed")
                result = I4AS2EmptyRunBoundary(
                    owner, anchor, owner.self_id, owner.native_session_id,
                    anchor.world_epoch, witness.ticket.request_id,
                    witness.after_probe.request_id, witness.after_probe.seq,
                    anchor.skill_execution_id, anchor.intent_id,
                    handoff.skill_execution_id, handoff.intent_id,
                    handoff.invocation_ref, handoff.preset_ref, handoff.target_ref,
                    anchor.wal_row_count, anchor.wal_sha256, anchor.action_ids,
                    owner.retained, owner.pattern_registry,
                    owner.intent.events, tuple(sorted(owner.skills.items())),
                )
                owner._i4a_s2_empty_run_boundary = result
                try:
                    _require_original_empty_boundary(
                        owner, physical, lane, result,
                        current_probe_id=witness.after_probe.request_id,
                        current_probe_seq=witness.after_probe.seq,
                    )
                except BaseException:
                    owner._i4a_s2_empty_run_boundary = None
                    raise
                return result
        except (PhysicalIssueFenceError, I4ALiveAnchorHold) as exc:
            raise I4AS2RunBoundaryHold("original WAL/issuer not quiescent") from exc


def verify_i4a_s2_empty_run_boundary(
    boundary: I4AS2EmptyRunBoundary,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
) -> None:
    """Revalidate the unchanged prefix while S2 still has zero Actions."""
    if (
        not isinstance(boundary, I4AS2EmptyRunBoundary)
        or boundary.new_action_authorized
        or boundary.owner.cohort is None
    ):
        raise I4AS2RunBoundaryHold("unrecognized or action-authorized S2 boundary")
    owner = boundary.owner
    with owner.cohort.lock:
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=boundary.native_session_id,
            ):
                _require_original_empty_boundary(
                    owner, physical, lane, boundary,
                    current_probe_id=boundary.post_model_probe_id,
                    current_probe_seq=boundary.post_model_probe_seq,
                )
        except (PhysicalIssueFenceError, I4ALiveAnchorHold) as exc:
            raise I4AS2RunBoundaryHold("previous Owner/WAL source no longer qualified") from exc
