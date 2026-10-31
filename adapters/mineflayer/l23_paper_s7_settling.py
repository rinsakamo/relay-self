"""L23 read-only Paper/S7 sampled-settling correlation (no authority transfer).

The Paper S50_DEV_WAIT_* callback schema belongs to S owner PR #545.
An operator-supplied Paper marker is NOT a proof of the moment at which
S15 clear became effective. Paper callback quiet != input-idle for a full
World tick. This module cannot qualify Goal, L10, P1 WAIT or any R result.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerStreamDecoder,
)

SCHEMA = "L23_PAPER_S7_SAMPLED_SETTLING_READBACK_V1"
MAX_PAPER_BYTES = 2_000_000
MAX_PAPER_LINES = 10000
MAX_WORLD_LABEL = 128
MAX_MARKER = 256


class L23SourceRejected(ValueError):
    """Paper original or cross-source association is missing/unsafe."""


@dataclass(frozen=True, slots=True)
class L23PaperReadback:
    schema: str
    session_id: str
    action_id: str
    paper_world: str
    marker_id: str
    paper_original_sha256: str
    s7_received_sha256: str
    s16_original_sha256: str
    paper_first_tick: int
    paper_last_tick: int
    paper_sample_count: int
    paper_activity_ticks: tuple[int, ...]
    paper_last_to_s7_goal_distance_m: float
    paper_s7_geometry_compatible: bool
    paper_sample_state: str
    clock_alignment: str = "NOT_ATTESTED"
    paper_effective_input_clear_tick: str = "NOT_ATTESTED"
    paper_full_tick_input_idle: bool = False
    world_session_independently_bound: bool = False
    physical_stability_verified: bool = False
    accepted_goal_status: str = "UNDETERMINED"
    qualified_real_learning_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0
    p1_wait_ticks_admitted: int = 0


def _paper_rows(raw: bytes, label: str) -> list[dict[str, str]]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_PAPER_BYTES:
        raise L23SourceRejected("missing or unbounded immutable Paper original")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise L23SourceRejected("Paper original is not UTF-8") from exc
    if len(lines) > MAX_PAPER_LINES:
        raise L23SourceRejected("unbounded Paper original lines")
    found = []
    for line in lines:
        if label not in line:
            continue
        # Expected source is a single Java log event per physical callback.
        # Reject ambiguous doubled markers / duplicate tokens.
        if line.count(label) != 1:
            raise L23SourceRejected("ambiguous Paper marker")
        tokens = line.split(label, 1)[1].split()
        if not tokens:
            raise L23SourceRejected("empty Paper source event")
        row = {}
        for token in tokens:
            if token.count("=") != 1:
                raise L23SourceRejected("malformed Paper source field")
            key, value = token.split("=", 1)
            if not key or not value or key in row:
                raise L23SourceRejected("duplicate/empty Paper source field")
            row[key] = value
        found.append(row)
    return found


def _num(row: dict, key: str, *, integer: bool = False) -> float | int:
    try:
        val = float(row[key])
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise L23SourceRejected(f"missing/invalid Paper {key}") from exc
    if not math.isfinite(val) or val < 0 and integer:
        raise L23SourceRejected(f"nonfinite/negative Paper {key}")
    if integer:
        if val != int(val):
            raise L23SourceRejected(f"noninteger Paper {key}")
        return int(val)
    return val


def _pose(row: dict, prefix: str = "") -> tuple[float, float, float]:
    return tuple(float(_num(row, prefix + k)) for k in ("x", "y", "z"))


def inspect_l23_paper_s7(
    *, received_original: bytes, sent_original: bytes, s7_receipt: dict,
    s16_original: bytes, plan, session_id: str, action_id: str,
    paper_original: bytes, expected_world: str,
    geometry_limit_m: float = 0.05,
) -> L23PaperReadback:
    """Join two read-only originals only at *shape/identity/geometry* level.

    Exactly eight consecutive S-owned WAIT sampling callbacks are required
    here because that is the frozen S50 source schema. This is NOT an
    independently authenticated cross-clock join or S49 clear-time proof.
    """
    if (
        not isinstance(expected_world, str)
        or not 0 < len(expected_world) <= MAX_WORLD_LABEL
        or type(geometry_limit_m) not in (int, float)
        or not math.isfinite(geometry_limit_m)
        or not 0 < geometry_limit_m <= 0.1
    ):
        raise L23SourceRejected("explicit bounded Paper World and geometry required")
    marker = f"{action_id}-{session_id}"
    if not isinstance(action_id, str) or not isinstance(session_id, str) or (
        not 0 < len(marker) <= MAX_MARKER
    ):
        raise L23SourceRejected("invalid owner identity")
    l22 = inspect_l22_settling(
        received_original=received_original, sent_original=sent_original,
        s7_receipt=s7_receipt, s16_original=s16_original, plan=plan,
        session_id=session_id, action_id=action_id,
    )
    phase_rows = _paper_rows(paper_original, "M02_DEV_S50_PHASE ")
    if (
        len(phase_rows) != 2
        or [r.get("phase") for r in phase_rows]
        != ["PRE_FORWARD", "POST_CLEAR"]
        or any(r.get("marker_id") != marker for r in phase_rows)
        or any(r.get("world") != expected_world for r in phase_rows)
        or _num(phase_rows[0], "world_full_time", integer=True)
        > _num(phase_rows[1], "world_full_time", integer=True)
    ):
        raise L23SourceRejected(
            "Paper PRE_FORWARD/POST_CLEAR causal console observation absent"
        )
    starts = _paper_rows(paper_original, "S50_DEV_WAIT_BEGIN ")
    samples = _paper_rows(paper_original, "S50_DEV_WAIT_TICK ")
    if len(starts) != 1 or len(samples) != 8:
        raise L23SourceRejected("missing/duplicate Paper callback bracket (8 ticks)")
    start = starts[0]
    if start.get("marker_id") != marker or start.get("world") != expected_world:
        raise L23SourceRejected("unbound Paper marker or World")
    begin = _num(start, "tick", integer=True)
    if begin < _num(phase_rows[1], "world_full_time", integer=True):
        raise L23SourceRejected("Paper WAIT started before Paper POST_CLEAR marker")
    previous = _pose(start)
    packet = _num(start, "packets", integer=True)
    blocks = _num(start, "blocks")
    meter = _num(start, "tick_meter_blocks")
    combat = _num(start, "combat_events", integer=True)
    swings = _num(start, "swing_events", integer=True)
    basal = _num(start, "basal_ticks", integer=True)
    activity = []
    for i, row in enumerate(samples, 1):
        tick = _num(row, "tick", integer=True)
        if (
            row.get("marker_id") != marker
            or row.get("world") != expected_world
            or _num(row, "index", integer=True) != i
            or tick != begin + i
            or _pose(row, "from_") != previous
        ):
            raise L23SourceRejected("missing/foreign/gapped Paper World callback")
        current = _pose(row)
        new_packet = _num(row, "motion_packets", integer=True)
        new_blocks = _num(row, "motion_blocks")
        new_meter = _num(row, "tick_meter_blocks")
        new_combat = _num(row, "combat_events", integer=True)
        new_swings = _num(row, "swing_events", integer=True)
        new_basal = _num(row, "basal_ticks", integer=True)
        if (
            new_packet < packet or new_blocks < blocks or new_meter < meter
            or new_combat < combat or new_swings < swings
            or new_basal != basal + 1
            or row.get("sprint") not in ("true", "false")
            or row.get("sneak") not in ("true", "false")
            or row.get("swimming") not in ("true", "false")
        ):
            raise L23SourceRejected("regressed/corrupted Paper activity counters")
        quiet_sample = (
            current == previous
            and (new_packet, new_blocks, new_meter, new_combat, new_swings)
            == (packet, blocks, meter, combat, swings)
            and all(row[k] == "false" for k in ("sprint", "sneak", "swimming"))
        )
        if not quiet_sample:
            activity.append(tick)
        previous = current
        packet, blocks, meter, combat, swings, basal = (
            new_packet, new_blocks, new_meter, new_combat,
            new_swings, new_basal,
        )
    # Independently decode the last native S7 probe; no trust in derived report.
    decoder = MineflayerStreamDecoder()
    try:
        frames = [
            decoder.decode(line.decode("utf-8"))
            for line in received_original.splitlines(keepends=True)
        ]
    except (ValueError, TypeError, UnicodeError) as exc:
        raise L23SourceRejected("S7 source changed during readback") from exc
    last = frames[-1]
    if (
        not isinstance(last, MineflayerObservation)
        or last.kind != "probe"
        or last.seq != l22.second_probe_seq
        or last.session_id != session_id
    ):
        raise L23SourceRejected("native Goal terminal source missing")
    native = last.snapshot.position
    distance = math.dist(previous, (native.x, native.y, native.z))
    compatible = distance <= geometry_limit_m
    return L23PaperReadback(
        schema=SCHEMA, session_id=session_id, action_id=action_id,
        paper_world=expected_world, marker_id=marker,
        paper_original_sha256=hashlib.sha256(paper_original).hexdigest(),
        s7_received_sha256=l22.received_sha256,
        s16_original_sha256=l22.s16_original_sha256,
        paper_first_tick=int(begin) + 1, paper_last_tick=int(begin) + 8,
        paper_sample_count=8, paper_activity_ticks=tuple(activity),
        paper_last_to_s7_goal_distance_m=distance,
        paper_s7_geometry_compatible=compatible,
        paper_sample_state=(
            "PAPER_SAMPLED_ACTIVITY" if activity else
            "PAPER_8_QUIET_SAMPLES_ONLY"
        ),
    )
