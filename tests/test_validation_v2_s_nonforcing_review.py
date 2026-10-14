"""V2 independent nonforcing source-boundary negative controls."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from experiments.validation import v2_s_nonforcing_review as v


def sample():
    return {
        "classification": v.CLASSIFICATION,
        "s_source_head": v.S_NONFORCING_HEAD,
        "source_kind": "S_OWNED_SYNTHETIC_MINEFLAYER_SHAPED_FIXTURE",
        "s_opportunity_max_decisions_per_epoch": 24,
        "s_issued_move_max_per_epoch": 8,
        "s_epoch_max": 2,
        "v_registered_global_m0_horizon": 16,
        "v_registered_total_move_budget": 8,
        "arms": {
            "SENSOR_ON": ["WAIT"] * 7 + ["SEEK"],
            "SHAM_ON": ["WAIT"] * 7 + ["SEEK"],
            "SENSOR_MASKED": ["WAIT"] * 16,
            "CHEAP_NATIVE": ["SEEK"],
        },
        "m0_end_state": {
            "SENSOR_ON": {
                "energy": 8.5, "tick": 7, "terminal": False, "credits": 0,
            },
            "SHAM_ON": {
                "energy": 8.5, "tick": 7, "terminal": False, "credits": 0,
            },
            "SENSOR_MASKED": {
                "energy": 4, "tick": 16, "terminal": False, "credits": 0,
            },
            "CHEAP_NATIVE": {
                "energy": 12, "tick": 0, "terminal": False, "credits": 0,
            },
        },
        "quantization_boundary": (
            "E8.5_SENSOR_8_TIES_TO_EVEN_SEEK_AT_DECISION_8"
        ),
        "independent_real_world_starts": 0,
        "actual_world_trials": 0,
        "physical_original_readback": "NOT_RUN",
        "no_action_issued": True,
        "v2_live_trial_admitted": False,
        "scientific_g3": "NO_GO",
        "science_go": False,
        "blockers": v.EXPECTED_BLOCKERS.copy(),
    }


def test_4_arm_same_input_synthetic_example_not_trial_qualified():
    r = v.validate_review(sample())
    assert r["arms"]["SENSOR_ON"] == r["arms"]["SHAM_ON"]
    assert r["arms"]["CHEAP_NATIVE"] == ["SEEK"]
    assert len(r["arms"]["SENSOR_MASKED"]) == 16
    assert r["m0_end_state"]["SENSOR_MASKED"]["energy"] == 4
    assert not r["v2_live_trial_admitted"] and not r["science_go"]
    assert r["s_opportunity_max_decisions_per_epoch"] != (
        r["v_registered_global_m0_horizon"]
    )


@pytest.mark.parametrize(("section", "key", "value"), [
    (None, "classification", "V2_S_NONFORCING_SCIENCE_PASS"),
    (None, "source_kind", "ORIGINAL_NATIVE_WORLD"),
    (None, "s_source_head", "0" * 40),
    (None, "independent_real_world_starts", 4),
    (None, "actual_world_trials", 1),
    (None, "physical_original_readback", "PASS"),
    (None, "no_action_issued", False),
    (None, "v2_live_trial_admitted", True),
    (None, "science_go", True),
    (None, "scientific_g3", "GO"),
    (None, "s_opportunity_max_decisions_per_epoch", 16),
    (None, "s_issued_move_max_per_epoch", 4),
    (None, "v_registered_total_move_budget", 16),
    (None, "quantization_boundary", "E8.5_SENSOR_9"),
    ("arms", "SENSOR_ON", ["WAIT"] * 8 + ["SEEK"]),
    ("arms", "CHEAP_NATIVE", ["WAIT"]),
    ("m0_end_state", "SENSOR_MASKED", {
        "energy": 0, "tick": 16, "terminal": True, "credits": 0,
    }),
])
def test_modified_or_promoted_report_rejected(section, key, value):
    d = copy.deepcopy(sample())
    if section is None:
        d[key] = value
    else:
        d[section][key] = value
    with pytest.raises(v.SBoundaryRejected):
        v.validate_review(d)


def test_blocker_omission_or_unexpected_claim_rejected():
    d = sample()
    d["blockers"].pop()
    with pytest.raises(v.SBoundaryRejected):
        v.validate_review(d)
    d = sample()
    d["native_action_attested"] = True
    with pytest.raises(v.SBoundaryRejected):
        v.validate_review(d)


def test_source_loop_bounds_parser_safely_checks_declared_functions(tmp_path):
    path = tmp_path / "fixture.py"
    path.write_text(
        "async def acquire_staged_ground_flesh():\n"
        "    for n in range(24):\n"
        "        pass\n"
        "    for i in range(8):\n"
        "        pass\n"
        "    for j in range(8):\n"
        "        pass\n", encoding="utf-8",
    )
    assert v._range_calls(path, "acquire_staged_ground_flesh") == [24, 8, 8]
    with pytest.raises(v.SBoundaryRejected):
        v._range_calls(Path(str(path) + ".missing"), "source")
    path.write_text("def changed():\n    return True\n", encoding="utf-8")
    with pytest.raises(v.SBoundaryRejected):
        v._range_calls(path, "acquire_staged_ground_flesh")
