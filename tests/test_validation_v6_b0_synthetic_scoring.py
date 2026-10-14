"""V6 output-score contract: no observed Minecraft data are consumed."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import v6_b0_synthetic_scoring as score


def _find(rows, start, regime, arm):
    return next(x for x in rows if x["world_start_slot"] == start
                and x["regime"] == regime and x["arm"] == arm)


def test_all_48_slots_computed_as_zero_difference_if_explicitly_equal():
    cohort = score.mock_cohort()
    result = score.rehearse(cohort)
    assert result["planned_world_slots"] == 48
    assert result["computed_complete_primary_pairs"] == 16
    assert result["missing_primary_pairs"] == 0
    assert {x["synthetic_difference"] for x in result["predeclared_primary_contrasts"]} == {0}
    assert result["real_world_trials"] == result["genuine_s51_outcomes"] == 0
    assert not result["production_go"] and result["science_g3"] == "NO_GO"


def test_positive_and_negative_signs_are_not_favored_or_discarded():
    cohort = score.mock_cohort()
    low = _find(cohort, "WORLD_START_A", "LOW", "SENSOR_ON")
    low["assumed_issued_moves"] = 2
    low["assumed_eat_events"] = 1
    low["assumed_final_m0_energy"] = 7.5
    high_blind = _find(cohort, "WORLD_START_A", "HIGH", "ALWAYS_SEEK")
    high_blind["assumed_issued_moves"] = 2
    high_blind["assumed_eat_events"] = 1
    high_blind["assumed_final_m0_energy"] = 15.5
    x = score.rehearse(cohort)
    s = {(r["world_start_slot"], r["regime"], r["contrast"]): r["synthetic_difference"]
         for r in x["predeclared_primary_contrasts"]}
    assert s["WORLD_START_A", "LOW", "ON_MINUS_ALWAYS_WAIT"] == 3.5
    assert s["WORLD_START_A", "HIGH", "ON_MINUS_ALWAYS_SEEK"] == -3.5
    assert x["science_g3"] == "NO_GO" and x["real_world_trials"] == 0


def test_invalid_and_censored_are_missing_not_zero_and_all_slots_retained():
    cohort = score.mock_cohort()
    invalid = _find(cohort, "WORLD_START_A", "LOW", "ALWAYS_SEEK")
    invalid["status"] = "INVALID"
    invalid["invalid_or_censor_reason"] = "MISSING_R_ORIGINAL_CLOCK"
    invalid["assumed_final_m0_energy"] = None
    censored = _find(cohort, "WORLD_START_B", "HIGH", "SENSOR_ON")
    censored["status"] = "CENSORED"
    censored["invalid_or_censor_reason"] = "NATIVE_SOURCE_CENSORED"
    censored["assumed_final_m0_energy"] = None
    censored["observed_m0_ticks"] = 12
    x = score.rehearse(cohort)
    assert x["simulated_invalid"] == x["simulated_censored"] == 1
    assert x["missing_primary_pairs"] == 3
    assert x["computed_complete_primary_pairs"] == 13
    assert all(r["synthetic_difference"] is None
               for r in x["predeclared_primary_contrasts"]
               if not r["source_complete_pair"])


@pytest.mark.parametrize(("field", "bad"), [
    ("source", "REAL_WORLD"),
    ("real_world_source_verified", True),
    ("native_world_elapsed_tick_verified", True),
    ("genuine_s51_receipt_verified", True),
    ("user_world_grant", True),
    ("assumed_eat_events", 2),
    ("assumed_issued_moves", 9),
    ("observed_m0_ticks", 17),
    ("assumed_final_m0_energy", 20),
    ("status", "PASS"),
    ("world_start_slot", "REAL_WORLD_1"),
    ("arm", "SENSOR_OWNED"),
    ("planned_order", 8),
])
def test_never_accept_forged_source_or_nonregistered_outcome(field, bad):
    rows = score.mock_cohort()
    rows[0][field] = bad
    with pytest.raises(score.V6SyntheticRejected):
        score.rehearse(rows)


def test_no_dropped_duplicated_or_scorefilled_invalid():
    rows = score.mock_cohort()
    with pytest.raises(score.V6SyntheticRejected):
        score.rehearse(rows[:-1])
    rows = score.mock_cohort()
    rows[1] = copy.deepcopy(rows[0])
    with pytest.raises(score.V6SyntheticRejected):
        score.rehearse(rows)
    rows = score.mock_cohort()
    rows[0]["status"] = "INVALID"
    rows[0]["invalid_or_censor_reason"] = "ORIGINAL_UNAVAILABLE"
    with pytest.raises(score.V6SyntheticRejected):
        score.rehearse(rows)


def test_cli_no_real_world_receipt(capsys):
    assert score.main() == 0
    o = json.loads(capsys.readouterr().out)
    assert o["classification"] == "V6_SYNTHETIC_PREOUTCOME_SCORING_REHEARSAL_ONLY"
    assert o["real_world_trials"] == 0 and o["genuine_s51_outcomes"] == 0
    assert not o["r_world_clock_admitted"] and not o["production_go"]
