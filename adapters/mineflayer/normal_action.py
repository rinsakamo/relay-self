"""S49 normal-session supervised MOVE_BACKWARD, independent of fault gates.

Real source probe and operator-issued PROPOSE / ISSUE grants are not inferred
from planning. Uses frozen S14/S15/S16 owners, never replays uncertain effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequence,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    BoundExecutionCandidate,
    start_and_propose_bound_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0Step
from relay_self.world_conditioned_choice import WorldChoiceKind


class NormalActionRejected(ValueError):
    """A current authenticated independent Action authority was not proven."""


class NormalActionStage(str, Enum):
    PROPOSE = "PROPOSE"
    ISSUE = "ISSUE"


@dataclass(frozen=True, slots=True)
class NormalActionAuthorization:
    stage: NormalActionStage
    authority_id: str
    intent_id: str
    session_id: str
    action_id: str
    event_seq: int
    probe_seq: int
    entity_id: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stage, NormalActionStage)
            or not all(isinstance(v, str) and v for v in (
                self.authority_id, self.intent_id, self.session_id,
                self.action_id,
            ))
            or any(type(v) is not int or v < 0 for v in (
                self.event_seq, self.probe_seq, self.entity_id,
            ))
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise NormalActionRejected("independent typed Action authorization required")


@dataclass(frozen=True, slots=True)
class NormalActionReceipt:
    terminal: ActionLifecycle
    consequence: WorldConsequence
    source: Provenance


class NormalSessionActionExecutor:
    """Caller-owned one-session Action supervisor, never implicit authority."""

    def __init__(self, session_id: str, intent: IntentCommitment) -> None:
        if (
            not isinstance(session_id, str) or not session_id
            or not isinstance(intent, IntentCommitment)
            or intent.current_intent is None
        ):
            raise NormalActionRejected("active named session and Intent required")
        self.session_id = session_id
        self.intent = intent
        self.supervisor = ActionSupervisor()
        self._dispatched: set[str] = set()
        self._count = 0

    def require_authorizations(
        self, step: L0Step, bound: BoundExecutionCandidate,
        probe: MineflayerObservation,
        propose: NormalActionAuthorization, issue: NormalActionAuthorization,
    ) -> None:
        if (
            not isinstance(step, L0Step)
            or step.choice.selection is not WorldChoiceKind.MOVE_AWAY
            or not step.asks_for_action or step.grant is None
            or not isinstance(bound, BoundExecutionCandidate)
            or not isinstance(probe, MineflayerObservation)
            or self.intent.current_intent is None
            or self.intent.pending_reconsideration is not None
            or probe.session_id != self.session_id
            or probe.seq != step.choice.probe_seq
            or probe.request_id != step.choice.request_id
            or probe.provenance != step.choice.provenance
            or probe.snapshot.nearby_entities_coverage.truncated
            or not isinstance(propose, NormalActionAuthorization)
            or not isinstance(issue, NormalActionAuthorization)
            or propose.stage is not NormalActionStage.PROPOSE
            or issue.stage is not NormalActionStage.ISSUE
            or not propose.granted or not issue.granted
            or propose.authority_id == issue.authority_id
            or propose.provenance == issue.provenance
            or step.grant.authority_id in {
                propose.authority_id, issue.authority_id,
            }
            or step.grant.provenance in {
                propose.provenance, issue.provenance,
            }
            or self.supervisor.open_actions
        ):
            raise NormalActionRejected("live source/Action admission is not current")
        p = project_mineflayer_present(probe)
        if (
            p.coverage_truncated
            or len(p.observed_entities) != 1
            or p.observed_entities[0].entity_id != step.choice.entity_id
            or bound.candidate_ref != "MOVE_AWAY"
            or bound.binding.action_ref != "MOVE_BACKWARD"
            or bound.binding.action_id != step.action_request_id
            or bound.binding.action_id in self._dispatched
            or bound.intent_id != self.intent.current_intent.intent_id
            or bound.binding.required_intent_id != step.grant.intent_id
            or bound.binding.required_intent_id != self.intent.current_intent.intent_id
        ):
            raise NormalActionRejected("source/retained/bound Action mismatch")
        for g in (propose, issue):
            if (
                g.intent_id != bound.intent_id
                or g.session_id != self.session_id
                or g.action_id != step.action_request_id
                or g.event_seq != step.event_seq
                or g.probe_seq != step.choice.probe_seq
                or g.entity_id != step.choice.entity_id
            ):
                raise NormalActionRejected("authority is not scoped to this exact event")

    async def execute(
        self, session: MineflayerProcessSession, step: L0Step,
        bound: BoundExecutionCandidate, probe: MineflayerObservation,
        propose: NormalActionAuthorization, issue: NormalActionAuthorization,
        *, timeout_s: float = 9,
    ) -> NormalActionReceipt:
        if (
            not isinstance(session, MineflayerProcessSession)
            or session.started.session_id != self.session_id
            or session.process_returncode is not None
        ):
            raise NormalActionRejected("live Mineflayer session mismatch")
        self.require_authorizations(step, bound, probe, propose, issue)
        # A monotonically increasing owner-local ordering index, not wall time.
        t = 100 + 10 * self._count
        origin = Provenance("normal-action-runtime", f"{self.session_id}:{t}")
        skill, proposed, result = start_and_propose_bound_execution(
            bound, self.intent, at_ns=t, provenance=origin,
        )
        if not skill.is_current_snapshot or proposed.state is not ActionState.PROPOSED:
            raise NormalActionRejected("actual Skill/Action proposal absent")
        authorized = proposed.authorize(
            at_ns=t + 1, provenance=propose.provenance,
            authority=propose.authority_id,
        )
        issued = self.supervisor.issue(
            authorized, at_ns=t + 2, deadline_ns=t + 100,
            provenance=issue.provenance,
        )
        command = build_mineflayer_command(issued, result)
        # Consumed BEFORE any external IO. Incomplete physical work is UNKNOWN.
        self._dispatched.add(command.action_id)
        self._count += 1
        try:
            consequence = await execute_mineflayer_command(
                session, command, timeout_s=timeout_s, provenance=origin,
            )
            interpretation = interpret_world_consequence(
                issued, result, consequence, provenance=origin,
            )
            if interpretation.disposition is ActionOutcomeDisposition.UNAVAILABLE:
                terminal = self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            else:
                terminal = record_interpreted_action_outcome(
                    self.supervisor, interpretation, at_ns=t + 3,
                )
            return NormalActionReceipt(terminal, consequence, probe.provenance)
        except BaseException:
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            raise
