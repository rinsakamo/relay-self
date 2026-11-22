"""Q8 hostile synthetic Paper main-thread position vs original Native evidence."""
from __future__ import annotations

import uuid

import pytest

from experiments.q_lane_q8_paper_native_two_move_audit_dev import (
    Q8PaperHold,
    audit_two_moves_paper,
)
from test_q_lane_q7_native_three_way_audit_dev import _prepare, _save

BOOT = "c8628518-b538-4d75-a0a6-9035d80d61da"
WORLD = "ed0715c3-bd83-4cbb-a4d4-e80b92a3ef1b"
ACTOR = "87b8bc7d-3e64-4337-887f-48c76766da24"


def _paper_event(event, tick, x, *, actor=ACTOR, boot=BOOT, world=WORLD):
    return (
        f"P0D_RESIDENT event={event} boot={boot} tick={tick} "
        f"world={world} actor={actor} name=RelaySelf "
        f"x={x} y=64.0 z=0.0 source=PAPER_MAIN_THREAD\n"
    )


def _fixture(tmp_path):
    rows, messages, wal, stdout, stdin, commands = _prepare(tmp_path)
    _save(rows, messages, wal, stdout, stdin, commands)
    paper = tmp_path / "original-paper-owned.log"
    events = [
        _paper_event("JOIN", 100, 0),
        _paper_event("MOVE", 110, 0.45),
        _paper_event("PRESENT", 120, 0.45),
        _paper_event("PRESENT", 130, 0.45),
        _paper_event("MOVE", 210, 0.90),
        _paper_event("PRESENT", 220, 0.90),
        _paper_event("PRESENT", 230, 0.90),
    ]
    _write(paper, events)
    return wal, stdout, stdin, paper, events


def _write(path, events, *, boot=BOOT):
    header = (
        f"P0D_RESIDENT_READY boot={boot} "
        f"source=PAPER_MAIN_THREAD version=1\n"
    )
    path.write_text(header + "".join(events), encoding="utf-8")


def _audit(inputs):
    wal, stdout, stdin, paper, _ = inputs
    return audit_two_moves_paper(
        wal=wal, native_stdout=stdout, native_stdin=stdin,
        paper_log=paper,
    )


def test_two_original_moves_have_separate_same_actor_paper_windows(tmp_path):
    values = _audit(_fixture(tmp_path))
    assert len(values) == 2
    assert values[0]["paper_ticks"] == [110, 120, 130]
    assert values[1]["paper_ticks"] == [210, 220, 230]
    assert values[0]["paper_actor_uuid"] == ACTOR
    assert values[0]["paper_world_uuid"] == WORLD
    assert values[1]["paper_displacement_m"] == 0.45


@pytest.mark.parametrize("fault", [
    "s2_no_new_position", "s2_no_move_event", "s2_no_samples",
    "s2_too_short_8tick", "s2_too_long_200tick",
    "s2_swapped_actor", "s2_swapped_world", "s2_wrong_stop_position",
    "s2_late_drift", "s2_rejoin", "s2_quit", "boot_changed",
    "ready_replay", "nonfinite_position", "missing_ready",
    "replay_s1_window_only", "malformed_duplicate_field",
    "foreign_log_without_newline", "paper_tick_rewind",
])
def test_hostile_paper_source_fails_independent_q8(tmp_path, fault):
    inputs = _fixture(tmp_path)
    wal, stdout, stdin, paper, events = inputs
    if fault == "s2_no_new_position":
        events[4:] = [
            _paper_event("PRESENT", 210, 0.45),
            _paper_event("PRESENT", 220, 0.45),
            _paper_event("PRESENT", 230, 0.45),
        ]
    elif fault == "s2_no_move_event":
        events[4] = _paper_event("PRESENT", 210, 0.90)
    elif fault in {"s2_no_samples", "replay_s1_window_only"}:
        del events[4:]
    elif fault == "s2_too_short_8tick":
        events[5] = _paper_event("PRESENT", 217, 0.90)
    elif fault == "s2_too_long_200tick":
        events[5] = _paper_event("PRESENT", 411, 0.90)
        events[6] = _paper_event("PRESENT", 422, 0.90)
    elif fault == "s2_swapped_actor":
        events[5] = _paper_event(
            "PRESENT", 220, 0.90, actor=str(uuid.uuid4()),
        )
    elif fault == "s2_swapped_world":
        events[5] = _paper_event(
            "PRESENT", 220, 0.90, world=str(uuid.uuid4()),
        )
    elif fault == "s2_wrong_stop_position":
        events[4] = _paper_event("MOVE", 210, 5.0)
    elif fault == "s2_late_drift":
        events[6] = _paper_event("PRESENT", 230, 0.65)
    elif fault == "s2_rejoin":
        events.insert(4, _paper_event("JOIN", 201, 0.45))
    elif fault == "s2_quit":
        events.insert(4, _paper_event("QUIT", 201, 0.45))
    elif fault == "boot_changed":
        events[5] = _paper_event(
            "PRESENT", 220, 0.90, boot=str(uuid.uuid4()),
        )
    elif fault == "ready_replay":
        events.append(
            f"P0D_RESIDENT_READY boot={BOOT} "
            "source=PAPER_MAIN_THREAD version=1\n"
        )
    elif fault == "nonfinite_position":
        events[4] = events[4].replace("x=0.9", "x=nan")
    elif fault == "missing_ready":
        _write(paper, events)
        paper.write_bytes(b"".join(paper.read_bytes().splitlines(keepends=True)[1:]))
    elif fault == "malformed_duplicate_field":
        events[4] = events[4].replace(
            "source=PAPER_MAIN_THREAD", "x=0.9 source=PAPER_MAIN_THREAD",
        )
    elif fault == "foreign_log_without_newline":
        _write(paper, events)
        paper.write_bytes(paper.read_bytes().rstrip(b"\n"))
    elif fault == "paper_tick_rewind":
        events[5] = _paper_event("PRESENT", 109, 0.90)
    if fault not in {"missing_ready", "foreign_log_without_newline"}:
        _write(paper, events)
    with pytest.raises(Q8PaperHold):
        _audit(inputs)


def test_original_paper_archive_never_mutated_by_q(tmp_path):
    inputs = _fixture(tmp_path)
    original = [p.read_bytes() for p in inputs[:4]]
    _audit(inputs)
    assert original == [p.read_bytes() for p in inputs[:4]]
