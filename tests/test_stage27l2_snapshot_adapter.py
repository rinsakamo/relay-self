"""All snapshots here are invented; no Paper or real World evidence."""
import copy

from experiments.stage27l2_snapshot_adapter import inspect_snapshot


def snapshot():
    cells = []
    for x in range(-1, 7):
        for y in range(-1, 3):
            for z in range(-1, 2):
                boxes = [[x, y, z, x+1, y+1, z+1]] if y == -1 else []
                cells.append({"x": x, "y": y, "z": z, "chunk_loaded": True,
                              "read_ok": True, "collision_boxes_world": boxes})
    return {"world_uuid": "ac2bd368-ccd9-4111-90ee-41cb0f79b295", "terrain_complete": True,
            "start_tick": 10, "end_tick": 10, "bounds_exclusive": [-1, -1, -1, 7, 3, 2],
            "position": [0.5, 0, 0.5], "body_aabb": [0.25, 0, 0.25, 0.75, 1.8, 0.75], "cells": cells}


def test_clear_is_diagnostic_not_pass():
    result = inspect_snapshot(snapshot(), [5.5, 0, 0.5])
    assert result["status"] == "UNKNOWN"
    assert result["unqualified_geometry_diagnostic"]["status"] == "CLEAR"


def test_wall_and_partial_shape_diagnostics_never_qualify():
    for shape in ([[3, 0, 0, 4, 1, 1]], [[3, 0, 0, 4, 0.5, 1], [3, 0.5, 0.5, 4, 1, 1]]):
        s = snapshot()
        next(c for c in s["cells"] if (c["x"], c["y"], c["z"]) == (3, 0, 0))["collision_boxes_world"] = shape
        result = inspect_snapshot(s, [5.5, 0, 0.5])
        assert result["status"] == "UNKNOWN"
        assert result["unqualified_geometry_diagnostic"]["status"] == "BLOCKED"


def test_incomplete_and_invalid_never_clear():
    for change in (lambda s: s.update(terrain_complete=False), lambda s: s.update(end_tick=11),
                   lambda s: s["cells"].pop(), lambda s: s["cells"].append(copy.deepcopy(s["cells"][0])),
                   lambda s: s["cells"][0].update(chunk_loaded=False),
                   lambda s: s.update(body_aabb=[0, 0, 0, float("nan"), 2, 1]),
                   lambda s: s.pop("body_aabb")):
        s = snapshot()
        change(s)
        result = inspect_snapshot(s, [5.5, 0, 0.5])
        assert result["status"] == "UNKNOWN"
        assert "unqualified_geometry_diagnostic" not in result
