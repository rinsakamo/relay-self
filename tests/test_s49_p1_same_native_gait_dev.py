"""Fifth L0 same-input fatigue gait candidate, no new issuer."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import compose_third_move_native_dev
from adapters.mineflayer.s49_p1_same_native_gait_dev import compare_fifth_p1_gait_dev
from test_s49_p1_fifth_epoch_dev import inputs


def test_same_fifth_native_probe_produces_distinct_gait_budget_without_issuing(monkeypatch):
    action, prior, move, fifth = inputs(monkeypatch)
    model, third = compose_third_move_native_dev(
        action, move, previous_wait_native_seq=prior.seq,
    )
    out = compare_fifth_p1_gait_dev(model, fifth)
    assert out["status"] == "DEV_SAME_NATIVE_PROBE_P1_GAIT_POLICY_COMPARISON"
    assert out["session_id"] == fifth.session_id
    assert out["fifth_native_seq"] == fifth.seq
    assert out["fifth_native_request_id"] == fifth.request_id
    assert out["third_original_action_id"] == action["action"]
    assert out["third_original_move_distance_m"] == action["movement_m"]
    assert out["p1_model_fatigue"] == third["p1_model_fatigue_after"]
    assert out["baseline_nominal_command_duration_s"] == pytest.approx(0.20)
    assert 0 < out["fatigue_aware_candidate_duration_s"] < 0.20
    assert out["modeled_duration_reduction_s"] == pytest.approx(
        0.20 - out["fatigue_aware_candidate_duration_s"],
    )
    assert out["modeled_one_tick_capacity_blocks"] < 1.0
    assert out["baseline_one_tick_capacity_blocks"] == 1.0
    assert out["same_native_world_input"] is True
    assert out["original_l0_choice_changed"] is False
    assert out["candidate_executed"] is False
    assert out["new_grants"] == 0
    assert out["new_action_issuers"] == 0
    assert out["wait_ticks_admitted"] == 0
    assert out["qualification_go"] is False


@pytest.mark.parametrize("bad", [
    "foreign", "stale", "wrong_request", "zero_fatigue",
    "changed_profile", "wrong_move_action",
])
def test_wrong_model_or_native_source_never_produces_motor_authority(monkeypatch, bad):
    action, prior, move, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, move, previous_wait_native_seq=prior.seq,
    )
    if bad == "foreign":
        fifth = replace(fifth, session_id="foreign")
    elif bad == "stale":
        fifth = replace(fifth, seq=move.seq)
    elif bad == "wrong_request":
        fifth = replace(fifth, request_id="wrong-correlation")
    elif bad == "zero_fatigue":
        model = replace(model, model_fatigue=0.0)
    elif bad == "changed_profile":
        model = replace(model, model_profile_sha256="changed")
    elif bad == "wrong_move_action":
        model = replace(model, third_action_id="forged-action")
    with pytest.raises(BoundaryRejected):
        compare_fifth_p1_gait_dev(model, fifth)
