"""Small DEV P1->S49 motor envelope is not permission for new Actions."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.execution import MineflayerCommand
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import compose_third_move_native_dev
from adapters.mineflayer.s49_p1_motor_envelope_dev import (
    apply_issued_p1_motor_envelope_dev,
)
from adapters.mineflayer.s49_p1_physical_pair_dev import (
    BASELINE,
    STRESS,
    evaluate_sixth_motor_sensitivity_dev,
)
from adapters.mineflayer.s49_p1_same_native_gait_dev import compare_fifth_p1_gait_dev
from test_s49_p1_fifth_epoch_dev import inputs
from test_self_live_think import native_probe


def evidence(monkeypatch, scenario):
    action, prior, third, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, third, previous_wait_native_seq=prior.seq,
    )
    gait = compare_fifth_p1_gait_dev(model, fifth)
    sensitivity = evaluate_sixth_motor_sensitivity_dev(model, gait, scenario)
    sid = fifth.session_id
    event_seq = fifth.seq + 5
    sixth = replace(
        native_probe(fifth.seq + 8, 2.0, sid=sid),
        request_id=f"s49-actual:{sid}:event-{event_seq}",
    )
    cmd = MineflayerCommand(
        action_id=f"s49-native-move-{event_seq}",
        binding_id="s14-normal-binding",
        action_ref="MOVE_BACKWARD", effect="set_control",
        control="back", state=True, duration_s=0.20,
        cleanup_action_id=f"s49-native-move-{event_seq}-s15-clear",
    )
    return cmd, sixth, sensitivity, action["action"], fifth.seq


@pytest.mark.parametrize("scenario,expected", [
    (BASELINE, 0.19648932318884205),
    (STRESS, 0.06),
])
def test_model_input_is_applied_only_to_matching_original_issued_action(
    monkeypatch, scenario, expected,
):
    command, sixth, sensitivity, third_id, fifth_seq = evidence(
        monkeypatch, scenario,
    )
    updated, env = apply_issued_p1_motor_envelope_dev(
        command, sixth, sensitivity,
        expected_third_action_id=third_id, expected_fifth_seq=fifth_seq,
    )
    assert updated.action_id == command.action_id
    assert updated.binding_id == command.binding_id
    assert updated.action_ref == "MOVE_BACKWARD"
    assert updated.cleanup_action_id == command.cleanup_action_id
    assert updated.duration_s == pytest.approx(expected)
    assert updated.duration_s == sensitivity["duration_s"]
    assert command.duration_s == 0.2
    assert env.candidate_duration_s == updated.duration_s
    assert env.session_id == sixth.session_id
    assert env.sixth_probe_seq == sixth.seq
    assert env.fifth_model_probe_seq == fifth_seq
    assert env.third_source_action_id == third_id
    assert env.native_fatigue_measured is False


@pytest.mark.parametrize("fault", [
    "other_action_id", "other_probe_session", "stale_probe",
    "wrong_probe_kind", "wrong_request", "missing_fifth",
    "other_third_action", "claim_action_permission", "claim_native_sensor",
    "extra_issuer", "extra_reader", "pretend_qualification",
    "pretend_source_bound_tick", "nonfinite_duration", "overlong_duration",
    "wrong_original_duration", "invalid_profile_sha",
])
def test_forged_or_stale_model_envelopes_fail_closed(monkeypatch, fault):
    command, sixth, model, third_id, fifth_seq = evidence(monkeypatch, STRESS)
    if fault == "other_action_id":
        command = replace(command, action_id="fake-issued")
    elif fault == "other_probe_session":
        sixth = replace(sixth, session_id="foreign")
    elif fault == "stale_probe":
        sixth = replace(sixth, seq=fifth_seq)
    elif fault == "wrong_probe_kind":
        sixth = replace(sixth, kind="entities", request_id=None)
    elif fault == "wrong_request":
        sixth = replace(sixth, request_id="wrong")
    elif fault == "missing_fifth":
        fifth_seq = sixth.seq
    elif fault == "other_third_action":
        third_id = "foreign-original-action"
    elif fault == "claim_action_permission":
        model = {**model, "action_permission": True}
    elif fault == "claim_native_sensor":
        model = {**model, "native_fatigue_measured": True}
    elif fault == "extra_issuer":
        model = {**model, "additional_issuers": 1}
    elif fault == "extra_reader":
        model = {**model, "additional_native_receivers": 1}
    elif fault == "pretend_qualification":
        model = {**model, "qualification_go": True}
    elif fault == "pretend_source_bound_tick":
        model = {**model, "source_bound_tick": 3}
    elif fault == "nonfinite_duration":
        model = {**model, "duration_s": float("nan")}
    elif fault == "overlong_duration":
        model = {**model, "duration_s": 0.22}
    elif fault == "wrong_original_duration":
        command = replace(command, duration_s=0.3)
    elif fault == "invalid_profile_sha":
        model = {**model, "hypothetical_profile_sha256": "forged"}
    with pytest.raises(BoundaryRejected):
        apply_issued_p1_motor_envelope_dev(
            command, sixth, model,
            expected_third_action_id=third_id,
            expected_fifth_seq=fifth_seq,
        )
