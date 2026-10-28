"""DEV native block Present: stricter than remembered route, no false clearance."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerRouteBlocksDev,
    encode_route_blocks_dev,
    parse_mineflayer_line,
)
from relay_self.goal_memory_choice_dev import (
    L1RecallStatusDev,
    select_selfworld_route_dev,
)
from relay_self.goal_native_blocks_dev import (
    NativeLanePresentDev,
    NativeRouteBlockPresentDev,
)
from relay_self.goal_navigation import GoalControlRejected
from relay_self.provenance import Provenance
from relay_self.self_world import WorldOrigin
from tests.test_s49_l1_selfworld_memory_choice_dev import (
    _context,
    _episode,
    _memory,
    _select,
)


def _present(left=("BLOCKED","BLOCKED","BLOCKED"),
             right=("CLEAR","CLEAR","CLEAR"),
             session="world-new",seq=50):
    return NativeRouteBlockPresentDev(
        session_id=session,native_seq=seq,
        request_id="native-probe-50",
        origin_x=3.5,origin_z=4.5,player_y=64.0,
        coverage="loaded_client_cache_only",
        lanes=(
            NativeLanePresentDev("LEFT",left),
            NativeLanePresentDev("RIGHT",right),
        ),
        provenance=Provenance("mineflayer",f"{session}:{seq}"),
    )


def _two_successes():
    return _context((
        _memory("route-a","world-a",_episode("world-a",side=2.5)),
        _memory("route-b","world-b",_episode("world-b",side=-2.5)),
    ))


def _decide(present):
    view,owner,goal=_two_successes()
    return _select(view,owner,goal,route_present_dev=present)


def test_native_present_resolves_only_one_safe_side():
    present=_present()
    assert present.observed_lane("LEFT").origin is WorldOrigin.OBSERVED
    assert present.observed_lane("RIGHT").value=="CLEAR"
    result=_decide(present)
    assert result.status is L1RecallStatusDev.SELECTED
    assert result.reason=="NATIVE_PRESENT_RESOLVED_CONFLICT"
    assert result.matching_successes==2
    assert result.selected_memory_id=="route-a"
    assert result.plan.stages[0].target_x==6.0


@pytest.mark.parametrize("left,right",[
    (("UNKNOWN","UNKNOWN","UNKNOWN"),("CLEAR","CLEAR","CLEAR")),
    (("CLEAR","CLEAR","CLEAR"),("CLEAR","CLEAR","CLEAR")),
    (("BLOCKED","BLOCKED","BLOCKED"),("BLOCKED","BLOCKED","BLOCKED")),
    (("UNKNOWN","BLOCKED","UNKNOWN"),("UNKNOWN","CLEAR","CLEAR")),
])
def test_missing_or_ambiguous_actual_cache_is_defer(left,right):
    result=_decide(_present(left,right))
    assert result.status is L1RecallStatusDev.DEFER
    assert result.plan is None


def test_reverse_observed_clear_lane_selects_left_route():
    result=_decide(_present(
        left=("CLEAR","CLEAR","CLEAR"),
        right=("CLEAR","BLOCKED","CLEAR"),
    ))
    assert result.status is L1RecallStatusDev.SELECTED
    assert result.selected_memory_id=="route-b"


@pytest.mark.parametrize("fault",[
    {"session_id":"foreign-world"},
    {"native_seq":47},
    {"origin_x":7.5},
    {"origin_z":11.2},
])
def test_foreign_stale_or_unrelated_present_rejected(fault):
    evidence=replace(_present(),**fault)
    with pytest.raises(GoalControlRejected):
        _decide(evidence)


def test_forged_native_provenance_fails_closed():
    with pytest.raises(GoalControlRejected):
        replace(
            _present(),
            provenance=Provenance("test","not-an-original-client-packet"),
        )


def test_native_packet_decode_strict_lanes_and_unloaded_cells():
    payload={
        "type":"route_blocks_dev","session_id":"world-new","seq":50,
        "request_id":"native-probe-50","origin_x":3.5,
        "origin_z":4.5,"player_y":64.0,
        "coverage":"loaded_client_cache_only","samples_per_lane":3,
        "unknown_is_not_clear":True,
        "lanes":[
            {"side":"LEFT","states":["BLOCKED","UNKNOWN","UNKNOWN"]},
            {"side":"RIGHT","states":["CLEAR","CLEAR","CLEAR"]},
        ],
    }
    message=parse_mineflayer_line(json.dumps(payload))
    assert isinstance(message,MineflayerRouteBlocksDev)
    assert message.lanes[0].states[1]=="UNKNOWN"
    assert message.lanes[1].side=="RIGHT"
    assert json.loads(encode_route_blocks_dev(
        "native-probe-50",origin_x=3.5,origin_z=4.5,
    ))=={
        "type":"observe_route_blocks_dev","request_id":"native-probe-50",
        "origin_x":3.5,"origin_z":4.5,
    }
    for mutation in (
        {**payload,"unknown_is_not_clear":False},
        {**payload,"coverage":"full_world"},
        {**payload,"samples_per_lane":4},
        {**payload,"lanes":payload["lanes"][:1]},
        {**payload,"extra":"forged"},
    ):
        with pytest.raises(MineflayerAdapterProtocolError):
            parse_mineflayer_line(json.dumps(mutation))


def test_no_observed_geometry_keeps_earlier_conflict_defer():
    view,owner,goal=_two_successes()
    ordinary=select_selfworld_route_dev(
        view,owner,goal,start_x=3.5,start_z=4.5,
        fixture_scope="fixture-known-from-operator",
        blocked_action_id="goal-approach-demo-step-2",
        blocked_s16_seq=48,
        blocked_reason="MOTOR_CONSEQUENCE_UNDETERMINED",
        blocked_terminal="unknown",
        blocked_consequence="undetermined",
        provenance=Provenance("test-l1","defer"),
    )
    assert ordinary.status is L1RecallStatusDev.DEFER
