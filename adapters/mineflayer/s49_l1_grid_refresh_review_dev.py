"""Independent fixed-source review of native waypoint grid refresh DEV Worlds.

Reconstruct every revision from recorded new native voxel packet and the
original physically blocked S16. This does NOT certify continuous trajectory
safety, fast in-flight preemption, dynamic entities, or SCIENCE validity.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from adapters.mineflayer.s49_l1_native_grid_review_dev import _read, _rebuild
from relay_self.goal_grid_refresh_dev import refresh_grid_route_dev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.provenance import Provenance


class GridRefreshAuditRejected(ValueError):
    pass


def review_grid_refresh_worlds_dev(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise GridRefreshAuditRejected("original independent World reports required")
    worlds = ("UNCHANGED", "MIDROUTE_BLOCKED")
    reports = {name: _read(root, name) for name in worlds}
    if len({r["session_id"] for r in reports.values()}) != len(worlds):
        raise GridRefreshAuditRejected("reused native Minecraft session")
    summaries = {}
    for name, report in reports.items():
        initial = _rebuild(report)
        prior = initial.plan
        trace = report.get("native_grid_refresh_observations_dev")
        route = report.get("detour")
        if (
            prior is None or not isinstance(route, dict)
            or report.get("grid_refresh_dev") is not True
            or report.get("grid_midroute_obstacle_dev") is not (
                name == "MIDROUTE_BLOCKED"
            )
            or route.get("route_status") != "REACHED"
            or route.get("reached_final_goal") is not True
            or report.get("classification")
               != "DEV_ONLY_S49_L1_NATIVE_GRID_REFRESH_GOAL_REACHED"
            or not isinstance(trace, list) or not trace
            or len(trace) != len(route.get("replan_events", []))
        ):
            raise GridRefreshAuditRejected("no genuine closed original L1 route refresh")
        source_ids = [a["action_id"] for a in report["native_actions"]]
        stage_actions = []
        for stage in route["stages"]:
            if (
                stage["result"] != "REACHED"
                or not stage["actions"]
                or len(stage["look_acks"]) != len(stage["actions"])
                or stage["reached_error_m"] > stage["tolerance_m"]
                or any(a["terminal"] != "outcome" or a["S16_status"] != "executed"
                       or a["after_seq"] <= a["before_seq"]
                       for a in stage["actions"])
            ):
                raise GridRefreshAuditRejected("stage not settled by native S16")
            stage_actions.extend(a["action_id"] for a in stage["actions"])
        all_ids = source_ids + stage_actions
        if len(all_ids) != len(set(all_ids)):
            raise GridRefreshAuditRejected("original Action ID was reissued")
        first_path = None
        for native, event in zip(trace, route["replan_events"]):
            if (
                native["session_id"] != report["session_id"]
                or native["seq"] != event["fresh_voxel_seq"]
                or native["request_id"] != event["fresh_voxel_request_id"]
                or native["last_s16_after_seq"] != event["last_s16_after_seq"]
                or native["last_closed_action_id"] != event["last_closed_action_id"]
                or native["seq"] <= native["last_s16_after_seq"]
                or native["previous_revision"] != prior.revision
                or event["previous_revision"] != prior.revision
                or event["last_closed_action_id"] not in stage_actions
                or len(native["cells"]) != 42
            ):
                raise GridRefreshAuditRejected("stale or disassociated real refresh packet")
            live = NativeVoxelPresentDev(
                session_id=native["session_id"],
                native_seq=native["seq"],
                request_id=native["request_id"],
                origin_x=float(native["origin_x"]),
                origin_z=float(native["origin_z"]),
                player_x=float(native["player_x"]),
                player_z=float(native["player_z"]),
                player_y=float(native["player_y"]),
                coverage=native["coverage"],
                cells=tuple(VoxelColumnDev(**c) for c in native["cells"]),
                provenance=Provenance(
                    "mineflayer", f"{native['session_id']}:{native['seq']}"
                ),
            )
            reproduced = refresh_grid_route_dev(
                live, prior,
                last_s16_after_seq=event["last_s16_after_seq"],
                last_closed_action_id=event["last_closed_action_id"],
                provenance=Provenance(
                    "s49-goal-dev-operator", f"grid-refresh-{prior.revision + 1}"
                ),
            )
            if (
                reproduced.status != event["status"]
                or reproduced.reason != event["reason"]
                or [list(v) for v in reproduced.chosen_cell_path]
                   != event["chosen_cell_path"]
                or reproduced.plan is None
                or reproduced.plan.revision != event["new_revision"]
            ):
                raise GridRefreshAuditRejected("L1 refresh not reproducible from native")
            if first_path is None:
                first_path = reproduced.chosen_cell_path
                if name == "MIDROUTE_BLOCKED":
                    if (
                        live.observed(2, 2).value.feet != "BLOCKED"
                        or (2, 2) not in initial.chosen_cell_path
                        or (2, 2) in first_path
                        or report.get("midroute_stone_stimulus_dev", {})
                            .get("native_confirmed") is not True
                    ):
                        raise GridRefreshAuditRejected("midroute native obstruction not proven")
            prior = reproduced.plan
        last = route["stages"][-1]
        final_error = math.hypot(
            last["reached_x"] - report["goal_l2"]["target_x"],
            last["reached_z"] - report["goal_l2"]["target_z"],
        )
        if (
            final_error > last["tolerance_m"]
            or not math.isclose(
                final_error, route["final_parent_goal_error_m"], abs_tol=1e-8
            )
        ):
            raise GridRefreshAuditRejected("not physically at original parent Goal")
        summaries[name] = {
            "status": "REACHED",
            "revisions": len(trace),
            "native_actions_after_original_unknown": len(stage_actions),
            "final_parent_goal_error_m": final_error,
            "first_refresh_path": [list(v) for v in first_path],
        }
    result = {
        "classification": "S49_L1_NATIVE_GRID_REFRESH_PHYSICAL_DEV",
        "worlds": summaries,
        "new_action_issuer": False,
        "new_native_reader": False,
        "learning_attested": False,
        "inflight_l0_interrupt_attested": False,
        "qualification_go": False,
        "science_go": False,
    }
    (root / "grid_refresh_two_world_review.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf8"
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    print(
        "S49_L1_NATIVE_GRID_REFRESH_REAL_DEV_PASS",
        json.dumps(review_grid_refresh_worlds_dev(args.root), sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
