"""MP11 Stage0.1: independent Paper multi-marker *shape* auditor.

Not S16 / native bridge qualification. No authority from a caller's receipt.
Accept original bytes only; a future original S49 owner must independently
supply per-action S16, actual INPUT control regime and L0 grants.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

class MP11PaperRejected(ValueError):
    """Original Paper sequence cannot be bound to one World and multiple trials."""


@dataclass(frozen=True, slots=True)
class TrialPaperSource:
    marker_id: str
    world_uuid: str
    subject_uuid: str
    paper_sha256: str
    condition: str
    ordinal: int
    wait_ticks: tuple[int, ...]
    wait_motion_m: tuple[float, ...]
    status: str = "ORIGINAL_PAPER_MARKER_SHAPE_ONLY_NO_NATIVE_S16_AUTHORITY"


def audit_multi_trial_paper(
    original: bytes, *,
    action_markers: tuple[str, ...],
    world_uuid: str,
    subject_uuid: str,
    surfaces: tuple[str, ...],
) -> tuple[TrialPaperSource, ...]:
    """Check 2..4 original Paper marker groups in EXACT ordered same World."""
    if (not isinstance(original, bytes)
            or not 0 < len(original) <= 16_000_000
            or not original.endswith(b"\n")
            or type(action_markers) is not tuple
            or not 2 <= len(action_markers) <= 4
            or len(set(action_markers)) != len(action_markers)
            or not all(isinstance(x, str) and 0 < len(x) <= 128
                       and not any(c.isspace() for c in x) for x in action_markers)
            or not isinstance(world_uuid, str) or not world_uuid
            or not isinstance(subject_uuid, str) or not subject_uuid
            or type(surfaces) is not tuple
            or len(surfaces) != len(action_markers)
            or any(s not in ("GRASS_BLOCK", "PACKED_ICE") for s in surfaces)):
        raise MP11PaperRejected("unbounded, foreign or incomplete original Paper input")

    try:
        decoded = original.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise MP11PaperRejected("non UTF-8 original Paper") from exc
    lines = []
    for line in decoded.splitlines():
        payload = dict(part.split("=", 1) for part in line.split()
                       if part.count("=") == 1)
        lines.append((line, payload))
    kinds = (
        "M02_DEV_S50_PHASE", "S50_DEV_SURFACE_LOCK", "S50_DEV_WAIT_BEGIN",
        "S50_DEV_WAIT_TICK", "S50_DEV_INPUT_TICK",
        "S50_DEV_LOCAL_FORECAST_FIXED", "S50_DEV_LOCAL_FORECAST_SCORE",
    )
    grouped = {}
    for number, (line, payload) in enumerate(lines):
        if not any(kind + " marker_id=" in line for kind in kinds):
            continue
        marker = payload.get("marker_id")
        if marker not in action_markers:
            raise MP11PaperRejected("foreign/unexpected original Paper action marker")
        grouped.setdefault(marker, []).append((number, line, payload))

    last_end = -1
    last_tick = -1
    results = []
    for index, (marker, surface) in enumerate(zip(action_markers, surfaces)):
        rows = grouped.get(marker, ())
        if not rows:
            raise MP11PaperRejected("missing expected original action marker")
        def kind(k):
            return [(n, p) for n, line, p in rows if k+" marker_id=" in line]
        phases = kind("M02_DEV_S50_PHASE")
        locks = kind("S50_DEV_SURFACE_LOCK")
        begins = kind("S50_DEV_WAIT_BEGIN")
        waits = kind("S50_DEV_WAIT_TICK")
        inputs = kind("S50_DEV_INPUT_TICK")
        fixed = kind("S50_DEV_LOCAL_FORECAST_FIXED")
        scored = kind("S50_DEV_LOCAL_FORECAST_SCORE")
        if (len(phases) != 2 or [x[1].get("phase") for x in phases]
                != ["PRE_FORWARD", "POST_CLEAR"]
                or len(locks) != 1 or len(begins) != 1
                or len(waits) != 8 or len(inputs) != 8
                or len(fixed) != 7 or len(scored) != 7):
            raise MP11PaperRejected("wrong per-action phases, WAIT or forecast count")
        if (any(row.get("world") != world_uuid for _, row in phases)
                or begins[0][1].get("world") != world_uuid):
            raise MP11PaperRejected("foreign Paper phase or WAIT begin World")
        lock = locks[0][1]
        expected_mode = ("GRASS_BLOCK_5X5_READONLY" if surface=="GRASS_BLOCK"
                         else "PACKED_ICE_5X5")
        if (lock.get("world") != world_uuid
                or lock.get("subject_uuid") != subject_uuid
                or lock.get("status") != "REAL_PAPER_PRE_ACTION_SURFACE_LOCK"
                or lock.get("target_material") != surface
                or lock.get("original_material") != "GRASS_BLOCK"
                or lock.get("mode") != expected_mode
                or lock.get("blocks_verified") != "25"
                or lock.get("on_ground") != "true"):
            raise MP11PaperRejected("per-action Paper original surface lock mismatch")
        if not (
            last_end < phases[0][0] < locks[0][0] < phases[1][0]
            < begins[0][0] < waits[0][0]
        ):
            raise MP11PaperRejected("overlapping World experiments or postaction lock")
        motions = []
        ticks = []
        for i, (wait_num, wait) in enumerate(waits):
            input_num, input_row = inputs[i]
            if (wait.get("world") != world_uuid or input_row.get("world") != world_uuid
                    or input_row.get("subject_uuid") != subject_uuid
                    or int(wait.get("index", -1)) != i+1
                    or int(input_row.get("index",-1)) != i+1
                    or not wait_num < input_num
                    or (i<7 and input_num >= waits[i+1][0])):
                raise MP11PaperRejected("input/WAIT event identity/order mismatch")
            tick = int(wait["tick"])
            if (int(input_row.get("tick",-1)) != tick
                    or (ticks and tick != ticks[-1]+1)
                    or tick <= last_tick):
                raise MP11PaperRejected("out-of-order/overlapping original Paper tick")
            start=[float(wait["from_"+axis]) for axis in "xyz"]
            end=[float(wait[axis]) for axis in "xyz"]
            if not all(math.isfinite(z) for z in (*start,*end)):
                raise MP11PaperRejected("nonfinite real original position")
            motions.append(math.dist(start,end))
            ticks.append(tick)
        for i in range(7):
            a,b = fixed[i], scored[i]
            if not (
                waits[i][0] < a[0] < waits[i+1][0] < b[0]
                and a[1].get("world") == b[1].get("world") == world_uuid
                and a[1].get("subject_uuid") == b[1].get("subject_uuid") == subject_uuid
                and int(a[1].get("prior_tick",-1)) == ticks[i]
                and int(a[1].get("target_tick",-1)) == ticks[i+1]
                and int(b[1].get("target_tick",-1)) == ticks[i+1]
                and a[1].get("ticket_sha256") == b[1].get("ticket_sha256")
            ):
                raise MP11PaperRejected("per-action future Paper forecast not frozen before target")
        last_end = max(n for n,_,_ in rows)
        last_tick = ticks[-1]
        results.append(TrialPaperSource(
            marker_id=marker, world_uuid=world_uuid, subject_uuid=subject_uuid,
            paper_sha256=hashlib.sha256(original).hexdigest(),
            condition=surface, ordinal=index+1,
            wait_ticks=tuple(ticks), wait_motion_m=tuple(motions),
        ))
    return tuple(results)
