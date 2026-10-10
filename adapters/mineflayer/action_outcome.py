from __future__ import annotations

from adapters.mineflayer.execution import (
    MineflayerCommand,
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
)
from relay_self.action import ActionLifecycle
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
    InvalidActionOutcomeData,
)
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.provenance import Provenance


def interpret_world_consequence(
    issued_action: ActionLifecycle,
    binding_result: ExecutionBindingResult,
    consequence: WorldConsequence,
    *,
    provenance: Provenance,
    allow_forward: bool = False,
) -> ActionOutcomeInterpretation:
    """Purely interpret one exact S15 consequence for existing Action closure.

    The exact S15 issued-action / binding guard is reused rather than rebuilt.
    This function owns no Action state and performs no supervisor transition.
    """

    command = build_mineflayer_command(
        issued_action, binding_result, allow_forward=allow_forward,
    )
    if not isinstance(consequence, WorldConsequence):
        raise InvalidActionOutcomeData(
            "consequence must be WorldConsequence"
        )
    if not isinstance(provenance, Provenance):
        raise InvalidActionOutcomeData(
            "interpretation provenance must be Provenance"
        )

    _require_exact_consequence_lineage(
        command,
        binding_result,
        consequence,
    )

    if consequence.status is WorldConsequenceStatus.EXECUTED:
        disposition = ActionOutcomeDisposition.OUTCOME
        reason_code = "observed_execution"
    elif consequence.status is WorldConsequenceStatus.FAILED:
        dispatch = consequence.dispatch_receipt
        if dispatch is not None and dispatch.result == "rejected":
            # Existing Mineflayer runtime semantics already treat an explicit
            # rejected effect_result as a known target result: OUTCOME means
            # known result, not successful Action.
            disposition = ActionOutcomeDisposition.OUTCOME
            reason_code = "known_adapter_rejection"
        else:
            # A transport/adapter/cleanup failure does not establish whether
            # the physical Action succeeded. Existing UNKNOWN is the exact
            # Action-owner representation for that unresolved closure.
            disposition = ActionOutcomeDisposition.UNKNOWN
            reason_code = "adapter_failure_consequence_unknown"
    else:
        # S15 UNDETERMINED already carries complete structured observations
        # but does not establish the qualified physical consequence. Preserve
        # the issued Action for later evidence or ActionSupervisor timeout.
        disposition = ActionOutcomeDisposition.UNAVAILABLE
        reason_code = "world_consequence_undetermined"

    return ActionOutcomeInterpretation(
        action_id=issued_action.action_id,
        binding_id=binding_result.binding_id,
        action_ref=binding_result.action_ref,
        skill_execution_id=issued_action.skill_execution_id,
        intent_id=issued_action.intent_id,
        session_id=consequence.session_id,
        source_status=consequence.status.value,
        disposition=disposition,
        reason_code=reason_code,
        world_provenance=consequence.provenance,
        provenance=provenance,
    )


def _require_exact_consequence_lineage(
    command: MineflayerCommand,
    binding_result: ExecutionBindingResult,
    consequence: WorldConsequence,
) -> None:
    if consequence.action_id != command.action_id:
        raise InvalidActionOutcomeData(
            "WorldConsequence action_id does not match issued Action"
        )
    if consequence.binding_id != command.binding_id:
        raise InvalidActionOutcomeData(
            "WorldConsequence binding_id does not match ExecutionBindingResult"
        )
    if consequence.action_ref != command.action_ref:
        raise InvalidActionOutcomeData(
            "WorldConsequence action_ref does not match ExecutionBindingResult"
        )
    if binding_result.action_id != command.action_id:
        raise InvalidActionOutcomeData(
            "ExecutionBindingResult action_id does not match Mineflayer command"
        )

    evidence = (
        consequence.before_observation,
        consequence.dispatch_receipt,
        consequence.cleanup_receipt,
        consequence.after_observation,
    )
    for item in evidence:
        if item is not None and item.session_id != consequence.session_id:
            raise InvalidActionOutcomeData(
                "WorldConsequence evidence session_id mismatch"
            )

    dispatch = consequence.dispatch_receipt
    if dispatch is not None:
        if dispatch.action_id != consequence.action_id:
            raise InvalidActionOutcomeData(
                "WorldConsequence dispatch action_id mismatch"
            )
        if dispatch.effect != command.effect:
            raise InvalidActionOutcomeData(
                "WorldConsequence dispatch effect mismatch"
            )

    cleanup = consequence.cleanup_receipt
    if cleanup is not None:
        if cleanup.action_id != command.cleanup_action_id:
            raise InvalidActionOutcomeData(
                "WorldConsequence cleanup action_id mismatch"
            )
        if cleanup.effect != "clear_controls":
            raise InvalidActionOutcomeData(
                "WorldConsequence cleanup effect mismatch"
            )
