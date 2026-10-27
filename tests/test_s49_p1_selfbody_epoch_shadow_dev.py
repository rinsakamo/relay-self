"""Fail-closed next-epoch P1 SelfBody counterfactuals on synthetic Paper ticks."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_dev_wait_observed import (
    replay_p1_observed_static_wait_dev,
)
from adapters.mineflayer.s49_p1_selfbody_epoch_shadow_dev import (
    P1BodyEpochDevRejected,
    project_p1_static_next_body_epoch_dev,
)
from test_s49_p1_dev_wait_observed import example


def inputs(tmp_path):
    raw = example(tmp_path)
    model = replay_p1_observed_static_wait_dev(**raw)
    return dict(
        model=model, fence=raw["fence"], profile=raw["profile"],
        session_id=raw["session_id"],
        first_action_id=raw["first_action_id"],
        second_action_id=raw["second_action_id"],
    )


def test_two_retrospective_selfbody_hypotheses_not_native_state(tmp_path):
    d = inputs(tmp_path)
    unchanged = deepcopy(d)
    result = project_p1_static_next_body_epoch_dev(**d)
    assert d == unchanged
    assert result["classification"] == (
        "P1_RETROSPECTIVE_NEXT_SELFBODY_HYPOTHESES_DEV_ONLY"
    )
    assert result["epoch_hypotheses_count"] == 2
    assert result["body_origin"] == "hypothesis"
    assert result["paper_candidate_source_sha256"] == (
        d["model"]["paper_candidate_source_sha256"]
    )
    assert result["unclassified_gap_ticks_before_candidate"] > 0
    assert result["model_not_actual_fatigue_bounds"] is True
    assert result["no_recovery_carry_fatigue_bp"] > (
        result["wait_assumed_fatigue_bp"]
    )
    assert result["no_recovery_forward_dash_ceiling_bp"] < (
        result["wait_assumed_forward_dash_ceiling_bp"]
    )
    assert result["model_ceiling_gain_bp"] > 0
    assert result["next_original_action_is_historical"] is True
    assert result["native_present_or_postcandidate_p1_sensor"] is None
    assert result["physically_admitted_next_action_power"] is None
    assert result["original_s49_action_policy_modified"] is False
    assert result["new_action_issuers"] == 0
    assert result["additional_native_reads"] == 0
    assert result["live_p1_state_modified"] is False
    assert result["m0_posted"] is False
    assert result["qualified_wait_ticks"] == 0
    assert result["qualification_go"] is False
    assert result["science_go"] is False


@pytest.mark.parametrize("fault", [
    "model_class", "source_grade", "foreign_session", "wrong_first",
    "foreign_profile", "actual_recovery", "qualified_wait", "source_bound",
    "live_owner", "m0_post", "fake_qualification", "wrong_digest",
    "out_of_window", "wrong_tick_count", "wrong_end_tick",
    "second_before_candidate", "unknown_gap_lost", "bad_fatigue",
    "negative_recovery", "inconsistent_recovery", "wrong_fence",
    "owner_wait_claim", "fence_qualification", "wrong_actor",
])
def test_no_body_projection_from_mismatched_sources(tmp_path, fault):
    d = inputs(tmp_path)
    model, fence = d["model"], d["fence"]
    if fault == "model_class":
        model["classification"] = "P1_POSTED"
    elif fault == "source_grade":
        model["evidence_grade"] = "QUALIFIED"
    elif fault == "foreign_session":
        d["session_id"] = "foreign-session"
    elif fault == "wrong_first":
        d["first_action_id"] = "other-action"
    elif fault == "foreign_profile":
        model["p1_profile_sha256"] = "0" * 64
    elif fault == "actual_recovery":
        model["actual_physical_recovery_attested"] = True
    elif fault == "qualified_wait":
        model["r_qualified_wait_ticks"] = 1
    elif fault == "source_bound":
        model["source_bound_tick_created"] = True
    elif fault == "live_owner":
        model["live_p1_owner_state_modified"] = True
    elif fault == "m0_post":
        model["m0_posted"] = True
    elif fault == "fake_qualification":
        model["qualification_go"] = True
    elif fault == "wrong_digest":
        model["paper_candidate_source_sha256"] = "g" * 64
    elif fault == "out_of_window":
        model["first_tick"] -= 1
    elif fault == "wrong_tick_count":
        model["dev_wait_model_ticks_replayed"] -= 1
    elif fault == "wrong_end_tick":
        model["p1_dev_model_world_tick"] -= 1
    elif fault == "second_before_candidate":
        fence["paper_second_owner_fence_delivery_tick"] = model["last_tick"]
    elif fault == "unknown_gap_lost":
        model["p1_start_assumption_gap_ticks"] = 0
    elif fault == "bad_fatigue":
        model["p1_dev_model_before"] = float("nan")
    elif fault == "negative_recovery":
        model["p1_dev_model_after"] = model["p1_dev_model_before"] + .1
    elif fault == "inconsistent_recovery":
        model["p1_dev_model_recovered"] = 0.00001
    elif fault == "wrong_fence":
        fence["paper_causal_subwindow_last_tick"] -= 1
    elif fault == "owner_wait_claim":
        fence["physical_WAIT_admitted"] = True
    elif fault == "fence_qualification":
        fence["qualification_go"] = True
    elif fault == "wrong_actor":
        fence["session_id"] = "other-session"
    with pytest.raises(P1BodyEpochDevRejected):
        project_p1_static_next_body_epoch_dev(**d)


@pytest.mark.parametrize("value", ["", "bad session", "other\nsession"])
def test_bad_self_identity_rejected(tmp_path, value):
    d = inputs(tmp_path)
    d["self_id"] = value
    with pytest.raises(P1BodyEpochDevRejected):
        project_p1_static_next_body_epoch_dev(**d)
