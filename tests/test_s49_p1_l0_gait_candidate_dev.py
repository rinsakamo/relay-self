"""Actual fresh post-WAIT event/probe, two DEV P1 gait candidates, zero Action."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_gait_candidate_dev import (
    evaluate_fatigue_aware_fresh_candidate_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import compose_s49_p1_dev_self_body
from experiments.fatigue_p1 import FatigueProfile
from test_s49_paper_world_first_dev import PLAYER, sources
from test_self_live_think import native_probe


def source(monkeypatch, *, distance=2.0):
    original, paper = sources(monkeypatch)
    handoff, _ = compose_s49_p1_dev_self_body(
        original, paper, expected_player_uuid=PLAYER,
        profile=FatigueProfile(enabled=True, initial=0.0),
    )
    sid = handoff.session_id
    last_seq = original["actual_native_actions"][-1][
        "execution_evidence"]["after_observation"]["seq"]
    prior_seq = last_seq + 5
    prior = replace(
        native_probe(prior_seq, distance, sid=sid),
        request_id=f"s49-postwait:{sid}:{handoff.action_id}",
    )
    event_seq = prior_seq + 3
    event = replace(
        native_probe(event_seq, distance, sid=sid),
        kind="entities", request_id=None,
    )
    next_probe = native_probe(event_seq + 2, distance, sid=sid)
    next_probe = replace(
        next_probe,
        snapshot=replace(
            next_probe.snapshot,
            nearby_entities=event.snapshot.nearby_entities,
            nearby_entities_coverage=event.snapshot.nearby_entities_coverage,
        ),
        request_id=f"s49-postwait-event:{sid}:{event.seq}",
    )
    retained = s19._epoch_one()[1].new_state
    return original, paper, prior, event, next_probe, retained


def evaluate(args):
    original, paper, prior, event, next_probe, retained = args
    return evaluate_fatigue_aware_fresh_candidate_dev(
        original, paper, prior, event, next_probe,
        expected_player_uuid=PLAYER, retained=retained,
    )


def test_fresh_native_zombie_same_source_baseline_vs_stress_gait(monkeypatch):
    original, paper, prior, event, probe, retained = source(monkeypatch)
    actions = tuple(original["actual_native_actions"])
    result = evaluate((original, paper, prior, event, probe, retained))
    assert result["status"] == (
        "DEV_FRESH_WORLD_P1_CAPABILITY_CONDITIONED_L0_CANDIDATE"
    )
    assert result["fresh_event_seq"] == event.seq
    assert result["fresh_probe_seq"] == probe.seq
    assert result["fresh_probe_request_id"] == probe.request_id
    assert result["fresh_s42_selection_unchanged"] == "MOVE_AWAY"
    assert result["nominal_one_tick_demand_blocks"] == pytest.approx(1)
    assert result["baseline_after_wait_model_fatigue"] == pytest.approx(0)
    assert result["stress_after_wait_model_fatigue"] == pytest.approx(0.2)
    assert result["baseline_one_tick_capacity_blocks"] == pytest.approx(1)
    assert result["stress_one_tick_capacity_blocks"] == pytest.approx(0.86)
    assert result["baseline_cognition_candidate"] == "MOVE_AWAY_NOMINAL_MODEL_CANDIDATE"
    assert result["stress_cognition_candidate"] == (
        "MOVE_AWAY_LIMIT_TO_MODEL_CAPACITY_CANDIDATE"
    )
    assert result["gait_candidate_changed_by_p1_scenario"] is True
    assert result["s42_intent_modified"] is False
    assert result["actual_l0_decide_called"] is False
    assert result["new_action_grant_issued"] is False
    assert result["new_action_issued"] is False
    assert result["additional_native_receivers"] == 0
    assert result["additional_native_probes"] == 0
    assert result["p1_physically_attested"] is False
    assert result["production_p1_mutated"] is False
    assert not result["qualification_go"] and not result["science_go"]
    assert original["actual_native_actions"] == list(actions)


def test_far_fresh_native_zombie_waits_for_both_profiles(monkeypatch):
    result = evaluate(source(monkeypatch, distance=10.0))
    assert result["fresh_s42_selection_unchanged"] == "WAIT"
    assert result["baseline_cognition_candidate"] == "WAIT_NO_ACTION_CANDIDATE"
    assert result["stress_cognition_candidate"] == "WAIT_NO_ACTION_CANDIDATE"
    assert result["gait_candidate_changed_by_p1_scenario"] is False
    assert result["new_action_issued"] is False


@pytest.mark.parametrize("bad", (
    "foreign_session", "replayed_event", "replayed_probe",
    "wrong_probe_id", "wrong_entity", "wrong_original_distance",
    "altered_paper", "foreign_retained",
))
def test_fresh_l0_gait_candidate_fails_closed(monkeypatch, bad):
    original, paper, prior, event, probe, retained = source(monkeypatch)
    if bad == "foreign_session":
        event = replace(event, session_id="foreign")
    elif bad == "replayed_event":
        event = replace(event, seq=prior.seq)
    elif bad == "replayed_probe":
        probe = replace(probe, seq=event.seq)
    elif bad == "wrong_probe_id":
        probe = replace(probe, request_id="forged")
    elif bad == "wrong_entity":
        different = replace(probe.snapshot.nearby_entities[0], entity_id=99999)
        probe = replace(
            probe, snapshot=replace(probe.snapshot, nearby_entities=(different,)),
        )
    elif bad == "wrong_original_distance":
        original["actual_native_actions"][-1]["movement_m"] += 0.5
    elif bad == "altered_paper":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    else:
        retained = s19._epoch_one()[1].previous_state
    with pytest.raises(BoundaryRejected):
        evaluate((original, paper, prior, event, probe, retained))
