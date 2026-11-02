"""Independent source-only movement readback for one genuine Paper zombie window.

DOES NOT prove why a zombie moved, who it chased, a native-client exact-tick
join, a Gemma prediction, or an autonomous safe L0 response.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from tools.l_zombie_paper_original_audit import (
    PaperZombieSourceRejected,
    audit_paper_zombie_window,
)

MAX_STEP_M = 0.6
MIN_NET_MOVEMENT_M = 0.02


def audit_z1b_movement(
    original: bytes, *, sha256: str, marker: str, session: str,
) -> dict:
    """Require genuine original-shaped full source first, then bound every move."""
    paper = audit_paper_zombie_window(
        original, original_sha256=sha256,
        expected_marker=marker, expected_session=session,
    )
    rows: list[tuple[float, float]] = []
    for line in original.decode("utf-8", errors="strict").splitlines():
        needle = f"L_ZOMBIE_TICK_V1 marker={marker} session={session} "
        if needle not in line:
            continue
        values = {}
        for item in line.split(needle, 1)[1].split(" "):
            key, value = item.split("=", 1)
            values[key] = value
        rows.append((float(values["x"]), float(values["z"])))
    if len(rows) != 31:
        raise PaperZombieSourceRejected("movement requires all original 31 tick rows")
    segments = [math.dist(rows[i-1], rows[i]) for i in range(1, 31)]
    if any(not math.isfinite(step) or step > MAX_STEP_M for step in segments):
        raise PaperZombieSourceRejected("movement includes nonphysical step / teleport")
    total = sum(segments)
    net = math.dist(rows[0], rows[30])
    # Valid untouched original source can still have an inert zombie;
    # classify it explicitly as NOT moving, not an instrumentation failure.
    return {
        "schema": "L_ZOMBIE_Z1B_MOVEMENT_SOURCE_V1",
        "classification": (
            "Z1B_PAPER_MOVEMENT_OBSERVED_SOURCE_ONLY"
            if net > MIN_NET_MOVEMENT_M
            else "Z1B_PAPER_SOURCE_VALID_BUT_MOTION_NOT_ESTABLISHED"
        ),
        "original_sha256": sha256,
        "entity_uuid": paper.entity_uuid,
        "world_uuid": paper.world_uuid,
        "start_tick": paper.pre_source_tick,
        "freeze_reference_tick": paper.forecast_freeze_tick,
        "target_tick": paper.target_tick,
        "same_zombie": True,
        "sample_count": 31,
        "max_step_m": max(segments),
        "total_path_length_m": total,
        "net_horizontal_displacement_m": net,
        "movement_observed": net > MIN_NET_MOVEMENT_M,
        "client_paper_tick_join_attested": False,
        "causal_pursuit_attested": False,
        "real_gemma_hypothesis": False,
        "self_action_count": 0,
        "qualifying_science": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-original", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if (
            not args.paper_original.is_absolute()
            or not args.report.is_absolute()
            or args.paper_original.is_symlink()
            or args.report.is_symlink()
            or args.paper_original == args.report
            or args.report.exists()
        ):
            raise PaperZombieSourceRejected("exclusive report, absolute real original required")
        raw = args.paper_original.read_bytes()
        report = audit_z1b_movement(
            raw, sha256=args.sha256, marker=args.marker, session=args.session,
        )
        with args.report.open("x", encoding="utf-8") as dest:
            json.dump(report, dest, sort_keys=True, indent=2)
            dest.write("\n")
    except (PaperZombieSourceRejected, OSError, ValueError) as exc:
        print(f"L_Z1B_MOTION_AUDIT_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": report["classification"],
        "net_horizontal_displacement_m": report["net_horizontal_displacement_m"],
    }, sort_keys=True))
    return 0 if report["movement_observed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
