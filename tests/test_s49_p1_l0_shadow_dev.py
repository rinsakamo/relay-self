"""No-issuer L0 shadow evaluation from original S49+Paper post-WAIT probe."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_shadow_dev import preview_postwait_l0_dev
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from test_s49_p1_self_body_dev import correlated_next_native


def source(monkeypatch):
    handoff, reviewed, last, native, request = correlated_next_native(monkeypatch)
    body, _ = compose_s49_p1_postwait_native_dev(
        handoff, reviewed, last, native, expected_request_id=request,
    )
    _, committed, _, _, _, _ = s19._epoch_one()
    return body, native, handoff, reviewed, committed.new_state


def evaluate(body, native, handoff, reviewed, retained):
    return preview_postwait_l0_dev(
        body, native, handoff, reviewed,
        FatigueProfile(enabled=True, initial=0.0), retained,
    )


def test_native_postwait_shadow_s42_remains_original_without_action(monkeypatch):
    body, native, handoff, reviewed, retained = source(monkeypatch)
    out = evaluate(body, native, handoff, reviewed, retained)
    assert out["status"] == "DEV_S42_ORIGINAL_POLICY_SHADOW_COMPARISON"
    assert out["session_id"] == native.session_id
    assert out["native_seq"] == native.seq
    assert out["native_request_id"] == native.request_id
    assert out["body_epoch_id"] == body.epoch_id
    assert out["original_frozen_retained_revision"] == 1
    assert out["original_frozen_retained_value"] == 4
    assert out["original_s42_selection"] == "MOVE_AWAY"
    assert out["s42_distance_m"] == pytest.approx(2.0)
    assert out["s42_wait_score"] == 8
    assert out["s42_move_score"] == 7
    assert out["after_move_p1_model_efficiency_pct"] < 100
    assert out["after_wait_p1_model_efficiency_pct"] == 100
    assert out["after_move_p1_model_max_blocks_per_tick"] < (
        out["after_wait_p1_model_max_blocks_per_tick"]
    )
    assert out["s42_has_p1_input"] is False
    assert out["p1_changed_original_s42_selection"] is False
    assert out["original_l0_entities_event_consumed"] is False
    assert out["actual_reactive_l0_decide_called"] is False
    assert out["fresh_action_grant_issued"] is False
    assert out["extra_action_issuers"] == 0
    assert out["additional_native_probes"] == 0
    assert out["independent_fatigue_attested"] is False
    assert not out["qualification_go"]
    assert not out["science_go"]


@pytest.mark.parametrize("bad", (
    "wrong_session", "wrong_request", "wrong_seq", "old_body",
    "source_sha", "mode", "retained", "foreign_p1", "missing_target",
))
def test_shadow_rejects_crosssource_or_modified_world(monkeypatch, bad):
    body, native, handoff, reviewed, retained = source(monkeypatch)
    if bad == "wrong_session":
        native = replace(native, session_id="foreign")
    elif bad == "wrong_request":
        native = replace(native, request_id="wrong")
    elif bad == "wrong_seq":
        native = replace(native, seq=native.seq + 10)
    elif bad == "old_body":
        body = replace(body, hypotheses=())
    elif bad == "source_sha":
        reviewed["paper_window_sha256"] = "other"
    elif bad == "mode":
        reviewed["dev_fatigue_mode"] = "SEED"
    elif bad == "retained":
        retained = s19._epoch_one()[1].previous_state
    elif bad == "foreign_p1":
        body = replace(body, session_id="foreign")
    else:
        native = replace(native, snapshot=replace(
            native.snapshot, nearby_entities=(),
            nearby_entities_coverage=replace(
                native.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ))
    with pytest.raises(BoundaryRejected):
        evaluate(body, native, handoff, reviewed, retained)
