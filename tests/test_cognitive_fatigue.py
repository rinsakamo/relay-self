"""L-CF offline negative controls. No provider, World or GPU execution."""
from dataclasses import replace

import pytest

from relay_self.cognitive_fatigue import (
    CognitiveFatigueRejected,
    FatigueProfile,
    FatigueState,
    L2Start,
    L2Usage,
    NonL2Interval,
    account_l2,
    begin_l2,
    budget_for_l2,
    recover_idle,
    sensory_projection,
)

NS = 1_000_000_000


def evidence(n):
    return f"{n:064x}"


def start(profile=None, *, initial=0, session="a", base=100):
    p = profile or FatigueProfile(mode="NONLINEAR", initial_fatigue=initial)
    s = FatigueState.genesis(p, session, 0)
    admitted = budget_for_l2(p, s, base)
    if admitted.admitted:
        s = begin_l2(p, s, L2Start(session, "task-1", 1, 0, evidence(1),
                                    admitted.max_output_tokens), base)
    return p, s


def account(p, s, tokens, status="COMPLETED", *, at=NS, seq=None):
    return account_l2(p, s, L2Usage(s.session_id, s.active_work_id,
                                   s.seq+1 if seq is None else seq,
                                   at, evidence(100+s.seq), tokens, status))


def idle(p, s, to=6*NS):
    return recover_idle(p, s, NonL2Interval(s.session_id, s.seq+1,
                                            s.last_ns, to, evidence(200+s.seq)))


def test_off_no_budget_fatigue_or_sensor_change():
    p, s = start(FatigueProfile(mode="OFF", initial_fatigue=0.8), base=96)
    assert s.fatigue == 0
    assert budget_for_l2(p, FatigueState.genesis(p, "a", 0), 96).max_output_tokens == 96
    assert sensory_projection(s, p) == {}
    s = account(p, s, 200)
    s = idle(p, s)
    assert s.fatigue == 0 and s.total_metered_tokens == 200


def test_long_work_more_fatigue_than_short_and_separate_compute_counter():
    p, s = start()
    short = account(p, s, 10)
    long = account(p, s, 110)
    assert long.fatigue > short.fatigue > 0
    assert long.total_metered_tokens == 110
    assert short.total_metered_tokens == 10


def test_body_move_idle_recovers_and_body_wait_during_l2_does_not():
    p, s = start()
    s = account(p, s, 100, "PROGRESS", at=NS)
    with pytest.raises(CognitiveFatigueRejected):
        idle(p, s, 10*NS)
    s = account(p, s, 110, "COMPLETED", at=4*NS)
    before = s.fatigue
    s = idle(p, s, 8*NS)
    assert s.fatigue < before
    assert s.total_metered_tokens == 110


def test_progress_and_cancel_unconfirmed_never_waives_usage():
    p, s = start()
    s = account(p, s, 30, "PROGRESS")
    assert s.total_metered_tokens == 30
    assert budget_for_l2(p, s, 100).admitted is False
    with pytest.raises(CognitiveFatigueRejected):
        idle(p, s, 7*NS)
    s = account(p, s, 42, "STOP_ACK", at=3*NS)
    assert s.total_metered_tokens == 42 and s.active_work_id is None


def test_same_receipts_deterministic_hash_chain():
    p, a = start()
    _, b = start()
    for n, t, kind in [(10, NS, "PROGRESS"), (100, 2*NS, "COMPLETED")]:
        a = account(p, a, n, kind, at=t)
        b = account(p, b, n, kind, at=t)
    a, b = idle(p, a), idle(p, b)
    assert a == b and a.chain_hash == b.chain_hash and a.state_sha256 == b.state_sha256
    assert a.profile_sha256 == p.sha256


def test_non_linear_cliff_linear_fixed_and_off_comparison():
    p = FatigueProfile(mode="NONLINEAR", initial_fatigue=0.7,
                       knee=0.55, slope=20)
    state = FatigueState.genesis(p, "a", 0)
    nonlinear = budget_for_l2(p, state, 100).max_output_tokens
    q = replace(p, mode="LINEAR")
    linear = budget_for_l2(q, FatigueState.genesis(q, "a", 0), 100).max_output_tokens
    q = replace(p, mode="FIXED", fixed_max_tokens=33)
    fixed = budget_for_l2(q, FatigueState.genesis(q, "a", 0), 100).max_output_tokens
    q = replace(p, mode="OFF")
    off = budget_for_l2(q, FatigueState.genesis(q, "a", 0), 100).max_output_tokens
    assert 1 <= nonlinear < linear < off == 100
    assert fixed == 33
    assert budget_for_l2(p, FatigueState.genesis(p, "a", 0), 5).max_output_tokens <= 5


