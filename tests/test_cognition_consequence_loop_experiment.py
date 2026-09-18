from experiments.cognition_consequence_loop import (
    run_controller_failure_case,
    run_expected_consequence_case,
    run_non_convergence_case,
    run_reference_fixture,
    run_stale_present_mismatch_case,
    run_unknown_consequence_case,
    run_world_changed_case,
)


def test_non_convergence_does_not_start_execution_path() -> None:
    result = run_non_convergence_case()

    assert result["decision"] == "escalate"
    assert result["skill_started"] is False
    assert result["action_created"] is False
    assert result["training_label_created"] is False


def test_expected_consequence_can_close_action_and_skill_normally() -> None:
    result = run_expected_consequence_case()

    assert result["comparison"] == "match"
    assert result["action_state"] == "outcome"
    assert result["skill_state"] == "succeeded"
    assert result["intent_id"] == "intent-expected-consequence"
    assert result["training_label_created"] is False


def test_stale_present_mismatch_reopens_present_and_recovers_locally() -> None:
    result = run_stale_present_mismatch_case()

    assert result["comparison"] == "mismatch"
    assert result["decision_input_source"] == "fixture.estimate"
    assert result["consequence_source"] == "fixture.world"
    assert result["old_present_current"] is False
    assert result["reopened_present_revision"] == 2
    assert result["action_state"] == "outcome"
    assert result["skill_state"] == "failed"
    assert result["reconsideration_admission"] == "local_recovery"
    assert result["reconsideration_request_created"] is False
    assert result["intent_id"] == "intent-stale-present-mismatch"


def test_unknown_consequence_does_not_invent_success_or_failure() -> None:
    result = run_unknown_consequence_case()

    assert result["comparison"] == "unknown"
    assert result["action_state"] == "unknown"
    assert result["skill_state"] == "started"
    assert result["intent_id"] == "intent-unknown-consequence"
    assert result["training_label_created"] is False


def test_changed_world_is_distinct_from_bad_predecision_estimate() -> None:
    result = run_world_changed_case()

    assert result["comparison"] == "mismatch"
    assert result["decision_input_source"] == "fixture.world"
    assert "external-change" in result["world_change_reference"]
    assert result["old_present_current"] is False
    assert result["action_state"] == "outcome"
    assert result["skill_state"] == "failed"
    assert result["reconsideration_admission"] == "local_recovery"
    assert result["reconsideration_request_created"] is False
    assert result["intent_id"] == "intent-world-changed"


def test_controller_failure_does_not_rewrite_world_route_truth() -> None:
    result = run_controller_failure_case()

    assert result["comparison"] == "mismatch"
    assert result["route_remains_open"] is True
    assert result["route_provenance_source"] == "fixture.world"
    assert result["failure_provenance_source"] == "fixture.controller"
    assert result["action_state"] == "outcome"
    assert result["skill_state"] == "failed"
    assert result["reconsideration_request_created"] is False
    assert result["intent_id"] == "intent-controller-failure"


def test_reference_fixture_creates_no_automatic_training_labels() -> None:
    result = run_reference_fixture()

    assert result["case_count"] == 6
    assert result["automatic_training_labels"] == 0
