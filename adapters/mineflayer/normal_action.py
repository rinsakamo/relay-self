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
from adapters.mineflayer.d6_loot_approach import (
    D6LootApproach,
    source_qualified_loot_approach,
)
from adapters.mineflayer.attack_execution import AttackActionReceipt, IssuedAttackingExecutor
from adapters.mineflayer.eat_execution import EatingActionReceipt, IssuedEatingExecutor
from adapters.mineflayer.execution import (
    WorldConsequence,
    WorldConsequenceStatus,
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
from relay_self.eat_hunger import EatChoice, EatCursor, EatingOutcome, EatStatus
from relay_self.execution_binding import (
    BoundExecutionCandidate,
    ExecutionBindingResult,
    start_and_propose_bound_execution,
)
from relay_self.intent import IntentCommitment, IntentEventKind
from relay_self.learning import LearningCommitResult, LearningPreferenceState
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import (
    L0Step,
    ReactiveL0,
    ReactiveL0Rejected,
)
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from relay_self.skill import SkillExecution, SkillState
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

    def extend_after_worldbody_rest_dev(self, *, token: object) -> None:
        """Separate, bounded DEV approval: ONE extra genuine L0 event/MOVE.

        Keeps the same original S49 L0 and original ActionSupervisor. This is
        not an Action grant, does not affect WorldBody physics, and cannot be
        exercised in default product paths. Existing PROPOSE/ISSUE checks
        still apply to a fresh native threat before any third MOVE.
        """
        if (
            type(token) is not object
            or getattr(self, "_worldbody_retest_extended", False)
            or self.intent_id != "escape-threat"
            or self.max_events != 3 or self.max_action_requests != 2
            or self.events != 3 or self.action_requests != 2
            or len(self._seen_entities) != 3
            or len(self._used_action_ids) != 2
            or self._stage_r_dev_token is not None
            or self._stage_t_dev_token is not None
            or self._stage_r_dev_commit is not None
            or self._stage_t_dev_commit is not None
        ):
            raise NormalActionRejected(
                "WorldBody REST retest needs exactly two original closed L0 moves"
            )
        self.max_events = 4
        self.max_action_requests = 3
        self._worldbody_retest_extended = True

    def bind_stage_r_dev_owner(self, *, token: object) -> None:
        """Explicit opt-in from sole S49 runner; no default learning authority."""
        if (self._stage_r_dev_token is not None
                or self._stage_t_dev_token is not None
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
        s10_owner_state: LearningPreferenceState,
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
            or not isinstance(s10_owner_state, LearningPreferenceState)
            or commit.new_state is not s10_owner_state
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


class NormalEatingObservationStatus(str, Enum):
    """Bounded native-view risk gate, NOT proof that the World is safe."""

    NO_NEARBY_ENTITY_OBSERVED = "NO_NEARBY_ENTITY_OBSERVED"
    OBSERVED_ENTITY_NEARBY = "OBSERVED_ENTITY_NEARBY"
    TRUNCATED_COVERAGE = "TRUNCATED_COVERAGE"
    BODY_NOT_VIABLE = "BODY_NOT_VIABLE"


def assess_normal_eating_observation(
    probe: MineflayerObservation,
) -> NormalEatingObservationStatus:
    """Conservative Bug-0 EAT *precondition*, never a physical Action grant.

    An empty bounded Mineflayer registry is not a global safety certificate.
    The operator/issuer must separately qualify source, threats, resource use,
    permission, physical occupancy and the actual moment of Action ISSUE.
    """
    if (
        not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe"
        or not probe.request_id
        or probe.provenance.source != "mineflayer"
    ):
        raise NormalActionRejected("native current probe required for eating")
    if probe.snapshot.nearby_entities_coverage.truncated:
        return NormalEatingObservationStatus.TRUNCATED_COVERAGE
    if probe.snapshot.health <= 0 or probe.snapshot.oxygen_level == 0:
        return NormalEatingObservationStatus.BODY_NOT_VIABLE
    if probe.snapshot.nearby_entities:
        return NormalEatingObservationStatus.OBSERVED_ENTITY_NEARBY
    return NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED


@dataclass(frozen=True, slots=True)
class NormalFoodDecision:
    """Cheap native-source food decision; neither an S49 Action nor authority."""

    selection: str
    reason: str
    probe_seq: int
    food: float
    choice: EatChoice
    risk: NormalEatingObservationStatus


class NormalFoodL0:
    """S49-scoped food L0 for bounded DEV episodes, not a new Action issuer.

    Reuses S46 EatCursor and S49's limited native risk gate. The same owner
    observes the outcome and may choose WAIT again; it cannot forge a grant,
    issue a physical Action, credit energy, or override the movement/STOP fence.
    """

    def __init__(self, session_id: str, *, max_decisions: int = 20) -> None:
        if type(max_decisions) is not int or not 2 <= max_decisions <= 64:
            raise NormalActionRejected("bounded food L0 decision budget required")
        self.session_id = session_id
        self.cursor = EatCursor(session_id, hunger_threshold=14.0)
        self.max_decisions = max_decisions
        self.decisions = 0
        self._closed_eat = False
        self._last_decision: NormalFoodDecision | None = None

    def decide(self, probe: MineflayerObservation) -> NormalFoodDecision:
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.session_id != self.session_id
            or self.decisions >= self.max_decisions
        ):
            raise NormalActionRejected("food L0 requires bounded own-session native probe")
        risk = assess_normal_eating_observation(probe)
        choice = self.cursor.choose(probe)  # enforces original native sequence
        if choice.status is EatStatus.NOT_HUNGRY:
            selection, reason = "WAIT", "NOT_HUNGRY"
        elif risk is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED:
            selection, reason = "WAIT", "NATIVE_OBSERVATION_RISK"
        elif choice.status is EatStatus.NO_FOOD:
            selection, reason = "WAIT", "NO_INVENTORY_FOOD"
        elif self._closed_eat:
            selection, reason = "WAIT", "ONE_EAT_BUDGET_USED"
        else:
            selection, reason = "EAT", "HUNGRY_WITH_FOOD_AND_BOUNDED_EMPTY_REGISTRY"
        result = NormalFoodDecision(
            selection, reason, probe.seq, choice.food_before, choice, risk,
        )
        self.decisions += 1
        self._last_decision = result
        return result

    def acknowledge_verified_eat(self, receipt: EatingActionReceipt) -> None:
        """Admit only S49-owned, S51-verified terminal; not a nutrition credit."""
        last = self._last_decision
        if (
            self._closed_eat
            or last is None or last.selection != "EAT"
            or not isinstance(receipt, EatingActionReceipt)
            or not isinstance(receipt.terminal, ActionLifecycle)
            or not isinstance(receipt.outcome, EatingOutcome)
            or receipt.terminal.state is not ActionState.OUTCOME
            or receipt.outcome.session_id != self.session_id
            or receipt.terminal.action_id != receipt.outcome.action_id
            or receipt.outcome.food_before != last.food
            or receipt.outcome.food_after <= receipt.outcome.food_before
            or receipt.outcome.after_probe_seq <= last.probe_seq
        ):
            raise NormalActionRejected("food L0 cannot acknowledge unverified EAT")
        self._closed_eat = True


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
class NormalEatingAuthorization:
    """Caller-provided independent EAT-specific grant; not a signed capability.

    It is NOT interchangeable with MOVE-specific NormalActionAuthorization.
    External principal/source qualification remains the S/R caller's duty.
    """

    stage: NormalActionStage
    authority_id: str
    intent_id: str
    session_id: str
    action_id: str
    probe_seq: int
    probe_request_id: str
    food_item: str
    food_slot: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stage, NormalActionStage)
            or not all(isinstance(x, str) and x for x in (
                self.authority_id, self.intent_id, self.session_id,
                self.action_id, self.probe_request_id, self.food_item,
            ))
            or type(self.probe_seq) is not int or self.probe_seq < 0
            or type(self.food_slot) is not int or self.food_slot < 0
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise NormalActionRejected("independent scoped EAT authorization required")


