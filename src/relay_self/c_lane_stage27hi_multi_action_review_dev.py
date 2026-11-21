"""C Lane Stage27h/i: settled MOVE L0 -> original bounded L1 review -> C1.

The original L0 parent admits up to four terminal physical children but does NOT
call the single-child Stage27g review. Here a new bounded *read-only* L1
request is built from the exact original WAL and L0 terminal parent.
The separate, explicit Self acceptance is never inferred from model number 2.
No physical effect, Goal completion, Skill replay or C2 is authorized.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from adapters.llama_cpp.relay_engine import LlamaCppProviderError
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.c_lane_stage27_source_bridge import (
    assemble_stage27_c1_from_canonical_wal,
)
from relay_self.c_lane_stage27g_original_owner_review_dev import (
    C1OwnerReviewHold,
    OriginalSelfC1Approval,
    _sha,
)
from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_learning_contract import OutcomeAssessment
from relay_self.cognitive_learning_owner_adapter import propose_existing_memory
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27h_bounded_l0_move_dev import (
    Stage27hBoundedMoveLoop,
    Stage27hLoopRefusal,
    Stage27hLoopStep,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill import SkillState
from relay_self.target_contract import (
    TargetBodyObservation,
    TargetConditionStatus,
    evaluate_target,
)


@dataclass(frozen=True, slots=True)
class Stage27MultiReviewFrame:
    self_id: str
    native_session_id: str
    world_epoch: int
    world_id: str
    skill_execution_id: str
    intent_id: str
    action_ids: tuple[str, ...]
    first_probe_seq: int
    last_probe_seq: int
    last_request_id: str
    wal_digest: str
    invocation_ref: str
    target_contract_ref: str
    terminal_status: str
    completion_review_offered: bool
    request: BoundedChoiceRequest
    skill_mutated: bool = False
    goal_succeeded: bool = False
    physical_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Stage27MultiReviewWitness:
    frame: Stage27MultiReviewFrame
    ticket: ResidentInferenceTicket
    choice_number: str | None
    review_completion_selected: bool
    original_model_http_request_sha256: str
    original_model_http_response_sha256: str
    post_model_native_session_id: str
    post_model_probe_seq: int
    post_model_probe_request_id: str
    model_source_compatible: bool = True
    original_self_approval_attested: bool = False
    physical_effect_attested: bool = False
    skill_succeeded: bool = False
    goal_succeeded: bool = False
    physical_action_issued: bool = False


@dataclass(frozen=True, slots=True)
class Stage27MultiC1Retention:
    self_id: str
    skill_execution_id: str
    action_ids: tuple[str, ...]
    memory_id: str
    original_wal_sha256: str
    model_http_response_sha256: str
    terminal_skill_in_original_owner: bool = True
    original_cognition_file_readback: bool = True
    autonomous_approval_attested: bool = False
    actual_paper_native_causality_attested: bool = False
    parent_goal_completed: bool = False
    physical_action_replayed: bool = False


def _original_source(
    loop: Stage27hBoundedMoveLoop,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
) -> tuple[CheckpointedCognitiveOwner, PhysicalActionJournal]:
    if (
        not isinstance(loop, Stage27hBoundedMoveLoop)
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
        or loop.physical is not physical
        or not isinstance(bridge, OwnedResidentPhysicalBridge)
        or bridge.physical is not physical
        or bridge.owners.get(loop.owner.self_id) is not loop.owner
        or bridge.cognitive_work is not lane.cognitive_work
        or bridge.lifecycle.world.epoch != loop.world_epoch
        or bridge.paper.owned_session_id
        != bridge.lifecycle.world.paper_session_id
        or bridge.paper.world_id != bridge.lifecycle.world.world_id
        or bridge.paper.branch_id != bridge.lifecycle.world.branch_id
        or loop.owner.self_id not in bridge.sessions
        or bridge.sessions[loop.owner.self_id].started.session_id
        != loop.owner.native_session_id
        or lane.cognitive_work.owners.get(loop.owner.self_id) is not loop.owner
        or loop.owner.cohort is not lane.cognitive_work
        or loop.prepared.original_owner is not loop.owner
        or loop.terminal_status is None
        or loop.action_count < 1 or loop.action_count > 4
        or loop._settlement_reserved != 0
        or loop._reserved_source_seq is not None
        or loop.owner.fresh_native_observation_required
    ):
        raise C1OwnerReviewHold("original terminal multi-child cognitive scope absent")
    try:
        scope = lane.cognitive_work.current_scope(loop.owner.self_id)
    except ResidentCognitiveWorkError as exc:
        raise C1OwnerReviewHold("original Self cognitive epoch is fenced") from exc
    if scope[1:] != (loop.prepared.native_session, loop.world_epoch):
        raise C1OwnerReviewHold("original native/World cognitive scope changed")
    try:
        journal = loop._validate_owner_and_journal()
        journal.require_clear()
    except (Stage27hLoopRefusal, PhysicalJournalError) as exc:
        raise C1OwnerReviewHold("original terminal L0/WAL not qualified") from exc
    rows = journal.records
    if (
        len(rows) != loop.action_count
        or journal.digest != loop.last_wal_digest
        or len({r["action_id"] for r in rows}) != len(rows)
        or loop.last_action_id != rows[-1]["action_id"]
        or loop.last_native_seq != rows[-1]["after_seq"]
        or any(
            r["capability"] != "MOVE_PLACE"
            or r["status"] != "NATIVE_PLACE_MOVE_SETTLED"
            or r["skill_execution_id"] != loop.handoff.skill_execution_id
            or r["intent_id"] != loop.handoff.intent_id
            or r["session_id"] != loop.prepared.native_session
            or r["invocation_ref"] != loop.invocation.invocation_ref
            or r["preset_ref"] != loop.invocation.parameter_preset_ref
            or r["target_contract_ref"]
            != loop.invocation.target.contract.contract_ref
            or r.get("gait_mode", "WALK") not in ("WALK", "SNEAK")
            for r in rows
        )
        or any(
            loop.owner.supervisor.get(r["action_id"]).state
            is not ActionState.OUTCOME
            for r in rows
        )
    ):
        raise C1OwnerReviewHold("original multi-child Action/WAL lineage changed")
    return loop.owner, journal


def prepare_stage27hi_multi_review(
    loop: Stage27hBoundedMoveLoop,
    step: Stage27hLoopStep,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    first_action_probe: MineflayerObservation,
    last_settled_probe: MineflayerObservation,
    world_id: str,
) -> Stage27MultiReviewFrame:
    """One finite-choice review of settled evidence, without MOVE authority.

    Partial review is not an independent Self adoption decision and does not
    authorize the existing success-only C1 retention path.
    """
    owner, journal = _original_source(loop, physical=physical, lane=lane, bridge=bridge)
    rows = journal.records
    if (
        not isinstance(step, Stage27hLoopStep)
        or world_id != bridge.lifecycle.world.world_id
        or not isinstance(first_action_probe, MineflayerObservation)
        or not isinstance(last_settled_probe, MineflayerObservation)
        or type(world_id) is not str or not world_id
        or step.status != loop.terminal_status
        or step.status not in {
            "L0_TARGET_REACHED_YIELD_EVALUATION",
            "L0_WORLD_CONDITION_YIELD_EVALUATION",
            "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION",
            "L0_OVERSHOOT_YIELD_EVALUATION",
            "L0_NO_PROGRESS_YIELD_EVALUATION",
            "L0_CUMULATIVE_OVERSHOOT_YIELD_EVALUATION",
        }
        or step.action_count != loop.action_count
        or step.last_action_id != loop.last_action_id
        or step.terminal_wal_sha256 != journal.digest
        or step.last_native_seq != loop.last_native_seq
        or first_action_probe.seq != rows[0]["probe_seq"]
        or first_action_probe.request_id != rows[0]["probe_request_id"]
        or first_action_probe.kind != "probe"
        or first_action_probe.provenance.source != "mineflayer"
        or first_action_probe.provenance.reference
        != f"{owner.native_session_id}:{first_action_probe.seq}"
        or any(getattr(first_action_probe.snapshot.position, coord) !=
               rows[0]["started_position"][coord] for coord in ("x", "y", "z"))
        or last_settled_probe.seq != rows[-1]["after_seq"]
        or last_settled_probe.session_id != owner.native_session_id
        or first_action_probe.session_id != owner.native_session_id
        or last_settled_probe.kind != "probe"
        or not last_settled_probe.request_id
        or last_settled_probe.snapshot.time is None
        or last_settled_probe.snapshot.health <= 0
        or last_settled_probe.provenance.source != "mineflayer"
        or last_settled_probe.provenance.reference
        != f"{owner.native_session_id}:{last_settled_probe.seq}"
        or any(getattr(last_settled_probe.snapshot.position, coord) !=
               rows[-1]["settled_position"][coord] for coord in ("x", "y", "z"))
    ):
        raise C1OwnerReviewHold("last L0 status/native source not terminal or foreign")
    contract = loop.invocation.target.contract
    assert contract is not None
    assessment = evaluate_target(contract, TargetBodyObservation(
        scope=loop.invocation.scope,
        seq=last_settled_probe.seq,
        provenance=last_settled_probe.provenance,
        position=last_settled_probe.snapshot.position,
    ))
    initial_assessment = evaluate_target(contract, TargetBodyObservation(
        scope=loop.invocation.scope, seq=first_action_probe.seq,
        provenance=first_action_probe.provenance,
        position=first_action_probe.snapshot.position,
    ))
    observed_reached = assessment.status is TargetConditionStatus.CONDITION_OBSERVED
    reached = step.status == "L0_TARGET_REACHED_YIELD_EVALUATION" and observed_reached
    if step.status == "L0_TARGET_REACHED_YIELD_EVALUATION" and not observed_reached:
        raise C1OwnerReviewHold("terminal Target observation changed")
    ids = tuple(r["action_id"] for r in rows)
    request = BoundedChoiceRequest(
        request_id=(
            f"c-stage27hi-review-{owner.self_id}-{owner.native_session_id}-"
            f"{last_settled_probe.seq}"
        ),
        instruction=(
            "Original bounded MOVE Skill executed physical children. "
            "Choose only a numbered evaluation recommendation. A Target status "
            "is a WorldBody observation, NOT Goal or Skill completion. "
            "Do not issue an Action, set a parameter or grant success."
        ),
        intent_id=loop.handoff.intent_id,
        focus="POST_MULTI_ACTION_SKILL_EVALUATION",
        choices=(
            BoundedChoice("1", "CONTINUE_INTENT: gather new WorldBody, no Action"),
            BoundedChoice("2", (
                "REVIEW_COMPLETION: only consider owner terminal review" if reached
                else "EVALUATE_PARTIAL: consider progress, effectiveness, information, "
                "applicability, failure conditions and uncertainty; do not infer success"
            )),
            BoundedChoice("3", "ESCALATE_L2: deliberate without Action authority"),
            BoundedChoice("4", "DEFER: leave original Skill STARTED"),
        ),
        context=(CognitionDatum.from_value(
            "original_multi_action_wal_and_target",
            {
                "self_id": owner.self_id,
                "native_session_id": owner.native_session_id,
                "world_id": world_id,
                "world_epoch": loop.world_epoch,
                "intent_id": loop.handoff.intent_id,
                "skill_execution_id": loop.handoff.skill_execution_id,
                "original_invocation_ref": loop.invocation.invocation_ref,
                "target_contract_ref": contract.contract_ref,
                "preset_ref": loop.invocation.parameter_preset_ref,
                "original_action_ids": list(ids),
                "original_wal_sha256": journal.digest,
                "original_l0_terminal_status": loop.terminal_status,
                "action_count": loop.action_count,
                "gait_modes": [r.get("gait_mode", "WALK") for r in rows],
                "last_native_seq": last_settled_probe.seq,
                "target_status": assessment.status.value,
                "initial_target_status": initial_assessment.status.value,
                "target_gap_m": assessment.gap_to_envelope_m,
                "initial_target_gap_m": initial_assessment.gap_to_envelope_m,
                "executed_actions": list(rows),
                "unexecuted_actions": "UNKNOWN; not evidence of failure",
                "skill_success_attested": False,
                "goal_success_attested": False,
                "next_physical_action_authorized": False,
            }, last_settled_probe.provenance,
        ),),
        think_allowed=False,
    )
    return Stage27MultiReviewFrame(
        owner.self_id, owner.native_session_id, loop.world_epoch, world_id,
        loop.handoff.skill_execution_id, loop.handoff.intent_id, ids,
        first_action_probe.seq, last_settled_probe.seq,
        last_settled_probe.request_id, journal.digest,
        loop.invocation.invocation_ref, contract.contract_ref,
        loop.terminal_status, reached, request,
    )


def submit_stage27hi_multi_review(
    frame: Stage27MultiReviewFrame,
    loop: Stage27hBoundedMoveLoop,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    first_action_probe: MineflayerObservation,
    last_settled_probe: MineflayerObservation,
) -> ResidentInferenceTicket:
    current = prepare_stage27hi_multi_review(
        loop, frame_to_step(frame, loop),
        physical=physical, lane=lane, bridge=bridge,
        first_action_probe=first_action_probe,
        last_settled_probe=last_settled_probe,
        world_id=frame.world_id,
    )
    if current != frame:
        raise C1OwnerReviewHold("original multi-action L1 request was altered")
    lane.require_world_idle()
    ticket = lane.submit(
        frame.self_id, work_ref=f"c-stage27hi:{frame.wal_digest}:{frame.last_probe_seq}",
        request=frame.request, mode=CognitionMode.BOUNDED,
    )
    if (
        ticket.self_id != frame.self_id
        or ticket.request_id != frame.request.request_id
        or ticket.native_session_id != frame.native_session_id
        or ticket.world_epoch != frame.world_epoch
        or ticket.action_issue_authorized
    ):
        raise C1OwnerReviewHold("shared L1 ticket not bound to original Self")
    return ticket


def frame_to_step(frame: Stage27MultiReviewFrame, loop: Stage27hBoundedMoveLoop) -> Stage27hLoopStep:
    """Reconstruct only immutable original terminal counters for read-only audit.

    Never a new L0 continuation or physical authority. The original loop and
    canonical journal are independently checked by prepare_stage27hi_multi_review.
    """
    return Stage27hLoopStep(
        frame.terminal_status, "CONDITION_OBSERVED", None,
        loop.action_count, loop.observation_count, loop.cumulative_distance_m,
        loop.last_native_seq, loop.last_action_id, loop.last_wal_digest,
    )


async def finish_stage27hi_multi_review(
    frame: Stage27MultiReviewFrame,
    loop: Stage27hBoundedMoveLoop,
    *,
    ticket: ResidentInferenceTicket,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    first_action_probe: MineflayerObservation,
    last_settled_probe: MineflayerObservation,
    fresh_probe: Callable[[], Awaitable[MineflayerObservation]],
) -> tuple[Stage27MultiReviewWitness, MineflayerObservation]:
    """Wait on original GPU slot, then obtain one *new* native probe."""
    if (
        not isinstance(ticket, ResidentInferenceTicket)
        or not callable(fresh_probe)
        or ticket.request_id != frame.request.request_id
        or ticket.self_id != frame.self_id
        or ticket.world_epoch != frame.world_epoch
        or ticket.native_session_id != frame.native_session_id
        or ticket.backend_ref != lane.backend_ref
        or ticket.mode is not CognitionMode.BOUNDED
        or ticket.work_ref != f"c-stage27hi:{frame.wal_digest}:{frame.last_probe_seq}"
        or ticket.action_issue_authorized
    ):
        raise C1OwnerReviewHold("foreign post-L0 original model ticket")
    current = prepare_stage27hi_multi_review(
        loop, frame_to_step(frame, loop), physical=physical, lane=lane,
        bridge=bridge,
        first_action_probe=first_action_probe,
        last_settled_probe=last_settled_probe, world_id=frame.world_id,
    )
    if current != frame:
        raise C1OwnerReviewHold("original multi-action context altered before L1 result")
    result = await lane.await_result(ticket)
    if not isinstance(result, ProviderDecision) or lane.result(ticket) != result:
        raise C1OwnerReviewHold("bounded original L1 decision absent")
    facts = result.call_facts
    if (
        facts.finish_reason != "stop"
        or facts.prompt_tokens is None
        or facts.completion_tokens is None
        or facts.total_tokens != facts.prompt_tokens + facts.completion_tokens
    ):
        raise C1OwnerReviewHold("original model token/source facts not attested")
    raw = lane.provider.stage26_raw_receipt(ticket.request_id)
    if (
        _sha(Path(raw.request_path)) != raw.request_sha256
        or _sha(Path(raw.response_path)) != raw.response_sha256
    ):
        raise C1OwnerReviewHold("owned model HTTP original bytes changed")
    # The original resident GPU job must be idle BEFORE a new native query.
    lane.require_world_idle()
    after = await fresh_probe()
    if (
        not isinstance(after, MineflayerObservation)
        or after.kind != "probe"
        or after.session_id != frame.native_session_id
        or not after.request_id
        or after.request_id == frame.last_request_id
        or after.seq <= frame.last_probe_seq
        or after.provenance.source != "mineflayer"
        or after.provenance.reference
        != f"{frame.native_session_id}:{after.seq}"
        or after.snapshot.time is None
        or after.snapshot.health <= 0
    ):
        raise C1OwnerReviewHold("original post-model native source is stale/foreign")
    _original_source(loop, physical=physical, lane=lane, bridge=bridge)
    if lane.result(ticket) != result:
        raise C1OwnerReviewHold("L1 result lost original GPU scope")
    contract = loop.invocation.target.contract
    assert contract is not None
    target = evaluate_target(contract, TargetBodyObservation(
        scope=loop.invocation.scope, seq=after.seq,
        provenance=after.provenance, position=after.snapshot.position,
    ))
    selected = result.choice_id if result.status is DecisionStatus.RESOLVED else None
    if selected is not None and selected not in {c.choice_id for c in frame.request.choices}:
        raise C1OwnerReviewHold("model selected unoffered post-L0 choice")
    witness = Stage27MultiReviewWitness(
        frame, ticket, selected,
        frame.completion_review_offered and selected == "2"
        and target.status is TargetConditionStatus.CONDITION_OBSERVED,
        raw.request_sha256, raw.response_sha256,
        after.session_id, after.seq, after.request_id,
    )
    return witness, after


def accept_stage27hi_original_c1(
    *,
    witness: Stage27MultiReviewWitness,
    approval: OriginalSelfC1Approval,
    loop: Stage27hBoundedMoveLoop,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    first_action_probe: MineflayerObservation,
    last_settled_probe: MineflayerObservation,
    post_model_probe: MineflayerObservation,
    at_ns: int,
) -> Stage27MultiC1Retention:
    """Original Owner Skill+C1 write, requiring distinct explicit Self approval."""
    if (
        not isinstance(witness, Stage27MultiReviewWitness)
        or not isinstance(approval, OriginalSelfC1Approval)
        or approval.explicit_self_decision != "ACCEPT_SKILL_SUCCESS_AND_RETAIN_C1"
        or approval.self_id != witness.frame.self_id
        or approval.native_session_id != witness.frame.native_session_id
        or approval.evaluation_request_id != witness.frame.request.request_id
        or approval.skill_execution_id != witness.frame.skill_execution_id
        or not witness.review_completion_selected
        or witness.choice_number != "2"
        or witness.skill_succeeded or witness.goal_succeeded
        or witness.physical_action_issued or witness.original_self_approval_attested
        or type(at_ns) is not int or at_ns < 0
    ):
        raise C1OwnerReviewHold("independent original Self terminal adoption not supplied")
    owner = loop.owner
    with owner._mutating():
        _original_source(loop, physical=physical, lane=lane, bridge=bridge)
        current = prepare_stage27hi_multi_review(
            loop, frame_to_step(witness.frame, loop),
            physical=physical, lane=lane, bridge=bridge,
            first_action_probe=first_action_probe,
            last_settled_probe=last_settled_probe, world_id=witness.frame.world_id,
        )
        if current != witness.frame:
            raise C1OwnerReviewHold("multi-Action original review became stale")
        if (
            owner.current_worldbody_observation != post_model_probe
            or post_model_probe.kind != "probe"
            or post_model_probe.session_id != owner.native_session_id
            or post_model_probe.seq != witness.post_model_probe_seq
            or post_model_probe.request_id != witness.post_model_probe_request_id
            or post_model_probe.provenance.source != "mineflayer"
            or post_model_probe.provenance.reference
            != f"{post_model_probe.session_id}:{post_model_probe.seq}"
            or post_model_probe.seq <= witness.frame.last_probe_seq
        ):
            raise C1OwnerReviewHold("post-model current source not adopted by original Self")
        contract = loop.invocation.target.contract
        assert contract is not None
        target = evaluate_target(contract, TargetBodyObservation(
            scope=loop.invocation.scope, seq=post_model_probe.seq,
            provenance=post_model_probe.provenance,
            position=post_model_probe.snapshot.position,
        ))
        if target.status is not TargetConditionStatus.CONDITION_OBSERVED:
            raise C1OwnerReviewHold("target condition expired before Self adoption")
        if (
            witness.ticket.request_id != witness.frame.request.request_id
            or witness.ticket.self_id != owner.self_id
            or witness.ticket.native_session_id != owner.native_session_id
            or witness.ticket.world_epoch != loop.world_epoch
            or witness.ticket.backend_ref != lane.backend_ref
            or witness.ticket.action_issue_authorized
        ):
            raise C1OwnerReviewHold("original bounded GPU ticket scope altered")
        result = lane.result(witness.ticket)
        try:
            raw = lane.provider.stage26_raw_receipt(witness.ticket.request_id)
        except (LlamaCppProviderError, OSError, ValueError) as exc:
            raise C1OwnerReviewHold("original model HTTP evidence unavailable or altered") from exc
        if (
            not isinstance(result, ProviderDecision)
            or result.status is not DecisionStatus.RESOLVED
            or result.choice_id != "2"
            or witness.original_model_http_request_sha256 != raw.request_sha256
            or witness.original_model_http_response_sha256 != raw.response_sha256
            or _sha(Path(raw.request_path)) != raw.request_sha256
            or _sha(Path(raw.response_path)) != raw.response_sha256
            or lane.require_world_idle().n_slots != 1
        ):
            raise C1OwnerReviewHold("original bounded model choice/bytes no longer qualified")
        if (
            load_persistent_cognition(owner.files.cognition_file) != owner.retained
            or owner.supervisor.open_actions
        ):
            raise C1OwnerReviewHold("original Owner storage or Action fence changed")
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        actions = tuple(
            owner.supervisor.get(r["action_id"]) for r in journal.records
        )
        old = owner.skills[witness.frame.skill_execution_id]
        stamp = max(old.events[-1].at_ns, *(a.events[-1].at_ns for a in actions))
        if at_ns <= stamp:
            raise C1OwnerReviewHold("terminal Self review before physical child")
        # Preflight candidate on DETACHED Skill history: avoid partial owner
        # mutation from native/WAL/Target failure or duplicate C1.
        draft = copy.deepcopy(old).succeed(
            reason="explicit Self review of bounded multi-MOVE",
            at_ns=at_ns, provenance=approval.provenance,
        )
        exp = assemble_stage27_c1_from_canonical_wal(
            cognition=owner.retained, intent=owner.intent, skill=draft,
            actions=actions, journal_path=owner.files.physical_wal_file,
            original_wal_sha256=journal.digest,
            selected_invocation=loop.invocation,
            before_probe=first_action_probe,
            after_probe=last_settled_probe,
            world_id=witness.frame.world_id, world_epoch=loop.world_epoch,
            selected_provenance=approval.provenance,
        )
        if (
            exp is None
            or exp.action_ids != witness.frame.action_ids
            or exp.target_outcome is not OutcomeAssessment.SUCCESS
        ):
            raise C1OwnerReviewHold("original three-child episode source not qualified")
        memory = propose_existing_memory(
            owner.retained, exp, integration_provenance=approval.provenance,
        )
        if memory is None:
            raise C1OwnerReviewHold("C1 is already retained: refuse second adoption")
        terminal = owner.finish_reviewed_skill(
            old.execution_id, outcome=SkillState.SUCCEEDED,
            reason="explicit Self review of bounded multi-MOVE",
            at_ns=at_ns, provenance=approval.provenance,
        )
        if terminal.events != draft.events:
            raise C1OwnerReviewHold("owner terminal Skill differed from preflight")
        owner.retain_memory(memory)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
        if (
            load_persistent_cognition(owner.files.cognition_file) != owner.retained
            or owner.skills[old.execution_id] is not terminal
            or PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=owner.self_id,
            ).digest != witness.frame.wal_digest
        ):
            raise C1OwnerReviewHold("canonical original multi-Action C1 file readback failed")
        return Stage27MultiC1Retention(
            owner.self_id, old.execution_id, exp.action_ids,
            memory.memory_id, journal.digest, raw.response_sha256,
        )
