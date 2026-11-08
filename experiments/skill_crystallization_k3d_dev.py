"""K3-D: request a source-grounded *behavior-changing* Skill or explicit abstention.

DEV synthetic World only. Never installs a Skill, calls real S49, or issues real
physical Actions. Fixture tests cannot demonstrate real Gemma learning.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import ModelCallFailure, gemma_l2, validate_skill
from experiments.skill_crystallization_k3b_dev import (
    prepare_revision,
    proposal_json_schema,
    validate_proposal,
)
from experiments.skill_crystallization_k3c_dev import (
    evaluate_comparison,
    semantic_delta,
)

REAL_GEMMA_HOLDOUT_SEED = 20261126  # Keep unopened until after a real model response.
FIXTURE_SEED = 20261122  # Opened by deterministic tests, NOT a future real holdout.
EXPOSED_SEEDS = frozenset({20261108, 20261109, 20261110, 20261111, 20261112, 20261120, FIXTURE_SEED})


def _grounded_prior(first: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Check old source, original suspension and the previously equivalent L2 proposal."""
    from experiments.skill_crystallization_k3b_dev import verify_suspension

    # Never generate missing observations while authenticating the original.
    if not isinstance(previous.get("shift_observations"), list) or not verify_suspension(
        previous["shift_observations"]
    ):
        raise ValueError("ORIGINAL_SUSPENSION_REQUIRED")
    state = prepare_revision(first, previous)
    if not state["suspended"]:
        raise ValueError("SUSPENSION_REQUIRED")
    if previous.get("proposal_status") != "SKILL" or previous.get("schema_validation") != "PASS":
        raise ValueError("PRIOR_VALIDATED_PROPOSAL_REQUIRED")
    old = state["old_skill"]
    ids = {r["experience_id"] for r in state["training"] + state["shift_observations"]}
    proposal = validate_proposal(previous.get("proposal"), ids)
    prior_skill = proposal["skill"]
    if semantic_delta(old, prior_skill)["classification"] != "EXECUTION_EQUIVALENT":
        raise ValueError("K3B_PARENT_NOT_EXECUTION_EQUIVALENT")
    return {**state, "prior_skill": prior_skill}


def _evidence_scope(skill: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, int]:
    """Count observed shift traces covered by a guard, without hidden effects."""
    counts = {"observed_selected": 0, "observed_selected_success": 0,
              "observed_selected_failure": 0, "observed_excluded_failure": 0,
              "observed_excluded_success": 0}
    for row in observations:
        start = row["start_distance"]
        selected = (row["surface_cue"] == skill["surface"]
                    and skill["min_distance"] <= start < skill["max_distance"])
        # A bound narrower than the old 4 moves can be assessed from the observed prefix;
        # no inaccessible future effect is invented.
        trace = row["observed_trace"]
        if selected:
            counts["observed_selected"] += 1
            outcome = trace[min(skill["max_actions"], len(trace) - 1)] >= skill["target_distance"]
            counts["observed_selected_success" if outcome else "observed_selected_failure"] += 1
        else:
            counts["observed_excluded_success" if row["outcome_success"] else
                   "observed_excluded_failure"] += 1
    return counts