@dataclass(frozen=True, slots=True)
class NormalAttackingAuthorization:
    """Operator-scoped one-time ATTACK fallback, never inferred from L0.

    This typed object is not independent attestation of the operator/principal.
    """

    stage: NormalActionStage
    authority_id: str
    intent_id: str
    session_id: str
    action_id: str
    probe_seq: int
    probe_request_id: str
    target_entity_id: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stage, NormalActionStage)
            or not all(isinstance(x, str) and x for x in (
                self.authority_id, self.intent_id, self.session_id,
                self.action_id, self.probe_request_id,
            ))
            or type(self.probe_seq) is not int or self.probe_seq < 0
            or type(self.target_entity_id) is not int or self.target_entity_id < 0
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise NormalActionRejected("scoped original S49 ATTACK grant required")


@dataclass(frozen=True, slots=True)
class NormalLootMoveAuthorization:
    """DEV-only item-target movement grant for the original S49 supervisor.

    Not substitutable for zombie MOVE_AWAY or EAT/ATTACK grants.
    Does NOT attest who provided the operator authority.
    """

    stage: NormalActionStage
    authority_id: str
    intent_id: str
    session_id: str
    action_id: str
    probe_seq: int
    probe_request_id: str
    item_entity_id: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stage, NormalActionStage)
            or not all(isinstance(x, str) and x for x in (
                self.authority_id, self.intent_id, self.session_id,
                self.action_id, self.probe_request_id,
            ))
            or type(self.probe_seq) is not int or self.probe_seq < 0
            or type(self.item_entity_id) is not int or self.item_entity_id < 0
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise NormalActionRejected("original S49 bounded D6 loot MOVE grant required")


