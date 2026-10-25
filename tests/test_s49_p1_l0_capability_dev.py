"""S49 true postwait native & two model counterfactual capacity envelopes."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_capability_dev import (
    compare_body_capability_l0_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from test_s49_p1_l0_shadow_dev import source


def evaluate(monkeypatch, *, distance=None):
    body, native, handoff, reviewed, retained = source(monkeypatch)
    if distance is not None:
        from test_self_live_think import native_probe
        updated = native_probe(native.seq, distance, sid=native.session_id)
        native = replace(updated, request_id=native.request_id)
        # The original postwait model must join the specific native pose.
        body, _ = compose_s49_p1_postwait_native_dev(
            handoff, reviewed,
            {
                "action": handoff.action_id,
                "source": handoff.session_id,
                "terminal": "outcome",
                "execution_evidence": {
                    "after_observation": {"seq": native.seq - 3},
                },
            }, native, expected_request_id=native.request_id,
        )
    profile = FatigueProfile(enabled=True, initial=0.0)
    return body, native, handoff, reviewed, retained, profile


def test_same_native_near_world_before_move_vs_after_wait_gait(monkeypatch):
    body, native, handoff, reviewed, retained, profile = evaluate(monkeypatch)
    view = compare_body_capability_l0_dev(
        body, native, handoff, reviewed, profile, retained,
    )
    assert view["status"] == "DEV_P1_L0_S42_NOMINAL_GAIT_COMPARISON"
    assert view["s42_selection_unchanged"] == "MOVE_AWAY"
    assert view["nominal_one_tick_demand_blocks"] == 1.0
    assert view["modeled_after_move_one_tick_capacity_blocks"] == pytest.approx(
        1.0 - 0.7 * (0.6269065734210617 * 0.04),
    )
    assert view["modeled_after_move_one_tick_capacity_blocks"] < (
        view["modeled_after_wait_one_tick_capacity_blocks"]
    )
    assert view["modeled_after_wait_one_tick_capacity_blocks"] == 1.0
    assert view["after_move_on_postwait_world_counterfactual"] == (
        "MOVE_AWAY_SCALE_TO_CAPACITY_MODEL_ONLY"
    )
    assert view["after_wait_on_actual_postwait_world_model"] == (
        "MOVE_AWAY_NOMINAL_GAIT_MODEL_ONLY"
    )
    assert view["native_seq"] == native.seq
    assert view["body_epoch_id"] == body.epoch_id
    assert view["counterfactual_same_world_geometry_not_native_at_move_time"] is True
    assert view["original_s49_action_displacement_is_not_one_tick_demand"] is True
    assert view["original_l0_policy_modified"] is False
    assert view["original_l0_decide_called"] is False
    assert view["new_action_grant_issued"] is False
    assert view["actual_native_actions_added"] == 0
    assert view["additional_native_reads"] == 0
    assert view["production_p1_state_updated"] is False


def test_far_world_keeps_wait_without_introducing_move(monkeypatch):
    body, native, handoff, reviewed, retained, profile = evaluate(
        monkeypatch, distance=10.0,
    )
    view = compare_body_capability_l0_dev(
        body, native, handoff, reviewed, profile, retained,
    )
    assert view["s42_selection_unchanged"] == "WAIT"
    assert view["after_move_on_postwait_world_counterfactual"] == (
        "S42_WAIT_UNCHANGED"
    )
    assert view["after_wait_on_actual_postwait_world_model"] == (
        "S42_WAIT_UNCHANGED"
    )
    assert view["new_action_grant_issued"] is False


@pytest.mark.parametrize("bad", (
    "foreign_native", "request_changed", "p1_review_crossworld",
    "p1_profile_changed", "body_foreign", "new_retained", "no_p1",
))
def test_bad_input_cannot_be_promoted_to_authorized_l0(monkeypatch, bad):
    body, native, handoff, reviewed, retained, profile = evaluate(monkeypatch)
    if bad == "foreign_native":
        native = replace(native, session_id="another-session")
    elif bad == "request_changed":
        native = replace(native, request_id="unexpected")
    elif bad == "p1_review_crossworld":
        reviewed = {**reviewed, "world": "crossworld"}
    elif bad == "p1_profile_changed":
        profile = FatigueProfile(enabled=True, initial=0.0, nominal_move_limit_blocks=2.0)
    elif bad == "body_foreign":
        body = replace(body, self_id="other-self")
    elif bad == "new_retained":
        _, original, _, _, _, _ = __import__(
            "test_postmain_two_epoch_continuation"
        )._epoch_one()
        retained = original.previous_state
    elif bad == "no_p1":
        profile = FatigueProfile()
    with pytest.raises(BoundaryRejected):
        compare_body_capability_l0_dev(
            body, native, handoff, reviewed, profile, retained,
        )
