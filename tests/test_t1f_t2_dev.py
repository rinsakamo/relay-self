"""Source/admission, epoch release and real-tick accounting failure controls."""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from adapters.mineflayer.execution import MineflayerExecutionError, _check_l0_interrupt
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerPaperSnapshot,
    parse_mineflayer_line,
)
from adapters.mineflayer.t2_tick_accounting import TickAccounting

UUID = "11111111-1111-1111-1111-111111111111"


def frame(i=1, *, control="CLEARED", bits=0, x=0, seq=None, status="ADMITTED"):
    s = dict(version=1, boot=UUID, index=i, tick=100 + i, world_tick=200 + i,
             paper_ns=i * 50000000, world=UUID, player=UUID,
             challenge="a" * 32 + f":{i}", x=x, y=1, z=0, health=20, food=20,
             input=bits, threats_complete=True, threats=[], basal_ticks=i,
             basal_exhaustion=i * .001, motion_blocks=x, motion_exhaustion=x * .01)
    received = i * 50000000
    d = dict(snapshot=s, status=status, reason="test", assessment="NO_KNOWN_URGENT_SIGNAL"
             if status == "ADMITTED" else "UNKNOWN", latest_confirmed_tick=s["tick"],
             received_ns=str(received), evaluation_start_ns=str(received + 1),
             evaluation_completed_ns=str(received + 2), age_upper_ns="1000002", age_lower_ns="2",
             paper_to_node_exact_ns=None, cache_mismatch=None, qualification=False,
             tps_admission_granted=False, challenge_sent_ns=str(received - 1000000),
             control=dict(phase=control, since_ns="1", generation=2))
    return MineflayerPaperSnapshot(session_id="test-session", seq=seq or i * 10, data=d)


@pytest.mark.parametrize("mutate", [
    lambda d: d["snapshot"].pop("health"),
    lambda d: d.update(age_upper_ns="150000000"),
    lambda d: d.update(latest_confirmed_tick=999),
    lambda d: d.update(assessment="LOW_HEALTH"),
    lambda d: d.update(qualification=True),
    lambda d: d.update(age_lower_ns="1"),
    lambda d: d["snapshot"].update(threats_complete=False),
    lambda d: d["snapshot"].update(x=float("nan")),
    lambda d: d["snapshot"].update(input=128),
])
def test_wire_refuses_false_freshness_and_missing_values(mutate):
    f = frame()
    d = copy.deepcopy(f.data)
    mutate(d)
    with pytest.raises(MineflayerAdapterProtocolError):
        MineflayerPaperSnapshot(session_id=f.session_id, seq=f.seq, data=d)


def test_new_wire_has_exact_fields():
    import json
    f = frame()
    raw = dict(type="paper_snapshot", session_id=f.session_id, seq=f.seq, data=f.data)
    assert parse_mineflayer_line(json.dumps(raw)) == f
    raw["extra"] = True
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps(raw))


@pytest.mark.parametrize("status", ["STALE", "MISSING", "LATE", "UNDETERMINED"])
def test_s49_refuses_any_nonadmission(status):
    with pytest.raises(MineflayerExecutionError):
        _check_l0_interrupt(frame(status=status), session_id="test-session")


def test_s49_uses_paper_hazard_and_rejects_foreign_session():
    f = frame()
    assert _check_l0_interrupt(f, session_id=f.session_id)
    with pytest.raises(MineflayerExecutionError):
        _check_l0_interrupt(f, session_id="another-session")
    d = copy.deepcopy(f.data)
    d["snapshot"]["health"] = 3
    d["assessment"] = "LOW_HEALTH"
    with pytest.raises(MineflayerExecutionError, match="LOW_HEALTH"):
        _check_l0_interrupt(MineflayerPaperSnapshot(f.session_id, f.seq, d), session_id=f.session_id)


def release(owner, seq=1):
    owner.begin("action-1")
    owner.finish(SimpleNamespace(action_id="action-1", cleanup_receipt=SimpleNamespace(
        result="applied", effect="clear_controls", seq=seq), after_observation=None),
        SimpleNamespace(action_id="action-1"))


def test_real_tick_basal_and_p1_wait_causality():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    release(owner)
    owner.observe(frame(2, control="MOVING", bits=2, x=.5))
    owner.observe(frame(3, x=.5))
    owner.observe(frame(4, x=.5))
    assert [r["activity"] for r in owner.rows] == ["MOVE_OR_UNDETERMINED"] * 2 + ["WAIT_DEV"]
    assert owner.rows[-1]["p1"]["recovered"] > 0
    assert sum(r["m0_basal"] for r in owner.rows) == pytest.approx(.003)
    assert owner.energy.body.tick == 3
    assert sum(r["m0_cognition"] for r in owner.rows) == pytest.approx(.0003)


def test_blocked_move_never_recovers_even_with_zero_displacement():
    owner = TickAccounting("test-session")
    owner.observe(frame())
    owner.begin("blocked-move")
    owner.observe(frame(2, bits=2, control="MOVING"))
    assert owner.rows[-1]["activity"] != "WAIT_DEV"
    assert owner.rows[-1]["p1"]["recovered"] == 0


def test_lost_ack_blocks_next_action_and_recovery():
    owner = TickAccounting("test-session")
    owner.begin("a")
    owner.finish(SimpleNamespace(action_id="a", cleanup_receipt=None), SimpleNamespace(action_id="a"))
    assert owner.failed
    with pytest.raises(ValueError):
        owner.begin("b")


@pytest.mark.parametrize("i", [1, 3])
def test_replay_or_missing_tick_never_credits_wait_or_fills_gap(i):
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    with pytest.raises(ValueError):
        owner.observe(frame(i))
    assert owner.energy.body.tick == 0
    assert owner.rows == []


def test_ack_and_boundary_snapshots_do_not_become_wait():
    owner = TickAccounting("test-session")
    owner.observe(frame(1))
    release(owner, seq=15)
    owner.observe(frame(2))
    assert owner.rows[-1]["p1"]["recovered"] == 0
    owner.observe(frame(3))
    assert owner.rows[-1]["activity"] == "WAIT_DEV"


def test_same_worldticks_account_identically_regardless_of_arrival_tps():
    results = []
    for tps in (2, 20, 200):
        owner = TickAccounting("test-session")
        for i in range(1, 21):
            f = frame(i, bits=2, control="MOVING", x=i * .1)
            # All timestamps remain in the same Node domain. Arrival rate is
            # deliberately irrelevant to admitted World-time bookkeeping.
            d = copy.deepcopy(f.data)
            received = int(i * 1e9 / tps)
            d.update(received_ns=str(received), evaluation_start_ns=str(received + 1),
                     evaluation_completed_ns=str(received + 2), challenge_sent_ns=str(received - 1000000))
            owner.observe(MineflayerPaperSnapshot(f.session_id, f.seq, d))
        results.append((owner.energy.body.energy, owner.fatigue.fatigue, len(owner.rows)))
    assert results[0] == results[1] == results[2]
