"""S12: current S49 goal/learning discrimination is NOT yet executable."""
from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.self_s10_memory_ablation import compare_shadow_ab
from adapters.mineflayer.self_s11_l5_shadow_intake import review_l5_against_s10
from adapters.mineflayer.self_s12_discrimination_preflight import (
    S12PreflightRejected,
    S12Readiness,
    assess_s12,
)
from test_self_s11_l5_shadow_intake import _inputs


def _v_cheap():
    # Source-shaped expectation; the *actual* pinned V owner result is checked
    # by the separate S12 pinned-V/L5 cross-lane CI job.
    return {
        "schema": "RELAYSELF_V_L5_STRONG_CHEAP_NULL_V1",
        "l5_exact_head": "17c5357fd5625274ee567ad979b780e77bf7b1e7",
        "s11_exact_head": "69a150cc6f687e5b379713ba4c5e0ba2de60b38f",
        "source_class": "PINNED_L5_SYNTHETIC_FIXTURE_NOT_REAL_WORLD",
        "independent_cheap_policy": "SAME_TRAINING_TWO_FEATURE_FOUR_CELL_RATE_LOOKUP",
        "training_source_shaped_episodes": 16,
        "paired_s10_world_outcomes": 0,
        "heldout_original_goal_receipts": 0,
        "paired_s11_original_action_vocabulary": False,
        "four_contexts_tested": 4,
        "cheap_matches_l5_all_contexts": True,
        "memory_shifts_shadow_ref": True,
        "physical_goal_effect": "NOT_MEASURED",
        "learning_mechanism_advantage_over_strongest_cheap": False,
        "s11_action_authorized": False,
        "scientific_g3": "NO_GO",
        "classification": "V_L5_TWO_FEATURE_CHEAP_NULL_REPRODUCES_CONTEXTUAL_SHADOW",
    }


def _sources():
    from test_self_s10_memory_ablation import _arms

    a, _ = _arms()
    s10 = compare_shadow_ab(**a)
    s11_args = _inputs()
    # Both helpers intentionally create independent source-shaped fixtures;
    # compare output identity only (same source session and seq), not R1 bytes.
    s11 = review_l5_against_s10(**s11_args)
    assert s10.session_id == s11.session_id
    assert s10.probe_seq == s11.probe_seq
    return s10, s11


def test_current_s49_action_opportunity_has_only_one_executable_ref():
    s10, s11 = _sources()
    out = assess_s12(s10=s10, s11=s11, v_cheap=_v_cheap())
    assert out.status is S12Readiness.NOT_READY
    assert out.s49_executable_candidate_refs == ("MOVE_AWAY",)
    assert out.s49_nonissuing_refs == ("WAIT",)
    assert out.v_two_feature_parity
    assert len(out.blockers) == 8
    assert not out.experiment_ready and not out.action_authority
    assert not out.fresh_world_permission and not out.science_qualified
    assert out.real_world_actions_issued == 0
    assert out.independent_physical_goal_receipts == 0
    assert out.actual_paired_heldout_trials == 0
    assert out.learning_updates == out.habit_grants == 0


def test_original_s49_exec_contract_is_move_away_only():
    actual = inspect.getsource(NormalSessionActionExecutor.require_authorizations)
    assert "step.choice.selection is not WorldChoiceKind.MOVE_AWAY" in actual
    assert 'bound.candidate_ref != "MOVE_AWAY"' in actual
    assert 'bound.binding.action_ref != "MOVE_BACKWARD"' in actual


@pytest.mark.parametrize("field", [
    "l5_exact_head", "s11_exact_head", "source_class",
    "independent_cheap_policy", "cheap_matches_l5_all_contexts",
    "learning_mechanism_advantage_over_strongest_cheap",
    "physical_goal_effect", "scientific_g3",
    "training_source_shaped_episodes", "four_contexts_tested",
    "heldout_original_goal_receipts", "paired_s11_original_action_vocabulary",
])
def test_v_forged_strong_cheap_advantage_or_source_not_admitted(field):
    s10, s11 = _sources()
    v = _v_cheap()
    original = v[field]
    if type(original) is bool:
        v[field] = not original
    elif type(original) is int:
        v[field] = original + 1
    else:
        v[field] = "FORGED"
    with pytest.raises(S12PreflightRejected, match="V original cheap"):
        assess_s12(s10=s10, s11=s11, v_cheap=v)


@pytest.mark.parametrize("field", [
    "action_authority", "science_qualified",
    "goal_evidence_authenticated_here", "source_byte_authenticated_here",
    "memory_causal_benefit_established",
])
def test_s11_cannot_launder_authority_or_claimed_goal(field):
    s10, s11 = _sources()
    with pytest.raises(S12PreflightRejected, match="S10/S11"):
        assess_s12(s10=s10, s11=replace(s11, **{field: True}), v_cheap=_v_cheap())


def test_s10_real_action_or_goal_claim_rejected():
    s10, s11 = _sources()
    with pytest.raises(S12PreflightRejected, match="S10/S11"):
        assess_s12(s10=replace(s10, issued_actions=1), s11=s11, v_cheap=_v_cheap())
    with pytest.raises(S12PreflightRejected, match="S10/S11"):
        assess_s12(s10=replace(s10, goal_attested=True), s11=s11, v_cheap=_v_cheap())


def test_s12_rejects_wrong_s11_session_or_source():
    s10, s11 = _sources()
    with pytest.raises(S12PreflightRejected, match="S10/S11"):
        assess_s12(s10=s10, s11=replace(s11, session_id="foreign"), v_cheap=_v_cheap())
    with pytest.raises(S12PreflightRejected, match="S10/S11"):
        assess_s12(s10=s10, s11=replace(s11, probe_seq=777), v_cheap=_v_cheap())
