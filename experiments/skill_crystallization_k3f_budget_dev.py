"""K3-F: compare four vs ten MOVE_AWAY actions, isolating *capacity*.

Synthetic DEV shadow only. This module does NOT modify K3-B/K3-E DSL limits,
reuse prior holdouts, install a Skill, or admit native S49 physical Actions.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import (
    MockIssuer,
    TARGET,
    WorldTrial,
    applicable,
    cue_for,
    outcome,
    run_baseline,
    run_skill,
    skill_json_schema,
    validate_skill,
)

BUDGETS = (4, 10)
EXPLORATORY_SEED = 20261207  # Already exposed when this comparison is run.
PROTECTED_SEEDS = frozenset({20261126, 20261205, 20261128})
MOTION_REGIMES = {"changed": (0.18, 0.23), "slow": (0.09, 0.14)}


def budget10_schema() -> dict[str, Any]:
    """Opt-in K3-F wire schema, never replace the historic 1..4 default."""
    schema = copy.deepcopy(skill_json_schema())
    schema["properties"]["max_actions"]["enum"] = list(range(1, 11))
    return schema


def validate_budget10_shadow(spec: object, evidence_ids: set[str]) -> dict[str, Any]:
    """All original DSL checks remain active; only the *shadow* cap changes."""
    if not isinstance(spec, dict):
        raise ValueError("SHADOW_SPEC_INVALID")
    n = spec.get("max_actions")
    if type(n) is not int or not 1 <= n <= 10:
        raise ValueError("SHADOW_ACTION_BUDGET_INVALID")
    # Legacy validator still verifies all other fields and evidence references.
    validate_skill({**spec, "max_actions": min(n, 4)}, evidence_ids)
    return spec


def run_budget10_shadow(
    spec: dict[str, Any], trial: WorldTrial, *, evidence_ids: set[str],
) -> dict[str, Any]:
    """Never share the original S49 issuer; fail before consuming missing effects."""
    validate_budget10_shadow(spec, evidence_ids)
    if len(trial.effects) < spec["max_actions"]:
        raise ValueError("PHYSICAL_EFFECT_SEQUENCE_TOO_SHORT")
    cue = cue_for(trial)
    if not applicable(spec, cue, trial):
        raise ValueError("NO_MATCH_OR_STALE_SOURCE")
    issuer = MockIssuer(trial)
    while issuer.actions < spec["max_actions"] and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    return outcome(issuer)


def paired_trials(
    old: dict[str, Any], *, seed: int, n: int,
) -> list[tuple[str, WorldTrial]]:
    """Predeclared 10-effect synthetic sequences, identical under both budgets."""
    if type(seed) is not int or seed in PROTECTED_SEEDS:
        raise ValueError("PROTECTED_OR_INVALID_SEED")
    if type(n) is not int or not 2 <= n <= 1024 or n % 2:
        raise ValueError("PAIRED_TRIAL_COUNT_INVALID")
    if old["surface"] != "normal" or old["max_actions"] != 4:
        raise ValueError("EXPECTED_OLD_NORMAL_FOUR_ACTION_SKILL")
    rng = random.Random(seed)
    trials: list[tuple[str, WorldTrial]] = []
    for i in range(n):
        regime = "changed" if i % 2 == 0 else "slow"
        low, high = MOTION_REGIMES[regime]
        start = rng.uniform(old["min_distance"], old["max_distance"])
        # Source-observation examples are not retroactively extended: these are
        # NEW simulated trials, each provisioned with ten possible outcomes.
        effects = tuple(rng.uniform(low, high) for _ in range(10))
        trials.append((regime, WorldTrial(
            surface="normal", start=start, effects=effects,
            session=f"k3f-{seed}-{i:03}",
        )))
    return trials


def compare_action_budgets(
    first: dict[str, Any], *, seed: int = EXPLORATORY_SEED, n: int = 64,
) -> dict[str, Any]:
    if not isinstance(first.get("training"), list):
        raise ValueError("ORIGINAL_TRAINING_MISSING")
    ids = {row["experience_id"] for row in first["training"]}
    old = validate_skill(first.get("candidate_raw"), ids)
    trial_set = paired_trials(old, seed=seed, n=n)
    widened = {**old, "max_actions": 10}
    validate_budget10_shadow(widened, ids)
    summaries = {
        regime: {
            "n": 0, "fixed2_success": 0, "budget4_success": 0,
            "budget10_success": 0, "fixed2_actions": 0, "budget4_actions": 0,
            "budget10_actions": 0, "budget4_exhausted_and_failed": 0,
            "budget10_exhausted_and_failed": 0, "rescued_by_extra_actions": 0,
            "extra_actions_on_successful_budget4": 0,
        }
        for regime in MOTION_REGIMES
    }
    rows = []
    for regime, trial in trial_set:
        fixed = run_baseline(trial)
        old_result = run_skill(old, trial, cue_for(trial))
        new_result = run_budget10_shadow(widened, trial, evidence_ids=ids)
        if (new_result["trace"][:len(old_result["trace"])] != old_result["trace"]
                or new_result["action_count"] < old_result["action_count"]):
            raise ValueError("PAIRED_PHYSICAL_PREFIX_MISMATCH")
        if old_result["success"] and new_result != old_result:
            raise ValueError("POST_GOAL_ACTION_OR_RESULT_DIVERGENCE")
        metric = summaries[regime]
        metric["n"] += 1
        for label, result in (("fixed2", fixed), ("budget4", old_result),
                              ("budget10", new_result)):
            metric[f"{label}_success"] += int(result["success"])
            metric[f"{label}_actions"] += result["action_count"]
        metric["budget4_exhausted_and_failed"] += int(
            old_result["action_count"] == 4 and not old_result["success"]
        )
        metric["budget10_exhausted_and_failed"] += int(
            new_result["action_count"] == 10 and not new_result["success"]
        )
        metric["rescued_by_extra_actions"] += int(
            not old_result["success"] and new_result["success"]
        )
        metric["extra_actions_on_successful_budget4"] += (
            new_result["action_count"] - old_result["action_count"]
            if old_result["success"] else 0
        )
        rows.append({
            "session": trial.session, "regime": regime,
            "start_distance": round(trial.start, 6),
            "fixed2": fixed, "budget4": old_result,
            "budget10": new_result,
            "effects_length": len(trial.effects),
        })
    return {
        "classification": "DEV_ONLY_K3F_SYNTHETIC_CAPACITY_AB",
        "parent_skill_id": old["skill_id"],
        "seed": seed, "trials": n, "policy_change": "MAX_ACTIONS_4_TO_10_ONLY",
        "action_mode": "GOAL_EARLY_STOP",
        "summary": summaries, "paired_trials": rows,
        "gemma_posts": 0, "native_s49_actions": 0, "real_worlds": 0,
        "old_skill_modified": False, "previous_holdout_20261126": "UNOPENED",
        "k3e_probe_20261205": "UNOPENED",
        "notes": (
            "Fresh synthetic physical sequences with ten potential outcomes, "
            "not continuations of original four-action observations. "
            "Mock Action counts are not measured physical cost. "
            "No new real S49 admission, real Gemma judgment or learning update."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=EXPLORATORY_SEED)
    parser.add_argument("--n", type=int, default=64)
    args = parser.parse_args()
    first = json.loads(args.first.read_text(encoding="utf-8"))
    report = compare_action_budgets(first, seed=args.seed, n=args.n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    for regime, metrics in report["summary"].items():
        print(f"{regime}: 4={metrics['budget4_success']}/{metrics['n']} "
              f"10={metrics['budget10_success']}/{metrics['n']} "
              f"rescued={metrics['rescued_by_extra_actions']}")


if __name__ == "__main__":
    main()
