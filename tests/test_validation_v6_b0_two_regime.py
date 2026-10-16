"""V6 bacterial L0 first opportunity and nonpromotion tests."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import v6_b0_two_regime as v6


def test_low_high_and_six_controls_including_equal_information_cheap():
    r = v6.first_source_choice()
    lo, hi = r["first_choices"]["LOW"], r["first_choices"]["HIGH"]
    assert (lo["true_energy"], lo["sensor_reading"]) == (6.5, 6)
    assert (hi["true_energy"], hi["sensor_reading"]) == (14.5, 14)
    assert lo["SENSOR_ON"] == "SEEK" and hi["SENSOR_ON"] == "WAIT"
    assert lo["SHAM_ON"] == "SEEK" and hi["SHAM_ON"] == "WAIT"
    assert lo["SENSOR_MASKED_HIGH"] == hi["SENSOR_MASKED_HIGH"] == "WAIT"
    assert lo["ALWAYS_SEEK"] == hi["ALWAYS_SEEK"] == "SEEK"
    assert lo["ALWAYS_WAIT"] == hi["ALWAYS_WAIT"] == "WAIT"
    assert lo["SENSOR_ON"] == lo["EQUAL_INFO_CHEAP_THRESHOLD"]
    assert hi["SENSOR_ON"] == hi["EQUAL_INFO_CHEAP_THRESHOLD"]
    assert r["oracle_only_controls_not_s_live"] == [
        "ALWAYS_WAIT", "EQUAL_INFO_CHEAP_THRESHOLD",
    ]
    assert r["ecological_value"] == "NOT_ATTESTED"
    assert not r["science_go"] and r["new_world_runs"] == 0


@pytest.mark.parametrize(("area", "key", "value"), [
    ("top", "parent_v5_head", "0" * 40),
    ("top", "state", "LIVE"),
    ("source", "wait_m0_ticks", 1),
    ("source", "world_food", 20),
    ("source", "initial_energy_high", 30),
    ("source", "horizon_m0_ticks", 24),
    ("endpoints", "cheap_info_tie_b0_allowed", False),
    ("admission", "s_six_arm_live_mode", True),
    ("admission", "user_per_run_grant", True),
    ("admission", "new_real_world_trials", 1),
    ("admission", "scientific_g3", "GO"),
])
def test_v6_source_or_admission_substitution_rejected(area, key, value):
    x = copy.deepcopy(v6.manifest())
    (x if area == "top" else x[area])[key] = value
    with pytest.raises(v6.V6Rejected):
        v6.verify(x)


def test_manifest_and_console_do_not_claim_world_run(capsys):
    m = v6.manifest()
    old = copy.deepcopy(m)
    assert v6.verify(m) == old and m == old
    assert v6.main() == 0
    x = json.loads(capsys.readouterr().out)
    assert x["new_world_runs"] == 0 and not x["science_go"]
