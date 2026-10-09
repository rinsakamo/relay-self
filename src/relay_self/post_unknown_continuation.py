"""S41 caller-serial post-UNKNOWN continuation: new source, new Action.

S40 UNKNOWN is an immutable historical terminal Action, not a pending operation
to retry. The explicit third Node generation must independently revalidate a
new native event and probe through the unchanged S38/S37/S35 cognition chain.
Only then may new, disjoint PROPOSE and ISSUE grants flow into the S39 gate.
No reconstruction of the old physical effect is attempted or authorized.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.bounded_native_host_loop import HostCognitionEvent
from relay_self.execution_binding import ExecutionBinding
from relay_self.forced_node_loss_fence import (
    ForcedNodeLossFence,
    WorldLossState,
)
from relay_self.fresh_source_action import FreshSourceActionGate
from relay_self.inflight_node_loss import InFlightUnknownReceipt
from relay_self.provenance import Provenance


class PostUnknownReentryRejected(ValueError):
    """Explicit source/authority/Action lineage did not qualify a new Action."""


@dataclass(frozen=True, slots=True)
class PostUnknownReentryGrant:
    authority_id: str
    previous_action_id: str
    previous_session_id: str
    new_session_id: str
    new_event_seq: int
    new_probe_seq: int
    new_entity_id: int
    new_action_id: str
    new_binding_id: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            any(not isinstance(x, str) or not x.strip() for x in (
                self.authority_id, self.previous_action_id,
                self.previous_session_id, self.new_session_id,
                self.new_action_id, self.new_binding_id,
            ))
            or any(type(v) is not int or v < 0 for v in (
                self.new_event_seq, self.new_probe_seq, self.new_entity_id,
            ))
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
        ):
            raise PostUnknownReentryRejected("malformed S41 explicit reentry grant")


@dataclass(frozen=True, slots=True)
class PostUnknownContinuationReceipt:
    prior_action_id: str
    prior_terminal: str
    prior_world_outcome: str
    prior_session_id: str
    new_action_id: str
    new_terminal: str
    new_session_id: str
    new_event_seq: int
    new_probe_seq: int
    new_entity_id: int
    historical_unknown_rewritten: bool
    previous_command_replayed: bool


class PostUnknownContinuationGate:
    """Separate one new Action from a terminal UNKNOWN, without retroclosure.

    Requires the *same* bounded S38 fence to see a fresh third generation
    through its ordinary PROBATION -> ACTIVE transition; use an explicit
    HostLoopBudget(max_sessions=3, max_total_epochs=3) at construction.
    No privileged S38 state bypass, no hidden recovery, no global sandbox.
    """

    def __init__(
        self,
        fence: ForcedNodeLossFence,
        supervisor: ActionSupervisor,
        unknown: ActionLifecycle,
        unknown_receipt: InFlightUnknownReceipt,
    ) -> None:
        if (
            not isinstance(fence, ForcedNodeLossFence)
            or not isinstance(supervisor, ActionSupervisor)
            or not isinstance(unknown, ActionLifecycle)
            or not isinstance(unknown_receipt, InFlightUnknownReceipt)
            or unknown.state is not ActionState.UNKNOWN
            or supervisor.get(unknown.action_id) is not unknown
            or supervisor.open_actions != ()
            or fence.state is not WorldLossState.QUARANTINED
            or fence.fault is None
            or fence.fault.session_id != unknown_receipt.session_id
            or fence.fault.process_returncode != unknown_receipt.process_returncode
            or fence.fault.transport_error != "MineflayerProcessEnded"
            or unknown.action_id != unknown_receipt.action_id
            or unknown_receipt.terminal_action_state != ActionState.UNKNOWN.value
            or unknown_receipt.raw_world_status != "failed"
            or unknown_receipt.interpretation_reason
            != "adapter_failure_consequence_unknown"
            or unknown_receipt.replay_authorized
        ):
            raise PostUnknownReentryRejected(
                "requires exact terminal UNKNOWN and quarantined S40 source"
            )
        self._fence = fence
        self._supervisor = supervisor
        self._unknown = unknown
        self._receipt = unknown_receipt
        self._admitted = False
        self._new_event: HostCognitionEvent | None = None

    def admit_new_action(
        self,
        event: HostCognitionEvent,
        binding: ExecutionBinding,
        grant: PostUnknownReentryGrant,
    ) -> FreshSourceActionGate:
        """Return an S39 gate only after new native source and distinct authority.

        The caller must *separately* supply S39 PROPOSE and ISSUE grants.
        """
        if (
            self._admitted
            or not isinstance(event, HostCognitionEvent)
            or not isinstance(binding, ExecutionBinding)
            or not isinstance(grant, PostUnknownReentryGrant)
            or not grant.granted
            or grant.provenance.source == "mineflayer"
            or self._fence.state is not WorldLossState.ACTIVE
            or self._fence.fault is None
            or self._fence.fault.session_id != self._receipt.session_id
            or self._fence.host.active_session_id != event.session_id
            or event.session_id == self._receipt.session_id
            or event.ticket.candidate.session_id != event.session_id
            or event.ticket.correlated_probe.session_id != event.session_id
            or event.ticket.correlated_probe.seq != event.probe_seq
            or event.ticket.candidate.event_seq != event.event_seq
            or event.ticket.candidate.target_entity_id != event.entity_id
            or event.event_seq >= event.probe_seq
            or binding.action_id == self._unknown.action_id
            or binding.skill_execution_id == self._unknown.skill_execution_id
            or self._supervisor.get(self._unknown.action_id) is not self._unknown
            or self._supervisor.open_actions != ()
            or grant.previous_action_id != self._unknown.action_id
            or grant.previous_session_id != self._receipt.session_id
            or grant.new_session_id != event.session_id
            or grant.new_event_seq != event.event_seq
            or grant.new_probe_seq != event.probe_seq
            or grant.new_entity_id != event.entity_id
            or grant.new_action_id != binding.action_id
            or grant.new_binding_id != binding.binding_id
            or grant.authority_id in {"", event.ticket.grant.authority_id}
            or grant.provenance == event.ticket.grant.provenance
        ):
            raise PostUnknownReentryRejected(
                "fresh native generation, disjoint Action and reentry grant required"
            )
        self._fence.require_active_ticket(event.ticket)
        if (
            not isinstance(event.cognition, dict)
            or event.cognition.get("selected") != "MOVE_AWAY"
            or event.cognition.get("admission") != "admitted"
            or event.cognition.get("source")
            != event.ticket.correlated_probe.provenance.reference
        ):
            raise PostUnknownReentryRejected("new independently admitted cognition missing")
        self._admitted = True
        self._new_event = event
        return FreshSourceActionGate(self._fence, self._supervisor, event)

    def verify_independent_terminal(
        self, new_terminal: ActionLifecycle,
    ) -> PostUnknownContinuationReceipt:
        """Read-only adjudication. Never change old UNKNOWN to OUTCOME."""
        event = self._new_event
        if (
            not self._admitted
            or event is None
            or not isinstance(new_terminal, ActionLifecycle)
            or new_terminal.action_id == self._unknown.action_id
            or new_terminal.skill_execution_id == self._unknown.skill_execution_id
            or self._supervisor.get(self._unknown.action_id) is not self._unknown
            or self._unknown.state is not ActionState.UNKNOWN
            or self._supervisor.get(new_terminal.action_id) is not new_terminal
            or new_terminal.state is not ActionState.OUTCOME
            or self._supervisor.open_actions != ()
            or self._fence.state is not WorldLossState.ACTIVE
            or self._fence.host.active_session_id != event.session_id
        ):
            raise PostUnknownReentryRejected(
                "only a distinct supervised terminal OUTCOME preserves prior UNKNOWN"
            )
        self._fence.require_active_ticket(event.ticket)
        return PostUnknownContinuationReceipt(
            prior_action_id=self._unknown.action_id,
            prior_terminal=self._unknown.state.value,
            prior_world_outcome="UNDETERMINED",
            prior_session_id=self._receipt.session_id,
            new_action_id=new_terminal.action_id,
            new_terminal=new_terminal.state.value,
            new_session_id=event.session_id,
            new_event_seq=event.event_seq,
            new_probe_seq=event.probe_seq,
            new_entity_id=event.entity_id,
            historical_unknown_rewritten=False,
            previous_command_replayed=False,
        )
