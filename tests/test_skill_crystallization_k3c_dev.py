"""K3-C negative controls and fresh synthetic paired comparison; zero real LLM/World calls."""

from __future__ import annotations

import pytest

from experiments.skill_crystallization_dev import Cue, WorldTrial, cue_for, make_trials, observed_training
from experiments.skill_crystallization_k3c_dev import (
    NEW_HOLDOUT_SEED,
    continue_as_new_intent,
    evaluate_comparison,
    execute_attempt,
    report_from_files,
    semantic_delta,
)


def candidates():
    training = observed_training(make_trials(20261108, 16, phase="train"))
    old = {
        "version": 1, "skill_id": "old", "surface": "normal",
        "min_distance": 2.314917, "max_distance": 2.457525,
        "target_distance": 3.2, "max_actions": 4,
        "on_failure": "ESCALATE",
        "evidence_ids": [r["experience_id"] for r in training if r["surface_cue"] == "normal"],
    }
    new = {**old, "skill_id": "changed_name",
           "evidence_ids": ["shift-experience-000", "shift-experience-001"]}
    return old, new, training


def test_semantic_comparator_detects_metadata_only():
    old, new, _ = candidates()
    result = semantic_delta(old, new)
    assert result["classification"] == "EXECUTION_EQUIVALENT"
    assert result["metadata_changed"]
    assert result["changed_execution_fields"] == []
    assert result["reason_semantics"] == "NOT_VERIFIED_BY_STRUCTURAL_COMPARISON"


def test_scope_narrowing_is_not_metadata_only():
    old, new, _ = candidates()
    new["min_distance"] = 2.43
    result = semantic_delta(old, new)
    assert result["classification"] == "EXECUTION_SPEC_CHANGED"
    assert result["changed_execution_fields"] == ["min_distance"]
    observed = evaluate_comparison(old, new, seed=NEW_HOLDOUT_SEED)
    assert observed["new_selected_guard_differ"] > 0
    assert observed["scope_change_covered_by_holdout"] is True


def test_paired_equivalent_execution_and_new_seed():
    old, new, _ = candidates()
    evaluated = evaluate_comparison(old, new)
    assert evaluated["seed"] == 20261120
    assert evaluated["n"] == 32
    assert evaluated["old_success"] == evaluated["new_success"]
    assert evaluated["old_actions"] == evaluated["new_actions"]
    assert evaluated["old_selected"] == evaluated["new_selected"]
    assert evaluated["new_selected_traces_differ"] == 0
    assert evaluated["new_selected_guard_differ"] == 0
    assert evaluated["cue_negative_rejections"] == 128
    assert evaluated["cue_negative_checks"] == 128
    assert evaluated["new_automatic_postfailure_actions"] == 0


def _failed_trial():
    return WorldTrial("normal", 2.4, (0.19,) * 5, "session-k3c")


def test_failure_preserves_outcome_no_implicit_fallback():
    old, _, _ = candidates()
    trial = _failed_trial()
    observed = execute_attempt(old, trial, intent_id="intent-A")
    assert observed["status"] == "ESCALATE"
    assert observed["actions"] == 4
    assert observed["final_distance"] == 3.16
    assert observed["world_effect_cursor"] == 4
    assert observed["escalation"]["remaining_skill_budget"] == 0
    assert observed["escalation"]["automatic_fallback_actions"] == 0
    assert observed["fallback_stage"] == "NONE"


def test_no_match_only_uses_preskill_fixed_l0():
    old, _, _ = candidates()
    trial = WorldTrial("normal", 2.1, (0.2,) * 5, "known-source")
    observed = execute_attempt(old, trial, intent_id="before-skill")
    assert observed["selected"] is False
    assert observed["fallback_stage"] == "BEFORE_SKILL"
    assert observed["actions"] == 2
    assert observed["status"] == "CHEAP_FAILED"
    assert observed["escalation"] is None


@pytest.mark.parametrize("bad", ["wrong-session", "unknown", "stale", "incomplete"])
def test_invalid_source_never_falls_through_to_cheap(bad):
    old, _, _ = candidates()
    trial = _failed_trial()
    cue = cue_for(trial)
    if bad == "wrong-session":
        cue = cue_for(trial, wrong_session=True)
    elif bad == "unknown":
        cue = cue_for(trial, unknown=True)
    elif bad == "stale":
        cue = cue_for(trial, stale=True)
    elif bad == "incomplete":
        cue = Cue(cue.surface, cue.distance, cue.session, 10, 11, False)
    result = execute_attempt(old, trial, intent_id="bad-cue", cue=cue)
    assert result["status"] == "DEFER_INVALID_CUE"
    assert result["actions"] == 0
    assert result["fallback_stage"] == "NONE"


