"""S11 offline S-owned consumer: source-shaped L5 report is never Action authority."""
from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from adapters.mineflayer.self_s10_memory_ablation import compare_shadow_ab
from adapters.mineflayer.self_s11_l5_shadow_intake import (
    L5_EXACT_HEAD,
    S11Disposition,
    S11IntakeRejected,
    S11SourcePointer,
    review_l5_against_s10,
)
from test_self_s10_memory_ablation import _arms


def _inputs():
    arms, _ = _arms()
    s10 = compare_shadow_ab(**arms)
    original = "a" * 64
    source = S11SourcePointer(s10.session_id, s10.probe_seq, original, L5_EXACT_HEAD)
    advice = {
        "status": "shadow_distinct_from_cheapest_controls",
        "proposed_action_ref": "WAIT",
        "original_no_memory_ref": "MOVE_AWAY",
        "exact_cue_cheap_ref": None,
        "singleton_cheap_ref": None,
        "global_cheap_ref": None,
        "training_sessions": 16,
        "comparisons": 6,
        "memory_causal_benefit_established": False,
        "goal_improvement_attested": False,
        "action_authority": False,
        "habit_grants": 0,
        "learning_updates": 0,
        "reason": "synthetic_l5_shadow_only",
    }
    return {
        "paired": s10,
        "current_probe": arms["probe"],
        "source": source,
        "admitted_current_probe_sha256": frozenset({original}),
        "l5_advice": advice,
    }


def test_distinct_l5_candidate_remains_non_authorizing_s10_baseline():
    fields = _inputs()
    before = asdict(fields["paired"])
    result = review_l5_against_s10(**fields)
    assert result.status is S11Disposition.SHADOW_DIFFERENCE
    assert result.fixed_l0_selection == "MOVE_AWAY"
    assert result.suggested_ref == "WAIT"
    assert result.no_memory_ref == "MOVE_AWAY"
    assert result.two_feature_cheap_equivalent_possible
    assert result.physical_actions == result.habit_grants == result.learning_updates == 0
    assert not result.action_authority
    assert not result.science_qualified
    assert not result.goal_evidence_authenticated_here
    assert not result.source_byte_authenticated_here
    assert not result.memory_causal_benefit_established
    assert asdict(fields["paired"]) == before


def test_actual_l5_fixture_vocabulary_is_not_falsely_paired_with_s10():
    fields = _inputs()
    fields["l5_advice"] = {
        **fields["l5_advice"],
        "proposed_action_ref": "OPTION_B",
        "original_no_memory_ref": "OPTION_A",
    }
    result = review_l5_against_s10(**fields)
    assert result.status is S11Disposition.UNPAIRED_SOURCE
    assert result.action_authority is False


@pytest.mark.parametrize("mutation", [
    "foreign_session", "stale_sequence", "missing_probe_sha",
    "unknown_l5_head", "foreign_probe", "old_s10", "s10_action",
    "positive_authority", "positive_goal", "positive_causal",
    "positive_habit", "positive_learning", "unknown_status",
    "no_training", "fabricated_cheap_difference", "same_candidate",
    "invalid_action_ref", "missing_field", "unexpected_field",
    "abstention_with_candidate",
])
def test_wrong_or_forged_crosslane_claims_cannot_create_a_positive_admission(mutation):
    fields = _inputs()
    value = fields["l5_advice"].copy()
    src = fields["source"]
    if mutation == "foreign_session":
        fields["source"] = replace(src, session_id="foreign")
    elif mutation == "stale_sequence":
        fields["source"] = replace(src, source_seq=src.source_seq - 1)
    elif mutation == "missing_probe_sha":
        fields["admitted_current_probe_sha256"] = frozenset()
    elif mutation == "unknown_l5_head":
        with pytest.raises(S11IntakeRejected):
            replace(src, claimed_l5_head="0" * 40)
        return
    elif mutation == "foreign_probe":
        fields["current_probe"] = replace(fields["current_probe"], session_id="foreign")
    elif mutation == "old_s10":
        fields["paired"] = replace(fields["paired"], withheld_selection="WAIT")
    elif mutation == "s10_action":
        fields["paired"] = replace(fields["paired"], issued_actions=1)
    elif mutation == "positive_authority":
        value["action_authority"] = True
    elif mutation == "positive_goal":
        value["goal_improvement_attested"] = True
    elif mutation == "positive_causal":
        value["memory_causal_benefit_established"] = True
    elif mutation == "positive_habit":
        value["habit_grants"] = 1
    elif mutation == "positive_learning":
        value["learning_updates"] = 1
    elif mutation == "unknown_status":
        value["status"] = "learning_proven"
    elif mutation == "no_training":
        value["training_sessions"] = 1
    elif mutation == "fabricated_cheap_difference":
        value["global_cheap_ref"] = "WAIT"
    elif mutation == "same_candidate":
        value["original_no_memory_ref"] = "WAIT"
    elif mutation == "invalid_action_ref":
        value["proposed_action_ref"] = "MOVE AWAY"
    elif mutation == "missing_field":
        del value["goal_improvement_attested"]
    elif mutation == "unexpected_field":
        value["signs_goal"] = True
    elif mutation == "abstention_with_candidate":
        value["status"] = "no_goal_data"
    fields["l5_advice"] = value
    if mutation in {"foreign_session", "stale_sequence", "missing_probe_sha"}:
        result = review_l5_against_s10(**fields)
        assert result.status is S11Disposition.UNPAIRED_SOURCE
        assert result.physical_actions == 0 and not result.action_authority
    else:
        with pytest.raises(S11IntakeRejected):
            review_l5_against_s10(**fields)


def test_abstention_and_equal_controls_cannot_issue_action():
    fields = _inputs()
    advice = fields["l5_advice"]
    advice["status"] = "no_goal_data"
    advice["proposed_action_ref"] = None
    result = review_l5_against_s10(**fields)
    assert result.status is S11Disposition.L5_ABSTAINED
    assert result.suggested_ref is None
    assert not result.action_authority
    advice["status"] = "cheap_same_information_matches"
    advice["proposed_action_ref"] = "WAIT"
    advice["global_cheap_ref"] = "WAIT"
    result = review_l5_against_s10(**fields)
    assert result.status is S11Disposition.CHEAP_OR_NO_MEMORY_EQUAL
    assert not result.action_authority
