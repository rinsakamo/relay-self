"""M-only optional S completed-epoch to RelayEngine usage handoff.

S42 cognition_requested may denote a deterministic WorldConditionedChoice:
it is NOT proof of a provider call. Measure only an already-returned original
RelayEngine result bound by identity to the completed S owner epoch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_cognitive_lifecycle import CognitiveWorkReceipt
from experiments.metabolism_relay_engine_usage import (
    OwnerEngineCall,
    OwnerEpochEngineBinding,
    cognitive_receipt_from_engine_results,
)

HandoffStatus = Literal["DISABLED", "RECORDED", "UNMEASURED", "DEFERRED"]


@dataclass(frozen=True, slots=True)
class SOwnerEngineCostObservation:
    original_s_epoch: object
    status: HandoffStatus
    reason: str
    usage: CognitiveWorkReceipt | None = None
    source_attested: bool = False
    action_authority: bool = False
    native_reads: int = 0
    model_invocations: int = 0
    action_issues: int = 0
    energy_debits: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


def observe_s_owner_engine_usage(
    *,
    enabled: bool = False,
    original_s_epoch: object,
    original_slm_tap: object = None,
    engine_call: OwnerEngineCall | None = None,
    binding: OwnerEpochEngineBinding | None = None,
) -> SOwnerEngineCostObservation:
    """Post-decision passive tap: fail closed without affecting S or Action."""
    def skipped(status: HandoffStatus, reason: str) -> SOwnerEngineCostObservation:
        return SOwnerEngineCostObservation(original_s_epoch, status, reason)

    if type(enabled) is not bool or not enabled:
        return skipped("DISABLED", "not_enabled_or_invalid_flag")
    try:
        from experiments.metabolism_slm_dev_host_tap import (
            SLMDevTapResult,
            bounded_s_l_m_audit_row,
        )
        from relay_self.epoch_plan import PlannedDecisionEpochResult
        from relay_self.relay_engine import OpenCognitionResult, RelayEngineResult
        from relay_self.runtime_coordination import DecisionEpochResult

        if (
            not isinstance(original_slm_tap, SLMDevTapResult)
            or original_slm_tap.original_s_epoch is not original_s_epoch
            or original_slm_tap.status != "RECORDED"
        ):
            return skipped("DEFERRED", "original_s_epoch_or_tap_not_admitted")
        row = bounded_s_l_m_audit_row(original_slm_tap)
        if isinstance(original_s_epoch, PlannedDecisionEpochResult):
            if not original_s_epoch.executed_work_ids:
                return skipped("DEFERRED", "original_s_epoch_or_tap_not_admitted")
            decision = original_s_epoch.decision
        else:
            decision = original_s_epoch
        if not isinstance(decision, DecisionEpochResult):
            return skipped("DEFERRED", "original_s_epoch_or_tap_not_admitted")
        if decision.next_action_deadline_ns is not None:
            return skipped("DEFERRED", "original_s_epoch_or_tap_not_admitted")

        # Deterministic S42 choices can mark cognition_requested=True.
        # No inference of model calls, even if the S result was admitted.
        actual_result = decision.cognition_result
        if not isinstance(actual_result, (OpenCognitionResult, RelayEngineResult)):
            if engine_call is not None or binding is not None:
                return skipped("DEFERRED", "non_engine_s_epoch_cannot_accept_meter")
            return skipped("UNMEASURED", "no_original_engine_result")
        if (
            decision.cognition_requested is not True
            or not isinstance(engine_call, OwnerEngineCall)
            or engine_call.result is not actual_result
            or not isinstance(binding, OwnerEpochEngineBinding)
        ):
            return skipped("DEFERRED", "engine_result_identity_or_binding_mismatch")
        usage = cognitive_receipt_from_engine_results(
            audit_row=row, binding=binding, completed_calls=(engine_call,),
        )
        return SOwnerEngineCostObservation(
            original_s_epoch, "RECORDED", "original_owner_engine_result",
            usage=usage,
        )
    except Exception:
        # Optional M diagnostic cannot interrupt S49. Do not swallow BaseException.
        return skipped("DEFERRED", "owner_source_or_engine_rejected")


def bounded_s_owner_engine_cost_row(
    observed: SOwnerEngineCostObservation,
) -> dict[str, object]:
    """Allowlisted telemetry without raw S epoch, model output or prompt."""
    if not isinstance(observed, SOwnerEngineCostObservation):
        raise ValueError("typed S owner engine observation required")
    if (
        observed.source_attested or observed.action_authority
        or any(type(getattr(observed, k)) is not int or getattr(observed, k) != 0
               for k in ("native_reads", "model_invocations", "action_issues",
                         "energy_debits", "learning_updates", "habit_grants"))
    ):
        raise ValueError("forged M telemetry authority")
    reasons = {
        "DISABLED": ("not_enabled_or_invalid_flag",),
        "RECORDED": ("original_owner_engine_result",),
        "UNMEASURED": ("no_original_engine_result",),
        "DEFERRED": (
            "original_s_epoch_or_tap_not_admitted",
            "non_engine_s_epoch_cannot_accept_meter",
            "engine_result_identity_or_binding_mismatch",
            "owner_source_or_engine_rejected",
        ),
    }
    if observed.reason not in reasons.get(observed.status, ()):
        raise ValueError("inconsistent S engine cost telemetry")
    if (observed.status == "RECORDED") != (observed.usage is not None):
        raise ValueError("unrecorded epoch cannot include cognitive meter")
    meter = observed.usage
    if meter is not None and (
        not isinstance(meter, CognitiveWorkReceipt)
        or meter.measurement_scope != "DECLARED_DEV_NOT_SOURCE_ATTESTED"
        or type(meter.provider_calls) is not int or meter.provider_calls < 1
    ):
        raise ValueError("invalid original model receipt")
    return {
        "schema": "M_S_OWNER_ENGINE_USAGE_DEV_V1",
        "status": observed.status,
        "reason": observed.reason,
        "session_id": meter.session_id if meter else None,
        "probe_seq": meter.probe_seq if meter else None,
        "request_id": meter.request_id if meter else None,
        "receipt_id": meter.receipt_id if meter else None,
        "level": meter.level if meter else None,
        "provider_calls": meter.provider_calls if meter else None,
        "input_tokens": meter.input_tokens if meter else None,
        "output_tokens": meter.output_tokens if meter else None,
        "wall_ns": meter.wall_ns if meter else None,
        "cpu_ns": None,
        "gpu_ns": None,
        "source_attested": False,
        "action_authority": False,
        "new_model_calls": 0,
        "action_issues": 0,
        "energy_debits": 0,
        "learning_updates": 0,
        "habit_grants": 0,
    }
