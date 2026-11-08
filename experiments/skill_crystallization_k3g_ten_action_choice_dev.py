"""K3-G: real L2 choice under opt-in maximum ten MOVE_AWAY Actions.

Only shadow/mock evaluation. Never changes native S49 limits, original 1..4 DSL,
Memory/Habit or prior evidence. Model has no access to future mock outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import (
    TARGET,
    MockIssuer,
    ModelCallFailure,
    WorldTrial,
    applicable,
    cue_for,
    gemma_l2,
    outcome,
    run_baseline,
    run_skill,
)
from experiments.skill_crystallization_k3d_dev import _grounded_prior
from experiments.skill_crystallization_k3e_dev import (
    HYPOTHESES,
    PATTERNS,
    PROBES,
    _check_ids,
)
from experiments.skill_crystallization_k3f_budget_dev import (
    budget10_schema,
    run_budget10_shadow,
    validate_budget10_shadow,
)

K3G_SYSTEM_INSTRUCTION = (
    "You are L2. Return only JSON with ALL required fields in the strict Schema. "
    "The maximum permitted MOVE_AWAY actions for a NEW tentative Skill is TEN, "
    "not four. Ten is an upper bound: stop immediately upon reaching distance 3.2. "
    "The old Skill had max_actions=4; this is not an observation of what 10 "
    "actions would accomplish. From observed source evidence only, choose ONE: "
    "SKILL with a 1..10 bounded Skill and no PROBE; PROBE with one matching "
    "falsifiable hypothesis/prediction and skill=null; or ABSTAIN with skill=null. "
    "For SKILL set hypothesis INDETERMINATE, probe_id NONE, prediction UNKNOWN. "
    "For ABSTAIN use the same three fields. Do not copy unsupported claims of "
    "optimality, invent observations, or claim action permission. "
    "Do not know or predict the hidden simulator physics as established facts."
)

MODES = ("fixture", "gemma")
CHOICES = ("SKILL", "PROBE", "ABSTAIN")
FIXTURE_SEED = 20261210  # Used by offline tests; never a future blind seed.
REAL_SKILL_HOLDOUT_SEED = 20261213  # Never open in fixture mode or before valid real SKILL.
PREVIOUS_SEEDS = frozenset({
    20261108, 20261109, 20261110, 20261111, 20261112,
    20261120, 20261122, 20261124, 20261126, 20261128,
    20261205, 20261207,
})
REGIMES = {
    "normal_changed": ("normal", 0.18, 0.23),
    "normal_slower_stress": ("normal", 0.09, 0.14),
    "normal_reference": ("normal", 0.59, 0.67),
    "ice_changed": ("ice", 0.18, 0.23),
}


def verify_input_manifests(files: list[Path]) -> dict[str, Any]:
    """Verify all files listed in each historical source directory SHA256SUMS.

    File integrity only: the manifest itself is not an external signature.
    """
    summaries: dict[str, Any] = {}
    for item in files:
        directory = item.parent.resolve()
        manifest = directory / "SHA256SUMS"
        if not manifest.is_file() or not item.is_file():
            raise ValueError("ORIGINAL_SHA_MANIFEST_OR_INPUT_MISSING")
        rows = manifest.read_text(encoding="utf-8").splitlines()
        checked: set[str] = set()
        for line in rows:
            if not line.strip():
                continue
            fields = line.split(maxsplit=1)
            if len(fields) != 2:
                raise ValueError("ORIGINAL_SHA_MANIFEST_FORMAT_INVALID")
            digest, filename = fields
            filename = filename.lstrip("*").strip()
            relative = Path(filename)
            target = (directory / relative).resolve()
            if (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                    or not target.is_relative_to(directory)
                    or not target.is_file() or str(relative) in checked):
                raise ValueError("ORIGINAL_SHA_MANIFEST_ENTRY_INVALID")
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError("ORIGINAL_SHA_MANIFEST_MISMATCH")
            checked.add(str(relative))
        if not checked or not item.resolve().is_relative_to(directory):
            raise ValueError("ORIGINAL_INPUT_NOT_MANIFESTED")
        target_name = str(item.resolve().relative_to(directory))
        manifested_names = {
            str((directory / name).resolve().relative_to(directory))
            for name in checked
        }
        if target_name not in manifested_names:
            raise ValueError("ORIGINAL_INPUT_NOT_MANIFESTED")
        summaries[str(directory)] = {"checked_entries": len(checked), "status": "PASS"}
    return summaries


def choice_schema() -> dict[str, Any]:
    """One grammar-friendly closed response with all branch fields present."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": list(CHOICES)},
            "reason": {"type": "string", "minLength": 1, "maxLength": 700},
            "skill": {"anyOf": [budget10_schema(), {"type": "null"}]},
            "hypothesis": {"type": "string", "enum": list(HYPOTHESES)},
            "probe_id": {"type": "string", "enum": list(PROBES)},
            "prediction": {"type": "string", "enum": list(PATTERNS)},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "status", "reason", "skill", "hypothesis", "probe_id",
            "prediction", "evidence_ids",
        ],
    }