def run_k3d(
    first: dict[str, Any], previous: dict[str, Any], *, mode: str,
    fixture_proposal: dict[str, Any] | None = None,
    endpoint: str | None = None, model: str | None = None, timeout: float = 300,
    evaluation_seed: int | None = None, record_dir: Path | None = None,
) -> dict[str, Any]:
    """One optional L2 call. No holdout access until a validated novel Skill exists."""
    state = _grounded_prior(first, previous)
    old = state["old_skill"]
    prior_skill = state["prior_skill"]
    if mode not in ("fixture", "gemma"):
        raise ValueError("INVALID_MODE")
    seed = evaluation_seed if evaluation_seed is not None else (
        FIXTURE_SEED if mode == "fixture" else REAL_GEMMA_HOLDOUT_SEED
    )
    if type(seed) is not int or (mode == "gemma" and seed in EXPOSED_SEEDS) or (
        mode == "fixture" and seed == REAL_GEMMA_HOLDOUT_SEED
    ):
        raise ValueError("HOLDOUT_SEED_CONTAMINATION")
    report: dict[str, Any] = {
        "classification": "DEV_ONLY_K3D_SYNTHETIC_NO_S49",
        "mode": mode, "old_skill_state": "SUSPENDED",
        "previous_revision_semantics": "EXECUTION_EQUIVALENT",
        "model_record": None, "model_calls_in_mock_runner": 0,
        "proposal": None, "validator_error": None,
        "proposal_status": None, "schema_validation": "NOT_RUN",
        "semantic_delta": None, "observed_scope": None,
        "holdout": None, "evaluation_seed": None, "stages": [],
    }
    evidence = state["training"] + state["shift_observations"]
    ids = {r["experience_id"] for r in evidence}
    if mode == "fixture":
        if fixture_proposal is None:
            raise ValueError("FIXTURE_PROPOSAL_REQUIRED")
        proposal = fixture_proposal
    else:
        if not endpoint or not model:
            raise ValueError("LOCAL_GEMMA_ENDPOINT_AND_MODEL_REQUIRED")
        context = {
            "old_skill": old,
            "previous_revision": prior_skill,
            "previous_revision_execution_equal_to_old": True,
            "previous_explanation_error": (
                "The previous answer described the old Skill as one MOVE_AWAY, "
                "but the old Skill was already max_actions=4."
            ),
            "objective": (
                "Change the executable guard or bounded control meaningfully "
                "based on observed results, or abstain. Do not relabel the same "
                "policy as an improved Skill."
            ),
            "max_actions_inclusive": 4,
            "allowed_action": "MOVE_AWAY",
        }
        try:
            proposal, raw = gemma_l2(
                evidence, endpoint=endpoint, model=model, timeout=timeout,
                revision_context=context,
                response_schema=proposal_json_schema(), record_dir=record_dir,
                system_append=(
                    "The previous Skill already allowed FOUR MOVE_AWAY actions, "
                    "so do not repeat the inaccurate one-action claim. "
                    "Use SKILL only if you change executable behavior/guard. "
                    "Otherwise choose ABSTAIN or an explicitly uncertain UNSAT. "
                    "Do not claim that a changed name, evidence IDs or rationale "
                    "changes physical behavior. Never exceed four actions."
                ),
            )
            report["model_record"] = raw
            report["stages"].append("L2_REVISION_ATTEMPTED")
        except ModelCallFailure as exc:
            report["model_record"] = exc.record
            report["validator_error"] = str(exc)
            report["stages"].append("L2_REVISION_ATTEMPTED")
            return report
    report["proposal"] = proposal
    try:
        import jsonschema
    except ImportError:
        report["validator_error"] = "JSONSCHEMA_UNAVAILABLE"
        return report
    try:
        jsonschema.validate(proposal, proposal_json_schema())
    except jsonschema.ValidationError as exc:
        report["schema_validation"] = "REJECTED"
        report["validator_error"] = f"SCHEMA_INVALID: {exc.message}"
        return report
    report["schema_validation"] = "PASS"
    try:
        candidate = validate_proposal(proposal, ids)
    except ValueError as exc:
        report["validator_error"] = str(exc)
        return report
    report["stages"].append("PROPOSAL_VALIDATED")
    report["proposal_status"] = candidate["status"]
    if candidate["status"] != "SKILL":
        report["stages"].append("EXPLICIT_ABSTENTION_ACCEPTED")
        return report
    skill = validate_skill(candidate["skill"], ids)
    delta = semantic_delta(old, skill)
    report["semantic_delta"] = delta
    report["observed_scope"] = _evidence_scope(skill, state["shift_observations"])
    if delta["classification"] == "EXECUTION_EQUIVALENT":
        report["stages"].append("NO_BEHAVIORAL_CHANGE")
        # Protect unopened real holdout from a known-equivalent relabeling.
        return report
    report["stages"].append("EXECUTION_SPEC_CHANGED")
    # Independent new-seed outcomes below do NOT modify this candidate.
    paired = evaluate_comparison(old, skill, seed=seed)
    report["holdout"] = paired
    report["evaluation_seed"] = seed
    report["stages"].append("PAIRED_MOCK_HOLDOUT_EVALUATED")
    report["behavioral_difference_observed"] = bool(
        paired["new_selected_guard_differ"] or paired["new_selected_traces_differ"]
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first", type=Path, required=True)
    p.add_argument("--k3b-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mode", choices=("fixture", "gemma"), required=True)
    p.add_argument("--proposal-file", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--evaluation-seed", type=int)
    p.add_argument("--record-dir", type=Path, required=False)
    a = p.parse_args()
    first = json.loads(a.first.read_text(encoding="utf-8"))
    previous = json.loads(a.k3b_report.read_text(encoding="utf-8"))
    fixture = json.loads(a.proposal_file.read_text(encoding="utf-8")) if a.proposal_file else None
    result = run_k3d(first, previous, mode=a.mode, fixture_proposal=fixture,
                     endpoint=a.endpoint, model=a.model, timeout=a.timeout,
                     evaluation_seed=a.evaluation_seed, record_dir=a.record_dir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                     encoding="utf-8")
    print(f"{result['classification']} status={result['proposal_status']} "
          f"stages={result['stages']} out={a.out}")


if __name__ == "__main__":
    main()
