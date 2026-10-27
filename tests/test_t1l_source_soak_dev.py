"""T1l source-only long run; no actions, invented ticks or P1-qualified WAIT."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace as S

import pytest

from adapters.mineflayer import t1l_source_soak_dev as soak
from test_t1f_t2_dev import frame


class Session:
    def __init__(self, *, start=1, skip=None):
        self.started = S(session_id="test-session")
        self.process_returncode = None
        self.source_lost = False
        self.tick_owner = None
        self.next_index = start
        self.skip = skip

    async def take(self, *, after_seq=-1, timeout=3):
        i = self.next_index
        if self.skip is not None and i == self.skip:
            i += 1
            self.next_index += 1
        self.next_index += 1
        source = frame(i)
        if self.tick_owner is not None:
            self.tick_owner.observe(source)
        return source


def run(session, monkeypatch, *, ticks=100):
    monkeypatch.setattr(soak, "next_tick", lambda sess, **kw: sess.take(**kw))
    return asyncio.run(soak.run_source_soak(
        session, report := {}, accounted_ticks=ticks)), report


def test_soak_counts_only_100_consecutive_admitted_world_ticks(monkeypatch):
    session = Session()
    result, report = run(session, monkeypatch)
    assert result["accounted_ticks"] == 100
    assert result["accounted_world_ticks_consecutive"]
    assert result["first_accounted_world_tick"] == 202
    assert result["last_accounted_world_tick"] == 301
    assert result["new_action_count"] == 0
    assert result["no_issued_motor_or_eat_actions"]
    assert not result["p1_qualified_wait"]
    assert session.tick_owner.energy.credit_count == 0
    assert len(session.tick_owner.rows) == 100
    assert all(not row["full_tick_R_attested"] for row in session.tick_owner.rows)
    assert report["status"] == "PASS"


def test_200_ticks_writes_real_owner_checkpoint_without_new_action(monkeypatch):
    session = Session()
    result, _ = run(session, monkeypatch, ticks=200)
    assert [c["accounted_ticks"] for c in result["checkpoints"]] == [200]
    assert session.tick_owner.energy.body.tick == 200
    assert not session.tick_owner.failed


def test_gap_latches_ledger_instead_of_minting_missing_tick(monkeypatch):
    session = Session(skip=55)
    with pytest.raises(ValueError, match="nonconsecutive"):
        run(session, monkeypatch)
    assert session.source_lost and session.tick_owner.failed
    assert session.tick_owner.rows[-1]["world_tick"] == 254
    assert session.tick_owner.energy.body.tick == 53


def test_challenge_limit_refuses_upfront_before_one_accounted_tick(monkeypatch):
    session = Session(start=2260)
    with pytest.raises(soak.SoakDevRejected, match="budget"):
        run(session, monkeypatch, ticks=100)
    assert session.source_lost and session.tick_owner.failed
    assert session.tick_owner.rows == []


def test_rejects_unbounded_request_without_creating_any_ledger(monkeypatch):
    session = Session()
    monkeypatch.setattr(soak, "next_tick", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("must not touch World")))
    with pytest.raises(soak.SoakDevRejected):
        asyncio.run(soak.run_source_soak(session, {}, accounted_ticks=2001))
    assert session.tick_owner is None
