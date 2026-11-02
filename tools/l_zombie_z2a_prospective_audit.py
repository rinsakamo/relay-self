"""Independent Z2a Paper pre-outcome CHEAP freeze audit.

This can certify Paper-original textual ordering and deterministic CHEAP
math, if the original JVM/stdout provenance is separately verified.
It CANNOT certify a Gemma prediction, client↔Paper tick join or learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

from tools.l_zombie_paper_original_audit import (
    PaperZombieSourceRejected,
    audit_paper_zombie_window,
)

FREEZE = "L_ZOMBIE_CHEAP_FREEZE_V2 "
TICK = "L_ZOMBIE_TICK_V1 "
FLOAT_EPS = 2e-11
MAX_RAW = 16_000_000
FREEZE_KEYS = {
    "marker", "session", "world", "entity_uuid", "entity_id",
    "source_first_tick", "issued_tick", "target_tick",
    "stationary_x", "stationary_z", "velocity_x", "velocity_z",
}
TICK_KEYS = {
    "marker", "session", "world", "entity_uuid", "entity_id", "spawn_instance",
    "server_tick", "offset", "x", "y", "z",
}


def _row(line: str, prefix: str) -> dict[str, str]:
    fragment = line.split(prefix, 1)[1]
    parts = fragment.split(" ")
    if not parts or any(re.fullmatch(r"[a-z_]+=[^\s=]+", part) is None for part in parts):
        raise PaperZombieSourceRejected("malformed prospective source token")
    data = dict(item.split("=", 1) for item in parts)
    if len(data) != len(parts):
        raise PaperZombieSourceRejected("duplicate source field")
    return data


def _finite_number(data: dict, key: str) -> float:
    try:
        value = float(data[key])
    except (KeyError, ValueError) as exc:
        raise PaperZombieSourceRejected("invalid frozen numeric source") from exc
    if not math.isfinite(value) or abs(value) > 30_000_000:
        raise PaperZombieSourceRejected("unbounded frozen numeric source")
    return value


def _strict_int(data: dict, key: str) -> int:
    token = data.get(key, "")
    if re.fullmatch(r"(0|[1-9][0-9]*)", token) is None:
        raise PaperZombieSourceRejected("non-integer frozen source")
    value = int(token)
    if value >= 2**31:
        raise PaperZombieSourceRejected("frozen source tick out of range")
    return value


def audit_z2a_prospective(
    original: bytes, *, sha256: str, marker: str, session: str,
) -> dict:
    """Require EXACT Paper tick10 record then one freeze before tick11."""
    if (
        type(original) is not bytes or not 0 < len(original) <= MAX_RAW
        or not original.endswith(b"\n")
        or type(sha256) is not str or hashlib.sha256(original).hexdigest() != sha256
    ):
        raise PaperZombieSourceRejected("original/SHA mismatch or unbounded source")
    paper = audit_paper_zombie_window(
        original, original_sha256=sha256,
        expected_marker=marker, expected_session=session,
    )
    lines = original.decode("utf-8", errors="strict").splitlines()
    observations: dict[int, tuple[int, dict[str, str]]] = {}
    freezes: list[tuple[int, dict[str, str]]] = []
    for index, line in enumerate(lines):
        if TICK in line:
            row = _row(line, TICK)
            if row.get("marker") == marker:
                if set(row) != TICK_KEYS or row.get("session") != session:
                    raise PaperZombieSourceRejected("invalid matching tick source")
                off = _strict_int(row, "offset")
                if off in observations:
                    raise PaperZombieSourceRejected("duplicate prior Paper observation")
                observations[off] = (index, row)
        if FREEZE in line:
            row = _row(line, FREEZE)
            # Any freeze line must be accounted for; no extra/unmatched candidates.
            freezes.append((index, row))
    if set(observations) != set(range(31)) or len(freezes) != 1:
        raise PaperZombieSourceRejected("31 Paper ticks and exactly ONE freeze required")
    index, prediction = freezes[0]
    if (
        set(prediction) != FREEZE_KEYS
        or prediction["marker"] != marker
        or prediction["session"] != session
        or prediction["world"] != paper.world_uuid
        or prediction["entity_uuid"] != paper.entity_uuid
        or _strict_int(prediction, "entity_id") != paper.entity_id
        or _strict_int(prediction, "source_first_tick") != paper.pre_source_tick
        or _strict_int(prediction, "issued_tick") != paper.forecast_freeze_tick
        or _strict_int(prediction, "target_tick") != paper.target_tick
        or not observations[10][0] < index < observations[11][0]
    ):
        raise PaperZombieSourceRejected("forecast after outcome, wrong owner or wrong server tick")
    _, first = observations[0]
    _, present = observations[10]
    _, target = observations[30]
    x0, z0 = _finite_number(first, "x"), _finite_number(first, "z")
    x10, z10 = _finite_number(present, "x"), _finite_number(present, "z")
    x30, z30 = _finite_number(target, "x"), _finite_number(target, "z")
    expected = {
        "stationary_x": x10,
        "stationary_z": z10,
        "velocity_x": x10 + 2*(x10-x0),
        "velocity_z": z10 + 2*(z10-z0),
    }
    points = {key: _finite_number(prediction, key) for key in expected}
    if any(abs(points[key] - value) > FLOAT_EPS for key, value in expected.items()):
        raise PaperZombieSourceRejected("frozen CHEAP used data not available at tick10")
    return {
        "schema": "L_ZOMBIE_Z2A_PROSPECTIVE_CHEAP_V2",
        "classification": "Z2A_PAPER_PREOUTCOME_CHEAP_FROZEN_AND_SCORED",
        "paper_original_sha256": sha256,
        "marker": marker, "session": session,
        "world_uuid": paper.world_uuid,
        "entity_uuid": paper.entity_uuid,
        "entity_id": paper.entity_id,
        "issued_tick": paper.forecast_freeze_tick,
        "target_tick": paper.target_tick,
        "freeze_before_tick11": True,
        "exact_20_tick_target": True,
        "original_freeze_line": index + 1,
        "target_observation_line": observations[30][0] + 1,
        "pre_source_xz_m": [x0, z0],
        "issued_source_xz_m": [x10, z10],
        "original_target_xz_m": [x30, z30],
        "stationary_forecast_xz_m": [points["stationary_x"], points["stationary_z"]],
        "velocity_forecast_xz_m": [points["velocity_x"], points["velocity_z"]],
        "stationary_error_m": math.hypot(points["stationary_x"]-x30, points["stationary_z"]-z30),
        "constant_velocity_error_m": math.hypot(points["velocity_x"]-x30, points["velocity_z"]-z30),
        "forecast_owner": "PAPER_CHEAP_NOT_L2",
        "model_calls": 0,
        "self_actions": 0,
        "model_learning_admitted": False,
        "native_client_tick_join_attested": False,
        "real_gemma_forecast_attested": False,
        "physical_paper_owner_attested_by_this_parser": False,
        "qualification_go": False,
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
            not args.paper_original.is_absolute() or args.paper_original.is_symlink()
            or not args.report.is_absolute() or args.report.is_symlink()
            or args.report.exists() or args.report == args.paper_original
        ):
            raise PaperZombieSourceRejected("absolute original and exclusive report required")
        report = audit_z2a_prospective(
            args.paper_original.read_bytes(), sha256=args.sha256,
            marker=args.marker, session=args.session,
        )
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except (PaperZombieSourceRejected, OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Z2A_ORIGINAL_AUDIT_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": report["classification"],
        "stationary_error_m": report["stationary_error_m"],
        "constant_velocity_error_m": report["constant_velocity_error_m"],
        "original_sha256": report["paper_original_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
