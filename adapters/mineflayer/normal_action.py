"""S49 normal-session supervised MOVE_BACKWARD, independent of fault gates.

Real source probe and operator-issued PROPOSE / ISSUE grants are not inferred
from planning. Uses frozen S14/S15/S16 owners, never replays uncertain effects.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
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
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import LearningFeedbackInterpretation
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import (
    BoundExecutionCandidate,
    start_and_propose_bound_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import LearningCommitResult, LearningPreferenceState
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import (
    L0Step,
    ReactiveL0,
    ReactiveL0Rejected,
)
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_stage_q_dev_committed_world_choice,
    select_stage_t_dev_directional_world_choice,
    select_world_conditioned_choice,
    verify_stage_t_dev_directional_commit,
)


class NormalActionRejected(ValueError):
    """A current authenticated independent Action authority was not proven."""




@dataclass(frozen=True, slots=True)
class NormalRetainedOwnerReadback:
    """Unmodified exact L0 owner-held S10 state reference at constructor time."""

    session_id: str
    intent_id: str
    owner_snapshot: LearningPreferenceState


_OWNER_READ_ONLY: ContextVar[
    Callable[[NormalRetainedOwnerReadback], None] | None
] = ContextVar("normal_l0_retained_owner_read_only", default=None)


@contextmanager
def observe_original_retained_owner(
    callback: Callable[[NormalRetainedOwnerReadback], None],
) -> Iterator[None]:
    """S-only, opt-in DEV owner-identity tap; no write or learning grant."""
    if not callable(callback):
        raise NormalActionRejected("retained owner observer required")
    token = _OWNER_READ_ONLY.set(callback)
    try:
        yield
    finally:
        _OWNER_READ_ONLY.reset(token)


class NormalWorldL0(ReactiveL0):
    """S49 target-specific admission for one zombie amid other native entities.

    Unlike S44's deliberately one-total-entity experiment, genuine Minecraft
    can contain village cats, villagers, golems or other non-target entities.
    The original untruncated native snapshots stay intact. This operator
    selects exactly one *zombie* witness, never infers a safe empty World.
    """

    def __init__(
        self, session_id: str, intent_id: str,
        retained: LearningPreferenceState, *, max_events: int = 8,
        max_action_requests: int = 3,
    ) -> None:
        super().__init__(
            session_id, intent_id, retained, max_events=max_events,
            max_action_requests=max_action_requests,
        )
        self._stage_r_dev_token: object | None = None
        self._stage_r_dev_commit: LearningCommitResult | None = None
        # Stage T is explicit synthetic OFFLINE rehearsal, NOT S49 live path.
        self._stage_t_dev_token: object | None = None
        self._stage_t_dev_commit: LearningCommitResult | None = None
        self._stage_t_dev_s17: LearningFeedbackInterpretation | None = None
        # The SAME exact object is still owned by original L0, and is never
        # replaced by the observer or reconstructed from JSON.
        callback = _OWNER_READ_ONLY.get()
        if callback is not None:
            try:
                callback(NormalRetainedOwnerReadback(
                    self.session_id, self.intent_id, self.retained,
                ))
            except Exception:
                # Passive witness failures cannot veto original S49 owner.
                pass

    def bind_stage_r_dev_owner(self, *, token: object) -> None:
        """Explicit opt-in from sole S49 runner; no default learning authority."""
        if (self._stage_r_dev_token is not None
                or self._stage_r_dev_commit is not None
                or type(token) is not object
                or self.events != 0 or self.action_requests != 0
                or self.retained.target_id != "risk_weight"
                or self.retained.revision != 1
                or self.retained.value != 4):
            raise NormalActionRejected("Stage R owner must bind before native epochs")
        self._stage_r_dev_token = token

    def install_stage_r_dev_successor(
        self, *, token: object, commit: LearningCommitResult,
    ) -> None:
        """One synchronous, terminal-bound owner handoff (not Action issuance)."""
        if (self._stage_r_dev_token is None
                or self._stage_t_dev_token is not None
                or token is not self._stage_r_dev_token
                or self._stage_r_dev_commit is not None
                or not isinstance(commit, LearningCommitResult)
                or commit.previous_state is not self.retained
                or commit.new_state is self.retained
                or commit.new_state.revision != self.retained.revision + 1
                or commit.new_state.last_update is not commit.record
                or commit.new_state.value != self.retained.value
                or self.action_requests < 1):
            raise NormalActionRejected("no exact single-use Stage R owner transition")
        self.retained = commit.new_state
        self._stage_r_dev_commit = commit

    def bind_stage_t_dev_preview(self, *, token: object) -> None:
        """Opt-in offline original-host policy rehearsal; no issuer or Action."""
        if (
            type(token) is not object
            or self._stage_r_dev_token is not None
            or self._stage_t_dev_token is not None
            or self.events != 0 or self.action_requests != 0
            or self.retained.target_id != "risk_weight"
            or self.retained.revision != 1 or self.retained.value != 4
        ):
            raise NormalActionRejected("Stage T requires unused original rev1 owner")
        self._stage_t_dev_token = token

    def install_stage_t_dev_preview(
        self, *, token: object, commit: LearningCommitResult,
        typed_s17: LearningFeedbackInterpretation,
    ) -> None:
        """DEV/OFFLINE: one exact Stage S S17→S10 successor, no live runner.

        The real S49 qualify() does NOT call this method. Source-authenticated
        S10 issuer and physical admission remain separate qualification work.
        """
        if (
            self._stage_t_dev_token is None
            or token is not self._stage_t_dev_token
            or self._stage_r_dev_token is not None
            or self._stage_t_dev_commit is not None
            or self._stage_t_dev_s17 is not None
            or not isinstance(commit, LearningCommitResult)
            or commit.previous_state is not self.retained
            or not isinstance(typed_s17, LearningFeedbackInterpretation)
            or typed_s17.action_id not in self._used_action_ids
            or self.action_requests < 1
            or self.events < 1
        ):
            raise NormalActionRejected("Stage T exact original-host preview denied")
        successor = verify_stage_t_dev_directional_commit(
            commit, self.retained, typed_s17,
        )
        # No asynchronous window between preview owner and its evidence.
        self.retained = successor
        self._stage_t_dev_commit = commit
        self._stage_t_dev_s17 = typed_s17

    def _check(self, event, probe):
        if (
            not isinstance(event, MineflayerObservation)
            or not isinstance(probe, MineflayerObservation)
            or event.kind != "entities"
            or event.request_id is not None
            or probe.kind != "probe"
            or not probe.request_id
            or event.session_id != self.session_id
            or probe.session_id != self.session_id
            or event.seq <= self._last_seq
            or probe.seq <= event.seq
            or event.provenance.source != "mineflayer"
            or probe.provenance.source != "mineflayer"
            or event.snapshot.nearby_entities_coverage.truncated
            or probe.snapshot.nearby_entities_coverage.truncated
            or self.events >= self.max_events
        ):
            raise ReactiveL0Rejected("stale, foreign, incomplete native target source")
        before = [e for e in event.snapshot.nearby_entities if e.name == "zombie"]
        after = [e for e in probe.snapshot.nearby_entities if e.name == "zombie"]
        if (
            len(before) != 1
            or len(after) != 1
            or before[0].entity_id != after[0].entity_id
            or before[0].entity_id in self._seen_entities
        ):
            raise ReactiveL0Rejected("no single current native zombie witness")
        native = _native_threat(
            probe, probe.request_id, expected_entity_id=after[0].entity_id,
        )
        if self._stage_t_dev_commit is not None:
            assert self._stage_t_dev_s17 is not None
            return select_stage_t_dev_directional_world_choice(
                native, self.retained,
                commit=self._stage_t_dev_commit,
                original_owner=self._stage_t_dev_commit.previous_state,
                typed_s17=self._stage_t_dev_s17,
                expected_session_id=self.session_id,
                expected_entity_id=native.entity_id,
            )
        if self._stage_r_dev_commit is not None:
            return select_stage_q_dev_committed_world_choice(
                native, self.retained,
                commit=self._stage_r_dev_commit,
                original_owner=self._stage_r_dev_commit.previous_state,
                expected_session_id=self.session_id,
                expected_entity_id=native.entity_id,
            )
        return select_world_conditioned_choice(
            native, self.retained,
            expected_session_id=self.session_id, expected_entity_id=native.entity_id,
        )


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


@dataclass(frozen=True, slots=True)
class NormalActionClosedReadback:
    """Typed S16 closure delivered after original ActionSupervisor terminal."""

    terminal: ActionLifecycle
    interpretation: ActionOutcomeInterpretation
    consequence: WorldConsequence
    original_probe: MineflayerObservation


# Context-local, disabled by default. It is NOT an Action/LRN authority.
# The optional observer may inspect the already-closed original Action only.
_READ_ONLY_CLOSURE: ContextVar[
    Callable[[NormalActionClosedReadback], None] | None
] = ContextVar("normal_action_read_only_closure", default=None)


@contextmanager
def observe_closed_native_actions(
    callback: Callable[[NormalActionClosedReadback], None],
) -> Iterator[None]:
    """Product-owned DEV tap. Never grants, cancels or alters Action issuance."""
    if not callable(callback):
        raise NormalActionRejected("typed closure observer required")
    token = _READ_ONLY_CLOSURE.set(callback)
    try:
        yield
    finally:
        _READ_ONLY_CLOSURE.reset(token)


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
            or len([e for e in p.observed_entities if e.name == "zombie"]) != 1
            or not any(
                e.name == "zombie" and e.entity_id == step.choice.entity_id
                for e in p.observed_entities
            )
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
            observer = _READ_ONLY_CLOSURE.get()
            if observer is not None:
                # Only AFTER genuine terminal outcome closure; callback
                # failure cannot veto a dispatched/completed World Action.
                try:
                    observer(NormalActionClosedReadback(
                        terminal, interpretation, consequence, probe,
                    ))
                except Exception:
                    pass
            return NormalActionReceipt(terminal, consequence, probe.provenance)
        except BaseException:
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            raise
