"""V6 prospective paired World plan: source-only and negative controls."""
from __future__ import annotations

import copy
import json

import pytest

from experiments.validation import v6_b0_paired_world_plan as plan


def test_all_six_arms_two_regimes_four_independent_start_slots_not_worlds():
    d = plan.load_plan_spec()
    rows = plan.offline_session_slots()
    assert d["schema"] == "RELAYSELF_V6_B0_PAIRED_WORLD_PRE_ADMISSION_1"
    assert d["parent_v6_head"] == plan.V6_G0_HEAD
    assert len(rows) == 48
    assert len({x["world_start_slot"] for x in rows}) == 4
    for start in plan.STARTS:
        block = [x for x in rows if x["world_start_slot"] == start]
        assert len(block) == 12
        assert {(x["regime"], x["arm"]) for x in block} == {
            (r, a) for r, _ in plan.REGIMES for a in plan.ARMS
        }
        assert [x["planned_order"] for x in block] == list(range(12))
    assert all(x["world_start_digest"] is None for x in rows)
    assert all(not x["user_live_grant"] for x in rows)
    assert not d["admission"]["prospective_real_trial_authorized"]
    assert not d["admission"]["production_go"]


@pytest.mark.parametrize(("section", "key", "value"), [
    ("design", "total_planned_world_sessions", 12),
    ("design", "initial_native_food", 14),
    ("design", "first_opportunity_m0_tick", 12),
    ("design", "max_issued_move_per_session", 9),
    ("design", "exogenous_food_schedule", "M0_TICK11_ONLY"),
    ("design", "new_explicit_permission_per_session", False),
    ("design", "arms", ["SENSOR_ON", "ALWAYS_SEEK"]),
    ("endpoints", "primary", "BEST_OF_EATS_AND_ENERGY"),
    ("endpoints", "null", "SENSOR_MUST_WIN"),
    ("endpoints", "feasibility_floor_not_power_calculation", False),
    ("admission", "six_arm_s_real_controller", True),
    ("admission", "same_world_reset_r_attested", True),
    ("admission", "actual_world_trials", 1),
    ("admission", "b0_science_g3", "GO"),
])
def test_no_silent_amendment_or_earned_authority(section, key, value):
    d = copy.deepcopy(plan.load_plan_spec())
    d[section][key] = value
    with pytest.raises(plan.V6PlanRejected):
        plan.validate_plan_spec(d)


@pytest.mark.parametrize(("index", "key", "value"), [
    (0, "arm", "SENSOR_ONN"),
    (0, "regime", "HIGH"),
    (0, "world_start_slot", "REAL_HASH"),
    (0, "planned_order", 1),
    (0, "world_start_digest", "0" * 64),
    (0, "native_opportunity_time_attested", True),
    (0, "user_live_grant", True),
    (0, "s_physical_arm_implemented", True),
    (0, "world_run_status", "LIVE_PASS"),
    (12, "initial_m0_energy", 100),
])
def test_no_fabricated_physical_plan_slots(index, key, value):
    rows = plan.offline_session_slots()
    rows[index][key] = value
    with pytest.raises(plan.V6PlanRejected):
        plan.validate_offline_slots(rows)


def test_dropped_or_duplicated_world_session_slot_rejected():
    rows = plan.offline_session_slots()
    with pytest.raises(plan.V6PlanRejected):
        plan.validate_offline_slots(rows[:-1])
    rows = plan.offline_session_slots()
    rows[12] = copy.deepcopy(rows[0])
    with pytest.raises(plan.V6PlanRejected):
        plan.validate_offline_slots(rows)


def test_explicit_null_not_engineered_ecological_success(capsys):
    assert plan.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["classification"] == "V6_PAIRED_WORLD_PRE_ADMISSION_PROTOCOL_ONLY"
    assert out["total_unexecuted_session_slots"] == 48
    assert out["number_of_real_world_trials"] == 0
    assert not out["s_full_six_arm_mode_qualified"]
    assert not out["r_native_elapsed_world_clock_matched"]
    assert out["science_g3"] == "NO_GO" and not out["production_go"]
