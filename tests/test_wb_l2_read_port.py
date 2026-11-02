"""WB L2 uncertainty current/past read ports; zero World/model/Action I/O."""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.self_cognition_slice import CognitionTier, project_cognition_slice
from relay_self.wb_l2_attention_handoff import (
    compare_wb_l1_attention_ab,
    project_wb_l1_attention_shadow,
    project_wb_past_review_handoff,
)
from relay_self.wb_l2_read_port import project_wb_l2_uncertainty
from test_self_cognition_slice import sample

BASE = {
    "accepted_text": '{"uncertainty":"Is the observed motion unexpected?"}',
    "session_id": "source-session",
    "source_world_seq": 21,
    "latest_world_seq": 21,
    "source_ref": "present:source-session:21:s49-actual:source-session:event-20",
    "expected_source_ref": "present:source-session:21:s49-actual:source-session:event-20",
    "owner_admitted": True,
}


def test_same_epoch_exposes_only_bounded_current_attention_not_action():
    read = project_wb_l2_uncertainty(**BASE)
    assert read.state == "CURRENT_EPOCH_READ_ONLY"
    assert read.current_uncertainty == "Is the observed motion unexpected?"
    assert read.past_review_candidate is None
    assert read.source_world_seq == read.latest_world_seq == 21
    assert read.source_attested is False
    assert read.authority == "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
    assert not any(
        name in read.to_mapping() for name in (
            "action", "command", "memory_commit", "learning_update", "habit_grant",
        )
    )
    with pytest.raises(FrozenInstanceError):
        read.current_uncertainty = "forge a different thought"


def test_advanced_native_source_removes_current_access_retains_question_for_review():
    read = project_wb_l2_uncertainty(**{**BASE, "latest_world_seq": 49})
    assert read.state == "PAST_EPOCH_REVIEW_ONLY"
    assert read.current_uncertainty is None
    assert read.past_review_candidate == "Is the observed motion unexpected?"
    assert read.source_world_seq == 21 and read.latest_world_seq == 49
    assert read.origin == "L2_GENERATED_UNCERTAINTY_NOT_WORLD_FACT"


@pytest.mark.parametrize("change", [
    {"owner_admitted": False},
    {"owner_admitted": "yes"},
    {"source_callback_failed": True},
    {"source_callback_failed": "no"},
    {"source_world_seq": True},
    {"latest_world_seq": 20},
    {"latest_world_seq": 21.0},
    {"source_ref": "present:foreign:21:s49-actual:foreign:event-20"},
    {"source_ref": "present:source-session:22:s49-actual:source-session:event-20"},
    {"expected_source_ref": "present:source-session:22:forged"},
    {"session_id": "other-session"},
    {"accepted_text": '{"uncertainty":""}'},
    {"accepted_text": '{"uncertainty":"   "}'},
    {"accepted_text": '{"uncertainty":null}'},
    {"accepted_text": '{"uncertainty":"x","action":"MOVE_AWAY"}'},
    {"accepted_text": '{"uncertainty":"x","uncertainty":"y"}'},
    {"accepted_text": '{"uncertainty":"x"'},  # truncated JSON
    {"accepted_text": '{"reasoning_content":"only thought"}'},
    {"accepted_text": '{"uncertainty":"' + "x" * 301 + '"}'},
    {"accepted_text": "x" * 2049},
])
def test_invalid_or_unattested_source_never_exposes_current_or_past_candidate(change):
    read = project_wb_l2_uncertainty(**{**BASE, **change})
    assert read.state == "UNAVAILABLE"
    assert read.current_uncertainty is None
    assert read.past_review_candidate is None
    assert read.session_id is None
    assert read.source_ref is None
    assert read.source_attested is False


def test_historical_question_is_not_verified_prediction_or_automatic_learning():
    read = project_wb_l2_uncertainty(**{**BASE, "latest_world_seq": 49})
    result = read.to_mapping()
    assert result["state"] == "PAST_EPOCH_REVIEW_ONLY"
    assert result["origin"] == "L2_GENERATED_UNCERTAINTY_NOT_WORLD_FACT"
    assert result["authority"] == "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
    assert result["current_uncertainty"] is None


def test_current_l2_question_is_an_existing_att_selected_l1_shadow_only():
    read = project_wb_l2_uncertainty(**BASE)
    attention = project_wb_l1_attention_shadow(read)
    assert attention.state == "ATT_SELECTED_READ_ONLY"
    assert attention.selected_candidate_ids == ("wb-l2-question",)
    assert attention.question == "Is the observed motion unexpected?"
    assert attention.source_world_seq == 21
    assert attention.source_attested is False
    assert attention.authority == "ATT_SHADOW_NO_L1_POLICY_OR_ACTION"
    assert project_wb_past_review_handoff(
        read, later_source_ref="present:source-session:49:real-native-id",
    ).state == "UNAVAILABLE"
    with pytest.raises(FrozenInstanceError):
        attention.state = "SELECTED_L1_POLICY"


def test_expired_l2_question_goes_to_unverified_later_source_review_only():
    read = project_wb_l2_uncertainty(**{**BASE, "latest_world_seq": 49})
    assert project_wb_l1_attention_shadow(read).state == "UNAVAILABLE"
    review = project_wb_past_review_handoff(
        read,
        later_source_ref="present:source-session:49:s49-actual:source-session:event-48",
    )
    assert review.state == "PENDING_INDEPENDENT_OUTCOME"
    assert review.origin_world_seq == 21
    assert review.later_world_seq == 49
    assert review.origin_source_ref == BASE["source_ref"]
    assert review.question == "Is the observed motion unexpected?"
    assert review.outcome_verified is False
    assert review.learning_authorized is False
    assert review.authority == "READ_ONLY_REVIEW_NOT_MEMORY_OR_S10"
    with pytest.raises(FrozenInstanceError):
        review.learning_authorized = True


