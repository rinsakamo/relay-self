"""Independent native S49 L0 hazard-after-L1-refresh physical DEV review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.mineflayer.s49_l1_native_grid_review_dev import _read, _rebuild
from relay_self.goal_grid_refresh_dev import refresh_grid_route_dev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.provenance import Provenance


class GridInflightAuditRejected(ValueError):
    pass


def audit_grid_inflight_dev(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise GridInflightAuditRejected("original World required")
    report = _read(root, "HAZARD")
    source = _rebuild(report)
    plan = source.plan
    route = report.get("detour")
    if (
        plan is None or not isinstance(route, dict)
        or report.get("grid_refresh_dev") is not True
        or report.get("grid_inflight_hazard_dev") is not True
        or route.get("route_status") != "INTERRUPT"
        or route.get("reached_final_goal") is not False
        or report.get("classification")
           != "DEV_ONLY_S49_L1_GRID_REFRESH_L0_INFLIGHT_PREEMPTED"
        or report.get("stage") != "L0_GRID_INFLIGHT_INTERRUPTED"
        or len(route.get("replan_events", [])) < 1
    ):
        raise GridInflightAuditRejected("no original L1 reroute / native L0 stop")
    original_stage = route["stages"][0]
    stopped_stage = route["stages"][-1]
    incident = route.get("l0_inflight_interrupt")
    voxels = report["native_grid_refresh_observations_dev"][0]
    event = route["replan_events"][0]
    if (
        original_stage["result"] != "REACHED"
        or not original_stage["actions"]
        or original_stage["route_revision"] != 1
        or stopped_stage["route_revision"] <= 1
        or stopped_stage["result"] != "INTERRUPT"
        or stopped_stage["actions"]
        or stopped_stage["decisions"][-1]["kind"] != "INTERRUPT"
        or incident is None
        or incident.get("route_revision") != stopped_stage["route_revision"]
        or incident.get("action_id") != stopped_stage["inflight_action_id"]
        or incident.get("terminal") != "unknown"
        or incident.get("S16_status") != "failed"
        or incident.get("S16_error")
           != "DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED"
        or incident.get("next_action_issued") is not False
        or incident.get("original_action_owner") is not True
        or incident.get("native_threat", {}).get("kind") != "INTERRUPT"
        or incident.get("native_threat", {}).get("provenance_source")
           != "mineflayer"
        or incident.get("applied_ack", {}).get("result") != "applied"
        or incident.get("clear_ack", {}).get("result") != "applied"
        or incident["clear_ack"]["seq"] <= incident["native_threat"]["probe_seq"]
        or incident.get("live_probe_count", 0) < 1
        or report.get("grid_inflight_hazard_stimulus_dev", {})
            .get("after_actual_applied_action_id") != incident["action_id"]
    ):
        raise GridInflightAuditRejected("native original L0 APPLIED/PROBE/CLEAR missing")
    fresh = NativeVoxelPresentDev(
        session_id=voxels["session_id"],
        native_seq=voxels["seq"],
        request_id=voxels["request_id"],
        origin_x=float(voxels["origin_x"]),
        origin_z=float(voxels["origin_z"]),
        player_x=float(voxels["player_x"]),
        player_z=float(voxels["player_z"]),
        player_y=float(voxels["player_y"]),
        coverage=voxels["coverage"],
        cells=tuple(VoxelColumnDev(**c) for c in voxels["cells"]),
        provenance=Provenance(
            "mineflayer", f"{voxels['session_id']}:{voxels['seq']}"
        ),
    )
    derived = refresh_grid_route_dev(
        fresh, plan, last_s16_after_seq=event["last_s16_after_seq"],
        last_closed_action_id=event["last_closed_action_id"],
        provenance=Provenance(
            "s49-goal-dev-operator", "grid-refresh-2"
        ),
    )
    if (
        derived.plan is None
        or derived.plan.revision != stopped_stage["route_revision"]
        or [list(v) for v in derived.chosen_cell_path]
           != event["chosen_cell_path"]
        or event["fresh_voxel_seq"] <= event["last_s16_after_seq"]
    ):
        raise GridInflightAuditRejected("revised L1 route lacks fresh voxel source")
    outcome_ids=[
        action["action_id"] for stage in route["stages"]
        for action in stage["actions"]
    ]
    if incident["action_id"] in outcome_ids or len(outcome_ids) != len(set(outcome_ids)):
        raise GridInflightAuditRejected("S49 original Action reused after interruption")
    review={
        "classification":"S49_L1_GRID_REFRESH_PLUS_L0_INFLIGHT_PHYSICAL_DEV",
        "session_id":report["session_id"],
        "native_replans":len(route["replan_events"]),
        "original_waypoint_outcomes":len(outcome_ids),
        "interrupted_action_id":incident["action_id"],
        "native_probe_seq":incident["native_threat"]["probe_seq"],
        "native_clear_seq":incident["clear_ack"]["seq"],
        "terminal":"UNKNOWN",
        "additional_action_after_interrupt":False,
        "original_parent_goal_preserved":True,
        "goal_reached":False,
        "qualification_go":False,"science_go":False,
    }
    (root/"grid_l0_inflight_review.json").write_text(
        json.dumps(review,indent=2,sort_keys=True)+"\n",encoding="utf8"
    )
    return review


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    print("S49_L1_GRID_L0_INFLIGHT_NATIVE_REAL_DEV_PASS",
          json.dumps(audit_grid_inflight_dev(args.root),sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
