"""K3-E: L2 proposes a falsifiable probe, observes mock outcome, then revises its belief.

DEV-only isolated 1-D simulator; no Minecraft, S49, Learning/Habit writes or L0 install.
No simulation future is given to the model at proposal time. Stages call L2 separately.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_dev import (
    TARGET,
    MockIssuer,
    ModelCallFailure,
    WorldTrial,
    gemma_l2,
    skill_json_schema,
    validate_skill,
)
from experiments.skill_crystallization_k3c_dev import semantic_delta
from experiments.skill_crystallization_k3d_dev import _grounded_prior

# No K3-D unopened holdout (20261126) is accessed by this experiment.
FIXTURE_PROBE_SEED = 20261124
REAL_PROBE_SEED = 20261128
HYPOTHESES = ("START_MARGIN_SENSITIVE", "MOTION_EFFECT_CHANGED", "INDETERMINATE")
PROBES = ("START_MARGIN_PAIR", "MOTION_REGIME_PAIR", "NONE")
PATTERNS = ("A_SUCCEEDS_B_FAILS", "A_FAILS_B_SUCCEEDS", "BOTH_SUCCEED",
            "BOTH_FAIL", "UNKNOWN")


def proposal_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["PROBE", "ABSTAIN"]},
            "hypothesis": {"type": "string", "enum": list(HYPOTHESES)},
            "probe_id": {"type": "string", "enum": list(PROBES)},
            "prediction": {"type": "string", "enum": list(PATTERNS)},
            "reason": {"type": "string", "minLength": 1, "maxLength": 700},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "hypothesis", "probe_id", "prediction", "reason", "evidence_ids"],
    }


def update_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["UPDATE", "ABSTAIN"]},
            "hypothesis": {"type": "string", "enum": list(HYPOTHESES)},
            "reason": {"type": "string", "minLength": 1, "maxLength": 700},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "skill_candidate": {"anyOf": [skill_json_schema(), {"type": "null"}]},
        },
        "required": ["status", "hypothesis", "reason", "evidence_ids", "skill_candidate"],
    }


def _schema_check(value: object, schema: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise ValueError("JSONSCHEMA_UNAVAILABLE") from exc
    try:
        jsonschema.validate(value, schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"SCHEMA_INVALID: {exc.message}") from exc


def _evidence_ids(rows: list[dict[str, Any]]) -> set[str]:
    ids = [x["experience_id"] for x in rows]
    if any(type(x) is not str for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("EVIDENCE_SOURCE_DUPLICATE_OR_INVALID")
    return set(ids)


def _check_ids(ids: object, allowed: set[str], *, required: bool) -> None:
    if (not isinstance(ids, list) or (required and not ids)
            or any(type(x) is not str for x in ids)
            or len(set(ids)) != len(ids) or not set(ids) <= allowed):
        raise ValueError("UNSOURCED_EVIDENCE_ID")


def validate_probe(value: object, evidence: set[str]) -> dict[str, Any]:
    _schema_check(value, proposal_schema())
    assert isinstance(value, dict)
    if value["status"] == "ABSTAIN":
        if (value["probe_id"], value["prediction"], value["hypothesis"]) != (
            "NONE", "UNKNOWN", "INDETERMINATE"
        ):
            raise ValueError("ABSTAIN_MUST_NOT_SELECT_PROBE")
        _check_ids(value["evidence_ids"], evidence, required=False)
    else:
        pairing = {"START_MARGIN_SENSITIVE": "START_MARGIN_PAIR",
                   "MOTION_EFFECT_CHANGED": "MOTION_REGIME_PAIR"}
        if (pairing.get(value["hypothesis"]) != value["probe_id"]
                or value["prediction"] == "UNKNOWN"):
            raise ValueError("NON_DISCRIMINATING_OR_MISMATCHED_PROBE")
        _check_ids(value["evidence_ids"], evidence, required=True)
    return value


def validate_update(value: object, evidence: set[str]) -> dict[str, Any]:
    _schema_check(value, update_schema())
    assert isinstance(value, dict)
    _check_ids(value["evidence_ids"], evidence, required=value["status"] == "UPDATE")
    if value["status"] == "ABSTAIN" and value["skill_candidate"] is not None:
        raise ValueError("ABSTAIN_CANNOT_CREATE_SKILL")
    if value["skill_candidate"] is not None:
        validate_skill(value["skill_candidate"], evidence)
    return value


def _verified_context(first: dict[str, Any], k3b: dict[str, Any],
                      k3d: dict[str, Any]) -> dict[str, Any]:
    state = _grounded_prior(first, k3b)
    proposal = k3d.get("proposal")
    if (k3d.get("mode") != "gemma" or k3d.get("proposal_status") != "ABSTAIN"
            or k3d.get("schema_validation") != "PASS"
            or not isinstance(proposal, dict) or proposal.get("status") != "ABSTAIN"
            or proposal.get("skill", object()) is not None
            or not isinstance(proposal.get("reason"), str)
            or not proposal["reason"].strip()):
        raise ValueError("K3D_ABSTAIN_SOURCE_INVALID")
    evidence = state["training"] + state["shift_observations"]
    allowed = _evidence_ids(evidence)
    if not state["suspended"]:
        raise ValueError("OLD_SKILL_NOT_SUSPENDED")
    return {"old_skill": state["old_skill"], "evidence": evidence,
            "ids": allowed, "k3d_abstain_reason": proposal["reason"]}


def probe_protocols() -> dict[str, Any]:
    """Pre-register interventions without including physics or their outcomes."""
    return {
        "START_MARGIN_PAIR": {
            "question": "With the same changed-motion steps, does initial margin change Goal success?",
            "A_start": 2.32, "B_start": 2.44,
            "controlled": "identical four motion effects across A/B; changed-motion regime",
        },
        "MOTION_REGIME_PAIR": {
            "question": "At the same start, does changing the motion regime affect Goal success?",
            "A_start": 2.4, "B_start": 2.4,
            "controlled": "same sampled motion quantiles; reference vs changed regime",
        },
        "common": {"target_distance": TARGET, "max_actions_per_trial": 4,
                   "allowed_action": "MOVE_AWAY", "physical_world": False},
    }


def _make_probe_trials(probe_id: str, seed: int) -> list[WorldTrial]:
    if probe_id not in ("START_MARGIN_PAIR", "MOTION_REGIME_PAIR"):
        raise ValueError("UNKNOWN_PROBE")
    rng = random.Random(seed)
    u = [rng.random() for _ in range(4)]
    changed = tuple(0.18 + 0.05 * v for v in u)
    reference = tuple(0.59 + 0.08 * v for v in u)
    if probe_id == "START_MARGIN_PAIR":
        pairs = ((2.32, changed), (2.44, changed))
    else:
        pairs = ((2.4, reference), (2.4, changed))
    return [WorldTrial("normal", start, effects, f"k3e-{probe_id}-{seed}-{side}")
            for side, (start, effects) in zip(("A", "B"), pairs)]


def _observe(trial: WorldTrial, tag: str) -> dict[str, Any]:
    issuer = MockIssuer(trial)
    while issuer.actions < 4 and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    return {
        "experience_id": f"k3e-probe-{tag}", "source_session": trial.session,
        "surface_cue": "normal", "start_distance": trial.start,
        "observed_action": "MOVE_AWAY", "observed_trace": issuer.history,
        "outcome_success": issuer.distance >= TARGET, "target_distance": TARGET,
        "action_count": issuer.actions,
    }


def _outcome_pattern(a: bool, b: bool) -> str:
    if a and b:
        return "BOTH_SUCCEED"
    if not a and not b:
        return "BOTH_FAIL"
    return "A_SUCCEEDS_B_FAILS" if a else "A_FAILS_B_SUCCEEDS"


def execute_mock_probe(proposal: dict[str, Any], *, seed: int,
                       mock_grant: bool) -> dict[str, Any]:
    if mock_grant is not True:
        raise ValueError("PROBE_MOCK_GRANT_REQUIRED")
    if proposal.get("status") != "PROBE":
        raise ValueError("PROBE_PROPOSAL_REQUIRED")
    obs = [_observe(t, label) for label, t in zip(("A", "B"),
                                                  _make_probe_trials(proposal["probe_id"], seed))]
    total_actions = sum(row["action_count"] for row in obs)
    if total_actions > 8 or any(row["action_count"] > 4 for row in obs):
        raise ValueError("PROBE_ACTION_BUDGET_EXCEEDED")
    observed = _outcome_pattern(obs[0]["outcome_success"], obs[1]["outcome_success"])
    return {
        "probe_id": proposal["probe_id"], "seed": seed,
        "observations": obs, "observed_pattern": observed,
        "predicted_pattern": proposal["prediction"],
        "prediction_matches": observed == proposal["prediction"],
        "mock_actions": total_actions,
        "authority": "MOCK_TESTER_ONLY_NO_S49",
        "inference": "PAIR_OBSERVATION_ONLY_NOT_CAUSAL_IDENTIFICATION",
    }


def _invoke(evidence: list[dict[str, Any]], *, endpoint: str, model: str,
            schema: dict[str, Any], context: dict[str, Any],
            instruction: str, record_dir: Path | None, timeout: float):
    return gemma_l2(
        evidence, endpoint=endpoint, model=model, timeout=timeout,
        response_schema=schema, revision_context=context, record_dir=record_dir,
        system_instruction=instruction,
    )


def run_proposal(first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
                 *, mode: str, fixture: dict[str, Any] | None = None,
                 endpoint: str | None = None, model: str | None = None,
                 record_dir: Path | None = None, timeout: float = 300,
                 mock_grant: bool = True) -> dict[str, Any]:
    source = _verified_context(first, k3b, k3d)
    if mode not in ("fixture", "gemma"):
        raise ValueError("INVALID_MODE")
    report = {
        "classification": "DEV_ONLY_K3E_SYNTHETIC_NO_REAL_S49", "mode": mode,
        "status": "NOT_RUN", "proposal": None, "provider": None, "error": None,
        "probe": None, "stages": [], "holdout_20261126": "UNOPENED",
        "model_calls_in_mock_probe": 0,
    }
    if mode == "fixture":
        if fixture is None:
            raise ValueError("FIXTURE_REQUIRED")
        value = fixture
    else:
        if not endpoint or not model:
            raise ValueError("LOCAL_GEMMA_ENDPOINT_AND_MODEL_REQUIRED")
        context = {"prior_skill": source["old_skill"],
                   "k3d_abstain_reason": source["k3d_abstain_reason"],
                   "probe_protocols": probe_protocols(),
                   "objective": "Propose a falsifiable next observation or abstain. "
                   "Neither existing Skill optimality nor impossibility is established."}
        instruction = (
            "You are L2 doing investigation, not creating a Skill. Return only "
            "schema-compliant JSON. Choose PROBE with a source-grounded hypothesis, "
            "matching pre-registered probe and prediction, or ABSTAIN with "
            "hypothesis INDETERMINATE, probe_id NONE, prediction UNKNOWN. "
            "Do not invent World physics or future outcomes. Probe effects are hidden. "
            "Cite only provided experience IDs. Do not claim the old Skill is optimized."
        )
        try:
            value, raw = _invoke(source["evidence"], endpoint=endpoint, model=model,
                                 schema=proposal_schema(), context=context,
                                 instruction=instruction, record_dir=record_dir,
                                 timeout=timeout)
            report["provider"] = raw
        except ModelCallFailure as exc:
            report["provider"] = exc.record
            report["error"] = str(exc)
            report["stages"].append("L2_PROBE_PROPOSAL_ATTEMPTED")
            return report
        report["stages"].append("L2_PROBE_PROPOSAL_ATTEMPTED")
    report["proposal"] = value
    try:
        valid = validate_probe(value, source["ids"])
    except ValueError as exc:
        report["error"] = str(exc)
        return report
    report["status"] = valid["status"]
    report["stages"].append("PROPOSAL_VALIDATED")
    if valid["status"] == "ABSTAIN":
        report["stages"].append("PROBE_ABSTENTION_ACCEPTED")
        return report
    seed = FIXTURE_PROBE_SEED if mode == "fixture" else REAL_PROBE_SEED
    report["probe"] = execute_mock_probe(valid, seed=seed, mock_grant=mock_grant)
    report["stages"].append("MOCK_PROBE_OBSERVED")
    return report


def _verify_proposal_report(report: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    mode = report.get("mode")
    if mode not in ("fixture", "gemma") or report.get("status") != "PROBE":
        raise ValueError("VALID_PROBE_REPORT_REQUIRED")
    valid = validate_probe(report.get("proposal"), source["ids"])
    seed = FIXTURE_PROBE_SEED if mode == "fixture" else REAL_PROBE_SEED
    expected = execute_mock_probe(valid, seed=seed, mock_grant=True)
    if report.get("probe") != expected:
        raise ValueError("PROBE_OBSERVATION_SOURCE_MISMATCH")
    return expected


def run_reassessment(first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
                     proposal_report: dict[str, Any], *, mode: str,
                     fixture: dict[str, Any] | None = None,
                     endpoint: str | None = None, model: str | None = None,
                     record_dir: Path | None = None, timeout: float = 300) -> dict[str, Any]:
    source = _verified_context(first, k3b, k3d)
    probe = _verify_proposal_report(proposal_report, source)
    if mode not in ("fixture", "gemma"):
        raise ValueError("INVALID_MODE")
    if mode != proposal_report["mode"]:
        raise ValueError("MIXED_PROVENANCE_MODES")
    observations = probe["observations"]
    evidence = source["evidence"] + observations
    allowed = _evidence_ids(evidence)
    report = {
        "classification": "DEV_ONLY_K3E_REASSESSMENT_NO_REAL_S49", "mode": mode,
        "status": "NOT_RUN", "update": None, "provider": None, "error": None,
        "semantic_delta": None, "stages": [], "holdout_20261126": "UNOPENED",
        "skill_execution": "NOT_RUN", "new_skill_installed": False,
    }
    if mode == "fixture":
        if fixture is None:
            raise ValueError("FIXTURE_REQUIRED")
        value = fixture
    else:
        if not endpoint or not model:
            raise ValueError("LOCAL_GEMMA_ENDPOINT_AND_MODEL_REQUIRED")
        context = {
            "prior_skill": source["old_skill"],
            "prior_hypothesis": proposal_report["proposal"],
            "observed_probe_pattern": probe["observed_pattern"],
            "prediction_matches": probe["prediction_matches"],
            "objective": "Revise or retain the hypothesis using only the new observed pair. "
            "A typed Skill candidate is optional and must satisfy the existing 1..4 budget.",
        }
        instruction = (
            "You are L2 after a controlled mock observation. Return JSON only. "
            "Choose UPDATE to state your current hypothesis, or ABSTAIN if inconclusive. "
            "Cite only available experience IDs. You may supply an optional typed Skill "
            "candidate but do not claim autonomous installation or proven optimality. "
            "Do not invent observations or infer hidden physics as established fact."
        )
        try:
            value, raw = _invoke(evidence, endpoint=endpoint, model=model,
                                 schema=update_schema(), context=context,
                                 instruction=instruction, record_dir=record_dir,
                                 timeout=timeout)
            report["provider"] = raw
        except ModelCallFailure as exc:
            report["provider"] = exc.record
            report["error"] = str(exc)
            report["stages"].append("L2_REASSESSMENT_ATTEMPTED")
            return report
        report["stages"].append("L2_REASSESSMENT_ATTEMPTED")
    report["update"] = value
    try:
        valid = validate_update(value, allowed)
    except ValueError as exc:
        report["error"] = str(exc)
        return report
    report["status"] = valid["status"]
    report["stages"].append("REASSESSMENT_VALIDATED")
    if valid["skill_candidate"] is not None:
        report["semantic_delta"] = semantic_delta(source["old_skill"],
                                                   valid["skill_candidate"])
        report["stages"].append("SKILL_CANDIDATE_ONLY_NOT_EXECUTED")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=("propose", "reassess"), required=True)
    p.add_argument("--mode", choices=("fixture", "gemma"), required=True)
    p.add_argument("--first", type=Path, required=True)
    p.add_argument("--k3b-report", type=Path, required=True)
    p.add_argument("--k3d-report", type=Path, required=True)
    p.add_argument("--proposal-report", type=Path)
    p.add_argument("--fixture", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--record-dir", type=Path)
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    first = json.loads(a.first.read_text(encoding="utf-8"))
    k3b = json.loads(a.k3b_report.read_text(encoding="utf-8"))
    k3d = json.loads(a.k3d_report.read_text(encoding="utf-8"))
    fixture = json.loads(a.fixture.read_text(encoding="utf-8")) if a.fixture else None
    if a.phase == "propose":
        result = run_proposal(first, k3b, k3d, mode=a.mode, fixture=fixture,
                              endpoint=a.endpoint, model=a.model, timeout=a.timeout,
                              record_dir=a.record_dir)
    else:
        if a.proposal_report is None:
            raise ValueError("PROPOSAL_REPORT_REQUIRED")
        prior = json.loads(a.proposal_report.read_text(encoding="utf-8"))
        result = run_reassessment(first, k3b, k3d, prior, mode=a.mode,
                                  fixture=fixture, endpoint=a.endpoint, model=a.model,
                                  timeout=a.timeout, record_dir=a.record_dir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{result['classification']} status={result['status']} out={a.out}")


if __name__ == "__main__":
    main()
