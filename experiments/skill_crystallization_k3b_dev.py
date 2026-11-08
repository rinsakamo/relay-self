"""K3-B: one bounded real-L2 revision proposal, or explicit abstention.

DEV synthetic World only. Never installs an L0 skill, issues S49 actions, or
writes Learning/Habit. Uses only already-observed failures in the model prompt.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import (
    Cue,
    ModelCallFailure,
    WorldTrial,
    applicable,
    cue_for,
    gemma_l2,
    run_baseline,
    run_skill,
    skill_json_schema,
    validate_skill,
)
from experiments.skill_crystallization_revision_dev import failures, shifted

MAX_ACTIONS = 4
STATES = ("SKILL", "ABSTAIN", "UNSATISFIABLE_WITHIN_BUDGET")
EVALUATION_SEED = 20261112
REVISION_SEED = 20261111


def proposal_json_schema() -> dict[str, Any]:
    """A closed, strictly bounded wire response; abstention has null skill."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": list(STATES)},
            "reason": {"type": "string", "minLength": 1, "maxLength": 512},
            "skill": {"anyOf": [skill_json_schema(), {"type": "null"}]},
        },
        "required": ["status", "reason", "skill"],
    }


def validate_proposal(raw: object, evidence_ids: set[str]) -> dict[str, Any]:
    """Schema is not authorization: validate status, evidence and budget again."""
    if not isinstance(raw, dict) or set(raw) != {"status", "reason", "skill"}:
        raise ValueError("PROPOSAL_FIELDS_INVALID")
    status = raw["status"]
    if not isinstance(status, str) or status not in STATES:
        raise ValueError("PROPOSAL_STATUS_INVALID")
    reason = raw["reason"]
    if not isinstance(reason, str) or not (1 <= len(reason.strip()) <= 512):
        raise ValueError("PROPOSAL_REASON_INVALID")
    if status != "SKILL":
        if raw["skill"] is not None:
            raise ValueError("ABSTENTION_CANNOT_EXECUTE_SKILL")
    else:
        validate_skill(raw["skill"], evidence_ids)
    return raw


def verify_suspension(rows: list[dict[str, Any]]) -> bool:
    """Only actually observed adjacent failures can suspend, never a label."""
    if len(rows) < 2:
        return False
    return all(row.get("outcome_success") is False for row in rows[-2:])


def prepare_revision(
    first: dict[str, Any], prior: dict[str, Any], *, seed: int = REVISION_SEED
) -> dict[str, Any]:
    """Continue source-qualified observed trials, exclude all future eval data."""
    if not isinstance(first.get("training"), list):
        raise ValueError("TRAINING_MISSING")
    source_rows = first["training"]
    ids = {row["experience_id"] for row in source_rows}
    old = validate_skill(first.get("candidate_raw"), ids)
    if not isinstance(prior.get("shift_observations"), list):
        raise ValueError("PRIOR_OBSERVATIONS_MISSING")
    prior_rows = prior["shift_observations"]
    if not all(isinstance(row, dict) and "source_session" in row
               and type(row.get("outcome_success")) is bool for row in prior_rows):
        raise ValueError("PRIOR_OBSERVATIONS_INVALID")
    # Never append post-suspension trials to previously recorded evidence.
    observations = (list(prior_rows) if verify_suspension(prior_rows)
                    else failures(old, shifted(seed, old["surface"]), prior_rows))
    suspended = verify_suspension(observations)
    return {
        "old_skill": old,
        "training": source_rows,
        "shift_observations": observations,
        "suspended": suspended,
        "rollback": ("FIXED_L0_FALLBACK" if suspended else None),
        "revision_context": {
            "old_skill": old,
            "failure_reason": (
                "Two consecutive observed, applicable attempts failed after changed motion. "
                "Produce a bounded revised skill, or explicitly abstain."
            ),
            "available_actions": ["MOVE_AWAY"],
            "max_actions_inclusive": MAX_ACTIONS,
            "no_proof_of_unsatisfiability": True,
        },
    }


def _cheap(trial: WorldTrial) -> dict[str, Any]:
    # The predeclared Grand Null is fixed two moves on normal, three on ice.
    if trial.surface != "ice":
        return run_baseline(trial)
    from experiments.skill_crystallization_dev import MockIssuer, outcome

    issuer = MockIssuer(trial)
    while issuer.actions < 3 and issuer.distance < 3.2:
        issuer.move_away(session=trial.session)
    return outcome(issuer)


