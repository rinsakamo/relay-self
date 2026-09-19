from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.gemma_flee_crystallization import filter_request
from experiments.gemma_skill_narrowing import (
    CASES,
    ObservedLlamaCppProtocolFailure,
    ObservedLlamaCppProvider,
    build_request,
)
from relay_self.relay_engine import CognitionMode

TARGET_CASE_ID = "cave_only"
TARGET_CANDIDATE_KEY = "route_open:cave"
ACCEPTED_PREFIX_COUNT = 13


def build_reconstructed_request():
    case = next(case for case in CASES if case.case_id == TARGET_CASE_ID)
    broad = build_request(case, condition="broad")
    candidate_keys = tuple(sorted(datum.key for datum in broad.context))
    if candidate_keys[ACCEPTED_PREFIX_COUNT] != TARGET_CANDIDATE_KEY:
        raise RuntimeError(
            "reconstructed ablation order no longer targets route_open:cave"
        )
    retained_keys = candidate_keys[ACCEPTED_PREFIX_COUNT + 1 :]
    return filter_request(
        broad,
        retained_keys=retained_keys,
    )


def _surface_payload() -> dict[str, object]:
    request = build_reconstructed_request()
    return {
        "case_id": TARGET_CASE_ID,
        "candidate_key": TARGET_CANDIDATE_KEY,
        "accepted_prefix_count": ACCEPTED_PREFIX_COUNT,
        "request_id": request.request_id,
        "instruction": request.instruction,
        "choices": [
            {
                "choice_id": choice.choice_id,
                "description": choice.description,
            }
            for choice in request.choices
        ],
        "context": [
            {
                "key": datum.key,
                "value_json": datum.value_json,
            }
            for datum in request.context
        ],
    }


def dry_run_payload() -> dict[str, object]:
    request = build_reconstructed_request()
    rendered = render_llama_cpp_request(
        request,
        mode=CognitionMode.THINK,
        model="dry-run",
    )
    return {
        "evidence_class": "gemma think protocol qualification plan only",
        "model_generation_calls": 1,
        "mode": CognitionMode.THINK.value,
        "surface": _surface_payload(),
        "request_contract": {
            "max_tokens": rendered.get("max_tokens"),
            "temperature": rendered.get("temperature"),
            "reasoning_effort": rendered.get("reasoning_effort"),
            "cache_prompt": rendered.get("cache_prompt"),
        },
        "non_claims": [
            "this is apparatus qualification, not a #164 scientific rerun",
            "one valid wire response does not establish model quality",
            "model output is not World truth or Action authorization",
        ],
    }


def run_actual(
    *,
    endpoint: str,
    model: str,
    timeout: float,
) -> dict[str, object]:
    request = build_reconstructed_request()
    provider = ObservedLlamaCppProvider(
        endpoint=endpoint,
        model=model,
        timeout=timeout,
    )
    provider.clear_records()

    try:
        decision = provider(
            request,
            mode=CognitionMode.THINK,
        )
    except ObservedLlamaCppProtocolFailure as exc:
        record = exc.record
        return {
            "evidence_class": (
                "actual-model gemma think protocol qualification"
            ),
            "qualification": "INVALID_PROTOCOL",
            "model_generation_calls": 1,
            "surface": _surface_payload(),
            "protocol_error": str(exc),
            "provider_call": record,
        }

    if len(provider.records) != 1:
        raise RuntimeError(
            "THINK protocol qualification must contain exactly one model call"
        )

    return {
        "evidence_class": "actual-model gemma think protocol qualification",
        "qualification": "VALID_PROTOCOL",
        "model_generation_calls": 1,
        "surface": _surface_payload(),
        "provider_decision": {
            "status": decision.status.value,
            "choice_id": decision.choice_id,
            "reason": decision.reason,
        },
        "provider_call": dict(provider.records[0]),
    }


def write_payload(payload: dict[str, object], output: str | None) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if output is None:
        print(serialized)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify the exact unresolved THINK wire surface exposed by #164."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:1234/v1/chat/completions",
    )
    parser.add_argument("--model", default="gemma-local")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        payload = (
            run_actual(
                endpoint=args.endpoint,
                model=args.model,
                timeout=args.timeout,
            )
            if args.run
            else dry_run_payload()
        )
        write_payload(payload, args.output)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    if payload.get("qualification") == "INVALID_PROTOCOL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
