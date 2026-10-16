"""R V7 prospective independent Paper BASAL source-log readback, offline only.

A source log is not proof of origin without external original-byte attestation.
This parser does not change historical V7, qualify a new JAR, or start a World.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any

CLASSIFICATION = "RSEE_V7_M02_DIRECT_BASAL_DEV_SOURCE_SHAPE_REVIEW_ONLY"
RATES = {"BASE_ON": 0.001, "SHAM_ON": 0.001, "BASAL_ZERO": 0.0,
         "WALK_ZERO": 0.001, "BOTH_ZERO": 0.0}
NUM = r"([+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)"
WRITE_RE = re.compile(
    r"M02_DEV_BASAL_WRITE id=(\d+) world_full_time=(\d+)"
    + r" before=" + NUM + r" requested=" + NUM
    + r" write_target=" + NUM + r" observed_after=" + NUM
    + r" cumulative_requested=" + NUM
    + r" x=" + NUM + r" y=" + NUM + r" z=" + NUM
    + r" yaw=" + NUM + r" pitch=" + NUM + r"\s*$"
)
BODY_RE = re.compile(
    r"M02_DEV_BODY sampled_tick=(\d+) player=RelaySelf"
    + r".*? exhaustion=" + NUM + r"(?:\s|$)"
)
BODY_CHECKPOINTS = (1, 20, 100, 200)
MAX_LOG_BYTES = 8 * 1024 * 1024
MAX_RECORDED_WRITES = 500


class SourceRejected(ValueError):
    """Invalid, incomplete, or falsely admitted source telemetry."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceRejected(reason)


def finite_number(value: str) -> float:
    try:
        n = float(value)
    except (ValueError, OverflowError) as exc:
        raise SourceRejected("malformed numeric source") from exc
    need(math.isfinite(n), "nonfinite numeric source")
    return n


def review_original_server_log(raw: bytes, arm: str) -> dict[str, Any]:
    """Read genuine-format source bytes; never attest who produced those bytes."""
    need(type(raw) is bytes and 0 < len(raw) <= MAX_LOG_BYTES,
         "missing/oversized original Paper log")
    need(type(arm) is str and arm in RATES, "unknown BASAL factor")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise SourceRejected("non-UTF8 original Paper log") from exc
    need(any("M02_DEV_ONLY: candidate physics" in line for line in lines),
         "no candidate Paper source startup")
    need(not any("M02_DEV_DISABLED:" in line for line in lines),
         "disabled Paper source cannot bill BASAL")
    writes: list[tuple[int, int, tuple[float, ...]]] = []
    bodies: dict[int, float] = {}
    for line in lines:
        if "M02_DEV_BASAL_WRITE " in line:
            match = WRITE_RE.search(line)
            need(match is not None, "truncated/malformed BASAL write original")
            vals = tuple(finite_number(x) for x in match.groups()[2:])
            writes.append((int(match.group(1)), int(match.group(2)), vals))
            need(len(writes) <= MAX_RECORDED_WRITES, "excess BASAL write source")
        if "M02_DEV_BODY sampled_tick=" in line:
            body = BODY_RE.search(line)
            need(body is not None, "malformed Paper native body checkpoint")
            tick = int(body.group(1))
            need(tick not in bodies, "duplicate native body checkpoint")
            bodies[tick] = finite_number(body.group(2))
    need(len(writes) >= 200, "missing direct 200 BASAL Paper source writes")
    need(all(w[0] == i + 1 for i, w in enumerate(writes)),
         "missing/replayed/duplicate BASAL source write counter")
    need(all(writes[i][1] == writes[i - 1][1] + 1
             for i in range(1, len(writes))),
         "missing/repeated Paper world full-time tick")
    need(all(i in bodies for i in BODY_CHECKPOINTS),
         "missing body/native readback checkpoint")
    expected_rate = RATES[arm]
    total = 0.0
    observed_by_id = {}
    for tick, _, vals in writes:
        before, charge, target, after, cumulative, x, y, z, yaw, pitch = vals
        need(all(math.isfinite(v) for v in (x, y, z, yaw, pitch)),
             "invalid pose in source write")
        need(0 <= before <= 40 and 0 <= after <= 40,
             "invalid native exhaustion readback")
        need(charge >= 0 and abs(charge - expected_rate) <= 1e-9,
             "unexpected BASAL source-side requested rate")
        need(abs(target - (before + charge)) <= 1e-6,
             "BASAL setExhaustion write input does not match")
        total += charge
        need(abs(cumulative - total) <= 1e-6,
             "BASAL running source request sum mismatch")
        observed_by_id[tick] = after
    for tick in BODY_CHECKPOINTS:
        need(abs(observed_by_id[tick] - bodies[tick]) <= 1e-5,
             "body checkpoint not tied to direct BASAL source write")
    first200 = writes[:200]
    requested200 = sum(w[2][1] for w in first200)
    need(abs(requested200 - expected_rate * 200) <= 1e-8,
         "200 source tick baseline request mismatch")
    return {
        "classification": CLASSIFICATION,
        "arm": arm,
        "source_log_sha256": hashlib.sha256(raw).hexdigest(),
        "source_writes_recorded": len(writes),
        "first200_source_player_callbacks": 200,
        "first_world_full_time": first200[0][1],
        "world_full_time_at_200th": first200[-1][1],
        "body_readbacks_independently_parsed": list(BODY_CHECKPOINTS),
        "configured_basal_request_per_tick": expected_rate,
        "direct_source_requested_basal_cumulative_first200": requested200,
        "write_side_consistent_with_config": True,
        "native_meter_causality_attested": False,
        "s50_move_bracket_attested": False,
        "s_source_binary_and_original_bytes_authenticated_here": False,
        "changed_profile_engineering_qualified": False,
        "science_trials_credited": 0,
        "v_science_go": False,
        "production_go": False,
    }