def evaluate_revision(spec: dict[str, Any], *, seed: int = EVALUATION_SEED,
                      count: int = 16) -> dict[str, Any]:
    """Frozen independent holdout; a skill cannot see this before validation."""
    trials = shifted(seed, spec["surface"])[:count]
    totals = {
        "n": 0, "selected": 0, "success": 0, "actions": 0,
        "baseline_success": 0, "baseline_actions": 0,
        "cheap_success": 0, "cheap_actions": 0,
        "no_match": 0, "misapplication": 0, "invalid_cue_selected": 0,
        "runtime_error": 0, "guard_elapsed_ns": 0, "skill_execution_elapsed_ns": 0,
    }
    for trial in trials:
        base = run_baseline(trial)
        cheap = _cheap(trial)
        cue = cue_for(trial)
        start = time.perf_counter_ns()
        selected = applicable(spec, cue, trial)
        totals["guard_elapsed_ns"] += time.perf_counter_ns() - start
        if selected:
            start = time.perf_counter_ns()
            try:
                result = run_skill(spec, trial, cue)
            except ValueError:
                totals["runtime_error"] += 1
                raise
            totals["skill_execution_elapsed_ns"] += time.perf_counter_ns() - start
        else:
            result = base
        totals["n"] += 1
        totals["selected"] += int(selected)
        totals["no_match"] += int(not selected)
        totals["misapplication"] += int(selected and trial.surface != spec["surface"])
        totals["success"] += int(result["success"])
        totals["actions"] += result["action_count"]
        totals["baseline_success"] += int(base["success"])
        totals["baseline_actions"] += base["action_count"]
        totals["cheap_success"] += int(cheap["success"])
        totals["cheap_actions"] += cheap["action_count"]
        bad_cues = [
            cue_for(trial, stale=True),
            cue_for(trial, unknown=True),
            cue_for(trial, wrong_session=True),
            Cue(trial.surface, trial.start, trial.session, 10, 11, False),
        ]
        totals["invalid_cue_selected"] += sum(
            applicable(spec, bad, trial) for bad in bad_cues
        )
    totals["notes"] = (
        "Timing is local Python mock wall-clock overhead, not native S49 or "
        "physical latency. Action counts are synthetic costs, not measured body cost."
    )
    return totals


def run_k3b(
    first: dict[str, Any], prior: dict[str, Any], *, mode: str,
    endpoint: str | None = None, model: str | None = None, timeout: float = 300,
    fixture_proposal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = prepare_revision(first, prior)
    report: dict[str, Any] = {
        "classification": "DEV_ONLY_SYNTHETIC_WORLD_NO_REAL_S49",
        "mode": mode,
        "old_skill_state": ("SUSPENDED" if state["suspended"] else "ACTIVE"),
        "rollback": state["rollback"],
        "shift_observations": state["shift_observations"],
        "proposal": None,
        "proposal_status": None,
        "validator_error": None,
        "model_record": None,
        "holdout": None,
        "stages": [],
    }
    if not state["suspended"]:
        report["validator_error"] = "TWO_CONSECUTIVE_FAILURES_NOT_OBSERVED"
        return report
    evidence = state["training"] + state["shift_observations"]
    ids = {row["experience_id"] for row in evidence}
    if mode == "fixture":
        if fixture_proposal is None:
            raise ValueError("FIXTURE_PROPOSAL_REQUIRED")
        proposal = fixture_proposal
    elif mode == "gemma":
        if not endpoint or not model:
            raise ValueError("GEMMA_ENDPOINT_AND_MODEL_REQUIRED")
        try:
            proposal, record = gemma_l2(
                evidence, endpoint=endpoint, model=model, timeout=timeout,
                revision_context=state["revision_context"],
                response_schema=proposal_json_schema(),
                system_append=(
                    "Return a proposal object with status SKILL, ABSTAIN or "
                    "UNSATISFIABLE_WITHIN_BUDGET, a reason, and skill. "
                    "For abstention set skill=null. For SKILL, use 1..4 actions and "
                    "cite only observed experience IDs. 4 is an execution "
                    "constraint, not a physical law. Do not claim mathematical "
                    "unsatisfiability without proof; UNSAT is an uncertain judgment."
                ),
            )
            report["model_record"] = record
        except ModelCallFailure as exc:
            report["model_record"] = exc.record
            report["validator_error"] = str(exc)
            return report
    else:
        raise ValueError("UNKNOWN_MODE")
    report["proposal"] = proposal
    try:
        result = validate_proposal(proposal, ids)
    except ValueError as exc:
        report["validator_error"] = str(exc)
        return report
    report["stages"].append("PROPOSAL_VALIDATED")
    report["proposal_status"] = result["status"]
    if result["status"] == "SKILL":
        report["holdout"] = evaluate_revision(result["skill"])
        report["stages"].append("NEW_SKILL_MOCK_EVALUATED")
        # Never declare actual self-installation or real-world learning here.
    else:
        report["stages"].append("EXPLICIT_ABSTENTION_ACCEPTED")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("gemma", "fixture"), required=True)
    parser.add_argument("--proposal-file", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    first = json.loads(args.first.read_text(encoding="utf-8"))
    prior = json.loads(args.prior.read_text(encoding="utf-8"))
    fixture = (json.loads(args.proposal_file.read_text(encoding="utf-8"))
               if args.proposal_file is not None else None)
    result = run_k3b(first, prior, mode=args.mode, endpoint=args.endpoint,
                     model=args.model, timeout=args.timeout, fixture_proposal=fixture)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                        encoding="utf-8")
    print(f"{result['classification']} old={result['old_skill_state']} "
          f"proposal={result['proposal_status']} validation={result['validator_error']}")


if __name__ == "__main__":
    main()
