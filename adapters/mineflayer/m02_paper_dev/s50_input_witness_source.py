"""S-owned read-only Paper input witness (not effective clear or full-tick idle).

Paper PlayerInputEvent reports input *updates*. Player.getCurrentInput()
reports the most recently provided input at one server callback. Neither
is the complete packet/input history between consecutive world callbacks.
"""
from __future__ import annotations

from dataclasses import dataclass

PREFIX = "S50_DEV_INPUT_TICK "
MAX_SOURCE_BYTES = 2_000_000
FLAGS = ("forward", "backward", "left", "right", "jump", "sneak", "sprint")
COVERAGE = "LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY"


class S50InputWitnessRejected(ValueError):
    """Incomplete, foreign, or corrupted S-owned source."""


@dataclass(frozen=True, slots=True)
class S50InputWitnessReadback:
    marker_id: str
    world: str
    subject_uuid: str
    first_tick: int
    last_tick: int
    sampled_input_active_ticks: tuple[int, ...]
    input_event_count_final: int
    input_event_observed: bool
    coverage: str = COVERAGE
    effective_client_clear_tick: str = "NOT_ATTESTED"
    entire_tick_input_idle: bool = False
    physical_stability_verified: bool = False
    goal_admitted: bool = False
    p1_wait_ticks_admitted: int = 0
    l10_episodes_admitted: int = 0


def _fields(line: str) -> dict[str, str]:
    if line.count(PREFIX) != 1:
        raise S50InputWitnessRejected("ambiguous Paper input sample")
    tokens = line.split(PREFIX, 1)[1].split()
    row: dict[str, str] = {}
    for token in tokens:
        if token.count("=") != 1:
            raise S50InputWitnessRejected("malformed Paper input field")
        key, value = token.split("=", 1)
        if not key or not value or key in row:
            raise S50InputWitnessRejected("empty/duplicate Paper input field")
        row[key] = value
    required = {
        "marker_id", "world", "subject_uuid", "tick", "index",
        "input_events", "last_input_event_tick", "event_overflow",
        "coverage", "effective_s15_clear_tick", *FLAGS,
    }
    if row.keys() != required:
        raise S50InputWitnessRejected("missing/extra Paper input fields")
    return row


def _int(row: dict[str, str], key: str, *, allow_minus_one: bool = False) -> int:
    raw = row[key]
    if len(raw) > 20 or not raw.isascii() or (
        raw.startswith("-") and (not allow_minus_one or raw != "-1")
    ) or not raw.lstrip("-").isdecimal():
        raise S50InputWitnessRejected(f"invalid Paper input {key}")
    value = int(raw)
    if value < (-1 if allow_minus_one else 0):
        raise S50InputWitnessRejected(f"negative Paper input {key}")
    return value


def review_s50_input_samples(
    original: bytes, *, marker_id: str, world: str, subject_uuid: str,
    start_tick: int, count: int = 8,
) -> S50InputWitnessReadback:
    """Strict 8-sample source readback; no source clock or Goal promotion."""
    if not isinstance(original, bytes) or not 0 < len(original) <= MAX_SOURCE_BYTES:
        raise S50InputWitnessRejected("unbounded/missing Paper input original")
    if (
        not all(isinstance(x, str) and 0 < len(x) <= 128
                for x in (marker_id, world, subject_uuid))
        or type(start_tick) is not int or start_tick < 0 or count != 8
    ):
        raise S50InputWitnessRejected("invalid expected Paper source identity")
    try:
        text = original.decode("utf-8")
    except UnicodeError as exc:
        raise S50InputWitnessRejected("invalid Paper original UTF-8") from exc
    rows = [_fields(line) for line in text.splitlines() if PREFIX in line]
    if len(rows) != count:
        raise S50InputWitnessRejected("not exactly eight Paper input callbacks")
    active: list[int] = []
    previous_events = -1
    previous_last_tick = -1
    for i, row in enumerate(rows, 1):
        tick = _int(row, "tick")
        index = _int(row, "index")
        events = _int(row, "input_events")
        latest = _int(row, "last_input_event_tick", allow_minus_one=True)
        if (
            row["marker_id"] != marker_id or row["world"] != world
            or row["subject_uuid"] != subject_uuid
            or tick != start_tick + i or index != i
            or row["coverage"] != COVERAGE
            or row["effective_s15_clear_tick"] != "NOT_ATTESTED"
            or row["event_overflow"] != "false"
            or events < previous_events
            or latest < previous_last_tick or latest > tick
            or (events == 0 and latest != -1)
            or (events > 0 and latest == -1)
            or (events == previous_events and latest != previous_last_tick)
        ):
            raise S50InputWitnessRejected("uncorrelated/unqualified Paper input")
        for flag in FLAGS:
            if row[flag] not in ("true", "false"):
                raise S50InputWitnessRejected("unknown Paper input flag")
        if any(row[flag] == "true" for flag in FLAGS):
            active.append(tick)
        previous_events, previous_last_tick = events, latest
    return S50InputWitnessReadback(
        marker_id=marker_id, world=world, subject_uuid=subject_uuid,
        first_tick=start_tick + 1, last_tick=start_tick + count,
        sampled_input_active_ticks=tuple(active),
        input_event_count_final=previous_events,
        input_event_observed=previous_events > 0,
    )
