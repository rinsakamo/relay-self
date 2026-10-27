"""DEV seven-positive-Paper-tick count: source joins and negative controls."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_matched_boost_review_dev import (
    MatchedBoostDevRejected,
    compare_matched_boost_pairs_dev,
    matched_boost_rows_dev,
)
from test_s49_p1_synced_motor_pair_dev import example


def synthetic_paper_ticks(*, arm="A", sid="sid", case="CARRY"):
    power = .75 if case == "CARRY" else 1.
    rows = []
    for i in range(1, 14):
        boosted = 3 <= i <= 9
        rows.append(
            "S49_DASH_DEV_TICK "
            f"action_id={arm} session_id={sid} world=world-{sid} "
            f"player_uuid=uuid-{sid} tick={300+i} index={i} "
            f"p1_world_ticks={i} p1_motor_dev=true "
            f"modifier_applied={'true' if boosted else 'false'} "
            f"sampled_speed_mps={5+i*.2} "
            f"p1_current_applied_power={power if boosted else 0.0}"
        )
    rows.append(
        "S49_DASH_DEV_COMPLETE "
        f"action_id={arm} session_id={sid} world=world-{sid} "
        f"player_uuid=uuid-{sid} reason=OWNER_RELEASE "
        "p1_matched_boost_cap=7 p1_matched_boost_cap_reached=true "
        "forward_boost_ticks=7 modifier_applied=false "
        "p1_world_ticks=13 P1_APPLIED=false M0_POSTED=false"
    )
    return "\n".join(rows)


def synthetic_source(case, pair):
    key = "carry_world" if case == "CARRY" else "wait_assumed_world"
    arm = pair[key]
    source = matched_boost_rows_dev(
        synthetic_paper_ticks(arm=arm["first_action_id"],
                              sid=arm["session_id"], case=case),
        action_id=arm["first_action_id"], session_id=arm["session_id"],
    )
    source["world"] = arm["paper_world_uuid"]
    source["matched_positive_power_by_ordinal"][0] = arm["paper_first_applied_power"]
    return source


def test_exact_seven_paper_positive_ticks_are_not_same_clock():
    x = matched_boost_rows_dev(
        synthetic_paper_ticks(),
        action_id="A", session_id="sid",
    )
    assert x["exact_paper_positive_bonus_ticks"] == 7
    assert x["positive_first_index"] == 3
    assert x["positive_last_index"] == 9
    assert x["paper_total_gait_ticks"] == 13
    assert x["same_world_tick_clock_as_other_world"] is False
    assert x["paper_action_owner_issued"] is False


@pytest.mark.parametrize("fault", [
    "wrong_session", "short_cap", "not_reached", "duplicate_complete",
    "world_changed", "other_player", "positive_extra", "no_tail",
    "gait_replay", "tick_gap", "nonconsecutive_boost",
    "missing_p1", "fake_m0", "wrong_release", "bad_speed",
])
def test_paper_source_rejects_unbounded_or_forged_p1_boost(fault):
    raw = synthetic_paper_ticks()
    lines = raw.splitlines()
    if fault == "wrong_session":
        lines[4] = lines[4].replace("session_id=sid", "session_id=foreign")
    elif fault == "short_cap":
        lines[-1] = lines[-1].replace("p1_matched_boost_cap=7", "p1_matched_boost_cap=8")
    elif fault == "not_reached":
        lines[-1] = lines[-1].replace("p1_matched_boost_cap_reached=true", "p1_matched_boost_cap_reached=false")
    elif fault == "duplicate_complete":
        lines.append(lines[-1])
    elif fault == "world_changed":
        lines[4] = lines[4].replace("world=world-sid", "world=alien")
    elif fault == "other_player":
        lines[4] = lines[4].replace("player_uuid=uuid-sid", "player_uuid=foreign")
    elif fault == "positive_extra":
        lines[9] = lines[9].replace("modifier_applied=false", "modifier_applied=true").replace(
            "p1_current_applied_power=0.0", "p1_current_applied_power=.75"
        )
    elif fault == "no_tail":
        lines = lines[:9] + [lines[-1]]
    elif fault == "gait_replay":
        lines[5] = lines[5].replace("p1_world_ticks=6", "p1_world_ticks=5")
    elif fault == "tick_gap":
        lines[5] = lines[5].replace("tick=306", "tick=308")
    elif fault == "nonconsecutive_boost":
        lines[6] = lines[6].replace("modifier_applied=true", "modifier_applied=false").replace(
            "p1_current_applied_power=0.75", "p1_current_applied_power=0.0"
        )
        lines[9] = lines[9].replace("modifier_applied=false", "modifier_applied=true").replace(
            "p1_current_applied_power=0.0", "p1_current_applied_power=0.75"
        )
    elif fault == "missing_p1":
        lines[4] = lines[4].replace("p1_motor_dev=true", "p1_motor_dev=false")
    elif fault == "fake_m0":
        lines[-1] = lines[-1].replace("M0_POSTED=false", "M0_POSTED=true")
    elif fault == "wrong_release":
        lines[-1] = lines[-1].replace("reason=OWNER_RELEASE", "reason=OTHER")
    else:
        lines[4] = lines[4].replace("sampled_speed_mps=6.0", "sampled_speed_mps=nan")
    with pytest.raises(MatchedBoostDevRejected):
        matched_boost_rows_dev(
            "\n".join(lines), action_id="A", session_id="sid",
        )


def test_p1_two_source_synced_native_and_paper_matched_pair():
    synced, _ = example()
    sources = {
        case: synthetic_source(case, synced)
        for case in ("CARRY", "WAIT_ASSUMED")
    }
    original = deepcopy((synced, sources))
    v = compare_matched_boost_pairs_dev(synced, sources)
    assert original == (synced, sources)
    assert v["same_number_of_positive_paper_boost_ticks"] is True
    assert len(v["positive_matched_paper_speed_delta_by_ordinal_mps"]) == 7
    assert len(v["positive_matched_paper_power_delta_by_ordinal"]) == 7
    assert v["native_original_s16_displacement_gain_m"] == pytest.approx(.5)
    assert v["world_clock_phase_matched"] is False
    assert v["model_preload_not_actual_longitudinal_p1_recovery"] is True
    assert v["physical_l0_dash_power_admission"] is None
    assert v["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "model_source", "fatigue_admitted", "wrong_session",
    "wrong_world", "boost_count", "power_below", "fake_clock",
    "fake_qualified", "case_missing", "new_issuer", "l0_admitted",
])
def test_matched_Paper_model_pair_fails_closed(fault):
    synced, _ = example()
    sources = {
        case: synthetic_source(case, synced)
        for case in ("CARRY", "WAIT_ASSUMED")
    }
    carry = sources["CARRY"]
    rested = sources["WAIT_ASSUMED"]
    if fault == "model_source":
        synced["classification"] = "QUALIFIED_RECOVERY"
    elif fault == "fatigue_admitted":
        synced["same_self_longitudinal_wait_recovery_observed"] = True
    elif fault == "wrong_session":
        carry["session_id"] = "alien"
    elif fault == "wrong_world":
        rested["world"] = "foreign-world"
    elif fault == "boost_count":
        rested["exact_paper_positive_bonus_ticks"] = 6
    elif fault == "power_below":
        rested["matched_positive_power_by_ordinal"] = [.01] * 7
    elif fault == "fake_clock":
        carry["same_world_tick_clock_as_other_world"] = True
    elif fault == "fake_qualified":
        carry["qualification_go"] = True
    elif fault == "case_missing":
        sources.pop("WAIT_ASSUMED")
    elif fault == "new_issuer":
        synced["new_native_action_issuers"] = 1
    else:
        synced["l0_physical_dash_power_admission"] = 1.
    with pytest.raises(MatchedBoostDevRejected):
        compare_matched_boost_pairs_dev(synced, sources)
