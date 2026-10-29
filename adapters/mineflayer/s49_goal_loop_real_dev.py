"""One real Minecraft DEV World: L2/L1 goal, autonomous L0 XZ loop.

The goal is provided by an explicit DEV operator acting as L2/L1 inputs,
not a live LLM or learned L1. L0 triggers on native probes WITHOUT zombies.
The same inherited S49 ActionSupervisor owns each real S15/S16 transaction.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from dataclasses import asdict, replace
from functools import partial
from pathlib import Path

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.g3_applied_gait_source_dev import applied_gait_from_original_t1u_dev
from adapters.mineflayer.g4_observed_gait_choice_dev import choose_g4_observed_gait_dev
from adapters.mineflayer.g41_inflight_brake_dev import (
    decide_g41_inflight_brake_dev,
    g41_feedback_window_duration_dev,
)
from adapters.mineflayer.g42_native_brake_timing_dev import qualify_g42_native_window_dev
from adapters.mineflayer.g43_passive_native_tail_dev import (
    G43PassiveNativeSampleDev,
    qualify_g43_passive_native_tail_dev,
)
from adapters.mineflayer.g44_intra_action_gait_dev import (
    decide_g44_intra_action_gait_dev,
)
from adapters.mineflayer.g45_paper_gait_join_dev import (
    join_g45_native_ack_paper_gait_dev,
)
from adapters.mineflayer.g46_paper_control_generation_dev import (
    join_g46_control_generation_dev,
)
from adapters.mineflayer.g47_original_t2_gait_join_dev import (
    join_g47_original_t2_worldticks_dev,
)
from adapters.mineflayer.g48_direct_action_generation_dev import (
    join_g48_direct_action_worldticks_dev,
)
from adapters.mineflayer.normal_action import NormalActionAuthorization, NormalActionStage
from adapters.mineflayer.python_protocol import (
    MineflayerLocalVoxelsDev,
    MineflayerObservation,
    MineflayerPaperSnapshot,
    MineflayerRouteBlocksDev,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
from adapters.mineflayer.s49_goal_t2_boundary_dev import GoalT2BoundaryRejected
from adapters.mineflayer.s49_goal_waypoint_route_dev import follow_l1_detour_dev
from adapters.mineflayer.s49_l1_experience_export_dev import load_episode_dev
from adapters.mineflayer.s49_l1_selfworld_memory_dev import recall_from_selfworld_dev
from adapters.mineflayer.s49_normal_session_real_ci import (
    _cleanup_session,
    _write_final_report,
)
from adapters.mineflayer.s49_paper_world_first_dev import (
    _await_dash_dev_line,
    offline_uuid,
)
from adapters.mineflayer.s49_t2_applied_gait_observation_dev import G1AppliedGaitObserverDev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from relay_self.action import ActionState
from relay_self.goal_detour_dev import explicit_l1_detour_dev
from relay_self.goal_experience_dev import select_route_from_episode_dev
from relay_self.goal_grid_search_dev import choose_grid_route_dev
from relay_self.goal_local_voxel_dev import (
    NativeVoxelPresentDev,
    VoxelColumnDev,
    choose_voxel_waypoint_dev,
)
from relay_self.goal_memory_choice_dev import L1RecallStatusDev
from relay_self.goal_navigation import (
    GoalDecisionKind,
    GoalPurpose,
    L2GoalProposal,
    ObservedGoalL0,
    compile_l1_goal_dev,
    compute_goal_bearing_dev,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


async def _correlated_native_voxels_dev(
    session, request_id:str, *, origin_x:float, origin_z:float,
) -> MineflayerLocalVoxelsDev:
    """Same original process reader: source-linked 42-column cache packet."""
    await session.send_local_voxels_dev(
        request_id,origin_x=origin_x,origin_z=origin_z,
    )
    for _ in range(48):
        message=await asyncio.wait_for(session.receive(),timeout=6.0)
        if isinstance(message,MineflayerLocalVoxelsDev):
            if (
                message.request_id!=request_id
                or message.session_id!=session.started.session_id
                or not math.isclose(message.origin_x,origin_x,abs_tol=1e-8)
                or not math.isclose(message.origin_z,origin_z,abs_tol=1e-8)
            ):
                raise RuntimeError("foreign/stale correlated native voxels")
            return message
        if type(message).__name__ in (
            "MineflayerCommandError","MineflayerConnectionEnd",
            "MineflayerAdapterErrorMessage",
        ):
            raise RuntimeError("native voxel command error/connection lost")
    raise RuntimeError("no bounded correlated native voxel packet")


async def _correlated_native_route_blocks_dev(
    session, request_id:str, *, origin_x:float, origin_z:float,
) -> MineflayerRouteBlocksDev:
    """Sole original session receive owner reads one bounded live block packet."""
    await session.send_route_blocks_dev(
        request_id,origin_x=origin_x,origin_z=origin_z,
    )
    for _ in range(36):
        message=await asyncio.wait_for(session.receive(),timeout=6.0)
        if isinstance(message,MineflayerRouteBlocksDev):
            if (
                message.request_id!=request_id
                or message.session_id!=session.started.session_id
                or not math.isclose(message.origin_x,origin_x,abs_tol=1e-8)
                or not math.isclose(message.origin_z,origin_z,abs_tol=1e-8)
            ):
                raise RuntimeError("foreign/stale correlated native block present")
            return message
        if type(message).__name__ in (
            "MineflayerCommandError","MineflayerConnectionEnd",
            "MineflayerAdapterErrorMessage",
        ):
            raise RuntimeError("native route block observation failed closed")
    raise RuntimeError("no bounded correlated native route block Present")


def source(tag:str)->Provenance:
    return Provenance("s49-goal-dev-operator",tag)


async def qualify(
    report_path:Path, server_log:Path, *, offset_m:float=2.6,
    inject_threat_after_first_dev:bool=False,
    inject_threat_during_first_dev:bool=False,
    goal_turn_dx_dev:float=0.0,
    obstacle_wall_dev:bool=False,
    detour_after_wall_dev:bool=False,
    experience_memory_dev:Path|None=None,
    experience_source_report_dev:Path|None=None,
    selfworld_memory_snapshot_dev:Path|None=None,
    selfworld_memory_catalog_dev:Path|None=None,
    detour_left_dev:bool=False,
    left_lane_block_dev:bool=False,
    native_route_present_dev:bool=False,
    native_voxel_map_dev:bool=False,
    right_lane_block_dev:bool=False,
    local_grid_search_dev:bool=False,
    grid_refresh_dev:bool=False,
    grid_midroute_obstacle_dev:bool=False,
    paper_jar_dev:Path|None=None,
    paper_plugin_dev:Path|None=None,
    paper_dash_plugin_dev:Path|None=None,
    g2_dash_first_dev:bool=False,
    g3_single_owner_dev:bool=False,
    g3_modifier_identity_dev:bool=False,
    paper_gait_observation_dev:bool=False,
    g2_sprint_first_dev:bool=False,
    g2_sprint_prefix_dev:bool=False,
    g2_sneak_prefix_dev:bool=False,
    g4_auto_gait_dev:bool=False,
    g41_inflight_brake_dev:bool=False,
    g42_brake_timing_dev:bool=False,
    g43_passive_tail_control_dev:bool=False,
    g44_intra_action_gait_dev:bool=False,
    g45_paper_gait_join_dev:bool=False,
    g45_hazard_during_gait_dev:bool=False,
    g46_paper_generation_dev:bool=False,
    g47_original_t2_gait_join_dev:bool=False,
    g48_direct_action_generation_dev:bool=False,
)->int:
    report={
        "classification":"DEV_ONLY_S49_L2_L1_GOAL_AUTONOMOUS_L0",
        "status":"BLOCKED","stage":"START",
        "real_model_calls":0,"learned_L1_attested":False,
        "L2_source":"EXPLICIT_DEV_OPERATOR_NOT_LIVE_L2",
        "L1_source":"DETERMINISTIC_DEV_POLICY_NOT_LEARNED",
        "real_world":False,"native_actions":[],
        "l0_decisions":[],"zombie_events_needed_for_continuation":False,
        "existing_S49_action_supervisor_reused":True,
        "legacy_zombie_S14_admission_reused":False,
        "goal_S14_dev_admission":True,
        "qualification_go":False,"science_go":False,
        "threat_injection_dev":inject_threat_after_first_dev,
        "threat_inflight_dev":inject_threat_during_first_dev,
        "inflight_l0":None,
        "goal_handoff":None,
        "upper_layer_replan_executed":False,
        "goal_turn_dx_dev":goal_turn_dx_dev,
        "obstacle_wall_dev":obstacle_wall_dev,
        "detour_left_dev":detour_left_dev,
        "left_lane_block_dev":left_lane_block_dev,
        "native_route_present_dev":native_route_present_dev,
        "native_voxel_map_dev":native_voxel_map_dev,
        "right_lane_block_dev":right_lane_block_dev,
        "local_grid_search_dev":local_grid_search_dev,
        "grid_refresh_dev":grid_refresh_dev,
        "grid_midroute_obstacle_dev":grid_midroute_obstacle_dev,
        "l1_t2_shared_channel_dev":os.environ.get("S49_L1_T2_CHANNEL_DEV_ONLY")=="1",
        "paper_server_dev":paper_jar_dev is not None,
        "g1_applied_gait_observation_dev":paper_gait_observation_dev,
        "g2_sprint_first_dev":g2_sprint_first_dev,
        "g2_sprint_prefix_dev":g2_sprint_prefix_dev,
        "g2_sprint_actions_dev":[],
        "g2_dash_first_dev":g2_dash_first_dev,
        "g3_single_owner_dev":g3_single_owner_dev,
        "g3_modifier_identity_dev":g3_modifier_identity_dev,
        "g4_auto_gait_dev":g4_auto_gait_dev,
        "g4_observed_choices_dev":[],
        "g41_inflight_brake_dev":g41_inflight_brake_dev,
        "g41_inflight_samples_dev":[],
        "g42_brake_timing_dev":g42_brake_timing_dev,
        "g42_native_windows_dev":[],
        "g43_passive_tail_control_dev":g43_passive_tail_control_dev,
        "g43_passive_native_tails_dev":[],
        "g44_intra_action_gait_dev":g44_intra_action_gait_dev,
        "g44_native_transition_probes_dev":[],
        "g44_native_transition_acks_dev":[],
        "g45_paper_gait_join_dev":g45_paper_gait_join_dev,
        "g45_action_clear_acks_dev":[],
        "g45_paper_transition_windows_dev":[],
        "g45_hazard_during_gait_dev":g45_hazard_during_gait_dev,
        "g45_native_hazard_preempt_dev":None,
        "g46_paper_generation_dev":g46_paper_generation_dev,
        "g46_native_paper_generations_dev":[],
        "g46_original_run_applied_acks_dev":[],
        "g47_original_t2_gait_join_dev":g47_original_t2_gait_join_dev,
        "g47_worldtick_gait_audit_dev":None,
        "g48_direct_action_generation_dev":g48_direct_action_generation_dev,
        "g48_original_direct_action_acks_dev":[],
        "g48_direct_worldtick_audit_dev":None,
        "g2_dash_modifier_dev":None,
        "g2_sneak_prefix_dev":g2_sneak_prefix_dev,
        "g2_sneak_actions_dev":[],
        "native_grid_refresh_observations_dev":[],
        "native_grid_search_choice_dev":None,
        "native_local_voxel_observation_dev":None,
        "native_local_voxel_choice_dev":None,
        "native_route_blocks_observation_dev":None,
        "detour_after_wall_dev":detour_after_wall_dev,
        "experience_requested_dev":experience_memory_dev is not None,
        "experience_selection_dev":None,
        "selfworld_memory_selection_dev":None,
        "native_goal_looks":[],
    }
    server=collector=session=temp=None
    t2_owner=None
    gait_observer=None
    cleanup_cancel=[]
    rc=2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI")!="1"
            or os.environ.get("S49_L0_GOAL_LOOP_DEV_ONLY")!="1"
            or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY")!="1"
            or os.environ.get("NODE_OPTIONS")
            or type(offset_m) is not float or not 1.8<=offset_m<=4.0
            or type(g4_auto_gait_dev) is not bool
            or type(g41_inflight_brake_dev) is not bool
            or type(g42_brake_timing_dev) is not bool
            or type(g43_passive_tail_control_dev) is not bool
            or type(g44_intra_action_gait_dev) is not bool
            or type(g45_paper_gait_join_dev) is not bool
            or type(g45_hazard_during_gait_dev) is not bool
            or type(g46_paper_generation_dev) is not bool
            or type(g47_original_t2_gait_join_dev) is not bool
            or type(g48_direct_action_generation_dev) is not bool
            or (g48_direct_action_generation_dev and (
                not g47_original_t2_gait_join_dev
                or os.environ.get("S49_G48_DIRECT_ACTION_GENERATION_DEV_ONLY")!="1"
            ))
            or (g47_original_t2_gait_join_dev and (
                not g46_paper_generation_dev
                or os.environ.get("S49_G47_ORIGINAL_T2_GAIT_JOIN_DEV_ONLY")!="1"
            ))
            or (g46_paper_generation_dev and (
                not g45_paper_gait_join_dev
                or os.environ.get("S49_G46_PAPER_GENERATION_DEV_ONLY")!="1"
            ))
            or (g45_hazard_during_gait_dev and (
                not g45_paper_gait_join_dev
                or os.environ.get("S49_G45_HAZARD_DURING_GAIT_DEV_ONLY")!="1"
            ))
            or (g45_paper_gait_join_dev and (
                not g44_intra_action_gait_dev
                or os.environ.get("S49_G45_PAPER_GAIT_JOIN_DEV_ONLY")!="1"
            ))
            or (g44_intra_action_gait_dev and (
                not g43_passive_tail_control_dev
                or os.environ.get("S49_G44_INTRA_ACTION_GAIT_DEV_ONLY")!="1"
            ))
            or (g43_passive_tail_control_dev and (
                not g42_brake_timing_dev
                or os.environ.get("S49_G43_PASSIVE_TAIL_DEV_ONLY")!="1"
            ))
            or (g42_brake_timing_dev and (
                not g41_inflight_brake_dev
                or os.environ.get("S49_G42_BRAKE_TIMING_DEV_ONLY")!="1"
            ))
            or (g41_inflight_brake_dev and (
                not g4_auto_gait_dev
                or os.environ.get("S49_G41_INFLIGHT_BRAKE_DEV_ONLY")!="1"
            ))
            or (g4_auto_gait_dev and (
                os.environ.get("S49_G4_OBSERVED_GAIT_DEV_ONLY")!="1"
                or not g3_modifier_identity_dev or not g3_single_owner_dev
                or not g2_dash_first_dev or not paper_gait_observation_dev
                or any((g2_sprint_first_dev,g2_sprint_prefix_dev,
                        g2_sneak_prefix_dev))
                or obstacle_wall_dev or detour_after_wall_dev
                or inject_threat_after_first_dev or inject_threat_during_first_dev
                or goal_turn_dx_dev!=0.0
                or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY")!="1"
            ))
            or type(g2_sneak_prefix_dev) is not bool
            or (g2_sneak_prefix_dev and (
                not paper_gait_observation_dev
                or g2_sprint_first_dev
                or obstacle_wall_dev or detour_after_wall_dev
                or goal_turn_dx_dev!=0.0
                or os.environ.get("S49_GOAL_G2_SNEAK_DEV_ONLY")!="1"
            ))
            or type(g3_modifier_identity_dev) is not bool
            or (g3_modifier_identity_dev and (
                not g3_single_owner_dev
                or not paper_gait_observation_dev
                or os.environ.get("S49_G3_MODIFIER_IDENTITY_DEV_ONLY")!="1"
            ))
            or type(g3_single_owner_dev) is not bool
            or (g3_single_owner_dev and (
                not g2_dash_first_dev
                or not paper_gait_observation_dev
                or os.environ.get("S49_L1_G3_T2_DEV_ONLY")!="1"
            ))
            or type(g2_dash_first_dev) is not bool
            or (g2_dash_first_dev and (
                not (g2_sprint_prefix_dev or g4_auto_gait_dev)
                or not paper_gait_observation_dev
                or paper_dash_plugin_dev is None
                or not isinstance(paper_dash_plugin_dev,Path)
                or not paper_dash_plugin_dev.is_file()
                or paper_dash_plugin_dev.is_symlink()
                or os.environ.get("S49_GOAL_G2_DASH_FIRST_DEV_ONLY")!="1"
                or os.environ.get("S49_SPEED_ATTR_SYNC_DEV_ONLY")!="1"
                or obstacle_wall_dev or detour_after_wall_dev
            ))
            or (paper_dash_plugin_dev is not None and not g2_dash_first_dev)
            or type(g2_sprint_prefix_dev) is not bool
            or (g2_sprint_prefix_dev and (
                not paper_gait_observation_dev
                or g2_sprint_first_dev or g2_sneak_prefix_dev
                or obstacle_wall_dev or detour_after_wall_dev
                or goal_turn_dx_dev != 0.0
                or os.environ.get("S49_GOAL_G2_SPRINT_PREFIX_DEV_ONLY")!="1"
                or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY")!="1"
            ))
            or type(g2_sprint_first_dev) is not bool
            or (g2_sprint_first_dev and (
                not paper_gait_observation_dev
                or obstacle_wall_dev or detour_after_wall_dev
                or goal_turn_dx_dev!=0.0
                or os.environ.get("S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY")!="1"
                or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY")!="1"
            ))
            or type(paper_gait_observation_dev) is not bool
            or (paper_gait_observation_dev and (
                paper_jar_dev is None
                or os.environ.get("S49_L1_G1_OBSERVATION_DEV_ONLY")!="1"
                or os.environ.get("S49_L1_T2_CHANNEL_DEV_ONLY")!="1"
            ))
            or (paper_jar_dev is None) != (paper_plugin_dev is None)
            or (paper_jar_dev is not None and (
                os.environ.get("S49_L1_T2_CHANNEL_DEV_ONLY")!="1"
                or os.environ.get("S49_L1_T2_BOUNDARY_DEV_ONLY")!="1"
                or not isinstance(paper_jar_dev,Path)
                or not isinstance(paper_plugin_dev,Path)
                or not paper_jar_dev.is_file()
                or not paper_plugin_dev.is_file()
                or paper_jar_dev.is_symlink()
                or paper_plugin_dev.is_symlink()
            ))
            or (os.environ.get("S49_L1_T2_CHANNEL_DEV_ONLY")=="1"
                and paper_jar_dev is None)
            or type(inject_threat_during_first_dev) is not bool
            or (inject_threat_during_first_dev and (
                inject_threat_after_first_dev
                or os.environ.get("S49_L0_INFLIGHT_PREEMPT_DEV_ONLY")!="1"
            ))
            or type(goal_turn_dx_dev) is not float
            or not math.isfinite(goal_turn_dx_dev)
            or goal_turn_dx_dev not in (0.0, 1.4)
            or ((experience_memory_dev is None)
                !=(experience_source_report_dev is None))
            or (experience_memory_dev is not None and (
                not isinstance(experience_memory_dev,Path)
                or not isinstance(experience_source_report_dev,Path)
                or not detour_after_wall_dev
                or os.environ.get("S49_L1_EPISODIC_REUSE_DEV_ONLY")!="1"
            ))
            or (selfworld_memory_snapshot_dev is None)
               !=(selfworld_memory_catalog_dev is None)
            or (selfworld_memory_snapshot_dev is not None and (
                not isinstance(selfworld_memory_snapshot_dev,Path)
                or not isinstance(selfworld_memory_catalog_dev,Path)
                or not detour_after_wall_dev
                or experience_memory_dev is not None
                or os.environ.get("S49_L1_SELFWORLD_MEMORY_DEV_ONLY")!="1"
            ))
            or type(left_lane_block_dev) is not bool
            or type(native_route_present_dev) is not bool
            or (left_lane_block_dev and not (
                (native_route_present_dev and
                 os.environ.get("S49_L1_NATIVE_BLOCKS_DEV_ONLY")=="1")
                or (native_voxel_map_dev and
                    os.environ.get("S49_L1_VOXEL_DEV_ONLY")=="1")
            ))
            or (native_route_present_dev and (
                not detour_after_wall_dev
                or selfworld_memory_snapshot_dev is None
                or os.environ.get("S49_L1_NATIVE_BLOCKS_DEV_ONLY")!="1"
            ))
            or type(native_voxel_map_dev) is not bool
            or type(right_lane_block_dev) is not bool
            or type(local_grid_search_dev) is not bool
            or type(grid_refresh_dev) is not bool
            or type(grid_midroute_obstacle_dev) is not bool
            or (grid_refresh_dev and (
                not local_grid_search_dev
                or os.environ.get("S49_L1_GRID_REFRESH_DEV_ONLY")!="1"
            ))
            or (grid_midroute_obstacle_dev and (
                not grid_refresh_dev or not left_lane_block_dev
                or right_lane_block_dev
            ))
            or (left_lane_block_dev and right_lane_block_dev
                and not local_grid_search_dev)
            or (local_grid_search_dev and (
                not native_voxel_map_dev
                or os.environ.get("S49_L1_GRID_SEARCH_DEV_ONLY")!="1"
            ))
            or (right_lane_block_dev and not native_voxel_map_dev)
            or (native_voxel_map_dev and (
                not detour_after_wall_dev or not obstacle_wall_dev
                or selfworld_memory_snapshot_dev is not None
                or experience_memory_dev is not None
                or native_route_present_dev
                or detour_left_dev
                or os.environ.get("S49_L1_VOXEL_DEV_ONLY")!="1"
            ))
            or type(detour_left_dev) is not bool
            or (detour_left_dev and (
                not detour_after_wall_dev
                or selfworld_memory_snapshot_dev is not None
                or experience_memory_dev is not None
                or os.environ.get("S49_L1_CONFLICT_ROUTE_DEV_ONLY")!="1"
            ))
            or type(detour_after_wall_dev) is not bool
            or (detour_after_wall_dev and (
                not obstacle_wall_dev or goal_turn_dx_dev!=0.0
                or offset_m!=4.0
                or os.environ.get("S49_L1_WAYPOINT_DEV_ONLY")!="1"
            ))
            or type(obstacle_wall_dev) is not bool
            or (goal_turn_dx_dev!=0.0 and obstacle_wall_dev)
            or ((goal_turn_dx_dev!=0.0 or obstacle_wall_dev) and (
                inject_threat_after_first_dev or inject_threat_during_first_dev
                or os.environ.get("S49_L0_TURN_DEV_ONLY")!="1"
            ))
            or (obstacle_wall_dev and
                os.environ.get("S49_L0_WALL_DEV_ONLY")!="1")
            or type(inject_threat_after_first_dev) is not bool
            or (inject_threat_after_first_dev and
                os.environ.get("S49_L0_REAL_THREAT_DEV_ONLY")!="1")
        ):
            raise RuntimeError("original S49 goal DEV gates missing")
        temp=tempfile.TemporaryDirectory(prefix="s49-l0-goal-world-")
        root=Path(temp.name)
        if paper_jar_dev is None:
            report.update(await asyncio.to_thread(_fetch_official_server,root/"minecraft.jar"))
            _write_config(root)
            server_jar=root/"minecraft.jar"
        else:
            _write_config(root)
            # Reuse T1w Paper plugin exact-source build in isolated disposable
            # World. Do NOT modify original L1 plugin or Paper source.
            server_jar=root/"paper.jar"
            shutil.copy2(paper_jar_dev,server_jar)
            plugin_dir=root/"plugins/RelayMetabolismDev"
            plugin_dir.mkdir(parents=True)
            shutil.copy2(paper_plugin_dev,root/"plugins/relay-metabolism-dev.jar")
            if g2_dash_first_dev:
                dash_dir=root/"plugins/RelayS49DashDev"
                dash_dir.mkdir()
                shutil.copy2(
                    paper_dash_plugin_dev,root/"plugins/s49-dash-dev.jar",
                )
                (dash_dir/"config.yml").write_text(
                    "enabled: true\nexpected-player-name: RelaySelf\n",
                    encoding="utf-8",
                )
                report["g2_dash_plugin_sha256"]=hashlib.sha256(
                    (root/"plugins/s49-dash-dev.jar").read_bytes(),
                ).hexdigest()
            config=(Path(__file__).parent/
                    "m02_paper_dev/src/main/resources/config.yml").read_text()
            config=config.replace("dev-enabled: false","dev-enabled: true")
            config += ("\nadaptive-tick-observer-dev: true\n"
                       "t1f-snapshot-dev: true\n"
                       "t1u-gait-dev: "
                       +("true" if paper_gait_observation_dev else "false")
                       +"\n"
                       +"t1u-modifier-identity-dev: "
                       +("true" if g3_modifier_identity_dev else "false")
                       +"\n")
            (plugin_dir/"config.yml").write_text(config)
            original=(root/"server.properties").read_text()
            (root/"server.properties").write_text(
                original.replace("gamemode=creative","gamemode=survival")
                +"generate-structures=false\n"
            )
            report["server_source"]="PINNED_DEV_PAPER_NOT_OFFICIAL_VANILLA"
            report["paper_jar_sha256"]=hashlib.sha256(server_jar.read_bytes()).hexdigest()
            report["paper_plugin_sha256"]=hashlib.sha256(
                (root/"plugins/relay-metabolism-dev.jar").read_bytes()
            ).hexdigest()
        report["stage"]="SERVER_START"
        server,collector,_=await _ready_server(root,server_jar,server_log)
        assert server.stdin is not None
        _command(server,"gamerule doMobSpawning false")
        _command(server,"kill @e[type=minecraft:zombie]")
        await server.stdin.drain()
        session=await _new_session()
        sid=session.started.session_id
        report["session_id"]=sid
        intent=IntentCommitment()
        intent.commit(
            "goal-navigate",objective="approach a specified XZ location",
            at_ns=1,provenance=source("intent-goal-navigate"),
        )
        executor=S49GoalExecutorDev(sid,intent)
        if os.environ.get("S49_L1_T2_CHANNEL_DEV_ONLY")=="1":
            if not (
                os.environ.get("RELAYSELF_T1F_DEV")=="1"
                and os.environ.get("RELAYSELF_PAPER_TICK_DEV")=="1"
                and os.environ.get("S49_L1_T2_BOUNDARY_DEV_ONLY")=="1"
            ):
                raise RuntimeError("same-World L1/T2 DEV requires explicit T1f/T2/S49 gates")
            t2_owner=TickAccounting(
                sid,
                **({
                    "gait_source":(
                        partial(applied_gait_from_original_t1u_dev,
                                strict_modifier_identity_dev=True)
                        if g3_modifier_identity_dev
                        else applied_gait_from_original_t1u_dev
                    ),
                    "g3_partial_dev":True,
                } if g3_single_owner_dev else {}),
            )
            session.bind_l1_t2_owner_dev(t2_owner)
            if paper_gait_observation_dev:
                gait_observer=G1AppliedGaitObserverDev(sid)
                session.bind_l1_t2_gait_observer_dev(gait_observer)
        # Single native probe anchors a DEV L2 target at a fixed World XZ.
        initial=await _correlated_observe(session,f"goal-{sid}-initial")
        if t2_owner is not None:
            # Read through the SAME existing session. No background consumer,
            # fabricated initial Paper tick or second native receiver.
            for _ in range(48):
                if t2_owner.previous is not None:
                    break
                frame=await asyncio.wait_for(session.receive(),timeout=3.0)
                if type(frame).__name__ in (
                    "MineflayerAdapterErrorMessage","MineflayerConnectionEnd",
                    "MineflayerCommandError","MineflayerShutdownAck",
                ):
                    raise RuntimeError("T2 anchor source ended before first admitted Paper tick")
                if isinstance(frame,MineflayerPaperSnapshot) and (
                    frame.data["status"]!="ADMITTED" or t2_owner.failed
                ):
                    raise RuntimeError("unadmitted initial T2 Paper source")
            if t2_owner.previous is None or t2_owner.fatigue is None:
                raise RuntimeError("no source-admitted T2 Paper WorldTick")
            executor.bind_t2_owner_dev(t2_owner)
            # The first L1 probe may precede T2's first Paper snapshot.
            # Retake an original native probe AFTER anchor admission, rather
            # than weakening the existing source-order Action guard.
            initial=await _correlated_observe(
                session,f"goal-{sid}-post-paper-anchor-{t2_owner.previous.seq}",
            )
            if initial.seq<=t2_owner.previous.seq:
                raise RuntimeError("first L1 probe not newer than T2 Paper anchor")
            report["l1_t2_reanchored_probe_seq_dev"]=initial.seq
            report["l1_t2_anchor_dev"]={
                "session_id":sid,
                "source_seq":t2_owner.previous.seq,
                "world_tick":t2_owner.previous.data["snapshot"]["world_tick"],
                "status":t2_owner.previous.data["status"],
                "single_original_reader":True,
                "p1_native_gait_attested":False,
                "qualification":False,
            }
        start=initial.snapshot.position
        proposal=L2GoalProposal(
            goal_id="approach-demo",intent_id="goal-navigate",session_id=sid,
            target_x=start.x+goal_turn_dx_dev,target_z=start.z+offset_m,
            purpose=GoalPurpose.APPROACH,
            minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
            danger_interrupt_m=1.5,provenance=source("l2-proposed-fixed-xz"),
        )
        directive=compile_l1_goal_dev(
            proposal,current_x=start.x,current_z=start.z,
            provenance=source("l1-derives-precision-from-distance"),
        )
        forward_x,forward_z,yaw=compute_goal_bearing_dev(
            directive,current_x=start.x,current_z=start.z,
        )
        l0=ObservedGoalL0(
            directive,start_x=start.x,start_z=start.z,
            forward_x=forward_x,forward_z=forward_z,
        )
        if obstacle_wall_dev:
            if goal_turn_dx_dev!=0.0:
                raise RuntimeError("wall requires pinned +Z approach")
            # This is a disposable-world stimulus, NOT a Mineflayer
            # client collision observation. Native motor outcomes decide.
            _command(
                server,
                "execute at RelaySelf run fill "
                "~-1 ~ ~2 ~1 ~2 ~2 minecraft:stone",
            )
            await server.stdin.drain()
            await asyncio.sleep(0.25)
            report["wall_world_stimulus_requested"]=True
            if left_lane_block_dev:
                # World operator creates asymmetry; only the client-cache
                # read below may establish which corridor was observed.
                _command(
                    server,
                    "execute at RelaySelf run fill "
                    "~-3 ~ ~1 ~-2 ~2 ~4 minecraft:stone",
                )
                await server.stdin.drain()
                await asyncio.sleep(0.35)
                report["left_lane_block_world_stimulus_requested"]=True
            if right_lane_block_dev:
                _command(
                    server,
                    "execute at RelaySelf run fill "
                    "~2 ~ ~1 ~3 ~2 ~4 minecraft:stone",
                )
                await server.stdin.drain()
                await asyncio.sleep(0.35)
                report["right_lane_block_world_stimulus_requested"]=True
        report["goal_unit_forward"]={
            "x":forward_x,"z":forward_z,
            "requested_yaw_rad":yaw,
            "look_effect_not_orientation_attestation":True,
        }
        report["goal_l2"]=asdict(proposal)
        report["goal_l1"]=asdict(directive)
        report["initial_native_xz"]={"x":start.x,"z":start.z,"seq":initial.seq}
        report["stage"]="UNATTENDED_L0_GOAL_OBSERVE_ACT"
        g42_pending=None
        for iteration in range(directive.max_observations):
            # Probe, not a new zombie event or fixed tick equivalence, controls
            # each new L0 choice. The single original native reader is reused.
            probe=(
                initial if iteration==0
                else await _correlated_observe(session,f"goal-{sid}-probe-{iteration}")
            )
            if g42_brake_timing_dev and g42_pending is not None:
                # The next original Goal probe is after the prior S16/CLEAR,
                # and before any newly issued motor. This is a drift
                # candidate, not proof of inertia or speed per WorldTick.
                if (
                    probe.session_id!=sid or probe.provenance.source!="mineflayer"
                    or probe.snapshot.nearby_entities_coverage.truncated
                ):
                    raise RuntimeError("G4.2 refuses foreign next native position")
                pos42=probe.snapshot.position
                window42=qualify_g42_native_window_dev(
                    **g42_pending,
                    next_seq=probe.seq,next_x=pos42.x,next_z=pos42.z,
                    next_host_ns=time.perf_counter_ns(),
                )
                report["g42_native_windows_dev"].append(asdict(window42))
                g42_pending=None
            choice=l0.decide(probe)
            report["l0_decisions"].append(asdict(choice))
            if choice.kind is GoalDecisionKind.REACHED:
                report["stage"]="GOAL_REACHED"
                report["final_native_xz"]={
                    "x":choice.x,"z":choice.z,"seq":choice.source_seq,
                    "euclidean_error_m":choice.goal_error_m,
                }
                report["action_count"]=executor._count
                if executor.supervisor.open_actions:
                    raise RuntimeError("goal reached with open native action")
                report["status"]="PASS"
                report["real_world"]=True
                rc=0
                break
            if choice.kind in (GoalDecisionKind.INTERRUPT,GoalDecisionKind.NEEDS_REPLAN):
                report["stage"]=choice.kind.value
                report["last_failure"]=choice.reason
                if obstacle_wall_dev and choice.kind is GoalDecisionKind.NEEDS_REPLAN:
                    if (
                        len(report["native_actions"])<1
                        or not report.get("wall_world_stimulus_requested")
                        or executor.supervisor.open_actions
                    ):
                        raise RuntimeError("wall replan without original native motor")
                    report["wall_handoff"]={
                        "reason":choice.reason,
                        "native_probe_seq":choice.source_seq,
                        "goal_error_m":choice.goal_error_m,
                        "retained_target_x":proposal.target_x,
                        "retained_target_z":proposal.target_z,
                        "original_actions":executor._count,
                        "no_additional_action_issued":True,
                        "client_obstacle_block_detection_attested":False,
                        "upper_layer_replan_executed":False,
                    }
                    report["status"]="PASS"
                    report["real_world"]=True
                    report["classification"]="DEV_ONLY_S49_L0_WALL_REPLAN"
                    rc=0
                if inject_threat_after_first_dev and (
                    choice.kind is GoalDecisionKind.INTERRUPT
                ):
                    threats=[
                        e for e in probe.snapshot.nearby_entities
                        if e.name=="zombie" and e.distance<proposal.danger_interrupt_m
                    ]
                    if (
                        len(threats)!=1 or len(report["native_actions"])!=1
                        or not report.get("hazard_injection_after_first_s16")
                        or executor._count!=1
                        or executor.supervisor.open_actions
                        or probe.session_id!=proposal.session_id
                        or l0.closed is not True
                    ):
                        raise RuntimeError(
                            "real L0 interrupt did not match original S16 hazard source"
                        )
                    report["hazard_injection_after_first_s16"]["native_confirmed"]=True
                    report["goal_handoff"]={
                        "kind":"INTERRUPT",
                        "reason":choice.reason,
                        "goal_id":proposal.goal_id,
                        "intent_id":proposal.intent_id,
                        "session_id":sid,
                        "target_x":proposal.target_x,
                        "target_z":proposal.target_z,
                        "tolerance_m":directive.tolerance_m,
                        "probe_seq":probe.seq,
                        "probe_request_id":probe.request_id,
                        "probe_provenance_source":probe.provenance.source,
                        "observed_current_x":choice.x,
                        "observed_current_z":choice.z,
                        "remaining_goal_error_m":choice.goal_error_m,
                        "threat_entity_id":threats[0].entity_id,
                        "threat_distance_m":threats[0].distance,
                        "native_actions_before_handoff":executor._count,
                        "additional_action_issued_after_interrupt":False,
                        "original_goal_retained_for_upper_layer":True,
                        "upper_layer_replan_executed":False,
                        "owner_open_actions":len(executor.supervisor.open_actions),
                        "L0_goal_following_closed":l0.closed,
                    }
                    report["status"]="PASS"
                    report["real_world"]=True
                    report["classification"]=(
                        "DEV_ONLY_S49_NATIVE_GOAL_REAL_THREAT_INTERRUPTED"
                    )
                    rc=0
                break
            if choice.kind is GoalDecisionKind.WAIT_VERIFY:
                await asyncio.sleep(0.20)
                continue
            assert choice.kind is GoalDecisionKind.MOVE
            i=executor._count+1
            action_id=f"goal-{proposal.goal_id}-step-{i}"
            def grant(stage:NormalActionStage)->NormalActionAuthorization:
                return NormalActionAuthorization(
                    stage=stage,
                    authority_id=f"goal-{stage.value.lower()}-{i}",
                    intent_id=proposal.intent_id,session_id=sid,
                    action_id=action_id,
                    event_seq=probe.seq,probe_seq=probe.seq,
                    entity_id=0,granted=True,
                    provenance=source(f"distinct-{stage.value.lower()}-{i}"),
                )
            # Same original L0 issued Action: only the existing S15 receiver
            # consumes in-flight native probes. The DEV World stimulus is not
            # a sensor or a new Action authority.
            inflight={"native_poll_count":0,"native_threat":None,
                      "applied_ack":None,"clear_ack":None,
                      "injected_after_applied":False}
            async def ack_dev(stage,effect):
                if stage=="APPLIED":
                    inflight["applied_ack"]={
                        "action_id":effect.action_id,"seq":effect.seq,
                        "effect":effect.effect,"result":effect.result,
                    }
                    if effect.action_id!=action_id or effect.result!="applied":
                        raise RuntimeError("cannot inject before actual S15 APPLIED")
                    _command(
                        server,
                        "execute at RelaySelf run summon minecraft:zombie "
                        "~0.65 ~ ~ "
                        "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                    )
                    await server.stdin.drain()
                    inflight["injected_after_applied"]=True
                elif stage=="CLEARED":
                    inflight["clear_ack"]={
                        "action_id":effect.action_id,"seq":effect.seq,
                        "effect":effect.effect,"result":effect.result,
                    }
            def observe_during_action(live):
                inflight["native_poll_count"]+=1
                # Independent native packet source, no forged threat values.
                threats=[
                    e for e in live.snapshot.nearby_entities
                    if e.name=="zombie"
                    and 0<e.distance<proposal.danger_interrupt_m
                ]
                if not threats:
                    return False
                if len(threats)!=1:
                    raise RuntimeError("ambiguous native in-flight hazard")
                interrupted=l0.decide(live)
                if interrupted.kind is not GoalDecisionKind.INTERRUPT:
                    raise RuntimeError("L0 did not preempt own active Action")
                report["l0_decisions"].append(asdict(interrupted))
                inflight["native_threat"]={
                    "probe_seq":live.seq,
                    "probe_request_id":live.request_id,
                    "probe_provenance_source":live.provenance.source,
                    "entity_id":threats[0].entity_id,
                    "distance_m":threats[0].distance,
                    "goal_remaining_m":interrupted.goal_error_m,
                    "current_x":interrupted.x,"current_z":interrupted.z,
                    "kind":interrupted.kind.value,
                }
                return True
            turn_ack={}
            def on_turn_ack(receipt):
                if receipt.effect!="look" or receipt.result!="applied":
                    raise RuntimeError("S15 goal LOOK not independently acknowledged")
                turn_ack.update({
                    "effect":receipt.effect,
                    "result":receipt.result,
                    "seq":receipt.seq,
                    "action_id":receipt.action_id,
                    "requested_yaw_rad":yaw,
                    "signed_yaw_not_measured":True,
                })
            g42_trace={
                "brake_seq":None,"brake_host_ns":None,
                "clear_seq":None,"clear_host_ns":None,
            }
            async def g42_ack_dev(stage,effect):
                expected=(
                    action_id if stage=="APPLIED"
                    else f"{action_id}-s15-clear" if stage=="CLEARED"
                    else None
                )
                if (
                    expected is None or effect.action_id!=expected
                    or effect.session_id!=sid or effect.result!="applied"
                    or (stage=="CLEARED" and effect.effect!="clear_controls")
                    or (stage=="APPLIED" and g42_trace["clear_seq"] is not None)
                ):
                    raise RuntimeError("G4.2 refuses foreign or invalid original ACK")
                if (
                    stage=="APPLIED" and g46_paper_generation_dev
                    and g4_choice is not None and g4_choice.mode=="RUN"
                ):
                    report["g46_original_run_applied_acks_dev"].append({
                        "action_id":action_id,"effect_id":effect.action_id,
                        "ack_seq":effect.seq,"source":"ORIGINAL_S49_NATIVE_APPLIED",
                        "requested_not_paper_gait":True,
                    })
                if (
                    stage=="APPLIED" and g48_direct_action_generation_dev
                    and g4_choice is not None and g4_choice.mode in ("JOG","WALK")
                ):
                    report["g48_original_direct_action_acks_dev"].append({
                        "action_id":action_id,"effect_id":effect.action_id,
                        "effect":effect.effect,"ack_seq":effect.seq,
                        "requested_input_mode":g4_choice.mode,
                        "source":"ORIGINAL_S49_NATIVE_APPLIED",
                        "requested_not_paper_gait":True,
                    })
                if stage=="CLEARED":
                    g42_trace["clear_seq"]=effect.seq
                    g42_trace["clear_host_ns"]=time.perf_counter_ns()
            g41_last_seq=probe.seq
            def g41_inflight_brake(live):
                nonlocal g41_last_seq
                assert g4_choice is not None
                pos=live.snapshot.position
                decision_g41=decide_g41_inflight_brake_dev(
                    directive,action_id=action_id,mode=g4_choice.mode,
                    session_id=live.session_id,source_seq=live.seq,
                    request_id=live.request_id,source=live.provenance.source,
                    x=pos.x,z=pos.z,previous_seq=g41_last_seq,
                    action_start_error_m=choice.goal_error_m,
                    truncated=live.snapshot.nearby_entities_coverage.truncated,
                    danger_present=any(
                        e.name=="zombie"
                        and e.distance<proposal.danger_interrupt_m
                        for e in live.snapshot.nearby_entities
                    ),
                )
                g41_last_seq=live.seq
                report["g41_inflight_samples_dev"].append(asdict(decision_g41))
                if g42_brake_timing_dev and decision_g41.brake_requested:
                    if g42_trace["brake_seq"] is not None:
                        raise RuntimeError("duplicate G4.2 brake within original Action")
                    g42_trace["brake_seq"]=live.seq
                    g42_trace["brake_host_ns"]=time.perf_counter_ns()
                return decision_g41.brake_requested
            g44_last_seq=probe.seq
            g44_pending={}
            g45_threat=None
            g45_injection_done=False
            def g44_transition_probe(live,mode):
                nonlocal g44_last_seq,g45_threat
                pos=live.snapshot.position
                if g45_hazard_during_gait_dev and g45_injection_done:
                    if (
                        live.session_id!=sid
                        or live.provenance.source!="mineflayer"
                        or not live.request_id.startswith(action_id+"-inflight-")
                        or live.seq<=g44_last_seq
                        or live.snapshot.nearby_entities_coverage.truncated
                    ):
                        raise RuntimeError("G4.5 foreign hazard native probe")
                    threats=[
                        e for e in live.snapshot.nearby_entities
                        if e.name=="zombie"
                        and 0<e.distance<proposal.danger_interrupt_m
                    ]
                    if threats:
                        interrupt=l0.decide(live)
                        if len(threats)!=1 or interrupt.kind is not GoalDecisionKind.INTERRUPT:
                            raise RuntimeError("G4.5 native hazard did not cause L0 interrupt")
                        g44_last_seq=live.seq
                        g45_threat={
                            "action_id":action_id,"native_seq":live.seq,
                            "request_id":live.request_id,
                            "native_provenance":live.provenance.source,
                            "entity_id":threats[0].entity_id,
                            "distance_m":threats[0].distance,
                            "gait_phase":mode,
                            "decision":interrupt.kind.value,
                        }
                        report["l0_decisions"].append(asdict(interrupt))
                        return "INTERRUPT"
                decision44=decide_g44_intra_action_gait_dev(
                    directive,action_id=action_id,mode=mode,
                    session_id=live.session_id,source_seq=live.seq,
                    request_id=live.request_id,
                    source=live.provenance.source,
                    previous_seq=g44_last_seq,
                    x=pos.x,z=pos.z,
                    truncated=live.snapshot.nearby_entities_coverage.truncated,
                    danger_present=any(
                        e.name=="zombie"
                        and e.distance<proposal.danger_interrupt_m
                        for e in live.snapshot.nearby_entities
                    ),
                )
                g44_last_seq=live.seq
                report["g44_native_transition_probes_dev"].append(
                    asdict(decision44)
                )
                if decision44.target_mode is not None and (
                    decision44.target_mode!="CLEAR"
                ):
                    g44_pending[decision44.target_mode]=live.seq
                return decision44.target_mode
            async def g44_transition_ack(live,mode,effect):
                nonlocal g45_injection_done
                if (
                    effect.session_id!=sid
                    or effect.action_id!=(
                        f"{action_id}-g44-{1 if mode=='JOG' else 2}-"
                        f"{mode.lower()}"
                    )
                    or effect.effect!="g44_gait_transition_dev"
                    or effect.result!="applied"
                    or effect.seq<=g44_pending.get(mode,live.seq)
                    or g44_pending.get(mode)!=live.seq
                ):
                    raise RuntimeError("G4.4 ACK has no original native probe")
                report["g44_native_transition_acks_dev"].append({
                    "action_id":action_id,
                    "parent_s49_issued_action_id":action_id,
                    "native_probe_seq":live.seq,
                    "transition_effect_id":effect.action_id,
                    "ack_seq":effect.seq,
                    "mode_to":mode,
                    "effect":effect.effect,
                    "applied":True,
                    "world_tick_gait_attested":False,
                })
                if (
                    g45_hazard_during_gait_dev and mode=="JOG"
                    and i==2 and not g45_injection_done
                ):
                    # Physical disposable World stimulus, not forged sensor.
                    # It follows the source-confirmed original RUN->JOG ACK.
                    _command(
                        server,
                        "execute at RelaySelf run summon minecraft:zombie "
                        "~0.65 ~ ~ "
                        "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                    )
                    await server.stdin.drain()
                    g45_injection_done=True
            g4_choice=None
            if g4_auto_gait_dev:
                if t2_owner is None or t2_owner.failed or t2_owner.fatigue is None:
                    raise RuntimeError("G4 missing continuous single T2 P1/M0 owner")
                g4_choice=choose_g4_observed_gait_dev(
                    choice,directive,action_index=i,
                    p1_profile=t2_owner.profile,p1_state=t2_owner.fatigue,
                    m0_energy=t2_owner.energy.body.energy,
                    threats_present=bool(probe.snapshot.nearby_entities),
                )
                if g41_inflight_brake_dev:
                    g4_choice=replace(
                        g4_choice,duration_s=g41_feedback_window_duration_dev(
                            g4_choice.mode,g4_choice.remaining_clearance_m,
                            g4_choice.duration_s,
                        ),
                    )
                report["g4_observed_choices_dev"].append(asdict(g4_choice))
                choice=replace(choice,input_duration_s=g4_choice.duration_s)
            l0.admitted(choice)
            g2_dash_armed=False
            if g2_dash_first_dev and i==1 and (
                not g4_auto_gait_dev or g4_choice.mode=="DASH"
            ):
                # Paper modifier ONLY: the next physical Action still comes
                # from the original S49 owner. No second packet writer.
                offset=server_log.stat().st_size if server_log.exists() else 0
                _command(
                    server,"relays49dasharm "+action_id+" "+sid+" "
                    +offline_uuid("RelaySelf")+" 1.0",
                )
                await server.stdin.drain()
                await _await_dash_dev_line(
                    server_log,offset,marker="ARM",action_id=action_id,
                )
                g2_dash_armed=True
                if g3_single_owner_dev:
                    # This merely bounds *T2 accounting* to the Paper-armed
                    # original S49 Action. It cannot issue or authorize motor.
                    t2_owner.permit_g3_dash_action_dev(action_id)
            try:
                receipt=await executor.execute_goal_step(
                    session,directive=directive,decision=choice,probe=probe,
                propose=grant(NormalActionStage.PROPOSE),
                issue=grant(NormalActionStage.ISSUE),
                g2_sprint_first_dev=g2_sprint_first_dev and executor._count==0,
                g2_sprint_prefix_dev=g2_sprint_prefix_dev and executor._count<3,
                g2_sneak_prefix_dev=g2_sneak_prefix_dev and executor._count<3,
                g4_mode_dev=g4_choice.mode if g4_choice is not None else None,
                on_g41_brake_probe_dev=(
                    g41_inflight_brake if (
                        g41_inflight_brake_dev and g4_choice.mode!="WALK"
                        and not (g44_intra_action_gait_dev
                                 and g4_choice.mode=="RUN")
                    ) else None
                ),
                on_g44_transition_probe_dev=(
                    g44_transition_probe if (
                        g44_intra_action_gait_dev and g4_choice.mode=="RUN"
                    ) else None
                ),
                on_g44_transition_ack_dev=(
                    g44_transition_ack if (
                        g44_intra_action_gait_dev and g4_choice.mode=="RUN"
                    ) else None
                ),
                g45_hazard_preempt_dev=(
                    g45_hazard_during_gait_dev and i==2
                ),
                **({
                    "on_effect_ack_dev":ack_dev,
                    "on_live_probe_dev":observe_during_action,
                } if inject_threat_during_first_dev and i==1 else {
                    "on_effect_ack_dev":g42_ack_dev,
                } if g42_brake_timing_dev else {}),
                    **({
                        "look_yaw_dev":float(yaw),
                        "on_look_ack_dev":on_turn_ack,
                    } if goal_turn_dx_dev!=0.0 or obstacle_wall_dev else {}),
                )
                g42_s16_host_ns=time.perf_counter_ns() if g42_brake_timing_dev else None
            except GoalT2BoundaryRejected:
                # A physically interrupted native S16 has status FAILED,
                # not an OUTCOME or harmless UNKNOWN. Original T2 refuses
                # the handoff and latches; this is the DESIRED safe halt.
                # Verify original refusal provenance rather than minting P1
                # credit or issuing another S49 motor.
                if not (g45_hazard_during_gait_dev and i==2):
                    raise
                boundary45=executor._t2_boundary_dev
                refusal45=boundary45.refusal if boundary45 is not None else None
                if (
                    not g45_injection_done or g45_threat is None
                    or not isinstance(refusal45,dict)
                    or refusal45.get("reason")!="NATIVE_TERMINAL_NOT_SAFE_FOR_T2"
                    or refusal45.get("s49_active_action_id")!=action_id
                    or refusal45.get("terminal_state")!="unknown"
                    or refusal45.get("consequence_status")!="failed"
                    or refusal45.get("clear_ack_effect")!="clear_controls"
                    or refusal45.get("clear_ack_result")!="applied"
                    or refusal45.get("clear_ack_session_matches") is not True
                    or refusal45.get("after_session_matches") is not True
                    or refusal45.get("t2_active_matches") is not True
                    or refusal45.get("p1_credit_awarded") is not False
                    or refusal45.get("additional_action_issued") is not False
                    or type(refusal45.get("clear_ack_seq")) is not int
                    or type(refusal45.get("after_seq")) is not int
                    or not (
                        g45_threat["native_seq"]
                        < refusal45["clear_ack_seq"]
                        < refusal45["after_seq"]
                    )
                    or g42_trace["clear_seq"]!=refusal45["clear_ack_seq"]
                    or not report["g44_native_transition_acks_dev"]
                    or report["g44_native_transition_acks_dev"][-1]["action_id"]!=action_id
                    or report["g44_native_transition_acks_dev"][-1]["mode_to"]!="JOG"
                    or executor._count!=2
                    or executor.supervisor.open_actions
                    or not l0.closed or not t2_owner.failed
                ):
                    raise RuntimeError("G4.5 native threat lacks original fail-closed T2 refusal")
                report["g45_action_clear_acks_dev"].append({
                    "action_id":action_id,
                    "clear_seq":refusal45["clear_ack_seq"],
                    "s16_seq":refusal45["after_seq"],
                    "s16_terminal":"unknown",
                })
                report["g45_native_hazard_preempt_dev"]={
                    **g45_threat,
                    "transition_ack_seq":report["g44_native_transition_acks_dev"][-1]["ack_seq"],
                    "applied_clear_seq":refusal45["clear_ack_seq"],
                    "s16_after_seq":refusal45["after_seq"],
                    "s16_status":"failed",
                    "terminal":"unknown",
                    "t2_expected_refusal":True,
                    "p1_credit_awarded":False,
                    "new_s49_actions_after_hazard":0,
                    "qualified_paper_gait":False,
                }
                report["native_actions"].append({
                    "action_id":action_id,"s16_terminal":"unknown",
                    "s16_status":"failed",
                    "after_seq":refusal45["after_seq"],
                    "g44_same_issued_action_transitions_dev":["JOG"],
                })
                report["stage"]="G45_NATIVE_GAIT_HAZARD_T2_REFUSED"
                report["classification"]="DEV_ONLY_G45_HAZARD_ORIGINAL_S49_T2_FAIL_CLOSED"
                report["status"]="PASS"
                report["real_world"]=True
                rc=0
                break
            finally:
                if g2_dash_armed:
                    # Even UNKNOWN/FAILED native Action must release the
                    # physical Paper bonus. No P1/M0 receipt is minted.
                    offset=server_log.stat().st_size if server_log.exists() else 0
                    _command(
                        server,"relays49dashoff "+action_id+" "+sid+" "
                        +offline_uuid("RelaySelf"),
                    )
                    await server.stdin.drain()
                    window=await _await_dash_dev_line(
                        server_log,offset,marker="COMPLETE",action_id=action_id,
                    )
                    paper_rows=server_log.read_text(encoding="utf-8").splitlines()
                    observed_positive=sum(
                        "S49_DASH_DEV_TICK " in line
                        and "action_id="+action_id+" " in line
                        and "session_id="+sid+" " in line
                        and "modifier_applied=true " in line
                        for line in paper_rows
                    )
                    report["g2_dash_modifier_dev"]={
                        "paper_positive_modifier_callbacks":observed_positive,
                        "action_id":action_id,
                        "released":True,
                        "paper_complete_source_observed":True,
                        "one_shot":True,
                        "m0_extra_posted":False,
                        "p1_gait_posted":False,
                        "native_packet_to_world_tick_attested":False,
                    }
            if g2_sneak_prefix_dev and executor._count<=3:
                dispatch=receipt.consequence.dispatch_receipt
                report["g2_sneak_actions_dev"].append({
                    "action_id":receipt.terminal.action_id,
                    "dispatch_effect":getattr(dispatch,"effect",None),
                    "dispatch_applied":getattr(dispatch,"result",None)=="applied",
                    "terminal_state":receipt.terminal.state.value,
                    "requested_mode_not_physical_proof":True,
                })
            if g2_sprint_prefix_dev and executor._count<=3:
                dispatch=receipt.consequence.dispatch_receipt
                report["g2_sprint_actions_dev"].append({
                    "action_id":receipt.terminal.action_id,
                    "dispatch_effect":getattr(dispatch,"effect",None),
                    "dispatch_applied":getattr(dispatch,"result",None)=="applied",
                    "terminal_state":receipt.terminal.state.value,
                    "requested_mode_not_physical_proof":True,
                })
            if g2_sprint_first_dev and executor._count==1:
                dispatch=receipt.consequence.dispatch_receipt
                report["g2_first_original_motor_dev"]={
                    "action_id":receipt.terminal.action_id,
                    "dispatch_effect":getattr(dispatch,"effect",None),
                    "dispatch_applied":getattr(dispatch,"result",None)=="applied",
                    "terminal_state":receipt.terminal.state.value,
                    "paper_sprint_seen":False,
                    "actual_gait_not_inferred_from_action":True,
                }
            if goal_turn_dx_dev!=0.0 or obstacle_wall_dev:
                if (
                    turn_ack.get("result")!="applied"
                    or turn_ack.get("action_id")!=f"{action_id}-s15-look"
                ):
                    raise RuntimeError("missing S15 native yaw setup ACK")
                report["native_goal_looks"].append(turn_ack)
            if g45_hazard_during_gait_dev and i==2:
                consequence45=receipt.consequence
                after45=consequence45.after_observation
                clear45=consequence45.cleanup_receipt
                if (
                    not g45_injection_done or g45_threat is None
                    or not report["g44_native_transition_acks_dev"]
                    or report["g44_native_transition_acks_dev"][-1]["action_id"]!=action_id
                    or report["g44_native_transition_acks_dev"][-1]["mode_to"]!="JOG"
                    or after45 is None or after45.session_id!=sid
                    or clear45 is None or clear45.result!="applied"
                    or clear45.effect!="clear_controls"
                    or clear45.seq<=g45_threat["native_seq"]
                    or receipt.terminal.state is not ActionState.UNKNOWN
                    or consequence45.status is not WorldConsequenceStatus.FAILED
                    or consequence45.error!="DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED"
                    or executor._count!=2
                    or executor.supervisor.open_actions
                    or l0.closed is not True
                ):
                    raise RuntimeError("G4.5 original in-stage gait hazard stop not proven")
                report["g45_action_clear_acks_dev"].append({
                    "action_id":action_id,"clear_seq":clear45.seq,
                    "s16_seq":after45.seq,"s16_terminal":"unknown",
                })
                report["g45_native_hazard_preempt_dev"]={
                    **g45_threat,
                    "transition_ack_seq":report["g44_native_transition_acks_dev"][-1]["ack_seq"],
                    "applied_clear_seq":clear45.seq,
                    "s16_after_seq":after45.seq,
                    "s16_status":consequence45.status.value,
                    "terminal":receipt.terminal.state.value,
                    "new_s49_actions_after_hazard":0,
                    "qualified_paper_gait":False,
                }
                report["native_actions"].append({
                    "action_id":action_id,"s16_terminal":"unknown",
                    "s16_status":consequence45.status.value,
                    "after_seq":after45.seq,
                    "g44_same_issued_action_transitions_dev":["JOG"],
                })
                report["stage"]="G45_NATIVE_GAIT_HAZARD_INTERRUPTED"
                report["classification"]="DEV_ONLY_G45_NATIVE_HAZARD_CLEARED_S49_UNKNOWN"
                report["status"]="PASS"
                report["real_world"]=True
                rc=0
                break
            if inject_threat_during_first_dev:
                consequence=receipt.consequence
                ended=consequence.after_observation
                interrupt=inflight["native_threat"]
                if (
                    i!=1
                    or not inflight["injected_after_applied"]
                    or inflight["native_poll_count"]<1
                    or interrupt is None
                    or not isinstance(ended,MineflayerObservation)
                    or ended.session_id!=sid
                    or consequence.status is not WorldConsequenceStatus.FAILED
                    or consequence.error!="DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED"
                    or receipt.terminal.state is not ActionState.UNKNOWN
                    or consequence.cleanup_receipt is None
                    or consequence.cleanup_receipt.result!="applied"
                    or inflight["clear_ack"] is None
                    or inflight["clear_ack"]["seq"]<=interrupt["probe_seq"]
                    or executor._count!=1
                    or executor.supervisor.open_actions
                    or l0.closed is not True
                    or len(report["l0_decisions"])!=2
                    or report["l0_decisions"][-1]["kind"]!="INTERRUPT"
                ):
                    raise RuntimeError("in-flight original S49 L0 stop not attested")
                after=ended.snapshot.position
                report["inflight_l0"]={
                    **inflight,
                    "source_first_action_id":action_id,
                    "original_action_terminal":receipt.terminal.state.value,
                    "S16_consequence_status":consequence.status.value,
                    "S16_error":consequence.error,
                    "S16_after_seq":ended.seq,
                    "S16_after_x":after.x,
                    "S16_after_z":after.z,
                    "S16_observed_displacement_m":consequence.movement_distance,
                    "native_clear_receipt_applied":True,
                    "second_action_issued":False,
                    "goal_id":proposal.goal_id,
                    "intent_id":proposal.intent_id,
                    "target_x":proposal.target_x,
                    "target_z":proposal.target_z,
                    "L1_tolerance_m":directive.tolerance_m,
                    "upper_layer_replan_executed":False,
                    "mid_action_preempted_not_execution_success":True,
                }
                report["native_actions"].append({
                    "action_id":action_id,
                    "S15_dispatch_applied":True,
                    "S15_clear_applied":True,
                    "S16_status":consequence.status.value,
                    "terminal":receipt.terminal.state.value,
                    "physical_distance_m":consequence.movement_distance,
                    "terminal_not_outcome":True,
                })
                report["stage"]="INFLIGHT_L0_INTERRUPT"
                report["classification"]="DEV_ONLY_S49_L0_INFLIGHT_NATIVE_PREEMPTED"
                report["status"]="PASS"
                report["real_world"]=True
                rc=0
                break
            if obstacle_wall_dev and (
                receipt.terminal.state is ActionState.UNKNOWN
                or receipt.consequence.status is WorldConsequenceStatus.UNDETERMINED
            ):
                if (
                    receipt.consequence.after_observation is None
                    or receipt.consequence.cleanup_receipt is None
                    or receipt.consequence.cleanup_receipt.result!="applied"
                    or receipt.consequence.dispatch_receipt is None
                    or receipt.consequence.dispatch_receipt.result!="applied"
                    or executor.supervisor.open_actions
                ):
                    raise RuntimeError("wall motor ambiguity lacks CLEAR + S16 source")
                pos=receipt.consequence.after_observation.snapshot.position
                report["native_actions"].append({
                    "action_id":action_id,
                    "s16_status":receipt.consequence.status.value,
                    "s16_terminal":receipt.terminal.state.value,
                    "native_displacement_m":receipt.consequence.movement_distance,
                    "end_x":pos.x,"end_z":pos.z,
                    "uncertain_motor_not_success":True,
                })
                report["wall_handoff"]={
                    "reason":"MOTOR_CONSEQUENCE_UNDETERMINED",
                    "native_after_seq":receipt.consequence.after_observation.seq,
                    "retained_target_x":proposal.target_x,
                    "retained_target_z":proposal.target_z,
                    "original_actions":executor._count,
                    "no_additional_action_issued":True,
                    "client_obstacle_block_detection_attested":False,
                    "upper_layer_replan_executed":False,
                }
                if detour_after_wall_dev:
                    # This is an explicit L1-style OPERATOR-supplied plan,
                    # NOT a native claim that Self perceived a stone block.
                    # A closed original UNKNOWN is never silently retried.
                    if selfworld_memory_snapshot_dev is not None:
                        assert selfworld_memory_catalog_dev is not None
                        present=None
                        if native_route_present_dev:
                            present=await _correlated_native_route_blocks_dev(
                                session,
                                f"goal-{sid}-native-route-after-{receipt.consequence.after_observation.seq}",
                                origin_x=float(start.x),origin_z=float(start.z),
                            )
                            if present.seq<=receipt.consequence.after_observation.seq:
                                raise RuntimeError("native route Present must follow blocked S16")
                            report["native_route_blocks_observation_dev"]={
                                "session_id":present.session_id,
                                "seq":present.seq,
                                "request_id":present.request_id,
                                "origin_x":present.origin_x,
                                "origin_z":present.origin_z,
                                "player_y":present.player_y,
                                "coverage":present.coverage,
                                "samples_per_lane":present.samples_per_lane,
                                "unknown_is_not_clear":present.unknown_is_not_clear,
                                "lanes":[asdict(lane) for lane in present.lanes],
                                "source":"mineflayer",
                            }
                        choice=recall_from_selfworld_dev(
                            selfworld_memory_snapshot_dev,
                            selfworld_memory_catalog_dev,
                            proposal,start_x=float(start.x),
                            start_z=float(start.z),
                            blocked_action_id=receipt.terminal.action_id,
                            blocked_s16_seq=receipt.consequence.after_observation.seq,
                            blocked_reason=report["wall_handoff"]["reason"],
                            blocked_terminal=receipt.terminal.state.value,
                            blocked_consequence=receipt.consequence.status.value,
                            native_route_blocks_dev=present,
                        )
                        report["selfworld_memory_selection_dev"]={
                            "status":choice.status.value,
                            "reason":choice.reason,
                            "matching_successes":choice.matching_successes,
                            "matching_failures":choice.matching_failures,
                            "selected_memory_id":choice.selected_memory_id,
                            "source_ids":list(choice.source_ids),
                            "selfworld_origin":"REMEMBERED",
                            "persistent_owner":"PersistentCognition",
                            "current_world_source_event":
                                receipt.consequence.after_observation.seq,
                            "native_block_geometry_observed":present is not None,
                            "native_block_coverage_attested":(
                                present.coverage if present is not None else None
                            ),
                            "native_block_present_seq":(
                                present.seq if present is not None else None
                            ),
                            "physical_action_authorized_by_memory":False,
                        }
                        if choice.status is L1RecallStatusDev.DEFER:
                            report["classification"]=(
                                "DEV_ONLY_S49_L1_SELFWORLD_MEMORY_DEFER"
                            )
                            report["stage"]="L1_MEMORY_DEFER"
                            report["status"]="PASS"
                            report["real_world"]=True
                            rc=0
                            break
                        if choice.status is not L1RecallStatusDev.SELECTED:
                            raise RuntimeError("memory choice has unsupported status")
                        plan=choice.plan
                    elif native_voxel_map_dev:
                        voxel_source=await _correlated_native_voxels_dev(
                            session,
                            f"goal-{sid}-native-voxels-after-{receipt.consequence.after_observation.seq}",
                            origin_x=float(start.x),origin_z=float(start.z),
                        )
                        if voxel_source.seq<=receipt.consequence.after_observation.seq:
                            raise RuntimeError("stale native voxel map")
                        voxel_present=NativeVoxelPresentDev(
                            session_id=voxel_source.session_id,
                            native_seq=voxel_source.seq,
                            request_id=voxel_source.request_id,
                            origin_x=float(voxel_source.origin_x),
                            origin_z=float(voxel_source.origin_z),
                            player_y=float(voxel_source.player_y),
                            player_x=float(voxel_source.player_x),
                            player_z=float(voxel_source.player_z),
                            coverage=voxel_source.coverage,
                            cells=tuple(VoxelColumnDev(
                                dx=cell.dx,dz=cell.dz,
                                feet=cell.feet,head=cell.head,floor=cell.floor,
                            ) for cell in voxel_source.cells),
                            provenance=voxel_source.provenance,
                        )
                        report["native_local_voxel_observation_dev"]={
                            "session_id":voxel_source.session_id,
                            "seq":voxel_source.seq,
                            "request_id":voxel_source.request_id,
                            "origin_x":voxel_source.origin_x,
                            "origin_z":voxel_source.origin_z,
                            "player_y":voxel_source.player_y,
                            "player_x":voxel_source.player_x,
                            "player_z":voxel_source.player_z,
                            "coverage":voxel_source.coverage,
                            "x_min":voxel_source.x_min,
                            "x_max":voxel_source.x_max,
                            "z_min":voxel_source.z_min,
                            "z_max":voxel_source.z_max,
                            "unknown_is_not_clear":voxel_source.unknown_is_not_clear,
                            "cells":[asdict(cell) for cell in voxel_source.cells],
                            "source":"mineflayer",
                        }
                        if local_grid_search_dev:
                            voxel_choice=choose_grid_route_dev(
                                voxel_present,proposal,
                                blocked_after_seq=receipt.consequence.after_observation.seq,
                                blocked_action_id=receipt.terminal.action_id,
                                provenance=source("l1-native-grid-BFS"),
                            )
                            report["native_grid_search_choice_dev"]={
                                "status":voxel_choice.status,
                                "reason":voxel_choice.reason,
                                "source_seq":voxel_choice.voxel_source_seq,
                                "evaluated_columns":voxel_choice.evaluated_columns,
                                "visited_cells":voxel_choice.visited_cells,
                                "chosen_cell_path":[list(pair) for pair in
                                                    voxel_choice.chosen_cell_path],
                                "no_diagonal_edges":True,
                                "plan_from_current_observation":True,
                                "new_motor_issuer":False,
                            }
                        else:
                            voxel_choice=choose_voxel_waypoint_dev(
                                voxel_present,proposal,
                                blocked_after_seq=receipt.consequence.after_observation.seq,
                                blocked_action_id=receipt.terminal.action_id,
                                provenance=source("l1-observed-local-voxel-waypoints"),
                            )
                            report["native_local_voxel_choice_dev"]={
                                "status":voxel_choice.status,
                                "reason":voxel_choice.reason,
                                "left_state":voxel_choice.left_state,
                                "right_state":voxel_choice.right_state,
                                "selected_side":voxel_choice.selected_side,
                                "source_seq":voxel_choice.source_seq,
                                "sampled_voxel_columns":voxel_choice.sampled_voxel_columns,
                                "plan_from_current_observation":True,
                                "learned_l1":False,
                                "action_authorized_by_map":False,
                            }
                        if voxel_choice.status=="DEFER":
                            report["classification"]=(
                                "DEV_ONLY_S49_L1_GRID_NO_ROUTE_DEFER"
                                if local_grid_search_dev
                                else "DEV_ONLY_S49_L1_VOXEL_DEFER"
                            )
                            report["stage"]=(
                                "L1_GRID_DEFER" if local_grid_search_dev
                                else "L1_VOXEL_DEFER"
                            )
                            report["status"]="PASS"
                            report["real_world"]=True
                            rc=0
                            break
                        if voxel_choice.status!="SELECTED" or voxel_choice.plan is None:
                            raise RuntimeError("no bounded observed grid route")
                        plan=voxel_choice.plan
                    elif experience_memory_dev is None:
                        plan=explicit_l1_detour_dev(
                            proposal,start_x=float(start.x),start_z=float(start.z),
                            blocked_action_id=receipt.terminal.action_id,
                            blocked_s16_seq=receipt.consequence.after_observation.seq,
                            provenance=source("l1-explicit-detour-after-unknown"),
                            lateral_offset_dev=-2.5 if detour_left_dev else 2.5,
                        )
                    else:
                        # RECALL only after a NEW genuine blocked physical S16.
                        # The prior world's actual raw source is digest-bound.
                        assert experience_source_report_dev is not None
                        episode,envelope=load_episode_dev(
                            experience_memory_dev,experience_source_report_dev,
                        )
                        plan=select_route_from_episode_dev(
                            episode,proposal,
                            start_x=float(start.x),start_z=float(start.z),
                            blocked_action_id=receipt.terminal.action_id,
                            blocked_s16_seq=receipt.consequence.after_observation.seq,
                            blocked_reason=report["wall_handoff"]["reason"],
                            blocked_terminal=receipt.terminal.state.value,
                            blocked_consequence=receipt.consequence.status.value,
                            provenance=source("l1-recalled-episode-after-unknown"),
                        )
                        report["experience_selection_dev"]={
                            "source_session_id":episode.source_session_id,
                            "new_session_id":sid,
                            "source_goal_id":episode.source_goal_id,
                            "source_report_sha256":envelope["source_report_sha256"],
                            "source_native_actions":episode.source_native_actions,
                            "selected_route_offsets":[
                                list(row) for row in episode.stages
                            ],
                            "original_blocked_action_id":receipt.terminal.action_id,
                            "original_blocked_s16_seq":
                                receipt.consequence.after_observation.seq,
                            "new_world_goal_x":proposal.target_x,
                            "new_world_goal_z":proposal.target_z,
                            "recalled_plan_stages":[
                                asdict(stage) for stage in plan.stages
                            ],
                            "only_real_prior_episode":True,
                            "learned_general_policy":False,
                            "wall_block_sensed":False,
                        }
                    # Fresh voxel cache is read by the SAME original Mineflayer
                    # owner, after each reached waypoint and closed S16.
                    async def on_grid_refresh(old_plan,stage,closed_id):
                        if not isinstance(old_plan,type(plan)) or (
                            executor.supervisor.open_actions
                            or not stage["actions"]
                            or closed_id!=stage["actions"][-1]["action_id"]
                        ):
                            raise RuntimeError("grid refresh without original Action")
                        if (
                            grid_midroute_obstacle_dev
                            and not report.get("midroute_stone_stimulus_dev")
                        ):
                            # DEV operator alters only physical World state;
                            # native packet must independently observe it.
                            stone_x=math.floor(start.x)+2
                            stone_y=math.floor(start.y)
                            stone_z=math.floor(start.z)+2
                            _command(
                                server,
                                f"setblock {stone_x} {stone_y} {stone_z} minecraft:stone",
                            )
                            await server.stdin.drain()
                            await asyncio.sleep(0.35)
                            report["midroute_stone_stimulus_dev"]={
                                "x":stone_x,"y":stone_y,"z":stone_z,
                                "after_s16_action_id":closed_id,
                                "native_confirmed":False,
                            }
                        last_s16=stage["actions"][-1]["after_seq"]
                        source_packet=await _correlated_native_voxels_dev(
                            session,
                            f"goal-{sid}-grid-refresh-{old_plan.revision}-after-{last_s16}",
                            origin_x=float(start.x),origin_z=float(start.z),
                        )
                        if source_packet.seq<=last_s16:
                            raise RuntimeError("grid refresh not newer than original S16")
                        latest=NativeVoxelPresentDev(
                            session_id=source_packet.session_id,
                            native_seq=source_packet.seq,
                            request_id=source_packet.request_id,
                            origin_x=float(source_packet.origin_x),
                            origin_z=float(source_packet.origin_z),
                            player_y=float(source_packet.player_y),
                            player_x=float(source_packet.player_x),
                            player_z=float(source_packet.player_z),
                            coverage=source_packet.coverage,
                            cells=tuple(VoxelColumnDev(
                                dx=c.dx,dz=c.dz,feet=c.feet,
                                head=c.head,floor=c.floor,
                            ) for c in source_packet.cells),
                            provenance=source_packet.provenance,
                        )
                        report["native_grid_refresh_observations_dev"].append({
                            "after_stage_index":stage["index"],
                            "after_stage_goal_id":stage["goal_id"],
                            "last_s16_after_seq":last_s16,
                            "last_closed_action_id":closed_id,
                            "previous_revision":old_plan.revision,
                            "session_id":source_packet.session_id,
                            "seq":source_packet.seq,
                            "request_id":source_packet.request_id,
                            "origin_x":source_packet.origin_x,
                            "origin_z":source_packet.origin_z,
                            "player_x":source_packet.player_x,
                            "player_z":source_packet.player_z,
                            "player_y":source_packet.player_y,
                            "coverage":source_packet.coverage,
                            "cells":[asdict(c) for c in source_packet.cells],
                        })
                        if grid_midroute_obstacle_dev:
                            block=latest.observed(2,2).value
                            if block is None or block.feet!="BLOCKED":
                                raise RuntimeError("real midroute stone unseen in native grid")
                            report["midroute_stone_stimulus_dev"][
                                "native_confirmed"
                            ]=True
                        return latest
                    report["stage"]="FOLLOW_L1_WAYPOINTS"
                    report["detour"]=await follow_l1_detour_dev(
                        session,executor,plan,
                        first_blocked_action_id=receipt.terminal.action_id,
                        blocked_after_seq=receipt.consequence.after_observation.seq,
                        on_grid_refresh_dev=(
                            on_grid_refresh if grid_refresh_dev else None
                        ),
                    )
                    if report["detour"]["route_status"]=="DEFER":
                        if not grid_refresh_dev or executor.supervisor.open_actions:
                            raise RuntimeError("unexpected grid replan DEFER")
                        report["classification"]=(
                            "DEV_ONLY_S49_L1_GRID_REFRESH_NO_ROUTE_DEFER"
                        )
                        report["stage"]="L1_GRID_REFRESH_DEFER"
                        report["status"]="PASS"
                        report["real_world"]=True
                        rc=0
                        break
                    if (
                        not report["detour"]["reached_final_goal"]
                        or executor.supervisor.open_actions
                        or report["detour"]["final_parent_goal_error_m"]
                           > report["detour"]["stages"][-1]["tolerance_m"]
                    ):
                        raise RuntimeError("native L1 route failed parent L2 goal")
                    report["classification"]=(
                        "DEV_ONLY_S49_L1_NATIVE_GRID_REFRESH_GOAL_REACHED"
                        if grid_refresh_dev
                        else "DEV_ONLY_S49_L1_NATIVE_GRID_GOAL_REACHED"
                        if local_grid_search_dev
                        else "DEV_ONLY_S49_L1_VOXEL_GOAL_REACHED"
                        if native_voxel_map_dev
                        else "DEV_ONLY_S49_L1_SELFWORLD_MEMORY_GOAL_REACHED"
                        if selfworld_memory_snapshot_dev is not None
                        else "DEV_ONLY_S49_L1_EPISODE_REUSED_PARENT_GOAL_REACHED"
                        if experience_memory_dev is not None
                        else "DEV_ONLY_S49_L1_DETOUR_PARENT_GOAL_REACHED"
                    )
                    report["stage"]="L1_DETOUR_ORIGINAL_GOAL_REACHED"
                    report["status"]="PASS"
                    report["real_world"]=True
                    rc=0
                else:
                    report["classification"]="DEV_ONLY_S49_WALL_MOTOR_UNKNOWN_REPLAN"
                    report["stage"]="NEEDS_REPLAN"
                    report["status"]="PASS"
                    report["real_world"]=True
                    rc=0
                break
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.after_observation is None
            ):
                raise RuntimeError("no real original S16 terminal on goal Action")
            end=receipt.consequence.after_observation.snapshot.position
            start_native=receipt.consequence.before_observation.snapshot.position
            travel_x=end.x-start_native.x
            travel_z=end.z-start_native.z
            travel_norm=math.hypot(travel_x,travel_z)
            alignment=(
                (travel_x*forward_x+travel_z*forward_z)/travel_norm
                if travel_norm>0.01 else None
            )
            if g42_brake_timing_dev:
                clear42=receipt.consequence.cleanup_receipt
                after42=receipt.consequence.after_observation
                if (
                    clear42 is None or clear42.result!="applied"
                    or clear42.seq!=g42_trace["clear_seq"]
                    or g42_trace["clear_host_ns"] is None
                    or g42_s16_host_ns is None
                    or after42 is None or after42.session_id!=sid
                ):
                    raise RuntimeError("G4.2 original CLEAR and S16 telemetry mismatch")
                g42_pending={
                    "action_id":action_id,"session_id":sid,
                    "brake_seq":g42_trace["brake_seq"],
                    "brake_host_ns":g42_trace["brake_host_ns"],
                    "clear_seq":clear42.seq,
                    "clear_host_ns":g42_trace["clear_host_ns"],
                    "after_seq":after42.seq,
                    "after_x":end.x,"after_z":end.z,
                    "after_host_ns":g42_s16_host_ns,
                }
            if g45_paper_gait_join_dev:
                clear45=receipt.consequence.cleanup_receipt
                if (
                    clear45 is None or clear45.result!="applied"
                    or clear45.effect!="clear_controls"
                    or clear45.session_id!=sid
                    or clear45.action_id!=f"{action_id}-s15-clear"
                ):
                    raise RuntimeError("G4.5 needs original applied CLEAR source")
                report["g45_action_clear_acks_dev"].append({
                    "action_id":action_id,"clear_seq":clear45.seq,
                    "s16_seq":receipt.consequence.after_observation.seq,
                    "s16_terminal":receipt.terminal.state.value,
                })
            report["native_actions"].append({
                "action_id":receipt.terminal.action_id,
                "s16_status":receipt.consequence.status.value,
                "s16_terminal":receipt.terminal.state.value,
                "before_seq":receipt.consequence.before_observation.seq,
                "after_seq":receipt.consequence.after_observation.seq,
                "duration_s":choice.input_duration_s,
                "end_x":end.x,"end_z":end.z,
                "native_displacement_m":receipt.consequence.movement_distance,
                "native_travel_x":travel_x,
                "native_travel_z":travel_z,
                "native_alignment_to_goal":alignment,
                "goal_error_at_S16_end_m":math.hypot(
                    end.x-proposal.target_x,end.z-proposal.target_z,
                ),
                **({
                    "g4_requested_mode_dev":g4_choice.mode,
                    "g4_native_dispatch_effect_dev":getattr(
                        receipt.consequence.dispatch_receipt,"effect",None),
                    "g4_native_dispatch_applied_dev":getattr(
                        receipt.consequence.dispatch_receipt,"result",None)=="applied",
                    "g4_requested_not_actual_world_gait":True,
                    "g44_same_issued_action_transitions_dev":[
                        a["mode_to"]
                        for a in report["g44_native_transition_acks_dev"]
                        if a["action_id"]==action_id
                    ] if g44_intra_action_gait_dev else [],
                    "g41_brake_observed_dev":any(
                        s["action_id"]==action_id and s["brake_requested"]
                        for s in report["g41_inflight_samples_dev"]
                    ) if g41_inflight_brake_dev else False,
                } if g4_choice is not None else {}),
            })
            if goal_turn_dx_dev!=0.0 and executor._count==1 and (
                alignment is None or alignment<0.72 or abs(travel_x)<0.15
            ):
                raise RuntimeError("real physical XZ did not follow turned yaw")
            if inject_threat_after_first_dev and executor._count==1:
                # DEV operator changes only the physical disposable World.
                # This writes no sensor values. A genuine Mineflayer probe
                # must later witness the entity or the run FAILS, not PASS.
                if executor.supervisor.open_actions:
                    raise RuntimeError("cannot inject before first closed S16")
                _command(
                    server,
                    "execute at RelaySelf run summon minecraft:zombie "
                    "~0.65 ~ ~ "
                    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}",
                )
                await server.stdin.drain()
                report["hazard_injection_after_first_s16"]={
                    "world_command_requested":True,
                    "after_terminal_action_id":receipt.terminal.action_id,
                    "native_confirmed":False,
                }
                await asyncio.sleep(0.50)
            elif g43_passive_tail_control_dev:
                # No motor command may be issued until this sampling block
                # ends. Independent source reads are serialized through the
                # original session. The late period is a *within-action*
                # quiet reference, not a randomized independent control.
                if (
                    executor.supervisor.open_actions
                    or g42_s16_host_ns is None or g42_pending is None
                    or g42_pending["action_id"]!=action_id
                ):
                    raise RuntimeError("G4.3 passive samples need closed original S49")
                quiet=[]
                for sample_i,delay_s in enumerate((0.04,0.08,0.18,0.25,0.25)):
                    await asyncio.sleep(delay_s)
                    expected_request=f"{action_id}-g43-off-{sample_i}"
                    passive=await _correlated_observe(session,expected_request)
                    p=passive.snapshot.position
                    quiet.append(G43PassiveNativeSampleDev(
                        label=("EARLY_40","EARLY_120","MID_300",
                               "QUIET_550","QUIET_800")[sample_i],
                        session_id=passive.session_id,
                        source_seq=passive.seq,
                        request_id=passive.request_id,
                        source=passive.provenance.source,
                        x=p.x,z=p.z,
                        host_ns=time.perf_counter_ns(),
                        entities_truncated=(
                            passive.snapshot.nearby_entities_coverage.truncated
                        ),
                    ))
                passive_tail=qualify_g43_passive_native_tail_dev(
                    action_id=action_id,session_id=sid,
                    clear_seq=g42_pending["clear_seq"],
                    s16_seq=receipt.consequence.after_observation.seq,
                    s16_x=end.x,s16_z=end.z,
                    s16_host_ns=g42_s16_host_ns,
                    samples=tuple(quiet),
                    original_action_closed=(not executor.supervisor.open_actions),
                )
                report["g43_passive_native_tails_dev"].append(
                    asdict(passive_tail)
                )
            else:
                # Existing G4/G4.1/G4.2 path: World may continue after CLEAR.
                await asyncio.sleep(0.20)
        else:
            report["stage"]="OBSERVATION_BUDGET_EXHAUSTED"
    except BaseException as exc:
        report["status"]="FAIL"
        report["exception"]=f"{type(exc).__name__}: {exc}"
    finally:
        if t2_owner is not None and g3_single_owner_dev:
            report["g3_single_t2_p1_m0_owner_dev"]={
                "session_id":sid,
                "original_p1_owner":True,
                "original_m0_owner":True,
                "gait_source":"ORIGINAL_T1U_NODE_PAPER_STABLE_DEV",
                "exact_paper_modifier_identity_required_dev":g3_modifier_identity_dev,
                "single_p1_updates":len(t2_owner.rows),
                "stable_gait_ticks":t2_owner.g3_applied_gait_ticks_dev,
                "undetermined_fallback_ticks":t2_owner.g3_unknown_fallback_ticks_dev,
                "dash_extra_energy_paid":t2_owner.g3_dash_energy_total_dev,
                "paper_armed_original_dash_action_id":t2_owner.g3_dash_approved_action_dev,
                "dash_candidates_suppressed_without_active_s49_scope":(
                    t2_owner.g3_dash_scoped_fallback_ticks_dev
                ),
                "m0_energy_remaining":t2_owner.energy.body.energy,
                "m0_tick":t2_owner.energy.body.tick,
                "gait_R_attested":False,
                "p1_R_qualified":False,
                "dev_partial_source":True,
                "owner_failed":t2_owner.failed,
            }
        if gait_observer is not None:
            rows=[asdict(row) for row in gait_observer.rows]
            file=report_path.parent/"g1_applied_gait_observation_dev.json"
            with file.open("x",encoding="utf-8") as sink:
                json.dump({
                    "source":"ORIGINAL_T1U_PAPER_SNAPSHOT_AND_NODE_APPLIED_CONTROLS",
                    "full_tick_applied_gait_authenticated":False,
                    "p1_transitions_authorized":0,
                    "m0_extra_charge_authorized":0,
                    "rows":rows,
                },sink,sort_keys=True)
                sink.write("\n")
            kinds={}
            for row in gait_observer.rows:
                kinds[row.kind]=kinds.get(row.kind,0)+1
            if "g2_first_original_motor_dev" in report:
                # This is source-derived at the END of the World, never
                # inferred from the initial motor request/ACK. Do not
                # claim individual client packet -> Paper tick correlation.
                sprint_rows=[
                    item for item in gait_observer.rows
                    if item.kind=="STABLE_SPRINT_FORWARD_CANDIDATE"
                ]
                report["g2_first_original_motor_dev"].update({
                    "paper_sprint_seen":bool(sprint_rows),
                    "paper_sprint_candidate_source_seqs":[x.source_seq for x in sprint_rows],
                    "same_packet_paper_tick_attested":False,
                })
            report["g1_applied_gait_observation_dev"]={
                "source_session_id":gait_observer.session_id,
                "source_bound":True,
                "single_original_reader":True,
                "failed":gait_observer.failed,
                "rows":len(rows),
                "kinds":kinds,
                "derived_file":file.name,
                "derived_file_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
                "full_tick_gait_attested":False,
                "p1_transitions_posted":0,
                "m0_extra_charge_posted":0,
            }
        if t2_owner is not None:
            # Derived review material only, written after Actions have ceased.
            # No extra native receive/writer or per-tick sync trace is added.
            ledger_path=report_path.parent/"l1_t2_ledger_dev.json"
            with ledger_path.open("x",encoding="utf-8") as ledger_file:
                json.dump({
                    "source_scope":"SINGLE_ORIGINAL_SESSION_T1F_PAPER_T2_DERIVED_DEV",
                    "independent_native_source_authenticated":False,
                    "exact_gait_attested":False,
                    "rows":t2_owner.rows,
                },ledger_file,sort_keys=True)
                ledger_file.write("\n")
            report["l1_t2_ledger_dev"]={
                "derived_file":ledger_path.name,
                "derived_file_sha256":hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                "wait_dev_rows":sum(x["activity"]=="WAIT_DEV" for x in t2_owner.rows),
                "move_or_unknown_rows":sum(
                    x["activity"]=="MOVE_OR_UNDETERMINED" for x in t2_owner.rows
                ),
                "session_id":t2_owner.session_id,
                "source_admitted":t2_owner.previous is not None,
                "owner_failed":t2_owner.failed,
                "rows":len(t2_owner.rows),
                "source_seq_last":(
                    t2_owner.previous.seq if t2_owner.previous is not None else None
                ),
                "last_paper_world_tick":(
                    t2_owner.previous.data["snapshot"]["world_tick"]
                    if t2_owner.previous is not None else None
                ),
                "original_action_boundary_receipts":(
                    len(executor._t2_boundary_dev.receipts)
                    if session is not None and "executor" in locals()
                    and executor._t2_boundary_dev is not None else 0
                ),
                "continuous_gait_attested":False,
                "qualified_wait_attested":False,
                "one_native_reader":True,
                "s16_refusal_diagnostic_dev":(
                    executor._t2_boundary_dev.refusal
                    if session is not None and "executor" in locals()
                    and executor._t2_boundary_dev is not None else None
                ),
            }
        if g45_paper_gait_join_dev and gait_observer is not None and t2_owner is not None:
            # REVIEW ONLY: derive after the original G1/T2 capture. A join
            # refusal remains FAIL but must not skip session/process cleanup.
            try:
                report["g45_paper_transition_windows_dev"]=[
                    asdict(row) for row in join_g45_native_ack_paper_gait_dev(
                        session_id=sid,
                        transition_acks=report["g44_native_transition_acks_dev"],
                        original_clear_acks=report["g45_action_clear_acks_dev"],
                        paper_rows=[asdict(row) for row in gait_observer.rows],
                        t2_rows=t2_owner.rows,
                    )
                ]
            except ValueError as exc:
                report["g45_join_refusal_dev"]=f"{type(exc).__name__}: {exc}"
                report["status"]="FAIL"
                rc=2
        if g46_paper_generation_dev and gait_observer is not None and t2_owner is not None:
            try:
                report["g46_native_paper_generations_dev"]=[
                    asdict(row) for row in join_g46_control_generation_dev(
                        session_id=sid,
                        original_run_acks=report["g46_original_run_applied_acks_dev"],
                        transition_acks=report["g44_native_transition_acks_dev"],
                        original_clear_acks=report["g45_action_clear_acks_dev"],
                        paper_rows=[asdict(row) for row in gait_observer.rows],
                        t2_rows=t2_owner.rows,
                    )
                ]
            except ValueError as exc:
                report["g46_generation_refusal_dev"]=f"{type(exc).__name__}: {exc}"
                report["status"]="FAIL"
                rc=2
        g47_rows=None
        if g47_original_t2_gait_join_dev and gait_observer is not None and t2_owner is not None:
            try:
                g47_rows=[
                    asdict(row) for row in join_g47_original_t2_worldticks_dev(
                        session_id=sid,
                        original_run_acks=report["g46_original_run_applied_acks_dev"],
                        transition_acks=report["g44_native_transition_acks_dev"],
                        original_clear_acks=report["g45_action_clear_acks_dev"],
                        paper_rows=[asdict(row) for row in gait_observer.rows],
                        t2_rows=t2_owner.rows,
                    )
                ]
                g47_path=report_path.parent/"g47_original_t2_worldtick_gait_audit_dev.json"
                with g47_path.open("x",encoding="utf-8") as sink:
                    json.dump({
                        "source":"SINGLE_ORIGINAL_S49_G46_G1_PAPER_T2_DEV",
                        "original_t2_ledger_sha256":report["l1_t2_ledger_dev"]["derived_file_sha256"],
                        "original_g1_observation_sha256":report["g1_applied_gait_observation_dev"]["derived_file_sha256"],
                        "p1_or_m0_reposted":False,
                        "additional_t2_readers_or_owners":0,
                        "full_tick_R_attested":False,
                        "rows":g47_rows,
                    },sink,sort_keys=True)
                    sink.write("\n")
                statuses={}
                for item in g47_rows:
                    status=item["status"]
                    statuses[status]=statuses.get(status,0)+1
                report["g47_worldtick_gait_audit_dev"]={
                    "source":"SINGLE_ORIGINAL_S49_G46_G1_PAPER_T2_DEV",
                    "derived_file":g47_path.name,
                    "derived_file_sha256":hashlib.sha256(g47_path.read_bytes()).hexdigest(),
                    "original_t2_worldtick_rows":len(g47_rows),
                    "original_t2_ledger_sha256":report["l1_t2_ledger_dev"]["derived_file_sha256"],
                    "source_bound_stable_gait_candidates":statuses.get(
                        "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",0,
                    ),
                    "unknown_worldticks":len(g47_rows)-statuses.get(
                        "SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",0,
                    ),
                    "status_counts":statuses,
                    "p1_or_m0_reposted":False,
                    "additional_t2_readers_or_owners":0,
                    "full_tick_R_attested":False,
                }
            except (ValueError, KeyError, TypeError) as exc:
                report["g47_t2_join_refusal_dev"]=f"{type(exc).__name__}: {exc}"
                report["status"]="FAIL"
                rc=2
        if g48_direct_action_generation_dev and g47_rows is not None:
            try:
                g48_rows=[
                    asdict(row) for row in join_g48_direct_action_worldticks_dev(
                        session_id=sid, g47_rows=g47_rows,
                        direct_acks=report["g48_original_direct_action_acks_dev"],
                        original_clear_acks=report["g45_action_clear_acks_dev"],
                        paper_rows=[asdict(row) for row in gait_observer.rows],
                        t2_rows=t2_owner.rows,
                    )
                ]
                g48_path=report_path.parent/"g48_direct_action_worldtick_audit_dev.json"
                with g48_path.open("x",encoding="utf-8") as sink:
                    json.dump({
                        "source":"SINGLE_ORIGINAL_S49_DIRECT_ACTION_T1U_G1_T2_DEV",
                        "original_g47_sha256":report["g47_worldtick_gait_audit_dev"]["derived_file_sha256"],
                        "original_t2_sha256":report["l1_t2_ledger_dev"]["derived_file_sha256"],
                        "p1_or_m0_reposted":False,
                        "additional_native_readers_or_t2_owners":0,
                        "exact_physics_gait_attested":False,
                        "rows":g48_rows,
                    },sink,sort_keys=True)
                    sink.write("\n")
                statuses={}
                for row in g48_rows:
                    statuses[row["status"]]=statuses.get(row["status"],0)+1
                stable=statuses.get("DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV",0)
                old_stable=sum(
                    row["status"]=="SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
                    for row in g47_rows
                )
                report["g48_direct_worldtick_audit_dev"]={
                    "source":"SINGLE_ORIGINAL_S49_DIRECT_ACTION_T1U_G1_T2_DEV",
                    "derived_file":g48_path.name,
                    "derived_file_sha256":hashlib.sha256(g48_path.read_bytes()).hexdigest(),
                    "original_g47_sha256":report["g47_worldtick_gait_audit_dev"]["derived_file_sha256"],
                    "original_t2_sha256":report["l1_t2_ledger_dev"]["derived_file_sha256"],
                    "original_t2_worldtick_rows":len(g48_rows),
                    "g47_stable_candidates":old_stable,
                    "new_direct_action_stable_candidates":stable,
                    "combined_stable_candidates":stable+old_stable,
                    "combined_unknown_worldticks":len(g48_rows)-stable-old_stable,
                    "status_counts":statuses,
                    "p1_or_m0_reposted":False,
                    "additional_native_readers_or_t2_owners":0,
                    "exact_physics_gait_attested":False,
                }
            except (ValueError, KeyError, TypeError) as exc:
                report["g48_direct_join_refusal_dev"]=f"{type(exc).__name__}: {exc}"
                report["status"]="FAIL"
                rc=2
        report["pre_cleanup_status"]=report["status"]
        await _cleanup_session(
            report,server,collector,session,None,temp,None,None,cleanup_cancel,
        )
        if report.get("node_exit")!=0 or report.get("server_exit")!=0 or any(
            k.endswith("_error") or k.endswith("_unconfirmed")
            for k in report if k.startswith((
                "node_","server_","collector_","temp_"
            ))
        ):
            report["status"]="FAIL"
            rc=2
        _write_final_report(report_path,report)
        print("S49_GOAL_REPORT="+json.dumps(report,sort_keys=True))
    return rc


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--confirm",required=True)
    p.add_argument("--offset-m",type=float,default=2.6)
    p.add_argument("--threat-after-first-dev",action="store_true")
    p.add_argument("--threat-during-first-dev",action="store_true")
    p.add_argument("--goal-turn-dx-dev",type=float,default=0.0)
    p.add_argument("--obstacle-wall-dev",action="store_true")
    p.add_argument("--detour-after-wall-dev",action="store_true")
    p.add_argument("--detour-left-dev",action="store_true")
    p.add_argument("--left-lane-block-dev",action="store_true")
    p.add_argument("--native-route-present-dev",action="store_true")
    p.add_argument("--native-voxel-map-dev",action="store_true")
    p.add_argument("--local-grid-search-dev",action="store_true")
    p.add_argument("--grid-refresh-dev",action="store_true")
    p.add_argument("--grid-midroute-obstacle-dev",action="store_true")
    p.add_argument("--right-lane-block-dev",action="store_true")
    p.add_argument("--paper-jar-dev",type=Path)
    p.add_argument("--paper-plugin-dev",type=Path)
    p.add_argument("--paper-dash-plugin-dev",type=Path)
    p.add_argument("--g2-dash-first-dev",action="store_true")
    p.add_argument("--g3-single-owner-dev",action="store_true")
    p.add_argument("--g3-modifier-identity-dev",action="store_true")
    p.add_argument("--paper-gait-observation-dev",action="store_true")
    p.add_argument("--g2-sprint-first-dev",action="store_true")
    p.add_argument("--g2-sprint-prefix-dev",action="store_true")
    p.add_argument("--g2-sneak-prefix-dev",action="store_true")
    p.add_argument("--g4-auto-gait-dev",action="store_true")
    p.add_argument("--g41-inflight-brake-dev",action="store_true")
    p.add_argument("--g42-brake-timing-dev",action="store_true")
    p.add_argument("--g43-passive-tail-control-dev",action="store_true")
    p.add_argument("--g44-intra-action-gait-dev",action="store_true")
    p.add_argument("--g45-paper-gait-join-dev",action="store_true")
    p.add_argument("--g45-hazard-during-gait-dev",action="store_true")
    p.add_argument("--g46-paper-generation-dev",action="store_true")
    p.add_argument("--g47-original-t2-gait-join-dev",action="store_true")
    p.add_argument("--g48-direct-action-generation-dev",action="store_true")
    p.add_argument("--experience-memory-dev",type=Path)
    p.add_argument("--experience-source-report-dev",type=Path)
    p.add_argument("--selfworld-memory-snapshot-dev",type=Path)
    p.add_argument("--selfworld-memory-catalog-dev",type=Path)
    args=p.parse_args()
    if (
        args.confirm!="S49-GOAL-L0-DEV-DISPOSABLE-WORLD"
        or args.output_dir.exists() or args.output_dir.is_symlink()
    ):
        raise SystemExit("fresh disposable world and explicit DEV confirm required")
    args.output_dir.mkdir(mode=0o700,parents=True)
    return asyncio.run(qualify(
        args.output_dir/"goal_report.json",
        args.output_dir/"minecraft_server.log",offset_m=args.offset_m,
        inject_threat_after_first_dev=args.threat_after_first_dev,
        inject_threat_during_first_dev=args.threat_during_first_dev,
        goal_turn_dx_dev=args.goal_turn_dx_dev,
        obstacle_wall_dev=args.obstacle_wall_dev,
        detour_after_wall_dev=args.detour_after_wall_dev,
        detour_left_dev=args.detour_left_dev,
        left_lane_block_dev=args.left_lane_block_dev,
        native_route_present_dev=args.native_route_present_dev,
        native_voxel_map_dev=args.native_voxel_map_dev,
        local_grid_search_dev=args.local_grid_search_dev,
        grid_refresh_dev=args.grid_refresh_dev,
        grid_midroute_obstacle_dev=args.grid_midroute_obstacle_dev,
        right_lane_block_dev=args.right_lane_block_dev,
        paper_jar_dev=args.paper_jar_dev,
        paper_plugin_dev=args.paper_plugin_dev,
        paper_dash_plugin_dev=args.paper_dash_plugin_dev,
        g2_dash_first_dev=args.g2_dash_first_dev,
        g3_single_owner_dev=args.g3_single_owner_dev,
        g3_modifier_identity_dev=args.g3_modifier_identity_dev,
        paper_gait_observation_dev=args.paper_gait_observation_dev,
        g2_sprint_first_dev=args.g2_sprint_first_dev,
        g2_sprint_prefix_dev=args.g2_sprint_prefix_dev,
        g2_sneak_prefix_dev=args.g2_sneak_prefix_dev,
        g4_auto_gait_dev=args.g4_auto_gait_dev,
        g41_inflight_brake_dev=args.g41_inflight_brake_dev,
        g42_brake_timing_dev=args.g42_brake_timing_dev,
        g43_passive_tail_control_dev=args.g43_passive_tail_control_dev,
        g44_intra_action_gait_dev=args.g44_intra_action_gait_dev,
        g45_paper_gait_join_dev=args.g45_paper_gait_join_dev,
        g45_hazard_during_gait_dev=args.g45_hazard_during_gait_dev,
        g46_paper_generation_dev=args.g46_paper_generation_dev,
        g47_original_t2_gait_join_dev=args.g47_original_t2_gait_join_dev,
        g48_direct_action_generation_dev=args.g48_direct_action_generation_dev,
        experience_memory_dev=args.experience_memory_dev,
        experience_source_report_dev=args.experience_source_report_dev,
        selfworld_memory_snapshot_dev=args.selfworld_memory_snapshot_dev,
        selfworld_memory_catalog_dev=args.selfworld_memory_catalog_dev,
    ))


if __name__=="__main__":
    raise SystemExit(main())
