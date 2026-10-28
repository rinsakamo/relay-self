"""T1w passive correspondence review. Geometry never proves causal WorldTick.

Input is an existing Node DEV sidecar and the original Paper M02_DEV_MOTION
log. Neither side carries a shared movement-packet ID or authoritative
client-step clock. Never create a SourceBoundTick or debit P1/M0 from this.
"""
from __future__ import annotations

import json
import math
from collections import Counter


class T1wMotionRejected(ValueError):
    """Malformed, incomplete, altered or inconsistent DEV trace."""


def _finite_pose(value):
    return (
        type(value) is dict
        and set(value) == {"x", "y", "z"}
        and all(type(value[k]) in (int, float) and math.isfinite(value[k])
                for k in ("x", "y", "z"))
    )


def _paper_moves(lines):
    rows = []
    for line in lines:
        if "M02_DEV_MOTION " not in line:
            continue
        source = line.split("M02_DEV_MOTION ", 1)[1]
        pairs = [part.split("=", 1) for part in source.split()]
        if any(len(pair) != 2 for pair in pairs):
            raise T1wMotionRejected("invalid Paper move row")
        row = dict(pairs)
        if len(row) != len(pairs):
            raise T1wMotionRejected("duplicate Paper field")
        try:
            identity = (int(row["id"]), row["world"], int(row["world_full_time"]))
            start = {k: float(row[f"from_{k}"]) for k in ("x", "y", "z")}
            end = {k: float(row[f"to_{k}"]) for k in ("x", "y", "z")}
            blocks = float(row["blocks"])
        except (KeyError, TypeError, ValueError) as ex:
            raise T1wMotionRejected("malformed Paper movement") from ex
        if (not _finite_pose(start) or not _finite_pose(end)
                or not math.isfinite(blocks) or blocks <= 0
                or math.hypot(end["x"] - start["x"], end["z"] - start["z"]) == 0
                or identity[0] <= 0 or identity[2] < 0 or not identity[1]):
            raise T1wMotionRejected("invalid Paper movement geometry")
        rows.append({"id": identity[0], "world": identity[1],
                     "world_full_time": identity[2], "start": start,
                     "end": end, "blocks": blocks})
    if len({row["id"] for row in rows}) != len(rows):
        raise T1wMotionRejected("duplicate Paper event id")
    if any(b["id"] <= a["id"] or b["world_full_time"] < a["world_full_time"]
           or b["world"] != a["world"] for a, b in zip(rows, rows[1:])):
        raise T1wMotionRejected("Paper event order or world changed")
    return rows


def _node_rows(lines):
    # Materialize once: the single TRACE_END must be the final nonempty row.
    lines = [line for line in lines if line.strip()]
    rows = []
    for position, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except (TypeError, ValueError) as ex:
            raise T1wMotionRejected("invalid Node JSONL") from ex
        if type(obj) is not dict or obj.get("revision") != 1:
            raise T1wMotionRejected("invalid Node trace revision")
        if obj.get("kind") == "TRACE_END":
            if position != len(lines) - 1:
                raise T1wMotionRejected("Node trace appended rows after footer")
            if (obj.get("complete") is not True or obj.get("lost") is not False
                    or obj.get("recorded_rows") != len(rows)
                    or obj.get("motion_authority") is not False):
                raise T1wMotionRejected("incomplete or backpressured Node trace")
            return rows
        if (obj.get("index") != len(rows) + 1
                or obj.get("kind") not in (
                    "PHYSICS_EVENT_SAMPLE", "MOVEMENT_WRITE_RETURNED")
                or obj.get("source_authority") != "PASSIVE_LOCAL_DIAGNOSTIC"
                or obj.get("clock_scope") != "NODE_ONLY"):
            raise T1wMotionRejected("nonconsecutive or unauthorized Node row")
        try:
            node_ns = int(obj["node_ns"])
        except (TypeError, ValueError, KeyError) as ex:
            raise T1wMotionRejected("invalid Node event clock") from ex
        if node_ns < 0 or (rows and node_ns < int(rows[-1]["node_ns"])):
            raise T1wMotionRejected("Node event clock nonmonotone")
        if obj["kind"] == "MOVEMENT_WRITE_RETURNED":
            if (obj.get("packet_index") != 1 + sum(
                    r["kind"] == "MOVEMENT_WRITE_RETURNED" for r in rows)
                    or obj.get("network_delivered") is not False
                    or obj.get("paper_accepted") is not False):
                raise T1wMotionRejected("invalid outbound write witness")
        rows.append(obj)
    raise T1wMotionRejected("missing complete Node footer")


def review_motion_correspondence_dev(node_lines, paper_lines):
    """All matches are candidates; no shared packet identity/ACK is invented."""
    rows = _node_rows(node_lines)
    paper = _paper_moves(paper_lines)
    sent = [row for row in rows if row["kind"] == "MOVEMENT_WRITE_RETURNED"]
    physics = [row for row in rows if row["kind"] == "PHYSICS_EVENT_SAMPLE"]
    result = []
    for move in paper:
        candidates = []
        for row in sent:
            pose = row.get("packet_pose")
            if (_finite_pose(pose)
                    and all(math.isclose(pose[k], move["end"][k],
                                         abs_tol=1e-6, rel_tol=0)
                            for k in ("x", "y", "z"))):
                candidates.append(row["packet_index"])
        status = ("NO_GEOMETRY_MATCH" if not candidates else
                  "GEOMETRY_SINGLE_UNATTESTED" if len(candidates) == 1 else
                  "GEOMETRY_AMBIGUOUS")
        result.append({
            "paper_event_id": move["id"], "paper_world_full_time": move["world_full_time"],
            "world": move["world"], "matching_packet_indices": candidates,
            "candidate_status": status, "actual_source_link": False,
            "p1_transition_admitted": False,
        })
    return {
        "classification": "T1W_PASSIVE_CORRESPONDENCE_DEV_NOT_WORLD_TICK_AUTHORITY",
        "node_physics_samples": len(physics), "node_movement_write_returns": len(sent),
        "paper_move_events": len(paper),
        "candidate_counts": dict(Counter(x["candidate_status"] for x in result)),
        "paper_candidates": result,
        "exact_client_step_to_paper_tick_proven": False,
        "cross_process_packet_id_present": False,
        "network_acceptance_proven": False,
        "p1_transitions_admitted": 0, "m0_debits_posted": 0,
        "r_qualified": False, "science_qualified": False,
    }
