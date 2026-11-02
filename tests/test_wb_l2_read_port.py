"""WB L2 uncertainty current/past read ports; zero World/model/Action I/O."""
from dataclasses import FrozenInstanceError

import pytest

from relay_self.wb_l2_read_port import project_wb_l2_uncertainty


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
