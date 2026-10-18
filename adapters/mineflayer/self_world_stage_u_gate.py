"""Stage U: exact original S49 executor-owner terminal → local S10 grant gate.

DEV/OFFLINE rehearsal only. The grant issuer is independent of the S17
interpreter *within this process*, NOT externally authenticated. The same
original NormalSessionActionExecutor remains the only physical Action issuer.
Near-threat WAIT is never independently certified safe by S14 admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalActionReceipt,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_stage_s_feedback import (
    StageSFeedbackRejected,
    StageSPredeclaredSeparationRule,
    StageSSeparationAssessment,
    StageSSeparationClass,
    assess_stage_s_original_separation,
)
from adapters.mineflayer.self_world_stage_t_policy import (
    StageTDevJointPreview,
    preview_stage_t_joint_original_owner,
)
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0Step
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    verify_stage_t_dev_directional_commit,
)


class StageUDevRejected(ValueError):
    """The original executor owner or source evidence cannot authorize S10."""


class StageUWaitBoundary(str, Enum):
    """S14 plan admissibility is NOT an independently observed safety claim."""

    NEAR_WAIT_READ_ONLY_NO_ACTION = "near_wait_read_only_no_action"
    MOVE_NEEDS_SEPARATE_ACTION_GRANTS = "move_needs_separate_action_grants"


@dataclass(frozen=True, slots=True)
class StageULocalQualification:
    """Explicit DEV scope: no independent external issuer or World evidence."""

    commit: LearningCommitResult
    assessment: StageSSeparationAssessment
    next_source: MineflayerObservation
    preview: StageTDevJointPreview
    wait_boundary: StageUWaitBoundary
    exact_supervised_terminal: bool
    exact_s10_owner: bool
    action_executor_same_owner: bool
    local_issuer_separate_from_s17: bool
    external_issuer_attested: bool = False
    near_wait_safety_attested: bool = False
    physical_wait_permitted: bool = False
    action_issued: bool = False
    minecraft_session_started: bool = False
    on_off_sham_causal_gain_attested: bool = False


class StageUDevOriginalExecutorIssuer:
    """Operator-held one-use grant sealed against original supervisor state.

    Construction requires the real S49 host/executor/Intent object identities.
    It is NOT created by S17 or a prediction label. There is no physical
    runner wiring for this class, and tests prime synthetic executor state.
    """

    def __init__(
        self, host: NormalWorldL0,
        executor: NormalSessionActionExecutor,
        intent: IntentCommitment,
        *,
        preview_token: object,
    ) -> None:
        if (
            not isinstance(host, NormalWorldL0)
            or not isinstance(executor, NormalSessionActionExecutor)
            or not isinstance(intent, IntentCommitment)
            or executor.intent is not intent
            or executor.session_id != host.session_id
            or intent.current_intent is None
            or intent.current_intent.intent_id != host.intent_id
            or type(preview_token) is not object
            or host._stage_t_dev_token is not preview_token
            or host._stage_r_dev_token is not None
            or host._stage_t_dev_commit is not None
            or host.retained.target_id != "risk_weight"
            or host.retained.revision != 1
            or host.retained.value != 4
        ):
            raise StageUDevRejected("Stage U requires pre-bound original DEV owners")
        self._host = host
        self._executor = executor
        self._intent = intent
        self._token = preview_token
        self._original = host.retained
        self._consumed = False

    def commit_once(
        self, *,
        step: L0Step,
        original_closed: NormalActionClosedReadback,
        original_receipt: NormalActionReceipt,
        next_native_probe: MineflayerObservation,
        next_native_event: MineflayerObservation,
    ) -> StageULocalQualification:
        """Exact real-owner shaped, synthetic-only DEV grant and nonexecuting preview.

        Every predicate is checked before S10. Consume on entry to commit:
        unknown outcomes and interrupted grants are NEVER replayed.
        """
        if self._consumed:
            raise StageUDevRejected("original S49 learning grant already consumed")
        if (
            not isinstance(step, L0Step)
            or not isinstance(original_closed, NormalActionClosedReadback)
            or not isinstance(original_receipt, NormalActionReceipt)
            or not isinstance(next_native_probe, MineflayerObservation)
            or not isinstance(next_native_event, MineflayerObservation)
            or not step.asks_for_action
            or step.choice.selection is not WorldChoiceKind.MOVE_AWAY
            or step.grant is None
            or not step.grant.granted
            or step.action_request_id not in self._host._used_action_ids
            or step.event_seq != int(step.action_request_id.removeprefix("s49-native-move-"))
            or original_closed.terminal is not original_receipt.terminal
            or original_closed.consequence is not original_receipt.consequence
            or original_closed.terminal.action_id != step.action_request_id
            or original_closed.terminal.intent_id != self._host.intent_id
            or original_closed.terminal.state is not ActionState.OUTCOME
            or not original_closed.terminal.is_current_snapshot
            or original_closed.original_probe.session_id != self._host.session_id
            or original_closed.original_probe.seq != step.choice.probe_seq
            or original_closed.original_probe.request_id != step.choice.request_id
            or original_closed.original_probe.provenance != original_receipt.source
            or self._host.retained is not self._original
            or self._host._stage_t_dev_commit is not None
            or self._executor.supervisor.open_actions
            or step.action_request_id not in self._executor._dispatched
            or self._intent.current_intent is None
            or self._intent.current_intent.intent_id != self._host.intent_id
        ):
            raise StageUDevRejected("genuine original terminal and owner identities absent")
        try:
            supervised = self._executor.supervisor.get(step.action_request_id)
        except ValueError as exc:
            raise StageUDevRejected("original Action not in supervisor") from exc
        if supervised is not original_receipt.terminal:
            raise StageUDevRejected("copy of terminal does not belong to executor")

        world = original_receipt.consequence
        after = world.after_observation
        sid = self._host.session_id
        if (
            after is None
            or next_native_probe.session_id != sid
            or next_native_event.session_id != sid
            or next_native_event.kind != "entities"
            or next_native_event.request_id is not None
            or next_native_probe.kind != "probe"
            or next_native_probe.provenance.source != "mineflayer"
            or next_native_event.provenance.source != "mineflayer"
            or not (after.seq < next_native_event.seq < next_native_probe.seq)
            or next_native_probe.request_id
            != f"s49-actual:{sid}:event-{next_native_event.seq}"
            or next_native_event.seq <= step.choice.probe_seq
            or next_native_probe.snapshot.nearby_entities_coverage.truncated
            or next_native_event.snapshot.nearby_entities_coverage.truncated
        ):
            raise StageUDevRejected("original later native source cannot be correlated")
        try:
            assessment = assess_stage_s_original_separation(
                original_closed, StageSPredeclaredSeparationRule(),
            )
        except StageSFeedbackRejected as exc:
            raise StageUDevRejected("Stage S typed source cannot be qualified") from exc
        typed = assessment.typed_s17
        if (
            assessment.status not in (
                StageSSeparationClass.SEPARATION_INCREASED,
                StageSSeparationClass.SEPARATION_DECREASED,
            )
            or typed is None
            or typed.feedback is None
            or typed.action_id != step.action_request_id
            or typed.feedback.direction not in (
                FeedbackDirection.INCREASE, FeedbackDirection.DECREASE,
            )
            or self._host.events < 1
            or self._host.action_requests < 1
            or self._executor.supervisor.open_actions
        ):
            raise StageUDevRejected("only resolved directional S17 is eligible")

        proposal = propose_learning_update(
            self._original, typed.feedback,
            LearningUpdateRule("stage-t-dev-risk-weight-one-step", 1, 1),
        )
        # Sole S49 DEV operator grant, NOT S17 interpreter authority.
        self._consumed = True
        authority = LearningUpdateAuthority(
            f"stage-u-local-one-use:{sid}:{step.action_request_id}",
            self._original.target_id,
            Provenance(
                "stage-u-original-executor-local-issuer",
                f"{sid}:{step.action_request_id}:{typed.feedback.feedback_id}",
            ),
        )
        result = commit_learning_update(
            self._original, proposal, authority,
            provenance=Provenance(
                "stage-u-dev-s10-owner",
                f"{sid}:{step.action_request_id}:{next_native_probe.seq}",
            ),
        )
        verify_stage_t_dev_directional_commit(
            result, self._original, typed,
        )
        self._host.install_stage_t_dev_preview(
            token=self._token, commit=result,
            s10_owner_state=result.new_state, typed_s17=typed,
        )
        preview = preview_stage_t_joint_original_owner(
            host=self._host, event=next_native_event,
            probe=next_native_probe, intent=self._intent,
        )
        boundary = (
            StageUWaitBoundary.NEAR_WAIT_READ_ONLY_NO_ACTION
            if preview.new_l0_candidate == "WAIT"
            else StageUWaitBoundary.MOVE_NEEDS_SEPARATE_ACTION_GRANTS
        )
        if (
            preview.committed_revision != 2
            or preview.retained_value != result.new_state.value
            or not preview.l0_and_s14_same_owner_identity
            or preview.s14_admission != "admitted"
            or preview.new_l0_candidate != preview.new_s14_candidate
            or self._host.retained is not result.new_state
            or self._executor.supervisor.open_actions
        ):
            raise StageUDevRejected("native L0/S14 same-owner preview not qualified")
        return StageULocalQualification(
            commit=result, assessment=assessment,
            next_source=next_native_probe, preview=preview,
            wait_boundary=boundary, exact_supervised_terminal=True,
            exact_s10_owner=True, action_executor_same_owner=True,
            local_issuer_separate_from_s17=True,
        )
