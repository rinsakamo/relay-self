"""Single original S49 owner executes explicit L1 waypoints after wall UNKNOWN.

Independent dev operator plans a bypass, not a sensor-inferred obstacle.
Every stage retains a distinct immutable subgoal. The original L2 goal
is restored only via the final, predeclared L1 route stage.
"""
from __future__ import annotations

import asyncio
import math
import os
from dataclasses import asdict

from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
)
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
from relay_self.action import ActionState
from relay_self.goal_detour_dev import L1DetourPlanDev
from relay_self.goal_grid_refresh_dev import refresh_grid_route_dev
from relay_self.goal_grid_search_dev import L1GridRoutePlanDev
from relay_self.goal_navigation import (
    GoalDecisionKind,
    ObservedGoalL0,
    compile_l1_goal_dev,
    compute_goal_bearing_dev,
)
from relay_self.provenance import Provenance


class DetourRunRejected(RuntimeError):
    pass


async def follow_l1_detour_dev(
    session, executor:S49GoalExecutorDev,
    plan:L1DetourPlanDev|L1GridRoutePlanDev,
    *, first_blocked_action_id:str, blocked_after_seq:int,
    on_grid_refresh_dev=None,
)->dict:
    if (
        not isinstance(executor,S49GoalExecutorDev)
        or not isinstance(plan,(L1DetourPlanDev,L1GridRoutePlanDev))
        or executor.session_id!=session.started.session_id
        or first_blocked_action_id!=plan.source_action_id
        or blocked_after_seq!=plan.source_s16_seq
        or executor.supervisor.open_actions
        or executor.supervisor.get(first_blocked_action_id).state
           is not ActionState.UNKNOWN
        or (on_grid_refresh_dev is not None and (
            not isinstance(plan,L1GridRoutePlanDev)
            or not callable(on_grid_refresh_dev)
            or os.environ.get("S49_L1_GRID_REFRESH_DEV_ONLY")!="1"
        ))
    ):
        raise DetourRunRejected("source-bound native blocked S16 required")
    result={
        "original_l2_goal_id":plan.parent.goal_id,
        "original_l2_target_x":plan.parent.target_x,
        "original_l2_target_z":plan.parent.target_z,
        "original_wall_action_id":first_blocked_action_id,
        "original_wall_S16_after_seq":blocked_after_seq,
        "l1_detour_plan":asdict(plan),
        "stages":[],"replan_events":[],
        "route_status":"IN_PROGRESS","reached_final_goal":False,
        "learned_l1_attested":False,
        "real_l2_replan_attested":False,
        "obstacle_block_perception_attested":False,
        "extra_action_issuer":False,
        "extra_native_reader":False,
    }
    if isinstance(plan,L1GridRoutePlanDev):
        result["obstacle_block_perception_attested"]=True
    closed_id=first_blocked_action_id
    native_seq=blocked_after_seq
    index=0
    while index<len(plan.stages):
        # Drain input-off world displacement before choosing the next route
        # axis. Never infer the exact latency from the previous S16 scalar.
        await asyncio.sleep(0.22)
        first=await _correlated_observe(
            session,f"{plan.route_id}-stage-{index}-first",
        )
        if first.session_id!=plan.parent.session_id or first.seq<=native_seq:
            raise DetourRunRejected("stale/foreign native waypoint entry")
        executor.adopt_waypoint_dev(
            plan,index,last_closed_action_id=closed_id,
            latest_native_seq=first.seq,
        )
        goal=plan.subgoal(index)
        pos=first.snapshot.position
        directive=compile_l1_goal_dev(
            goal,current_x=pos.x,current_z=pos.z,
            provenance=Provenance(
                "s49-goal-dev-operator",f"l1-stage-{index}-precision",
            ),
        )
        fx,fz,yaw=compute_goal_bearing_dev(
            directive,current_x=pos.x,current_z=pos.z,
        )
        l0=ObservedGoalL0(
            directive,start_x=pos.x,start_z=pos.z,
            forward_x=fx,forward_z=fz,
        )
        stage={
            "index":index,
            "route_revision":plan.revision,
            "stage_id":plan.stages[index].stage_id,
            "goal_id":goal.goal_id,
            "session_id":goal.session_id,
            "target_x":goal.target_x,"target_z":goal.target_z,
            "tolerance_m":directive.tolerance_m,
            "entry_seq":first.seq,"entry_x":pos.x,"entry_z":pos.z,
            "computed_yaw_rad":yaw,"unit_forward_x":fx,"unit_forward_z":fz,
            "actions":[],"decisions":[],"look_acks":[],
            "result":"IN_PROGRESS",
        }
        result["stages"].append(stage)
        for attempt in range(directive.max_observations):
            probe=(
                first if attempt==0
                else await _correlated_observe(
                    session,f"{plan.route_id}-stage-{index}-probe-{attempt}",
                )
            )
            choice=l0.decide(probe)
            stage["decisions"].append(asdict(choice))
            if choice.kind is GoalDecisionKind.REACHED:
                if executor.supervisor.open_actions:
                    raise DetourRunRejected("reached with open original Action")
                if not stage["actions"]:
                    raise DetourRunRejected("no physical movement before reached")
                stage["result"]="REACHED"
                stage["reached_native_seq"]=probe.seq
                stage["reached_x"]=choice.x
                stage["reached_z"]=choice.z
                stage["reached_error_m"]=choice.goal_error_m
                native_seq=probe.seq
                break
            if choice.kind in (GoalDecisionKind.INTERRUPT,GoalDecisionKind.NEEDS_REPLAN):
                stage["result"]=choice.kind.value
                stage["last_reason"]=choice.reason
                raise DetourRunRejected(
                    f"L0 route stage {index} rejected: {choice.reason}"
                )
            if choice.kind is GoalDecisionKind.WAIT_VERIFY:
                await asyncio.sleep(0.20)
                continue
            if choice.kind is not GoalDecisionKind.MOVE:
                raise DetourRunRejected("invalid native L0 waypoint choice")
            count=executor._count+1
            action_id=f"goal-{goal.goal_id}-step-{count}"
            def grant(which:NormalActionStage)->NormalActionAuthorization:
                return NormalActionAuthorization(
                    stage=which,authority_id=(
                        f"l1-route-{plan.revision}-{index}-{which.value}-{count}"
                    ),
                    intent_id=goal.intent_id,session_id=goal.session_id,
                    action_id=action_id,event_seq=probe.seq,
                    probe_seq=probe.seq,entity_id=0,granted=True,
                    provenance=Provenance(
                        "s49-goal-dev-operator",
                        f"route-{index}-{which.value}-{count}",
                    ),
                )
            def look_ack(ack):
                if (
                    ack.action_id!=f"{action_id}-s15-look"
                    or ack.effect!="look" or ack.result!="applied"
                    or ack.session_id!=goal.session_id
                ):
                    raise DetourRunRejected("native LOOK lineage mismatch")
                stage["look_acks"].append({
                    "action_id":ack.action_id,"seq":ack.seq,
                    "result":ack.result,"effect":ack.effect,
                })
            l0.admitted(choice)
            receipt=await executor.execute_goal_step(
                session,directive=directive,decision=choice,probe=probe,
                propose=grant(NormalActionStage.PROPOSE),
                issue=grant(NormalActionStage.ISSUE),
                look_yaw_dev=float(yaw),on_look_ack_dev=look_ack,
            )
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status.value!="executed"
                or receipt.consequence.cleanup_receipt is None
                or receipt.consequence.cleanup_receipt.result!="applied"
                or receipt.consequence.after_observation is None
                or receipt.consequence.before_observation is None
                or not stage["look_acks"]
                or executor.supervisor.open_actions
            ):
                raise DetourRunRejected(
                    f"route stage {index} missing genuine closed S16 outcome"
                )
            end=receipt.consequence.after_observation.snapshot.position
            before=receipt.consequence.before_observation.snapshot.position
            if (
                receipt.consequence.after_observation.session_id!=goal.session_id
                or receipt.consequence.after_observation.seq
                    <=receipt.consequence.before_observation.seq
            ):
                raise DetourRunRejected("foreign/stale native waypoint S16")
            stage["actions"].append({
                "action_id":action_id,
                "terminal":receipt.terminal.state.value,
                "S16_status":receipt.consequence.status.value,
                "before_seq":receipt.consequence.before_observation.seq,
                "after_seq":receipt.consequence.after_observation.seq,
                "before_x":before.x,"before_z":before.z,
                "after_x":end.x,"after_z":end.z,
                "native_displacement_m":receipt.consequence.movement_distance,
                "distance_to_stage_target_m":math.hypot(
                    end.x-goal.target_x,end.z-goal.target_z,
                ),
                "input_duration_s":choice.input_duration_s,
            })
            closed_id=action_id
            await asyncio.sleep(0.20)
        else:
            raise DetourRunRejected(
                f"waypoint {index} observation budget exceeded"
            )
        if stage["result"]!="REACHED":
            raise DetourRunRejected("no stable native waypoint arrival")
        if on_grid_refresh_dev is not None and index<len(plan.stages)-1:
            if not stage["actions"] or executor.supervisor.open_actions:
                raise DetourRunRejected("grid refresh without settled closed Action")
            last_s16=stage["actions"][-1]["after_seq"]
            fresh=await on_grid_refresh_dev(plan,stage,closed_id)
            decision=refresh_grid_route_dev(
                fresh,plan,last_s16_after_seq=last_s16,
                last_closed_action_id=closed_id,
                provenance=Provenance(
                    "s49-goal-dev-operator",f"grid-refresh-{plan.revision+1}",
                ),
            )
            event={
                "previous_revision":plan.revision,
                "last_closed_action_id":closed_id,
                "last_s16_after_seq":last_s16,
                "fresh_voxel_seq":fresh.native_seq,
                "fresh_voxel_request_id":fresh.request_id,
                "status":decision.status,"reason":decision.reason,
                "chosen_cell_path":[list(cell) for cell in decision.chosen_cell_path],
                "new_revision":(
                    decision.plan.revision if decision.plan is not None else None
                ),
                "no_extra_action_issuer":True,
            }
            result["replan_events"].append(event)
            if decision.status=="DEFER":
                result["route_status"]="DEFER"
                result["defer_reason"]=decision.reason
                result["last_s16_action_id"]=closed_id
                result["total_route_native_actions"]=sum(
                    len(s["actions"]) for s in result["stages"]
                )
                return result
            if decision.status!="SELECTED" or decision.plan is None:
                raise DetourRunRejected("invalid native grid refresh")
            plan=decision.plan
            index=0
        else:
            index+=1
    last=result["stages"][-1]
    if (
        not math.isclose(last["target_x"],plan.parent.target_x,abs_tol=1e-9)
        or not math.isclose(last["target_z"],plan.parent.target_z,abs_tol=1e-9)
        or last["reached_error_m"]>last["tolerance_m"]
    ):
        raise DetourRunRejected("final native position not parent Goal")
    result["reached_final_goal"]=True
    result["route_status"]="REACHED"
    result["total_route_native_actions"]=sum(
        len(s["actions"]) for s in result["stages"]
    )
    result["final_parent_goal_error_m"]=last["reached_error_m"]
    result["final_parent_goal_x"]=last["reached_x"]
    result["final_parent_goal_z"]=last["reached_z"]
    result["last_s16_action_id"]=closed_id
    return result
