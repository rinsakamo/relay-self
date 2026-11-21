from __future__ import annotations

from collections.abc import Iterable

from adapters.llama_cpp.benchmark_jev_bounded import (
    GENERATED_ARM,
    JEV_ARM,
    _observe_jev_answer,
    benchmark_request,
    run_matched_benchmark,
)
from adapters.llama_cpp.relay_engine import LlamaCppProviderProtocolError
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderCallFacts,
    RelayEngineAttempt,
    RelayEngineResult,
)


def _result(
    elapsed_ns: int,
    *,
    choice_id: str = "cave",
    prompt_tokens: int = 400,
    completion_tokens: int = 5,
    finish_reason: str | None = "stop",
) -> RelayEngineResult:
    return RelayEngineResult(
        status=DecisionStatus.RESOLVED,
        choice_id=choice_id,
        attempts=(
            RelayEngineAttempt(
                mode=CognitionMode.BOUNDED,
                status=DecisionStatus.RESOLVED,
                choice_id=choice_id,
                reason="",
                elapsed_ns=elapsed_ns,
                call_facts=ProviderCallFacts(
                    requested_max_output_tokens=48,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    finish_reason=finish_reason,
                ),
            ),
        ),
        think_allowed=False,
    )


class SequenceEngine:
    def __init__(
        self,
        results: Iterable[RelayEngineResult | Exception],
    ) -> None:
        self._results = iter(results)
        self.call_count = 0

    def __call__(self, _request: object) -> RelayEngineResult:
        self.call_count += 1
        value = next(self._results)
        if isinstance(value, Exception):
            raise value
        return value


def test_matched_benchmark_alternates_order_and_reports_latency() -> None:
    generated = SequenceEngine(
        [
            _result(100),
            _result(110),
            _result(120),
            _result(130),
            _result(140),
        ]
    )
    jev = SequenceEngine(
        [
            _result(
                50,
                prompt_tokens=390,
                completion_tokens=0,
                finish_reason=None,
            ),
            _result(
                60,
                prompt_tokens=390,
                completion_tokens=0,
                finish_reason=None,
            ),
            _result(
                70,
                prompt_tokens=390,
                completion_tokens=0,
                finish_reason=None,
            ),
            _result(
                80,
                prompt_tokens=390,
                completion_tokens=0,
                finish_reason=None,
            ),
            _result(
                90,
                prompt_tokens=390,
                completion_tokens=0,
                finish_reason=None,
            ),
        ]
    )

    generated_report, jev_report, order = run_matched_benchmark(
        generated_engine=generated,  # type: ignore[arg-type]
        jev_engine=jev,  # type: ignore[arg-type]
        request=benchmark_request(),
        warmup_calls_per_arm=1,
        measured_calls_per_arm=4,
    )

    assert generated.call_count == 5
    assert jev.call_count == 5
    assert order == (
        GENERATED_ARM,
        JEV_ARM,
        JEV_ARM,
        GENERATED_ARM,
        GENERATED_ARM,
        JEV_ARM,
        JEV_ARM,
        GENERATED_ARM,
    )

    assert generated_report.provider_failure_count == 0
    assert generated_report.incorrect_outcome_count == 0
    assert generated_report.provider_latency is not None
    assert generated_report.provider_latency.median_ns == 125.0
    assert generated_report.provider_latency.p95_ns == 140
    assert generated_report.provider_latency.max_ns == 140

    assert jev_report.provider_failure_count == 0
    assert jev_report.incorrect_outcome_count == 0
    assert jev_report.provider_latency is not None
    assert jev_report.provider_latency.median_ns == 75.0
    assert jev_report.provider_latency.p95_ns == 90
    assert jev_report.provider_latency.max_ns == 90
    assert all(
        observation.completion_tokens == 0
        for observation in jev_report.observations
    )


def test_matched_benchmark_records_wrong_choice_without_think() -> None:
    generated = SequenceEngine([_result(100, choice_id="ridge")])
    jev = SequenceEngine(
        [
            _result(
                50,
                choice_id="cave",
                completion_tokens=0,
                finish_reason=None,
            )
        ]
    )

    generated_report, jev_report, _ = run_matched_benchmark(
        generated_engine=generated,  # type: ignore[arg-type]
        jev_engine=jev,  # type: ignore[arg-type]
        request=benchmark_request(),
        warmup_calls_per_arm=0,
        measured_calls_per_arm=1,
    )

    assert generated_report.incorrect_outcome_count == 1
    assert generated_report.observations[0].choice_id == "ridge"
    assert jev_report.incorrect_outcome_count == 0


def test_matched_benchmark_records_provider_protocol_failure() -> None:
    generated = SequenceEngine(
        [LlamaCppProviderProtocolError("generated malformed")]
    )
    jev = SequenceEngine(
        [
            _result(
                50,
                completion_tokens=0,
                finish_reason=None,
            )
        ]
    )

    generated_report, jev_report, _ = run_matched_benchmark(
        generated_engine=generated,  # type: ignore[arg-type]
        jev_engine=jev,  # type: ignore[arg-type]
        request=benchmark_request(),
        warmup_calls_per_arm=0,
        measured_calls_per_arm=1,
    )

    assert generated_report.provider_failure_count == 1
    assert generated_report.successful_call_count == 0
    assert generated_report.provider_latency is None
    assert generated_report.observations[0].error_type == (
        "LlamaCppProviderProtocolError"
    )
    assert jev_report.provider_failure_count == 0


def test_jev_probabilities_and_confidence_are_observation_only_facts() -> None:
    observed = _observe_jev_answer(
        {
            "answers": {
                "decision": {
                    "type": "choice",
                    "choice": "cave",
                    "probabilities": {
                        "cave": 0.75,
                        "ridge": 0.15,
                        "__relay_self_unresolved__": 0.10,
                    },
                    "confidence": 0.42,
                }
            }
        }
    )

    assert observed.probabilities == {
        "cave": 0.75,
        "ridge": 0.15,
        "__relay_self_unresolved__": 0.10,
    }
    assert observed.confidence == 0.42
