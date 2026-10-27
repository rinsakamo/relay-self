"""T1k second STOP marker must not reuse T1i's first Paper evidence."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from adapters.mineflayer import t1i_session_stop_dev as stop
from adapters.mineflayer.t1h_stop_owner_dev import StopDevRejected
from test_t1i_multi_owner_dev import PLAYER, WORLD, paper_text, setup

SECOND = "T1K_R1_AFTER_CLEAR"


def paper_with_two_different_stop_markers():
    lines = [paper_text().rstrip(),
             f"S_V8_DEV_SNAPSHOT marker_id={SECOND} server_tick=120 world={WORLD}"]
    for tick in range(121, 131):
        lines.append(
            f"PAPER_DEV_MOTOR_SAMPLE server_tick={tick} world={WORLD} player={PLAYER}"
            " x=0 y=64 z=0 forward=false backward=false"
            " left=false right=false jump=false sneak=false sprint=false"
        )
    return "\n".join(lines) + "\n"


def test_second_stop_cannot_reuse_first_marker_but_can_use_new_unique(tmp_path, monkeypatch):
    case = setup(tmp_path, monkeypatch, log=paper_with_two_different_stop_markers())
    owner, session, server, p, outcome, terminal, commands = case
    result = asyncio.run(stop.finish_multi_epoch_move_stop(
        session, server, {"world": WORLD, "player": PLAYER},
        outcome, terminal, owner, p, marker_id=SECOND,
    ))
    ack = result["stop_ack_dev"]
    assert ack["marker_id"] == SECOND
    assert ack["first_idle_tick"] >= 122
    assert ack["last_idle_tick"] <= 130
    assert commands == ["relaydevsnapshot " + SECOND]


def test_repeated_second_marker_never_mints_stop_ack(tmp_path, monkeypatch):
    original = paper_with_two_different_stop_markers()
    case = setup(tmp_path, monkeypatch,
                 log=original + f"S_V8_DEV_SNAPSHOT marker_id={SECOND} server_tick=132 world={WORLD}\n")
    owner, session, server, p, outcome, terminal, _commands = case
    with pytest.raises(StopDevRejected):
        asyncio.run(stop.finish_multi_epoch_move_stop(
            session, server, {"world": WORLD, "player": PLAYER},
            outcome, terminal, owner, p, marker_id=SECOND,
        ))
    assert owner.ack is None


def test_two_stop_closures_use_distinct_native_probe_ids(tmp_path, monkeypatch):
    requests = set()
    for marker in ("T1I_MULTI_AFTER_CLEAR", SECOND):
        owner, session, server, p, outcome, terminal, _ = setup(
            tmp_path, monkeypatch, log=(paper_text() if marker == "T1I_MULTI_AFTER_CLEAR"
                                       else paper_with_two_different_stop_markers()))

        async def probe(_session, request_id):
            # Same native session permanently rejects a repeated request ID.
            if request_id in requests:
                raise RuntimeError("duplicate_probe_request_id")
            requests.add(request_id)
            return SimpleNamespace(session_id=owner.session_id, seq=200)

        monkeypatch.setattr(stop, "_correlated_observe", probe)
        result = asyncio.run(stop.finish_multi_epoch_move_stop(
            session, server, {"world": WORLD, "player": PLAYER},
            outcome, terminal, owner, p, marker_id=marker,
        ))
        assert result["stop_ack_dev"]["marker_id"] == marker
    assert len(requests) == 2
