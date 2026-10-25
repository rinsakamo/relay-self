"""DEV motor budget is never Action authority and can change duration only."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.execution import MineflayerCommand
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import compose_third_move_native_dev
from adapters.mineflayer.s49_p1_motor_budget_dev import propose_issued_motor_budget_dev
from adapters.mineflayer.s49_p1_physical_pair_dev import (
    BASELINE,
    STRESS,
    evaluate_sixth_motor_sensitivity_dev,
)
from adapters.mineflayer.s49_p1_same_native_gait_dev import compare_fifth_p1_gait_dev
from test_s49_p1_fifth_epoch_dev import inputs


def _cases(monkeypatch):
    action, prior, third, fifth = inputs(monkeypatch)
    model, _ = compose_third_move_native_dev(
        action, third, previous_wait_native_seq=prior.seq,
    )
    gait = compare_fifth_p1_gait_dev(model, fifth)
    cases = {}
    for scenario in (BASELINE, STRESS):
        s = evaluate_sixth_motor_sensitivity_dev(model, gait, scenario)
        p = propose_issued_motor_budget_dev(
            s,
            session_id=third.session_id,
            sixth_native_seq=fifth.seq + 10,
            issued_action_id="s49-native-move-903",
        )
        cases[scenario] = s, p
    return cases


@pytest.mark.parametrize("scenario", [BASELINE, STRESS])
def test_p1_motor_budget_is_pure_issued_action_duration_only(monkeypatch, scenario):
    s, p = _cases(monkeypatch)[scenario]
    command = MineflayerCommand(
        action_id="s49-native-move-903", binding_id="binding-903",
        action_ref="MOVE_BACKWARD", effect="set_control", control="back",
        state=True, duration_s=0.2, cleanup_action_id="cleanup-903",
    )
    updated = p.apply_to_issued(command)
    assert updated is not command
    assert updated == replace(command, duration_s=s["duration_s"])
    assert updated.action_id == command.action_id
    assert updated.binding_id == command.binding_id
    assert updated.cleanup_action_id == command.cleanup_action_id
    assert command.duration_s == 0.2
    assert p.session_id
    assert p.fifth_native_seq < p.sixth_native_seq
    assert p.nominal_duration_s == 0.2


@pytest.mark.parametrize("mutation", [
    "permission", "receiver", "issuer", "true_fatigue", "invented_tick",
    "imputed_wait", "qualification", "science", "missing_source",
    "wrong_nominal", "wrong_duration", "not_finite", "wrong_profile",
    "wrong_status", "wrong_native_order",
])
def test_model_fails_closed_before_original_transport(monkeypatch, mutation):
    s, _ = _cases(monkeypatch)[STRESS]
    s = dict(s)
    seq = s["fifth_native_seq"] + 10
    overrides = {
        "permission": ("action_permission", True),
        "receiver": ("additional_native_receivers", 1),
        "issuer": ("additional_issuers", 1),
        "true_fatigue": ("native_fatigue_measured", True),
        "invented_tick": ("source_bound_tick", 5),
        "imputed_wait": ("zero_wait_ticks_imputed", False),
        "qualification": ("qualification_go", True),
        "science": ("science_go", True),
        "missing_source": ("same_original_native_third_move_source", False),
        "wrong_nominal": ("original_nominal_duration_s", 1.0),
        "wrong_duration": ("duration_s", 0.3),
        "not_finite": ("duration_s", float("nan")),
        "wrong_profile": ("hypothetical_profile_sha256", "invalid"),
        "wrong_status": ("status", "R_QUALIFIED"),
    }
    if mutation == "wrong_native_order":
        seq = s["fifth_native_seq"]
    else:
        field, value = overrides[mutation]
        s[field] = value
    with pytest.raises(BoundaryRejected):
        propose_issued_motor_budget_dev(
            s, session_id="same-native-session",
            sixth_native_seq=seq, issued_action_id="s49-native-move-903",
        )


def test_budget_rejects_unissued_or_pre_modified_action(monkeypatch):
    _, p = _cases(monkeypatch)[BASELINE]
    original = MineflayerCommand(
        action_id="s49-native-move-903", binding_id="binding-903",
        action_ref="MOVE_BACKWARD", effect="set_control", control="back",
        state=True, duration_s=0.2, cleanup_action_id="cleanup-903",
    )
    for altered in (
        replace(original, action_id="another"),
        replace(original, duration_s=0.13),
    ):
        with pytest.raises(BoundaryRejected):
            p.apply_to_issued(altered)
