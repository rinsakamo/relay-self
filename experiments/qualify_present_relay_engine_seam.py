from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.llama_cpp.qualify_relay_engine import (
    LlamaCppQualificationError,
    LlamaCppRuntimeIdentity,
    RepositoryIdentity,
    inspect_llama_cpp_runtime,
    inspect_repository,
)
from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from experiments.present_relay_engine_seam import run_reference_epoch
from relay_self.relay_engine import DecisionStatus, RelayEngine
from relay_self.skill import SkillState


@dataclass(frozen=True, slots=True)
class PresentRelayQualificationReport:
    evidence_class: str
    repository: RepositoryIdentity
    runtime: LlamaCppRuntimeIdentity
    broad_fact_count: int
    local_fact_count: int
    request_id: str
    request_intent_id: str | None
    request_focus: str | None
    context_keys: tuple[str, ...]
    context_provenance: tuple[dict[str, str], ...]
    final_status: str
    choice_id: str | None
    expected_choice_id: str
    broadened: bool
    reprojected: bool
    escalated: bool
    attempts: tuple[dict[str, object], ...]
    provider_call_count: int
    elapsed_ns: int
    elapsed_seconds: float
    observed_prompt_tokens: int | None
    observed_completion_tokens: int | None
    skill_execution_id: str
    skill_id: str
    skill_intent_id: str
    skill_state: str
    open_action_count: int
    qualified: bool


def qualify_present_relay_seam(
    engine: RelayEngine,
    runtime: LlamaCppRuntimeIdentity,
    repository: RepositoryIdentity,
) -> PresentRelayQualificationReport:
    epoch = run_reference_epoch(engine)

    if epoch.broadened or epoch.reprojected:
        raise LlamaCppQualificationError(
            "sufficient reference projection unexpectedly required recovery"
        )
    if epoch.cognition.status is not DecisionStatus.RESOLVED:
        raise LlamaCppQualificationError(
            "Present-backed RelayEngine path remained unresolved"
        )
    if epoch.cognition.choice_id != "cave":
        raise LlamaCppQualificationError(
            "Present-backed RelayEngine selected unexpected destination: "
            f"{epoch.cognition.choice_id}; expected cave"
        )
    if epoch.execution is None:
        raise LlamaCppQualificationError(
            "resolved Present-backed cognition did not start SkillExecution"
        )
    if epoch.execution.state is not SkillState.STARTED:
        raise LlamaCppQualificationError(
            "Present-backed handoff did not preserve STARTED SkillExecution"
        )
    if epoch.execution.intent_id != epoch.request.intent_id:
        raise LlamaCppQualificationError(
            "SkillExecution intent does not match request Current Intent"
        )

    return PresentRelayQualificationReport(
        evidence_class="model_or_system_quality",
        repository=repository,
        runtime=runtime,
        broad_fact_count=len(epoch.broad.facts),
        local_fact_count=len(epoch.local.facts),
        request_id=epoch.request.request_id,
        request_intent_id=epoch.request.intent_id,
        request_focus=epoch.request.focus,
        context_keys=tuple(
            datum.key for datum in epoch.request.context
        ),
        context_provenance=tuple(
            {
                "source": datum.provenance.source,
                "reference": datum.provenance.reference,
            }
            for datum in epoch.request.context
        ),
        final_status=epoch.cognition.status.value,
        choice_id=epoch.cognition.choice_id,
        expected_choice_id="cave",
        broadened=epoch.broadened,
        reprojected=epoch.reprojected,
        escalated=epoch.cognition.escalated,
        attempts=tuple(
            {
                "mode": attempt.mode.value,
                "status": attempt.status.value,
                "choice_id": attempt.choice_id,
                "reason": attempt.reason,
                "elapsed_ns": attempt.elapsed_ns,
                "elapsed_seconds": attempt.elapsed_s,
                "requested_max_output_tokens": (
                    attempt.call_facts.requested_max_output_tokens
                ),
                "prompt_tokens": attempt.call_facts.prompt_tokens,
                "completion_tokens": attempt.call_facts.completion_tokens,
                "total_tokens": attempt.call_facts.total_tokens,
                "finish_reason": attempt.call_facts.finish_reason,
            }
            for attempt in epoch.cognition.attempts
        ),
        provider_call_count=epoch.cognition.provider_call_count,
        elapsed_ns=epoch.cognition.elapsed_ns,
        elapsed_seconds=epoch.cognition.elapsed_s,
        observed_prompt_tokens=epoch.cognition.observed_prompt_tokens,
        observed_completion_tokens=(
            epoch.cognition.observed_completion_tokens
        ),
        skill_execution_id=epoch.execution.execution_id,
        skill_id=epoch.execution.skill_id,
        skill_intent_id=epoch.execution.intent_id,
        skill_state=epoch.execution.state.value,
        open_action_count=0,
        qualified=True,
    )


def run_live_qualification(
    *,
    origin: str = "http://127.0.0.1:1234",
    timeout: float = 60.0,
    repo_root: str | Path = ".",
) -> PresentRelayQualificationReport:
    repository = inspect_repository(repo_root)
    runtime = inspect_llama_cpp_runtime(
        origin=origin,
        timeout=timeout,
    )
    provider = LlamaCppRelayProvider(
        endpoint=f"{runtime.origin}/v1/chat/completions",
        model=runtime.model,
        timeout=timeout,
    )
    return qualify_present_relay_seam(
        RelayEngine(provider),
        runtime,
        repository,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify the Present projection -> RelayEngine -> "
            "SkillExecution FLEE seam on real llama.cpp."
        )
    )
    parser.add_argument(
        "--origin",
        default="http://127.0.0.1:1234",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--repo-root", default=".")
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = run_live_qualification(
        origin=args.origin,
        timeout=args.timeout,
        repo_root=args.repo_root,
    )
    print(
        json.dumps(
            asdict(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
