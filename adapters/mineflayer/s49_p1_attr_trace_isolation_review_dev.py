"""Original S49 real-World observer isolation; two model inputs, three modes.

OFF: listener disabled; MEM: listener/sampler enabled, file I/O absent;
FILE: same listener/sampler with one synchronous original CLEAR write.
MEM's internal Node tick count cannot be audited without adding output, so
NEVER infer Node tick count or timing from Paper ticks in OFF or MEM.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.s49_p1_dash_pair_review_dev import _case, compare_p1_pair_dev
from adapters.mineflayer.s49_p1_matched_boost_review_dev import matched_boost_rows_dev
from adapters.mineflayer.s49_speed_attr_boundary_dev import review_speed_attr_boundary_dev

MODES = ("OFF", "MEM", "FILE")
CASES = ("CARRY", "WAIT_ASSUMED")
ARMS = tuple(f"{m}_{c}" for m in MODES for c in CASES)


class P1TraceIsolationRejected(ValueError):
    pass


def _load_one(root: Path, name: str) -> dict:
    mode, case = name.split("_", 1)
    directory = root / name
    if directory.is_symlink() or not directory.is_dir():
        raise P1TraceIsolationRejected("original fresh World missing")
    original = _case(directory, case)  # S15/S16 native evidence & Paper replay.
    report_path = directory / "paper_forward_dash_dev_report.json"
    s49_path = directory / "original_s49_report.json"
    raw_path = directory / "paper_server.log"
    for path in (report_path, s49_path, raw_path):
        if (path.is_symlink() or not path.is_file()
                or path.stat().st_size > 4_000_000):
            raise P1TraceIsolationRejected("untrusted original Source file")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    s49 = json.loads(s49_path.read_text(encoding="utf-8"))
    action = s49["actual_native_actions"][0]["action"]
    sid = s49["session_id"]
    paper = matched_boost_rows_dev(
        raw_path.read_text(encoding="utf-8"), action_id=action, session_id=sid,
    )
    mode_receipt = report.get("p1_trace_ab_dev")
    path = directory / "node_speed_attr_boundary_dev.json"
    if (
        type(mode_receipt) is not dict
        or mode_receipt.get("node_attribute_observer_mode") != mode
        or mode_receipt.get("speed_attribute_projection_enabled") is not True
        or mode_receipt.get("node_attribute_observer_enabled") is not (
            mode != "OFF"
        )
        or mode_receipt.get("node_attribute_trace_file_exists") is not (
            mode == "FILE"
        )
        or mode_receipt.get("sole_original_s49_action_owner_unchanged") is not True
        or mode_receipt.get("native_trace_write_during_first_action") is not False
        or mode_receipt.get("qualification_go") is not False
        or mode_receipt.get("science_go") is not False
        or path.is_symlink() or path.exists() is not (mode == "FILE")
        or paper.get("world") != original.get("paper_world_uuid")
        or paper.get("exact_paper_positive_bonus_ticks") != 7
    ):
        raise P1TraceIsolationRejected("Node observer mode or Paper source mismatch")
    node_ticks = dash_ticks = None
    if mode == "FILE":
        node = review_speed_attr_boundary_dev(
            path, session_id=sid, action_id=action, sync_expected=True,
        )
        if (
            node.get("qualification_go") is not False
            or node.get("no_additional_packet_reader") is not True
        ):
            raise P1TraceIsolationRejected("FILE mode native source invalid")
        node_ticks = node["node_physics_ticks_sampled"]
        dash_ticks = node["node_active_physics_key_dash_seen_count"]
    return {
        "name": name, "mode": mode, "case": case,
        "session_id": sid,
        "world_uuid": original["paper_world_uuid"],
        "first_action_id": action,
        "native_actions": len(s49["actual_native_actions"]),
        "speed_projection_on": True,
        "observer_enabled": mode != "OFF",
        "trace_file_exists": mode == "FILE",
        "paper_positive_ticks": paper["exact_paper_positive_bonus_ticks"],
        "paper_gait_ticks": paper["paper_total_gait_ticks"],
        "mean_paper_positive_speed_mps": paper["matched_positive_speed_mean_mps"],
        "mean_paper_power": sum(paper["matched_positive_power_by_ordinal"]) / 7,
        "first_s16_distance_m": original["first_native_distance_m"],
        "unboosted_second_s16_distance_m": original["second_unboosted_distance_m"],
        "node_observed_physics_ticks": node_ticks,
        "node_observed_positive_attribute_ticks": dash_ticks,
        "genuine_s49_outcomes": True,
        "paper_original_owner_release": True,
        "qualification_go": False, "science_go": False,
    }


def summarize_isolation(arms: dict[str, dict]) -> dict:
    if type(arms) is not dict or set(arms) != set(ARMS):
        raise P1TraceIsolationRejected("must have six fresh real World arms")
    sessions = set()
    worlds = set()
    for name in ARMS:
        a = arms[name]
        mode, case = name.split("_", 1)
        if (
            type(a) is not dict or a.get("mode") != mode or a.get("case") != case
            or a.get("name") != name or not a.get("session_id")
            or not a.get("world_uuid") or not a.get("first_action_id")
            or a.get("native_actions") != 2
            or a.get("speed_projection_on") is not True
            or a.get("observer_enabled") is not (mode != "OFF")
            or a.get("trace_file_exists") is not (mode == "FILE")
            or a.get("paper_positive_ticks") != 7
            or type(a.get("paper_gait_ticks")) is not int
            or not 10 <= a["paper_gait_ticks"] <= 40
            or a.get("genuine_s49_outcomes") is not True
            or a.get("paper_original_owner_release") is not True
            or a.get("qualification_go") is not False
            or a.get("science_go") is not False
        ):
            raise P1TraceIsolationRejected(name + ": original evidence mismatch")
        for key in ("first_s16_distance_m", "mean_paper_positive_speed_mps"):
            value = a.get(key)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise P1TraceIsolationRejected(name + ": bad motor measurement")
        if mode != "FILE":
            if a.get("node_observed_physics_ticks") is not None or a.get(
                "node_observed_positive_attribute_ticks"
            ) is not None:
                raise P1TraceIsolationRejected("invented Node OFF/MEM tick evidence")
        elif (
            type(a.get("node_observed_physics_ticks")) is not int
            or not 3 <= a["node_observed_physics_ticks"] <= 100
            or type(a.get("node_observed_positive_attribute_ticks")) is not int
            or not 0 <= a["node_observed_positive_attribute_ticks"] <= a[
                "node_observed_physics_ticks"
            ]
        ):
            raise P1TraceIsolationRejected("FILE mode tick evidence invalid")
        sessions.add(a["session_id"])
        worlds.add(a["world_uuid"])
    if len(sessions) != len(ARMS) or len(worlds) != len(ARMS):
        raise P1TraceIsolationRejected("reused session or World source")
    deltas = {}
    for case in CASES:
        off, mem, file = (arms[f"{mode}_{case}"] for mode in MODES)
        deltas[case] = {
            "mem_minus_off_s16_m": (
                mem["first_s16_distance_m"] - off["first_s16_distance_m"]
            ),
            "file_minus_mem_s16_m": (
                file["first_s16_distance_m"] - mem["first_s16_distance_m"]
            ),
            "file_minus_off_s16_m": (
                file["first_s16_distance_m"] - off["first_s16_distance_m"]
            ),
            "mem_minus_off_paper_speed_mps": (
                mem["mean_paper_positive_speed_mps"]
                - off["mean_paper_positive_speed_mps"]
            ),
            "file_minus_mem_paper_speed_mps": (
                file["mean_paper_positive_speed_mps"]
                - mem["mean_paper_positive_speed_mps"]
            ),
            "file_minus_off_paper_speed_mps": (
                file["mean_paper_positive_speed_mps"]
                - off["mean_paper_positive_speed_mps"]
            ),
            "phase_matched": False,
            "mem_node_tick_count": None,
            "off_node_tick_count": None,
        }
    return {
        "classification": "P1_NODE_ATTRIBUTE_OBSERVER_OFF_MEMORY_FILE_SIX_WORLD_DEV_ONLY",
        "arms": arms,
        "per_model_differences": deltas,
        "source_verified_all_six_worlds": True,
        "paper_seven_positive_modifier_ticks_all_arms": True,
        "projection_enabled_all_arms": True,
        "MEM_and_FILE_same_sampling_code_path": True,
        "MEM_sync_trace_write_on_CLEAR": False,
        "FILE_sync_trace_write_on_CLEAR": True,
        "OFF_node_sampling_enabled": False,
        "MEM_internal_tick_count_attested": False,
        "OFF_internal_tick_count_attested": False,
        "cross_process_phase_synchronized": False,
        "independent_world_not_within_world_causal_comparison": True,
        "file_write_causally_changes_movement_proven": False,
        "sampling_causally_changes_movement_proven": False,
        "native_action_tick_controlled": False,
        "model_preloaded_not_longitudinal_p1_recovery": True,
        "native_action_issuers_added": 0,
        "native_packet_readers_added": 0,
        "qualification_go": False, "science_go": False,
    }


def review_worlds(root: Path) -> dict:
    if type(root) is not Path or root.is_symlink() or not root.is_dir():
        raise P1TraceIsolationRejected("missing six-World root")
    arms = {name: _load_one(root, name) for name in ARMS}
    # Existing original S49 pair reviewer replays real Paper origin, preloads
    # and exact same start observations within each of three mode cohorts.
    for mode in MODES:
        carry = _case(root / f"{mode}_CARRY", "CARRY")
        wait = _case(root / f"{mode}_WAIT_ASSUMED", "WAIT_ASSUMED")
        compare_p1_pair_dev(carry, wait)
    result = summarize_isolation(arms)
    (root / "p1_node_attr_trace_isolation_dev.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print("P1_NODE_TRACE_OFF_MEM_FILE_DEV", json.dumps(
        review_worlds(args.root), sort_keys=True,
    ))
