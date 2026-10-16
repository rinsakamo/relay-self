"""B0 bacteria-like V5: L0-only eligibility and cheap null negative controls."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import v5_b0_l0 as v5


def test_l0_only_milestone_does_not_promote_complex_cognition():
    m = v5.load_manifest()
    assert m["frozen"] == ["V2", "V3", "V4"]
    assert "L1" in m["not_required_at_b0"]
    assert "LEARNING" in m["not_required_at_b0"]
    assert m["scientific_targets"]["higher_cognition_equal_information_cheap_null_preserved"]
    assert m["prospective"]["cheap_information_equivalence_allowed_for_b0"]
    assert m["admission"]["original_b0_r_readback"] == "REVIEW_ONLY_58_FILES_50_OF_50"
    assert not m["admission"]["science_go"]


def test_regime_choices_and_equal_information_cheap_are_prospective_only():
    r = v5.source_only_l0_matrix()
    lo, hi = (r["choices"][x] for x in v5.REGIMES)
    assert (lo["true_energy"], lo["observed_energy"]) == (3.5, 4)
    assert (hi["true_energy"], hi["observed_energy"]) == (19.5, 20)
    assert lo["SENSOR_ON"] == lo["SHAM_ON"] == "SEEK"
    assert hi["SENSOR_ON"] == hi["SHAM_ON"] == "WAIT"
    assert hi["ALWAYS_SEEK"] == "SEEK"
    assert lo["MASKED_HIGH"] == hi["MASKED_HIGH"] == "WAIT"
    assert all(r["choices"][k]["EQUAL_INFORMATION_THRESHOLD"]
               == r["choices"][k]["SENSOR_ON"] for k in v5.REGIMES)
    assert not r["b0_invalidated_by_equivalent_cheap"]
    assert not r["higher_cognition_achieved"]
    assert r["ecological_benefit"] == "UNTESTED"
    assert r["world_trials"] == 0 and not r["science_go"]


def test_high_energy_food_cost_can_reverse_relative_utility():
    x = v5.no_presumed_ecological_advantage()
    assert x["on_wait"] == 17.5
    assert x["blind_food_obtained"] == 19
    assert x["blind_food_not_obtained"] == 16.5
    assert x["blind_food_obtained"] > x["on_wait"] > x["blind_food_not_obtained"]
    assert x["source"] == "UNAUTHENTICATED_ILLUSTRATIVE_ONLY"
    assert not x["science_go"]


@pytest.mark.parametrize(("section", "key", "value"), [
    ("admission", "new_world_trials", 1),
    ("admission", "new_user_grants", True),
    ("admission", "science_go", True),
    ("admission", "real_world_source_clock_qualified", True),
    ("admission", "ecological_effect", "PROVEN"),
    ("prospective", "fixed_threshold", 5),
    ("prospective", "cheap_information_equivalence_allowed_for_b0", False),
    ("prospective", "no_posthoc_optimization", False),
    ("prospective", "learn_train_holdout_required_for_b0", True),
    ("prospective", "controls", ["SENSOR_ON"]),
    ("scientific_targets", "t3", "MUST_BEAT_CHEAP"),
])
def test_changed_scope_or_fabricated_live_gate_rejected(section, key, value):
    m = copy.deepcopy(v5.load_manifest())
    m[section][key] = value
    with pytest.raises(v5.V5Rejected):
        v5.validate_manifest(m)


@pytest.mark.parametrize("actions", [
    ["WAIT"] * 5, ["EAT"] * 4, ["MOVE", "WAIT"],
    ["FIGHT", "WAIT", "WAIT", "WAIT"], ["MOVE", "WAIT", "EAT", 1],
])
def test_unregistered_simulation_inputs_rejected(actions):
    with pytest.raises(v5.V5Rejected):
        v5.synthetic_energy(actions)


def test_cli_does_not_promote_minecraft_run(capsys):
    assert v5.main() == 0
    d = json.loads(capsys.readouterr().out)
    assert d["classification"] == "V5_B0_L0_ONLY_PROSPECTIVE_NOT_RUN"
    assert not d["equal_information_cheap_beating_required"]
    assert d["ecological_outcome"] == "UNTESTED"
    assert d["world_trials"] == 0 and not d["science_go"]
