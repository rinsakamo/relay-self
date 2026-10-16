"""V7 Paper physics: strictly prospective factorial source-cost design."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.validation import v7_m02_physics as v


def test_frozen_v7_manifest_is_not_existing_v2_v6_science():
    p = v.load_manifest()
    assert p["schema"] == v.SCHEMA
    assert p["boundaries"]["actual_20_science_world_trials"] == 0
    assert p["boundaries"]["third_qualification_grant_consumed"]
    assert not p["boundaries"]["science_execution_authorized"]
    assert p["source_qualification"]["original_physical_run"] == 38730925452


def test_four_seed_five_arm_cheap_sham_synthetic_math():
    records = v.synthetic_fixture()
    result = v.review_synthetic(records)
    assert result["classification"] == v.CLASSIFICATION
    assert result["synthetic_rows"] == 20
    assert result["actual_world_starts"] == 0
    assert not result["v_science_go"]
    assert not result["ecological_calibration_qualified"]
    for group in result["per_seed_descriptive_contrasts"]:
        assert group["on_minus_sham"] == pytest.approx(0, abs=1e-8)
        assert group["basal_effect"] == pytest.approx(0.2)
        assert group["walk_effect"] > 0
        assert group["interaction"] == pytest.approx(0, abs=1e-8)
        assert 0 < group["walk_to_basal_ratio"] < 0.1


@pytest.mark.parametrize(("field", "value"), [
    ("schema", "OLD_M0_V3"),
    ("authority_issue", 537),
    ("status", "SCIENCE_PASS"),
    ("rate_arms", {"BASE_ON": {"basal_multiplier": 1, "walk_multiplier": 1}}),
])
def test_manifest_top_level_cannot_be_promoted(field, value):
    doc = copy.deepcopy(v.load_manifest())
    doc[field] = value
    with pytest.raises(v.V7Rejected):
        v.validate_manifest(doc)


@pytest.mark.parametrize(("section", "field", "value"), [
    ("boundaries", "actual_20_science_world_trials", 20),
    ("boundaries", "science_execution_authorized", True),
    ("boundaries", "third_qualification_grant_consumed", False),
    ("boundaries", "ecological_calibration_qualified", True),
    ("source_qualification", "original_physical_run", 38726682186),
    ("source_qualification", "qualification_scope", "GENERAL_INTELLIGENCE"),
    ("design", "total_planned_trials", 5),
    ("design", "duration_world_ticks", 16),
    ("design", "max_observed_path_blocks", 20),
    ("design", "no_hunger_effect", False),
    ("design", "clock_rule", "HOST_SECONDS_AS_WORLD_TICKS"),
    ("design", "primary", "NATIVE_FOOD_METER_DELTA"),
    ("invariants", "cognition_still_off", False),
    ("invariants", "paper_source_qualification_NOT_reused_for_changed_configs", False),
])
def test_prereg_source_physio_cost_guards_are_nonpromoting(section, field, value):
    doc = copy.deepcopy(v.load_manifest())
    doc[section][field] = value
    with pytest.raises(v.V7Rejected):
        v.validate_manifest(doc)


@pytest.mark.parametrize(("field", "value"), [
    ("origin", "PAPER_NATIVE_AUTHENTICATED"),
    ("science_attested", True),
    ("virtual_m0_ledger_used", True),
    ("world_ticks", 199),
    ("motion_packets", 0),
    ("observed_path_blocks", 0),
    ("billed_basal", 1.0),
    ("billed_walk", 2.0),
    ("walk_native_event_replacement", 0.001),
    ("other_charges", 0.005),
    ("native_food_end", 21),
    ("native_saturation_end", float("nan")),
    ("nonce", "reused-unknown"),
])
def test_invalid_or_promoted_pseudophysical_row_blocked(field, value):
    rows = v.synthetic_fixture()
    rows[0][field] = value
    with pytest.raises(v.V7Rejected):
        v.review_synthetic(rows)


def test_missing_duplicate_extra_or_mismatched_world_arms_rejected():
    rows = v.synthetic_fixture()
    with pytest.raises(v.V7Rejected):
        v.review_synthetic(rows[:-1])
    rows = v.synthetic_fixture()
    rows[1]["arm"] = rows[0]["arm"]
    with pytest.raises(v.V7Rejected):
        v.review_synthetic(rows)
    rows = v.synthetic_fixture()
    rows[1]["synthetic_setup_sha256"] = "f" * 64
    with pytest.raises(v.V7Rejected, match="setup"):
        v.review_synthetic(rows)
    rows = v.synthetic_fixture()
    rows[1]["observed_path_blocks"] = 1.15
    rows[1]["billed_walk"] = 1.15 * 0.01
    with pytest.raises(v.V7Rejected, match="paths"):
        v.review_synthetic(rows)
    rows = v.synthetic_fixture()
    rows[2]["nonce"] = rows[0]["nonce"]
    with pytest.raises(v.V7Rejected):
        v.review_synthetic(rows)


def test_sham_is_an_actual_cheap_null_not_better_than_base():
    p = v.load_manifest()
    assert p["rate_arms"]["BASE_ON"] == p["rate_arms"]["SHAM_ON"]
    records = v.synthetic_fixture()
    for row in records:
        if row["arm"] == "SHAM_ON":
            row["billed_walk"] += 0.001
    with pytest.raises(v.V7Rejected, match="charges"):
        v.review_synthetic(records)


def test_reject_duplicate_json_and_nonfinite_manifest(tmp_path: Path):
    raw = v.MANIFEST.read_text()
    path = tmp_path / "duplicate.json"
    path.write_text(raw.replace('"schema":', '"schema": "fake", "schema":', 1))
    with pytest.raises(v.V7Rejected, match="duplicate"):
        v.load_manifest(path)
    path.write_text(raw.replace('"basal_standard": 0.001', '"basal_standard": NaN'))
    with pytest.raises(v.V7Rejected):
        v.load_manifest(path)
    path.write_text(json.dumps({"schema": v.SCHEMA}))
    with pytest.raises(v.V7Rejected):
        v.load_manifest(path)
