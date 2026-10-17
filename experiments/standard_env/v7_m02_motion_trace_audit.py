"""R independent Paper source motion timing/pose diagnostic, DEV review only.

Actual PlayerMoveEvent path is not a nominal requested one-block step. Event
timings/positions are source observations, not proof of collision causality.
"""
from __future__ import annotations

import math
import re
from typing import Any

NUM = r"([+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)"
PATTERN = re.compile(
    r"M02_DEV_MOTION id=(\d+) reason=(WALK|SPRINT|CROUCH)"
    + r" blocks=" + NUM + r" billed=" + NUM
    + r" cumulative_blocks=" + NUM + r" cumulative_billed=" + NUM
    + r" from_x=" + NUM + r" from_y=" + NUM + r" from_z=" + NUM
    + r" to_x=" + NUM + r" to_y=" + NUM + r" to_z=" + NUM
    + r" world_full_time=(\d+)\s*$"
)
BASAL = re.compile(r"M02_DEV_BASAL_WRITE id=(\d+) world_full_time=(\d+) ")
CLASS = "RSEE_V7_M02_NATIVE_MOTION_POSE_TIME_DEV_DIAGNOSTIC_ONLY"


class InvalidMotion(ValueError):
    pass


def check(ok: bool, why: str) -> None:
    if not ok:
        raise InvalidMotion(why)


def review(raw: bytes) -> dict[str, Any]:
    check(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024,
          "invalid Paper original log")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise InvalidMotion("nonUTF8 Paper original log") from exc
    source: list[dict[str, Any]] = []
    first_basal_time = None
    for line in lines:
        if "M02_DEV_BASAL_WRITE " in line:
            b = BASAL.search(line)
            check(b is not None, "invalid BASAL write record in motion source")
            if b.group(1) == "1":
                check(first_basal_time is None, "duplicate first BASAL source")
                first_basal_time = int(b.group(2))
        if "M02_DEV_MOTION " not in line:
            continue
        m = PATTERN.search(line)
        check(m is not None, "motion source not coordinate-complete")
        nums = tuple(float(v) for v in m.groups()[2:-1])
        check(all(math.isfinite(v) for v in nums), "nonfinite motion source")
        blocks,billed,cblocks,cbilled,fx,fy,fz,tx,ty,tz = nums
        measured = math.hypot(tx - fx, tz - fz)
        check(0 < blocks <= 1 and billed >= 0 and math.isclose(
                  measured,blocks,rel_tol=0,abs_tol=1e-9),
              "native event coordinates do not reconstruct horizontal path")
        source.append({
            "id": int(m.group(1)), "reason":m.group(2),
            "blocks":blocks,"billed":billed,
            "cumulative_blocks":cblocks,"cumulative_billed":cbilled,
            "from":[fx,fy,fz],"to":[tx,ty,tz],
            "world_full_time":int(m.group(13)),
        })
    check(len(source)>0 and len(source)<=300, "no bounded native motion packets")
    check([x["id"] for x in source] == list(range(1,len(source)+1)),
          "skipped/duplicate original native movement ID")
    check(all(x["reason"]=="WALK" for x in source),
          "non-WALK physics not admitted in this diagnostic")
    total = 0.0
    cumulative_charge=0.0
    for row in source:
        total += row["blocks"]
        cumulative_charge += row["billed"]
        check(abs(row["cumulative_blocks"] - total) <= 1e-7
              and abs(row["cumulative_billed"] - cumulative_charge) <= 1e-7,
              "original packet cumulative distance/debit changed")
    fst,lst=source[0],source[-1]
    displacement=math.hypot(lst["to"][0]-fst["from"][0],
                            lst["to"][2]-fst["from"][2])
    check(total + 1e-7 >= displacement, "path shorter than net displacement")
    return {
        "classification": CLASS,
        "packet_count":len(source),
        "motion_path_blocks":total,
        "net_horizontal_displacement_blocks":displacement,
        "path_minus_net_displacement_blocks":total-displacement,
        "walk_source_debit":cumulative_charge,
        "observed_charge_per_actual_block":cumulative_charge/total,
        "first_native_motion_from_xyz":fst["from"],
        "last_native_motion_to_xyz":lst["to"],
        "first_native_motion_world_full_time":fst["world_full_time"],
        "last_native_motion_world_full_time":lst["world_full_time"],
        "motion_time_span_world_ticks":
            lst["world_full_time"]-fst["world_full_time"],
        "first_basal_source_world_time":first_basal_time,
        "first_motion_time_relative_to_first_basal":
            fst["world_full_time"]-first_basal_time
            if first_basal_time is not None else None,
        "same_start_pose_as_other_arms_attested": False,
        "identical_generated_collision_geometry_attested": False,
        "collision_cause_attested": False,
        "same_s50_action_phase_bracket_attested": False,
        "scientific_comparison_admitted": False,
        "engineering_qualification": False,
    }
