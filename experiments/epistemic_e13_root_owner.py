"""Caller-owned root -> S23 -> E12/E11 composition; no physical launcher.

World transports, independent goal evidence and authorities are explicit
inputs. Injected test transports never authenticate a physical World.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from adapters.mineflayer.python_protocol import MineflayerAdapterStarted
from experiments.epistemic_e11_sequential_action_world import EpisodeReceipt, run_episode
from experiments.epistemic_e12_native_owner import Action3TerminalReceipt, run_issued_parent_action3
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.epoch_continuation import read_retained_preference
from relay_self.execution_admission import AdmissionDecision, ExecutionAdmissionCriterion
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    LearningCommitResult,
    LearningPreferenceState,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.planning import PlanSelection
from relay_self.prediction import PredictionState
from relay_self.provenance import Provenance
from relay_self.recovery_action import RecoveryActionHandoff, propose_explicit_recovery_action
from relay_self.route_adjudication import ControlCandidate, RouteDecision
from relay_self.second_epoch_action import validate_second_epoch_lineage
from relay_self.skill import SkillExecution, SkillState
from relay_self.skill_exit_routing import assess_skill_exit, start_explicit_local_recovery
from relay_self.skill_terminal_closure import assess_skill_terminal, commit_skill_terminal


class E13OwnerRejected(ValueError):
    """Stop before the next owner transition; never repair or retry."""


class _NativeSession:
    """Validate every injected native frame, including discarded S15 frames."""

    def __init__(self, source):
        self.source = source
        self.started = source.started
        self.next_seq = self.started.seq + 1

    async def receive(self):
        frame = await self.source.receive()
        if frame.session_id != self.started.session_id or frame.seq != self.next_seq:
            raise E13OwnerRejected("native session/contiguous cursor mismatch")
        self.next_seq += 1
        return frame

    async def send_observe(self, request_id=None):
        return await self.source.send_observe(request_id)

    async def send_set_control(self, action_id, **kwargs):
        return await self.source.send_set_control(action_id, **kwargs)

    async def send_clear_controls(self, action_id):
        return await self.source.send_clear_controls(action_id)


@dataclass(frozen=True)
class AdmissionInputs:
    admission: AdmissionDecision
    control: ControlCandidate
    route: RouteDecision
    criterion: ExecutionAdmissionCriterion
    binding: ExecutionBinding
    prediction: PredictionState | None = None
    plan: PlanSelection | None = None
    retained: LearningPreferenceState | None = None


@dataclass(frozen=True)
class RootReceipt:
    supervisor: ActionSupervisor
    first_skill: SkillExecution
    intent: IntentCommitment
    first: Action3TerminalReceipt
    feedback: LearningFeedbackInterpretation
    commit: LearningCommitResult
    second: Action3TerminalReceipt
    failed_skill: SkillExecution
    recovery_skill: SkillExecution
    handoff: RecoveryActionHandoff
    third: Action3TerminalReceipt
    episode: EpisodeReceipt
    physically_authenticated: bool = False


def p(ref):
    return Provenance(source="e13-root-owner", reference=ref)


def _propose(inputs, intent, at_ns):
    bound = resolve_execution_binding(
        inputs.admission, inputs.control, inputs.route, intent,
        inputs.criterion, inputs.binding, provenance=p("binding-resolution"),
    )
    return start_and_propose_bound_execution(bound, intent, at_ns=at_ns, provenance=p("proposal"))


def _issue(supervisor, proposed, authorize, clock, deadline):
    authorized = authorize(proposed)
    if (not isinstance(authorized, ActionLifecycle)
            or authorized._lineage is not proposed._lineage
            or authorized.events[:-1] != proposed.events
            or authorized.action_id != proposed.action_id
            or authorized.intent_id != proposed.intent_id
            or authorized.skill_execution_id != proposed.skill_execution_id
            or authorized.state is not ActionState.AUTHORIZED
            or not authorized.is_current_snapshot):
        raise E13OwnerRejected("exact independently authorized current Action required")
    return supervisor.issue(authorized, at_ns=clock(), deadline_ns=deadline,
                            provenance=p(f"issue:{proposed.action_id}"))


async def run_root_to_episode(
    *, intent, initial, first_inputs: AdmissionInputs, second_inputs: Callable,
    recovery_inputs: Callable, sessions: tuple, authorize: Callable,
    learning_criterion, learning_rule, learning_authority,
    goal_inputs: Callable, exit_inputs: Callable, clock: Callable,
    deadlines: tuple[int, int, int], episode_inputs: Callable, used_root_sessions: set[str],
):
    """Exactly one sequence using native S15/S16, S19-S23, E12 and E11 APIs.

    `second_inputs` receives the exact newly committed retained object.
    Goal/exit callbacks return separately scoped criterion/evidence/authority;
    no FAILED Skill or local recovery authority is inferred from an OUTCOME.
    `episode_inputs` supplies independent S29 probes/S24/Action4 permissions.
    No session is created here and no externally fabricated OUTCOME is accepted.
    """
    if (initial.target_id != "risk_weight" or initial.revision != 0
            or initial.value != 3 or initial.last_update is not None):
        raise E13OwnerRejected("initial uncommitted risk_weight rev0/value3 required")
    if (len(sessions) != 3
            or any(not isinstance(s.started, MineflayerAdapterStarted) or s.started.seq != 0
                   or s.started.config != sessions[0].started.config for s in sessions)
            or len({s.started.session_id for s in sessions}) != 3):
        raise E13OwnerRejected("three distinct explicitly owned native sessions required")
    identities = {s.started.session_id for s in sessions}
    if not isinstance(used_root_sessions, set) or identities.intersection(used_root_sessions):
        raise E13OwnerRejected("root session already consumed")
    used_root_sessions.update(identities)
    sessions = tuple(_NativeSession(s) for s in sessions)
    supervisor = ActionSupervisor()
    skill1, proposed1, binding1 = _propose(first_inputs, intent, clock())
    issued1 = _issue(supervisor, proposed1, authorize, clock, deadlines[0])
    first = await run_issued_parent_action3(
        sessions[0], supervisor, issued1, binding1, at_ns=clock,
        provenance=issued1.events[-1].provenance,
    )
    if not first.parent_qualified:
        raise E13OwnerRejected("Action1 native World OUTCOME unavailable")
    feedback = interpret_action_outcome_as_learning_feedback(
        first.action, first.interpretation, learning_criterion, provenance=p("feedback"),
    )
    proposal = propose_learning_update(initial, feedback.feedback, learning_rule)
    commit = commit_learning_update(initial, proposal, learning_authority,
                                    provenance=p("governed-retained-commit"))
    if commit.new_state.revision != 1 or commit.new_state.value != 4:
        raise E13OwnerRejected("required governed rev1/value4 update missing")
    second_data = second_inputs(commit.new_state)
    read_retained_preference(
        commit.new_state, second_data.retained, required_target_id="risk_weight",
        expected_revision=1, provenance=p("second-retained-read"),
    )
    validate_second_epoch_lineage(
        supervisor, first.action, feedback, commit.new_state,
        second_data.prediction, second_data.plan, second_data.binding,
        provenance=p("second-lineage"),
    )
    skill2, proposed2, binding2 = _propose(second_data, intent, clock())
    issued2 = _issue(supervisor, proposed2, authorize, clock, deadlines[1])
    second = await run_issued_parent_action3(
        sessions[1], supervisor, issued2, binding2, at_ns=clock,
        provenance=issued2.events[-1].provenance,
    )
    if not second.parent_qualified:
        raise E13OwnerRejected("Action2 native World OUTCOME unavailable")
    criterion, evidence, authority = goal_inputs(skill2, second)
    assessment = assess_skill_terminal(skill2, supervisor, second.action,
                                      second.interpretation, criterion, evidence)
    failed = commit_skill_terminal(assessment, authority, at_ns=clock(),
                                   provenance=p("independent-skill-terminal"))
    if failed.state is not SkillState.FAILED:
        raise E13OwnerRejected("current independently evaluated FAILED Skill2 required")
    criterion, evidence, authority = exit_inputs(failed)
    assessment = assess_skill_exit(failed, intent, criterion, evidence)
    third_data = recovery_inputs(commit.new_state)
    read_retained_preference(
        commit.new_state, third_data.retained, required_target_id="risk_weight",
        expected_revision=1, provenance=p("recovery-retained-read"),
    )
    recovery = start_explicit_local_recovery(
        assessment, authority, execution_id=third_data.binding.skill_execution_id,
        at_ns=clock(), provenance=p("authorized-local-recovery"),
    )
    proposed3, binding3, handoff = propose_explicit_recovery_action(
        assessment=assessment, route_authority=authority, recovery_skill=recovery,
        previous_action=second.action, supervisor=supervisor,
        previous_admission=second_data.admission, new_admission=third_data.admission,
        control=third_data.control, route=third_data.route, criterion=third_data.criterion,
        binding=third_data.binding, at_ns=clock(), provenance=p("S23-proposal"),
    )
    issued3 = _issue(supervisor, proposed3, authorize, clock, deadlines[2])
    third = await run_issued_parent_action3(
        sessions[2], supervisor, issued3, binding3, at_ns=clock,
        provenance=issued3.events[-1].provenance,
    )
    if not third.parent_qualified:
        raise E13OwnerRejected("Action3 native World OUTCOME unavailable")
    args = episode_inputs(third, recovery, commit.new_state)
    reserved = {"adapter", "supervisor", "action", "consequence", "recovery_skill",
                "intent", "retained"}
    if reserved.intersection(args):
        raise E13OwnerRejected("caller cannot substitute root-owned E11 ancestry")
    episode = await run_episode(
        **args, adapter=sessions[2], supervisor=supervisor, action=third.action,
        consequence=third.consequence, recovery_skill=recovery,
        intent=intent, retained=commit.new_state,
    )
    return RootReceipt(supervisor, skill1, intent, first, feedback, commit, second, failed,
                       recovery, handoff, third, episode)
