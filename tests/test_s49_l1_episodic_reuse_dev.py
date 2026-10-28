"""Pure negative controls for source-bound L1 episodic route transfer."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.goal_experience_dev import (
    L1RouteEpisodeDev,
    select_route_from_episode_dev,
)
from relay_self.goal_navigation import GoalControlRejected, GoalPurpose, L2GoalProposal
from relay_self.provenance import Provenance


def episode():
    return L1RouteEpisodeDev(
        source_session_id="old-real-world",
        source_goal_id="approach-demo",
        source_blocked_action_id="goal-approach-demo-step-2",
        source_blocked_after_seq=43,
        original_goal_offset_x=0.0,original_goal_offset_z=4.0,
        source_reason="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR",
        stages=(
            ("lateral-before-wall",2.5,1.1),
            ("past-wall",2.5,3.8),
            ("original-destination",0.0,4.0),
        ),
        source_native_actions=9,
        source_final_error_m=0.029,
        source_final_tolerance_m=0.35,
    )


def goal(*,x=7.5,z=14.5,session="new-real-world"):
    return L2GoalProposal(
        goal_id="approach-demo",intent_id="goal-navigate",
        session_id=session,target_x=x,target_z=z,
        purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,
        provenance=Provenance("dev-operator","L2-proposal"),
    )


def select(*,memo=None,target=None,**edits):
    kwargs={
        "start_x":7.5,"start_z":10.5,
        "blocked_action_id":"goal-approach-demo-step-2",
        "blocked_s16_seq":28,
        "blocked_reason":"MOTOR_CONSEQUENCE_UNDETERMINED",
        "blocked_terminal":"unknown",
        "blocked_consequence":"undetermined",
        "provenance":Provenance("l1-recall","experienced-route"),
    }
    kwargs.update(edits)
    return select_route_from_episode_dev(
        memo or episode(),target or goal(),**kwargs,
    )


def test_actual_new_world_xz_is_translated_not_copied():
    result=select()
    assert result.parent.session_id=="new-real-world"
    assert result.source_s16_seq==28
    assert result.route_id=="recalled-approach-demo"
    assert result.source_action_id=="goal-approach-demo-step-2"
    assert [(s.target_x,s.target_z) for s in result.stages]==[
        (10.0,11.6),(10.0,14.3),(7.5,14.5),
    ]
    assert result.stages[-1].target_x==result.parent.target_x
    assert result.stages[-1].target_z==result.parent.target_z
    assert result.provenance.source=="l1-recall"


@pytest.mark.parametrize("fault",[
    {"blocked_terminal":"outcome"},
    {"blocked_reason":"BLOCK_SEEN"},
    {"blocked_consequence":"executed"},
    {"blocked_s16_seq":0},
    {"blocked_action_id":"same-old-action"},
    {"start_x":8.5},
    {"start_z":10.1},
    {"provenance":Provenance("mineflayer","pretend-L1")},
])
def test_no_experience_admission_without_matching_new_native_evidence(fault):
    with pytest.raises(GoalControlRejected):
        select(**fault)


def test_stale_world_and_changed_goal_rejected():
    with pytest.raises(GoalControlRejected):
        select(target=goal(session="old-real-world"))
    with pytest.raises(GoalControlRejected):
        select(target=goal(x=7.7))
    with pytest.raises(GoalControlRejected):
        select(target=goal(z=15.2))


@pytest.mark.parametrize("changes",[
    {"source_native_actions":0},
    {"source_final_error_m":0.8},
    {"original_goal_offset_z":2.6},
    {"stages":(
        ("lateral-before-wall",2.5,1.1),
        ("past-wall",2.5,3.8),
        ("original-destination",0.0,5.0),
    )},
    {"stages":(
        ("same",2.5,1.1),("same",2.5,3.8),
        ("original-destination",0.0,4.0),
    )},
])
def test_fake_or_unsupported_experience_fails_closed(changes):
    with pytest.raises(GoalControlRejected):
        replace(episode(),**changes)


def test_exporter_requires_real_source_and_immutable_digest(tmp_path):
    from adapters.mineflayer.s49_l1_experience_export_dev import (
        export_episode_dev,
        load_episode_dev,
    )
    with pytest.raises((GoalControlRejected,FileNotFoundError,ValueError)):
        export_episode_dev(tmp_path,tmp_path/"episode.json")
    bad_memory=tmp_path/"episode.json"
    bad_memory.write_text('{"format":"forged"}',encoding="utf8")
    source=tmp_path/"raw.json"
    source.write_text('{"status":"PASS"}',encoding="utf8")
    with pytest.raises(GoalControlRejected):
        load_episode_dev(bad_memory,source)


def test_runner_and_owner_use_one_original_action_supervisor():
    owner=Path("adapters/mineflayer/s49_goal_executor_dev.py").read_text()
    route=Path("adapters/mineflayer/s49_goal_waypoint_route_dev.py").read_text()
    runner=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    assert "select_route_from_episode_dev(" in runner
    assert "load_episode_dev(" in runner
    assert "follow_l1_detour_dev(" in runner
    assert "executor.adopt_waypoint_dev(" in route
    assert "executor.execute_goal_step(" in route
    assert "prior.state is not ActionState.UNKNOWN" in owner
    assert "self.supervisor.open_actions" in owner
    assert '"learned_general_policy":False' in runner
