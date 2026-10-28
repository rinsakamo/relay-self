"""DEV SelfWorld REMEMBERED selection: provenance, consensus, abstention."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relay_self.goal_experience_dev import L1RouteEpisodeDev
from relay_self.goal_memory_choice_dev import (
    L1RecallStatusDev,
    make_route_memory_dev,
    select_selfworld_route_dev,
)
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import SelfWorldView, WorldOrigin


def _episode(session,actions=8,error=0.12,side=2.5):
    return L1RouteEpisodeDev(
        source_session_id=session,source_goal_id="approach-demo",
        source_blocked_action_id="goal-approach-demo-step-2",
        source_blocked_after_seq=43,
        original_goal_offset_x=0.0,original_goal_offset_z=4.0,
        source_reason="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR",
        stages=(
            ("lateral-before-wall",float(side),1.1),
            ("past-wall",float(side),3.8),
            ("original-destination",0.0,4.0),
        ),
        source_native_actions=actions,
        source_final_error_m=error,
        source_final_tolerance_m=0.45,
    )


def _memory(memory_id,session,episode):
    return make_route_memory_dev(
        memory_id=memory_id,
        kind="SUCCESS_ROUTE" if episode is not None else "FAILED_BLOCKED",
        source_session_id=session,source_sha256=("a"*64 if session=="world-a"
                                                 else "b"*64 if session=="world-b"
                                                 else "c"*64),
        fixture_scope="fixture-known-from-operator",
        goal_offset_x=0.0,goal_offset_z=4.0,
        episode=episode,
    )


def _context(memories):
    owner=PersistentCognition(
        identity=IdentitySpecification(
            self_id="self-memory",directives=("Remember facts",),
            provenance=Provenance("test","self-identity"),
        ),
    )
    for memory in memories:
        owner=owner.retain_memory(memory)
    view=SelfWorldView(
        self_id="self-memory",session_id="world-new",
        epoch_id="epoch-48",observation=None,
        memories=owner.memories,beliefs=(),scenarios=(),
        forecasts=(),self_body=None,
    )
    goal=L2GoalProposal(
        goal_id="approach-demo",intent_id="goal-navigate",
        session_id="world-new",target_x=3.5,target_z=8.5,
        purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.3,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,
        provenance=Provenance("test-l2","original"),
    )
    return view,owner,goal


def _select(view,owner,goal,**override):
    kwargs={
        "start_x":3.5,"start_z":4.5,
        "fixture_scope":"fixture-known-from-operator",
        "blocked_action_id":"goal-approach-demo-step-2",
        "blocked_s16_seq":48,
        "blocked_reason":"MOTOR_CONSEQUENCE_UNDETERMINED",
        "blocked_terminal":"unknown",
        "blocked_consequence":"undetermined",
        "provenance":Provenance("test-l1","recall"),
    }
    kwargs.update(override)
    return select_selfworld_route_dev(view,owner,goal,**kwargs)


def test_two_independent_successes_one_failure_are_remembered_only():
    ma=_memory("route-a","world-a",_episode("world-a",actions=8))
    mb=_memory("route-b","world-b",_episode("world-b",actions=7))
    mf=_memory("failure","world-c",None)
    view,owner,goal=_context((ma,mb,mf))
    assert view.remembered("route-a").origin is WorldOrigin.REMEMBERED
    assert view.observation is None
    result=_select(view,owner,goal)
    assert result.status is L1RecallStatusDev.SELECTED
    assert result.matching_successes==2
    assert result.matching_failures==1
    assert result.selected_memory_id=="route-b"
    assert result.plan is not None
    assert result.plan.parent.session_id=="world-new"
    assert [(s.target_x,s.target_z) for s in result.plan.stages]==[
        (6.0,5.6),(6.0,8.3),(3.5,8.5),
    ]


def test_conflicting_route_signatures_defer_without_action():
    ma=_memory("route-a","world-a",_episode("world-a"))
    mb=_memory("route-b","world-b",_episode("world-b",side=-2.5))
    view,owner,goal=_context((ma,mb))
    r=_select(view,owner,goal)
    assert r.status is L1RecallStatusDev.DEFER
    assert r.reason=="CONFLICTING_RECALLED_ROUTES"
    assert r.plan is None


@pytest.mark.parametrize("fault",[
    {"fixture_scope":"unobserved-wall-geometry"},
    {"blocked_terminal":"outcome"},
    {"blocked_consequence":"executed"},
    {"blocked_reason":"BLOCK_SENSOR_CLAIM"},
    {"start_z":4.1},
])
def test_mismatch_or_missing_source_abstains(fault):
    view,owner,goal=_context((_memory("route-a","world-a",_episode("world-a")),))
    r=_select(view,owner,goal,**fault)
    assert r.status is L1RecallStatusDev.DEFER
    assert r.plan is None


def test_false_owner_and_foreign_world_fail_closed():
    view,owner,goal=_context((_memory("route-a","world-a",_episode("world-a")),))
    with pytest.raises(GoalControlRejected):
        _select(replace(view,self_id="stolen-other-self"),owner,goal)
    with pytest.raises(GoalControlRejected):
        _select(replace(view,session_id="foreign"),owner,goal)
    with pytest.raises(GoalControlRejected):
        _select(replace(view,memories=()),owner,goal)


def test_duplicate_source_session_and_forged_memory_fails_closed():
    a=_memory("a","world-a",_episode("world-a"))
    b=_memory("b","world-a",_episode("world-a"))
    view,owner,goal=_context((a,b))
    with pytest.raises(GoalControlRejected):
        _select(view,owner,goal)
    data=json.loads(a.content)
    data["stages"]=[("invented",4,4)]
    forged=replace(a,content=json.dumps(data))
    view,owner,goal=_context((forged,))
    with pytest.raises(GoalControlRejected):
        _select(view,owner,goal)


def test_invalid_memory_provenance_refused():
    a=_memory("route-a","world-a",_episode("world-a"))
    bad=replace(a,source_provenance=Provenance("mineflayer","forged"))
    view,owner,goal=_context((bad,))
    with pytest.raises(GoalControlRejected):
        _select(view,owner,goal)
