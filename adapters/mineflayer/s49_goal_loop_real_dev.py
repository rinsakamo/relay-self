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
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _fetch_official_server,
    _ready_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
from adapters.mineflayer.s49_normal_session_real_ci import (
    _cleanup_session,
    _write_final_report,
)
from relay_self.action import ActionState
from relay_self.goal_navigation import (
    GoalDecisionKind,
    GoalPurpose,
    L2GoalProposal,
    ObservedGoalL0,
    compile_l1_goal_dev,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def source(tag:str)->Provenance:
    return Provenance("s49-goal-dev-operator",tag)


async def qualify(report_path:Path, server_log:Path, *, offset_m:float=2.6)->int:
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
            target_x=start.x,target_z=start.z+offset_m,
            purpose=GoalPurpose.APPROACH,
            minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
            danger_interrupt_m=1.5,provenance=source("l2-proposed-fixed-xz"),
        )
        directive=compile_l1_goal_dev(
            proposal,current_x=start.x,current_z=start.z,
            provenance=source("l1-derives-precision-from-distance"),
        )
        l0=ObservedGoalL0(directive,start_x=start.x,start_z=start.z)
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
            # A single original L0 owner decides, then grants are checked
            # independently by the existing ActionSupervisor's GOAL DEV seam.
            l0.admitted(choice)
            receipt=await executor.execute_goal_step(
                session,directive=directive,decision=choice,probe=probe,
                propose=grant(NormalActionStage.PROPOSE),
                issue=grant(NormalActionStage.ISSUE),
            )
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                or receipt.consequence.after_observation is None
            ):
                raise RuntimeError("no real original S16 terminal on goal Action")
            end=receipt.consequence.after_observation.snapshot.position
            report["native_actions"].append({
                "action_id":receipt.terminal.action_id,
                "s16_status":receipt.consequence.status.value,
                "s16_terminal":receipt.terminal.state.value,
                "before_seq":receipt.consequence.before_observation.seq,
                "after_seq":receipt.consequence.after_observation.seq,
                "duration_s":choice.input_duration_s,
                "end_x":end.x,"end_z":end.z,
                "native_displacement_m":receipt.consequence.movement_distance,
                "goal_error_at_S16_end_m":math.hypot(
                    end.x-proposal.target_x,end.z-proposal.target_z,
                ),
            })
            # The World may keep moving after S16/clear. Sample again.
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
    ))


if __name__=="__main__":
    raise SystemExit(main())
