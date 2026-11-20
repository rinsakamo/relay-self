"""Offline operator fixture geometry check; never a Self percept or action grant.

Input cells must come from an independently verified, complete snapshot and
contain collision boxes in world coordinates; an empty list means known empty,
None or an absent cell means unknown. This tool does not infer shapes from IDs.
"""
from __future__ import annotations

import json
import math
import sys
import uuid
from pathlib import Path


def inspect(fixture: dict) -> dict:
    def result(status: str, reason: str) -> dict:
        return {"status": status, "reason": reason}

    try:
        expected = str(uuid.UUID(fixture["expected_world_uuid"]))
        actual = str(uuid.UUID(fixture["snapshot_world_uuid"]))
        if expected != actual:
            return result("UNKNOWN", "world UUID mismatch")
        if fixture["snapshot_complete"] is not True:
            return result("UNKNOWN", "snapshot not complete")
        start, end = fixture["start"], fixture["target"]
        width, height = fixture["width"], fixture["height"]
        vals = [*start, *end, width, height]
        if len(start) != 3 or len(end) != 3 or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in vals
        ) or not (0 < width <= 4 and 0 < height <= 4):
            return result("UNKNOWN", "invalid coordinates or dimensions")
        dx, dz = end[0] - start[0], end[2] - start[2]
        if start[1] != end[1] or (dx != 0 and dz != 0) or not (0 < abs(dx) + abs(dz) <= 5):
            return result("UNKNOWN", "only level axis-aligned routes up to 5m supported")
        cells = fixture["cells"]
        if not isinstance(cells, dict):
            return result("UNKNOWN", "missing cells")
        x0, x1 = min(start[0], end[0])-width/2, max(start[0], end[0])+width/2
        z0, z1 = min(start[2], end[2])-width/2, max(start[2], end[2])+width/2
        y0, y1 = start[1], start[1]+height
        unknown = False
        # The complete swept volume of an axis-aligned translation is a box.
        # Each intersected footprint cell also needs a full top support face.
        for x in range(math.floor(x0), math.ceil(x1)):
            for z in range(math.floor(z0), math.ceil(z1)):
                for y in range(math.floor(y0)-1, math.ceil(y1)):
                    boxes = cells.get(f"{x},{y},{z}")
                    if boxes is None:
                        unknown = True
                        continue
                    if not isinstance(boxes, list):
                        return result("UNKNOWN", "invalid shape")
                    for box in boxes:
                        if (not isinstance(box, list) or len(box) != 6 or
                            any(type(v) not in (int, float) or not math.isfinite(v) for v in box) or
                            not (x <= box[0] < box[3] <= x+1 and y <= box[1] < box[4] <= y+1 and z <= box[2] < box[5] <= z+1)):
                            return result("UNKNOWN", "invalid collision box")
                        if (box[0] < x1 and box[3] > x0 and box[1] < y1 and box[4] > y0 and box[2] < z1 and box[5] > z0):
                            return result("BLOCKED", f"collision at {x},{y},{z}")
                support_y = math.floor(y0)-1
                # Non-integral feet may stand on a partial shape in this cell.
                if y0 != math.floor(y0):
                    support_y = math.floor(y0)
                support = cells.get(f"{x},{support_y},{z}")
                if support is None:
                    unknown = True
                elif not any(b[1] < y0 == b[4] and b[0] <= max(x0,x) and b[3] >= min(x1,x+1) and b[2] <= max(z0,z) and b[5] >= min(z1,z+1) for b in support):
                    return result("BLOCKED", f"unsupported footprint at {x},{support_y},{z}")
        return result("UNKNOWN", "missing cell or collision shape") if unknown else result("CLEAR", "continuous supported swept volume")
    except (KeyError, TypeError, ValueError, OverflowError):
        return result("UNKNOWN", "invalid or missing fixture data")


def main() -> None:
    try:
        fixture = json.loads(Path(sys.argv[1]).read_text())
        print(json.dumps(inspect(fixture)))
    except (OSError, IndexError, ValueError):
        print(json.dumps({"status": "UNKNOWN", "reason": "fixture unavailable or invalid"}))


if __name__ == "__main__":
    main()
