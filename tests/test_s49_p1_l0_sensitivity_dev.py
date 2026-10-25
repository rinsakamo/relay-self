"""P1 knockdown: same real-typed World, alternate explicit DEV model rates."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_l0_sensitivity_dev import (
    BASELINE, CHALLENGE, compare_p1_knockdown_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import compose_s49_p1_dev_self_body
from test_s49_paper_world_first_dev import PLAYER, sources
from test_self_live_think import native_probe


def input_tuple(monkeypatch, *, distance=2.0):
    original, paper = sources(monkeypatch)
    handoff, reviewed = compose_s49_p1_dev_self_body(
        original, paper, expected_player_uuid=PLAYER, profile=BASELINE,
    )
    seq = original["actual_native_actions"][-1][
        "execution_evidence"]["after_observation"]["seq"] + 5
    req = f"s49-postwait:{handoff.session_id}:{handoff.action_id}"
    probe = replace(
        native_probe(seq, distance, sid=handoff.session_id), request_id=req,
    )
    retained = s19._epoch_one()[1].new_state
    return original, paper, probe, retained


def evaluate(original, paper, probe, retained):
    return compare_p1_knockdown_dev(
        original, paper, probe, expected_player_uuid=PLAYER, retained=retained,
    )


def test_same_postwait_native_s42_choice_but_p1_stress_changes_feasible_gait(monkeypatch):
    original, paper, probe, retained = input_tuple(monkeypatch)
    actions_before = tuple(original["actual_native_actions"])
    report = evaluate(original, paper, probe, retained)
    assert report["status"] == "DEV_SAME_WORLD_P1_RATE_KNOCKDOWN"
    assert report["classification"] == "DEV_ONLY_MODEL_SENSITIVITY_NOT_CALIBRATION"
    assert report["native_seq"] == probe.seq
    assert report["native_request_id"] == probe.request_id
    assert report["last_actual_move_m"] > 0
    assert report["baseline_move_rate_per_block"] == BASELINE.move_per_block.value
    assert report["stress_move_rate_per_block"] == CHALLENGE.move_per_block.value
    assert report["baseline_fatigue_after_move"] == pytest.approx(
        report["last_actual_move_m"] * BASELINE.move_per_block.value,
    )
    assert report["stress_fatigue_after_move"] == pytest.approx(1.0)
    assert report["baseline_fatigue_after_wait"] == pytest.approx(0)
    assert report["stress_fatigue_after_wait"] == pytest.approx(0.2)
    assert report["s42_original_selection"] == "MOVE_AWAY"
    assert report["baseline_l0_capability_candidate"] == (
        "MOVE_AWAY_NOMINAL_GAIT_MODEL_ONLY"
    )
    assert report["stress_l0_capability_candidate"] == (
        "MOVE_AWAY_SCALE_TO_CAPACITY_MODEL_ONLY"
    )
    assert report["baseline_one_tick_capacity"] == pytest.approx(1.0)
    assert report["stress_one_tick_capacity"] == pytest.approx(0.86)
    assert not report["stress_profile_is_measured"]
    assert not report["native_paper_tick_alignment_attested"]
    assert not report["real_next_l0_decide_called"]
    assert report["new_native_probes"] == report["new_action_issuers"] == 0
    assert report["real_action_count_added"] == 0
    assert original["actual_native_actions"] == list(actions_before)
    assert not report["qualification_go"] and not report["science_go"]


def test_far_real_native_geometry_never_creates_move_from_p1(monkeypatch):
    original, paper, probe, retained = input_tuple(monkeypatch, distance=10.0)
    report = evaluate(original, paper, probe, retained)
    assert report["s42_original_selection"] == "WAIT"
    assert report["baseline_l0_capability_candidate"] == "S42_WAIT_UNCHANGED"
    assert report["stress_l0_capability_candidate"] == "S42_WAIT_UNCHANGED"
    assert report["real_action_count_added"] == 0


@pytest.mark.parametrize("bad", (
    "foreign_session", "foreign_request", "old_seq", "forged_distance",
    "paper_abort", "missing_paper_tick", "foreign_retained",
))
def test_stress_comparison_requires_same_original_source(monkeypatch, bad):
    original, paper, probe, retained = input_tuple(monkeypatch)
    if bad == "foreign_session":
        probe = replace(probe, session_id="foreign")
    elif bad == "foreign_request":
        probe = replace(probe, request_id="foreign")
    elif bad == "old_seq":
        probe = replace(probe, seq=0)
    elif bad == "forged_distance":
        original["actual_native_actions"][-1]["movement_m"] = 900
    elif bad == "paper_abort":
        paper += "S49_DEV_BACK_WAIT_ABORT reason=SELF_MOVEMENT_EVENT_DURING_OBSERVATION\n"
    elif bad == "missing_paper_tick":
        paper = "".join(
            line for line in paper.splitlines(keepends=True)
            if "index=5 " not in line
        )
    else:
        retained = s19._epoch_one()[1].previous_state
    with pytest.raises(BoundaryRejected):
        evaluate(original, paper, probe, retained)
