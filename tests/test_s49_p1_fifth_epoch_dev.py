"""Fifth original native L0 DEV views: typed negatives and no action authority."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import (
    compose_third_move_native_dev,
    project_fifth_l0_view_dev,
)
from relay_self.self_body import BodyOrigin
from test_s49_p1_self_body_dev import correlated_next_native
from test_self_live_think import native_probe


def inputs(monkeypatch):
    _, _, action, prior, _ = correlated_next_native(monkeypatch)
    sid = prior.session_id
    move = replace(
        native_probe(prior.seq + 8, 2.0, sid=sid),
        request_id=f"s49-third-move:{sid}:{action['action']}",
    )
    fifth = replace(
        native_probe(move.seq + 8, 10.0, sid=sid),
        request_id=f"s49-actual:{sid}:event-{move.seq + 6}",
    )
    return action, prior, move, fifth


def test_third_original_native_move_debits_model_and_projects_fifth_epoch(monkeypatch):
    action, prior, move, fifth = inputs(monkeypatch)
    model, third = compose_third_move_native_dev(
        action, move, previous_wait_native_seq=prior.seq,
    )
    projected = project_fifth_l0_view_dev(model, fifth)
    assert third["status"] == "DEV_THIRD_ORIGINAL_MOVE_P1_MODEL_SELF_VIEWS"
    assert third["movement_m"] == action["movement_m"]
    assert third["p1_model_fatigue_before"] == 0
    assert third["p1_model_fatigue_after"] > 0
    assert third["p1_model_fatigue_accumulated"] > 0
    assert third["model_step_only"] == 1
    assert third["observed_move_world_tick"] is None
    assert third["selfworld_body_same_object"] is True
    assert third["p1_native_fatigue"] is None
    assert projected["status"] == "DEV_FIFTH_NATIVE_SELF_WORLD_BODY_PROJECTED_PRE_L0"
    assert projected["native_seq"] == fifth.seq
    assert projected["third_post_move_native_seq"] == move.seq
    assert projected["p1_model_fatigue"] == model.model_fatigue
    assert projected["p1_model_sensor_pct"] == third["p1_model_sensor_pct"]
    assert projected["p1_model_capability_pct"] == third["p1_model_capability_pct"]
    assert projected["p1_native_fatigue"] is None
    assert projected["original_l0_policy_consumes_p1"] is False
    assert projected["projection_before_original_l0_decide"] is True
    assert model.body.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert model.body.hypothetical(
        "p1-dev-distance-wait", "p1_phase",
    ).value == "after-third-move"


@pytest.mark.parametrize("bad", [
    "wrong_action", "wrong_distance", "stale_third", "foreign_third",
    "wrong_request", "wrong_kind", "stale_fifth", "foreign_fifth",
    "wrong_fifth_request", "altered_provenance", "foreign_receipt",
])
def test_bad_native_p1_source_never_projects_fifth_epoch(monkeypatch, bad):
    action, prior, move, fifth = inputs(monkeypatch)
    if bad == "wrong_action":
        action = dict(action, action="fake-new-action")
    elif bad == "wrong_distance":
        action = dict(action, movement_m=999.0)
    elif bad == "stale_third":
        move = replace(move, seq=prior.seq)
    elif bad == "foreign_third":
        move = replace(move, session_id="foreign")
    elif bad == "wrong_request":
        move = replace(move, request_id="other-request")
    elif bad == "wrong_kind":
        move = replace(move, kind="entities")
    elif bad == "foreign_receipt":
        action = dict(action, source="other-session")
    else:
        model, _ = compose_third_move_native_dev(
            action, move, previous_wait_native_seq=prior.seq,
        )
        if bad == "stale_fifth":
            fifth = replace(fifth, seq=move.seq)
        elif bad == "foreign_fifth":
            fifth = replace(fifth, session_id="foreign")
        elif bad == "wrong_fifth_request":
            fifth = replace(fifth, request_id="other-request")
        elif bad == "altered_provenance":
            fifth = replace(fifth, provenance=move.provenance)
        with pytest.raises(BoundaryRejected):
            project_fifth_l0_view_dev(model, fifth)
        return
    with pytest.raises(BoundaryRejected):
        compose_third_move_native_dev(
            action, move, previous_wait_native_seq=prior.seq,
        )


def test_fifth_dev_flag_is_default_off_and_rejected_without_fourth_move(tmp_path):
    from adapters.mineflayer.s49_paper_world_first_dev import run, CONFIRM
    import asyncio
    import hashlib

    paper = tmp_path / "paper.jar"
    observer = tmp_path / "observer.jar"
    paper.write_bytes(b"fixture-paper")
    observer.write_bytes(b"fixture-observer")
    output = tmp_path / "output"
    rc = asyncio.run(run(
        output, paper, hashlib.sha256(paper.read_bytes()).hexdigest(),
        observer, hashlib.sha256(observer.read_bytes()).hexdigest(),
        confirmation=CONFIRM, actual_next_epoch=False, actual_fifth_epoch=True,
        fresh_target_distance=2,
    ))
    assert rc == 2
    assert not output.exists()
