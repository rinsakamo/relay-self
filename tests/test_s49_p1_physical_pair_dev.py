"""DEV bounded P1 physical-pair scenarios: same original native source tests."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import compose_third_move_native_dev
from adapters.mineflayer.s49_p1_physical_pair_dev import (
    BASELINE,
    STRESS,
    evaluate_sixth_motor_sensitivity_dev,
)
from adapters.mineflayer.s49_p1_same_native_gait_dev import compare_fifth_p1_gait_dev
from test_s49_p1_fifth_epoch_dev import inputs


def test_distinct_scenarios_same_original_native_input_no_action_authority(monkeypatch):
    action, prior, third, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, third, previous_wait_native_seq=prior.seq,
    )
    gait = compare_fifth_p1_gait_dev(model, fifth)
    nominal = evaluate_sixth_motor_sensitivity_dev(model, gait, BASELINE)
    stress = evaluate_sixth_motor_sensitivity_dev(model, gait, STRESS)
    assert nominal["third_action_id"] == stress["third_action_id"] == action["action"]
    assert nominal["third_observed_move_m"] == stress["third_observed_move_m"]
    assert nominal["fifth_native_seq"] == stress["fifth_native_seq"] == fifth.seq
    assert nominal["scenario"] == BASELINE
    assert stress["scenario"] == STRESS
    assert nominal["duration_s"] == gait["fatigue_aware_candidate_duration_s"]
    assert stress["duration_s"] == pytest.approx(0.06)
    assert nominal["duration_s"] > stress["duration_s"]
    assert stress["hypothetical_fatigue"] == 1.0
    assert nominal["hypothetical_fatigue"] == model.model_fatigue
    assert nominal["sensitivity_not_calibration"] is True
    for case in (nominal, stress):
        assert case["native_fatigue_measured"] is False
        assert case["action_permission"] is False
        assert case["zero_wait_ticks_imputed"] is True
        assert case["source_bound_tick"] is None
        assert case["qualification_go"] is False
        assert case["science_go"] is False
        assert case["additional_issuers"] == 0
        assert case["additional_native_receivers"] == 0


@pytest.mark.parametrize("fault", [
    "wrong_action", "wrong_distance", "wrong_profile", "changed_native",
    "wrong_fifth", "missing_gait", "forged_model", "unsupported_scenario",
])
def test_mutated_sources_and_scenarios_fail_closed(monkeypatch, fault):
    action, prior, third, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, third, previous_wait_native_seq=prior.seq,
    )
    gait = compare_fifth_p1_gait_dev(model, fifth)
    if fault == "wrong_action":
        gait = {**gait, "third_original_action_id": "fake"}
    elif fault == "wrong_distance":
        gait = {**gait, "third_original_move_distance_m": 200}
    elif fault == "wrong_profile":
        gait = {**gait, "original_p1_model_sha256": "changed"}
    elif fault == "changed_native":
        gait = {**gait, "same_native_world_input": False}
    elif fault == "wrong_fifth":
        gait = {**gait, "fifth_native_seq": -1}
    elif fault == "missing_gait":
        gait = {}
    elif fault == "forged_model":
        model = replace(model, third_action_id="fake")
    with pytest.raises(BoundaryRejected):
        evaluate_sixth_motor_sensitivity_dev(
            model, gait,
            "INVALID" if fault == "unsupported_scenario" else STRESS,
        )