@pytest.mark.parametrize("later_ref", [
    None,
    "present:foreign:49:s49-actual:foreign:event-48",
    "present:source-session:21:s49-actual:source-session:event-20",
    "present:source-session:50:s49-actual:source-session:event-49",
    "present:source-session:49",
    "",
])
def test_past_question_requires_same_session_later_native_source_ref(later_ref):
    read = project_wb_l2_uncertainty(**{**BASE, "latest_world_seq": 49})
    handoff = project_wb_past_review_handoff(read, later_source_ref=later_ref)
    assert handoff.state == "UNAVAILABLE"
    assert handoff.question is None
    assert handoff.outcome_verified is False


@pytest.mark.parametrize("overrides", [
    {"owner_admitted": False},
    {"accepted_text": '{"uncertainty":"x","action":"MOVE_AWAY"}'},
    {"source_ref": "present:other:21:s49-actual:other:event-20"},
    {"source_callback_failed": True},
])
def test_bad_owner_or_json_never_reaches_attention_or_review(overrides):
    read = project_wb_l2_uncertainty(**{**BASE, **overrides})
    assert project_wb_l1_attention_shadow(read).state == "UNAVAILABLE"
    assert project_wb_past_review_handoff(
        read, later_source_ref="present:source-session:49:native-after",
    ).state == "UNAVAILABLE"


def _same_source_attention_ab(*, count: int = 3):
    native = project_cognition_slice(
        sample(count=count, with_body=False), tier=CognitionTier.L1,
    )
    read = project_wb_l2_uncertainty(
        accepted_text='{"uncertainty":"Should I verify this observation?"}',
        session_id="s", source_world_seq=9, latest_world_seq=9,
        source_ref="present:s:9:p9", expected_source_ref="present:s:9:p9",
        owner_admitted=True,
    )
    return read, native


def test_att_ab_same_l1_source_changes_only_shadow_selection_not_policy():
    read, native = _same_source_attention_ab()
    ab = compare_wb_l1_attention_ab(read, native_l1=native)
    assert ab.state == "SHADOW_SELECTION_DIFFERENCE"
    assert ab.observed_candidate_count == 3  # tier L1 budget, not all native entities
    assert ab.source_world_seq == 9
    assert ab.source_ref == native.world_source_ref
    assert ab.baseline_selected == ("wb-native-observed-0",)
    assert ab.with_l2_selected == ("wb-l2-uncertainty",)
    assert ab.selection_changed is True
    assert ab.policy == "EXPLICIT_SHADOW_L2_PRIORITY_1_VS_NATIVE_0"
    assert ab.actual_l1_policy_changed is False
    assert ab.useful_for_goal is False
    assert ab.authority == "ATT_SHADOW_AB_NO_ACTION_MEMORY_LEARNING"
    with pytest.raises(FrozenInstanceError):
        ab.selection_changed = False


def test_att_ab_empty_native_baseline_does_not_count_as_real_selection_change():
    read, native = _same_source_attention_ab(count=0)
    ab = compare_wb_l1_attention_ab(read, native_l1=native)
    assert ab.state == "NO_NATIVE_BASELINE"
    assert ab.baseline_selected == ()
    assert ab.with_l2_selected == ("wb-l2-uncertainty",)
    assert ab.observed_candidate_count == 0
    assert ab.selection_changed is False
    assert ab.actual_l1_policy_changed is False


@pytest.mark.parametrize("malformed", [
    "expired", "no_admission", "foreign", "other_tier",
    "mismatched_cue_source", "duplicate_observed_entity",
])
def test_att_ab_rejects_stale_unqualified_or_forged_native_baselines(malformed):
    read, native = _same_source_attention_ab(count=2)
    if malformed == "expired":
        read = project_wb_l2_uncertainty(
            accepted_text='{"uncertainty":"Check source"}', session_id="s",
            source_world_seq=9, latest_world_seq=12, source_ref="present:s:9:p9",
            expected_source_ref="present:s:9:p9", owner_admitted=True,
        )
    elif malformed == "no_admission":
        read = project_wb_l2_uncertainty(
            accepted_text='{"uncertainty":"Check source"}', session_id="s",
            source_world_seq=9, latest_world_seq=9, source_ref="present:s:9:p9",
            expected_source_ref="present:s:9:p9", owner_admitted=False,
        )
    elif malformed == "foreign":
        native = replace(native, session_id="foreign")
    elif malformed == "other_tier":
        native = replace(native, tier=CognitionTier.L2)
    elif malformed == "mismatched_cue_source":
        cue = native.visible_world[0]
        native = replace(native, visible_world=(
            replace(cue, source_ref="present:foreign:9:p9"),
            *native.visible_world[1:],
        ))
    elif malformed == "duplicate_observed_entity":
        native = replace(native, visible_world=(
            native.visible_world[0], native.visible_world[0],
        ))
    result = compare_wb_l1_attention_ab(read, native_l1=native)
    assert result.state == "UNAVAILABLE"
    assert result.selection_changed is False
    assert result.actual_l1_policy_changed is False
