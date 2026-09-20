from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from adapters.llama_cpp.qualify_relay_engine import (
    LlamaCppRuntimeIdentity,
    RepositoryIdentity,
    build_reference_request,
    inspect_llama_cpp_runtime,
    inspect_repository,
)
from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppRelayProvider,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    RelayEngine,
    RelayEngineResult,
)

GENERATED_ARM = "generated_bounded"
JEV_ARM = "jev_bounded"
EXPECTED_CHOICE_ID = "cave"


class JevBenchmarkError(RuntimeError):
    """Raised when the matched Jev benchmark cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class SourceRepositoryIdentity:
    root: str
    head: str
    tree: str


@dataclass(frozen=True, slots=True)
class ModelArtifactIdentity:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class GpuIdentity:
    name: str
    driver_version: str


@dataclass(frozen=True, slots=True)
class BenchmarkObservation:
    arm: str
    ordinal: int
    pair_index: int
    position_in_pair: int
    wall_elapsed_ns: int
    wall_elapsed_seconds: float
    provider_elapsed_ns: int | None
    provider_elapsed_seconds: float | None
    final_status: str | None
    choice_id: str | None
    correct: bool
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None
    error_type: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class LatencySummary:
    count: int
    median_ns: float
    p95_ns: int
    max_ns: int
    median_seconds: float
    p95_seconds: float
    max_seconds: float


@dataclass(frozen=True, slots=True)
class BenchmarkArmReport:
    arm: str
    measured_call_count: int
    successful_call_count: int
    provider_failure_count: int
    incorrect_outcome_count: int
    provider_latency: LatencySummary | None
    wall_latency: LatencySummary
    observations: tuple[BenchmarkObservation, ...]


@dataclass(frozen=True, slots=True)
class JevBoundedBenchmarkReport:
    evidence_class: str
    repository: RepositoryIdentity
    llama_cpp_source: SourceRepositoryIdentity
    runtime: LlamaCppRuntimeIdentity
    model_artifact: ModelArtifactIdentity
    gpu: GpuIdentity
    request_id: str
    expected_choice_id: str
    warmup_calls_per_arm: int
    measured_calls_per_arm: int
    measured_call_order: tuple[str, ...]
    server_model_load_included: bool
    cache_reuse_qualified: bool
    generated: BenchmarkArmReport
    jev: BenchmarkArmReport
    qualified: bool


def benchmark_request() -> BoundedChoiceRequest:
    """Return the fixed #257 request with THINK disabled for direct A/B timing."""

    return replace(
        build_reference_request(),
        request_id="mvp-flee-destination-jev-benchmark",
        think_allowed=False,
        soft_wall_time_budget_s=None,
    )


def run_matched_benchmark(
    *,
    generated_engine: RelayEngine,
    jev_engine: RelayEngine,
    request: BoundedChoiceRequest,
    warmup_calls_per_arm: int,
    measured_calls_per_arm: int,
) -> tuple[
    BenchmarkArmReport,
    BenchmarkArmReport,
    tuple[str, ...],
]:
    if not isinstance(request, BoundedChoiceRequest):
        raise TypeError("request must be BoundedChoiceRequest")
    if request.think_allowed:
        raise JevBenchmarkError(
            "matched bounded benchmark requires think_allowed=false"
        )
    _require_non_negative_int("warmup_calls_per_arm", warmup_calls_per_arm)
    _require_positive_int("measured_calls_per_arm", measured_calls_per_arm)

    engines = {
        GENERATED_ARM: generated_engine,
        JEV_ARM: jev_engine,
    }

    for warmup_index in range(warmup_calls_per_arm):
        for arm in _pair_order(warmup_index):
            observation = _run_observation(
                engine=engines[arm],
                request=request,
                arm=arm,
                ordinal=warmup_index,
                pair_index=warmup_index,
                position_in_pair=_pair_order(warmup_index).index(arm),
            )
            if not observation.correct:
                detail = (
                    observation.error_message
                    or f"status={observation.final_status} choice={observation.choice_id}"
                )
                raise JevBenchmarkError(
                    f"{arm} warmup did not preserve expected outcome: {detail}"
                )

    measured: dict[str, list[BenchmarkObservation]] = {
        GENERATED_ARM: [],
        JEV_ARM: [],
    }
    order: list[str] = []
    arm_ordinals = {
        GENERATED_ARM: 0,
        JEV_ARM: 0,
    }

    for pair_index in range(measured_calls_per_arm):
        pair_order = _pair_order(pair_index)
        for position_in_pair, arm in enumerate(pair_order):
            observation = _run_observation(
                engine=engines[arm],
                request=request,
                arm=arm,
                ordinal=arm_ordinals[arm],
                pair_index=pair_index,
                position_in_pair=position_in_pair,
            )
            arm_ordinals[arm] += 1
            measured[arm].append(observation)
            order.append(arm)

    generated = _summarize_arm(GENERATED_ARM, measured[GENERATED_ARM])
    jev = _summarize_arm(JEV_ARM, measured[JEV_ARM])
    return generated, jev, tuple(order)


