"""One disposable native Minecraft World: original S49 L0 three true Actions.

No extra controller, reader, fake feedback or Paper/Node synchronous clock.
This is solely a DEV physical test of the previously closed second S16 ->
third original L0 Action -> third S16 loop.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from adapters.mineflayer.s49_normal_session_real_ci import qualify


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--confirm",required=True)
    a=p.parse_args()
    if (a.confirm!="S49-L0-THREE-S16-DEV-WORLD"
        or os.environ.get("S49_REAL_SERVER_CI")!="1"
        or os.environ.get("S49_FORWARD_MOTOR_DEV_ONLY")!="1"
        or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY")!="1"
        or os.environ.get("S49_NEXT_EPOCH_DEV_ONLY")!="1"
        or os.environ.get("S49_L0_OBSERVED_FEEDBACK_DEV_ONLY")!="1"
        or os.environ.get("S49_L0_RESIDUAL_THIRD_DEV_ONLY")!="1"
        or os.environ.get("NODE_OPTIONS")):
        raise RuntimeError("original three S16 DEV owner gates missing")
    if a.output_dir.exists():
        raise RuntimeError("fresh disposable output directory required")
    a.output_dir.mkdir(parents=True,mode=0o700)
    report=a.output_dir/"s49_original_three_action_report.json"
    world=a.output_dir/"original_minecraft_server.log"
    rc=asyncio.run(qualify(
        report, world, dev_forward_motor=True, dev_sprint_motor=True,
        dev_next_epoch="MOVE_AWAY", dev_l0_next_step_m=1.0,
        dev_l0_residual_third_dev=True,
    ))
    if not report.is_file():
        raise RuntimeError("original S49 did not publish terminal report")
    r=json.loads(report.read_text(encoding="utf8"))
    if rc!=0 or r.get("status")!="PASS":
        raise RuntimeError(
            "DEV original S49 failed closed: "+str(r.get("error",r.get("stage")))
        )
    actions=r.get("actual_native_actions")
    second=r.get("dev_l0_observed_feedback")
    third=r.get("dev_l0_residual_third")
    if (
        r.get("classification")!="DEV_ONLY_S49_S16_RESIDUAL_THIRD_ORIGINAL_OWNER"
        or type(actions) is not list or len(actions)!=3
        or type(second) is not dict or type(third) is not dict
        or second.get("second_action_id")!=actions[1]["action"]
        or third.get("second_action_id")!=actions[1]["action"]
        or third.get("third_action_id")!=actions[2]["action"]
        or third.get("third_terminal_state")!="outcome"
        or third.get("same_original_S49_executor") is not True
        or third.get("original_sole_action_issuer") is not True
        or third.get("new_packet_reader") is not False
        or third.get("qualification_go") is not False
        or third.get("science_go") is not False
        or third.get("cross_world_goal_reached_attested") is not False
        or r.get("real_model_calls")!=0
    ):
        raise RuntimeError("third native S16/action owner source mismatch")
    print("S49_L0_THREE_REAL_S16_DEV_PASS",json.dumps({
        "session_id":r["session_id"],
        "first_s16_m":actions[0]["movement_m"],
        "second_s16_m":actions[1]["movement_m"],
        "third_s16_m":actions[2]["movement_m"],
        "second_input_s":second["second_input_duration_s"],
        "third_input_s":third["proposed_duration_s"],
        "target_relative_m":1.0,
        "second_only_error_m":third["original_second_only_error_m"],
        "combined_second_third_m":third["second_plus_third_s16_m"],
        "combined_error_m":third["second_plus_third_error_m"],
        "error_improved_in_this_world":(
            third["second_plus_third_error_m"] <
            third["original_second_only_error_m"]
        ),
        "provenance":"ORIGINAL_S49_NATIVE_THREE_S16_DEV_ONLY",
        "qualification_go":False,"science_go":False,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
