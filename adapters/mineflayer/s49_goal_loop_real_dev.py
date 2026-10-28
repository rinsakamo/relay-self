"""One real Minecraft DEV World: L2/L1 goal, autonomous L0 XZ loop.

The goal is provided by an explicit DEV operator acting as L2/L1 inputs,
not a live LLM or learned L1. L0 triggers on native probes WITHOUT zombies.
The same inherited S49 ActionSupervisor owns each real S15/S16 transaction.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionAuthorization, NormalActionStage
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
from adapters.mineflayer.s49_goal_waypoint_route_dev import follow_l1_detour_dev
from adapters.mineflayer.s49_normal_session_real_ci import (
    _cleanup_session,
    _write_final_report,
)
from relay_self.action import ActionState
from relay_self.goal_detour_dev import explicit_l1_detour_dev
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


def source(tag:str)->Provenance:
    return Provenance("s49-goal-dev-operator",tag)


async def qualify(
    report_path:Path, server_log:Path, *, offset_m:float=2.6,
    inject_threat_after_first_dev:bool=False,
    inject_threat_during_first_dev:bool=False,
    goal_turn_dx_dev:float=0.0,
    obstacle_wall_dev:bool=False,
    detour_after_wall_dev:bool=False,
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
        "detour_after_wall_dev":detour_after_wall_dev,
        "native_goal_looks":[],
    }
    server=collector=session=temp=None
    cleanup_cancel=[]
    rc=2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI")!="1"
            or os.environ.get("S49_L0_GOAL_LOOP_DEV_ONLY")!="1"
            or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY")!="1"
            or os.environ.get("NODE_OPTIONS")
            or type(offset_m) is not float or not 1.8<=offset_m<=4.0
            or type(inject_threat_during_first_dev) is not bool
            or (inject_threat_during_first_dev and (
                inject_threat_after_first_dev
                or os.environ.get("S49_L0_INFLIGHT_PREEMPT_DEV_ONLY")!="1"
            ))
            or type(goal_turn_dx_dev) is not float
            or not math.isfinite(goal_turn_dx_dev)
            or goal_turn_dx_dev not in (0.0, 1.4)
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
        report.update(await asyncio.to_thread(_fetch_official_server,root/"minecraft.jar"))
        _write_config(root)
        report["stage"]="SERVER_START"
        server,collector,_=await _ready_server(root,root/"minecraft.jar",server_log)
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
        # Single native probe anchors a DEV L2 target at a fixed World XZ.
        initial=await _correlated_observe(session,f"goal-{sid}-initial")
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
        report["goal_unit_forward"]={
            "x":forward_x,"z":forward_z,
            "requested_yaw_rad":yaw,
            "look_effect_not_orientation_attestation":True,
        }
        report["goal_l2"]=asdict(proposal)
        report["goal_l1"]=asdict(directive)
        report["initial_native_xz"]={"x":start.x,"z":start.z,"seq":initial.seq}
        report["stage"]="UNATTENDED_L0_GOAL_OBSERVE_ACT"
        for iteration in range(directive.max_observations):
            # Probe, not a new zombie event or fixed tick equivalence, controls
            # each new L0 choice. The single original native reader is reused.
            probe=(
                initial if iteration==0
                else await _correlated_observe(session,f"goal-{sid}-probe-{iteration}")
            )
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
            l0.admitted(choice)
            receipt=await executor.execute_goal_step(
                session,directive=directive,decision=choice,probe=probe,
                propose=grant(NormalActionStage.PROPOSE),
                issue=grant(NormalActionStage.ISSUE),
                **({
                    "on_effect_ack_dev":ack_dev,
                    "on_live_probe_dev":observe_during_action,
                } if inject_threat_during_first_dev and i==1 else {}),
                **({
                    "look_yaw_dev":float(yaw),
                    "on_look_ack_dev":on_turn_ack,
                } if goal_turn_dx_dev!=0.0 or obstacle_wall_dev else {}),
            )
            if goal_turn_dx_dev!=0.0 or obstacle_wall_dev:
                if (
                    turn_ack.get("result")!="applied"
                    or turn_ack.get("action_id")!=f"{action_id}-s15-look"
                ):
                    raise RuntimeError("missing S15 native yaw setup ACK")
                report["native_goal_looks"].append(turn_ack)
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
                    plan=explicit_l1_detour_dev(
                        proposal,start_x=float(start.x),start_z=float(start.z),
                        blocked_action_id=receipt.terminal.action_id,
                        blocked_s16_seq=receipt.consequence.after_observation.seq,
                        provenance=source("l1-explicit-detour-after-unknown"),
                    )
                    report["stage"]="FOLLOW_L1_WAYPOINTS"
                    report["detour"]=await follow_l1_detour_dev(
                        session,executor,plan,
                        first_blocked_action_id=receipt.terminal.action_id,
                        blocked_after_seq=receipt.consequence.after_observation.seq,
                    )
                    if (
                        not report["detour"]["reached_final_goal"]
                        or executor.supervisor.open_actions
                        or report["detour"]["final_parent_goal_error_m"]
                           > report["detour"]["stages"][-1]["tolerance_m"]
                    ):
                        raise RuntimeError("native L1 route failed parent L2 goal")
                    report["classification"]="DEV_ONLY_S49_L1_DETOUR_PARENT_GOAL_REACHED"
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
            else:
                # World can keep moving after S16/CLEAR. Sample again.
                await asyncio.sleep(0.20)
        else:
            report["stage"]="OBSERVATION_BUDGET_EXHAUSTED"
    except BaseException as exc:
        report["status"]="FAIL"
        report["exception"]=f"{type(exc).__name__}: {exc}"
    finally:
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
    ))


if __name__=="__main__":
    raise SystemExit(main())
