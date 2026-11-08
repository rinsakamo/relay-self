"""K3-C: semantic Skill comparison and bounded post-failure handoff (synthetic DEV).

Neither a new L2 inference nor a physical S49 Action issuer/permission path.
Never interprets ordinary fallback as an implicit post-failure Action grant.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import (
    TARGET,
    Cue,
    MockIssuer,
    WorldTrial,
    applicable,
    cue_for,
    run_baseline,
    run_skill,
    validate_skill,
)
from experiments.skill_crystallization_revision_dev import shifted

# Identifying tags and evidence are intentionally excluded from behavioral meaning.
EXECUTION_FIELDS = (
    "version", "surface", "min_distance", "max_distance",
    "target_distance", "max_actions", "on_failure",
)
NEW_HOLDOUT_SEED = 20261120  # Never use the earlier 20261112 for this new comparison.


def semantic_delta(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changed = [field for field in EXECUTION_FIELDS if old[field] != new[field]]
    return {
        "classification": "EXECUTION_EQUIVALENT" if not changed else "EXECUTION_SPEC_CHANGED",
        "changed_execution_fields": changed,
        "metadata_changed": any(old.get(k) != new.get(k)
                                for k in ("skill_id", "evidence_ids")),
        "reason_semantics": "NOT_VERIFIED_BY_STRUCTURAL_COMPARISON",
        "note": "A scope/budget change is not proof of improved outcomes; compare paired traces.",
    }


def _cue_is_current(cue: Cue, trial: WorldTrial) -> bool:
    # Missing/expired source does not permit even the pre-skill cheap fallback.
    return bool(
        cue.coverage_complete
        and cue.surface in ("normal", "ice")
        and cue.session == trial.session
        and cue.sequence <= cue.valid_until
        and type(cue.distance) in (int, float)
        and math.isfinite(cue.distance)
        and cue.distance == trial.start
    )


def execute_attempt(spec: dict[str, Any], trial: WorldTrial, *,
                    intent_id: str, cue: Cue | None = None) -> dict[str, Any]:
    """One attempted Intent. Failed Skill returns ESCALATE, not implicit MOVE."""
    if not isinstance(intent_id, str) or not intent_id.strip():
        raise ValueError("INTENT_ID_REQUIRED")
    active_cue = cue if cue is not None else cue_for(trial)
    if not _cue_is_current(active_cue, trial):
        return {"status": "DEFER_INVALID_CUE", "intent_id": intent_id,
                "session": trial.session, "selected": False,
                "actions": 0, "final_distance": trial.start, "success": False,
                "trace": [trial.start], "escalation": None,
                "fallback_stage": "NONE", "world_effect_cursor": 0}
    selected = applicable(spec, active_cue, trial)
    result = run_skill(spec, trial, active_cue) if selected else run_baseline(trial)
    state = "SUCCEEDED" if result["success"] else (
        "ESCALATE" if selected else "CHEAP_FAILED"
    )
    escalation = None
    if selected and not result["success"]:
        escalation = {
            "source_session": trial.session,
            "intent_id": intent_id,
            "skill_id": spec["skill_id"],
            "source_sequence": active_cue.sequence,
            "last_observed_distance": result["final_distance"],
            "actions_consumed": result["action_count"],
            "remaining_skill_budget": spec["max_actions"] - result["action_count"],
            "failure": "TARGET_NOT_REACHED",
            "next_step": "REASSESS_INTENT_OR_REQUEST_NEW_ADMISSION",
            "automatic_fallback_actions": 0,
        }
    return {
        "status": state, "intent_id": intent_id, "session": trial.session,
        "selected": selected, "actions": result["action_count"],
        "final_distance": result["final_distance"],
        "success": result["success"], "trace": result["trace"],
        "escalation": escalation,
        "fallback_stage": "BEFORE_SKILL" if not selected else "NONE",
        "world_effect_cursor": result["action_count"],
    }


def continue_as_new_intent(
    trial: WorldTrial, prior: dict[str, Any], *,
    new_intent_id: str, fresh_cue: Cue,
    admitted: bool, cleared: bool, budget: int,
    consumed_receipts: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Explicitly authorized mock new Intent, anchored to terminal position.

    This is an independent, synthetic admission fixture, not S49 authorization.
    No autonomous fallback or in-place refill of the previous Skill budget.
    """
    escalation = prior.get("escalation")
    if prior.get("status") != "ESCALATE" or not isinstance(escalation, dict):
        raise ValueError("NO_ESCALATION_TO_CONTINUE")
    if not (admitted is True and cleared is True):
        raise ValueError("NEW_INTENT_ADMISSION_REQUIRED")
    if not isinstance(new_intent_id, str) or not new_intent_id.strip():
        raise ValueError("NEW_INTENT_ID_REQUIRED")
    if new_intent_id == escalation["intent_id"]:
        raise ValueError("OLD_INTENT_CANNOT_REISSUE")
    if type(budget) is not int or not (1 <= budget <= 2):
        raise ValueError("NEW_INTENT_BUDGET_INVALID")
    key = (trial.session, escalation["intent_id"])
    if consumed_receipts is not None and key in consumed_receipts:
        raise ValueError("REPLAYED_ESCALATION")
    cursor = prior["world_effect_cursor"]
    if type(cursor) is not int or cursor < 0 or cursor > len(trial.effects):
        raise ValueError("WORLD_CURSOR_INVALID")
    expected_distance = round(trial.start + sum(trial.effects[:cursor]), 6)
    expected_trace = [round(trial.start + sum(trial.effects[:n]), 6)
                      for n in range(cursor + 1)]
    if (prior.get("session") != trial.session
            or prior.get("actions") != cursor
            or prior.get("trace") != expected_trace
            or prior.get("final_distance") != expected_distance
            or escalation.get("source_session") != trial.session
            or escalation.get("actions_consumed") != cursor
            or escalation.get("last_observed_distance") != expected_distance
            or escalation.get("remaining_skill_budget") != 0):
        raise ValueError("TERMINAL_OUTCOME_SOURCE_MISMATCH")
    if (fresh_cue.session != trial.session
            or fresh_cue.surface != trial.surface
            or not fresh_cue.coverage_complete
            or fresh_cue.sequence <= escalation["source_sequence"]
            or fresh_cue.valid_until < fresh_cue.sequence
            or type(fresh_cue.distance) not in (float, int)
            or not math.isfinite(fresh_cue.distance)
            or abs(fresh_cue.distance - prior["final_distance"]) > 1e-6):
        raise ValueError("FRESH_ANCHORED_OBSERVATION_REQUIRED")
    if budget > len(trial.effects) - cursor:
        raise ValueError("FUTURE_EFFECTS_UNAVAILABLE")
    # No rewind: the new attempted Intent resumes at the post-Skill physical state.
    next_trial = WorldTrial(
        surface=trial.surface, start=prior["final_distance"],
        effects=trial.effects[cursor:], session=trial.session,
    )
    issuer = MockIssuer(next_trial)
    while issuer.actions < budget and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    if consumed_receipts is not None:
        consumed_receipts.add(key)
    return {
        "status": "NEW_INTENT_SUCCEEDED" if issuer.distance >= TARGET
        else "NEW_INTENT_FAILED",
        "intent_id": new_intent_id, "session": trial.session,
        "start_distance": next_trial.start,
        "final_distance": round(issuer.distance, 6),
        "actions": issuer.actions,
        "cumulative_actions": cursor + issuer.actions,
        "trace": issuer.history,
        "source_sequence": fresh_cue.sequence,
        "physical_authority": "MOCK_ONLY",
    }


