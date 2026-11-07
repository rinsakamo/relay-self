"""DEV-only: observed experience -> typed L2 skill -> bounded L0 mock executor.

No Minecraft, no S49 integration, no persistent Learning/Habit writes.
Use --mode gemma only with an explicitly running local llama.cpp server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET = 3.2
TRAIN_N = 16
VALID_N = 16
HOLDOUT_N = 32
SHIFT_N = 16
DEFAULT_SEED = 20261108
FIELDS = (
    "version", "skill_id", "surface", "min_distance", "max_distance",
    "target_distance", "max_actions", "on_failure", "evidence_ids",
)


@dataclass(frozen=True)
class WorldTrial:
    surface: str
    start: float
    effects: tuple[float, ...]
    session: str


@dataclass(frozen=True)
class Cue:
    surface: str | None
    distance: float
    session: str
    sequence: int
    valid_until: int
    coverage_complete: bool = True


class ModelCallFailure(RuntimeError):
    """Preserve failed HTTP/protocol evidence rather than discarding the raw reply."""

    def __init__(self, message: str, record: dict[str, Any]) -> None:
        super().__init__(message)
        self.record = record


class MockIssuer:
    """Deliberately NOT the actual S49; one bounded move at a time."""

    def __init__(self, trial: WorldTrial) -> None:
        self.trial = trial
        self.distance = trial.start
        self.actions = 0
        self.history = [round(trial.start, 6)]

    def move_away(self, *, session: str) -> float:
        if session != self.trial.session:
            raise ValueError("WRONG_SESSION")
        if self.actions >= len(self.trial.effects):
            raise ValueError("MISSING_PHYSICAL_OUTCOME")
        self.distance += self.trial.effects[self.actions]
        self.actions += 1
        self.history.append(round(self.distance, 6))
        return self.distance


def make_trials(seed: int, n: int, *, phase: str, shift: bool = False) -> list[WorldTrial]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        surface = "ice" if (shift or i % 2 == 0) else "normal"
        # The evaluator knows hidden physics; the L2 input never includes these ranges.
        if surface == "normal":
            low, high = 0.59, 0.67
        else:
            low, high = (0.18, 0.23) if shift else (0.35, 0.40)
        start = rng.uniform(2.26, 2.46) if phase == "train" else rng.uniform(2.12, 2.52)
        effects = tuple(rng.uniform(low, high) for _ in range(5))
        rows.append(WorldTrial(surface, start, effects, f"{phase}-{i:03}"))
    return rows


def cue_for(
    trial: WorldTrial, *, stale: bool = False, unknown: bool = False,
    wrong_session: bool = False,
) -> Cue:
    return Cue(
        None if unknown else trial.surface, trial.start,
        "other-session" if wrong_session else trial.session, 10, 9 if stale else 11,
    )


def run_baseline(trial: WorldTrial) -> dict[str, Any]:
    issuer = MockIssuer(trial)
    while issuer.actions < 2 and issuer.distance < TARGET:
        issuer.move_away(session=trial.session)
    return outcome(issuer)


def outcome(issuer: MockIssuer) -> dict[str, Any]:
    return {
        "success": issuer.distance >= TARGET,
        "action_count": issuer.actions,
        "final_distance": round(issuer.distance, 6),
        "trace": issuer.history,
    }


def observed_training(trials: list[WorldTrial]) -> list[dict[str, Any]]:
    """One attempted-Intent proxy per row; only effects observed during issued actions."""
    rows = []
    for index, trial in enumerate(trials):
        observed = run_baseline(trial)
        rows.append({
            "experience_id": f"train-experience-{index:03}",
            "source_session": trial.session,
            "surface_cue": trial.surface,
            "start_distance": round(trial.start, 6),
            "observed_action": "MOVE_AWAY",
            "observed_trace": observed["trace"],
            "outcome_success": observed["success"],
            "target_distance": TARGET,
        })
    return rows


def skill_json_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "version": {"type": "integer", "enum": [1]},
            "skill_id": {"type": "string"},
            "surface": {"type": "string", "enum": ["ice", "normal"]},
            "min_distance": {"type": "number"},
            "max_distance": {"type": "number"},
            "target_distance": {"type": "number"},
            "max_actions": {"type": "integer"},
            "on_failure": {"type": "string", "enum": ["ESCALATE"]},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": list(FIELDS),
    }


def validate_skill(spec: object, evidence_ids: set[str]) -> dict[str, Any]:
    """Fail closed; neither JSON schema nor LLM text is trusted as authority."""
    if not isinstance(spec, dict) or set(spec) != set(FIELDS):
        raise ValueError("DSL_FIELDS_INVALID")
    if type(spec["version"]) is not int or spec["version"] != 1:
        raise ValueError("DSL_VERSION_INVALID")
    if not isinstance(spec["skill_id"], str) or not (1 <= len(spec["skill_id"]) <= 64):
        raise ValueError("SKILL_ID_INVALID")
    if spec["surface"] not in ("ice", "normal") or not isinstance(spec["surface"], str):
        raise ValueError("SURFACE_INVALID")
    for field in ("min_distance", "max_distance", "target_distance"):
        v = spec[field]
        if type(v) not in (int, float) or not math.isfinite(v):
            raise ValueError("BOUNDS_NOT_FINITE")
    if not (0 <= spec["min_distance"] < spec["max_distance"] <= TARGET
            and spec["target_distance"] == TARGET):
        raise ValueError("BOUNDS_INVALID")
    if type(spec["max_actions"]) is not int or not 1 <= spec["max_actions"] <= 4:
        raise ValueError("ACTION_BUDGET_INVALID")
    if spec["on_failure"] != "ESCALATE":
        raise ValueError("NO_ESCALATION_PATH")
    ids = spec["evidence_ids"]
    if (not isinstance(ids, list) or not ids
            or any(not isinstance(i, str) for i in ids)
            or len(ids) != len(set(ids))):
        raise ValueError("EVIDENCE_INVALID")
    if any(not isinstance(i, str) or i not in evidence_ids for i in ids):
        raise ValueError("EVIDENCE_NOT_TRAINING_SOURCED")
    return spec


def applicable(spec: dict[str, Any], cue: Cue, trial: WorldTrial) -> bool:
    return bool(
        cue.coverage_complete and cue.surface == spec["surface"]
        and cue.session == trial.session and cue.sequence <= cue.valid_until
        and type(cue.distance) in (int, float) and math.isfinite(cue.distance)
        and cue.distance == trial.start
        and spec["min_distance"] <= cue.distance < spec["max_distance"]
    )


def run_skill(spec: dict[str, Any], trial: WorldTrial, cue: Cue) -> dict[str, Any]:
    # Runtime bounds also apply to direct invocations, not just preflight validators.
    budget = spec.get("max_actions")
    if type(budget) is not int or not 1 <= budget <= 4 or spec.get("target_distance") != TARGET:
        raise ValueError("INVALID_RUNTIME_SKILL")
    if not applicable(spec, cue, trial):
        raise ValueError("NO_MATCH_OR_STALE_SOURCE")
    issuer = MockIssuer(trial)
    while issuer.distance < spec["target_distance"] and issuer.actions < spec["max_actions"]:
        issuer.move_away(session=cue.session)
    return outcome(issuer)


def proxy_l2(training: list[dict[str, Any]]) -> dict[str, Any]:
    """Transparent non-LLM stand-in, NOT an empirical L2 result."""
    ice = [e for e in training if e["surface_cue"] == "ice"]
    deltas = [b - a for e in ice for a, b in zip(e["observed_trace"], e["observed_trace"][1:])]
    conservative = min(deltas)
    min_start = min(e["start_distance"] for e in ice)
    budget = math.ceil((TARGET - min_start) / conservative)
    return {
        "version": 1, "skill_id": "PROXY_EVADE_ICE_V1", "surface": "ice",
        "min_distance": 0.0, "max_distance": TARGET, "target_distance": TARGET,
        "max_actions": min(budget, 4), "on_failure": "ESCALATE",
        "evidence_ids": [e["experience_id"] for e in ice],
    }


def gemma_l2(training: list[dict[str, Any]], *, endpoint: str, model: str,
             timeout: float, revision_context: dict[str, Any] | None = None,
             ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Exactly one explicitly requested HTTP call; no retries or World actions."""
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.path != "/v1/chat/completions" or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("LOCAL_ENDPOINT_REQUIRED")
    req_body = {
        "model": model, "temperature": 0, "max_tokens": 768,
        "reasoning_effort": "none", "cache_prompt": False,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "relay_self_skill_v1", "strict": True, "schema": skill_json_schema(),
        }},
        "messages": [
            {"role": "system", "content": (
                "You are proposing ONE tentative low-cost, bounded MOVE_AWAY skill from observed "
                "world experiences. Return only JSON matching the schema. Input outcomes are "
                "observations, not the simulator physics. Choose an applicability scope, 1..4 "
                "moves and evidence_ids from the input. A successful proposal need not be "
                "general. No code, no new actions, no guesses of future measurements."
            )},
            {"role": "user", "content": json.dumps({
                "allowed_action": "MOVE_AWAY", "maximum_actions": 4, "target_distance": TARGET,
                "train_experiences": training,
                **({"revision_context": revision_context} if revision_context else {}),
            }, sort_keys=True, separators=(",", ":"))},
        ],
    }
    serialized = json.dumps(req_body, separators=(",", ":"), ensure_ascii=False).encode()
    request_sha = hashlib.sha256(serialized).hexdigest()
    request = urllib.request.Request(endpoint, data=serialized,
                                     headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    status: int | None = None
    raw_response: str | None = None
    record: dict[str, Any] = {"request_sha256": request_sha, "request": req_body}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw_response = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw_response = exc.read().decode("utf-8", errors="replace")
        record.update({"http_status": status, "response_raw": raw_response,
                       "elapsed_seconds": time.perf_counter() - start})
        raise ModelCallFailure(f"GEMMA_HTTP_{status}", record) from exc
    except (urllib.error.URLError, TimeoutError, UnicodeError) as exc:
        record.update({"http_status": None, "response_raw": None,
                       "elapsed_seconds": time.perf_counter() - start})
        raise ModelCallFailure(f"GEMMA_HTTP_FAILED: {type(exc).__name__}: {exc}", record) from exc
    record.update({"response_raw": raw_response, "http_status": status,
                   "elapsed_seconds": time.perf_counter() - start})
    try:
        body = json.loads(raw_response)
        choice = body["choices"][0]
        record["finish_reason"] = choice.get("finish_reason")
        record["usage"] = body.get("usage")
        record["reasoning_content"] = choice["message"].get("reasoning_content")
        if choice.get("finish_reason") != "stop" or record["reasoning_content"]:
            raise ValueError("NOT_STOP_OR_REASONING_PRESENT")
        spec = json.loads(choice["message"]["content"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelCallFailure(f"GEMMA_PROTOCOL_INVALID: {exc}", record) from exc
    return spec, record


def eval_trials(spec: dict[str, Any], trials: list[WorldTrial]) -> dict[str, Any]:
    results = {
        surface: {"n": 0, "baseline_success": 0, "cheap_success": 0,
                  "skill_success": 0, "baseline_actions": 0, "cheap_actions": 0,
                  "skill_actions": 0, "skill_selected": 0}
        for surface in ("ice", "normal")
    }
    for trial in trials:
        row = results[trial.surface]
        base = run_baseline(trial)
        cue = cue_for(trial)
        is_selected = applicable(spec, cue, trial)
        newer = run_skill(spec, trial, cue) if is_selected else base
        # Grand Null: a fixed, human-specified 3-move conditional rule.
        if trial.surface == "ice":
            cheap_issuer = MockIssuer(trial)
            while cheap_issuer.actions < 3 and cheap_issuer.distance < TARGET:
                cheap_issuer.move_away(session=trial.session)
            cheap = outcome(cheap_issuer)
        else:
            cheap = base
        row["n"] += 1
        row["baseline_success"] += int(base["success"])
        row["cheap_success"] += int(cheap["success"])
        row["skill_success"] += int(newer["success"])
        row["baseline_actions"] += base["action_count"]
        row["cheap_actions"] += cheap["action_count"]
        row["skill_actions"] += newer["action_count"]
        row["skill_selected"] += int(is_selected)
    return results


def shift_probe(spec: dict[str, Any], trials: list[WorldTrial]) -> dict[str, Any]:
    active = True
    consecutive_failures = 0
    suspended_at: int | None = None
    for index, trial in enumerate(trials, 1):
        if not active:
            run_baseline(trial)
            continue
        cue = cue_for(trial)
        if not applicable(spec, cue, trial):
            continue
        out = run_skill(spec, trial, cue)
        consecutive_failures = 0 if out["success"] else consecutive_failures + 1
        if consecutive_failures >= 2:
            active = False
            suspended_at = index
    return {"suspended_at_episode": suspended_at, "active_after": active,
            "policy": "two consecutive verified failed attempts -> suppress and request L2",
            "note": "requesting L2 is a marker; this probe does not run L2 again"}


def negative_controls(
    spec: dict[str, Any], evidence_ids: set[str], trial: WorldTrial,
) -> dict[str, bool]:
    checks = {
        "valid_cue_control": applicable(spec, cue_for(trial), trial),
        "stale": not applicable(spec, cue_for(trial, stale=True), trial),
        "unknown": not applicable(spec, cue_for(trial, unknown=True), trial),
        "wrong_session": not applicable(spec, cue_for(trial, wrong_session=True), trial),
        "incomplete_coverage": not applicable(
            spec, Cue(trial.surface, trial.start, trial.session, 10, 11, False), trial,
        ),
    }
    for name, change in (
        ("unbounded", {"max_actions": 10_000}),
        ("invented_action", {"on_failure": "ATTACK"}),
        ("unobserved_evidence", {"evidence_ids": ["holdout-00"]}),
        ("nan_distance", {"min_distance": float("nan")}),
    ):
        try:
            validate_skill({**spec, **change}, evidence_ids)
            checks[name] = False
        except ValueError:
            checks[name] = True
    return checks


def experiment(*, mode: str, seed: int, endpoint: str | None = None,
               model: str | None = None, timeout: float = 120) -> dict[str, Any]:
    training = observed_training(make_trials(seed, TRAIN_N, phase="train"))
    evidence_ids = {e["experience_id"] for e in training}
    provider: dict[str, Any] | None = None
    provider_error: str | None = None
    if mode == "proxy":
        candidate = proxy_l2(training)
    elif mode == "gemma":
        if not endpoint or not model:
            raise ValueError("GEMMA_ENDPOINT_AND_MODEL_REQUIRED")
        try:
            candidate, provider = gemma_l2(training, endpoint=endpoint, model=model,
                                           timeout=timeout)
        except ModelCallFailure as exc:
            provider_error = str(exc)
            provider = exc.record
            candidate = None
    else:
        raise ValueError("UNKNOWN_MODE")
    # Freeze once; validation/holdout are never passed to candidate generation.
    candidate_sha = (hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
                     if candidate is not None else None)
    try:
        spec = validate_skill(candidate, evidence_ids)
        validation_error = None
    except ValueError as exc:
        spec = None
        validation_error = str(exc)
    report: dict[str, Any] = {
        "classification": "DEV_ONLY_SIMULATED_WORLD_NO_REAL_S49",
        "source": "independent 1D synthetic World; no real Minecraft, no semantic owner writes",
        "mode": mode,
        "seed": seed,
        "training": training,
        "candidate_raw": candidate,
        "candidate_sha256": candidate_sha,
        "validator_error": validation_error,
        "provider_record": provider,
        "provider_error": provider_error,
        "validation": None, "holdout": None, "shift": None, "negatives": None,
    }
    if spec is not None:
        report["validation"] = eval_trials(spec, make_trials(seed + 1, VALID_N, phase="validation"))
        report["holdout"] = eval_trials(spec, make_trials(seed + 2, HOLDOUT_N, phase="holdout"))
        report["shift"] = shift_probe(
            spec, make_trials(seed + 3, SHIFT_N, phase="shift", shift=True),
        )
        # In-scope negative tests must not pass vacuously via an unmatched surface.
        control_trial = WorldTrial(
            spec["surface"], (spec["min_distance"] + spec["max_distance"]) / 2,
            (0.37,) * 5, "negative-source",
        )
        report["negatives"] = negative_controls(spec, evidence_ids, control_trial)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("proxy", "gemma"), default="proxy")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--endpoint", help="local /v1/chat/completions (Gemma mode only)")
    parser.add_argument("--model", help="exact served GGUF model identifier (Gemma mode only)")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = experiment(mode=args.mode, seed=args.seed,
                        endpoint=args.endpoint, model=args.model, timeout=args.timeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{result['classification']} mode={args.mode} "
        f"validator={result['validator_error']} out={args.out}"
    )


if __name__ == "__main__":
    main()
