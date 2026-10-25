"""Typed DEV S49 P1 motor interface: no authority, only bounded issued duration."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.execution import MineflayerCommand
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import compose_third_move_native_dev
from adapters.mineflayer.s49_p1_motor_envelope_dev import (
    DevMotorEnvelope,
    apply_motor_envelope_dev,
    bind_motor_envelope_dev,
)
from adapters.mineflayer.s49_p1_physical_pair_dev import (
    BASELINE,
    STRESS,
    evaluate_sixth_motor_sensitivity_dev,
)
from adapters.mineflayer.s49_p1_same_native_gait_dev import compare_fifth_p1_gait_dev
from test_s49_p1_fifth_epoch_dev import inputs
from test_self_live_think import native_probe


def source(monkeypatch, scenario=STRESS):
    action, prior, third, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, third, previous_wait_native_seq=prior.seq,
    )
    gait = compare_fifth_p1_gait_dev(model, fifth)
    sensitivity = evaluate_sixth_motor_sensitivity_dev(model, gait, scenario)
    sixth = replace(
        native_probe(fifth.seq + 5, 2, sid=fifth.session_id),
        request_id=f"s49-actual:{fifth.session_id}:event-{fifth.seq + 4}",
    )
    cmd = MineflayerCommand(
        action_id=f"s49-native-move-{fifth.seq + 4}",
        binding_id="original-s14-binding",
        action_ref="MOVE_BACKWARD",
        effect="set_control",
        control="back",
        state=True,
        duration_s=0.2,
        cleanup_action_id="different-s16-cleanup-action",
    )
    return cmd, sixth, gait, sensitivity


@pytest.mark.parametrize("scenario", [BASELINE, STRESS])
def test_model_envelope_typed_bounded_native_and_original_action_unchanged(
    monkeypatch, scenario,
):
    cmd, probe, gait, sensitivity = source(monkeypatch, scenario)
    envelope = bind_motor_envelope_dev(cmd, probe, gait, sensitivity)
    constrained = apply_motor_envelope_dev(envelope, cmd, probe)
    assert isinstance(envelope, DevMotorEnvelope)
    assert envelope.action_id == cmd.action_id
    assert envelope.probe_seq == probe.seq
    assert envelope.fifth_source_seq == gait["fifth_native_seq"]
    assert envelope.model_scenario == scenario
    assert 0.05 <= constrained.duration_s < cmd.duration_s == 0.2
    assert constrained.duration_s == sensitivity["duration_s"]
    assert constrained.action_id == cmd.action_id
    assert constrained.cleanup_action_id == cmd.cleanup_action_id
    assert constrained.binding_id == cmd.binding_id
    assert constrained.action_ref == cmd.action_ref
    assert constrained.control == cmd.control
    assert constrained.state is True
    assert cmd.duration_s == 0.2
    assert envelope.model_efficiency < 1


@pytest.mark.parametrize("fault", [
    "wrong_action", "wrong_cleanup_scenario", "foreign_probe",
    "stale_probe", "wrong_request", "foreign_kind", "wrong_duration",
    "wrong_sensitivity_action", "false_attestation", "new_issuer",
    "bad_model_duration", "bad_model_efficiency", "expired_fifth_source",
])
def test_unbound_candidate_cannot_modulate_original_command(monkeypatch, fault):
    cmd, probe, gait, sensitivity = source(monkeypatch)
    if fault == "wrong_action":
        cmd = replace(cmd, action_id="forged")
    elif fault == "wrong_cleanup_scenario":
        cmd = replace(cmd, action_ref="EAT")
    elif fault == "foreign_probe":
        probe = replace(probe, session_id="foreign")
    elif fault == "stale_probe":
        probe = replace(probe, seq=gait["fifth_native_seq"])
    elif fault == "wrong_request":
        probe = replace(probe, request_id="other")
    elif fault == "foreign_kind":
        probe = replace(probe, kind="entities", request_id=None)
    elif fault == "wrong_duration":
        cmd = replace(cmd, duration_s=0.4)
    elif fault == "wrong_sensitivity_action":
        sensitivity = {**sensitivity, "third_action_id": "fake"}
    elif fault == "false_attestation":
        sensitivity = {**sensitivity, "native_fatigue_measured": True}
    elif fault == "new_issuer":
        sensitivity = {**sensitivity, "additional_issuers": 1}
    elif fault == "bad_model_duration":
        sensitivity = {**sensitivity, "duration_s": 0.21}
    elif fault == "bad_model_efficiency":
        sensitivity = {**sensitivity, "hypothetical_efficiency": 1.5}
    elif fault == "expired_fifth_source":
        sensitivity = {**sensitivity, "fifth_native_seq": probe.seq + 1}
        gait = {**gait, "fifth_native_seq": probe.seq + 1}
    with pytest.raises((BoundaryRejected, ValueError)):
        bind_motor_envelope_dev(cmd, probe, gait, sensitivity)


def test_expired_or_foreign_probe_rejected_at_application(monkeypatch):
    cmd, probe, gait, sensitivity = source(monkeypatch)
    envelope = bind_motor_envelope_dev(cmd, probe, gait, sensitivity)
    for corrupted in (
        replace(probe, seq=probe.seq + 1),
        replace(probe, session_id="foreign"),
        replace(probe, request_id="other"),
    ):
        with pytest.raises(BoundaryRejected):
            apply_motor_envelope_dev(envelope, cmd, corrupted)
    with pytest.raises(BoundaryRejected):
        apply_motor_envelope_dev(envelope, replace(cmd, action_id="other"), probe)