def evaluate_comparison(old: dict[str, Any], new: dict[str, Any], *,
                        seed: int = NEW_HOLDOUT_SEED, count: int = 32,
                        recovery_budget: int = 1) -> dict[str, Any]:
    """Fresh paired synthetic scenarios; freeze candidate before inspecting them."""
    if type(count) is not int or count < 1 or count > 128:
        raise ValueError("EVALUATION_COUNT_INVALID")
    if type(recovery_budget) is not int or recovery_budget != 1:
        raise ValueError("RECOVERY_BUDGET_INVALID")
    from experiments.skill_crystallization_k3b_dev import _cheap

    trials = shifted(seed, "normal")[:count]
    summary = {
        "n": count, "seed": seed,
        "old_success": 0, "new_success": 0, "fixed_success": 0, "cheap_success": 0,
        "cheap_actions": 0, "new_no_match": 0, "new_misapplication": 0,
        "new_cpu_ns": 0, "llm_calls_in_holdout": 0,
        "old_actions": 0, "new_actions": 0, "fixed_actions": 0,
        "old_selected": 0, "new_selected": 0,
        "new_escalated": 0, "new_failure_after_selected": 0,
        "new_automatic_postfailure_actions": 0,
        "new_recovery_attempted": 0,
        "new_recovery_success": 0,
        "new_recovery_actions": 0,
        "new_selected_traces_differ": 0,
        "new_selected_guard_differ": 0,
        "cue_negative_checks": 0, "cue_negative_rejections": 0,
    }
    used_handoffs: set[tuple[str, str]] = set()
    for i, trial in enumerate(trials):
        old_receipt = execute_attempt(old, trial, intent_id=f"old-{i}")
        started = time.process_time_ns()
        new_receipt = execute_attempt(new, trial, intent_id=f"new-{i}")
        summary["new_cpu_ns"] += time.process_time_ns() - started
        fixed = run_baseline(trial)
        cheap = _cheap(trial)
        summary["cheap_success"] += int(cheap["success"])
        summary["cheap_actions"] += cheap["action_count"]
        summary["new_no_match"] += int(not new_receipt["selected"])
        summary["new_misapplication"] += int(new_receipt["selected"] and trial.surface != new["surface"])
        summary["old_success"] += int(old_receipt["success"])
        summary["new_success"] += int(new_receipt["success"])
        summary["fixed_success"] += int(fixed["success"])
        summary["old_actions"] += old_receipt["actions"]
        summary["new_actions"] += new_receipt["actions"]
        summary["fixed_actions"] += fixed["action_count"]
        summary["old_selected"] += int(old_receipt["selected"])
        summary["new_selected"] += int(new_receipt["selected"])
        summary["new_escalated"] += int(new_receipt["status"] == "ESCALATE")
        summary["new_failure_after_selected"] += int(
            new_receipt["selected"] and not new_receipt["success"]
        )
        if old_receipt["trace"] != new_receipt["trace"]:
            summary["new_selected_traces_differ"] += 1
        if old_receipt["selected"] != new_receipt["selected"]:
            summary["new_selected_guard_differ"] += 1
        for bad_cue in (
            cue_for(trial, stale=True), cue_for(trial, wrong_session=True),
            cue_for(trial, unknown=True),
            Cue(trial.surface, trial.start, trial.session, 10, 11, False),
        ):
            negative = execute_attempt(new, trial, intent_id=f"bad-{i}", cue=bad_cue)
            summary["cue_negative_checks"] += 1
            summary["cue_negative_rejections"] += int(
                negative["status"] == "DEFER_INVALID_CUE" and negative["actions"] == 0
            )
        if new_receipt["status"] == "ESCALATE":
            assert new_receipt["escalation"]["automatic_fallback_actions"] == 0
            remaining = len(trial.effects) - new_receipt["world_effect_cursor"]
            if remaining >= recovery_budget:
                fresh = Cue(
                    trial.surface, new_receipt["final_distance"],
                    trial.session, 11, 12,
                )
                recovered = continue_as_new_intent(
                    trial, new_receipt, new_intent_id=f"recover-{i}",
                    fresh_cue=fresh, admitted=True, cleared=True,
                    budget=recovery_budget, consumed_receipts=used_handoffs,
                )
                summary["new_recovery_attempted"] += 1
                summary["new_recovery_actions"] += recovered["actions"]
                summary["new_recovery_success"] += int(
                    recovered["status"] == "NEW_INTENT_SUCCEEDED"
                )
    summary["equivalence"] = semantic_delta(old, new)
    summary["scope_change_covered_by_holdout"] = (
        summary["new_selected_guard_differ"] > 0
    )
    summary["notes"] = (
        "Postfailure behavior is ESCALATE, not automatic physical fallback. "
        "Recovery is a separate mock Intent with fresh cue, clear and a new explicit "
        "one-Action budget; it is NOT actual S49 admission or Self learning. "
        "All costs are synthetic Action counts."
    )
    return summary