def _independent_schema_check(value: object) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise ValueError("JSONSCHEMA_UNAVAILABLE") from exc
    try:
        jsonschema.validate(value, choice_schema())
    except jsonschema.ValidationError as exc:
        raise ValueError(f"SCHEMA_INVALID: {exc.message}") from exc


def validate_choice(value: object, *, evidence_ids: set[str]) -> dict[str, Any]:
    """Strict branch semantics in addition to JSON Schema and the Skill validator."""
    _independent_schema_check(value)
    if not isinstance(value, dict):
        raise ValueError("CHOICE_FIELDS_INVALID")
    if value["status"] == "SKILL":
        if (value["skill"] is None or value["hypothesis"] != "INDETERMINATE"
                or value["probe_id"] != "NONE" or value["prediction"] != "UNKNOWN"):
            raise ValueError("SKILL_CHOICE_BRANCH_CONFLICT")
        _check_ids(value["evidence_ids"], evidence_ids, required=False)
        validate_budget10_shadow(value["skill"], evidence_ids)
    elif value["status"] == "PROBE":
        if value["skill"] is not None:
            raise ValueError("PROBE_CANNOT_EXECUTE_SKILL")
        expected = {
            "START_MARGIN_SENSITIVE": "START_MARGIN_PAIR",
            "MOTION_EFFECT_CHANGED": "MOTION_REGIME_PAIR",
        }
        if (expected.get(value["hypothesis"]) != value["probe_id"]
                or value["prediction"] == "UNKNOWN"):
            raise ValueError("PROBE_MUST_BE_FALSIFIABLE")
        _check_ids(value["evidence_ids"], evidence_ids, required=True)
    else:
        if (value["skill"] is not None or value["hypothesis"] != "INDETERMINATE"
                or value["probe_id"] != "NONE" or value["prediction"] != "UNKNOWN"):
            raise ValueError("ABSTAIN_CANNOT_SELECT_ACTION_OR_PROBE")
        _check_ids(value["evidence_ids"], evidence_ids, required=False)
    return value


def verified_context(
    first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
    k3e: dict[str, Any],
) -> dict[str, Any]:
    """Require historically observed suspension and two recorded model abstentions."""
    parent = _grounded_prior(first, k3b)
    d = k3d.get("proposal")
    e = k3e.get("proposal")
    if (k3d.get("mode") != "gemma" or k3d.get("proposal_status") != "ABSTAIN"
            or k3d.get("schema_validation") != "PASS"
            or not isinstance(d, dict) or d.get("status") != "ABSTAIN"
            or d.get("skill", object()) is not None):
        raise ValueError("K3D_ABSTENTION_SOURCE_INVALID")
    if (k3e.get("mode") != "gemma" or k3e.get("status") != "ABSTAIN"
            or not isinstance(e, dict) or e.get("status") != "ABSTAIN"
            or e.get("probe_id") != "NONE" or k3e.get("probe") is not None
            or "PROBE_ABSTENTION_ACCEPTED" not in k3e.get("stages", [])):
        raise ValueError("K3E_ABSTENTION_SOURCE_INVALID")
    evidence = parent["training"] + parent["shift_observations"]
    allowed = {r["experience_id"] for r in evidence}
    return {
        "old_skill": parent["old_skill"], "evidence": evidence, "ids": allowed,
        "prior_decisions": ["K3D_ABSTAIN", "K3E_ABSTAIN"],
    }