def test_explicit_fresh_new_intent_preserves_physical_cursor():
    old, _, _ = candidates()
    trial = _failed_trial()
    observed = execute_attempt(old, trial, intent_id="old-intent")
    new_cue = Cue("normal", observed["final_distance"], trial.session, 11, 12)
    ledger = set()
    result = continue_as_new_intent(
        trial, observed, new_intent_id="new-intent",
        fresh_cue=new_cue, admitted=True, cleared=True, budget=1,
        consumed_receipts=ledger,
    )
    assert result["start_distance"] == observed["final_distance"]
    assert result["final_distance"] == 3.35
    assert result["actions"] == 1
    assert result["cumulative_actions"] == 5  # two distinct attempted Intents
    assert result["status"] == "NEW_INTENT_SUCCEEDED"
    with pytest.raises(ValueError, match="REPLAYED_ESCALATION"):
        continue_as_new_intent(trial, observed, new_intent_id="third-intent",
                               fresh_cue=new_cue, admitted=True, cleared=True, budget=1,
                               consumed_receipts=ledger)


@pytest.mark.parametrize("mutation,code", [
    ({"admitted": False}, "NEW_INTENT_ADMISSION_REQUIRED"),
    ({"cleared": False}, "NEW_INTENT_ADMISSION_REQUIRED"),
    ({"new_intent_id": "old-intent"}, "OLD_INTENT_CANNOT_REISSUE"),
    ({"budget": 3}, "NEW_INTENT_BUDGET_INVALID"),
    ({"budget": True}, "NEW_INTENT_BUDGET_INVALID"),
    ({"fresh_cue": Cue("normal", 3.16, "other", 11, 12)},
     "FRESH_ANCHORED_OBSERVATION_REQUIRED"),
    ({"fresh_cue": Cue("normal", 2.4, "session-k3c", 11, 12)},
     "FRESH_ANCHORED_OBSERVATION_REQUIRED"),
    ({"fresh_cue": Cue("normal", 3.16, "session-k3c", 10, 12)},
     "FRESH_ANCHORED_OBSERVATION_REQUIRED"),
])
def test_invalid_recovery_never_issues_action(mutation, code):
    old, _, _ = candidates()
    trial = _failed_trial()
    observed = execute_attempt(old, trial, intent_id="old-intent")
    args = {
        "new_intent_id": "new-intent",
        "fresh_cue": Cue("normal", 3.16, trial.session, 11, 12),
        "admitted": True, "cleared": True, "budget": 1,
    }
    args.update(mutation)
    with pytest.raises(ValueError, match=code):
        continue_as_new_intent(trial, observed, **args)


def test_non_escalated_intent_cannot_be_recontinued():
    old, _, _ = candidates()
    trial = WorldTrial("normal", 3.1, (0.19,) * 5, "sess")
    result = execute_attempt(old, trial, intent_id="a")
    assert result["status"] != "ESCALATE"
    with pytest.raises(ValueError, match="NO_ESCALATION_TO_CONTINUE"):
        continue_as_new_intent(trial, result, new_intent_id="b",
                               fresh_cue=Cue("normal", result["final_distance"],
                                             "sess", 11, 12),
                               admitted=True, cleared=True, budget=1)


def test_original_and_k3b_fixture_report_can_be_inspected_without_model():
    old, new, training = candidates()
    source = {"candidate_raw": old, "training": training}
    report = {"proposal": {"status": "SKILL", "skill": new},
              "shift_observations": [
                  {"experience_id": "shift-experience-000"},
                  {"experience_id": "shift-experience-001"},
              ]}
    result = report_from_files(source, report)
    assert result["model_calls"] == 0
    assert result["new_model_revision"] == "NOT_RUN"
    assert result["semantic_delta"]["classification"] == "EXECUTION_EQUIVALENT"
    assert result["stage"] == "POSTFAILURE_ESCALATE_AND_MOCK_NEW_INTENT_EVALUATED"
    assert result["holdout"]["new_selected_traces_differ"] == 0


@pytest.mark.parametrize("field,value", [
    ("final_distance", 99),
    ("actions", 3),
    ("world_effect_cursor", 3),
    ("trace", [2.4]),
])
def test_forged_terminal_receipt_rejected(field, value):
    old, _, _ = candidates()
    trial = _failed_trial()
    result = execute_attempt(old, trial, intent_id="old-intent")
    result[field] = value
    with pytest.raises(ValueError, match="TERMINAL_OUTCOME_SOURCE_MISMATCH"):
        continue_as_new_intent(
            trial, result, new_intent_id="next-intent",
            fresh_cue=Cue("normal", 3.16, trial.session, 11, 12),
            admitted=True, cleared=True, budget=1,
        )