def build_report(
    *,
    repository: RepositoryIdentity,
    llama_cpp_source: SourceRepositoryIdentity,
    runtime: LlamaCppRuntimeIdentity,
    model_artifact: ModelArtifactIdentity,
    gpu: GpuIdentity,
    request: BoundedChoiceRequest,
    generated: BenchmarkArmReport,
    jev: BenchmarkArmReport,
    measured_call_order: tuple[str, ...],
    warmup_calls_per_arm: int,
    measured_calls_per_arm: int,
) -> JevBoundedBenchmarkReport:
    qualified = (
        generated.provider_failure_count == 0
        and jev.provider_failure_count == 0
        and generated.incorrect_outcome_count == 0
        and jev.incorrect_outcome_count == 0
        and generated.successful_call_count == measured_calls_per_arm
        and jev.successful_call_count == measured_calls_per_arm
    )
    return JevBoundedBenchmarkReport(
        evidence_class="model_or_system_quality",
        repository=repository,
        llama_cpp_source=llama_cpp_source,
        runtime=runtime,
        model_artifact=model_artifact,
        gpu=gpu,
        request_id=request.request_id,
        expected_choice_id=EXPECTED_CHOICE_ID,
        warmup_calls_per_arm=warmup_calls_per_arm,
        measured_calls_per_arm=measured_calls_per_arm,
        measured_call_order=measured_call_order,
        server_model_load_included=False,
        cache_reuse_qualified=False,
        generated=generated,
        jev=jev,
        qualified=qualified,
    )


def inspect_source_repository(root: str | Path) -> SourceRepositoryIdentity:
    path = Path(root).expanduser().resolve()
    if not (path / ".git").exists():
        raise JevBenchmarkError(f"llama_cpp_root is not a git checkout: {path}")
    status = _run_git(path, "status", "--porcelain")
    if status.strip():
        raise JevBenchmarkError(
            "Jev benchmark requires a clean llama.cpp source checkout"
        )
    return SourceRepositoryIdentity(
        root=str(path),
        head=_run_git(path, "rev-parse", "HEAD").strip(),
        tree=_run_git(path, "rev-parse", "HEAD^{tree}").strip(),
    )


def inspect_model_artifact(path: str | Path) -> ModelArtifactIdentity:
    artifact = Path(path).expanduser().resolve()
    if not artifact.is_file():
        raise JevBenchmarkError(f"model_artifact is not a file: {artifact}")
    digest = hashlib.sha256()
    with artifact.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return ModelArtifactIdentity(
        path=str(artifact),
        size_bytes=artifact.stat().st_size,
        sha256=digest.hexdigest(),
    )


def inspect_gpu() -> GpuIdentity:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise JevBenchmarkError(
            f"nvidia-smi could not start: {type(exc).__name__}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JevBenchmarkError(
            f"nvidia-smi failed ({completed.returncode}): {detail}"
        )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise JevBenchmarkError(
            "Jev benchmark requires exactly one visible NVIDIA GPU"
        )
    parts = [part.strip() for part in lines[0].split(",", maxsplit=1)]
    if len(parts) != 2 or not all(parts):
        raise JevBenchmarkError("nvidia-smi GPU identity response is invalid")
    return GpuIdentity(name=parts[0], driver_version=parts[1])


