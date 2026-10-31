"""M DEV side-tap: bounded, fault-contained read-only S/L8/M diagnostics.

The original S owner may call this *after* it has returned its own decision.
The outcome is never a policy proposal and must not be used as an S49 issuer
input. Disabled is the default. No imports of B0, L8 or native sources are
made from the disabled path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_s_l_m_post_epoch import (
    SLMPostEpochRejected,
    read_s_l_m_after_owner_epoch,
)

TapStatus = Literal["DISABLED", "RECORDED", "DEFERRED", "OBSERVER_ERROR"]
TapReason = Literal[
    "not_enabled", "invalid_flag", "complete",
    "owner_source_or_scope_rejected", "observer_internal_error",
]


@dataclass(frozen=True, slots=True)
class SLMDevTapResult:
    """Original S epoch identity is retained; diagnostics cannot issue Action."""

    original_s_epoch: object
    status: TapStatus
    reason: TapReason
    session_id: str | None = None
    probe_seq: int | None = None
    request_id: str | None = None
    s_choice: str | None = None
    l1_candidate: str | None = None
    l1_status: str | None = None
    m_model_tension: str | None = None
    l1_model_status: str | None = None
    source_scope: str = "DEV_OPTIONAL_S_L_M_AUDIT_NOT_ACTION_INPUT"
    native_source_attested: bool = False
    action_authority: bool = False
    new_native_reads: int = 0
    new_cognition_calls: int = 0
    action_issues: int = 0
    learning_updates: int = 0
    habit_grants: int = 0
    food_credits: int = 0


def observe_optional_s_l_m_dev(
    *,
    enabled: bool = False,
    original_s_epoch: object,
    probe: object = None,
    native: object = None,
    ledger: object = None,
    original_b0_decision: object = None,
    retained: object = None,
    self_id: str = "",
    epoch_id: str = "",
    learning: object | None = None,
    retention_enabled: bool | None = None,
    noise_bound: float | None = None,
) -> SLMDevTapResult:
    """Optional telemetry must not intercept or replay an original S decision.

    Calls existing source-checked passive reader once when enabled.
    Only expected source rejections become DEFERRED. Unexpected normal
    exceptions are OBSERVER_ERROR, with sanitized reason and no exception
    details disclosed. BaseException (KeyboardInterrupt/SystemExit) is
    intentionally not masked. No logging, socket, filesystem or callbacks.
    """
    if type(enabled) is not bool:
        return SLMDevTapResult(original_s_epoch, "DISABLED", "invalid_flag")
    if not enabled:
        return SLMDevTapResult(original_s_epoch, "DISABLED", "not_enabled")
    try:
        observed = read_s_l_m_after_owner_epoch(
            probe=probe,
            native=native,
            ledger=ledger,
            original_b0_decision=original_b0_decision,
            original_s_epoch=original_s_epoch,
            retained=retained,
            self_id=self_id,
            epoch_id=epoch_id,
            learning=learning,
            retention_enabled=retention_enabled,
            noise_bound=noise_bound,
        )
        if (
            observed.m.s_epoch is not original_s_epoch
            or observed.action_authority
            or observed.action_issues
            or observed.new_native_reads
            or observed.new_cognition_calls
            or observed.learning_updates
            or observed.habit_grants
            or observed.food_credits
            or observed.source_attested
        ):
            raise SLMPostEpochRejected("side-tap readout unexpectedly holds authority")
        return SLMDevTapResult(
            original_s_epoch,
            "RECORDED",
            "complete",
            session_id=observed.session_id,
            probe_seq=observed.probe_seq,
            request_id=observed.request_id,
            s_choice=observed.m.choice.value,
            l1_candidate=(
                observed.l8_m.l1_shadow_ref if observed.l8_m is not None else None
            ),
            l1_status=(
                observed.l8_m.l1_status if observed.l8_m is not None else None
            ),
            m_model_tension=observed.m.modeled_tension,
            l1_model_status=(
                observed.l8_m.l1_candidate_model_status
                if observed.l8_m is not None else None
            ),
        )
    except SLMPostEpochRejected:
        return SLMDevTapResult(
            original_s_epoch, "DEFERRED", "owner_source_or_scope_rejected",
        )
    except Exception:
        # DEV telemetry is an optional consumer: no application-layer S49
        # admission, deadline or execution is allowed to depend on this path.
        return SLMDevTapResult(
            original_s_epoch, "OBSERVER_ERROR", "observer_internal_error",
        )


def bounded_s_l_m_audit_row(result: SLMDevTapResult) -> dict[str, object]:
    """Allowlisted JSON-safe diagnostic row. No raw probes, health or Energy.

    The original owner epoch pointer is deliberately EXCLUDED. Identifiers
    are *references*, not authenticated Minecraft source certificates.
    """
    if not isinstance(result, SLMDevTapResult):
        raise ValueError("typed DEV tap result required")
    if (
        result.source_scope != "DEV_OPTIONAL_S_L_M_AUDIT_NOT_ACTION_INPUT"
        or result.native_source_attested
        or result.action_authority
        or any(getattr(result, k) != 0 for k in (
            "new_native_reads", "new_cognition_calls", "action_issues",
            "learning_updates", "habit_grants", "food_credits",
        ))
    ):
        raise ValueError("forged authority-bearing DEV tap result")
    if result.status != "RECORDED":
        if any(getattr(result, k) is not None for k in (
            "session_id", "probe_seq", "request_id", "s_choice",
            "l1_candidate", "l1_status", "m_model_tension",
            "l1_model_status",
        )):
            raise ValueError("unadmitted source values in skipped audit row")
    else:
        if (
            type(result.session_id) is not str or not result.session_id
            or type(result.request_id) is not str or not result.request_id
            or type(result.probe_seq) is not int or result.probe_seq < 0
            or result.s_choice not in ("WAIT", "MOVE_AWAY")
            or result.m_model_tension not in (
                "MOVE_MODEL_INSUFFICIENT", "MOVE_MODEL_AMBIGUOUS",
                "MOVE_MODEL_UNKNOWN", "WAIT_MODEL_INSUFFICIENT",
                "WAIT_MODEL_AMBIGUOUS", "WAIT_MODEL_UNKNOWN",
                "NO_MODEL_TENSION",
            )
        ):
            raise ValueError("malformed recorded audit source/choice")
    # This object is intentionally small, never more than bounded IDs.
    def short(value: str | None) -> str | None:
        if value is None:
            return None
        if type(value) is not str or len(value) > 192 or not value.isprintable():
            raise ValueError("unbounded or unsafe diagnostic string")
        return value

    return {
        "schema": "SLM_PASSIVE_DEV_AUDIT_V1",
        "status": result.status,
        "reason": result.reason,
        "session_id": short(result.session_id),
        "probe_seq": result.probe_seq,
        "request_id": short(result.request_id),
        "s_choice": short(result.s_choice),
        "l1_candidate": short(result.l1_candidate),
        "l1_status": short(result.l1_status),
        "m_model_tension": short(result.m_model_tension),
        "l1_model_status": short(result.l1_model_status),
        "source_scope": result.source_scope,
        "native_source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_cognition_calls": 0,
        "action_issues": 0,
        "learning_updates": 0,
        "habit_grants": 0,
        "food_credits": 0,
    }
