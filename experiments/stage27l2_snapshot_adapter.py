"""Offline-only snapshot geometry diagnostics; never qualifies a live route.

The present sources do not bind the original native connection to a Paper
player, establish live world generation, or prove entity search coverage.
"""
from __future__ import annotations

import math

from experiments.stage27k_route_preflight import inspect


def inspect_snapshot(snapshot: dict, target: list[float]) -> dict:
    """Return UNKNOWN with an optional unqualified Stage27k diagnostic."""
    result = {"status": "UNKNOWN", "reason": "source qualification unavailable"}
    try:
        if snapshot["terrain_complete"] is not True or snapshot["start_tick"] != snapshot["end_tick"]:
            return result
        body, start = snapshot["body_aabb"], snapshot["position"]
        if len(body) != 6 or len(start) != 3 or len(target) != 3:
            return result
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in [*body, *start, *target]):
            return result
        x0, y0, z0, x1, y1, z1 = body
        width = x1 - x0
        if not (0 < width <= 4 and 0 < y1-y0 <= 4 and z1-z0 == width
                and x0 == start[0]-width/2 and x1 == start[0]+width/2
                and z0 == start[2]-width/2 and z1 == start[2]+width/2 and y0 == start[1]):
            return result
        bounds = snapshot["bounds_exclusive"]
        if len(bounds) != 6 or any(type(v) is not int for v in bounds):
            return result
        bx0, by0, bz0, bx1, by1, bz1 = bounds
        if not (0 < bx1-bx0 <= 16 and 0 < by1-by0 <= 16 and 0 < bz1-bz0 <= 16
                and (bx1-bx0)*(by1-by0)*(bz1-bz0) <= 1024):
            return result
        cells = {}
        for c in snapshot["cells"]:
            x, y, z = c["x"], c["y"], c["z"]
            if (any(type(v) is not int for v in (x, y, z)) or not (bx0 <= x < bx1 and by0 <= y < by1 and bz0 <= z < bz1)
                    or c["chunk_loaded"] is not True or c["read_ok"] is not True):
                return result
            key = f"{x},{y},{z}"
            if key in cells:
                return result
            cells[key] = c["collision_boxes_world"]
        if len(cells) != (bx1-bx0)*(by1-by0)*(bz1-bz0):
            return result
        fixture = {"expected_world_uuid": snapshot["world_uuid"], "snapshot_world_uuid": snapshot["world_uuid"],
                   "snapshot_complete": True, "start": start, "target": target,
                   "width": width, "height": y1-y0, "cells": cells}
        result["unqualified_geometry_diagnostic"] = inspect(fixture)
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    return result
