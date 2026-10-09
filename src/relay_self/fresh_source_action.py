"""S39 caller-serial gate: post-fault fresh World cognition -> explicit one-shot Action.

Not a global capability sandbox: callers must use this gate for the S39 path.
The unmodified ActionSupervisor/adapter remain independently accessible to
other callers. No implicit proposal, authorization, issue or retry occurs.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.execution import MineflayerCommand, build_mineflayer_command
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.bounded_native_host_loop import HostCognitionEvent
from relay_self.execution_binding import (
    ExecutionBinding,
    ExecutionBindingResult,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.forced_node_loss_fence import ForcedNodeLossFence, WorldLossState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class FreshSourceActionRejected(ValueError):
    """Missing fresh post-fault source, separate authority or one-shot lineage."""


@dataclass(frozen=True, slots=True)
class FreshSourceActionGrant:
    authority_id: str
    purpose: str
    session_id: str
    event_seq: int
    probe_seq: int
    entity_id: int
    binding_id: str
    action_id: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authority_id, str) or not self.authority_id
            or self.purpose not in {"PROPOSE", "ISSUE"}
            or not isinstance(self.session_id, str) or not self.session_id
            or any(type(x) is not int or x < 0 for x in (
                self.event_seq, self.probe_seq, self.entity_id,
            ))
            or not isinstance(self.binding_id, str) or not self.binding_id
            or not isinstance(self.action_id, str) or not self.action_id
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
        ):
            raise FreshSourceActionRejected("malformed explicit scoped Action grant")


class FreshSourceActionGate:
    """Only a verified successor HostCognitionEvent can release one Action.

    Bound to the precise in-memory event/ticket object; the S38 fence remains
    responsible for the native source generation. The caller separately grants
    PROPOSE and ISSUE. No cross-process replay claim.
    """

    def __init__(
        self, fence: ForcedNodeLossFence,
        supervisor: ActionSupervisor,
        event: HostCognitionEvent,
    ) -> None:
        if (
            not isinstance(fence, ForcedNodeLossFence)
            or not isinstance(supervisor, ActionSupervisor)
            or not isinstance(event, HostCognitionEvent)
        ):
            raise FreshSourceActionRejected("typed fence, supervisor, event required")
        self._fence = fence
        self._supervisor = supervisor
        self._event = event
        self._proposal_grant: FreshSourceActionGrant | None = None
        self._proposed: ActionLifecycle | None = None
        self._binding_result: ExecutionBindingResult | None = None
        self._issued: ActionLifecycle | None = None
        self._dispatched = False

    def _require_source(self) -> dict:
        event = self._event
        ticket = event.ticket
        if (
            self._fence.state is not WorldLossState.ACTIVE
            or self._fence.fault is None
            or self._fence.host.active_session_id != event.session_id
            or self._fence.fault.session_id == event.session_id
            or ticket.candidate.session_id != event.session_id
            or ticket.candidate.event_seq != event.event_seq
            or ticket.candidate.target_entity_id != event.entity_id
            or ticket.correlated_probe.session_id != event.session_id
            or ticket.correlated_probe.seq != event.probe_seq
            or ticket.probe_request_id != event.probe_request_id
            or event.event_seq >= event.probe_seq
        ):
            raise FreshSourceActionRejected("not a current post-fault native generation")
        self._fence.require_active_ticket(ticket)
        result = event.cognition
        if (
            not isinstance(result, dict)
            or result.get("selected") != "MOVE_AWAY"
            or result.get("admission") != "admitted"
            or result.get("source") != ticket.correlated_probe.provenance.reference
            or not isinstance(result.get("values"), dict)
        ):
            raise FreshSourceActionRejected("missing bound cognition trace")
        values = result["values"]
        if (
            values.get("plan") is None
            or values["plan"].selected is None
            or values["plan"].selected.candidate_id != "MOVE_AWAY"
            or values.get("admission") is None
            or values["admission"].status.value != "admitted"
            or values.get("external") is None
            or values["external"][1].provenance != ticket.correlated_probe.provenance
            or values.get("read") is None
            or values["read"].revision != 1
        ):
            raise FreshSourceActionRejected("cognition does not bind new native proof")
        return values

    def _require_grant(
        self, grant: FreshSourceActionGrant, purpose: str, binding: ExecutionBinding,
    ) -> None:
        event = self._event
        if (
            not isinstance(grant, FreshSourceActionGrant)
            or not grant.granted
            or grant.purpose != purpose
            or grant.session_id != event.session_id
            or grant.event_seq != event.event_seq
            or grant.probe_seq != event.probe_seq
            or grant.entity_id != event.entity_id
            or grant.binding_id != binding.binding_id
            or grant.action_id != binding.action_id
            or grant.provenance.source == "mineflayer"
            or grant.provenance == event.ticket.grant.provenance
        ):
            raise FreshSourceActionRejected("separately scoped Action grant rejected")

    def propose(
        self, intent: IntentCommitment, binding: ExecutionBinding,
        grant: FreshSourceActionGrant, *, at_ns: int, provenance: Provenance,
    ) -> tuple[SkillExecution, ActionLifecycle, ExecutionBindingResult]:
        values = self._require_source()
        if self._proposed is not None or not isinstance(binding, ExecutionBinding):
            raise FreshSourceActionRejected("one proposal and typed binding only")
        self._require_grant(grant, "PROPOSE", binding)
        bound = resolve_execution_binding(
            values["admission"], values["control"], values["route"],
            intent, values["policies"][-2], binding, provenance=provenance,
        )
        skill, proposed, result = start_and_propose_bound_execution(
            bound, intent, at_ns=at_ns, provenance=provenance,
        )
        if proposed.state is not ActionState.PROPOSED:
            raise FreshSourceActionRejected("Action owner not PROPOSED")
        self._proposed = proposed
        self._binding_result = result
        self._proposal_grant = grant
        return skill, proposed, result

    def authorize_issue(
        self, proposed: ActionLifecycle, binding: ExecutionBinding,
        grant: FreshSourceActionGrant, *, at_ns: int, deadline_ns: int,
        provenance: Provenance,
    ) -> ActionLifecycle:
        self._require_source()
        if (
            self._proposed is None or proposed is not self._proposed
            or self._issued is not None or self._binding_result is None
            or self._proposal_grant is None
            or binding.binding_id != self._binding_result.binding_id
            or binding.action_id != proposed.action_id
        ):
            raise FreshSourceActionRejected("unproposed/replayed/foreign Action")
        self._require_grant(grant, "ISSUE", binding)
        if (
            grant.authority_id == self._proposal_grant.authority_id
            or grant.provenance == self._proposal_grant.provenance
        ):
            raise FreshSourceActionRejected("ISSUE needs an independent authority")
        authorized = proposed.authorize(
            at_ns=at_ns, provenance=provenance, authority=grant.authority_id,
        )
        issued = self._supervisor.issue(
            authorized, at_ns=at_ns, deadline_ns=deadline_ns,
            provenance=provenance,
        )
        self._issued = issued
        return issued

    def claim_command(
        self, issued: ActionLifecycle, session: object,
    ) -> MineflayerCommand:
        self._require_source()
        if (
            self._dispatched or self._issued is None
            or issued is not self._issued or self._binding_result is None
            or self._supervisor.get(issued.action_id) is not issued
            or getattr(getattr(session, "started", None), "session_id", None)
            != self._event.session_id
            or getattr(session, "process_returncode", None) is not None
        ):
            raise FreshSourceActionRejected("not a current one-shot physical dispatch")
        command = build_mineflayer_command(issued, self._binding_result)
        # Consumed *before* an external IO call. No retry if a World result
        # becomes uncertain: handling in-flight UNKNOWN belongs to S40.
        self._dispatched = True
        return command
