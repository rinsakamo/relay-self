"""Four independent Paper superflat DEV foraging arms; never V8 SCIENCE.

Uses the frozen seed=63101 stopped original World, copies it per arm,
reuses existing S50/S51 action owners via base.arm_run, and retains failures.
BASE_ON was already executed and is not repeated by this launcher.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from adapters.mineflayer.m02_paper_dev import s50_flat_base_foraging_dev as base
from adapters.mineflayer.m02_paper_dev.v7_paired_config import ARMS
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import (
    need,
    sha,
    world_index,
)

ARMS_TO_RUN = ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
CONFIRM = "S50-FLAT-FOUR-WORLD-DEV-ONLY"
CLASS = "S50_FLAT_FOUR_INDEPENDENT_FORAGE_DEV_ONLY_NOT_QUALIFIED"
BASE_ON_HISTORICAL_RUN = 38990613628


def preflight(args: argparse.Namespace) -> list[dict]:
    need(args.confirm == CONFIRM, "explicit four-arm FLAT DEV consent required")
    need(set(ARMS_TO_RUN) == set(ARMS) - {"BASE_ON"},
         "only the four remaining metabolic profiles may run")
    for path in (args.archive, args.paper_jar, args.plugin_jar, args.output):
        need(path.is_absolute() and ".." not in path.parts
             and not path.is_symlink()
             and not any(parent.is_symlink() for parent in path.parents),
             "absolute non-aliased paths without symlinks required")
    return base.preflight(
        args.archive, args.paper_jar, args.plugin_jar,
        args.plugin_sha256, args.output, base.CONFIRM,
    )


def summarize(
    reports: list[dict], original_source: Path, expected: list[dict]
) -> dict:
    arms_seen = [r["arm"] for r in reports]
    need(arms_seen == list(ARMS_TO_RUN[: len(arms_seen)]),
         "arm order or per-arm identity invalid")
    unchanged = world_index(original_source) == expected
    need(unchanged, "original stopped FLAT World mutated")
    entries = {}
    for r in reports:
        arm = r["arm"]
        native = r.get("initial_server_marker") or {}
        trace = r.get("foraging") or {}
        pickup = trace.get("pickup") or {}
        need(not native or native.get("seed") == "63101",
             "unexpected native World seed in a FLAT arm")
        need(r.get("basal_multiplier", ARMS[arm][0]) == ARMS[arm][0]
             and r.get("walk_multiplier", ARMS[arm][1]) == ARMS[arm][1],
             "metabolism arm configuration mismatch")
        entries[arm] = {
            "behavioral_status": r.get("status"),
            "foraging_status": trace.get("status"),
            "move_outcomes": len(trace.get("movement_outcomes", [])),
            "pickup_inventory_delta": pickup.get("cooked_beef_inventory_delta"),
            "S51_eat_recorded": r.get("eating") is not None,
            "cleanup_complete": r.get("cleanup_complete") is True,
            "native_initial_pose": [native.get(k) for k in
                                    ("x", "y", "z", "yaw", "pitch")]
                                   if native else None,
            "native_initial_full_time": native.get("full_time"),
            "native_initial_seed": native.get("seed"),
            "basal_multiplier": r.get("basal_multiplier"),
            "walk_multiplier": r.get("walk_multiplier"),
            "config_sha256": r.get("config_sha256"),
            "metabolism_source": r.get("metabolism_source"),
            "terminal_native_marker": r.get("terminal_server_marker"),
            "error": r.get("error"),
            "java_launch_attempts": r.get("java_launch_attempts", 0),
            "node_launch_attempts": r.get("node_launch_attempts", 0),
        }
    poses = [v["native_initial_pose"] for v in entries.values()]
    times = [v["native_initial_full_time"] for v in entries.values()]
    all_started = len(reports) == len(ARMS_TO_RUN)
    return {
        "classification": CLASS,
        "mode": "FLAT_DEV_ONLY",
        "arm_order": list(ARMS_TO_RUN),
        "arms": entries,
        "not_run": list(ARMS_TO_RUN[len(reports):]),
        "all_four_executed": all_started,
        "all_four_behavioral_pass": all_started and all(
            v["behavioral_status"] == "PASS" and
            v["foraging_status"] == "PICKUP_SOURCE_CONSISTENT" and
            v["S51_eat_recorded"] for v in entries.values()
        ),
        "same_initial_native_pose": all_started and all(p is not None for p in poses)
                                     and all(p == poses[0] for p in poses),
        "same_initial_native_full_time": all_started and all(t is not None for t in times)
                                          and all(t == times[0] for t in times),
        "original_stopped_world_unchanged": unchanged,
        "historical_base_on_run_not_reexecuted": BASE_ON_HISTORICAL_RUN,
        "operator_staged_food": True,
        "strict_player_collect_causality": "UNKNOWN",
        "r_independent_audit": "PENDING",
        "retries": 0,
        "science_trials": 0,
        "engineering_qualified": False,
        "science_go": False,
        "production_go": False,
    }


async def run(args: argparse.Namespace) -> int:
    expected = preflight(args)
    args.output.mkdir(mode=0o700)
    reports = []
    for arm in ARMS_TO_RUN:
        need(base.owner._port_free(), "previous/foreign listener still active")
        # Existing base.arm_run does the full S50/S51 native issue/outcome/STOP;
        # each arm creates a fresh copy from the same immutable source.
        try:
            result = await base.arm_run(
                args.archive, args.output, arm,
                args.paper_jar, args.plugin_jar, expected,
            )
        except Exception as exc:
            # A lifecycle/evidence exception must never permit another Java.
            result = {"arm": arm, "status": "FAIL", "cleanup_complete": False,
                      "error": f"{type(exc).__name__}: {exc}"}
            base.write(args.output / (arm + "-launcher-error.json"), result)
        reports.append(result)
        if not result.get("cleanup_complete") or not base.owner._port_free():
            # Do not start another World on uncertain host cleanup.
            break
    summary = summarize(reports, args.archive / base.FLAT_SOURCE, expected)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    # Hash every retained file, including Paper/remapped plugin and caches
    # omitted from the historical per-arm bounded source index.
    saved = {str(p.relative_to(args.output)): sha(p)
             for p in sorted(args.output.rglob("*")) if p.is_file()}
    base.write(args.output / "saved_files_sha256.json", saved)
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    # Behavioral failures remain original DEV evidence, not a retry trigger.
    return 0 if summary["all_four_executed"] and all(
        a["cleanup_complete"] for a in summary["arms"].values()
    ) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("archive", "paper-jar", "plugin-jar", "output"):
        parser.add_argument("--" + field, required=True, type=Path)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--confirm", required=True)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
