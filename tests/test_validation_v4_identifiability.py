"""V4 V-owner G0 identifiability, source-shaped source-only negative gates."""
from __future__ import annotations

import copy

import pytest

from experiments.validation import v4_identifiability as v4


def test_abstract_policy_phenotypes_and_info_matched_cheap_no_go():
    r = v4.policy_choices()
    x = r["phases"]
    assert r["classification"] == "V4_G0_EQUAL_INFORMATION_CHEAP_REPLICATION_BLOCK"
    assert x["V3_FIXED_FIRST_ITEM"]["body_energy"] == 6.5
    assert x["V3_FIXED_FIRST_ITEM"]["on"] == x["V3_FIXED_FIRST_ITEM"]["cheap_native"] == "SEEK"
    assert x["LOW_ENERGY"]["on"] == "SEEK"
    assert x["LOW_ENERGY"]["masked"] == "WAIT"
    assert x["HIGH_ENERGY"]["on"] == "WAIT"
    assert x["HIGH_ENERGY"]["cheap_native"] == "SEEK"
    assert all(x[k]["on"] == x[k]["cheap_equal_information"] for k in v4.PHASES)
    assert not r["net_energy_or_survival_benefit_established"]
    assert not r["v4_real_s_product_mode_eligible"]
    assert not r["science_go"]


@pytest.mark.parametrize(("group", "key", "changed"), [
    ("top", "parent_v3_head", "0" * 40),
    ("top", "status", "LIVE_ADMITTED"),
    ("top", "s_source_head", "0" * 40),
    ("baseline_assumptions", "seek_threshold", 12),
    ("baseline_assumptions", "mask_bias", 0),
    ("baseline_assumptions", "basal_per_tick", 0),
    ("prospective_study_requirements", "cheap_equal_information", "NATIVE_ONLY"),
    ("prospective_study_requirements", "learned_policy_required_for_advanced_cognitive_claim", False),
    ("prospective_study_requirements", "train_holdout_disjoint_world_starts", False),
    ("prospective_study_requirements", "real_s_implementation_exists", True),
    ("prospective_study_requirements", "original_bytes_attested", True),
    ("prospective_study_requirements", "scientific_g3", "GO"),
    ("boundaries", "permission_granted", True),
    ("boundaries", "actual_world_trials", 1),
    ("boundaries", "science_go", True),
])
def test_counterfeit_eligible_or_changed_source_rejected(group, key, changed):
    m = copy.deepcopy(v4.load_manifest())
    dest = m if group == "top" else m[group]
    dest[key] = changed
    with pytest.raises(v4.V4Rejected):
        v4.validate_manifest(m)


def test_scenario_substitution_or_feasibility_fraud_rejected():
    m = copy.deepcopy(v4.load_manifest())
    m["factorial_source_shaped_states"][1]["expected_e"] = 8
    with pytest.raises(v4.V4Rejected):
        v4.validate_manifest(m)
    m = copy.deepcopy(v4.load_manifest())
    m["factorial_source_shaped_states"][2]["source_mode"] = "S_GROUNDV2_AVAILABLE"
    with pytest.raises(v4.V4Rejected):
        v4.validate_manifest(m)


def test_source_assumption_not_a_measured_cognitive_gain(capsys):
    assert v4.main() == 0
    printed = capsys.readouterr().out
    assert '"science_go": false' in printed
    assert '"matched_native_world_time": "NOT_ATTESTED"' in printed
