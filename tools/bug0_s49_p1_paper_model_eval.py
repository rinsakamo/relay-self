"""DEV P1 virtual Body transitions on native Paper callback-tick candidates.

Uses EXACT original P1 model from separately pinned checkout. The rows come
from ONE live S49 World, not the prior invented ticks 1/2/3. A callback
interval is still NOT independent proof of a full physically inactive tick.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from adapters.mineflayer.s49_p1_paper_dev import inspect_paper_tick_source

P1_EXACT_COMMIT = "0ab76b4e46efd914877e543a65de58b6cfc71326"


def evaluate_source(report: dict, paper_log: str, *, p1_checkout: Path) -> dict:
    if (
        report.get("status") != "PASS"
        or report.get("classification")
            != "DEV_ONLY_S49_PAPER_FIGHT_TICK_AND_REST_CALLBACK_SOURCE"
        or report.get("s49_dev_server") != "PINNED_PAPER_1_21_8"
        or report.get("rest_intent_selected") is not True
        or report.get("p1_paper_source_scope")
            != "DEV_CALLBACK_BOUNDED_NO_R_ATTESTATION"
    ):
        raise ValueError("one original Paper S49 source-bound DEV session required")
    nonce = report["session_id"].replace("-", "")[:20]
    source = inspect_paper_tick_source(paper_log, nonce=nonce, native_report=report)
    checked_head = subprocess.run(
        ["git", "-C", str(p1_checkout), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if checked_head != P1_EXACT_COMMIT:
        raise ValueError("original P1 HEAD is not pinned")
    original = p1_checkout / "experiments" / "fatigue_p1.py"
    if not original.is_file():
        raise ValueError("original P1 module missing")
    p1_source_digest = hashlib.sha256(original.read_bytes()).hexdigest()
    sys.path.insert(0, str(p1_checkout.resolve()))
    from experiments.fatigue_p1 import (
        FatigueFrame,
        FatigueProfile,
        advance,
        initial_state,
    )

    profile = FatigueProfile(enabled=True)
    rows = source["source_tick_rows"]
    fight_index = next(
        i for i, x in enumerate(rows)
        if x["world_tick"] == source["paper_fight_callback_tick"]
    )
    first_tick = rows[fight_index]["world_tick"]
    state = initial_state(
        profile, source["native_session_id"], world_tick=first_tick - 1,
    )
    fatigue_at_rest = None
    recovered_before_rest = 0.0
    recovered_after_rest = 0.0
    evaluated = []
    stopped_reason = None
    for row in rows[fight_index:]:
        counters = row["event_counters"]
        world_tick = row["world_tick"]
        if counters["fight_events"] == 1:
            if (
                counters["move_events"] != 0 or
                row["observed_move_blocks"] != 0 or
                counters["teleport_events"] != 0
            ):
                stopped_reason = "MIXED_FIGHT_AND_MOVE_TICK"
                break
            activity, kw = "FIGHT", {"observed_fight_events": 1}
        elif counters["move_events"] or row["observed_move_blocks"] > 0:
            if (
                counters["swing_events"] or counters["interact_events"]
                or counters["velocity_events"] or counters["teleport_events"]
                or counters["player_damage_events"] or
                row["observed_move_blocks"] > 1.0
            ):
                stopped_reason = "UNCOVERED_MIXED_MOVE_EVENT"
                break
            activity, kw = "MOVE", {
                "observed_blocks": row["observed_move_blocks"],
            }
        elif (
            any(counters.values())
            or row["sprint"] or row["sneak"] or row["swimming"]
        ):
            stopped_reason = "NON_IDLE_CALLBACK_ACTIVITY"
            break
        else:
            activity, kw = "WAIT", {}
        transition = advance(
            profile, state,
            FatigueFrame(source["native_session_id"], world_tick, activity, **kw),
        )
        state = transition.after
        after_rest = world_tick > source["paper_rest_marker_tick"]
        if after_rest:
            recovered_after_rest += transition.recovered
        else:
            recovered_before_rest += transition.recovered
        if world_tick >= source["paper_rest_marker_tick"] and fatigue_at_rest is None:
            fatigue_at_rest = transition.after.fatigue
        if len(evaluated) < 600:
            evaluated.append({
                "source_world_tick": world_tick,
                "activity_from_callback": activity,
                "P1_model_before": transition.before.fatigue,
                "P1_model_after": transition.after.fatigue,
                "P1_model_accumulated": transition.accumulated,
                "P1_model_recovered": transition.recovered,
                "source_type": "PAPER_CALLBACK_INTERVAL_DEV_NOT_FULL_TICK_ATTESTED",
            })
        if world_tick >= source["paper_rest_marker_tick"] + 9:
            break
    fight_steps = [x for x in evaluated if x["activity_from_callback"] == "FIGHT"]
    wait_steps = [x for x in evaluated if x["activity_from_callback"] == "WAIT"]
    # Preserve partial prefixes on any unexpected activity; never invent WAIT.
    if not evaluated or len(fight_steps) != 1:
        raise ValueError("original P1 never received the one Paper FIGHT callback")
    return {
        "classification": "S49_P1_REAL_WORLD_CALLBACK_BOUNDED_VIRTUAL_BODY_DEV",
        "original_p1_commit": checked_head,
        "original_p1_module_sha256": p1_source_digest,
        "original_p1_profile_sha256": profile.sha256,
        "original_s49_session_id": report["session_id"],
        "original_s49_action_id": source["native_attack_action_id"],
        "source_world_uuid": source["paper_world"],
        "source_world_tick_start": source["world_tick_start"],
        "source_fight_event_world_tick": source["paper_fight_event_tick"],
        "source_fight_callback_world_tick": source["paper_fight_callback_tick"],
        "source_rest_intent_world_tick": source["paper_rest_marker_tick"],
        "source_tick_callback_count": source["total_consecutive_source_callback_rows"],
        "model_evaluated_tick_count": len(evaluated),
        "model_stop_reason": stopped_reason,
        "model_fight_steps": len(fight_steps),
        "model_wait_steps": len(wait_steps),
        "model_fatigue_at_rest_intent": fatigue_at_rest,
        "model_fatigue_at_last_candidate_tick": state.fatigue,
        "model_recovery_before_rest_intent": recovered_before_rest,
        "model_recovery_after_rest_intent": recovered_after_rest,
        "model_steps": evaluated,
        "source_stillness_post_rest_eight_callbacks": True,
        "model_from_real_paper_tick_candidates": True,
        "model_tick_time_is_synthetic": False,
        "source_full_tick_activity_independently_attested": False,
        "P1_real_physical_fatigue_sensor_observed": False,
        "P1_real_physical_recovery_independently_attested": False,
        "original_p1_owner_runtime_installed": False,
        "m_basal_cost_waived": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--p1-checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = evaluate_source(
        report, args.paper_log.read_text(encoding="utf-8"),
        p1_checkout=args.p1_checkout,
    )
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print(
        "P1_ORIGINAL_SOURCE_LINKED_DEV_CALLBACK_MODEL"
        + " / FULL_TICK_INDEPENDENT_ATTESTATION_NOT_GRANTED"
    )


if __name__ == "__main__":
    main()
