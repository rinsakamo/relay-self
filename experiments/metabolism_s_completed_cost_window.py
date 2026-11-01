"""Bounded M-only longitudinal readback of original completed S owner epochs.

A source-joined S/L8/M tap and original S epoch are required for each
observation. Model usage is measured ONLY if the original S epoch includes
the exact completed typed RelayEngine result. Cheap deterministic S42 work
is UNMEASURED, not a modeled provider call or an asserted measured zero.

M never invokes S, cognition, Minecraft, Action or physical Energy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_cognitive_lifecycle import (
    CognitionCostSample,
    CognitiveLifecycleRejected,
    CognitiveLifecycleSummary,
    Outcome,
    Phase,
    summarize_cognitive_lifecycle,
)
from experiments.metabolism_relay_engine_usage import (
    OwnerEngineCall,
    OwnerEpochEngineBinding,
)
from experiments.metabolism_s_owner_engine_handoff import (
    observe_s_owner_engine_usage,
)

WindowStatus = Literal["DISABLED", "RECORDED", "DEFERRED"]


@dataclass(frozen=True, slots=True)
class SCompletedEpochCostSource:
    """Owner supplies originals once S has returned. Never an Action input."""

    original_s_epoch: object
    original_slm_tap: object
    epoch_id: str
    task_id: str
    condition_id: str
    phase: Phase
    outcome: Outcome = "UNKNOWN"
    engine_call: OwnerEngineCall | None = None
    binding: OwnerEpochEngineBinding | None = None


@dataclass(frozen=True, slots=True)
class SCompletedCostWindow:
    status: WindowStatus
    reason: str
    attempted_epochs: int
    admitted_epochs: int = 0
    model_measured_epochs: int = 0
    unknown_cost_epochs: int = 0
    summary: CognitiveLifecycleSummary | None = None
    source_attested: bool = False
    action_authority: bool = False
    native_reads: int = 0
    model_invocations: int = 0
    action_issues: int = 0
    energy_debits: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


def observe_completed_s_cost_window(
    sources: tuple[SCompletedEpochCostSource, ...],
    *,
    enabled: bool = False,
) -> SCompletedCostWindow:
    """Fail atomically rather than silently omit a rejected owner epoch.

    No sample is emitted on an invalid World/session/epoch. All source
    mismatches are contained inside this passive post-owner diagnostic.
    """
    if type(enabled) is not bool or not enabled:
        return SCompletedCostWindow("DISABLED", "not_enabled", 0)
    if type(sources) is not tuple or not 1 <= len(sources) <= 64:
        return SCompletedCostWindow("DEFERRED", "invalid_bounded_window", 0)
    try:
        from experiments.metabolism_slm_dev_host_tap import (
            SLMDevTapResult,
            bounded_s_l_m_audit_row,
        )

        samples = []
        measured = 0
        seen_owner_epochs: set[int] = set()
        seen_model_results: set[int] = set()
        for item in sources:
            if not isinstance(item, SCompletedEpochCostSource):
                raise CognitiveLifecycleRejected("typed completed owner source needed")
            # A new native probe must never replay an old completed S epoch.
            identity = id(item.original_s_epoch)
            if identity in seen_owner_epochs:
                raise CognitiveLifecycleRejected("original S epoch object replayed")
            seen_owner_epochs.add(identity)
            tap = item.original_slm_tap
            if (
                not isinstance(tap, SLMDevTapResult)
                or tap.original_s_epoch is not item.original_s_epoch
                or tap.status != "RECORDED"
            ):
                raise CognitiveLifecycleRejected("source-joined original epoch missing")
            row = bounded_s_l_m_audit_row(tap)
            observed = observe_s_owner_engine_usage(
                enabled=True,
                original_s_epoch=item.original_s_epoch,
                original_slm_tap=tap,
                engine_call=item.engine_call,
                binding=item.binding,
            )
            if observed.status not in ("RECORDED", "UNMEASURED"):
                raise CognitiveLifecycleRejected("engine source admission rejected")
            if observed.status == "RECORDED":
                model_id = id(item.engine_call.result)
                if model_id in seen_model_results:
                    raise CognitiveLifecycleRejected("completed model result replayed")
                seen_model_results.add(model_id)
                measured += 1
            samples.append(CognitionCostSample(
                epoch_id=item.epoch_id,
                task_id=item.task_id,
                condition_id=item.condition_id,
                phase=item.phase,
                outcome=item.outcome,
                audit_row=row,
                usage=observed.usage,
            ))
        summary = summarize_cognitive_lifecycle(tuple(samples))
        return SCompletedCostWindow(
            status="RECORDED",
            reason="source_joined_postowner_readback",
            attempted_epochs=len(sources),
            admitted_epochs=len(sources),
            model_measured_epochs=measured,
            unknown_cost_epochs=len(sources) - measured,
            summary=summary,
        )
    except Exception:
        # Optional readout cannot interfere with owner execution; fail
        # the whole batch rather than cherry-pick successful samples.
        return SCompletedCostWindow(
            "DEFERRED", "source_or_engine_window_rejected", len(sources),
        )


def bounded_completed_s_cost_window_row(
    result: SCompletedCostWindow,
) -> dict[str, object]:
    """Small counts and aggregate summary only; no raw owner objects."""
    if not isinstance(result, SCompletedCostWindow):
        raise ValueError("typed completed owner window required")
    expected_reason = {
        "DISABLED": "not_enabled",
        "DEFERRED": (
            "invalid_bounded_window",
            "source_or_engine_window_rejected",
        ),
        "RECORDED": "source_joined_postowner_readback",
    }
    reasons = expected_reason.get(result.status, ())
    if isinstance(reasons, str):
        reasons = (reasons,)
    if (
        result.reason not in reasons
        or result.source_attested
        or result.action_authority
        or any(type(getattr(result, k)) is not int or getattr(result, k) != 0
               for k in ("native_reads", "model_invocations", "action_issues",
                         "energy_debits", "learning_updates", "habit_grants"))
    ):
        raise ValueError("forged completed owner cost window")
    if result.status != "RECORDED":
        if (
            result.admitted_epochs != 0 or result.model_measured_epochs != 0
            or result.unknown_cost_epochs != 0 or result.summary is not None
        ):
            raise ValueError("unadmitted batch cannot expose cost summary")
    elif (
        result.summary is None or result.attempted_epochs != result.admitted_epochs
        or result.summary.epoch_count != result.admitted_epochs
        or result.unknown_cost_epochs + result.model_measured_epochs
        != result.admitted_epochs
        or result.summary.source_attested or result.summary.action_authority
    ):
        raise ValueError("invalid admitted batch counts")
    return {
        "schema": "M_S_OWNER_COST_WINDOW_DEV_V1",
        "status": result.status,
        "reason": result.reason,
        "attempted_epochs": result.attempted_epochs,
        "admitted_epochs": result.admitted_epochs,
        "model_measured_epochs": result.model_measured_epochs,
        "unknown_cost_epochs": result.unknown_cost_epochs,
        "source_attested": False,
        "action_authority": False,
        "native_reads": 0,
        "new_model_calls": 0,
        "action_issues": 0,
        "energy_debits": 0,
        "learning_updates": 0,
        "habit_grants": 0,
    }
