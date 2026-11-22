"""Q10 read-only dual-clock U24 diagnostic, entirely synthetic source fixtures."""
from __future__ import annotations

import uuid

import pytest

from experiments.q_lane_q10_u24_paper_clock_diagnostic_dev import (
    Q10ClockHold,
    audit_u24_two_source_clock_progress,
)
from test_q_lane_q9_u24_s1_stop_diagnostic_dev import ROLES, _make_source, _seal

BOOT = "00a4cb1e-c9c5-445c-b987-d437e7c89aa8"
WORLD = "7b5eb607-a25c-4e64-af1c-2d82dfab29f4"
ACTOR = "dc810915-18c0-4d74-9cb8-476d047e281c"


def _event(kind, tick, x, *, actor=ACTOR, world=WORLD, boot=BOOT):
    return (
        f"P0D_RESIDENT event={kind} boot={boot} tick={tick} "
        f"world={world} actor={actor} name=RelaySelf "
        f"x={x} y=64.0 z=0.0 source=PAPER_MAIN_THREAD\n"
    )


def _fixtures(tmp_path, *, trial="two_moves", short_paper=False):
    _make_source(tmp_path, trial)
    point_ticks = (105, 110) if short_paper else (105, 115, 135)
    events = [
        _event("JOIN", 100, 0),
        _event("MOVE", point_ticks[0], 0.3),
        *[_event("PRESENT", tick, 0.3) for tick in point_ticks[1:]],
        _event("QUIT", point_ticks[-1] + 1, 0.3),
    ]
    return _write(tmp_path, trial, events), events


def _write(root, trial, events, *, header=True, newline=True):
    ready = (
        f"P0D_RESIDENT_READY boot={BOOT} "
        f"source=PAPER_MAIN_THREAD version=1\n" if header else ""
    )
    raw = (ready + "".join(events)).encode()
    if not newline:
        raw = raw.rstrip(b"\n")
    (root / ROLES["paper_ticks"]).write_bytes(raw)
    return _seal(root, trial)


def _audit(root, manifest, trial="two_moves"):
    return audit_u24_two_source_clock_progress(
        root=root, manifest_path=manifest, trial=trial,
    )


def test_original_paper_ticks_advance_while_native_stop_ticks_stall(tmp_path):
    manifest, _ = _fixtures(tmp_path)
    result = _audit(tmp_path, manifest)
    assert result["classification"] == (
        "NATIVE_STOP_CLOCK_SHORT_WITH_PAPER_RUN_PROGRESS"
    )
    assert result["native"]["stop_probe_count"] == 24
    assert result["native"]["native_stop_tick_span"] == 0
    assert result["paper"]["paper_observed_tick_span"] == 35
    assert result["paper"]["paper_player_quit_recorded"]
    assert not result["paper_progress_during_exact_stop_probes_attested"]
    assert not result["real_world_dev_pass"]


def test_paper_and_native_both_short_not_called_clock_frozen(tmp_path):
    manifest, _ = _fixtures(tmp_path, short_paper=True)
    result = _audit(tmp_path, manifest)
    assert result["classification"] == (
        "NATIVE_STOP_CLOCK_SHORT_PAPER_PROGRESS_INCONCLUSIVE"
    )


def test_stop_fault_record_is_not_mistaken_for_settled_s1(tmp_path):
    manifest, _ = _fixtures(tmp_path, trial="stop_failure")
    result = _audit(tmp_path, manifest, trial="stop_failure")
    assert result["classification"] == "STOP_FAILURE_CAPTURE_REQUIRES_OS_EXIT_REVIEW"
    assert "native" not in result
    assert not result["real_world_dev_pass"]


@pytest.mark.parametrize("bad", [
    "actor_swap", "world_swap", "boot_swap", "nonfinite_x",
    "duplicate_field", "duplicate_ready", "missing_ready",
    "rejoin", "duplicate_quit", "position_after_quit",
    "tick_regression", "no_join", "no_sample",
    "partial_line", "missing_paper", "noncanonical_uuid",
])
def test_hostile_paper_source_remains_hold(tmp_path, bad):
    manifest, events = _fixtures(tmp_path)
    if bad == "actor_swap":
        events[1] = _event("MOVE", 105, 0.3, actor=str(uuid.uuid4()))
    elif bad == "world_swap":
        events[1] = _event("MOVE", 105, 0.3, world=str(uuid.uuid4()))
    elif bad == "boot_swap":
        events[1] = _event("MOVE", 105, 0.3, boot=str(uuid.uuid4()))
    elif bad == "nonfinite_x":
        events[1] = events[1].replace("x=0.3", "x=nan")
    elif bad == "duplicate_field":
        events[1] = events[1].replace(
            "source=PAPER_MAIN_THREAD",
            "x=0.3 source=PAPER_MAIN_THREAD",
        )
    elif bad == "duplicate_ready":
        events.append(
            f"P0D_RESIDENT_READY boot={BOOT} "
            "source=PAPER_MAIN_THREAD version=1\n"
        )
    elif bad == "missing_ready":
        manifest = _write(tmp_path, "two_moves", events, header=False)
    elif bad == "rejoin":
        events.insert(-1, _event("JOIN", 136, 0.3))
    elif bad == "duplicate_quit":
        events.append(_event("QUIT", 137, 0.3))
    elif bad == "position_after_quit":
        events.append(_event("PRESENT", 137, 0.3))
    elif bad == "tick_regression":
        events[2] = _event("PRESENT", 103, 0.3)
    elif bad == "no_join":
        del events[0]
    elif bad == "no_sample":
        events[:] = [
            _event("JOIN", 100, 0.0),
            _event("QUIT", 101, 0.0),
        ]
    elif bad == "partial_line":
        manifest = _write(tmp_path, "two_moves", events, newline=False)
    elif bad == "missing_paper":
        (tmp_path / ROLES["paper_ticks"]).unlink()
        with pytest.raises((Q10ClockHold, ValueError, OSError)):
            _audit(tmp_path, manifest)
        return
    elif bad == "noncanonical_uuid":
        events[1] = _event("MOVE", 105, 0.3, actor=ACTOR.upper())
    if bad not in {"missing_ready", "partial_line"}:
        manifest = _write(tmp_path, "two_moves", events)
    with pytest.raises((Q10ClockHold, ValueError)):
        _audit(tmp_path, manifest)


def test_original_seven_sources_stay_byte_identical(tmp_path):
    manifest, _ = _fixtures(tmp_path)
    paths = [tmp_path / role for role in ROLES.values()]
    before = {str(path): path.read_bytes() for path in paths}
    _audit(tmp_path, manifest)
    assert before == {str(path): path.read_bytes() for path in paths}
