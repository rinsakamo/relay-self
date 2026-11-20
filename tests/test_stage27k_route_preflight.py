import copy

from experiments.stage27k_route_preflight import inspect


def fixture():
    cells = {}
    for x in range(-1, 7):
        for z in range(-1, 2):
            cells[f"{x},-1,{z}"] = [[x, -1, z, x+1, 0, z+1]]
            for y in (0, 1, 2):
                cells[f"{x},{y},{z}"] = []
    return {"expected_world_uuid": "ac2bd368-ccd9-4111-90ee-41cb0f79b295", "snapshot_world_uuid": "ac2bd368-ccd9-4111-90ee-41cb0f79b295", "snapshot_complete": True, "start": [0.5, 0, 0.5], "target": [5.5, 0, 0.5], "width": 0.6, "height": 1.8, "cells": cells}


def test_clear_and_touching_boundary():
    f = fixture()
    assert inspect(f)["status"] == "CLEAR"
    f["cells"]["1,0,0"] = [[1, 0, 0, 2, 1, 1]]
    assert inspect(f)["status"] == "BLOCKED"  # contact after 0.2m
    f["target"] = [0.7, 0, 0.5]
    assert inspect(f)["status"] == "CLEAR"  # contact alone is not overlap


def test_obstacles_and_shape():
    for cell, box in [("3,0,0", [3,0,0,4,1,1]), ("2,1,0", [2,1,0,3,2,1]), ("3,0,0", [3,0,0,4,0.5,1])]:
        f = fixture()
        f["cells"][cell] = [box]
        assert inspect(f)["status"] == "BLOCKED"
    f = fixture()
    f["width"] = 1.2
    f["cells"]["2,0,-1"] = [[2,0,-1,3,1,0]]
    assert inspect(f)["status"] == "BLOCKED"
    f = fixture()
    f["cells"]["3,0,0"] = [[3,0,0,4,0.5,0.1]]
    assert inspect(f)["status"] == "CLEAR"  # known partial shape outside footprint
    f["cells"]["3,-1,0"] = []
    assert inspect(f)["status"] == "BLOCKED"


def test_missing_unknown_and_boundaries():
    f = fixture()
    for key in ("3,0,0", "3,-1,0"):
        g = copy.deepcopy(f)
        del g["cells"][key]
        assert inspect(g)["status"] == "UNKNOWN"
    f["cells"]["3,0,0"] = None
    assert inspect(f)["status"] == "UNKNOWN"
    f = fixture()
    f["snapshot_world_uuid"] = "00000000-0000-0000-0000-000000000000"
    assert inspect(f)["status"] == "UNKNOWN"
    assert inspect({})["status"] == "UNKNOWN"
    for field, value in [("width", 0), ("height", float('nan')), ("target", [5.6, 0, 0.5]), ("target", [5, 0, 1])]:
        f = fixture()
        f[field] = value
        assert inspect(f)["status"] == "UNKNOWN"
