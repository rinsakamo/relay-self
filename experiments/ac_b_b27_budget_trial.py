"""AC-B B27: independent single real-L2 trial, sole change max_tokens=2048.

Uses frozen B26 source-only 11-example prompt, original strict 16-coefficient
qualification and NORMAL/TWIN/CHEAP_DEG2 evaluation unchanged. This is a
MANUAL local-model CLI: importing it or running CI never calls a model.
Both valid and invalid HTTP completions retain raw wire bytes before parse.

No retries, format correction, reasoning_effort toggle, gifted H1 or Minecraft.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experiments.ac_b_b24_structural_transfer import StructuralWorld
from experiments.ac_b_b26_l2_trial import (
    InvalidB26Proposal,
    _strict_json,
    evaluate_frozen_proposal,
    parse_and_qualify,
    prompt_messages,
    run_local_one_call,
    train_original_world,
)

NEW_BUDGET = 2048
PREVIOUS_BUDGET = 512
ONE_CALL_SCOPE = "B27_REAL_LOCAL_L2_ONLY_WHEN_OPERATOR_RUNS_CLI"


def _save_json(path: Path, data: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _capture_observed_wire(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "wire_response_received": False,
            "finish_reason": None,
            "usage": None,
            "raw_content_length": None,
            "reasoning_content_present": None,
        }
    raw = path.read_bytes()
    try:
        outer = _strict_json(raw.decode("utf-8"))
        if not isinstance(outer, dict):
            raise InvalidB26Proposal("response was not a JSON object")
        choices = outer.get("choices")
        first = choices[0] if isinstance(choices, list) and choices else {}
        if not isinstance(first, dict):
            first = {}
        message = first.get("message")
        if not isinstance(message, dict):
            message = {}
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        return {
            "wire_response_received": True,
            "finish_reason": first.get("finish_reason"),
            "usage": outer.get("usage"),
            "reported_model": outer.get("model"),
            "system_fingerprint": outer.get("system_fingerprint"),
            "raw_content_length": len(content) if isinstance(content, str) else None,
            "reasoning_content_present": bool(reasoning) if isinstance(reasoning, str) else None,
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_response_filename": path.name,
        }
    except (ValueError, UnicodeDecodeError):
        return {
            "wire_response_received": True,
            "wire_response_parse_error": True,
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_response_filename": path.name,
        }


def execute_b27_once(
    *,
    endpoint: str,
    model: str,
    evidence_root: Path,
    timeout_seconds: int = 300,
) -> dict[str, object]:
    """One optional LOCAL HTTP call, terminal receipt also on invalid output.

    Creates the evidence directory exclusively. No transport retry or output
    repair; evaluation is reached only after a frozen valid 16-bit ANF model.
    """
    if not isinstance(evidence_root, Path):
        raise InvalidB26Proposal("B27 requires an explicit evidence Path")
    # Fail rather than overwriting an earlier physical trial.
    evidence_root.mkdir(parents=True, exist_ok=False)
    train = train_original_world(
        StructuralWorld("b27-prompt-training-source", twin=False)
    )
    messages = prompt_messages(train)
    request = {
        "endpoint": endpoint,
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": NEW_BUDGET,
        "stream": False,
        "original_training_actions": 16,
        "call_scope": ONE_CALL_SCOPE,
        "B26_prior_max_tokens": PREVIOUS_BUDGET,
        "B27_changed_parameter_only": "max_tokens",
        "additional_reasoning_effort": None,
    }
    _save_json(evidence_root / "request.json", request)
    raw_path = evidence_root / "response.raw.json"
    terminal: dict[str, object] = {
        "classification": "B27_UNKNOWN_BEFORE_ONE_ATTEMPT",
        "B26_512_trial": "INVALID_FIXED_UNCHANGED",
        "B27_generation_budget": NEW_BUDGET,
        "actual_local_model_call_started": False,
        "generation_requests_attempted": 0,
        "retries": 0,
        "prompt_training_actions": 16,
        "heldout_actions": 0,
        "eval_world_actions": 0,
        "source_only_prompt": True,
        "no_real_minecraft": True,
        "no_production_S11": True,
        "result_validity": "UNDETERMINED",
    }
    try:
        terminal["actual_local_model_call_started"] = True
        terminal["generation_requests_attempted"] = 1
        reply = run_local_one_call(
            endpoint=endpoint,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_tokens=NEW_BUDGET,
            raw_response_path=raw_path,
        )
        # The source issued completion (including reasoning_content)
        # is already frozen in response.raw.json at this point.
        candidate = parse_and_qualify(
            reply["raw_completion"], train,
            source="B27_ONE_ACTUAL_LOCAL_L2_RESPONSE",
        )
        result = evaluate_frozen_proposal(
            candidate, source_mark="B27_VALID_LOCAL_L2_2048_IF_EXECUTED"
        )
        _save_json(evidence_root / "evaluation.json", result)
        terminal["classification"] = "B27_VALID_STRUCTURE_OFFLINE_WORLD_EVALUATED"
        terminal["result_validity"] = "VALID_TRAINING_FIT"
        terminal["heldout_actions"] = sum(
            value["novel_action_attempts"] for value in result["worlds"].values()
        )
        terminal["eval_world_actions"] = (
            result["total_independently_issued_offline_world_actions"]
        )
        terminal["proposed_coefficients"] = list(candidate.coefficients)
        terminal["reported_model"] = reply["reported_model"]
        terminal["reported_usage"] = reply["reported_usage"]
    except (InvalidB26Proposal, OSError, UnicodeDecodeError, TimeoutError) as exc:
        observed = _capture_observed_wire(raw_path)
        if (
            observed.get("raw_content_length") == 0
            and observed.get("finish_reason") == "length"
        ):
            terminal["classification"] = "B27_INVALID_2048_EXHAUSTED_BEFORE_CONTENT"
        elif observed["wire_response_received"]:
            terminal["classification"] = "B27_INVALID_RESPONSE_OR_TRAINING_FIT"
        else:
            terminal["classification"] = "B27_TRANSPORT_OR_PREFLIGHT_FAILURE"
        terminal["result_validity"] = "INVALID"
        terminal["failure_type"] = type(exc).__name__
        terminal["failure_description"] = str(exc)
    finally:
        terminal["wire_observation"] = _capture_observed_wire(raw_path)
        _save_json(evidence_root / "terminal.json", terminal)
        # Content-addressed evidence list; no self-referential SHA256SUMS.
        with (evidence_root / "SHA256SUMS").open("x", encoding="utf-8") as manifest:
            for artifact in sorted(evidence_root.iterdir()):
                if artifact.is_file() and artifact.name != "SHA256SUMS":
                    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                    manifest.write(f"{digest}  {artifact.name}\n")
    return terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-local-l2", action="store_true")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:1234/v1/chat/completions"
    )
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--evidence-root", type=Path)
    args = parser.parse_args(argv)
    if not args.run_local_l2:
        parser.error("B27 is non-generative by default; use --run-local-l2")
    if not args.model or args.evidence_root is None:
        parser.error("exact --model and unique --evidence-root required")
    terminal = execute_b27_once(
        endpoint=args.endpoint,
        model=args.model,
        evidence_root=args.evidence_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps({
        "classification": terminal["classification"],
        "result_validity": terminal["result_validity"],
        "evidence_root": str(args.evidence_root),
        "generation_requests_attempted": terminal["generation_requests_attempted"],
    }, sort_keys=True))
    return 0 if terminal["result_validity"] == "VALID_TRAINING_FIT" else 3


if __name__ == "__main__":
    raise SystemExit(main())