def fresh_trials(seed: int, *, n: int = 64) -> list[tuple[str, WorldTrial]]:
    """Four predeclared regimes with ten fresh possible outcomes per trial."""
    if type(seed) is not int or seed in PREVIOUS_SEEDS:
        raise ValueError("EXPOSED_OR_INVALID_SEED")
    if type(n) is not int or n < 4 or n > 256 or n % len(REGIMES):
        raise ValueError("TRIAL_COUNT_INVALID")
    rng = random.Random(seed)
    result: list[tuple[str, WorldTrial]] = []
    kinds = list(REGIMES)
    for i in range(n):
        name = kinds[i % len(kinds)]
        surface, low, high = REGIMES[name]
        start = rng.uniform(2.10, 2.55)
        effects = tuple(rng.uniform(low, high) for _ in range(10))
        result.append((name, WorldTrial(
            surface, start, effects, f"k3g-{seed}-{i:03}",
        )))
    return result


def _cheap(trial: WorldTrial) -> dict[str, Any]:
    if trial.surface != "ice":
        return run_baseline(trial)
    issuer = MockIssuer(trial)
    while issuer.actions < 3 and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    return outcome(issuer)


def _apply(old: dict[str, Any], candidate: dict[str, Any],
           trial: WorldTrial, ids: set[str]) -> dict[str, Any]:
    cue = cue_for(trial)
    matched = applicable(candidate, cue, trial)
    if not matched:
        return {"selected": False, "result": run_baseline(trial),
                "fallback": "BEFORE_SKILL", "escalated": False}
    if candidate is old:
        result = run_skill(old, trial, cue)
    else:
        result = run_budget10_shadow(candidate, trial, evidence_ids=ids)
    return {
        "selected": True, "result": result, "fallback": "NONE",
        "escalated": not result["success"],
    }


def paired_evaluation(old: dict[str, Any], revised: dict[str, Any], *,
                      evidence_ids: set[str], seed: int, n: int = 64) -> dict[str, Any]:
    """Only called after a validated meaningful model-generated SKILL."""
    summary = {
        key: {
            "n": 0, "selected_old": 0, "selected_new": 0,
            "fixed_success": 0, "cheap_success": 0,
            "old_success": 0, "new_success": 0,
            "fixed_actions": 0, "cheap_actions": 0,
            "old_actions": 0, "new_actions": 0,
            "changed_selection": 0, "changed_trace": 0,
            "new_selected_failure_escalations": 0,
            "automatic_postfailure_actions": 0,
            "fixed_max_actions": 0, "cheap_max_actions": 0,
            "old_max_actions": 0, "new_max_actions": 0,
            "old_fallbacks": 0, "new_fallbacks": 0,
        }
        for key in REGIMES
    }
    rows = []
    for regime, trial in fresh_trials(seed, n=n):
        base = run_baseline(trial)
        cheap = _cheap(trial)
        a = _apply(old, old, trial, evidence_ids)
        b = _apply(old, revised, trial, evidence_ids)
        row = summary[regime]
        row["n"] += 1
        row["selected_old"] += int(a["selected"])
        row["selected_new"] += int(b["selected"])
        row["fixed_success"] += int(base["success"])
        row["cheap_success"] += int(cheap["success"])
        row["old_success"] += int(a["result"]["success"])
        row["new_success"] += int(b["result"]["success"])
        for prefix, result in (("fixed", base), ("cheap", cheap),
                               ("old", a["result"]), ("new", b["result"])):
            row[f"{prefix}_actions"] += result["action_count"]
            row[f"{prefix}_max_actions"] = max(
                row[f"{prefix}_max_actions"], result["action_count"]
            )
        row["changed_selection"] += int(a["selected"] != b["selected"])
        row["changed_trace"] += int(a["result"]["trace"] != b["result"]["trace"])
        row["new_selected_failure_escalations"] += int(b["escalated"])
        row["old_fallbacks"] += int(not a["selected"])
        row["new_fallbacks"] += int(not b["selected"])
        rows.append({"regime": regime, "session": trial.session,
                     "fixed": base, "cheap": cheap, "old": a, "new": b})
    return {
        "classification": "DEV_ONLY_NEW_INDEPENDENT_SYNTHETIC_HOLDOUT",
        "seed": seed, "count": n, "by_regime": summary, "trials": rows,
        "physical_actions": 0, "model_calls_in_mock": 0,
        "note": "All Action counts are mock costs, not physical energy. "
                "No fallback after a selected Skill failed.",
    }


