"""S40 one-way reconciliation: real Node death after applied Action dispatch.

An applied adapter effect is *not* proof of completed movement. A genuine
in-flight Node death with missing cleanup/after observation is adjudicated as
UNKNOWN through frozen S16 and the existing ActionSupervisor; never retry.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    MineflayerCommand,
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
)
from adapters.mineflayer.process_session import MineflayerProcessEnded
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.forced_node_loss_fence import ForcedNodeLossFence, WorldLossState
from relay_self.provenance import Provenance


class InFlightNodeLossRejected(ValueError):
    """Insufficient evidence for supervised post-dispatch UNKNOWN closure."""


@dataclass(frozen=True, slots=True)
class InFlightUnknownReceipt:
    action_id: str
    binding_id: str
    session_id: str
    before_seq: int
    applied_dispatch_seq: int
    process_returncode: int
    transport_error_type: str
    raw_world_status: str
    terminal_action_state: str
    interpretation_reason: str
    replay_authorized: bool


def close_inflight_node_loss_unknown(
    fence: ForcedNodeLossFence,
    supervisor: ActionSupervisor,
    issued: ActionLifecycle,
    binding_result: ExecutionBindingResult,
    command: MineflayerCommand,
    consequence: WorldConsequence,
    *,
    session_id: str,
    transport_error: MineflayerProcessEnded,
    process_returncode: int,
    at_ns: int,
    provenance: Provenance,
) -> tuple[ActionLifecycle, InFlightUnknownReceipt]:
    """Close exact in-flight ISSUE to UNKNOWN; never authorize a replacement.

    The S38 caller has already observed a genuine second process EOF and
    quarantined this source. Caller must serialize this method with issuance.
    The gate checks the native applied receipt and the absence of post-effect
    completion evidence; it does not infer what occurred in the actual World.
    """
    if (
        not isinstance(fence, ForcedNodeLossFence)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(issued, ActionLifecycle)
        or not isinstance(binding_result, ExecutionBindingResult)
        or not isinstance(command, MineflayerCommand)
        or not isinstance(consequence, WorldConsequence)
        or not isinstance(session_id, str)
        or not session_id
        or not isinstance(transport_error, MineflayerProcessEnded)
        or type(process_returncode) is not int
        or process_returncode >= 0
        or type(at_ns) is not int
        or at_ns < 0
        or not isinstance(provenance, Provenance)
        or fence.state is not WorldLossState.QUARANTINED
    ):
        raise InFlightNodeLossRejected("typed negative actual Node loss required")
    fault = fence.fault
    if (
        fault is None
        or fault.session_id != session_id
        or fault.process_returncode != process_returncode
        or fault.transport_error != "MineflayerProcessEnded"
    ):
        raise InFlightNodeLossRejected("source must be quarantined for exact Node death")
    if (
        issued.state is not ActionState.ISSUED
        or supervisor.get(issued.action_id) is not issued
        or issued is not supervisor.get(issued.action_id)
        or command != build_mineflayer_command(issued, binding_result)
        or consequence.action_id != issued.action_id
        or consequence.binding_id != binding_result.binding_id
        or consequence.session_id != session_id
        or consequence.status is not WorldConsequenceStatus.FAILED
        or consequence.before_observation is None
        or consequence.before_observation.session_id != session_id
        or consequence.dispatch_receipt is None
        or consequence.dispatch_receipt.result != "applied"
        or consequence.dispatch_receipt.action_id != command.action_id
        or consequence.dispatch_receipt.effect != command.effect
        or consequence.dispatch_receipt.session_id != session_id
        or consequence.dispatch_receipt.seq <= consequence.before_observation.seq
        or consequence.cleanup_receipt is not None
        or consequence.after_observation is not None
        or consequence.movement_distance is not None
        or consequence.error is None
        or "MineflayerProcessEnded" not in consequence.error
    ):
        raise InFlightNodeLossRejected(
            "requires current ISSUED Action, applied effect and absent final World evidence"
        )
    interpretation = interpret_world_consequence(
        issued, binding_result, consequence, provenance=provenance,
    )
    if (
        interpretation.disposition is not ActionOutcomeDisposition.UNKNOWN
        or interpretation.reason_code != "adapter_failure_consequence_unknown"
        or interpretation.session_id != session_id
    ):
        raise InFlightNodeLossRejected("existing S16 must select UNKNOWN, not success")
    closed = record_interpreted_action_outcome(
        supervisor, interpretation, at_ns=at_ns,
    )
    if closed.state is not ActionState.UNKNOWN:
        raise InFlightNodeLossRejected("existing Action owner did not terminate UNKNOWN")
    receipt = InFlightUnknownReceipt(
        action_id=closed.action_id,
        binding_id=binding_result.binding_id,
        session_id=session_id,
        before_seq=consequence.before_observation.seq,
        applied_dispatch_seq=consequence.dispatch_receipt.seq,
        process_returncode=process_returncode,
        transport_error_type=type(transport_error).__name__,
        raw_world_status=consequence.status.value,
        terminal_action_state=closed.state.value,
        interpretation_reason=interpretation.reason_code,
        replay_authorized=False,
    )
    return closed, receipt
