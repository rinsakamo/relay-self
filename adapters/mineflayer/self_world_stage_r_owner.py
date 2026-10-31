"""Stage R opt-in DEV-only terminal-to-next-probe single-writer owner.

S49's ONE original L0 host and ONE original Action executor must invoke this
synchronously. The first qualified physical OUTCOME is classified by existing
S17, then the independently declared S49 DEV learning owner issues a bounded
HOLD S10 authority only after the executor returned terminal success. The
successor is installed only at a later genuine native probe, before next L0
decision. No external actor can use this as a credential for SCIENCE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalActionReceipt,
    NormalRetainedOwnerReadback,
    NormalSessionActionExecutor,
    NormalWorldL0,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_native_feedback import (
    StageNDeclaredPolicy,
    StageNNativeClosureObserver,
)
from adapters.mineflayer.self_world_owner_handoff import StageOOwnerReadback
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    LearningCommitResult,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateProposal,
    LearningUpdateRule,
    commit_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0Step


class StageRDevRejected(ValueError):
    """DEV owner identity, authentic terminal, or later source absent."""


@dataclass(frozen=True, slots=True)
class _PendingTerminal:
    original: NormalActionClosedReadback
    proposal: LearningUpdateProposal
    after_native_seq: int
    sealed: bool = False


class StageRDevOperatorLearningIssuer:
    """Original S49 operator's single-use DEV permission, NOT Action authority.

    This separates S10 grant construction from the S17 interpreter and
    commit owner. Local operator grant is not externally authenticated.
    """

    def __init__(
        self, host: NormalWorldL0,
        executor: NormalSessionActionExecutor,
        intent: IntentCommitment,
    ) -> None:
        if (not isinstance(host, NormalWorldL0)
                or not isinstance(executor, NormalSessionActionExecutor)
                or not isinstance(intent, IntentCommitment)
                or executor.intent is not intent
                or executor.session_id != host.session_id
                or intent.current_intent is None
                or intent.current_intent.intent_id != host.intent_id
                or host.retained.target_id != "risk_weight"
                or host.retained.revision != 1
                or host.retained.value != 4):
            raise StageRDevRejected("S49 DEV operator issuer requires exact owners")
        self._host = host
        self._executor = executor
        self._intent = intent
        self._initial = host.retained
        self._issued = False

    def authorize_once(
        self, *,
        original: NormalActionClosedReadback,
        proposal: LearningUpdateProposal,
        later_probe: MineflayerObservation,
    ) -> LearningUpdateAuthority:
        if (
            self._issued
            or not isinstance(original, NormalActionClosedReadback)
            or not isinstance(proposal, LearningUpdateProposal)
            or not isinstance(later_probe, MineflayerObservation)
            or original.terminal.state is not ActionState.OUTCOME
            or original.original_probe.session_id != self._host.session_id
            or later_probe.session_id != self._host.session_id
            or original.consequence.after_observation is None
            or later_probe.seq <= original.consequence.after_observation.seq
            or proposal.target_id != self._initial.target_id
            or proposal.expected_revision != self._initial.revision
            or proposal.expected_value != self._initial.value
            or self._executor.supervisor.open_actions
            or self._intent.current_intent is None
            or self._intent.current_intent.intent_id != self._host.intent_id
            or proposal.feedback.consequence_ref is None
        ):
            raise StageRDevRejected("S49 DEV issuer rejects unsealed or replayed grant")
        self._issued = True  # single-use even if later S10 fails
        action = original.terminal.action_id
        return LearningUpdateAuthority(
            f"s49-dev-operator-s10-once:{later_probe.session_id}:{action}",
            self._initial.target_id,
            Provenance(
                "s49-dev-learning-owner",
                f"{later_probe.session_id}:{action}:{proposal.feedback.feedback_id}",
            ),
        )


class StageRDevSingleWriter:
    """S49-attached owner, NOT a second action runner or an observer grant.

    This object MUST be constructed by the opted-in original S49 qualify()
    immediately after the original L0 and executor exist, before any event.
    Its bounded S10 issuer is owned by S49, not inferred from a prediction or
    supplied by the Stage N read-only callback.
    """

    def __init__(
        self, host: NormalWorldL0,
        executor: NormalSessionActionExecutor,
        intent: IntentCommitment,
        issuer: StageRDevOperatorLearningIssuer,
    ) -> None:
        if (
            not isinstance(issuer, StageRDevOperatorLearningIssuer)
            or issuer._host is not host
            or issuer._executor is not executor
            or issuer._intent is not intent
            or not isinstance(host, NormalWorldL0)
            or not isinstance(executor, NormalSessionActionExecutor)
            or not isinstance(intent, IntentCommitment)
            or executor.intent is not intent
            or executor.session_id != host.session_id
            or host.intent_id != "escape-threat"
            or intent.current_intent is None
            or intent.current_intent.intent_id != host.intent_id
            or host.events != 0 or host.action_requests != 0
            or host.retained.target_id != "risk_weight"
            or host.retained.revision != 1
            or host.retained.value != 4
            or executor.supervisor.open_actions
        ):
            raise StageRDevRejected("original S49 L0/executor/Intent owner required")
        self._token = object()
        host.bind_stage_r_dev_owner(token=self._token)
        self._host = host
        self._executor = executor
        self._intent = intent
        self._issuer = issuer
        self._initial: LearningPreferenceState = host.retained
        self._current: LearningPreferenceState = host.retained
        self._stage_n = StageNNativeClosureObserver(StageNDeclaredPolicy())
        self._stage_o = StageOOwnerReadback()
        self._stage_o.receive_original_owner(NormalRetainedOwnerReadback(
            host.session_id, host.intent_id, host.retained,
        ))
        self._pending: _PendingTerminal | None = None
        self._committed: LearningCommitResult | None = None
        self._last_native_seq = -1
        self._operator_grants = 0
        self._commit_source: dict[str, Any] | None = None
        self._closed_action_ids: set[str] = set()

    @property
    def current(self) -> LearningPreferenceState:
        return self._current

    @property
    def committed(self) -> LearningCommitResult | None:
        return self._committed

    def observe_original_probe(self, probe: MineflayerObservation) -> None:
        """Inside original S49.reprobe, BEFORE original L0._check."""
        self._stage_n.observe_existing_probe(probe)
        self._stage_o.observe_existing_probe(probe)
        if (
            probe.session_id != self._host.session_id
            or probe.seq <= self._last_native_seq
            or self._host.retained is not self._current
        ):
            raise StageRDevRejected("stale/foreign native source or split owner")
        self._last_native_seq = probe.seq
        if self._pending is None or self._committed is not None:
            return
        pending = self._pending
        original = pending.original
        if (
            not pending.sealed
            or probe.seq <= pending.after_native_seq
            or not isinstance(probe.request_id, str)
            or not probe.request_id.startswith(
                f"s49-actual:{probe.session_id}:event-"
            )
            or not probe.request_id.rsplit("event-", 1)[-1].isdecimal()
            or int(probe.request_id.rsplit("event-", 1)[-1])
            <= pending.after_native_seq
            or int(probe.request_id.rsplit("event-", 1)[-1]) >= probe.seq
            or self._host.retained is not self._initial
            or self._current is not self._initial
            or self._executor.supervisor.open_actions
            or self._intent.current_intent is None
            or self._intent.current_intent.intent_id != self._host.intent_id
        ):
            raise StageRDevRejected("first terminal has no safe later epoch boundary")

        # S49 operator's *separate*, predeclared learning permission, scoped
        # to the exact already-sealed original Action. This is not a grant
        # from S17 itself, and does not provide cross-run authentication.
        action = original.terminal.action_id
        authority = self._issuer.authorize_once(
            original=original, proposal=pending.proposal, later_probe=probe,
        )
        result = commit_learning_update(
            self._current, pending.proposal, authority,
            provenance=Provenance(
                "s49-dev-single-writer-commit",
                f"{probe.session_id}:{action}:{probe.seq}",
            ),
        )
        if (
            result.previous_state is not self._current
            or result.new_state.value != self._current.value
            or result.new_state.revision != self._current.revision + 1
            or result.record.authority_id != authority.authority_id
        ):
            raise StageRDevRejected("S10 did not produce bounded exact HOLD")
        # Critical: no await, no second L0 or World issuer; a synchronous
        # single-writer publication to original L0 and S14's same getter.
        self._host.install_stage_r_dev_successor(
            token=self._token, commit=result,
        )
        self._current = result.new_state
        self._committed = result
        self._commit_source = {
            "terminal_action_id": action,
            "terminal_after_native_seq": pending.after_native_seq,
            "next_source_probe_seq": probe.seq,
            "next_source_request_id": probe.request_id,
            "feedback_id": pending.proposal.feedback.feedback_id,
            "s10_authority_id": authority.authority_id,
            "s10_authority_source": authority.provenance.source,
            "s10_commit_revision": result.new_state.revision,
        }
        self._operator_grants += 1
        self._pending = None

    def observe_original_closed(self, closed: NormalActionClosedReadback) -> None:
        """Called synchronously by the original executor terminal callback."""
        if not isinstance(closed, NormalActionClosedReadback):
            raise StageRDevRejected("original typed S16 terminal readback required")
        if closed.original_probe.session_id != self._host.session_id:
            raise StageRDevRejected("foreign terminal session")
        if closed.terminal.action_id in self._closed_action_ids:
            raise StageRDevRejected("duplicate S49 terminal")
        typed = self._stage_n.observe_closed(closed)
        self._closed_action_ids.add(closed.terminal.action_id)
        if self._committed is not None:
            return  # exactly ONE S10 update for this DEV session
        if self._pending is not None:
            raise StageRDevRejected("concurrent terminal learning candidates")
        proposal = self._stage_o.prepare_original_hold(
            typed, LearningUpdateRule("stage-r-dev-predeclared-hold", 1, 1),
        )
        if (
            closed.consequence.after_observation is None
            or closed.terminal.state is not ActionState.OUTCOME
            or closed.consequence.after_observation.seq <= closed.original_probe.seq
            or proposal.proposed_value != self._initial.value
        ):
            raise StageRDevRejected("no terminal OUTCOME with bounded HOLD")
        self._pending = _PendingTerminal(
            closed, proposal, closed.consequence.after_observation.seq,
        )

    def seal_original_action(
        self, step: L0Step, receipt: NormalActionReceipt,
    ) -> None:
        """Only original S49 on_action calls this AFTER executor.execute."""
        if (not isinstance(step, L0Step)
                or not isinstance(receipt, NormalActionReceipt)
                or receipt.terminal.state is not ActionState.OUTCOME
                or step.action_request_id != receipt.terminal.action_id
                or self._executor.supervisor.open_actions):
            raise StageRDevRejected("original S49 Action outcome not fully closed")
        if self._committed is not None:
            if receipt.terminal.action_id not in self._closed_action_ids:
                raise StageRDevRejected("later Action lacked typed closure")
            return
        pending = self._pending
        if (
            pending is None or pending.sealed
            or receipt.terminal is not pending.original.terminal
            or receipt.consequence is not pending.original.consequence
            or pending.original.original_probe.seq != step.choice.probe_seq
            or receipt.terminal.action_id != pending.original.terminal.action_id
            or step.choice.retained_revision != self._current.revision
        ):
            raise StageRDevRejected("same original terminal/owner seal absent")
        self._pending = _PendingTerminal(
            pending.original, pending.proposal, pending.after_native_seq,
            sealed=True,
        )

    def require_joint_admission_owner(self, step: L0Step) -> LearningPreferenceState:
        """Original S49 on_action's S14 must use THIS exact current owner."""
        if (
            not isinstance(step, L0Step)
            or self._host.retained is not self._current
            or step.choice.retained_target_id != self._current.target_id
            or step.choice.retained_revision != self._current.revision
            or step.choice.retained_value != self._current.value
            or self._executor.supervisor.open_actions
        ):
            raise StageRDevRejected("L0 and S14 owner differ or action in progress")
        return self._current

    def summary(self) -> dict[str, Any]:
        return {
            "kind": "stage_r_dev_single_writer",
            "classification": "DEV_ONLY_NOT_SCIENCE",
            "original_session_id": self._host.session_id,
            "initial_revision": self._initial.revision,
            "current_revision": self._current.revision,
            "current_value": self._current.value,
            "joint_l0_s14_owner_identity": self._host.retained is self._current,
            "operator_s10_grants": self._operator_grants,
            "commit_source": dict(self._commit_source) if self._commit_source else None,
            "s10_hold_commits": int(self._committed is not None),
            "original_action_closures": len(self._closed_action_ids),
            "pending_unsealed_or_unknown": self._pending is not None,
            "grant_independent_external_attestation": False,
            "hold_reward_or_policy_gain": False,
            "additional_action_issuer": False,
        }
