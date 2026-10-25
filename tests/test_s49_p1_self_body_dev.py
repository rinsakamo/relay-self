"""S49 actual MOVE/Paper WAIT -> fallible SelfBody model, not native sensor."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_self_body_dev import (
    MODEL,
    SOURCE_SCOPE,
    compose_s49_p1_dev_self_body,
)
from experiments.fatigue_p1 import FatigueProfile
from relay_self.self_body import BodyOrigin, SelfBodyView
from test_s49_paper_world_first_dev import PLAYER, sources


def projected(monkeypatch):
    original, paper = sources(monkeypatch)
    return compose_s49_p1_dev_self_body(
        original, paper, expected_player_uuid=PLAYER,
        profile=FatigueProfile(enabled=True, initial=0.0),
    )


def test_original_native_move_wait_to_two_read_only_selfbody_epochs(monkeypatch):
    handoff, p1 = projected(monkeypatch)
    move = handoff.after_move
    wait = handoff.after_wait
    assert isinstance(move, SelfBodyView) and isinstance(wait, SelfBodyView)
    assert move.session_id == wait.session_id == p1["session_id"]
    assert move.epoch_id != wait.epoch_id
    assert move.observation is wait.observation is None
    assert handoff.source_scope == SOURCE_SCOPE
    assert p1["dev_move"]["movement_m"] > 0
    assert p1["dev_fatigue_before"] > p1["dev_fatigue_after"]
    assert move.hypothetical(MODEL, "p1_phase").value == "after-move"
    assert wait.hypothetical(MODEL, "p1_phase").value == "after-wait"
    assert move.hypothetical(MODEL, "p1_sensor_pct").origin is BodyOrigin.HYPOTHESIS
    assert 0 < move.hypothetical(MODEL, "p1_sensor_pct").value <= 100
    assert wait.hypothetical(MODEL, "p1_sensor_pct").value == 0
    assert (
        move.hypothetical(MODEL, "p1_capability_pct").value
        <= wait.hypothetical(MODEL, "p1_capability_pct").value
    )
    assert move.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert wait.sensed("p1_fatigue_sensor").value is None
    assert wait.observed("p1_fatigue").value is None
    assert wait.observed("m0_energy").value is None
    assert wait.hypothetical(MODEL, "p1_source_scope").value == SOURCE_SCOPE
    assert handoff.observed_wait_samples == 8
    snapshot = handoff.next_cognition_readback()
    assert snapshot["p1_sensor_pct_after_move"] > snapshot["p1_sensor_pct_after_wait"]
    assert snapshot["paper_wait_sample_count"] == 8
    assert snapshot["body_model_origin"] == "hypothesis"
    assert snapshot["native_postwait_observation"] is None
    assert snapshot["native_postwait_sensor_handoff"] is None
    assert snapshot["additional_action_issuers"] == 0
    assert snapshot["additional_native_receivers"] == 0
    assert snapshot["actual_next_l0_decision_consumed"] is False
    assert snapshot["qualification_go"] is False
    assert snapshot["science_go"] is False
    with pytest.raises(FrozenInstanceError):
        wait.epoch_id = "forged-after-wait"


@pytest.mark.parametrize("mutation", [
    "foreign_session", "missing_tick", "wrong_move", "clear_failed",
    "observer_abort", "old_seed", "inactive_p1",
])
def test_unvalidated_source_never_updates_selfbody(monkeypatch, mutation):
    native, paper = sources(monkeypatch)
    p = FatigueProfile(enabled=True, initial=0.0)
    if mutation == "foreign_session":
        native["session_id"] = "new-session-not-original"
    elif mutation == "missing_tick":
        paper = "".join(
            line for line in paper.splitlines(keepends=True)
            if "index=5 " not in line
        )
    elif mutation == "wrong_move":
        native["actual_native_actions"][-1]["movement_m"] = 5.0
    elif mutation == "clear_failed":
        native["actual_native_actions"][-1]["execution_evidence"][
            "cleanup_receipt"]["result"] = "rejected"
    elif mutation == "observer_abort":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    elif mutation == "old_seed":
        p = FatigueProfile(enabled=True, initial=0.5)
    elif mutation == "inactive_p1":
        p = FatigueProfile()
    with pytest.raises(BoundaryRejected):
        compose_s49_p1_dev_self_body(
            native, paper, expected_player_uuid=PLAYER, profile=p,
        )


def test_no_postwait_native_present_stays_unknown_and_no_action_authority(monkeypatch):
    handoff, _ = projected(monkeypatch)
    body = handoff.after_wait
    assert body.observation is None
    assert body.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert body.observed("health").origin is BodyOrigin.UNKNOWN
    assert not hasattr(handoff, "issue_action")
    assert not hasattr(body, "authorize_action")
    assert len(body.interoceptions) == 0
    assert len(body.hypotheses) == 1
    assert len(body.predictions) == 0
