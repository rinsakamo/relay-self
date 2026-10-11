"""B28: RelayLM-proven top-level reasoning_effort=none, one optional LOCAL call.

B26/B27 source-only prompt and 11 original World training experiences are
unchanged. Output cap remains 2048, temperature=0 and stream=false. The ONLY
scientific intervention relative to B27 is a top-level Chat Completions
reasoning_effort='none' field. Pinned llama.cpp build10874 maps this field to
enable_thinking=false. It is not a server flag or response-format setting.

No native model/GPU call at import, from tests or without --run-local-l2.
No thinking-text rescue, retries, fallback, hidden World rule or Minecraft.
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
from experiments.ac_b_b27_budget_trial import _capture_observed_wire, _save_json

MAX_TOKENS = 2048
REASONING_EFFORT = "none"


def _check_no_thinking_from_original_wire(path: Path) -> dict[str, object]:
    """Effective OFF check; missing reasoning-token usage is UNKNOWN, not zero."""
    data = _strict_json(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise InvalidB26Proposal("original response must be an object")
    choices = data.get("choices")
    if type(choices) is not list or len(choices) != 1:
        raise InvalidB26Proposal("exact one completion choice required")
    choice = choices[0]
    if type(choice) is not dict or type(choice.get("message")) is not dict:
        raise InvalidB26Proposal("source completion has no assistant message")
    message = choice["message"]
    reason_parts = (message.get("reasoning"), message.get("reasoning_content"))
    if any(x is not None and (type(x) is not str or x.strip()) for x in reason_parts):
        raise InvalidB26Proposal("reasoning_effort none NOT effective: reasoning text present")
    usage = data.get("usage")
    token_verdict = "UNKNOWN_UNREPORTED"
    if type(usage) is dict:
        details = usage.get("completion_tokens_details")
        if type(details) is dict and "reasoning_tokens" in details:
            n = details["reasoning_tokens"]
            if type(n) is not int or n < 0:
                raise InvalidB26Proposal("invalid reasoning token accounting")
            if n:
                raise InvalidB26Proposal("reasoning_effort none NOT effective: reasoning tokens")
            token_verdict = "ZERO_REPORTED"
    if choice.get("finish_reason") != "stop":
        raise InvalidB26Proposal("response did not finish with stop")
    content = message.get("content")
    if type(content) is not str or not content.strip():
        raise InvalidB26Proposal("source content empty despite reasoning_effort none")
    return {
        "effective_thinking_off_by_visible_reasoning": True,
        "reported_reasoning_token_count": token_verdict,
        "reasoning_text_empty": True,
        "finish_reason": "stop",
        "visible_content_length": len(content),
    }


def execute_b28_once(
    *,
    endpoint: str,
    model: str,
    evidence_root: Path,
    timeout_seconds: int = 300,
) -> dict[str, object]:
    """Create unique evidence and invoke EXACTLY one opt-in native local L2 POST."""
    if not isinstance(evidence_root, Path):
        raise InvalidB26Proposal("explicit fresh evidence path required")
    evidence_root.mkdir(parents=True, exist_ok=False)
    train = train_original_world(
        StructuralWorld("b28-prompt-training-source", twin=False)
    )
    messages = prompt_messages(train)
    request = {
        "endpoint": endpoint,
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stream": False,
        "reasoning_effort": REASONING_EFFORT,
        "changed_from_B27": {"reasoning_effort": "ADDED_TOP_LEVEL_NONE"},
        "B27_prior_max_tokens": 2048,
        "B26_B27_terminal": "INVALID_FROZEN",
        "original_training_action_attempts": 16,
        "origin": "ONLY_REAL_IF_USER_EXECUTES_THIS_CLI_ON_OWNED_LLAMA_SERVER",
    }
    _save_json(evidence_root / "request.json", request)
    raw_path = evidence_root / "response.raw.json"
    terminal: dict[str, object] = {
        "classification": "B28_UNKNOWN_BEFORE_CALL",
        "result_validity": "UNDETERMINED",
        "generation_requests_attempted": 0,
        "retries": 0,
        "max_tokens": MAX_TOKENS,
        "reasoning_effort_requested": REASONING_EFFORT,
        "original_training_action_attempts": 16,
        "heldout_action_attempts": 0,
        "evaluation_action_attempts": 0,
        "no_real_minecraft": True,
        "no_production_S11": True,
        "B26_B27_invalid_unchanged": True,
    }
    try:
        terminal["generation_requests_attempted"] = 1
        reply = run_local_one_call(
            endpoint=endpoint,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            max_tokens=MAX_TOKENS,
            raw_response_path=raw_path,
            reasoning_effort=REASONING_EFFORT,
        )
        # Real transport recorded full, unedited HTTP bytes BEFORE parsing.
        thinking_check = _check_no_thinking_from_original_wire(raw_path)
        terminal["thinking_off_check"] = thinking_check
        candidate = parse_and_qualify(
            reply["raw_completion"], train,
            source="B28_ONE_REAL_NONTHINKING_LOCAL_RESPONSE",
        )
        result = evaluate_frozen_proposal(
            candidate, source_mark="B28_REAL_NONTHINKING_L2_IF_OPERATOR_RAN"
        )
        _save_json(evidence_root / "evaluation.json", result)
        terminal["classification"] = "B28_VALID_NONTHINKING_STRUCTURE_EVALUATED"
        terminal["result_validity"] = "VALID_TRAINING_FIT"
        terminal["proposed_coefficients"] = list(candidate.coefficients)
        terminal["heldout_action_attempts"] = sum(
            x["novel_action_attempts"] for x in result["worlds"].values()
        )
        terminal["evaluation_action_attempts"] = (
            result["total_independently_issued_offline_world_actions"]
        )
        terminal["reported_model"] = reply["reported_model"]
        terminal["reported_usage"] = reply["reported_usage"]
    except (InvalidB26Proposal, OSError, UnicodeDecodeError, TimeoutError) as exc:
        observed = _capture_observed_wire(raw_path)
        reason = str(exc)
        if "reasoning_effort none NOT effective" in reason:
            terminal["classification"] = "B28_INVALID_REASONING_OFF_NOT_EFFECTIVE"
        elif observed.get("raw_content_length") == 0 and observed.get("finish_reason") == "length":
            terminal["classification"] = "B28_INVALID_LENGTH_EMPTY_CONTENT"
        elif observed["wire_response_received"]:
            terminal["classification"] = "B28_INVALID_OUTPUT_OR_TRAINING_FIT"
        else:
            terminal["classification"] = "B28_TRANSPORT_OR_PREFLIGHT_FAILURE"
        terminal["result_validity"] = "INVALID"
        terminal["failure_type"] = type(exc).__name__
        terminal["failure_description"] = reason
    finally:
        terminal["wire_observation"] = _capture_observed_wire(raw_path)
        _save_json(evidence_root / "terminal.json", terminal)
        with (evidence_root / "SHA256SUMS").open("x", encoding="utf-8") as sums:
            for item in sorted(evidence_root.iterdir()):
                if item.is_file() and item.name != "SHA256SUMS":
                    sums.write(f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.name}\n")
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
        p.error("B28 does not infer by default: --run-local-l2 required")
    if not args.model or args.evidence_root is None:
        p.error("exact observed --model and fresh --evidence-root required")
    terminal = execute_b28_once(
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
