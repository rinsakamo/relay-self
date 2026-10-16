"""Prospective DEV BASAL source readout metadata; never V7 science."""
from __future__ import annotations

import pytest

from experiments.validation import v7_m02_direct_basal_dev as report
from experiments.validation import v7_m02_physics as v7


def test_new_real_s_r_original_basal_and_walk_source_is_separate_from_science():
    x = report.review_real_direct_basal_dev_metadata()
    assert x["classification"] == "V7_M02_NEW_DIRECT_BASAL_FIVE_DEV_R_SOURCE_REVIEW_ONLY"
    assert x["s_original_run"] == 38850179491
    assert x["r_independent_run"] == 38850421003
    assert x["r_immutable_archive_id"] == 12024688755
    assert x["new_dev_worlds"] == x["historical_dev_worlds"] == 5
    assert x["total_prescience_dev_attempts_preserved"] == 10
    assert x["science_slots_unexecuted"] == 20
    assert x["science_trials_credited"] == 0
    assert x["source_requested_basal_and_walk_consistent"] is True
    assert not x["historic_v7_paired_comparison_admitted"]
    assert not x["r_changed_plugin_engineering_qualified"]
    assert not x["controlled_move_bracket_attested"]
    assert not x["native_meter_ecological_effect_attested"]
    assert not x["v7_science_go"]
    assert x["observed_max_path_spread_blocks"] > .24
    for arm, v in x["arms"].items():
        basal, walk = v7.MULTIPLIERS[arm]
        assert v["basal_requested_per_actual_player_callback"] == pytest.approx(
            0.001 * basal, abs=1e-12,
        )
        assert v["walk_source_billed_per_actual_block"] == pytest.approx(
            0.01 * walk, abs=1e-12,
        )


@pytest.mark.parametrize(("arm", "index", "value"), [
    ("BASE_ON", 1, 0.0),
    ("WALK_ZERO", 3, 0.03),
    ("SHAM_ON", 2, 0.0),
    ("BOTH_ZERO", 2, float("nan")),
])
def test_forged_charge_or_zero_denominator_rejected(monkeypatch, arm, index, value):
    row = list(report.SOURCE[arm])
    row[index] = value
    monkeypatch.setitem(report.SOURCE, arm, tuple(row))
    with pytest.raises(v7.V7Rejected):
        report.review_real_direct_basal_dev_metadata()
