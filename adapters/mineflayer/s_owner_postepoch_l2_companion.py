"""S owner: post-completion L2 cost companion for an unchanged cheap S42 epoch.

S keeps the original source-admitted WorldConditionedChoice and Action owner.
A separately *already returned* L2 OpenCognitionResult may be attached as
POST_S_COMPANION for accounting, NOT as S42's cognition_result. This
module never invokes the model, modifies S, or issues Action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompanionStatus = Literal["DISABLED", "RECORDED", "DEFERRED"]


@dataclass(frozen=True, slots=True)
class SPostEpochL2Companion:
    original_s_epoch: object
    status: CompanionStatus
    reason: str
    usage: object | None = None
    cost_origin: str = "POST_S_SEPARATE_L2_COMPANION_NOT_CHEAP_S_COST"
    source_attested: bool = False
    action_authority: bool = False
    new_native_reads: int = 0
    new_provider_calls: int = 0
    action_issues: int = 0
    energy_debits: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


class SPostEpochL2CompanionLease:
    """Owner-local one-use source/engine-result lease, not physical attestation."""

    def __init__(self, *, enabled: bool = False, max_epochs: int = 8) -> None:
        if type(enabled) is not bool or type(max_epochs) is not int or not 1 <= max_epochs <= 8:
            raise ValueError("explicit bounded source lease required")
        self.enabled = enabled
        self.max_epochs = max_epochs
        self._seen_s: set[int] = set()
        self._seen_engine: set[int] = set()
        self._seen_source: set[tuple[str, int, str]] = set()

    def observe_after_owner(
        self,
        *,
        original_s_epoch: object,
        original_slm_tap: object = None,
        model_request: object = None,
        model_result: object = None,
        engine_binding: object = None,
    ) -> SPostEpochL2Companion:
        def deferred(reason: str) -> SPostEpochL2Companion:
            return SPostEpochL2Companion(original_s_epoch, "DEFERRED", reason)

        if not self.enabled:
            return SPostEpochL2Companion(original_s_epoch, "DISABLED", "not_enabled")
        try:
            from relay_self.epoch_plan import PlannedDecisionEpochResult
            from relay_self.world_conditioned_choice import WorldConditionedChoice

            from experiments.metabolism_cognitive_lifecycle import _check_audit
            from experiments.metabolism_relay_engine_usage import (
                OwnerEngineCall,
                OwnerEpochEngineBinding,
                cognitive_receipt_from_engine_results,
            )
            from experiments.metabolism_slm_dev_host_tap import (
                SLMDevTapResult,
                bounded_s_l_m_audit_row,
            )
            from relay_self.relay_engine import OpenCognitionRequest, OpenCognitionResult
            from relay_self.runtime_coordination import DecisionEpochResult

            if (
                not isinstance(original_slm_tap, SLMDevTapResult)
                or original_slm_tap.original_s_epoch is not original_s_epoch
                or original_slm_tap.status != "RECORDED"
            ):
                return deferred("owner_source_or_epoch_rejected")
            row = bounded_s_l_m_audit_row(original_slm_tap)
            source = _check_audit(row)
            decision = (
                original_s_epoch.decision
                if isinstance(original_s_epoch, PlannedDecisionEpochResult)
                else original_s_epoch
            )
            if (
                not isinstance(decision, DecisionEpochResult)
                or decision.cognition_requested is not True
                or not isinstance(decision.cognition_result, WorldConditionedChoice)
                or decision.cognition_result.selection.value != row["s_choice"]
                or decision.timed_out_actions
                or decision.next_action_deadline_ns is not None
                or (isinstance(original_s_epoch, PlannedDecisionEpochResult)
                    and not original_s_epoch.executed_work_ids)
            ):
                return deferred("owner_source_or_epoch_rejected")
            # This must be a *separate* completed L2 OPEN, not a replacement
            # of the cheap S42 cognition result.
            if (
                not isinstance(model_request, OpenCognitionRequest)
                or not isinstance(model_result, OpenCognitionResult)
                or model_result.request_id != model_request.request_id
                or not isinstance(engine_binding, OwnerEpochEngineBinding)
                or engine_binding.level != "L2"
                or (engine_binding.session_id, engine_binding.probe_seq,
                    engine_binding.native_request_id) != source
            ):
                return deferred("separate_l2_result_or_binding_rejected")
            if (
                id(original_s_epoch) in self._seen_s
                or id(model_result) in self._seen_engine
                or source in self._seen_source
                or len(self._seen_s) >= self.max_epochs
            ):
                return deferred("lease_replay_or_budget_rejected")
            # Do not reserve a lease until the externally supplied result and
            # its token usage pass checks. No source truth is minted here.
            usage = cognitive_receipt_from_engine_results(
                audit_row=row, binding=engine_binding,
                completed_calls=(OwnerEngineCall(model_request, model_result),),
            )
            self._seen_s.add(id(original_s_epoch))
            self._seen_engine.add(id(model_result))
            self._seen_source.add(source)
            return SPostEpochL2Companion(
                original_s_epoch, "RECORDED", "separate_returned_open_result",
                usage=usage,
            )
        except Exception:
            # Optional telemetry errors cannot change an already returned
            # owner Action/cognition decision.
            return deferred("owner_source_or_result_error")


def bounded_s_l2_companion_cost_row(readout: SPostEpochL2Companion) -> dict[str, object]:
    """Audit projection, never source bytes, prompt, model text or S objects."""
    from experiments.metabolism_cognitive_lifecycle import CognitiveWorkReceipt

    if not isinstance(readout, SPostEpochL2Companion):
        raise ValueError("typed S L2 companion readout required")
    reasons = {
        "DISABLED": ("not_enabled",),
        "RECORDED": ("separate_returned_open_result",),
        "DEFERRED": (
            "owner_source_or_epoch_rejected",
            "separate_l2_result_or_binding_rejected",
            "lease_replay_or_budget_rejected",
            "owner_source_or_result_error",
        ),
    }
    if (
        readout.reason not in reasons.get(readout.status, ())
        or readout.cost_origin != "POST_S_SEPARATE_L2_COMPANION_NOT_CHEAP_S_COST"
        or readout.source_attested or readout.action_authority
        or any(type(getattr(readout, field)) is not int or getattr(readout, field) != 0
               for field in ("new_native_reads", "new_provider_calls",
                             "action_issues", "energy_debits", "learning_updates",
                             "habit_grants"))
        or ((readout.status == "RECORDED") != (readout.usage is not None))
    ):
        raise ValueError("forged owner L2 companion status or authority")
    meter = readout.usage
    if meter is not None and (
        not isinstance(meter, CognitiveWorkReceipt)
        or meter.level != "L2" or meter.provider_calls != 1
        or meter.measurement_scope != "DECLARED_DEV_NOT_SOURCE_ATTESTED"
    ):
        raise ValueError("forged L2 companion meter")
    return {
        "schema": "S_POST_S42_L2_COMPANION_COST_DEV_V1",
        "status": readout.status,
        "reason": readout.reason,
        "cost_origin": readout.cost_origin,
        "session_id": meter.session_id if meter else None,
        "probe_seq": meter.probe_seq if meter else None,
        "request_id": meter.request_id if meter else None,
        "receipt_id": meter.receipt_id if meter else None,
        "provider_calls": meter.provider_calls if meter else None,
        "input_tokens": meter.input_tokens if meter else None,
        "output_tokens": meter.output_tokens if meter else None,
        "wall_ns": meter.wall_ns if meter else None,
        "cpu_ns": None,
        "gpu_ns": None,
        "native_source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_provider_calls": 0,
        "action_issues": 0,
        "energy_debits": 0,
        "learning_updates": 0,
        "habit_grants": 0,
    }
