"""S49 actual MOVE/Paper WAIT -> fallible SelfBody model, not native sensor."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_self_body_dev import (
    MODEL,
    SOURCE_SCOPE,
    compose_s49_p1_dev_self_body,
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueProfile
from relay_self.provenance import Provenance
from relay_self.self_body import BodyOrigin, SelfBodyView
from test_s49_paper_world_first_dev import PLAYER, sources
from test_self_live_think import native_probe


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


def correlated_next_native(monkeypatch):
    source, paper = sources(monkeypatch)
    handoff, reviewed = compose_s49_p1_dev_self_body(
        source, paper, expected_player_uuid=PLAYER,
        profile=FatigueProfile(enabled=True, initial=0.0),
    )
    last = source["actual_native_actions"][-1]
    prior_seq = last["execution_evidence"]["after_observation"]["seq"]
    seq = prior_seq + 5
    sid = reviewed["session_id"]
    req = f"s49-postwait:{sid}:{reviewed['action_id']}"
    native = native_probe(seq, 2.0, sid=sid)
    native = replace(
        native, request_id=req,
        provenance=Provenance("mineflayer", f"{sid}:{seq}"),
    )
    return handoff, reviewed, last, native, req


def test_true_postwait_native_probe_creates_next_readonly_cognition_epoch(monkeypatch):
    handoff, reviewed, last, probe, request = correlated_next_native(monkeypatch)
    body, readback = compose_s49_p1_postwait_native_dev(
        handoff, reviewed, last, probe, expected_request_id=request,
    )
    assert body.observation is not None
    assert body.session_id == reviewed["session_id"]
    assert body.observed("health").origin is BodyOrigin.OBSERVATION
    assert body.observed("health").value == probe.snapshot.health
    assert body.observed("position_x").origin is BodyOrigin.OBSERVATION
    assert body.hypothetical(MODEL, "p1_sensor_pct").origin is BodyOrigin.HYPOTHESIS
    assert body.hypothetical(MODEL, "p1_sensor_pct").value == 0
    assert body.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert body.observed("p1_fatigue").origin is BodyOrigin.UNKNOWN
    assert readback["native_request_id"] == request
    assert readback["native_seq"] == probe.seq
    assert readback["previous_action_after_probe_seq"] < probe.seq
    assert readback["native_source_ref"] == body.observation.source_ref
    assert readback["p1_native_sensor"] is None
    assert readback["p1_native_observation"] is None
    assert readback["extra_native_probes"] == 1
    assert readback["one_original_session_reader"] is True
    assert readback["real_next_l0_decision_consumed"] is False
    assert not readback["qualification_go"]
    assert not readback["science_go"]


@pytest.mark.parametrize("bad", [
    "foreign_session", "old_seq", "same_seq", "foreign_request",
    "foreign_origin", "foreign_action", "foreign_world",
    "profile_mode", "missing_consequence", "bad_expected_request",
])
def test_next_native_cognition_rejects_crosssource_or_stale_probe(monkeypatch, bad):
    handoff, reviewed, last, probe, req = correlated_next_native(monkeypatch)
    if bad == "foreign_session":
        probe = replace(probe, session_id="foreign")
    elif bad == "old_seq":
        probe = replace(probe, seq=0)
    elif bad == "same_seq":
        probe = replace(
            probe, seq=last["execution_evidence"]["after_observation"]["seq"],
        )
    elif bad == "foreign_request":
        probe = replace(probe, request_id="foreign")
    elif bad == "foreign_origin":
        probe = replace(probe, provenance=Provenance("untrusted", "other"))
    elif bad == "foreign_action":
        last["action"] = "foreign"
    elif bad == "foreign_world":
        reviewed["world"] = "foreign"
    elif bad == "profile_mode":
        reviewed["dev_fatigue_mode"] = "SEED"
    elif bad == "missing_consequence":
        last.pop("execution_evidence")
    else:
        req += ":forged"
    with pytest.raises(BoundaryRejected):
        compose_s49_p1_postwait_native_dev(
            handoff, reviewed, last, probe, expected_request_id=req,
        )


def test_native_present_reader_stays_separate_from_p1_hypothesis(monkeypatch):
    handoff, reviewed, last, probe, req = correlated_next_native(monkeypatch)
    body, snapshot = compose_s49_p1_postwait_native_dev(
        handoff, reviewed, last, probe, expected_request_id=req,
    )
    assert body.hypotheses == handoff.after_wait.hypotheses
    assert body.observation is not handoff.after_wait.observation
    assert body.interoceptions == ()
    assert snapshot["source_scope"].endswith(
        "NO_PAPER_TICK_NATIVE_EQUIVALENCE"
    )
    assert not hasattr(body, "issue_action")
