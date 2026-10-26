"""T1i: same T1h owner finalizes one multi-epoch MOVE STOP."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from adapters.mineflayer import t1i_session_stop_dev as t1i
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevRejected
from relay_self.action import ActionState

SID = "t1i-session"
WORLD = "11111111-1111-4111-8111-111111111111"
PLAYER = "22222222-2222-4222-8222-222222222222"
MARKER = "T1I_MULTI_AFTER_CLEAR"


def paper_text(*, marker=True, rows=10, moving=False):
    lines = []
    if marker:
        lines.append("S_V8_DEV_SNAPSHOT marker_id=" + MARKER
                     + f" server_tick=100 world={WORLD}")
    for i in range(1, rows + 1):
        pos = ".1" if moving and i > 3 else "0"
        lines.append(
            "PAPER_DEV_MOTOR_SAMPLE"
            + f" server_tick={100+i} world={WORLD} player={PLAYER}"
            + f" x={pos} y=64 z=0 forward=false backward=false"
            + " left=false right=false jump=false sneak=false sprint=false"
        )
    return "\n".join(lines) + "\n"


def setup(tmp_path, monkeypatch, *, log=None, wrong_action=False, lost=False):
    owner = S49DevStopOwner(SID)
    owner.request(
        "t1i-stop", active_action_id="t1i-move",
        expected_clear_action_id="t1i-move-clear",
    )
    effect = MineflayerEffectResult(
        SID, 33, "foreign-clear" if wrong_action else "t1i-move-clear",
        "clear_controls", "applied", None,
    )
    outcome = SimpleNamespace(
        action_id="t1i-move", session_id=SID,
        status=WorldConsequenceStatus.FAILED,
        cleanup_receipt=effect,
    )
    terminal = SimpleNamespace(state=ActionState.UNKNOWN)
    session = SimpleNamespace(source_lost=lost, process_returncode=None)
    async def probe(*args):
        return SimpleNamespace(session_id=SID, seq=88)
    monkeypatch.setattr(t1i, "_correlated_observe", probe)
    commands = []
    monkeypatch.setattr(t1i, "_command", lambda _server, line: commands.append(line))
    async def drain():
        pass
    server = SimpleNamespace(stdin=SimpleNamespace(drain=drain))
    p = tmp_path / "paper.log"
    p.write_text(paper_text() if log is None else log)
    return owner, session, server, p, outcome, terminal, commands


def run(case):
    owner, session, server, p, outcome, terminal, _commands = case
    return asyncio.run(t1i.finish_multi_epoch_move_stop(
        session, server, {"world": WORLD, "player": PLAYER},
        outcome, terminal, owner, p,
    ))


def test_owner_acks_bounded_paper_idle_but_not_qualification(tmp_path,monkeypatch):
    case = setup(tmp_path,monkeypatch)
    result = run(case)
    assert result["stop_ack_dev"]["high_level_dev_stop_ack"] is True
    assert not result["stop_ack_dev"]["full_tick_stillness_qualified"]
    assert not result["stop_ack_dev"]["p1_qualified_wait"]
    assert result["action_status"] == "failed"
    assert result["terminal"] == "unknown"
    assert result["next_action_issued"] is False
    assert case[-1] == ["relaydevsnapshot " + MARKER]
    with pytest.raises(StopDevRejected):
        run(case)


@pytest.mark.parametrize("fault", ["foreign_action","lost","short","moving"])
def test_no_stop_ack_on_missing_native_or_paper_evidence(tmp_path,monkeypatch,fault):
    kwargs = {}
    if fault == "foreign_action":
        kwargs["wrong_action"] = True
    if fault == "lost":
        kwargs["lost"] = True
    if fault == "short":
        kwargs["log"] = paper_text(rows=4)
    if fault == "moving":
        kwargs["log"] = paper_text(moving=True)
    case = setup(tmp_path,monkeypatch,**kwargs)
    with pytest.raises(StopDevRejected):
        run(case)
    assert case[0].ack is None


@pytest.mark.parametrize("foreign", [False, True])
def test_stopped_eat_passive_observation_never_promotes_outcome(tmp_path, monkeypatch, foreign):
    from dataclasses import dataclass

    @dataclass
    class Probe:
        session_id: str
        seq: int

    commands = []
    monkeypatch.setattr(t1i, "_command", lambda _server, line: commands.append(line))

    async def drain():
        pass

    async def sleep(_seconds):
        pass

    async def observe(_session, request_id):
        return Probe("foreign" if foreign else SID, int(request_id.rsplit("-", 1)[1]) + 20)

    monkeypatch.setattr(t1i.asyncio, "sleep", sleep)
    monkeypatch.setattr(t1i, "_correlated_observe", observe)
    session = SimpleNamespace(started=SimpleNamespace(session_id=SID))
    server = SimpleNamespace(stdin=SimpleNamespace(drain=drain))
    log = tmp_path / "paper.log"
    log.write_text("S_V8_DEV_SNAPSHOT marker_id=T1I_EAT_AFTER_STOP server_tick=100\n")
    result = asyncio.run(t1i.observe_stopped_eat(session, server, {"seq": 10}, log))
    assert result["creates_outcome"] is False and result["credits"] == 0
    assert result["status"] == ("NATIVE_UNVERIFIED" if foreign else "DEV_WORLD_OBSERVED")
    assert len(result["probes"]) == (0 if foreign else 12)
    assert commands == ["relaydevsnapshot T1I_EAT_AFTER_STOP"]
