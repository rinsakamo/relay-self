"""R independent direct BASAL write source shape — entirely synthetic fixtures."""
from __future__ import annotations

import math

import pytest

from experiments.standard_env import v7_m02_direct_basal_readback as r


def specimen(arm: str, *, change=None) -> bytes:
    rate = r.RATES[arm]
    rows = ["[INFO] M02_DEV_ONLY: candidate physics, not qualified by R/V"]
    cumulative = 0.0
    for n in range(1, 201):
        cumulative += rate
        seq = n
        full_time = 1000 + n
        charge = rate
        target = 1.0 + charge
        body_after = target
        if change is not None:
            altered = change(n)
            seq = altered.get("seq", seq)
            full_time = altered.get("full_time", full_time)
            charge = altered.get("charge", charge)
            target = altered.get("target", target)
            body_after = altered.get("after", body_after)
            cumulative = altered.get("cumulative", cumulative)
        rows.append(
            "[INFO] M02_DEV_BASAL_WRITE id={} world_full_time={} "
            "before=1.0 requested={} write_target={} observed_after={} "
            "cumulative_requested={} x=0.5 y=64.0 z=-2.0 yaw=45.0 pitch=0.0".format(
                seq, full_time, charge, target, body_after, cumulative,
            )
        )
        if n in r.BODY_CHECKPOINTS:
            rows.append(
                "[INFO] M02_DEV_BODY sampled_tick={} player=RelaySelf "
                "food=20 saturation=5 health=20 exhaustion={} "
                "motion_blocks=1.2".format(n, body_after)
            )
    return ("\n".join(rows) + "\n").encode("utf-8")


@pytest.mark.parametrize("arm", sorted(r.RATES))
def test_200_original_format_basal_writes_are_source_only(arm):
    raw = specimen(arm)
    v = r.review_original_server_log(raw, arm)
    assert v["classification"] == r.CLASSIFICATION
    assert v["arm"] == arm
    assert v["source_log_sha256"]
    assert v["source_writes_recorded"] == 200
    assert v["world_full_time_at_200th"] - v["first_world_full_time"] == 199
    assert v["direct_source_requested_basal_cumulative_first200"] == pytest.approx(
        r.RATES[arm] * 200,
    )
    assert v["write_side_consistent_with_config"]
    assert not v["native_meter_causality_attested"]
    assert not v["s50_move_bracket_attested"]
    assert not v["s_source_binary_and_original_bytes_authenticated_here"]
    assert not v["changed_profile_engineering_qualified"]
    assert v["science_trials_credited"] == 0
    assert not v["v_science_go"]


def test_quoted_zero_rate_never_substitutes_for_full_time():
    v = r.review_original_server_log(specimen("BOTH_ZERO"), "BOTH_ZERO")
    assert v["direct_source_requested_basal_cumulative_first200"] == 0
    assert v["first200_source_player_callbacks"] == 200


@pytest.mark.parametrize(("change", "message"), [
    (lambda n: {"seq": 98} if n == 99 else {}, "counter"),
    (lambda n: {"full_time": 3000 + n} if n >= 70 else {}, "full-time"),
    (lambda n: {"charge": .002} if n == 33 else {}, "requested rate"),
    (lambda n: {"target": 2} if n == 33 else {}, "input"),
    (lambda n: {"cumulative": .3} if n == 200 else {}, "sum"),
    (lambda n: {"after": 41} if n == 33 else {}, "readback"),
    (lambda n: {"charge": math.nan} if n == 33 else {}, "malformed"),
])
def test_source_integrity_fail_closed(change, message):
    with pytest.raises(r.SourceRejected, match=message):
        r.review_original_server_log(specimen("BASE_ON", change=change), "BASE_ON")


def test_body_readback_cross_check_is_independent_of_s_claim():
    raw = specimen("BASE_ON").replace(b"sampled_tick=100 player=RelaySelf food=20 "
                                      b"saturation=5 health=20 exhaustion=1.001",
                                      b"sampled_tick=100 player=RelaySelf food=20 "
                                      b"saturation=5 health=20 exhaustion=1.03")
    with pytest.raises(r.SourceRejected, match="checkpoint"):
        r.review_original_server_log(raw, "BASE_ON")


def test_missing_duplicate_and_wrong_profile_never_pass():
    raw = specimen("SHAM_ON")
    with pytest.raises(r.SourceRejected, match="rate"):
        r.review_original_server_log(raw, "BASAL_ZERO")
    with pytest.raises(r.SourceRejected, match="missing"):
        r.review_original_server_log(
            b"\n".join(raw.splitlines()[:200]) + b"\n", "SHAM_ON",
        )
    raw = raw + b"[INFO] M02_DEV_BASAL_WRITE id=201 invalid\n"
    with pytest.raises(r.SourceRejected, match="malformed"):
        r.review_original_server_log(raw, "SHAM_ON")


def test_wrong_source_and_no_world_are_not_silently_authenticated():
    for raw in (b"", b"unrelated-log", specimen("BASE_ON") + b"M02_DEV_DISABLED: no"):
        with pytest.raises(r.SourceRejected):
            r.review_original_server_log(raw, "BASE_ON")
    with pytest.raises(r.SourceRejected, match="unknown"):
        r.review_original_server_log(specimen("BASE_ON"), "OTHER")
