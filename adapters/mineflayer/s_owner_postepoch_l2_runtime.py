"""Opt-in S-owned post-epoch L2 OPEN over the canonical llama.cpp provider.

This is an executable seam for an *already returned* original S42 and a
RECORDED S/L8/M tap. It is NOT installed in the S49 runtime loop; callers
must explicitly authorize each request and supply real owner source objects.

No new Action issuer, no memory promotion, and no automatic retry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.s_owner_postepoch_l2_companion import (
    SPostEpochL2Companion,
    SPostEpochL2CompanionLease,
)
from relay_self.relay_engine import OpenCognitionRequest, RelayEngine

CallStatus = Literal["DISABLED", "DEFERRED", "RECORDED", "CALL_UNCERTAIN"]


@dataclass(frozen=True, slots=True)
class SPostEpochL2RuntimeResult:
    status: CallStatus
    reason: str
    companion: SPostEpochL2Companion | None
    requests_submitted: int = 0
    # A failed HTTP call may have reached the backend. Never claim zero usage.
    provider_calls_observed: int | None = None
    external_call_outcome_unknown: bool = False
    source_attested: bool = False
    action_authority: bool = False
    action_issues: int = 0
    energy_debits: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


class SPostEpochL2OpenRuntime:
    """Per-S-run single-writer budget. Failed submissions burn their lease."""

    def __init__(self, *, enabled: bool = False, max_calls: int = 1) -> None:
        if type(enabled) is not bool or type(max_calls) is not int or not 1 <= max_calls <= 3:
            raise ValueError("explicit opt-in and call cap 1..3 required")
        self.enabled = enabled
        self.max_calls = max_calls
        self._attempted: set[tuple[str, int, str]] = set()
        self._owner_objects: list[object] = []
        self._used = 0
        self._companion_lease = SPostEpochL2CompanionLease(
            enabled=True, max_epochs=max_calls,
        )

    @property
    def calls_reserved(self) -> int:
        return self._used

    def execute(
        self,
        *,
        original_s_epoch: object,
        original_slm_tap: object = None,
        request: object = None,
        binding: object = None,
        provider: object = None,
    ) -> SPostEpochL2RuntimeResult:
        """Execute exactly one owner-permitted OPEN *only after source preflight*."""
        def defer(reason: str) -> SPostEpochL2RuntimeResult:
            return SPostEpochL2RuntimeResult("DEFERRED", reason, None)

        if not self.enabled:
            return SPostEpochL2RuntimeResult("DISABLED", "not_enabled", None)

        # The source preflight runs before a possible network request.
        # A source pointer isn't proof of independent Minecraft provenance.
        try:
            from relay_self.epoch_plan import PlannedDecisionEpochResult
            from relay_self.world_conditioned_choice import WorldConditionedChoice

            from experiments.metabolism_cognitive_lifecycle import _check_audit
            from experiments.metabolism_relay_engine_usage import OwnerEpochEngineBinding
            from experiments.metabolism_slm_dev_host_tap import (
                SLMDevTapResult,
                bounded_s_l_m_audit_row,
            )
            from relay_self.runtime_coordination import DecisionEpochResult

            if (
                not isinstance(original_slm_tap, SLMDevTapResult)
                or original_slm_tap.original_s_epoch is not original_s_epoch
                or original_slm_tap.status != "RECORDED"
            ):
                return defer("source_not_admitted")
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
                or decision.next_action_deadline_ns is not None
                or decision.timed_out_actions
                or (isinstance(original_s_epoch, PlannedDecisionEpochResult)
                    and not original_s_epoch.executed_work_ids)
            ):
                return defer("source_not_admitted")
            if (
                not isinstance(request, OpenCognitionRequest)
                or request.focus != "POST_S_L2_SHADOW_DEV"
                or not isinstance(binding, OwnerEpochEngineBinding)
                or binding.level != "L2"
                or (binding.session_id, binding.probe_seq, binding.native_request_id)
                != source
            ):
                return defer("request_or_binding_rejected")
            if not isinstance(provider, LlamaCppRelayProvider):
                return defer("provider_not_canonical")
            parsed = urlsplit(provider.endpoint)
            if (
                parsed.scheme != "http"
                or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                or parsed.path != "/v1/chat/completions"
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment
                or parsed.port is None
            ):
                return defer("nonloopback_provider_rejected")
            if (
                source in self._attempted
                or any(p is original_s_epoch for p in self._owner_objects)
                or self._used >= self.max_calls
            ):
                return defer("duplicate_or_budget_exhausted")
        except (Exception,):
            return defer("preflight_rejected")

        # Reserve BEFORE network I/O. Even timeout, connection loss, or bad
        # response burns this call; backend may have completed it.
        self._attempted.add(source)
        self._owner_objects.append(original_s_epoch)
        self._used += 1
        try:
            actual = RelayEngine(provider).open(request)
        except Exception:
            return SPostEpochL2RuntimeResult(
                "CALL_UNCERTAIN", "provider_or_wire_failed",
                None, requests_submitted=1,
                provider_calls_observed=None,
                external_call_outcome_unknown=True,
            )
        observed = self._companion_lease.observe_after_owner(
            original_s_epoch=original_s_epoch,
            original_slm_tap=original_slm_tap,
            model_request=request,
            model_result=actual,
            engine_binding=binding,
        )
        if observed.status != "RECORDED":
            return SPostEpochL2RuntimeResult(
                "CALL_UNCERTAIN", "post_return_meter_rejected",
                None, requests_submitted=1,
                provider_calls_observed=None,
                external_call_outcome_unknown=True,
            )
        return SPostEpochL2RuntimeResult(
            "RECORDED", "one_returned_local_open",
            observed, requests_submitted=1, provider_calls_observed=1,
        )


def bounded_s_postepoch_runtime_row(
    result: SPostEpochL2RuntimeResult,
) -> dict[str, object]:
    """Small no-text audit; original S and raw model response never exported."""
    from adapters.mineflayer.s_owner_postepoch_l2_companion import (
        bounded_s_l2_companion_cost_row,
    )

    reasons = {
        "DISABLED": ("not_enabled",),
        "DEFERRED": (
            "source_not_admitted", "request_or_binding_rejected",
            "provider_not_canonical", "nonloopback_provider_rejected",
            "duplicate_or_budget_exhausted", "preflight_rejected",
        ),
        "RECORDED": ("one_returned_local_open",),
        "CALL_UNCERTAIN": ("provider_or_wire_failed", "post_return_meter_rejected"),
    }
    if (
        not isinstance(result, SPostEpochL2RuntimeResult)
        or result.reason not in reasons.get(result.status, ())
        or result.source_attested or result.action_authority
        or any(type(getattr(result, k)) is not int or getattr(result, k) != 0
               for k in ("action_issues", "energy_debits", "learning_updates",
                         "habit_grants"))
        or (result.status == "RECORDED") != (result.companion is not None)
        or (result.status in ("RECORDED", "CALL_UNCERTAIN"))
        != (result.requests_submitted == 1)
        or (result.status == "CALL_UNCERTAIN") != result.external_call_outcome_unknown
        or (result.status == "RECORDED") != (result.provider_calls_observed == 1)
        or (
            result.status not in ("RECORDED", "CALL_UNCERTAIN")
            and result.provider_calls_observed is not None
        )
    ):
        raise ValueError("forged S owner L2 runtime audit")
    companion_row = (
        bounded_s_l2_companion_cost_row(result.companion)
        if result.companion is not None else None
    )
    return {
        "schema": "S_POST_EPOCH_L2_LOCAL_OPEN_DEV_V1",
        "status": result.status,
        "reason": result.reason,
        "source_attested": False,
        "action_authority": False,
        "attempted_http_requests": result.requests_submitted,
        "backend_call_outcome_unknown": result.external_call_outcome_unknown,
        "observed_provider_calls": result.provider_calls_observed,
        "input_tokens": (
            companion_row["input_tokens"] if companion_row else None
        ),
        "output_tokens": (
            companion_row["output_tokens"] if companion_row else None
        ),
        "wall_ns": companion_row["wall_ns"] if companion_row else None,
        "cpu_ns": None,
        "gpu_ns": None,
        "action_issues": 0,
        "energy_debits": 0,
        "learning_updates": 0,
        "habit_grants": 0,
    }