def test_hysteresis_blocks_start_until_real_recovery_and_no_l0_gate():
    p = FatigueProfile(mode="NONLINEAR", initial_fatigue=0.96,
                       recovery_per_idle_s=0.03, resume_below=0.75)
    s = FatigueState.genesis(p, "a", 0)
    assert not budget_for_l2(p, s, 100).admitted
    s = idle(p, s, 2*NS)
    assert s.blocked
    s = idle(p, s, 10*NS)
    assert not s.blocked and budget_for_l2(p, s, 100).admitted
    assert budget_for_l2(p, s, 100).action_authority is False
    assert sensory_projection(s, p, enabled=True)["cognitive_budget_band"] in ("LOW", "AVAILABLE")


def test_session_replay_duplicate_missing_and_time_regression_rejected():
    p, s = start()
    with pytest.raises(CognitiveFatigueRejected):
        account(p, s, 1, seq=s.seq)
    with pytest.raises(CognitiveFatigueRejected):
        account_l2(p, s, L2Usage("b", "task-1", 2, NS, evidence(2), 10, "PROGRESS"))
    with pytest.raises(CognitiveFatigueRejected):
        account_l2(p, s, L2Usage("a", "task-1", 2, 0, "", 10, "COMPLETED"))
    s = account(p, s, 10)
    with pytest.raises(CognitiveFatigueRejected):
        idle(p, s, NS-1)
    with pytest.raises(CognitiveFatigueRejected):
        recover_idle(p, s, NonL2Interval("a", s.seq+1, 0, 3*NS, evidence(3)))


def test_forged_state_or_profile_forbidden():
    p, s = start()
    with pytest.raises(CognitiveFatigueRejected):
        budget_for_l2(p, replace(s, fatigue=0), 10)
    with pytest.raises(CognitiveFatigueRejected):
        budget_for_l2(replace(p, slope=12), s, 10)


@pytest.mark.parametrize("kwargs", [
    {"initial_fatigue": float("nan")}, {"initial_fatigue": 1.1},
    {"charge_per_total_token": float("inf")}, {"mode": "INVALID"},
    {"fixed_max_tokens": True}, {"slope": -1},
    {"resume_below": 0.96}, {"block_at": -1},
])
def test_invalid_profile_rejected(kwargs):
    with pytest.raises(CognitiveFatigueRejected):
        FatigueProfile(**kwargs)


def test_non_finite_or_missing_usage_and_work_regression_rejected():
    p, s = start()
    for quantity in (None, float("nan"), float("inf"), -1, 1.5, True):
        with pytest.raises(CognitiveFatigueRejected):
            account(p, s, quantity)
    s = account(p, s, 20, "PROGRESS")
    with pytest.raises(CognitiveFatigueRejected):
        account(p, s, 19, "STOP_ACK", at=2*NS)


def test_saturation_is_not_free_work_and_consecutive_idle_not_double_counted():
    p, s = start(FatigueProfile(mode="LINEAR", charge_per_total_token=1))
    s = account(p, s, 1000)
    assert s.fatigue == 1 and s.total_metered_tokens == 1000
    s = idle(p, s, 10*NS)
    with pytest.raises(CognitiveFatigueRejected):
        recover_idle(p, s, NonL2Interval("a", s.seq+1, NS, 10*NS, evidence(88)))
    assert s.fatigue < 1 and s.total_metered_tokens == 1000


def test_work_identity_reuse_forbidden():
    p, s = start()
    s = account(p, s, 1)
    with pytest.raises(CognitiveFatigueRejected):
        begin_l2(p, s, L2Start("a", "task-1", s.seq+1, 2*NS, evidence(991), 100), 100)


def test_evidence_hash_and_no_reset_via_modified_snapshot():
    p, s = start()
    with pytest.raises(CognitiveFatigueRejected):
        recover_idle(p, replace(s, active_work_id=None),
                     NonL2Interval("a", 2, 0, NS, evidence(21)))
    assert s.active_work_id == "task-1"
