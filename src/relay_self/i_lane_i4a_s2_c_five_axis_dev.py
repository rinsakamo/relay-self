"""I4a DEV: original Owner S1 historical prefix + S2 settled suffix to C L1.

Only a source-qualified read-only five-axis evaluation. No generic WAL
slicing is trusted; the previously live-Owner-certified S1 digest is
reconstructed from the full ORIGINAL canonical WAL and compared before
every bounded GPU choice, after each result and before final readout.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveReceipt
from relay_self.action import ActionState
from relay_self.c_lane_l1_evaluation_engine_dev import (
    EvaluationSourceStale,
    ExecutedEvaluation,
    InterruptedEvaluationAudit,
    _execute_evaluation,
)
from relay_self.c_lane_stage27hi_multi_action_review_dev import Stage27MultiReviewFrame
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import I4AS2FirstMoveProposal
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillState
from relay_self.target_contract import (
    TargetBodyObservation,
    evaluate_target,
)


class I4AS2CSourceHold(EvaluationSourceStale):
    """Historical S1 source or current S2 evidence cannot be adopted by C."""


@dataclass(frozen=True, slots=True, eq=False)
class I4AS2CQualified:
    """Original-source witness, not an Action grant or a Memory proposal."""

    frame: Stage27MultiReviewFrame
    candidate: I4AS2FirstMoveProposal
    receipt: Stage27PlaceMoveReceipt
    physical: PhysicalIssueAdmission
    lane: ResidentLlamaInferenceLane
    bridge: OwnedResidentPhysicalBridge
    last_owner_tick: int
    canonical_wal_sha256: str
    source_action_count: int = 1
    old_history_retained: bool = True
    physical_action_authorized: bool = False
    skill_success_attested: bool = False
    memory_adoption_authorized: bool = False


def _qualified_s2_source(
    candidate: I4AS2FirstMoveProposal,
    receipt: Stage27PlaceMoveReceipt,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    frame: Stage27MultiReviewFrame | None = None,
) -> tuple[PhysicalActionJournal, dict, str]:
    if (
        not isinstance(candidate, I4AS2FirstMoveProposal)
        or not isinstance(receipt, Stage27PlaceMoveReceipt)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or not isinstance(bridge, OwnedResidentPhysicalBridge)
    ):
        raise I4AS2CSourceHold("original S2 source objects required")
    bound = candidate.boundary
    owner = bound.owner
    anchor = bound.anchor
    first = candidate.source_probe
    after = receipt.settled_probe
    if owner.cohort is None:
        raise I4AS2CSourceHold("original Owner cohort missing")
    with owner.cohort.lock:
        if (
            owner.cohort is not lane.cognitive_work
            or lane.cognitive_work.owners.get(owner.self_id) is not owner
            or bridge.cognitive_work is not lane.cognitive_work
            or bridge.physical is not physical
            or bridge.owners.get(owner.self_id) is not owner
            or bridge.lifecycle.world.epoch != bound.world_epoch
            or bridge.paper.world_id != bridge.lifecycle.world.world_id
            or bridge.paper.owned_session_id
            != bridge.lifecycle.world.paper_session_id
            or bridge.paper.branch_id != bridge.lifecycle.world.branch_id
            or owner.self_id not in bridge.sessions
            or bridge.sessions[owner.self_id].started.session_id
            != bound.native_session_id
            or getattr(owner, "_i4a_live_wal_anchor", None) is not anchor
            or getattr(owner, "_i4a_s2_empty_run_boundary", None) is not bound
            or bound.self_id != owner.self_id
            or anchor.self_id != owner.self_id
            or anchor.native_session_id != bound.native_session_id
            or anchor.world_epoch != bound.world_epoch
            or bound.prefix_digest != anchor.wal_sha256
            or bound.prefix_count != anchor.wal_row_count
            or bound.prefix_action_ids != anchor.action_ids
            or candidate.action_id in bound.prefix_action_ids
            or candidate.ir.invocation.invocation_ref != bound.invocation_ref
            or candidate.ir.invocation.parameter_preset_ref != bound.preset_ref
            or candidate.ir.invocation.target.ref != bound.target_ref
            or candidate.ir.invocation.target.contract is None
            or candidate.proposal.binding.action_id != candidate.action_id
            or candidate.proposal.binding.skill_execution_id != bound.new_skill_id
            or candidate.proposal.binding.intent_id != bound.new_intent_id
            or receipt.action_id != candidate.action_id
            or receipt.original_invocation_ref != bound.invocation_ref
            or receipt.original_preset_ref != bound.preset_ref
            or receipt.target_contract_ref
            != candidate.ir.invocation.target.contract.contract_ref
            or receipt.native_session_id != bound.native_session_id
            or receipt.journal_status != "NATIVE_PLACE_MOVE_SETTLED"
            or not receipt.native_effect_issued
            or receipt.skill_success_attested or receipt.l0_goal_succeeded
            or owner.native_session_id != bound.native_session_id
            or owner.fresh_native_observation_required
            or getattr(owner, "current_worldbody_observation", None) != after
            or owner.supervisor.open_actions
            or physical.active_action_ids
            or not isinstance(first, MineflayerObservation)
            or not isinstance(after, MineflayerObservation)
            or first.session_id != bound.native_session_id
            or after.session_id != bound.native_session_id
            or first.kind != "probe" or after.kind != "probe"
            or first.request_id != bound.post_model_probe_id
            or first.seq != bound.post_model_probe_seq
            or after.seq <= first.seq or not after.request_id
            or after.snapshot.time is None or after.snapshot.health <= 0
            or after.provenance.reference != f"{after.session_id}:{after.seq}"
            or first.provenance.reference != f"{first.session_id}:{first.seq}"
        ):
            raise I4AS2CSourceHold("S1→S2 original Owner/Native context not qualified")
        try:
            scope = lane.cognitive_work.current_scope(owner.self_id)
        except ResidentCognitiveWorkError as exc:
            raise I4AS2CSourceHold("original resident Self fenced") from exc
        if scope[1:] != (bound.native_session_id, bound.world_epoch):
            raise I4AS2CSourceHold("native/World epoch stale")
        old_skill = owner.skills.get(bound.old_skill_id)
        new_skill = owner.skills.get(bound.new_skill_id)
        current_intent = owner.intent.current_intent
        if (
            old_skill is None or old_skill.state not in (
                SkillState.CANCELLED, SkillState.FAILED, SkillState.SUCCEEDED,
            )
            or old_skill.intent_id != bound.old_intent_id
            or new_skill is None or new_skill.state is not SkillState.STARTED
            or new_skill.intent_id != bound.new_intent_id
            or not new_skill.is_current_snapshot
            or current_intent is None
            or current_intent.intent_id != bound.new_intent_id
            or owner.intent.pending_reconsideration is not None
            or owner.retained != bound.memory_snapshot
            or owner.pattern_registry != bound.registry_snapshot
        ):
            raise I4AS2CSourceHold("S2 current Skill/Intent/Memory changed")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id, native_session_id=bound.native_session_id,
            ):
                journal = PhysicalActionJournal.restore(
                    owner.files.physical_wal_file, self_id=owner.self_id,
                )
                journal.require_clear()
                rows = journal.records
                if (
                    len(rows) != bound.prefix_count + 1
                    or journal.certified_prefix_digest(bound.prefix_count)
                    != bound.prefix_digest
                    or tuple(row["action_id"] for row in rows[:bound.prefix_count])
                    != bound.prefix_action_ids
                    or receipt.journal_sha256 != journal.digest
                    or any(
                        row["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                        or row["capability"] != "MOVE_PLACE"
                        or row["session_id"] != bound.native_session_id
                        or row["intent_id"] != bound.old_intent_id
                        or row["skill_execution_id"] != bound.old_skill_id
                        or owner.supervisor.get(row["action_id"]).state
                        is not ActionState.OUTCOME
                        for row in rows[:bound.prefix_count]
                    )
                ):
                    raise I4AS2CSourceHold("S1 certified prefix not retained")
                new = rows[-1]
                contract = candidate.ir.invocation.target.contract
                if (
                    new["action_id"] != candidate.action_id
                    or new["status"] != "NATIVE_PLACE_MOVE_SETTLED"
                    or new["capability"] != "MOVE_PLACE"
                    or new["session_id"] != bound.native_session_id
                    or new["intent_id"] != bound.new_intent_id
                    or new["skill_execution_id"] != bound.new_skill_id
                    or new["invocation_ref"] != bound.invocation_ref
                    or new["preset_ref"] != bound.preset_ref
                    or new["target_ref"] != bound.target_ref
                    or new["target_contract_ref"] != contract.contract_ref
                    or new["probe_seq"] != first.seq
                    or new["probe_request_id"] != first.request_id
                    or new["after_seq"] != after.seq
                    or new["effect_seqs"] != [
                        receipt.look_ack.seq, receipt.start_ack.seq,
                        receipt.stop_ack.seq,
                    ]
                    or any(
                        abs(getattr(first.snapshot.position, key)
                            - new["started_position"][key]) > 1e-6
                        or abs(getattr(after.snapshot.position, key)
                            - new["settled_position"][key]) > 1e-6
                        for key in ("x", "y", "z")
                    )
                    or owner.supervisor.get(candidate.action_id).state
                    is not ActionState.OUTCOME
                    or not owner.supervisor.get(candidate.action_id).is_current_snapshot
                ):
                    raise I4AS2CSourceHold("S2 Action/WAL/Native settled lineage invalid")
                if frame is not None and (
                    frame.self_id != owner.self_id
                    or frame.world_id != bridge.lifecycle.world.world_id
                    or frame.world_epoch != bound.world_epoch
                    or frame.skill_execution_id != bound.new_skill_id
                    or frame.intent_id != bound.new_intent_id
                    or frame.action_ids != (candidate.action_id,)
                    or frame.wal_digest != journal.digest
                    or frame.last_probe_seq != after.seq
                    or frame.last_request_id != after.request_id
                ):
                    raise I4AS2CSourceHold("S2 five-axis frame changed or reused")
                return journal, new, bridge.lifecycle.world.world_id
        except (PhysicalJournalError, PhysicalIssueFenceError) as exc:
            raise I4AS2CSourceHold("canonical WAL/issuer qualification lost") from exc


def prepare_i4a_s2_c_review(
    candidate: I4AS2FirstMoveProposal,
    receipt: Stage27PlaceMoveReceipt,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
) -> I4AS2CQualified:
    journal, row, world_id = _qualified_s2_source(
        candidate, receipt, physical=physical, lane=lane, bridge=bridge,
    )
    boundary = candidate.boundary
    owner = boundary.owner
    before = candidate.source_probe
    after = receipt.settled_probe
    inv = candidate.ir.invocation
    assessment_first = evaluate_target(inv.target.contract, TargetBodyObservation(
        scope=inv.scope, seq=before.seq, provenance=before.provenance,
        position=before.snapshot.position,
    ))
    assessment_last = evaluate_target(inv.target.contract, TargetBodyObservation(
        scope=inv.scope, seq=after.seq, provenance=after.provenance,
        position=after.snapshot.position,
    ))
    status = "I4A_S2_ONE_ACTION_SETTLED_YIELD_EVALUATION"
    request = BoundedChoiceRequest(
        request_id=(
            f"c-i4a-s2-{owner.self_id}-{boundary.native_session_id}-"
            f"{after.seq}-{journal.digest[:12]}"
        ),
        instruction=(
            "Evaluate ONLY the current S2 SkillRun one-Action suffix. "
            "Earlier S1 Actions are authenticated history, not S2 outcomes. "
            "This bounded L1 evaluation is read-only and cannot finish a Goal."
        ),
        intent_id=boundary.new_intent_id,
        focus="POST_S2_SKILL_EVALUATION",
        choices=(
            BoundedChoice("1", "CONTINUE without Action authority"),
            BoundedChoice("2", "EVALUATE_PARTIAL; no Skill success"),
            BoundedChoice("3", "ESCALATE_L2 without Action authority"),
            BoundedChoice("4", "DEFER"),
        ),
        context=(CognitionDatum.from_value(
            "original_multi_action_wal_and_target",
            {
                "self_id": owner.self_id,
                "world_id": world_id,
                "world_epoch": boundary.world_epoch,
                "intent_id": boundary.new_intent_id,
                "skill_execution_id": boundary.new_skill_id,
                "original_invocation_ref": boundary.invocation_ref,
                "target_contract_ref": inv.target.contract.contract_ref,
                "preset_ref": boundary.preset_ref,
                "original_action_ids": [candidate.action_id],
                "historical_action_ids": list(boundary.prefix_action_ids),
                "historical_wal_sha256": boundary.prefix_digest,
                "original_wal_sha256": journal.digest,
                "original_l0_terminal_status": status,
                "action_count": 1,
                "gait_modes": [row.get("gait_mode", "WALK")],
                "last_native_seq": after.seq,
                "target_status": assessment_last.status.value,
                "initial_target_status": assessment_first.status.value,
                "target_gap_m": assessment_last.gap_to_envelope_m,
                "initial_target_gap_m": assessment_first.gap_to_envelope_m,
                "executed_actions": [row],
                "unexecuted_actions": "UNKNOWN",
                "skill_success_attested": False,
                "goal_success_attested": False,
                "next_physical_action_authorized": False,
            }, after.provenance,
        ),),
        think_allowed=False,
    )
    frame = Stage27MultiReviewFrame(
        owner.self_id, boundary.native_session_id, boundary.world_epoch,
        world_id, boundary.new_skill_id, boundary.new_intent_id,
        (candidate.action_id,), before.seq, after.seq,
        after.request_id, journal.digest, boundary.invocation_ref,
        inv.target.contract.contract_ref, status, False, request,
    )
    return I4AS2CQualified(
        frame, candidate, receipt, physical, lane, bridge,
        owner.last_observed_tick, journal.digest,
    )


async def execute_i4a_s2_c_five_axis(
    source: I4AS2CQualified, *,
    task_id: str, budget_s: float = 60.0,
) -> ExecutedEvaluation:
    """Original resident T2, independent of old T1; no Memory/Skill mutation."""
    if not isinstance(source, I4AS2CQualified):
        raise I4AS2CSourceHold("qualified S2 source required")
    if (
        not isinstance(task_id, str) or not task_id.strip()
        or not task_id.startswith("i4a-t2-")
        or task_id == source.candidate.boundary.decision_request_id
    ):
        raise I4AS2CSourceHold("fresh dedicated T2 task identity required")
    candidate = source.candidate
    owner = candidate.boundary.owner
    frame = source.frame
    def validate() -> None:
        try:
            journal, _, _ = _qualified_s2_source(
                candidate, source.receipt,
                physical=source.physical, lane=source.lane,
                bridge=source.bridge, frame=frame,
            )
            if (
                journal.digest != source.canonical_wal_sha256
                or owner.last_observed_tick != source.last_owner_tick
                or source.candidate.boundary.new_skill_id
                != frame.skill_execution_id
            ):
                raise I4AS2CSourceHold("T2 original Owner/WAL/CURRENT changed")
        except I4AS2CSourceHold:
            raise

    receipts = []
    axes = []
    try:
        return await _execute_evaluation(
            frame, None, physical=source.physical, lane=source.lane,
            bridge=source.bridge,
            first_action_probe=candidate.source_probe,
            last_settled_probe=source.receipt.settled_probe,
            task_id=task_id, budget_s=budget_s,
            _receipts=receipts, _axes=axes,
            _source_validator=validate,
        )
    except BaseException as exc:
        status = "SOURCE_STALE" if isinstance(exc, EvaluationSourceStale) else "INTERRUPTED"
        exc.evaluation_audit = InterruptedEvaluationAudit(
            task_id, status, tuple(axes), tuple(receipts),
        )
        raise
