"""Original P1 exact-commit hypothetical replay for Bug-0 ATTACK->REST.

NOT a World fatigue measurement. The original P1 owner is read from a
separate pinned repository checkout; neither P1 code nor S/R authority is
copied into this product branch. Paper Health loss is NOT a P1 fight tick,
and stationary Mineflayer snapshots are NOT full-tick idle witnesses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

P1_EXACT_COMMIT = "0ab76b4e46efd914877e543a65de58b6cfc71326"


def preview(report: dict, *, p1_checkout: Path) -> dict:
    if (
        report.get("status") != "PASS"
        or report.get("classification") !=
            "DEV_ONLY_S49_ONE_ATTACK_THEN_REST_NATIVE_SAMPLES"
        or report.get("rest_intent_selected") is not True
        or report.get("attack_effect_commands_issued") != 1
        or len(report.get("actual_native_actions", [])) != 1
        or report["actual_native_actions"][0].get("terminal") != "outcome"
        or report.get("attack_server_health_drop_observed") is not True
        or not report.get("rest_observation", {}).get(
            "native_stationary_sample_candidate", False
        )
        or report.get("p1_scope", {}).get("physical_p1_wait_ticks_attested") != 0
        or report.get("p1_scope", {}).get("p1_fatigue_recovery_attested") is not False
        or not isinstance(report.get("session_id"), str)
    ):
        raise ValueError("one complete original native DEV ATTACK->REST source required")

    exact = subprocess.run(
        ["git", "-C", str(p1_checkout), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if exact != P1_EXACT_COMMIT:
        raise ValueError("wrong original P1 owner commit")
    path = p1_checkout / "experiments" / "fatigue_p1.py"
    if not path.is_file():
        raise ValueError("original P1 source unavailable")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    # Only in this separate process. Do not install P1 state into S49 or
    # claim any current World tick is authenticated by this experiment.
    sys.path.insert(0, str(p1_checkout.resolve()))
    from experiments.fatigue_p1 import (
        FatigueFrame, FatigueProfile, advance, initial_state,
    )
    profile = FatigueProfile(enabled=True)
    s0 = initial_state(profile, report["session_id"])
    # These are HYPOTHETICAL model ticks 1,2,3. They are not mapped to
    # Minecraft World ticks and cannot be supplied as physical evidence.
    fight = advance(profile, s0, FatigueFrame(s0.session_id, 1, "FIGHT",
                                              observed_fight_events=1))
    wait1 = advance(profile, fight.after, FatigueFrame(s0.session_id, 2, "WAIT"))
    wait2 = advance(profile, wait1.after, FatigueFrame(s0.session_id, 3, "WAIT"))
    if not (
        fight.accumulated > 0
        and wait1.recovered > 0
        and wait2.after.fatigue == 0
    ):
        raise ValueError("original P1 hypothetical mechanics changed")
    return {
        "status": "ORIGINAL_P1_OFFLINE_HYPOTHETICAL_REPLAY_ONLY",
        "p1_exact_commit": exact,
        "p1_original_source_sha256": digest,
        "p1_profile_sha256": profile.sha256,
        "original_native_session_id": report["session_id"],
        "native_attack_action_id": report["actual_native_actions"][0]["action_id"],
        "native_health_drop_observed": True,
        "native_rest_sample_count": report["rest_observation"]["sample_count"],
        "hypothetical_start_fatigue": s0.fatigue,
        "hypothetical_after_one_fight_event": fight.after.fatigue,
        "hypothetical_after_one_wait_tick": wait1.after.fatigue,
        "hypothetical_after_two_wait_ticks": wait2.after.fatigue,
        "hypothetical_total_recovery": wait1.recovered + wait2.recovered,
        "hypothetical_world_ticks": [1, 2, 3],
        "hypothetical_fight_event_assumed": 1,
        "hypothetical_wait_ticks_assumed": 2,
        "model_tick_source_from_real_world": False,
        "physical_p1_fight_tick_attested": False,
        "physical_p1_wait_ticks_attested": 0,
        "physical_fatigue_before": None,
        "physical_fatigue_after": None,
        "physical_p1_recovery_attested": False,
        "p1_owner_state_installed_in_s49": False,
        "m_basal_cost_waived": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--p1-checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    output = preview(report, p1_checkout=args.p1_checkout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print("P1_ORIGINAL_HYPOTHETICAL_REPLAY_NOT_WORLD_RECOVERY")


if __name__ == "__main__":
    main()