def validate_runtime_binding(
    *,
    source: SourceRepositoryIdentity,
    runtime: LlamaCppRuntimeIdentity,
    model_artifact: ModelArtifactIdentity,
) -> None:
    if runtime.build_info is None:
        raise JevBenchmarkError(
            "llama.cpp /props did not expose build_info for source binding"
        )
    short_head = source.head[:7]
    if short_head not in runtime.build_info:
        raise JevBenchmarkError(
            "served llama.cpp build_info does not identify the selected Jev source "
            f"HEAD {short_head}: {runtime.build_info}"
        )
    if runtime.model_path is None:
        raise JevBenchmarkError(
            "llama.cpp /props did not expose model_path for artifact binding"
        )
    served_model = Path(runtime.model_path).expanduser().resolve()
    if served_model != Path(model_artifact.path):
        raise JevBenchmarkError(
            "served llama.cpp model_path does not match the hashed model artifact"
        )


def run_live_benchmark(
    *,
    origin: str,
    timeout: float,
    repo_root: str | Path,
    llama_cpp_root: str | Path,
    model_artifact: str | Path,
    warmup_calls_per_arm: int,
    measured_calls_per_arm: int,
) -> JevBoundedBenchmarkReport:
    repository = inspect_repository(repo_root)
    source = inspect_source_repository(llama_cpp_root)
    runtime = inspect_llama_cpp_runtime(origin=origin, timeout=timeout)
    artifact = inspect_model_artifact(model_artifact)
    gpu = inspect_gpu()
    validate_runtime_binding(
        source=source,
        runtime=runtime,
        model_artifact=artifact,
    )

    request = benchmark_request()
    generated_engine = RelayEngine(
        LlamaCppRelayProvider(
            endpoint=f"{runtime.origin}/v1/chat/completions",
            model=runtime.model,
            timeout=timeout,
        )
    )
    jev_engine = RelayEngine(
        LlamaCppRelayProvider(
            endpoint=f"{runtime.origin}/v1/chat/completions",
            systemone_endpoint=f"{runtime.origin}/v1/systemone",
            model=runtime.model,
            timeout=timeout,
        )
    )

    generated, jev, order = run_matched_benchmark(
        generated_engine=generated_engine,
        jev_engine=jev_engine,
        request=request,
        warmup_calls_per_arm=warmup_calls_per_arm,
        measured_calls_per_arm=measured_calls_per_arm,
    )
    return build_report(
        repository=repository,
        llama_cpp_source=source,
        runtime=runtime,
        model_artifact=artifact,
        gpu=gpu,
        request=request,
        generated=generated,
        jev=jev,
        measured_call_order=order,
        warmup_calls_per_arm=warmup_calls_per_arm,
        measured_calls_per_arm=measured_calls_per_arm,
    )