def _model_context(source: dict[str, Any]) -> dict[str, Any]:
    """No previous synthetic K3-F results, future trial seeds or hidden physics."""
    return {
        "old_skill": source["old_skill"],
        "observed_skill_failures": "Two adjacent observed failures led to suspension.",
        "previous_decisions": source["prior_decisions"],
        "constraint_change": "The mock planning/execution budget may now be 1..10 "
                             "MOVE_AWAY actions instead of 1..4 per attempted Skill. "
                             "This is a budget allowance, NOT observed new movement. "
                             "Goal must stop execution early.",
        "public_probe_options": {
            "START_MARGIN_PAIR": {
                "A_start": 2.32, "B_start": 2.44,
                "contrast": "same unknown movement regime, different initial margin",
                "max_actions_per_condition": 10,
            },
            "MOTION_REGIME_PAIR": {
                "A_start": 2.4, "B_start": 2.4,
                "contrast": "same initial margin, different unknown movement regime",
                "max_actions_per_condition": 10,
            },
        },
        "decision": "Choose a bounded new Skill, a falsifiable PROBE, or ABSTAIN. "
                    "Nothing is assumed optimal. No Skill or PROBE is automatically executed.",
    }


def run_choice(
    first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
    k3e: dict[str, Any], *, mode: str,
    fixture: dict[str, Any] | None = None, endpoint: str | None = None,
    model: str | None = None, timeout: float = 300,
    record_dir: Path | None = None,
    evaluation_seed: int | None = None,
    soul_directive: str | None = None,
    evaluate_skill: bool = True,
) -> dict[str, Any]:
    if soul_directive is not None and (
        type(soul_directive) is not str or not soul_directive.strip()
        or len(soul_directive) > 500 or "\n" in soul_directive
    ):
        raise ValueError("SOUL_DIRECTIVE_INVALID")
    if type(evaluate_skill) is not bool:
        raise ValueError("EVALUATE_SKILL_FLAG_INVALID")
    source = verified_context(first, k3b, k3d, k3e)
    if mode not in MODES:
        raise ValueError("UNKNOWN_MODE")
    if evaluation_seed is None:
        evaluation_seed = REAL_SKILL_HOLDOUT_SEED if mode == "gemma" else FIXTURE_SEED
    if (type(evaluation_seed) is not int or evaluation_seed in PREVIOUS_SEEDS
            or (mode == "fixture" and evaluation_seed == REAL_SKILL_HOLDOUT_SEED)
            or (mode == "gemma" and evaluation_seed == FIXTURE_SEED)):
        raise ValueError("HOLDOUT_SEED_NOT_ALLOWED")
    report = {
        "classification": "DEV_ONLY_K3G_TEN_ACTION_L2_CHOICE",
        "mode": mode, "status": "NOT_RUN", "proposal": None,
        "model_record": None, "schema_validation": "NOT_RUN",
        "validator_error": None, "stages": [],
        "old_skill_state": "SUSPENDED", "skill_installed": False,
        "skill_holdout": None, "skill_holdout_seed": None,
        "preserved_seeds": {"20261126": "UNOPENED", "20261205": "UNOPENED"},
        "native_s49_actions": 0, "gemma_model_calls_in_mock": 0,
    }
    if mode == "fixture":
        if fixture is None:
            raise ValueError("FIXTURE_REQUIRED")
        proposal = fixture
    else:
        if not endpoint or not model or record_dir is None:
            raise ValueError("LOCAL_GEMMA_MODEL_AND_RAW_RECORD_DIR_REQUIRED")
        instruction = K3G_SYSTEM_INSTRUCTION
        if soul_directive is not None:
            instruction = (
                "Stable identity value prior (not World evidence or Action authority): "
                + soul_directive + "\n" + instruction
            )
        try:
            proposal, raw = gemma_l2(
                source["evidence"], endpoint=endpoint, model=model,
                timeout=timeout, revision_context=_model_context(source),
                response_schema=choice_schema(),
                system_instruction=instruction, max_actions_allowed=10,
                record_dir=record_dir,
            )
            report["model_record"] = raw
        except ModelCallFailure as exc:
            report["model_record"] = exc.record
            report["validator_error"] = str(exc)
            report["stages"].append("L2_TEN_ACTION_CHOICE_ATTEMPTED")
            return report
        report["stages"].append("L2_TEN_ACTION_CHOICE_ATTEMPTED")
    report["proposal"] = proposal
    try:
        _independent_schema_check(proposal)
    except ValueError as exc:
        report["schema_validation"] = (
            "UNAVAILABLE" if str(exc) == "JSONSCHEMA_UNAVAILABLE" else "REJECTED"
        )
        report["validator_error"] = str(exc)
        return report
    report["schema_validation"] = "PASS"
    try:
        valid = validate_choice(proposal, evidence_ids=source["ids"])
    except ValueError as exc:
        report["validator_error"] = str(exc)
        return report
    report["stages"].append("PROPOSAL_VALIDATED")
    report["status"] = valid["status"]
    if valid["status"] == "ABSTAIN":
        report["stages"].append("EXPLICIT_ABSTENTION_ACCEPTED")
        return report
    if valid["status"] == "PROBE":
        report["stages"].append("PROBE_SELECTED_NOT_EXECUTED")
        return report
    new_skill = valid["skill"]
    old = source["old_skill"]
    policy_fields = (
        "version", "surface", "min_distance", "max_distance", "target_distance",
        "max_actions", "on_failure",
    )
    differences = [f for f in policy_fields if old[f] != new_skill[f]]
    report["execution_changed_fields"] = differences
    if not differences:
        report["stages"].append("NO_BEHAVIORAL_CHANGE")
        return report
    report["stages"].append("EXECUTION_SPEC_CHANGED")
    if not evaluate_skill:
        report["stages"].append("SKILL_HOLDOUT_SKIPPED_MATCHED_SOUL_COMPARISON")
        return report
    result = paired_evaluation(
        old, new_skill, evidence_ids=source["ids"], seed=evaluation_seed,
    )
    report["skill_holdout"] = result
    report["skill_holdout_seed"] = evaluation_seed
    report["stages"].append("PAIRED_MOCK_HOLDOUT_EVALUATED")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first", type=Path, required=True)
    p.add_argument("--k3b-report", type=Path, required=True)
    p.add_argument("--k3d-report", type=Path, required=True)
    p.add_argument("--k3e-report", type=Path, required=True)
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--fixture", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--record-dir", type=Path)
    p.add_argument("--evaluation-seed", type=int)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    source_paths = [a.first, a.k3b_report, a.k3d_report, a.k3e_report]
    original_manifest_audit = (
        verify_input_manifests(source_paths) if a.mode == "gemma" else None
    )
    src = [json.loads(path.read_text(encoding="utf-8")) for path in source_paths]
    fixture = json.loads(a.fixture.read_text(encoding="utf-8")) if a.fixture else None
    result = run_choice(
        *src, mode=a.mode, fixture=fixture, endpoint=a.endpoint,
        model=a.model, timeout=a.timeout, record_dir=a.record_dir,
        evaluation_seed=a.evaluation_seed,
    )
    if original_manifest_audit is not None:
        result["original_manifest_audit"] = original_manifest_audit
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
    print(f"{result['classification']} status={result['status']} "
          f"stages={result['stages']}")


if __name__ == "__main__":
    main()