@dataclass(frozen=True, slots=True)
class NormalActionReceipt:
    terminal: ActionLifecycle
    consequence: WorldConsequence
    source: Provenance


@dataclass(frozen=True, slots=True)
class NormalPostMoveEatingReadback:
    """Read-only S15/S16 original evidence; never certifies physical STOP."""

    session_id: str
    action_id: str
    s16_terminal: str
    s15_clear_ack_applied: bool
    clear_ack_seq: int
    after_probe_seq: int
    readback_source: Provenance
    settling_status: str = "WORLD_TICK_IDLE_NOT_ATTESTED"
    physically_stopped_proven: bool = False
    eat_issuance_authorized: bool = False


@dataclass(frozen=True, slots=True)
class NormalIntentEpochRearm:
    """Read-only transition; no physical Action or second issuer granted."""

    session_id: str
    completed_intent_id: str
    next_intent_id: str
    completed_action_count: int
    next_epoch: int
    previous_zombie_entity_id: int
    next_zombie_entity_id: int
    next_native_source: Provenance
    physically_issued: bool = False


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

    def __init__(
        self, session_id: str, intent: IntentCommitment,
        *, max_sequential_attacks: int = 1,
        max_intent_epochs: int = 1,
    ) -> None:
        if (
            not isinstance(session_id, str) or not session_id
            or not isinstance(intent, IntentCommitment)
            or intent.current_intent is None
            or type(max_sequential_attacks) is not int
            or not 1 <= max_sequential_attacks <= 32
            or type(max_intent_epochs) is not int
            or not 1 <= max_intent_epochs <= 4
        ):
            raise NormalActionRejected("active named session and bounded Intent/ATTACK grant required")
        self.session_id = session_id
        self.intent = intent
        self.supervisor = ActionSupervisor()
        self._dispatched: set[str] = set()
        self._count = 0
        self._attack_count = 0
        self._max_sequential_attacks = max_sequential_attacks
        self._max_intent_epochs = max_intent_epochs
        self._intent_epoch = 1
        self._epoch_intent_id = intent.current_intent.intent_id
        self._epoch_action_count_start = 0
        self._epoch_attack_count = 0
        self._last_issued_probe_seq = -1
        # Once a physical MOVE was issued, S49's native S15 clear/S16 closure
        # alone does not qualify post-clear settling. EAT stays fenced until
        # a distinct original-source settling owner is integrated.
        self._post_move_settling_unqualified = False

    def advance_intent_epoch(
        self, next_native: MineflayerObservation,
        *, previous_zombie_entity_id: int,
    ) -> NormalIntentEpochRearm:
        """Explicit DEV rearm after a COMPLETED Intent, not by elapsed time.

        Retains the same session, supervisor, all issued Action IDs, old
        terminal evidence, and monotonic probe counter. A fresh native
        next-generation zombie is necessary but is NOT independent Paper
        confirmation of a death, World tick or learning success.
        """
        events = self.intent.events
        current = self.intent.current_intent
        if (
            self._max_intent_epochs <= 1
            or self._intent_epoch >= self._max_intent_epochs
            or not isinstance(next_native, MineflayerObservation)
            or next_native.kind != "probe"
            or not next_native.request_id
            or next_native.provenance.source != "mineflayer"
            or next_native.session_id != self.session_id
            or next_native.seq <= self._last_issued_probe_seq
            or next_native.snapshot.health <= 0
            or next_native.snapshot.oxygen_level == 0
            or next_native.snapshot.nearby_entities_coverage.truncated
            or type(previous_zombie_entity_id) is not int
            or previous_zombie_entity_id < 0
            or self._post_move_settling_unqualified
            or self.supervisor.open_actions
            or not self._dispatched
            or self._count <= self._epoch_action_count_start
            or any(
                self.supervisor.get(action_id).state is not ActionState.OUTCOME
                for action_id in self._dispatched
            )
            or current is None
            or self.intent.pending_reconsideration is not None
            or current.intent_id == self._epoch_intent_id
            or len(events) < 3
            or events[-1].kind is not IntentEventKind.COMMITTED
            or events[-1].intent_id != current.intent_id
            or events[-2].kind is not IntentEventKind.COMPLETED
            or events[-2].intent_id != self._epoch_intent_id
        ):
            raise NormalActionRejected(
                "new Intent epoch requires completed old owner and fresh native source"
            )
        zombies = [
            entity for entity in next_native.snapshot.nearby_entities
            if entity.name == "zombie"
        ]
        if (
            len(zombies) != 1
            or zombies[0].entity_id == previous_zombie_entity_id
            or next_native.snapshot.nearby_entities_coverage.candidate_count
            != len(next_native.snapshot.nearby_entities)
        ):
            raise NormalActionRejected(
                "one distinct authentic next-generation zombie is required"
            )
        record = NormalIntentEpochRearm(
            session_id=self.session_id,
            completed_intent_id=self._epoch_intent_id,
            next_intent_id=current.intent_id,
            completed_action_count=self._count,
            next_epoch=self._intent_epoch + 1,
            previous_zombie_entity_id=previous_zombie_entity_id,
            next_zombie_entity_id=zombies[0].entity_id,
            next_native_source=next_native.provenance,
        )
        self._intent_epoch += 1
        self._epoch_intent_id = current.intent_id
        self._epoch_action_count_start = self._count
        self._epoch_attack_count = 0
        return record

    def require_d6_loot_move_authorizations(
        self, previous_probe: MineflayerObservation,
        probe: MineflayerObservation, candidate: D6LootApproach,
        propose: NormalLootMoveAuthorization,
        issue: NormalLootMoveAuthorization,
    ) -> None:
        """Recompute source-only item direction before accepting scoped grants."""
        current = self.intent.current_intent
        if (
            current is None
            or current.intent_id != self._epoch_intent_id
            or self.intent.pending_reconsideration is not None
            or not isinstance(candidate, D6LootApproach)
            or not isinstance(propose, NormalLootMoveAuthorization)
            or not isinstance(issue, NormalLootMoveAuthorization)
            or propose.stage is not NormalActionStage.PROPOSE
            or issue.stage is not NormalActionStage.ISSUE
            or not propose.granted or not issue.granted
            or propose.authority_id == issue.authority_id
            or propose.provenance == issue.provenance
            or self.supervisor.open_actions
            or probe.seq <= self._last_issued_probe_seq
            or propose.action_id in self._dispatched
        ):
            raise NormalActionRejected("original D6 loot MOVE issuer/admission blocked")
        if candidate != source_qualified_loot_approach(
            previous_probe, probe, item_entity_id=candidate.item_entity_id,
        ):
            raise NormalActionRejected("item approach candidate is forged or stale")
        for grant in (propose, issue):
            if (
                grant.intent_id != current.intent_id
                or grant.session_id != self.session_id
                or grant.session_id != probe.session_id
                or grant.action_id != propose.action_id
                or grant.probe_seq != probe.seq
                or grant.probe_request_id != probe.request_id
                or grant.item_entity_id != candidate.item_entity_id
            ):
                raise NormalActionRejected("D6 grant not tied to current native item")

    async def execute_d6_loot_move(
        self, session: MineflayerProcessSession,
        previous_probe: MineflayerObservation,
        probe: MineflayerObservation, candidate: D6LootApproach,
        propose: NormalLootMoveAuthorization,
        issue: NormalLootMoveAuthorization,
        *, physical_fence: object,
    ) -> NormalActionReceipt:
        """Opt-in D6 item approach via existing S49/S15/S16; no alternate issuer.

        This is a narrow Action-level DEV admission like the existing
        ATTACK/EAT routes, NOT a claim of full S14 route adjudication.
        The unmodified S15 MOVE_BACKWARD and C1 pre-ISSUE physical fence
        are both required; never permit an unjournaled loot movement.
        """
        from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence

        if (
            not isinstance(session, MineflayerProcessSession)
            or session.started.session_id != self.session_id
            or session.process_returncode is not None
            or not isinstance(physical_fence, OriginalS49PhysicalFence)
        ):
            raise NormalActionRejected("D6 original S49 live native and MOVE fence required")
        self.require_d6_loot_move_authorizations(
            previous_probe, probe, candidate, propose, issue,
        )
        t = 100 + 10 * self._count
        origin = Provenance("normal-action-runtime", f"{self.session_id}:{t}")
        skill = SkillExecution.start(
            f"skill:collect-loot:{self.session_id}:{probe.seq}",
            skill_id="collect-loot", intent_commitment=self.intent,
            at_ns=t, provenance=origin,
        )
        proposed = ActionLifecycle.propose(
            propose.action_id, skill_execution=skill,
            intent_commitment=self.intent, at_ns=t, provenance=origin,
        )
        binding = ExecutionBindingResult(
            binding_id=f"d6-loot-{self.session_id}-{probe.seq}",
            candidate_ref="COLLECT_LOOT",
            intent_id=self.intent.current_intent.intent_id,
            skill_execution_id=skill.execution_id,
            skill_ref=skill.skill_id,
            action_id=propose.action_id,
            action_ref="MOVE_BACKWARD",
            skill_state=SkillState.STARTED,
            action_state=ActionState.PROPOSED,
            provenance=origin,
        )
        authorized = proposed.authorize(
            at_ns=t + 1, provenance=propose.provenance,
            authority=propose.authority_id,
        )
        # The source-bound write-ahead record MUST complete before
        # original supervisor ISSUE and before ANY native control command.
        physical_fence.prepare(
            session_id=self.session_id,
            intent_id=self.intent.current_intent.intent_id,
            action_id=propose.action_id, probe=probe,
        )
        issued = self.supervisor.issue(
            authorized, at_ns=t + 2, deadline_ns=t + 100,
            provenance=issue.provenance,
        )
        self._dispatched.add(issued.action_id)
        self._last_issued_probe_seq = probe.seq
        self._post_move_settling_unqualified = True
        self._count += 1
        try:
            # Any exception after original ISSUE must leave this Action UNKNOWN,
            # including a failed command build before native IO.
            command = build_mineflayer_command(issued, binding)
            consequence = await execute_mineflayer_command(
                session, command, timeout_s=9, provenance=origin,
            )
            interpretation = interpret_world_consequence(
                issued, binding, consequence, provenance=origin,
            )
            if interpretation.disposition is ActionOutcomeDisposition.OUTCOME:
                terminal = record_interpreted_action_outcome(
                    self.supervisor, interpretation, at_ns=t + 3,
                )
            else:
                # No silent movement retry on ambiguous S15/IO.
                terminal = self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            receipt = NormalActionReceipt(terminal, consequence, probe.provenance)
            if (
                terminal.state is not ActionState.OUTCOME
                or consequence.status is not WorldConsequenceStatus.EXECUTED
            ):
                raise NormalActionRejected("D6 movement has no successful physical S16")
            physical_fence.close(
                receipt, probe, original_supervisor=self.supervisor,
            )
            # Movement success != physical pickup, food identity, or STOP.
            return receipt
        except BaseException:
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            raise

    def read_only_post_move_eat_boundary(
        self, receipt: NormalActionReceipt,
    ) -> NormalPostMoveEatingReadback:
        """Inspect the SAME S49 supervisor and native S15 clear ACK, read-only.

        L22 sampled quiet, L23 Paper callback ticks and S50 input-off reports
        do not prove tick-aligned effective STOP. Do not un-fence EAT here.
        """
        if not isinstance(receipt, NormalActionReceipt):
            raise NormalActionRejected("original S49 Action receipt required")
        terminal, consequence = receipt.terminal, receipt.consequence
        clear = consequence.cleanup_receipt
        after = consequence.after_observation
        if (
            terminal.state is not ActionState.OUTCOME
            or consequence.status is not WorldConsequenceStatus.EXECUTED
            or terminal.action_id != consequence.action_id
            or terminal.action_id not in self._dispatched
            or consequence.session_id != self.session_id
            or consequence.action_ref != "MOVE_BACKWARD"
            or clear is None or after is None
            or clear.session_id != self.session_id
            or clear.effect != "clear_controls"
            or clear.result != "applied"
            or clear.provenance.source != "mineflayer"
            or after.session_id != self.session_id
            or after.kind != "probe"
            or after.provenance.source != "mineflayer"
            or not clear.seq < after.seq
            or not self._post_move_settling_unqualified
            or self.supervisor.get(terminal.action_id) is not terminal
        ):
            raise NormalActionRejected("original clear/after source not qualified")
        return NormalPostMoveEatingReadback(
            session_id=self.session_id,
            action_id=terminal.action_id,
            s16_terminal=terminal.state.value,
            s15_clear_ack_applied=True,
            clear_ack_seq=clear.seq,
            after_probe_seq=after.seq,
            readback_source=after.provenance,
        )

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


    def require_eating_authorizations(
        self, choice: EatChoice, probe: MineflayerObservation,
        propose: NormalEatingAuthorization, issue: NormalEatingAuthorization,
        *, previous_probe: MineflayerObservation,
    ) -> None:
        """Only the existing S49 issuer may admit this serial EAT request.

        A matching typed grant is still NOT independent proof of who granted it.
        No safety or freshness beyond the given native source is manufactured.
        """
        current = self.intent.current_intent
        # Two original-native observations bound to the same session are a
        # necessary pre-ISSUE check, not a verified tick clock/STOP ACK.
        # The separate native physical-settling owner must still qualify any
        # transition from earlier motion before a real World EAT grant.
        if (
            not isinstance(previous_probe, MineflayerObservation)
            or previous_probe.kind != "probe"
            or not previous_probe.request_id
            or previous_probe.provenance.source != "mineflayer"
            or previous_probe.session_id != self.session_id
            or not isinstance(probe, MineflayerObservation)
            or probe.session_id != previous_probe.session_id
            or probe.seq <= previous_probe.seq
            or probe.seq - previous_probe.seq > 32
            or probe.request_id == previous_probe.request_id
            or assess_normal_eating_observation(previous_probe)
            is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
            or any(
                abs(getattr(previous_probe.snapshot.position, axis)
                    - getattr(probe.snapshot.position, axis)) > 0.05
                for axis in ("x", "y", "z")
            )
        ):
            raise NormalActionRejected("no recent same-session steady native EAT window")
        if (
            not isinstance(choice, EatChoice)
            or choice.status is not EatStatus.CANDIDATE
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.provenance.source != "mineflayer"
            or probe.session_id != self.session_id
            or choice.session_id != self.session_id
            or choice.probe_seq != probe.seq
            or choice.provenance != probe.provenance
            or choice.food_before != probe.snapshot.food
            or choice.item_name is None or choice.item_slot is None
            or probe.seq <= self._last_issued_probe_seq
            or self._post_move_settling_unqualified
            or assess_normal_eating_observation(probe)
            is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
            or not any(
                item.name == choice.item_name
                and item.slot == choice.item_slot and item.count > 0
                for item in probe.snapshot.inventory
            )
            or current is None or self.intent.pending_reconsideration is not None
            or (
                current is not None
                and current.intent_id != self._epoch_intent_id
                and bool(self._dispatched)
            )
            or not isinstance(propose, NormalEatingAuthorization)
            or not isinstance(issue, NormalEatingAuthorization)
            or propose.stage is not NormalActionStage.PROPOSE
            or issue.stage is not NormalActionStage.ISSUE
            or not propose.granted or not issue.granted
            or propose.authority_id == issue.authority_id
            or propose.provenance == issue.provenance
            or propose.action_id in self._dispatched
            or self.supervisor.open_actions
        ):
            raise NormalActionRejected("S49 EAT source/Intent/Action admission invalid")
        for grant in (propose, issue):
            if (
                grant.intent_id != current.intent_id
                or grant.session_id != self.session_id
                or grant.action_id != propose.action_id
                or grant.probe_seq != probe.seq
                or grant.probe_request_id != probe.request_id
                or grant.food_item != choice.item_name
                or grant.food_slot != choice.item_slot
            ):
                raise NormalActionRejected("S49 EAT grant is not scoped to this source")

    def require_attack_authorizations(
        self, previous_probe: MineflayerObservation,
        probe: MineflayerObservation, target_entity_id: int,
        propose: NormalAttackingAuthorization,
        issue: NormalAttackingAuthorization,
    ) -> None:
        """One fresh original S49 native zombie, one explicit ATTACK fallback."""
        if (
            not isinstance(previous_probe, MineflayerObservation)
            or not isinstance(probe, MineflayerObservation)
            or previous_probe.kind != "probe" or probe.kind != "probe"
            or not previous_probe.request_id or not probe.request_id
            or previous_probe.request_id == probe.request_id
            or previous_probe.session_id != self.session_id
            or probe.session_id != self.session_id
            or previous_probe.provenance.source != "mineflayer"
            or probe.provenance.source != "mineflayer"
            or not previous_probe.seq < probe.seq <= previous_probe.seq + 32
            or type(target_entity_id) is not int or target_entity_id < 0
            or self._count - self._epoch_action_count_start
            != self._epoch_attack_count
            or self._epoch_attack_count >= self._max_sequential_attacks
            or (
                self.intent.current_intent is not None
                and self.intent.current_intent.intent_id != self._epoch_intent_id
                and bool(self._dispatched)
            )
            or propose.action_id in self._dispatched
            or self._post_move_settling_unqualified
            or self._last_issued_probe_seq >= probe.seq
            or self.supervisor.open_actions
            or any(
                self.supervisor.get(action_id).state is not ActionState.OUTCOME
                for action_id in self._dispatched
            )
            or self.intent.current_intent is None
            or self.intent.pending_reconsideration is not None
            or not isinstance(propose, NormalAttackingAuthorization)
            or not isinstance(issue, NormalAttackingAuthorization)
            or propose.stage is not NormalActionStage.PROPOSE
            or issue.stage is not NormalActionStage.ISSUE
            or not propose.granted or not issue.granted
            or propose.authority_id == issue.authority_id
            or propose.provenance == issue.provenance
        ):
            raise NormalActionRejected("original S49 ATTACK source/owner not eligible")
        for observation in (previous_probe, probe):
            snapshot = observation.snapshot
            coverage = snapshot.nearby_entities_coverage
            if (
                coverage.truncated or coverage.candidate_count != 1
                or len(snapshot.nearby_entities) != 1
                or snapshot.health <= 0
            ):
                raise NormalActionRejected("native ATTACK target coverage/health not safe")
            entity = snapshot.nearby_entities[0]
            if (
                entity.name != "zombie"
                or entity.entity_id != target_entity_id
                or entity.distance > 2.8
                or entity.distance < 0.1
            ):
                raise NormalActionRejected("ATTACK target not same near zombie")
        earlier = previous_probe.snapshot.nearby_entities[0]
        current = probe.snapshot.nearby_entities[0]
        if any(
            abs(getattr(earlier.position, k)
                - getattr(current.position, k)) > 0.25
            or abs(getattr(previous_probe.snapshot.position, k)
                - getattr(probe.snapshot.position, k)) > 0.05
            for k in ("x", "y", "z")
        ):
            raise NormalActionRejected("ATTACK target/body moved during admission window")
        for grant in (propose, issue):
            if (
                grant.intent_id != self.intent.current_intent.intent_id
                or grant.session_id != self.session_id
                or grant.action_id != propose.action_id
                or grant.probe_seq != probe.seq
                or grant.probe_request_id != probe.request_id
                or grant.target_entity_id != target_entity_id
            ):
                raise NormalActionRejected("ATTACK fallback authorization source mismatch")

    async def execute_attack(
        self, session: MineflayerProcessSession,
        previous_probe: MineflayerObservation,
        probe: MineflayerObservation, target_entity_id: int,
        propose: NormalAttackingAuthorization,
        issue: NormalAttackingAuthorization,
        *, allow_target_disappearance: bool = False,
        physical_fence: OriginalS49NonMotionFence | None = None,
    ) -> AttackActionReceipt:
        """Issue one operator-approved attack from THIS original S49 supervisor."""
        if (
            not isinstance(session, MineflayerProcessSession)
            or session.started.session_id != self.session_id
            or session.process_returncode is not None
        ):
            raise NormalActionRejected("original S49 native attack session required")
        self.require_attack_authorizations(
            previous_probe, probe, target_entity_id, propose, issue,
        )
        t = 100 + 10 * self._count
        origin = Provenance("normal-action-runtime", f"{self.session_id}:{t}")
        skill = SkillExecution.start(
            f"skill:attack:{self.session_id}:{probe.seq}",
            skill_id="attack", intent_commitment=self.intent,
            at_ns=t, provenance=origin,
        )
        proposed = ActionLifecycle.propose(
            propose.action_id, skill_execution=skill,
            intent_commitment=self.intent, at_ns=t, provenance=origin,
        )
        authorized = proposed.authorize(
            at_ns=t + 1, provenance=propose.provenance,
            authority=propose.authority_id,
        )
        # The fence is a DEV opt-in reservation, never independent authority.
        # It is fsynced after original S49 admission and BEFORE supervisor
        # ISSUE and ANY native ATTACK effect. Failure means no new Action.
        if physical_fence is not None:
            if not isinstance(physical_fence, OriginalS49NonMotionFence):
                raise NormalActionRejected("typed original ATTACK fence required")
            physical_fence.prepare_attack(
                probe=probe, intent_id=self.intent.current_intent.intent_id,
                action_id=propose.action_id, target_entity_id=target_entity_id,
            )
        issued = self.supervisor.issue(
            authorized, at_ns=t + 2, deadline_ns=t + 100,
            provenance=issue.provenance,
        )
        self._dispatched.add(issued.action_id)
        self._last_issued_probe_seq = probe.seq
        self._count += 1
        self._attack_count += 1
        self._epoch_attack_count += 1
        try:
            result = await IssuedAttackingExecutor().execute(
                session, self.supervisor, issued, probe,
                target_entity_id=target_entity_id,
                skill_execution=skill, intent_commitment=self.intent,
                allow_target_disappearance=allow_target_disappearance,
            )
            if physical_fence is not None:
                physical_fence.close_attack(
                    receipt=result, probe=probe, supervisor=self.supervisor,
                    allow_target_disappearance=allow_target_disappearance,
                )
            return result
        except BaseException:
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            raise

    async def execute_eat(
        self, session: MineflayerProcessSession, choice: EatChoice,
        probe: MineflayerObservation,
        propose: NormalEatingAuthorization, issue: NormalEatingAuthorization,
        *, previous_probe: MineflayerObservation,
        physical_fence: OriginalS49NonMotionFence | None = None,
    ) -> EatingActionReceipt:
        """Same original S49 supervisor issues, unchanged S51 performs EAT.

        Bounded owner integration candidate; existing normal-session runtime
        does not call this path. Real-world authorization is not self-granted.
        """
        if (
            not isinstance(session, MineflayerProcessSession)
            or session.started.session_id != self.session_id
            or session.process_returncode is not None
        ):
            raise NormalActionRejected("S49 EAT live Mineflayer session mismatch")
        self.require_eating_authorizations(
            choice, probe, propose, issue, previous_probe=previous_probe,
        )
        t = 100 + 10 * self._count
        origin = Provenance("normal-action-runtime", f"{self.session_id}:{t}")
        skill = SkillExecution.start(
            f"skill:eat:{self.session_id}:{probe.seq}:{self._count}",
            skill_id="eat", intent_commitment=self.intent,
            at_ns=t, provenance=origin,
        )
        proposed = ActionLifecycle.propose(
            propose.action_id, skill_execution=skill,
            intent_commitment=self.intent, at_ns=t, provenance=origin,
        )
        authorized = proposed.authorize(
            at_ns=t + 1, provenance=propose.provenance,
            authority=propose.authority_id,
        )
        if physical_fence is not None:
            if not isinstance(physical_fence, OriginalS49NonMotionFence):
                raise NormalActionRejected("typed original EAT fence required")
            physical_fence.prepare_eat(
                probe=probe, intent_id=self.intent.current_intent.intent_id,
                action_id=propose.action_id, food_item=choice.item_name,
            )
        issued = self.supervisor.issue(
            authorized, at_ns=t + 2, deadline_ns=t + 100,
            provenance=issue.provenance,
        )
        # Irreversible effect may begin next: never reissue this ID or source.
        self._dispatched.add(issued.action_id)
        self._last_issued_probe_seq = probe.seq
        self._count += 1
        try:
            result = await IssuedEatingExecutor().execute(
                session, self.supervisor, issued, choice, probe,
                skill_execution=skill, intent_commitment=self.intent,
            )
            if physical_fence is not None:
                physical_fence.close_eat(
                    receipt=result, choice=choice, probe=probe,
                    supervisor=self.supervisor,
                )
            return result
        except BaseException:
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id, at_ns=t + 3, provenance=origin,
                )
            raise

    async def execute(
        self, session: MineflayerProcessSession, step: L0Step,
        bound: BoundExecutionCandidate, probe: MineflayerObservation,
        propose: NormalActionAuthorization, issue: NormalActionAuthorization,
        *, timeout_s: float = 9,
        pre_issue_reservation: Callable[[], None] | None = None,
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
        # DEV opt-in: reserve the original MOVE before ActionSupervisor
        # ISSUE and before Mineflayer physical IO. Inability to persist
        # the reservation is a hard stop, not a new Action authority.
        if pre_issue_reservation is not None:
            if not callable(pre_issue_reservation):
                raise NormalActionRejected(
                    "physical pre-ISSUE reservation must be callable"
                )
            pre_issue_reservation()
        issued = self.supervisor.issue(
            authorized, at_ns=t + 2, deadline_ns=t + 100,
            provenance=issue.provenance,
        )
        command = build_mineflayer_command(issued, result)
        # Consumed BEFORE any external IO. Incomplete physical work is UNKNOWN.
        self._dispatched.add(command.action_id)
        # A MOVE issuer cannot infer physical quiescence merely from terminal
        # S16 or a couple of stable-looking native position probes.
        self._post_move_settling_unqualified = True
        self._last_issued_probe_seq = max(self._last_issued_probe_seq, probe.seq)
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