def report_from_files(first: dict[str, Any], k3b: dict[str, Any], *,
                      seed: int = NEW_HOLDOUT_SEED) -> dict[str, Any]:
    original = first.get("candidate_raw")
    training = first.get("training")
    if not isinstance(training, list):
        raise ValueError("OLD_TRAINING_MISSING")
    old = validate_skill(original, {r["experience_id"] for r in training})
    proposal = k3b.get("proposal")
    if not isinstance(proposal, dict) or proposal.get("status") != "SKILL":
        raise ValueError("VALIDATED_NEW_SKILL_REQUIRED")
    observations = k3b.get("shift_observations")
    if not isinstance(observations, list) or not all(
        isinstance(r, dict) and "experience_id" in r for r in observations
    ):
        raise ValueError("SHIFT_EVIDENCE_MISSING")
    revised = validate_skill(proposal.get("skill"), {
        r["experience_id"] for r in training + observations
    })
    return {
        "classification": "DEV_ONLY_SYNTHETIC_K3C_NO_REAL_S49",
        "model_calls": 0,
        "new_model_revision": "NOT_RUN",
        "old_skill_id": old["skill_id"],
        "new_skill_id": revised["skill_id"],
        "semantic_delta": semantic_delta(old, revised),
        "holdout": evaluate_comparison(old, revised, seed=seed),
        "stage": "POSTFAILURE_ESCALATE_AND_MOCK_NEW_INTENT_EVALUATED",
        "unproven": ["C3 autonomous promotion", "real S49 issuance", "real L2 repair"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--k3b-report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=NEW_HOLDOUT_SEED)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    first = json.loads(args.first.read_text(encoding="utf-8"))
    k3b = json.loads(args.k3b_report.read_text(encoding="utf-8"))
    result = report_from_files(first, k3b, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{result['classification']} equivalence="
          f"{result['semantic_delta']['classification']} "
          f"holdout={result['holdout']['new_success']}/{result['holdout']['n']}")


if __name__ == "__main__":
    main()
