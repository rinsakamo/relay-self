"""K3-H: optional-prediction L2 trial -> mock outcome -> L2 reflection.

DEV synthetic world only: no native S49, no Skill installation, no Learning/
Habit writes. Each Gemma call is explicit, one-shot, reason OFF, strict JSON.
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
    gemma_l2,
    outcome,
)
from experiments.skill_crystallization_k3e_dev import _check_ids, _schema_check
from experiments.skill_crystallization_k3f_budget_dev import (
    budget10_schema,
    validate_budget10_shadow,
)
from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    verified_context,
    verify_input_manifests,
)

DECISIONS = ("TRY_MOVE", "COMPARE_ARMS", "OBSERVE_ONLY", "DEFER")
PREDICTIONS = (
    "UNKNOWN", "GOAL_REACHED", "GOAL_NOT_REACHED",
    "A_SUCCEEDS_B_FAILS", "A_FAILS_B_SUCCEEDS", "BOTH_SUCCEED", "BOTH_FAIL",
)
NEXT_OPTIONS = DECISIONS
FIXTURE_SEED = 20261217  # Offline exploratory, permanently exposed by tests.
NEW_MODEL_TRIAL_SEED = 20261219  # Do not consume until real valid model proposal.
PREVIOUS_RESERVED_SEEDS = frozenset({20261126, 20261205, 20261213})
ARM_START = 2.4
ARM_DESCRIPTIONS = {
    "A": "normal surface, reference movement regime, initial distance 2.4m",
    "B": "normal surface, possible changed movement regime, initial distance 2.4m",
}


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _source_fingerprint(source: dict[str, Any]) -> str:
    """Bind both observed experiences and the suspended Skill/prior decision context."""
    return _canonical_sha({
        "old_skill": source["old_skill"],
        "evidence": source["evidence"],
        "prior_decisions": source["prior_decisions"],
    })


def proposal_schema() -> dict[str, Any]:
    """Predicting an outcome is OPTIONAL. Only an executable bounded envelope is required."""
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "decision": {"type": "string", "enum": list(DECISIONS)},
            "arm": {"type": "string", "enum": ["A", "B", "NONE"]},
            "max_actions_per_arm": {"type": "integer", "enum": list(range(11))},
            "prediction": {"type": "string", "enum": list(PREDICTIONS)},
            "reason": {"type": "string", "minLength": 1, "maxLength": 800},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "decision", "arm", "max_actions_per_arm", "prediction", "reason",
            "evidence_ids",
        ],
    }


def validate_proposal(value: object, ids: set[str]) -> dict[str, Any]:
    _schema_check(value, proposal_schema())
    assert isinstance(value, dict)
    _check_ids(value["evidence_ids"], ids, required=False)
    mode = value["decision"]
    arm = value["arm"]
    budget = value["max_actions_per_arm"]
    pred = value["prediction"]
    if type(budget) is not int:
        raise ValueError("ACTION_BUDGET_INVALID")
    if mode == "TRY_MOVE":
        if (arm not in ("A", "B") or budget < 1
                or pred not in ("UNKNOWN", "GOAL_REACHED", "GOAL_NOT_REACHED")):
            raise ValueError("TRY_MOVE_ENVELOPE_INVALID")
    elif mode == "COMPARE_ARMS":
        if (arm != "NONE" or budget < 1
                or pred in ("GOAL_REACHED", "GOAL_NOT_REACHED")):
            raise ValueError("COMPARE_ARMS_ENVELOPE_INVALID")
    elif (arm != "NONE" or budget != 0 or pred != "UNKNOWN"):
        raise ValueError("NON_ACTION_ENVELOPE_INVALID")
    return value


def reflection_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "next_decision": {"type": "string", "enum": list(NEXT_OPTIONS)},
            "understanding": {"type": "string", "minLength": 1, "maxLength": 900},
            "skill": {"anyOf": [budget10_schema(), {"type": "null"}]},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["next_decision", "understanding", "skill", "evidence_ids"],
    }


def validate_reflection(value: object, ids: set[str]) -> dict[str, Any]:
    _schema_check(value, reflection_schema())
    assert isinstance(value, dict)
    _check_ids(value["evidence_ids"], ids, required=value["skill"] is not None)
    if value["skill"] is not None:
        validate_budget10_shadow(value["skill"], ids)
    return value


K3H_PROPOSAL_INSTRUCTION = (
    "You are L2. Return only JSON matching the supplied strict Schema. "
    "Choose freely whether to TRY_MOVE, COMPARE_ARMS, OBSERVE_ONLY, or DEFER. "
    "Do not choose a mode because it is expected by the experimenter. "
    "The maximum is 10 MOVE_AWAY Actions per arm; Goal means immediate stop. "
    "Prediction UNKNOWN is VALID and does not mean your proposed trial is bad. "
    "If you have a specific prediction, record it prospectively. "
    "Do not invent past experience, unobserved physics, new Action authority, "
    "or a prediction after reading the trial result."
)


def verify_model_proposal_record(report: dict[str, Any],
                                 source: dict[str, Any]) -> None:
    """Source self-consistency only, not independent provider authentication."""
    raw = report.get("provider_record")
    if (not isinstance(raw, dict) or raw.get("http_status") != 200
            or raw.get("finish_reason") != "stop"
            or raw.get("reasoning_content")):
        raise ValueError("REAL_MODEL_SOURCE_UNATTESTED")
    req, resp = raw.get("request"), raw.get("response_raw")
    if not isinstance(req, dict) or not isinstance(resp, str):
        raise ValueError("REAL_MODEL_SOURCE_UNATTESTED")
    try:
        request_sha = hashlib.sha256(
            json.dumps(req, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if request_sha != raw.get("request_sha256"):
            raise ValueError("REQUEST_RAW_SHA_MISMATCH")
        if (req["reasoning_effort"] != "none"
                or req["cache_prompt"] is not False
                or req["temperature"] != 0
                or req["response_format"]["json_schema"]["strict"] is not True
                or req["response_format"]["json_schema"]["schema"]
                != proposal_schema()
                or req["messages"][0]["content"] != K3H_PROPOSAL_INSTRUCTION):
            raise ValueError("PROPOSAL_WIRE_CONTRACT_MISMATCH")
        user = json.loads(req["messages"][1]["content"])
        if (user["train_experiences"] != source["evidence"]
                or user["maximum_actions"] != 10
                or user["revision_context"] != _public_context(source)):
            raise ValueError("MODEL_PROPOSAL_INPUT_NOT_ORIGINAL")
        response = json.loads(resp)["choices"][0]
        if (response["finish_reason"] != "stop"
                or response["message"].get("reasoning_content")
                or json.loads(response["message"]["content"]) != report["proposal"]):
            raise ValueError("MODEL_PROPOSAL_NOT_RAW_RESPONSE")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("REAL_MODEL_PROPOSAL_SOURCE_MISMATCH") from exc


def _public_context(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "old_skill": source["old_skill"],
        "old_skill_state": "SUSPENDED_FROM_PREVIOUS_FAILURES",
        "candidate_worlds": ARM_DESCRIPTIONS,
        "goal_distance": TARGET,
        "max_actions_per_arm": 10,
        "stopping_rule": "Stop immediately on Goal; never exceed your proposed budget.",
        "allowed_experiments": {
            "TRY_MOVE": "Select A or B and try 1..10 MOVE_AWAY actions maximum.",
            "COMPARE_ARMS": "Compare A/B, each with the same proposed 1..10 Action cap.",
            "OBSERVE_ONLY": "Read current initial cue without moving; no new outcome.",
            "DEFER": "Do not perform a new observation or Action.",
        },
        "decision": (
            "Choose what you want to try next, or do nothing. A prediction is optional: "
            "UNKNOWN is a valid answer. A reason may be provisional. Do not claim hidden "
            "movement effects are known. Your proposal grants no real Action authority."
        ),
    }


def _source_ids(first: dict[str, Any], k3b: dict[str, Any],
                k3d: dict[str, Any], k3e: dict[str, Any]) -> dict[str, Any]:
    return verified_context(first, k3b, k3d, k3e)


def run_proposal(
    first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
    k3e: dict[str, Any], *, mode: str, fixture: dict[str, Any] | None = None,
    endpoint: str | None = None, model: str | None = None, timeout: float = 300,
    record_dir: Path | None = None,
) -> dict[str, Any]:
    source = _source_ids(first, k3b, k3d, k3e)
    if mode not in ("fixture", "gemma"):
        raise ValueError("UNKNOWN_MODE")
    report = {
        "classification": "DEV_ONLY_K3H_FREE_CHOICE_PROPOSAL",
        "mode": mode, "source_fingerprint": _source_fingerprint(source),
        "proposal": None, "schema_validation": "NOT_RUN",
        "semantic_validation": "NOT_RUN", "validator_error": None,
        "provider_record": None, "stages": [], "new_experiences": [],
        "mock_actions": 0, "native_s49_actions": 0, "skill_installed": False,
        "protected_seeds": {str(seed): "UNOPENED" for seed in
                            sorted(PREVIOUS_RESERVED_SEEDS)},
    }
    if mode == "fixture":
        if fixture is None:
            raise ValueError("FIXTURE_REQUIRED")
        proposal = fixture
    else:
        if not endpoint or not model or record_dir is None:
            raise ValueError("LOCAL_MODEL_AND_RAW_RECORD_DIR_REQUIRED")
        instruction = K3H_PROPOSAL_INSTRUCTION
        try:
            proposal, record = gemma_l2(
                source["evidence"], endpoint=endpoint, model=model,
                timeout=timeout, response_schema=proposal_schema(),
                system_instruction=instruction, max_actions_allowed=10,
                revision_context=_public_context(source), record_dir=record_dir,
            )
            report["provider_record"] = record
        except ModelCallFailure as exc:
            report["provider_record"] = exc.record
            report["validator_error"] = str(exc)
            report["stages"].append("MODEL_PROPOSAL_ATTEMPTED")
            return report
        report["stages"].append("MODEL_PROPOSAL_ATTEMPTED")
    report["proposal"] = proposal
    try:
        _schema_check(proposal, proposal_schema())
    except ValueError as exc:
        report["schema_validation"] = (
            "UNAVAILABLE" if "JSONSCHEMA_UNAVAILABLE" in str(exc)
            else "REJECTED"
        )
        report["validator_error"] = str(exc)
        return report
    report["schema_validation"] = "PASS"
    try:
        valid = validate_proposal(proposal, source["ids"])
    except ValueError as exc:
        report["semantic_validation"] = "REJECTED"
        report["validator_error"] = str(exc)
        return report
    report["semantic_validation"] = "PASS"
    report["stages"].append("VALID_BOUNDED_CHOICE")
    report["chosen_decision"] = valid["decision"]
    return report


def _make_arms(seed: int) -> dict[str, WorldTrial]:
    rng = random.Random(seed)
    quantiles = [rng.random() for _ in range(10)]
    return {
        "A": WorldTrial(
            "normal", ARM_START, tuple(0.59 + 0.08 * x for x in quantiles),
            f"k3h-{seed}-A",
        ),
        "B": WorldTrial(
            "normal", ARM_START, tuple(0.18 + 0.05 * x for x in quantiles),
            f"k3h-{seed}-B",
        ),
    }


def _observe(trial: WorldTrial, *, budget: int, arm: str) -> dict[str, Any]:
    issuer = MockIssuer(trial)
    while issuer.actions < budget and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    measured = outcome(issuer)
    return {
        "experience_id": f"k3h-experience-{arm}", "source_session": trial.session,
        "surface_cue": trial.surface, "start_distance": trial.start,
        "observed_action": "MOVE_AWAY", "goal_distance": TARGET,
        "action_count": measured["action_count"],
        "observed_trace": measured["trace"],
        "final_distance": measured["final_distance"],
        "outcome_success": measured["success"],
        "observation_kind": "FRESH_MOCK_ACTION_OUTCOME",
    }


def execute_mock(
    proposal_report: dict[str, Any], source: dict[str, Any], *,
    mock_grant: bool, result_mode: str,
) -> dict[str, Any]:
    if mock_grant is not True:
        raise ValueError("EXPLICIT_DEV_MOCK_GRANT_REQUIRED")
    if proposal_report.get("source_fingerprint") != _source_fingerprint(source):
        raise ValueError("PROPOSAL_SOURCE_MISMATCH")
    proposal = validate_proposal(proposal_report.get("proposal"), source["ids"])
    if ("VALID_BOUNDED_CHOICE" not in proposal_report.get("stages", [])
            or proposal_report.get("schema_validation") != "PASS"
            or proposal_report.get("semantic_validation") != "PASS"):
        raise ValueError("UNADMITTED_PROPOSAL")
    if result_mode not in ("fixture", "gemma") or result_mode != proposal_report["mode"]:
        raise ValueError("PROPOSAL_MODE_MISMATCH")
    seed = FIXTURE_SEED if result_mode == "fixture" else NEW_MODEL_TRIAL_SEED
    if seed in PREVIOUS_RESERVED_SEEDS:
        raise ValueError("PROTECTED_SEED")
    if result_mode == "gemma":
        verify_model_proposal_record(proposal_report, source)
    report = {
        "classification": "DEV_ONLY_K3H_NEW_MOCK_EXPERIENCE",
        "proposal_fingerprint": _canonical_sha(proposal_report),
        "source_fingerprint": proposal_report["source_fingerprint"],
        "proposal": proposal, "mode": result_mode, "mock_seed": None,
        "new_experiences": [], "mock_actions": 0, "native_s49_actions": 0,
        "skill_installed": False, "stages": [],
        "protected_seeds": {str(x): "UNOPENED" for x in sorted(PREVIOUS_RESERVED_SEEDS)},
    }
    if proposal["decision"] == "DEFER":
        report["stages"].append("DEFER_NO_NEW_EXPERIENCE")
        return report
    if proposal["decision"] == "OBSERVE_ONLY":
        report["new_experiences"] = [{
            "experience_id": "k3h-cue-read-only",
            "surface_cue": "normal", "start_distance": ARM_START,
            "outcome_success": None, "action_count": 0,
            "observation_kind": "INITIAL_CUE_ONLY_NO_NEW_OUTCOME",
        }]
        report["stages"].append("READ_ONLY_CUE_OBSERVED")
        return report
    arms = _make_arms(seed)
    selected = (
        (proposal["arm"],) if proposal["decision"] == "TRY_MOVE" else ("A", "B")
    )
    observed = [
        _observe(arms[arm], budget=proposal["max_actions_per_arm"], arm=arm)
        for arm in selected
    ]
    if any(o["action_count"] > proposal["max_actions_per_arm"] for o in observed):
        raise ValueError("MOCK_ACTION_BUDGET_EXCEEDED")
    report["mock_seed"] = seed
    report["new_experiences"] = observed
    report["mock_actions"] = sum(o["action_count"] for o in observed)
    report["stages"].append("FRESH_BOUNDED_MOCK_OUTCOME_OBSERVED")
    report["predicted_pattern"] = proposal["prediction"]
    report["prediction_assessment"] = (
        "NOT_PREDECLARED" if proposal["prediction"] == "UNKNOWN"
        else "PREDICTION_RECORDED_BUT_NOT_AUTOMATICALLY_SCIENCE_VALIDATED"
    )
    return report


def run_reflection(
    first: dict[str, Any], k3b: dict[str, Any], k3d: dict[str, Any],
    k3e: dict[str, Any], *, proposal_report: dict[str, Any],
    outcome_report: dict[str, Any], mode: str,
    fixture: dict[str, Any] | None = None, endpoint: str | None = None,
    model: str | None = None, record_dir: Path | None = None,
    timeout: float = 300,
) -> dict[str, Any]:
    source = _source_ids(first, k3b, k3d, k3e)
    if mode not in ("fixture", "gemma"):
        raise ValueError("UNKNOWN_MODE")
    if (outcome_report.get("proposal_fingerprint") != _canonical_sha(proposal_report)
            or outcome_report.get("source_fingerprint") != _source_fingerprint(
                source
            ) or outcome_report.get("mode") != mode
            or outcome_report.get("native_s49_actions") != 0):
        raise ValueError("OUTCOME_CHAIN_SOURCE_MISMATCH")
    if not isinstance(outcome_report.get("new_experiences"), list):
        raise ValueError("NEW_EXPERIENCES_NOT_RECORDED")
    # Independently rebuild the deterministic DEV mock outcome from the
    # original source-qualified proposal. Never accept a fabricated experience.
    expected = execute_mock(
        proposal_report, source, mock_grant=True, result_mode=mode,
    )
    audited = {
        key: value for key, value in outcome_report.items()
        if key not in ("original_manifest_audit", "original_source_sha256")
    }
    if audited != expected:
        raise ValueError("NEW_MOCK_OUTCOME_NOT_REPRODUCIBLE")
    if "DEFER_NO_NEW_EXPERIENCE" in outcome_report.get("stages", []):
        raise ValueError("NO_EXPERIENCE_FOR_REFLECTION")
    observations = outcome_report["new_experiences"]
    new_ids = {o.get("experience_id") for o in observations}
    if (len(observations) not in (1, 2) or len(new_ids) != len(observations)
            or any(type(x) is not str for x in new_ids)
            or any(o.get("observation_kind") not in (
                "FRESH_MOCK_ACTION_OUTCOME", "INITIAL_CUE_ONLY_NO_NEW_OUTCOME"
            ) for o in observations)):
        raise ValueError("INVALID_NEW_OBSERVATION")
    report = {
        "classification": "DEV_ONLY_K3H_L2_REFLECTION",
        "mode": mode, "proposal_fingerprint": _canonical_sha(proposal_report),
        "outcome_fingerprint": _canonical_sha(outcome_report),
        "provider_record": None, "reflection": None, "schema_validation": "NOT_RUN",
        "semantic_validation": "NOT_RUN", "validator_error": None,
        "stages": [], "skill_installed": False,
        "skill_evaluated": False, "native_s49_actions": 0, "mock_actions": 0,
    }
    evidence = source["evidence"] + observations
    available = source["ids"] | new_ids
    if mode == "fixture":
        if fixture is None:
            raise ValueError("FIXTURE_REQUIRED")
        reflection = fixture
    else:
        if not endpoint or not model or record_dir is None:
            raise ValueError("LOCAL_MODEL_AND_RAW_RECORD_DIR_REQUIRED")
        instruction = (
            "You are L2. A new mock observation has occurred following your "
            "previously saved bounded proposal. Consider what it means and choose "
            "a next decision. You may propose an optional conditional Skill, but "
            "no Skill must be proposed and nothing is automatically installed. "
            "Do not invent unobserved outcomes or identify synthetic mock physics "
            "as real World truth. Return only the supplied strict JSON Schema."
        )
        try:
            reflection, provider = gemma_l2(
                evidence, endpoint=endpoint, model=model, timeout=timeout,
                revision_context={
                    "previous_proposal": proposal_report["proposal"],
                    "new_observations": observations,
                    "source_scope": "DEV_MOCK_ONLY_NOT_REAL_WORLD",
                    "next_action_authority": "NO_REAL_ACTION_ADMISSION",
                },
                response_schema=reflection_schema(),
                system_instruction=instruction, max_actions_allowed=10,
                record_dir=record_dir,
            )
            report["provider_record"] = provider
        except ModelCallFailure as exc:
            report["provider_record"] = exc.record
            report["validator_error"] = str(exc)
            report["stages"].append("MODEL_REFLECTION_ATTEMPTED")
            return report
        report["stages"].append("MODEL_REFLECTION_ATTEMPTED")
    report["reflection"] = reflection
    try:
        _schema_check(reflection, reflection_schema())
    except ValueError as exc:
        report["schema_validation"] = (
            "UNAVAILABLE" if "JSONSCHEMA_UNAVAILABLE" in str(exc)
            else "REJECTED"
        )
        report["validator_error"] = str(exc)
        return report
    report["schema_validation"] = "PASS"
    try:
        validate_reflection(reflection, available)
    except ValueError as exc:
        report["semantic_validation"] = "REJECTED"
        report["validator_error"] = str(exc)
        return report
    report["semantic_validation"] = "PASS"
    report["stages"].append("VALID_REFLECTION_CANDIDATE_ONLY")
    if reflection["skill"] is not None:
        report["stages"].append("TENTATIVE_SKILL_NOT_EVALUATED_OR_INSTALLED")
    return report


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=("propose", "execute-mock", "reflect"), required=True)
    p.add_argument("--mode", choices=("fixture", "gemma"), required=True)
    for name in ("first", "k3b-report", "k3d-report", "k3e-report"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--fixture", type=Path)
    p.add_argument("--proposal-report", type=Path)
    p.add_argument("--outcome-report", type=Path)
    p.add_argument("--mock-grant", action="store_true")
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--record-dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    paths = [args.first, args.k3b_report, args.k3d_report, args.k3e_report]
    audit = verify_input_manifests(paths) if args.mode == "gemma" else None
    originals = [_read_json(x) for x in paths]
    fixture = _read_json(args.fixture) if args.fixture is not None else None
    if args.phase == "propose":
        result = run_proposal(
            *originals, mode=args.mode, fixture=fixture, endpoint=args.endpoint,
            model=args.model, timeout=args.timeout, record_dir=args.record_dir,
        )
    elif args.phase == "execute-mock":
        if args.proposal_report is None:
            raise ValueError("PROPOSAL_REPORT_REQUIRED")
        source = _source_ids(*originals)
        result = execute_mock(
            _read_json(args.proposal_report), source,
            mock_grant=args.mock_grant, result_mode=args.mode,
        )
    else:
        if args.proposal_report is None or args.outcome_report is None:
            raise ValueError("PROPOSAL_AND_OUTCOME_REPORT_REQUIRED")
        result = run_reflection(
            *originals, proposal_report=_read_json(args.proposal_report),
            outcome_report=_read_json(args.outcome_report),
            mode=args.mode, fixture=fixture, endpoint=args.endpoint,
            model=args.model, record_dir=args.record_dir, timeout=args.timeout,
        )
    if audit is not None:
        result["original_manifest_audit"] = audit
    result["original_source_sha256"] = {
        label: hashlib.sha256(path.read_bytes()).hexdigest()
        for label, path in zip(("first", "k3b", "k3d", "k3e"), paths)
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(result["classification"], result["stages"])


if __name__ == "__main__":
    main()
