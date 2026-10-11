"""AC-B B29 — native llama.cpp JSON Schema for exact one-shot ANF proposal.

One independent change vs B28: add provider-native top-level response_format.
Keep reasoning_effort='none', max_tokens=2048, temperature=0, and exact
B26 original 11-source training prompt/semantic evaluator unchanged.

This does NOT generate at import or in CI. Operator must start/attest owned
llama-server and explicitly invoke --run-local-l2, exactly once, without retry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experiments.ac_b_b24_structural_transfer import StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    InvalidB26Proposal,
    evaluate_frozen_proposal,
    parse_and_qualify,
    prompt_messages,
    run_local_one_call,
    train_original_world,
)
from experiments.ac_b_b27_budget_trial import _capture_observed_wire, _save_json
from experiments.ac_b_b28_reasoning_off_trial import _check_no_thinking_from_original_wire

SCHEMA_NAME = "relay_self_b29_anf_coefficients_v1"
MAX_TOKENS = 2048
REASONING_EFFORT = "none"
COEFFICIENT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "coefficients": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 1},
            "minItems": 16,
            "maxItems": 16,
        }
    },
    "required": ["coefficients"],
    "additionalProperties": False,
}
RESPONSE_FORMAT: dict[str, object] = {
    "type": "json_schema",
    "json_schema": {
        "name": SCHEMA_NAME,
        "strict": True,
        "schema": COEFFICIENT_SCHEMA,
    },
}


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def execute_b29_once(
    *, endpoint: str, model: str, evidence_root: Path,
    timeout_seconds: int = 300,
) -> dict[str, object]:
    """One optional L2 proposal; freeze original HTTP before ANY JSON semantics.

    The native schema is a *syntax* sampler. Original B26 `parse_and_qualify`
    remains the *semantic* authority for all eleven actual source labels.
    """
    if not isinstance(evidence_root, Path):
        raise InvalidB26Proposal("explicit fresh B29 evidence root required")
    evidence_root.mkdir(parents=True, exist_ok=False)
    training = train_original_world(
        StructuralWorld("b29-prompt-training-source", twin=False)
    )
    messages = prompt_messages(training)
    request = {
        "endpoint": endpoint, "model": model, "messages": messages,
        "temperature": 0, "stream": False,
        "max_tokens": MAX_TOKENS, "reasoning_effort": REASONING_EFFORT,
        "response_format": RESPONSE_FORMAT,
        "schema_sha256": _canonical_digest(COEFFICIENT_SCHEMA),
        "response_format_sha256": _canonical_digest(RESPONSE_FORMAT),
        "relative_to_B28": "TOP_LEVEL_RESPONSE_FORMAT_ONLY",
        "source_training_action_attempts": 16,
        "old_B26_B27_B28": "ALL_INVALID_IMMUTABLE",
    }
    _save_json(evidence_root / "request.json", request)
    raw_path = evidence_root / "response.raw.json"
    terminal: dict[str, object] = {
        "classification": "B29_UNKNOWN_BEFORE_CALL",
        "result_validity": "UNDETERMINED",
        "generation_requests_attempted": 0,
        "retries": 0,
        "source_training_action_attempts": 16,
        "heldout_action_attempts": 0,
        "evaluation_action_attempts": 0,
        "response_format_sha256": request["response_format_sha256"],
        "reasoning_effort_requested": REASONING_EFFORT,
        "max_tokens": MAX_TOKENS,
        "B26_B27_B28_invalid_unchanged": True,
        "no_real_minecraft": True,
        "no_production_S11": True,
    }
    try:
        terminal["generation_requests_attempted"] = 1
        reply = run_local_one_call(
            endpoint=endpoint, model=model, messages=messages,
            timeout_seconds=timeout_seconds, max_tokens=MAX_TOKENS,
            reasoning_effort=REASONING_EFFORT,
            response_format=RESPONSE_FORMAT, raw_response_path=raw_path,
        )
        terminal["thinking_off_check"] = _check_no_thinking_from_original_wire(
            raw_path
        )
        # NEVER strip a Markdown fence or recover an embedded JSON object.
        # The original source-experience fit remains mandatory.
        candidate = parse_and_qualify(
            reply["raw_completion"], training,
            source="B29_ONE_REAL_NATIVE_SCHEMA_THINKING_OFF_RESPONSE",
        )
        report = evaluate_frozen_proposal(
            candidate, source_mark="B29_ACTUAL_LOCAL_L2_IF_OPERATOR_EXECUTES"
        )
        _save_json(evidence_root / "evaluation.json", report)
        terminal["classification"] = "B29_VALID_NATIVE_JSON_AND_SOURCE_FIT_EVALUATED"
        terminal["result_validity"] = "VALID_TRAINING_FIT"
        terminal["proposed_coefficients"] = list(candidate.coefficients)
        terminal["heldout_action_attempts"] = sum(
            x["novel_action_attempts"] for x in report["worlds"].values()
        )
        terminal["evaluation_action_attempts"] = (
            report["total_independently_issued_offline_world_actions"]
        )
        terminal["reported_model"] = reply["reported_model"]
        terminal["reported_usage"] = reply["reported_usage"]
    except (InvalidB26Proposal, OSError, UnicodeDecodeError, TimeoutError) as exc:
        reason = str(exc)
        observation = _capture_observed_wire(raw_path)
        if "reasoning_effort none NOT effective" in reason:
            terminal["classification"] = "B29_INVALID_THINKING_OFF_UNQUALIFIED"
        elif reason == "proposed structure contradicts executed training":
            terminal["classification"] = "B29_INVALID_SOURCE_SEMANTIC_FIT"
        elif observation["wire_response_received"]:
            terminal["classification"] = "B29_INVALID_NATIVE_OUTPUT_OR_RESPONSE"
        else:
            terminal["classification"] = "B29_TRANSPORT_OR_PREFLIGHT_FAILURE"
        terminal["result_validity"] = "INVALID"
        terminal["failure_type"] = type(exc).__name__
        terminal["failure_description"] = reason
    finally:
        terminal["wire_observation"] = _capture_observed_wire(raw_path)
        _save_json(evidence_root / "terminal.json", terminal)
        with (evidence_root / "SHA256SUMS").open("x", encoding="utf-8") as sums:
            for item in sorted(evidence_root.iterdir()):
                if item.is_file() and item.name != "SHA256SUMS":
                    digest = hashlib.sha256(item.read_bytes()).hexdigest()
                    sums.write(f"{digest}  {item.name}\n")
    return terminal


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-local-l2", action="store_true")
    p.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions")
    p.add_argument("--model")
    p.add_argument("--timeout-seconds", type=int, default=300)
    p.add_argument("--evidence-root", type=Path)
    args = p.parse_args(argv)
    if not args.run_local_l2:
        p.error("no physical L2 inference by default: explicitly --run-local-l2")
    if not args.model or args.evidence_root is None:
        p.error("exact measured --model and unique --evidence-root required")
    outcome = execute_b29_once(
        endpoint=args.endpoint, model=args.model,
        timeout_seconds=args.timeout_seconds, evidence_root=args.evidence_root,
    )
    print(json.dumps({
        "classification": outcome["classification"],
        "result_validity": outcome["result_validity"],
        "generation_requests_attempted": outcome["generation_requests_attempted"],
        "evidence_root": str(args.evidence_root),
    }, sort_keys=True))
    return 0 if outcome["result_validity"] == "VALID_TRAINING_FIT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