def _run_observation(
    *,
    engine: RelayEngine,
    request: BoundedChoiceRequest,
    arm: str,
    ordinal: int,
    pair_index: int,
    position_in_pair: int,
) -> BenchmarkObservation:
    started_ns = time.perf_counter_ns()
    try:
        result = engine(request)
    except LlamaCppProviderError as exc:
        wall_elapsed_ns = time.perf_counter_ns() - started_ns
        return BenchmarkObservation(
            arm=arm,
            ordinal=ordinal,
            pair_index=pair_index,
            position_in_pair=position_in_pair,
            wall_elapsed_ns=wall_elapsed_ns,
            wall_elapsed_seconds=wall_elapsed_ns / 1_000_000_000,
            provider_elapsed_ns=None,
            provider_elapsed_seconds=None,
            final_status=None,
            choice_id=None,
            correct=False,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            finish_reason=None,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    wall_elapsed_ns = time.perf_counter_ns() - started_ns
    _validate_bounded_result(result)
    attempt = result.attempts[0]
    return BenchmarkObservation(
        arm=arm,
        ordinal=ordinal,
        pair_index=pair_index,
        position_in_pair=position_in_pair,
        wall_elapsed_ns=wall_elapsed_ns,
        wall_elapsed_seconds=wall_elapsed_ns / 1_000_000_000,
        provider_elapsed_ns=attempt.elapsed_ns,
        provider_elapsed_seconds=attempt.elapsed_s,
        final_status=result.status.value,
        choice_id=result.choice_id,
        correct=(
            result.status is DecisionStatus.RESOLVED
            and result.choice_id == EXPECTED_CHOICE_ID
        ),
        prompt_tokens=attempt.call_facts.prompt_tokens,
        completion_tokens=attempt.call_facts.completion_tokens,
        total_tokens=attempt.call_facts.total_tokens,
        finish_reason=attempt.call_facts.finish_reason,
        error_type=None,
        error_message=None,
    )


def _validate_bounded_result(result: RelayEngineResult) -> None:
    if not isinstance(result, RelayEngineResult):
        raise JevBenchmarkError("benchmark engine did not return RelayEngineResult")
    if result.provider_call_count != 1 or result.escalated:
        raise JevBenchmarkError(
            "direct #257 benchmark must contain exactly one BOUNDED provider call"
        )
    if len(result.attempts) != 1 or result.attempts[0].mode is not CognitionMode.BOUNDED:
        raise JevBenchmarkError(
            "direct #257 benchmark observed a non-BOUNDED attempt"
        )


def _summarize_arm(
    arm: str,
    observations: list[BenchmarkObservation],
) -> BenchmarkArmReport:
    successful = [
        observation
        for observation in observations
        if observation.error_type is None
    ]
    provider_latencies = [
        observation.provider_elapsed_ns
        for observation in successful
        if observation.provider_elapsed_ns is not None
    ]
    wall_latencies = [observation.wall_elapsed_ns for observation in observations]
    failures = len(observations) - len(successful)
    incorrect = sum(
        1
        for observation in successful
        if not observation.correct
    )
    return BenchmarkArmReport(
        arm=arm,
        measured_call_count=len(observations),
        successful_call_count=len(successful),
        provider_failure_count=failures,
        incorrect_outcome_count=incorrect,
        provider_latency=(
            _latency_summary(provider_latencies)
            if provider_latencies
            else None
        ),
        wall_latency=_latency_summary(wall_latencies),
        observations=tuple(observations),
    )


def _latency_summary(values: list[int]) -> LatencySummary:
    if not values:
        raise JevBenchmarkError("latency summary requires at least one value")
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    median_ns = float(statistics.median(ordered))
    p95_ns = ordered[p95_index]
    max_ns = ordered[-1]
    return LatencySummary(
        count=len(ordered),
        median_ns=median_ns,
        p95_ns=p95_ns,
        max_ns=max_ns,
        median_seconds=median_ns / 1_000_000_000,
        p95_seconds=p95_ns / 1_000_000_000,
        max_seconds=max_ns / 1_000_000_000,
    )


def _pair_order(pair_index: int) -> tuple[str, str]:
    return (
        (GENERATED_ARM, JEV_ARM)
        if pair_index % 2 == 0
        else (JEV_ARM, GENERATED_ARM)
    )


def _run_git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise JevBenchmarkError(
            f"git command could not start: {type(exc).__name__}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JevBenchmarkError(
            f"git command failed ({completed.returncode}): {detail}"
        )
    return completed.stdout


def _require_non_negative_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_positive_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the #257 matched generated-BOUNDED vs Jev BOUNDED benchmark "
            "against one already-running Jev-capable llama.cpp server."
        )
    )
    parser.add_argument(
        "--origin",
        default="http://127.0.0.1:1234",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--llama-cpp-root", required=True)
    parser.add_argument("--model-artifact", required=True)
    parser.add_argument("--warmup-calls-per-arm", type=int, default=2)
    parser.add_argument("--measured-calls-per-arm", type=int, default=24)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = run_live_benchmark(
        origin=args.origin,
        timeout=args.timeout,
        repo_root=args.repo_root,
        llama_cpp_root=args.llama_cpp_root,
        model_artifact=args.model_artifact,
        warmup_calls_per_arm=args.warmup_calls_per_arm,
        measured_calls_per_arm=args.measured_calls_per_arm,
    )
    print(
        json.dumps(
            asdict(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.qualified else 2


if __name__ == "__main__":
    raise SystemExit(main())
