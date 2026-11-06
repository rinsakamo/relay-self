"""DEV owner-side C1/S10 integration for the *existing* original S49 runner.

The only physical Action issuer remains NormalSessionActionExecutor. This
coordinator is called synchronously by its caller before and after that
executor, and retains exact original step/decision/terminal references. It
does NOT call the executor, create grants, schedule a World, or claim an
external Goal success. The S10 authority identifies technical owner custody,
not a human approval for learning.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.bug0_intent_motion_learning import (
    IntentMotionExperience,
    IntentMotionForecast,
    IntentMotionRejected,
    MotionComparison,
    close_motion_intent_experience,
    forecast_from_retained,
    learn_from_motion_experience,
)
from adapters.mineflayer.normal_action import NormalActionReceipt, NormalSessionActionExecutor
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    LearningCommitResult,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0Step
from relay_self.world_conditioned_choice import WorldChoiceKind


@dataclass(frozen=True, slots=True)
class S49C1DevTerminal:
    experience: IntentMotionExperience
    learning: LearningCommitResult | None


class S49C1MotionDevJoin:
    """One original terminal Intent and at most one subsequent original read.

    The exact original IntentCommitment and NormalSessionActionExecutor are
    passed by reference, not reconstructed from serialized reports. State is
    ephemeral DEV owner-local custody; there is no durable dedup journal.
    """

    def __init__(
        self,
        intent: IntentCommitment,
        executor: NormalSessionActionExecutor,
        retained_motion: LearningPreferenceState,
        *,
        self_id: str,
    ) -> None:
        if (
            not isinstance(intent, IntentCommitment)
            or not isinstance(executor, NormalSessionActionExecutor)
            or executor.intent is not intent
            or intent.current_intent is None
            or not isinstance(retained_motion, LearningPreferenceState)
            or retained_motion.target_id != "motion_decimeters"
            or type(self_id) is not str or not self_id or any(c.isspace() for c in self_id)
        ):
            raise IntentMotionRejected("original S49 Intent/executor and S10 owner required")
        self.intent = intent
        self.executor = executor
        self.retained_motion = retained_motion
        self.self_id = self_id
        self.initial_intent_id = intent.current_intent.intent_id
        self.forecast: IntentMotionForecast | None = None
        self._pending: tuple[L0Step, MineflayerObservation] | None = None
        self._decisions: list[MineflayerObservation] = []
        self._receipts: list[NormalActionReceipt] = []
        self._action_ids: set[str] = set()
        self._terminal: S49C1DevTerminal | None = None
        self._next_forecast: IntentMotionForecast | None = None

    @property
    def action_count(self) -> int:
        return len(self._receipts)

    @property
    def terminal(self) -> S49C1DevTerminal | None:
        return self._terminal

    @property
    def next_forecast(self) -> IntentMotionForecast | None:
        return self._next_forecast

    def prepare_original_action(
        self, step: L0Step, decision_probe: MineflayerObservation,
    ) -> IntentMotionForecast:
        """Receive an already made *original* L0 choice BEFORE S15 IO."""
        current = self.intent.current_intent
        if (
            self._terminal is not None or self._next_forecast is not None
            or self._pending is not None
            or current is None or current.intent_id != self.initial_intent_id
            or not isinstance(step, L0Step)
            or not step.asks_for_action or step.grant is None
            or step.choice.selection is not WorldChoiceKind.MOVE_AWAY
            or step.grant.intent_id != current.intent_id
            or step.grant.action_id != step.action_request_id
            or step.action_request_id in self._action_ids
            or not isinstance(decision_probe, MineflayerObservation)
            or decision_probe.kind != "probe" or not decision_probe.request_id
            or decision_probe.session_id != self.executor.session_id
            or step.choice.probe_seq != decision_probe.seq
            or step.choice.request_id != decision_probe.request_id
            or step.choice.provenance != decision_probe.provenance
            or self.executor.supervisor.open_actions
            or len(self._receipts) >= 8
        ):
            raise IntentMotionRejected("original S49 pending decision is not current")
        if self._receipts:
            last_after = self._receipts[-1].consequence.after_observation
            if last_after is None or decision_probe.seq <= last_after.seq:
                raise IntentMotionRejected("replayed or out-of-order original choice")
        elif self.forecast is None:
            self.forecast = forecast_from_retained(
                self.retained_motion, self.retained_motion,
                self_id=self.self_id, intent_id=current.intent_id,
                session_id=self.executor.session_id,
                native_probe_seq=decision_probe.seq,
                expected_revision=self.retained_motion.revision,
                source_provenance=decision_probe.provenance,
            )
        self._pending = (step, decision_probe)
        assert self.forecast is not None
        return self.forecast

    def accept_original_terminal(
        self, step: L0Step, decision_probe: MineflayerObservation,
        receipt: NormalActionReceipt,
    ) -> None:
        """Read the actual original supervisor's terminal, never issue Action."""
        if (
            self._pending is None
            or self._pending[0] is not step or self._pending[1] is not decision_probe
            or not isinstance(receipt, NormalActionReceipt)
            or receipt.terminal.action_id != step.action_request_id
            or receipt.terminal.intent_id != self.initial_intent_id
            or receipt.source != decision_probe.provenance
            or receipt.terminal.action_id in self._action_ids
            or receipt.terminal.state is not ActionState.OUTCOME
            or self.executor.supervisor.open_actions
            or receipt.terminal.action_id not in self.executor._dispatched
        ):
            raise IntentMotionRejected("original S49 closed receipt binding rejected")
        try:
            original = self.executor.supervisor.get(receipt.terminal.action_id)
        except ValueError as exc:
            raise IntentMotionRejected("terminal not held by original S49 supervisor") from exc
        if original is not receipt.terminal:
            raise IntentMotionRejected("a copied/replayed terminal is not original S16")
        self._decisions.append(decision_probe)
        self._receipts.append(receipt)
        self._action_ids.add(receipt.terminal.action_id)
        self._pending = None

    def close_original_intent(self) -> S49C1DevTerminal:
        """Owner explicitly ends an assessed attempt, not an escape-Goal proof."""
        if (
            self._terminal is not None
            or self._pending is not None
            or not self._receipts or self.forecast is None
            or self.intent.current_intent is None
            or self.intent.current_intent.intent_id != self.initial_intent_id
            or self.executor.supervisor.open_actions
        ):
            raise IntentMotionRejected("original Intent not ready for one C1 terminal")
        self.intent.complete(
            self.initial_intent_id,
            reason="S49 physical attempts assessed; external Goal remains unverified",
            at_ns=(self.intent.last_at_ns or 0) + 1,
            provenance=Provenance("s49-c1-dev-owner", "terminal-original-intent"),
        )
        experience = close_motion_intent_experience(
            self.intent, self.forecast, tuple(self._receipts),
            attempt_id="s49-" + self._receipts[0].terminal.action_id,
            decision_probes=tuple(self._decisions),
        )
        learning = None
        if experience.comparison is not MotionComparison.UNKNOWN:
            learning = learn_from_motion_experience(
                experience, self.retained_motion,
                LearningUpdateRule("s49-c1-motion-dev", 1, 1),
                LearningUpdateAuthority(
                    "s49-c1-technical-retained-owner", "motion_decimeters",
                    Provenance("s49-c1-dev-owner", "source-revision-custody"),
                ),
                provenance=Provenance("s49-c1-dev-owner", experience.experience_id),
            )
            if learning.previous_state is not self.retained_motion:
                raise IntentMotionRejected("S10 owner identity changed during commit")
            self.retained_motion = learning.new_state
        self._terminal = S49C1DevTerminal(experience, learning)
        return self._terminal

    def start_next_original_intent(
        self, next_probe: MineflayerObservation, *, next_intent_id: str,
    ) -> IntentMotionForecast:
        """Read the exact committed S10 revision for the next original Intent.

        The fresh native read does not imply a new physical Action or an L0
        choice/benefit. Both Intent transitions happen in the same owner.
        """
        last_after = self._receipts[-1].consequence.after_observation
        if (
            self._terminal is None or self._next_forecast is not None
            or self.intent.current_intent is not None
            or not isinstance(next_probe, MineflayerObservation)
            or next_probe.kind != "probe" or not next_probe.request_id
            or next_probe.session_id != self.executor.session_id
            or next_probe.seq <= last_after.seq
            or type(next_intent_id) is not str or not next_intent_id
            or next_intent_id == self.initial_intent_id
        ):
            raise IntentMotionRejected("next original Intent requires fresh native source")
        forecast = forecast_from_retained(
            self.retained_motion, self.retained_motion,
            self_id=self.self_id, intent_id=next_intent_id,
            session_id=self.executor.session_id, native_probe_seq=next_probe.seq,
            expected_revision=self.retained_motion.revision,
            source_provenance=next_probe.provenance,
        )
        self.intent.commit(
            next_intent_id, objective="reassess motion from new native Present",
            at_ns=(self.intent.last_at_ns or 0) + 1,
            provenance=Provenance("s49-c1-dev-owner", "next-original-intent"),
        )
        self._next_forecast = forecast
        return forecast
