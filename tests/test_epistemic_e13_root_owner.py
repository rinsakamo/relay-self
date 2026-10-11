"""Synthetic transport only; no prebuilt Action OUTCOME or retained update."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from itertools import count

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerEntityFact,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.epistemic_e13_root_owner import AdmissionInputs, p, run_root_to_episode
from relay_self.action import ActionState
from relay_self.action_feedback import ActionFeedbackCriterion
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.correlated_probe import CorrelatedProbeGrant
from relay_self.execution_admission import (
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import ExecutionBinding
from relay_self.explicit_probe import ExclusiveProbeCursor, ExplicitProbeAuthority
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
)
from relay_self.planning import (
    PlanningCriterion,
    PlanningDirection,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.route_adjudication import (
    RouteCriterion,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillState
from relay_self.skill_exit_routing import (
    IntentImpact,
    LocalPathStatus,
    SkillExitAuthority,
    SkillExitCriterion,
    SkillExitEvidence,
    SkillExitRoute,
)
from relay_self.skill_terminal_closure import (
    SkillGoalEvidence,
    SkillGoalStatus,
    SkillTerminalAuthority,
    SkillTerminalCriterion,
)


class SyntheticWorld:
    def __init__(self, session, fault=None):
        self.started = MineflayerAdapterStarted(session, 0, '4.39.0', MineflayerLaunchConfig())
        self.seq = 1
        self.frames = deque()
        self.commands = []
        self.fault = fault
        self.observations = 0

    def queue(self, frame):
        if self.fault == 'session':
            frame = replace(frame, session_id='alien')
        if self.fault == 'seq':
            frame = replace(frame, seq=999)
        self.frames.append(frame)
        self.seq += 1

    async def send_observe(self, request_id=None):
        self.observations += 1
        z = 0 if self.observations == 1 else .2
        distance = 1.8 if request_id == 'probe:first' else .2
        snapshot = MineflayerSnapshot(
            20, 20, 5, 20, MineflayerPosition(0, 64, z), None, (),
            (MineflayerEntityFact(42, 'zombie', 'mob', distance,
                                 MineflayerPosition(distance, 64, z)),),
            MineflayerNearbyEntitiesCoverage('mineflayer_entity_registry', 16, 16, 1, False),
        )
        self.queue(MineflayerObservation(self.started.session_id, self.seq,
                                        'probe', snapshot, request_id=request_id))

    async def receive(self):
        return self.frames.popleft()

    async def send_set_control(self, action_id, **kwargs):
        self.commands.append(action_id)
        if self.fault == 'missing':
            return
        self.queue(MineflayerEffectResult(self.started.session_id, self.seq,
                   'forged' if self.fault == 'action' else action_id,
                   'set_control', 'applied', None))

    async def send_clear_controls(self, action_id):
        self.queue(MineflayerEffectResult(self.started.session_id, self.seq,
                                         action_id, 'clear_controls', 'applied', None))


def admission(intent, n, retained=None):
    refs, sources = (), ()
    if retained:
        r = retained.last_update
        refs = (f'learning-target:{retained.target_id}', f'learning-revision:{retained.revision}',
                f'learning-feedback:{r.feedback_id}', f'learning-rule:{r.rule_id}:v{r.rule_version}',
                f'learning-authority:{r.authority_id}',
                f'learning-commit-revision:{r.committed_revision}')
        sources = (r.feedback_provenance, r.authority_provenance, r.update_provenance)
    state = PredictionState('prediction', (StateVariable('risk', retained.value if retained else 3),),
                            p('prediction'), source_refs=refs, source_provenance=sources)
    prediction = predict_transition(state, TransitionRule(
        'move', (StateVariable('risk', retained.value if retained else 3),),
        (StateVariable('score', 7),), p('move-rule')))
    plan = select_plan((plan_candidate_from_prediction(
        prediction, candidate_id='MOVE_AWAY', feature_keys=('score',), provenance=p('plan')),),
        PlanningCriterion('score', 'score', PlanningDirection.MINIMIZE))
    route = adjudicate_routes(plan, None, RouteCriterion(f'route{n}', allow_single_source=True),
                              provenance=p('route'))
    control = control_candidate_from_route_decision(route)
    criterion = ExecutionAdmissionCriterion(f'admission{n}', AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
                                             'escape', ('MOVE_AWAY',))
    admitted = admit_control_candidate(control, route, intent, criterion, provenance=p(f'admission{n}'))
    binding = ExecutionBinding(f'binding{n}', 'MOVE_AWAY', 'escape', f'skill{n}',
                               'recovery' if n == 3 else 'escape-movement',
                               f'action{n}', 'MOVE_BACKWARD', p('binding'))
    return AdmissionInputs(admitted, control, route, criterion, binding, state, plan, retained)


def prepare(fault=None):
    times = count(1)
    def clock():
        return next(times)
    intent = IntentCommitment()
    intent.commit('escape', objective='escape threat', at_ns=0, provenance=p('intent'))
    worlds = tuple(SyntheticWorld(f'session{n}', fault if n == 1 else None) for n in (1, 2, 3))

    def authorize(action):
        return action.authorize(at_ns=clock(), provenance=p('authority'), authority='operator-action')

    def goal(skill, terminal):
        criterion = SkillTerminalCriterion('goal', skill.skill_id, 'escape-distance', p('goal'))
        evidence = SkillGoalEvidence('goal', skill.execution_id, skill.intent_id,
                                     terminal.action.action_id, terminal.interpretation.binding_id,
                                     terminal.interpretation.session_id, 'escape-distance',
                                     SkillGoalStatus.VIOLATED, clock(), p('independent-goal'))
        authority = SkillTerminalAuthority('skill-authority', skill.execution_id, 'goal', True,
                                           p('skill-authority'))
        return criterion, evidence, authority

    def exit_inputs(failed):
        criterion = SkillExitCriterion('exit', failed.skill_id, failed.intent_id, p('exit'))
        evidence = SkillExitEvidence('exit', failed.execution_id, failed.intent_id, failed.state,
                                    failed.events[-1].at_ns, failed.events[-1].provenance,
                                    LocalPathStatus.AVAILABLE, 'recovery', IntentImpact.NOT_CHALLENGED,
                                    clock(), p('independent-local-path'))
        authority = SkillExitAuthority('exit-authority', 'exit', failed.intent_id,
                                      SkillExitRoute.LOCAL_RECOVERY_CANDIDATE, True, p('exit-authority'))
        return criterion, evidence, authority

    def episode(third, recovery, retained):
        t = clock()
        authority = ExplicitProbeAuthority('probe-authority', 'session3', 'action3', 42, 'zombie',
                                            True, p('probe-authority'))
        return dict(arm='OBSERVE', price_quarters=1, prior_ref='uniform-nearfar-v1',
                    cursor=ExclusiveProbeCursor('session3', third.consequence.after_observation.seq + 1),
                    grant=CorrelatedProbeGrant(authority, 'probe:first'),
                    second_grant=CorrelatedProbeGrant(authority, 'probe:second'),
                    observed_at_ns=t, inspected_at_ns=t+1, second_observed_at_ns=t+2,
                    second_inspected_at_ns=t+3, at_ns=t+4, provenance=p('episode'),
                    binding4=ExecutionBinding('binding4', 'MOVE_AWAY', 'escape', 'skill4',
                                              'recovery', 'action4', 'MOVE_BACKWARD', p('binding4')),
                    authorize4=lambda a: a.authorize(at_ns=a.events[-1].at_ns+1, provenance=p('action4'),
                                                     authority='action4-authority'),
                    action_adapter=SyntheticWorld('session4'), deadline_ns=10000,
                    evaluator_request_id='evaluate', reset_id='reset', used_sessions=set(),
                    used_resets=set(), clock=count(200, 10).__next__, evaluator_horizon_ns=1)
    return dict(intent=intent, initial=LearningPreferenceState('risk_weight', 3, 0, 10, 0, p('origin')),
                first_inputs=admission(intent, 1), second_inputs=lambda r: admission(intent, 2, r),
                recovery_inputs=lambda r: admission(intent, 3, r), sessions=worlds, authorize=authorize,
                learning_criterion=ActionFeedbackCriterion(
                    'feedback', 'risk_weight', 'action1', 'binding1', 'MOVE_BACKWARD',
                    ActionState.OUTCOME, ActionOutcomeDisposition.OUTCOME, 'observed_execution',
                    FeedbackDirection.INCREASE, p('feedback-criterion')),
                learning_rule=LearningUpdateRule('risk-step', 1, 1),
                learning_authority=LearningUpdateAuthority('learning-authority', 'risk_weight', p('lrn')),
                goal_inputs=goal, exit_inputs=exit_inputs, clock=clock, deadlines=(1000, 2000, 3000),
                episode_inputs=episode, used_root_sessions=set())


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def noop(_):
        pass
    monkeypatch.setattr('adapters.mineflayer.execution.asyncio.sleep', noop)


def test_root_native_api_chain_and_e11_s29_s24_action4():
    args = prepare()
    result = asyncio.run(run_root_to_episode(**args))
    assert result.commit.new_state.revision == 1 and result.commit.new_state.value == 4
    assert result.commit.record.feedback_id == result.feedback.feedback.feedback_id
    assert result.failed_skill.state is SkillState.FAILED
    assert result.handoff.failed_skill_execution_id == result.failed_skill.execution_id
    assert result.third.action.skill_execution_id == result.recovery_skill.execution_id
    assert all(result.supervisor.get(f'action{n}').state is ActionState.OUTCOME for n in (1, 2, 3, 4))
    assert result.episode.decision.epoch.wait_score == 8
    assert result.episode.action4.state is ActionState.OUTCOME
    assert not result.physically_authenticated and not result.episode.physically_authenticated


@pytest.mark.parametrize('fault', ['session', 'seq', 'action', 'missing'])
def test_native_transport_corruption_never_reaches_second_action(fault):
    args = prepare(fault)
    with pytest.raises((ValueError, IndexError)):
        asyncio.run(run_root_to_episode(**args))
    assert args['sessions'][1].commands == []


@pytest.mark.parametrize('fault', ['learning-denied', 'learning-missing', 'retained', 'old-action',
                                  'wrong-intent', 'same-session', 'goal-denied', 'exit-denied'])
def test_owner_and_authority_substitution_stops_before_next_action(fault):
    args = prepare()
    if fault == 'learning-denied':
        args['learning_authority'] = replace(args['learning_authority'], granted=False)
    elif fault == 'learning-missing':
        args['learning_authority'] = None
    elif fault in ('retained', 'old-action', 'wrong-intent'):
        original = args['second_inputs']
        def corrupt(r):
            data = original(r)
            if fault == 'retained':
                return replace(data, retained=replace(r, value=9))
            return replace(data, binding=replace(data.binding, **(
                {'action_id': 'action1'} if fault == 'old-action' else {'required_intent_id': 'alien'})))
        args['second_inputs'] = corrupt
    elif fault == 'same-session':
        args['sessions'][1].started = args['sessions'][0].started
    else:
        key = 'goal_inputs' if fault == 'goal-denied' else 'exit_inputs'
        original = args[key]
        def deny(*a):
            criterion, evidence, authority = original(*a)
            return criterion, evidence, replace(authority, granted=False)
        args[key] = deny
    with pytest.raises(ValueError):
        asyncio.run(run_root_to_episode(**args))
    assert args['sessions'][2].commands == []


def test_consumed_root_cannot_be_replayed_even_after_failure():
    args = prepare('action')
    with pytest.raises(ValueError):
        asyncio.run(run_root_to_episode(**args))
    commands = list(args['sessions'][0].commands)
    with pytest.raises(ValueError, match='consumed'):
        asyncio.run(run_root_to_episode(**args))
    assert args['sessions'][0].commands == commands


def test_foreign_authorization_same_action_id_cannot_replace_root_owner():
    from relay_self.action import ActionLifecycle
    args = prepare()
    original = args['authorize']
    def substitute(proposed):
        foreign = ActionLifecycle(proposed.action_id, proposed.skill_execution_id,
                                  proposed.intent_id, proposed.events)
        return original(foreign)
    args['authorize'] = substitute
    with pytest.raises(ValueError, match='exact independently authorized'):
        asyncio.run(run_root_to_episode(**args))
    assert args['sessions'][0].commands == []


@pytest.mark.parametrize('fault', ['feedback', 'goal-session', 'goal-satisfied', 'intent-released',
                                  'recovery-retained', 'episode-cursor', 'episode-owner'])
def test_remaining_owner_boundaries_fail_closed(fault):
    args = prepare()
    if fault == 'feedback':
        args['learning_criterion'] = replace(args['learning_criterion'], required_action_id='old')
    elif fault.startswith('goal'):
        original = args['goal_inputs']
        def goal(*a):
            c, e, authority = original(*a)
            return c, replace(e, **({'session_id': 'foreign'} if fault == 'goal-session'
                                     else {'status': SkillGoalStatus.SATISFIED})), authority
        args['goal_inputs'] = goal
    elif fault == 'intent-released':
        original = args['exit_inputs']
        def release(failed):
            values = original(failed)
            args['intent'].invalidate('escape', reason='released', at_ns=args['clock'](),
                                      provenance=p('release'))
            return values
        args['exit_inputs'] = release
    elif fault == 'recovery-retained':
        original = args['recovery_inputs']
        args['recovery_inputs'] = lambda r: replace(original(r), retained=replace(r))
    else:
        original = args['episode_inputs']
        def episode(*a):
            values = original(*a)
            if fault == 'episode-cursor':
                values['cursor'].next_seq += 1
            else:
                values['retained'] = replace(a[2])
            return values
        args['episode_inputs'] = episode
    with pytest.raises(ValueError):
        asyncio.run(run_root_to_episode(**args))
