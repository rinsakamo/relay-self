"""S55 user-local GGUF / RelayEngine receipt probe. No GPU attestation.

A configured loopback server response and hashing a file do NOT prove that
the backend actually loaded those GGUF bytes. This only measures local
interface behavior and prepares independent real-model qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from adapters.mineflayer.local_chat_provider import (
    LoopbackChatProvider,
    LoopbackInferenceConfig,
)
from relay_self.cognitive_allocation import CognitionBudget, allocate_cognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    RelayEngine,
)


class InvalidLocalQualification(ValueError):
    """Missing or mismatched local model evidence."""


def hash_gguf(path: Path | None, expected: str | None) -> dict[str, object]:
    if expected is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise InvalidLocalQualification("64-hex SHA256 expected")
    if path is None:
        if expected:
            raise InvalidLocalQualification("model file required for SHA256 bound")
        return {"file_sha256": None, "bytes": None, "loaded_by_backend": False}
    if not isinstance(path, Path) or not path.is_file() or path.suffix.lower() != ".gguf":
        raise InvalidLocalQualification("readable local GGUF file required")
    digest = hashlib.sha256()
    n = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            n += len(block)
            digest.update(block)
    h = digest.hexdigest()
    if expected and h != expected.lower():
        raise InvalidLocalQualification("local GGUF bytes do not match expected SHA256")
    return {
        "file_sha256": h, "bytes": n,
        "matched_expected_hash": expected is not None,
        "loaded_by_backend": False,
    }


def qualify(
    *, model: str, endpoint: str, timeout_s: float = 60,
    max_tokens: int = 64, allow_think: bool = False,
    gguf: Path | None = None, expected_sha256: str | None = None,
) -> dict[str, object]:
    file_facts = hash_gguf(gguf, expected_sha256)
    config = LoopbackInferenceConfig(
        model=model, endpoint=endpoint,
        timeout_s=timeout_s, max_tokens=max_tokens,
    )
    request = BoundedChoiceRequest(
        request_id="s55-measure-model-choice",
        instruction=(
            "Hypothetical zombie is two meters away. Answer exactly WAIT "
            "or MOVE_AWAY. No permission to take any World Action is granted."
        ),
        intent_id="s55-calibration", focus="hypothetical-world",
        choices=(
            BoundedChoice("WAIT", "remain stationary"),
            BoundedChoice("MOVE_AWAY", "move backward"),
        ),
        context=(CognitionDatum.from_value(
            "distance_m", 2.0,
            Provenance("s55-synthetic-question", "not-native-World-evidence"),
        ),),
    )
    budget = CognitionBudget(
        max_model_calls=2 if allow_think else 1, allow_think=allow_think,
        allow_open=False,
    )
    start = time.monotonic_ns()
    decision = allocate_cognition(
        budget=budget, bounded=request,
        engine=RelayEngine(LoopbackChatProvider(config)),
    )
    elapsed_ms = (time.monotonic_ns() - start) / 1_000_000
    b = decision.bounded_result
    if b is None or b.provider_call_count != decision.model_calls:
        raise InvalidLocalQualification("real RelayEngine call count mismatch")
    return {
        "milestone": "S55", "status": "PASS",
        "classification": "LOOPBACK_INFERENCE_RESPONSE_BACKEND_ID_UNVERIFIED",
        "model_requested": config.model, "model_file": file_facts,
        "transport": "127.0.0.1_OR_LOCALHOST_OPENAI_COMPATIBLE",
        "model_actually_loaded_attested": False,
        "gpu_used_attested": False, "backend_stop_ack": False,
        "gpu_memory_release_measured": False,
        "request_is_synthetic_not_minecraft": True,
        "action_authorized": False,
        "model_calls": decision.model_calls,
        "budget_calls": budget.max_model_calls,
        "candidate_choice": decision.choice_id,
        "unresolved": decision.unresolved,
        "path": decision.path.value,
        "elapsed_ms": round(elapsed_ms, 3),
        "prompt_tokens": b.observed_prompt_tokens,
        "completion_tokens": b.observed_completion_tokens,
        "attempts": [
            {
                "mode": a.mode.value, "status": a.status.value,
                "elapsed_ms": round(a.elapsed_s * 1000, 3),
                "prompt_tokens": a.call_facts.prompt_tokens,
                "completion_tokens": a.call_facts.completion_tokens,
                "finish_reason": a.call_facts.finish_reason,
            }
            for a in b.attempts
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument(
        "--endpoint", default="http://127.0.0.1:1234/v1/chat/completions",
    )
    p.add_argument("--max-tokens", type=int, default=64)
    p.add_argument("--timeout-s", type=float, default=60)
    p.add_argument("--allow-think", action="store_true")
    p.add_argument("--gguf", type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        result = qualify(
            model=args.model, endpoint=args.endpoint,
            timeout_s=args.timeout_s, max_tokens=args.max_tokens,
            allow_think=args.allow_think, gguf=args.gguf,
            expected_sha256=args.expected_sha256,
        )
        code = 0
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "milestone": "S55", "status": "FAIL",
            "classification": "LOCAL_INFERENCE_NOT_QUALIFIED",
            "error_type": type(exc).__name__,
            "action_authorized": False,
            "model_actually_loaded_attested": False,
        }
        code = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("S55_REPORT=" + json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
