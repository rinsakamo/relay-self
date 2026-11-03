"""M #616 read-only B0 owner decisions alongside original S49/S14/S16.

S separately owns B0EnergyLedger and computes B0Decision from already-read
native S49 probes. This M readout never advances that ledger, bills Minecraft
energy, issues an Action or changes the original L0. In this bridge the B0
model energy stays at its *initial unadvanced simulated state*; true physical
World-tick energy is UNKNOWN. S42/L8 independently remain NOT_SUPPLIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_b0_cognition import read_b0_resource_context
from experiments.metabolism_s49_s14_planned_owner_join import (
    bounded_m_s14_planned_row,
    observe_s49_s14_planned,
)

Status = Literal["DISABLED", "RECORDED", "DEFERRED"]


@dataclass(frozen=True, slots=True)
class M616B0OriginalDecisionObservation:
    status: Status
    reason: str
    session_id: str | None = None
    original_b0: object | None = None
    resources: tuple[object, ...] = ()
    source_attested: bool = False
    action_authority: bool = False


def observe_m_s49_b0_owner_decisions(
    *,
    enabled: bool = False,
    original_l0: object,
    original_planned: object,
    original_b0: object,
    m_admission_row: object,
    m_s16_row: object,
    m_planned_row: object,
) -> M616B0OriginalDecisionObservation:
    """Accept the actual three independent S callback wrappers, not JSON."""
    if type(enabled) is not bool or not enabled:
        return M616B0OriginalDecisionObservation("DISABLED", "not_enabled")
    try:
        from adapters.mineflayer.s49_b0_owner_decision_witness import (
            S49OriginalB0DecisionBatch,
            validate_original_b0_decisions,
        )
        from adapters.mineflayer.self_body_m0_projection import (
            compose_b0_cognition_views,
        )

        planned = observe_s49_s14_planned(
            enabled=True, original_l0=original_l0,
            original_planned=original_planned,
            m_admission_row=m_admission_row, m_s16_row=m_s16_row,
        )
        if (
            planned.status != "RECORDED"
            or bounded_m_s14_planned_row(planned) != m_planned_row
            or not isinstance(original_b0, S49OriginalB0DecisionBatch)
            or original_b0.original_l0 is original_l0
            or original_b0.original_l0 is original_planned.original_l0
            or original_b0.session_id != planned.session_id
            or len(original_l0.steps) != len(original_b0.original_l0.steps)
            or any(
                a.step is not b.step
                or a.probe is not b.probe
                or a.action_receipt is not b.action_receipt
                for a, b in zip(original_l0.steps, original_b0.original_l0.steps)
            )
        ):
            raise ValueError("B0 original callback not source joined with S49")
        validate_original_b0_decisions(original_b0)

        ledger = original_b0.owner_ledger
        # M projection never observes the evaluator's true energy directly:
        # project from the *exact original S B0 owner decision* and sensor.
        owner_resources = []
        for item in original_b0.original_decisions:
            probe = item.original_probe
            decision = item.original_decision
            views = compose_b0_cognition_views(
                probe, ledger, decision,
                self_id="self-s49-b0-dev",
                epoch_id=f"b0-owner-native-{probe.seq}",
            )
            measured = read_b0_resource_context(
                views, owner_decision=decision,
                config=ledger.config, sensor=ledger.sensor,
                noise_bound=None,
            )
            if (
                measured.session_id != original_b0.session_id
                or measured.native_seq != probe.seq
                or measured.owner_tick != 0
                or measured.original_l0_kind != decision.kind
                or any(f.affordability != "UNKNOWN" for f in measured.facts)
                or len(measured.facts) != 2
                or measured.energy_lower is not None
                or measured.energy_upper is not None
            ):
                raise ValueError("unsupported B0 model confidence / World energy")
            owner_resources.append(measured)
        if len(owner_resources) != len(original_l0.steps):
            raise ValueError("partial original B0 resource context")
        return M616B0OriginalDecisionObservation(
            "RECORDED", "original_b0_decision_only_source_bound",
            session_id=original_b0.session_id, original_b0=original_b0,
            resources=tuple(owner_resources),
        )
    except Exception:
        # No partial data or actions on failure: the S49 World remains owner.
        return M616B0OriginalDecisionObservation(
            "DEFERRED", "original_b0_decision_source_rejected",
        )


class M616B0DecisionLease:
    def __init__(self, *, enabled: bool = False) -> None:
        if type(enabled) is not bool:
            raise ValueError("boolean B0 read-only opt-in required")
        self.enabled = enabled
        self._used = False

    def admit(self, **kwargs: object) -> M616B0OriginalDecisionObservation:
        if not self.enabled:
            return M616B0OriginalDecisionObservation("DISABLED", "not_enabled")
        if self._used:
            return M616B0OriginalDecisionObservation(
                "DEFERRED", "original_b0_decision_source_rejected",
            )
        self._used = True
        return observe_m_s49_b0_owner_decisions(enabled=True, **kwargs)


def bounded_m_b0_original_decision_row(
    value: M616B0OriginalDecisionObservation,
) -> dict[str, object]:
    allowed = {
        "DISABLED": "not_enabled",
        "RECORDED": "original_b0_decision_only_source_bound",
        "DEFERRED": "original_b0_decision_source_rejected",
    }
    if (
        not isinstance(value, M616B0OriginalDecisionObservation)
        or allowed.get(value.status) != value.reason
        or value.source_attested or value.action_authority
        or (
            (value.status == "RECORDED")
            != (value.original_b0 is not None)
        )
        or (
            value.status != "RECORDED"
            and (value.session_id is not None or value.resources)
        )
    ):
        raise ValueError("forged M B0 source status")
    accepted = value.status == "RECORDED"
    if accepted and (
        type(value.session_id) is not str or not value.session_id
        or not 1 <= len(value.resources) <= 8
        or any(
            getattr(r, "session_id", None) != value.session_id
            or getattr(r, "owner_tick", None) != 0
            or getattr(r, "energy_lower", "forged") is not None
            or getattr(r, "energy_upper", "forged") is not None
            for r in value.resources
        )
    ):
        raise ValueError("forged M B0 ledger or sensor confidence")
    return {
        "schema": "M_S49_ORIGINAL_B0_DECISION_ONLY_DEV_V1",
        "status": value.status, "reason": value.reason,
        "session_id": value.session_id if accepted else None,
        "decision_count": len(value.resources) if accepted else None,
        "decisions": [
            {
                "probe_seq": r.native_seq,
                "owner_model_tick": r.owner_tick,
                "b0_kind": r.original_l0_kind,
                "model_cost_wait": r.facts[0].modeled_energy_cost,
                "model_cost_move": r.facts[1].modeled_energy_cost,
                "affordability_wait": r.facts[0].affordability,
                "affordability_move": r.facts[1].affordability,
            }
            for r in value.resources
        ] if accepted else [],
        "energy_transition_count": 0,
        "energy_debits": 0,
        "food_credits": 0,
        "true_world_energy": "UNKNOWN_NO_PHYSICAL_ENERGY_TICK",
        "b0_owner_model_energy": "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST",
        "s42_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "provider_calls": None, "cpu_ns": None, "gpu_ns": None,
        "source_attested": False, "action_authority": False,
        "new_native_reads": 0, "new_model_calls": 0,
        "new_action_issues": 0, "learning_updates": 0,
    }
