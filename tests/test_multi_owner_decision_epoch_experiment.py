from experiments.multi_owner_decision_epoch import run_multi_owner_trace


def test_multi_owner_trace_only_requests_cognition_for_local_uncertainty() -> None:
    result = run_multi_owner_trace()

    assert [row["event"] for row in result["trace"]] == [
        "irrelevant_observation",
        "material_route_observation",
        "action_supervision_deadline",
        "skill_local_control_step",
        "consequence_mismatch",
        "skill_local_uncertainty",
        "quiet_interval",
    ]
    assert [row["disposition"] for row in result["trace"]] == [
        "ignore",
        "decision_epoch_no_model",
        "decision_epoch_no_model",
        "decision_epoch_no_model",
        "decision_epoch_no_model",
        "decision_epoch_with_relayengine",
        "ignore",
    ]
    assert result["relayengine_request_count"] == 1


def test_material_observation_reprojects_present_without_replacing_intent() -> None:
    result = run_multi_owner_trace()
    material = result["trace"][1]

    assert result["old_present_is_current_after_material_update"] is False
    assert material["effects"] == ("present_reprojected",)
    assert material["present_revision"] == 2
    assert material["intent_id"] == "intent-safe-106"
    assert material["pending_reconsideration"] is False


def test_action_deadline_services_supervisor_without_reselecting_skill() -> None:
    result = run_multi_owner_trace()
    deadline = result["trace"][2]
    control = result["trace"][3]

    assert result["timed_out_action_ids"] == ["action-flee-106"]
    assert result["next_action_deadline_ns"] is None
    assert deadline["action_state"] == "timeout"
    assert deadline["skill_state"] == "started"
    assert deadline["intent_id"] == "intent-safe-106"
    assert control["skill_state"] == "started"
    assert control["intent_id"] == "intent-safe-106"


def test_mismatch_reopens_present_and_recovers_locally_before_reconsideration() -> None:
    result = run_multi_owner_trace()
    mismatch = result["trace"][4]

    assert result["mismatch_admission"] == "local_recovery"
    assert mismatch["effects"] == (
        "present_reopened",
        "local_recovery",
        "intent_unchanged",
    )
    assert mismatch["pending_reconsideration"] is False
    assert mismatch["intent_id"] == "intent-safe-106"


def test_quiet_interval_produces_no_artificial_owner_activity() -> None:
    result = run_multi_owner_trace()
    quiet = result["trace"][-1]

    assert quiet["disposition"] == "ignore"
    assert quiet["effects"] == ()
    assert result["final_intent_id"] == "intent-safe-106"
    assert result["final_skill_state"] == "started"
    assert result["final_action_state"] == "timeout"
