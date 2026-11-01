"""M-only post-execution bridge from original RelayEngine typed results to costs.

No engine/provider invocation, S49 action, model replay or raw text persistence.
The S/model owner MUST bind a completed result to its original S epoch;
a structurally matching claim is not independent source attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from experiments.metabolism_cognitive_lifecycle import (
    CognitiveLifecycleRejected,
    CognitiveWorkReceipt,
    Level,
    _check_audit,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    OpenCognitionResult,
    ProviderCallFacts,
    RelayEngineResult,
)


@dataclass(frozen=True, slots=True)
class OwnerEngineCall:
    """One already-finished S-owned request and exact returned engine result."""

    request: BoundedChoiceRequest | OpenCognitionRequest
    result: RelayEngineResult | OpenCognitionResult


@dataclass(frozen=True, slots=True)
class OwnerEpochEngineBinding:
    """An EXTERNAL owner's assertion; M cannot source-attest this association."""

    session_id: str
    probe_seq: int
    native_request_id: str
    meter_id: str
    level: Level


def _facts(facts: ProviderCallFacts) -> tuple[int | None, int | None]:
    if not isinstance(facts, ProviderCallFacts):
        raise CognitiveLifecycleRejected("only original typed provider call facts")
    if (
        facts.prompt_tokens is not None
        and facts.completion_tokens is not None
        and facts.total_tokens is not None
        and facts.total_tokens != facts.prompt_tokens + facts.completion_tokens
    ):
        raise CognitiveLifecycleRejected("inconsistent reported provider token totals")
    return facts.prompt_tokens, facts.completion_tokens


def _extract(
    call: OwnerEngineCall,
) -> tuple[str, int, int, int | None, int | None]:
    if not isinstance(call, OwnerEngineCall):
        raise CognitiveLifecycleRejected("typed original engine call required")
    req, result = call.request, call.result
    if isinstance(req, OpenCognitionRequest) and isinstance(result, OpenCognitionResult):
        if result.request_id != req.request_id:
            raise CognitiveLifecycleRejected("open result does not match its request")
        prompt, output = _facts(result.call_facts)
        return req.request_id, result.provider_call_count, result.elapsed_ns, prompt, output
    if isinstance(req, BoundedChoiceRequest) and isinstance(result, RelayEngineResult):
        attempts = result.attempts
        if (
            type(attempts) is not tuple or len(attempts) not in (1, 2)
            or attempts[0].mode is not CognitionMode.BOUNDED
            or (len(attempts) == 2 and attempts[1].mode is not CognitionMode.THINK)
            or len(attempts) == 2 and (
                not req.think_allowed
                or attempts[0].status is not DecisionStatus.UNRESOLVED
            )
            or (len(attempts) == 1 and (
                attempts[0].status is DecisionStatus.UNRESOLVED and req.think_allowed
            ))
            or result.status is not attempts[-1].status
            or result.choice_id != attempts[-1].choice_id
            or result.think_allowed != req.think_allowed
            or result.soft_wall_time_budget_s != req.soft_wall_time_budget_s
            or result.status is DecisionStatus.RESOLVED
            and result.choice_id not in {choice.choice_id for choice in req.choices}
        ):
            raise CognitiveLifecycleRejected("impossible bounded/think attempt sequence")
        token_pairs = [_facts(attempt.call_facts) for attempt in attempts]
        prompt = (
            sum(p for p, _ in token_pairs if p is not None)
            if all(p is not None for p, _ in token_pairs) else None
        )
        output = (
            sum(o for _, o in token_pairs if o is not None)
            if all(o is not None for _, o in token_pairs) else None
        )
        return req.request_id, result.provider_call_count, result.elapsed_ns, prompt, output
    raise CognitiveLifecycleRejected("engine request and result types do not match")


def cognitive_receipt_from_engine_results(
    *,
    audit_row: Mapping[str, object],
    binding: OwnerEpochEngineBinding,
    completed_calls: tuple[OwnerEngineCall, ...],
) -> CognitiveWorkReceipt:
    """Read actual preexisting EngineResult; don't infer a missing provider call.

    The returned usage is a caller-declared DEV receipt, not a physical source
    or provider authentication, even when the engine types are genuine.
    """
    if (
        not isinstance(binding, OwnerEpochEngineBinding)
        or type(completed_calls) is not tuple
        or not 1 <= len(completed_calls) <= 8
    ):
        raise CognitiveLifecycleRejected("one to eight finished owner calls required")
    source = _check_audit(audit_row)
    if (
        (binding.session_id, binding.probe_seq, binding.native_request_id) != source
        or type(binding.meter_id) is not str
        or not 1 <= len(binding.meter_id) <= 192
        or not binding.meter_id.isprintable()
        or binding.level not in ("L0", "L1", "L2", "UNKNOWN")
    ):
        raise CognitiveLifecycleRejected("source-bound engine binding mismatched")
    seen: set[str] = set()
    total_calls = 0
    total_wall = 0
    token_pairs: list[tuple[int | None, int | None]] = []
    for call in completed_calls:
        request_id, count, wall, prompt, output = _extract(call)
        if request_id in seen or count < 1 or type(wall) is not int or wall < 0:
            raise CognitiveLifecycleRejected("duplicate, missing or negative engine call")
        seen.add(request_id)
        total_calls += count
        total_wall += wall
        token_pairs.append((prompt, output))
    input_tokens = (
        sum(n for n, _ in token_pairs if n is not None)
        if all(n is not None for n, _ in token_pairs) else None
    )
    output_tokens = (
        sum(n for _, n in token_pairs if n is not None)
        if all(n is not None for _, n in token_pairs) else None
    )
    return CognitiveWorkReceipt(
        session_id=binding.session_id,
        probe_seq=binding.probe_seq,
        request_id=binding.native_request_id,
        receipt_id=binding.meter_id,
        level=binding.level,
        provider_calls=total_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        wall_ns=total_wall,
        # Engine wall time and token facts do not measure CPU or GPU time.
        cpu_ns=None,
        gpu_ns=None,
    )
