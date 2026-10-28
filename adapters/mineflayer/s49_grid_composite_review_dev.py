"""Independent saved-byte audit of composite L1/L0 DEV; no World operations."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from adapters.mineflayer.s49_l1_grid_inflight_review_dev import audit_grid_inflight_dev
from relay_self.goal_grid_search_dev import _find_path, swept_body_safe_dev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.provenance import Provenance


def audit(root: Path) -> dict:
    summary = audit_grid_inflight_dev(root)
    world = root / "HAZARD"
    report = json.loads((world / "goal_report.json").read_text())
    raw = (world / "w3-node-stdout.raw.jsonl").read_bytes()
    receipt = json.loads((world / "w3-node-stdout-receipt.json").read_text())
    def require(ok, reason):
        if not ok:
            raise ValueError(reason)
    require(hashlib.sha256(raw).hexdigest() == receipt["stdout_sha256"]
            and receipt["status"] == "COMPLETE_NODE_STDOUT"
            and receipt["eof_observed"] and receipt["process_exit_code"] == 0,
            "raw transcript not sealed")
    frames = [json.loads(line) for line in raw.splitlines()]
    byseq = {f["seq"]:f for f in frames}
    require(len(byseq) == len(frames) and [f["seq"] for f in frames] == sorted(byseq)
            and all(f["session_id"] == report["session_id"] for f in frames),
            "duplicate or foreign native sequence")
    for native in [report["native_local_voxel_observation_dev"],
                   *report["native_grid_refresh_observations_dev"],
                   *(r["native"] for r in report["seeded_layouts_dev"])]:
        wire = byseq[native.get("seq",native.get("native_seq"))]
        require(wire["type"] == "local_voxels_dev", "not native voxel bytes")
        for key in ("cells","request_id","origin_x","origin_z","player_x","player_z"):
            require(wire[key] == native[key], f"native source mismatch {key}")
    route = report["detour"]
    incident = route["l0_inflight_interrupt"]
    applied, threat, clear, ended = (incident["applied_ack"]["seq"],
        incident["native_threat"]["probe_seq"],incident["clear_ack"]["seq"],
        incident["after_s16_seq"])
    require(applied < threat < clear < ended, "native interrupt order")
    for key in ("applied_ack","clear_ack"):
        ack = incident[key]
        require(all(byseq[ack["seq"]][k] == ack[k] for k in ack), "ACK differs from bytes")
    danger = byseq[threat]
    require(danger["request_id"] == incident["native_threat"]["request_id"]
            and any(e["id"] == incident["native_threat"]["entity_id"]
                    and e["type"] == "hostile"
                    and e["distance"] <= report["goal_l2"]["danger_interrupt_m"]
                    for e in danger["snapshot"]["nearby_entities"]), "threat absent in bytes")
    moves = [f for f in frames if f.get("effect") == "set_control"]
    require(len({f["action_id"] for f in moves}) == len(moves)
            and not any(f["seq"] > threat for f in moves), "Action replay or post interrupt MOVE")
    require(report["grid_midroute_obstacle_dev"]
            and report["midroute_stone_stimulus_dev"]["native_confirmed"]
            and (2,2) in [tuple(p) for p in route["l1_detour_plan"]["cell_path"]]
            and (2,2) not in [tuple(p) for p in route["replan_events"][0]["chosen_cell_path"]],
            "stone and changed path not proven in same World")
    for stage in route["stages"]:
        require(bool(stage.get("swept_checks")), "MOVE lacks swept guard")
        for check in stage["swept_checks"]:
            packet = byseq[check["voxel_seq"]]
            live = NativeVoxelPresentDev(
                session_id=packet["session_id"], native_seq=packet["seq"],
                request_id=packet["request_id"],origin_x=float(packet["origin_x"]),
                origin_z=float(packet["origin_z"]),player_x=float(packet["player_x"]),
                player_z=float(packet["player_z"]),player_y=float(packet["player_y"]),
                coverage=packet["coverage"],cells=tuple(VoxelColumnDev(**c) for c in packet["cells"]),
                provenance=Provenance("mineflayer",f"{packet['session_id']}:{packet['seq']}"),
            )
            pos = byseq[check["probe_seq"]]["snapshot"]["position"]
            require(check["safe"] and check["radius_m"] == 0.30 and swept_body_safe_dev(
                live,(pos["x"]-live.origin_x,pos["z"]-live.origin_z),
                (stage["target_x"]-live.origin_x,stage["target_z"]-live.origin_z)),
                "recorded continuous footprint not safe")
    layouts = report["seeded_layouts_dev"]
    require([(e["name"],e["decision"]) for e in layouts] == [
        ("REACHABLE","SELECTED"),("CHANGED","SELECTED"),
        ("SEALED","DEFER"),("UNSUPPORTED","DEFER")], "missing layout coverage")
    require(not any(layouts[0]["native"]["native_seq"] < f["seq"]
                    < report["native_local_voxel_observation_dev"]["seq"] for f in moves),
            "Action issued during passive layout tests")
    for entry in layouts:
        v = entry["native"]
        live = NativeVoxelPresentDev(**{**v,"cells":tuple(VoxelColumnDev(**c) for c in v["cells"]),
            "provenance":Provenance(**v["provenance"])})
        start = (round(live.player_x-live.origin_x),round(live.player_z-live.origin_z))
        path, _ = _find_path(live,start,(0,4))
        require([list(p) for p in path] == entry["path"], "layout BFS not reproducible")
        require(entry["actions_issued"] == 0, "passive layout issued Action")
        # Deliberately masked source negative; explicitly not native UNKNOWN.
        masked = replace(live,cells=tuple(replace(c,feet="UNKNOWN") if c.dz == 2 else c
                                         for c in live.cells))
        require(not _find_path(masked,start,(0,4))[0], "UNKNOWN treated as CLEAR")
    require(layouts[0]["path"] != layouts[1]["path"], "fixed corridor dependence")
    summary.update({"classification":"S49_COMPOSITE_STONE_REROUTE_NATIVE_L0_DEV",
        "total_move_actions":len(moves),"route_updates":len(route["replan_events"]),
        "applied_seq":applied,"threat_seq":threat,"clear_seq":clear,"s16_seq":ended,
        "post_interrupt_actions":0,"physical_seeded_layouts":4,
        "unknown_negative":"MASKED_SOURCE_OFFLINE_ONLY",
        "native_sha256":receipt["stdout_sha256"],"final_goal":"INTERRUPTED_NOT_REACHED"})
    (root / "composite_review.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True,type=Path)
    print(json.dumps(audit(parser.parse_args().root),indent=2))
