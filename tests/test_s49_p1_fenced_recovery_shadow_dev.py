"""DEV negative controls: counterfactual recovery is never P1 WAIT admission."""
from __future__ import annotations

import math
from copy import deepcopy

import pytest

from adapters.mineflayer.s49_p1_fenced_recovery_shadow_dev import (
    P1CausalShadowRejected,
    project_p1_fenced_wait_shadow_dev,
)
from experiments.fatigue_p1 import FatigueProfile


def inputs():
    return dict(
        fence={
            "classification": "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY",
            "session_id": "s",
            "action_ids": ["a1", "a2"],
            "paper_first_owner_fence_delivery_tick": 258,
            "paper_second_owner_fence_delivery_tick": 442,
            "paper_causal_subwindow_first_tick": 264,
            "paper_causal_subwindow_last_tick": 437,
            "paper_causal_subwindow_contiguous_still_ticks": 174,
            "paper_stillness_candidate_interval": [264, 437],
            "boundary_guard_ticks_each_side": 2,
            "owner_original_first_s16_terminal_before_start_delivery": True,
            "owner_original_second_s15_issue_after_end_delivery": True,
            "node_original_first_clear_before_start_delivery": True,
            "node_original_second_set_after_end_delivery": True,
            "original_issuer_no_second_issue_during_causal_subwindow": True,
            "node_local_controls_off_sampled_between_first_clear_second_set": True,
            "paper_body_static_measured_inside_causal_subwindow": True,
            "same_process_native_paper_clock_epoch_calibrated": False,
            "node_physics_paper_tick_1_to_1_attested": False,
            "global_world_quiescence_attested": False,
            "global_action_absence_attested": False,
            "physical_WAIT_admitted": False,
            "P1_recovery_posted": False,
            "M0_posted": False,
            "qualification_go": False,
            "science_go": False,
        },
        p1_replay={
            "single_p1_model_replayed": True,
            "source_qualified": False,
            "p1_ledger_posted": False,
            "m0_ledger_posted": False,
            "fatigue_initial": 0.6,
            "fatigue_final": 0.6155207399,
            "world_ticks_replayed": 13,
        },
        action_bracket={
            "original_owner_release": True,
            "independent_source_attested": False,
            "last_tick": 260,
            "elapsed_callbacks": 13,
        },
        profile=FatigueProfile(enabled=True, initial=0.6),
        session_id="s", first_action_id="a1", second_action_id="a2",
        original_m0_energy_remaining=10.413667611509306,
    )


def test_174_tick_hypothetical_recovery_is_only_shadow():
    data = inputs()
    original = deepcopy(data)
    out = project_p1_fenced_wait_shadow_dev(**data)
    assert data == original
    assert out["candidate_ticks"] == 174
    assert out["paper_stillness_tick_interval"] == [264, 437]
    assert out["unclassified_world_ticks_after_first_dash_before_candidate"] == 3
    assert out["normalized_world_seconds_if_20tps"] == 8.7
    assert out["counterfactual_end_fatigue"] == pytest.approx(
        data["p1_replay"]["fatigue_final"] * math.exp(-0.12 * 8.7), abs=1e-12,
    )
    assert out["counterfactual_p1_recovered_if_all_wait"] == pytest.approx(
        0.39883054913786237, abs=1e-10,
    )
    assert out["verified_physical_WAIT_ticks"] == 0
    assert out["p1_recovery_applied"] == 0
    assert out["actual_p1_state_updated"] is False
    assert out["m0_posted"] is False
    assert out["action_issued"] is False
    assert out["physical_wait_admitted"] is False
    assert out["original_m0_energy_remaining_unchanged"] == original[
        "original_m0_energy_remaining"
    ]


@pytest.mark.parametrize("fault", [
    "fence_class", "foreign_session", "action", "zero_ticks",
    "lost_tick", "early_start", "no_guard", "no_owner",
    "node_off_missing", "paper_static_missing", "fake_global_wait",
    "fake_global_absence", "wait_admitted", "p1_posted", "m0_posted",
    "clock_join_claim", "foreign_bracket", "first_dash_not_replayed",
    "p1_source_qualified", "p1_ledger_posted", "replay_gap",
    "nan_fatigue", "high_fatigue", "wrong_profile",
    "infinite_m0", "forged_fence_world_end", "wrong_second_action",
])
def test_fail_closed_on_missing_provenance_or_unauthorized_effect(fault):
    d = inputs()
    fence, p1, bracket = d["fence"], d["p1_replay"], d["action_bracket"]
    if fault == "fence_class":
        fence["classification"] = "CERTIFIED_WAIT"
    elif fault == "foreign_session":
        fence["session_id"] = "alien"
    elif fault == "action":
        fence["action_ids"] = ["a1", "alien"]
    elif fault == "zero_ticks":
        fence["paper_causal_subwindow_contiguous_still_ticks"] = 0
    elif fault == "lost_tick":
        fence["paper_causal_subwindow_last_tick"] = 438
    elif fault == "early_start":
        fence["paper_causal_subwindow_first_tick"] = 259
    elif fault == "no_guard":
        fence["boundary_guard_ticks_each_side"] = 0
    elif fault == "no_owner":
        fence["original_issuer_no_second_issue_during_causal_subwindow"] = False
    elif fault == "node_off_missing":
        fence["node_local_controls_off_sampled_between_first_clear_second_set"] = False
    elif fault == "paper_static_missing":
        fence["paper_body_static_measured_inside_causal_subwindow"] = False
    elif fault == "fake_global_wait":
        fence["global_world_quiescence_attested"] = True
    elif fault == "fake_global_absence":
        fence["global_action_absence_attested"] = True
    elif fault == "wait_admitted":
        fence["physical_WAIT_admitted"] = True
    elif fault == "p1_posted":
        fence["P1_recovery_posted"] = True
    elif fault == "m0_posted":
        fence["M0_posted"] = True
    elif fault == "clock_join_claim":
        fence["node_physics_paper_tick_1_to_1_attested"] = True
    elif fault == "foreign_bracket":
        bracket["original_owner_release"] = False
    elif fault == "first_dash_not_replayed":
        p1["single_p1_model_replayed"] = False
    elif fault == "p1_source_qualified":
        p1["source_qualified"] = True
    elif fault == "p1_ledger_posted":
        p1["p1_ledger_posted"] = True
    elif fault == "replay_gap":
        p1["world_ticks_replayed"] = 12
    elif fault == "nan_fatigue":
        p1["fatigue_final"] = float("nan")
    elif fault == "high_fatigue":
        p1["fatigue_final"] = 1.1
    elif fault == "wrong_profile":
        d["profile"] = FatigueProfile(enabled=False)
    elif fault == "infinite_m0":
        d["original_m0_energy_remaining"] = float("inf")
    elif fault == "forged_fence_world_end":
        fence["paper_second_owner_fence_delivery_tick"] = 430
    else:
        d["second_action_id"] = "alien"
    with pytest.raises(P1CausalShadowRejected):
        project_p1_fenced_wait_shadow_dev(**d)


def test_no_initial_fatigue_cannot_mint_recovery():
    d = inputs()
    d["p1_replay"]["fatigue_final"] = 0.0
    out = project_p1_fenced_wait_shadow_dev(**d)
    assert out["counterfactual_end_fatigue"] == 0
    assert out["counterfactual_p1_recovered_if_all_wait"] == 0


def test_missing_unknown_transition_gap_rejected():
    d = inputs()
    d["action_bracket"]["last_tick"] = 265
    with pytest.raises(P1CausalShadowRejected):
        project_p1_fenced_wait_shadow_dev(**d)
