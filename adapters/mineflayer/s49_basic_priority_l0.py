"""Bug-0 common L0 choice surface for MOVE/EAT/REST/ATTACK (DEV).

Pure source-grounded prioritization only. An Action is never authorized, issued,
or executed here. S49 sole issuer, its S14 admissions and S51 delegated EAT
remain separate. Unsupported attack/rest and threatened movement DEFER.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.normal_action import (
    NormalEatingObservationStatus,
    NormalFoodL0,
)
from adapters.mineflayer.python_protocol import MineflayerObservation


@dataclass(frozen=True, slots=True)
class BasicPriorityDecision:
    session_id: str
    probe_seq: int
    selected: str  # WAIT | EAT | DEFER (only EAT is a positive candidate)
    reason: str
    preferred: str | None  # MOVE_AWAY | ATTACK | REST | EAT
    fallback: str | None
    food: float
    native_risk: str
    candidate_item: str | None = None
    candidate_slot: int | None = None
    action_issued: bool = False
    permission_granted: bool = False


class S49BasicPriorityL0:
    """One S49 session's native decision cursor; never owns an Action."""

    def __init__(self, session_id: str, *, max_decisions: int = 64) -> None:
        self.food = NormalFoodL0(session_id, max_decisions=max_decisions)
        self.session_id = session_id

    def acknowledge_verified_eat(self, receipt: EatingActionReceipt) -> None:
        """Record only the S49/S51 verified terminal, never mint EAT authority."""
        self.food.acknowledge_verified_eat(receipt)

    def decide(
        self, probe: MineflayerObservation, *, rest_requested: bool = False,
    ) -> BasicPriorityDecision:
        if type(rest_requested) is not bool:
            raise ValueError("REST request must be explicit, not inferred")
        observed = self.food.decide(probe)
        risk = observed.risk
        # A truncated or unhealthy source cannot mean a safe opportunity.
        if risk is NormalEatingObservationStatus.TRUNCATED_COVERAGE:
            selected, reason, preferred, fallback = (
                "DEFER", "COVERAGE_INCOMPLETE", None, None,
            )
        elif risk is NormalEatingObservationStatus.BODY_NOT_VIABLE:
            selected, reason, preferred, fallback = (
                "DEFER", "BODY_NOT_VIABLE", None, None,
            )
        elif risk is NormalEatingObservationStatus.OBSERVED_ENTITY_NEARBY:
            # No physical MOVE/ATTACK route or verified immediate response
            # is supplied by this policy-only projection.
            zombies = [e for e in probe.snapshot.nearby_entities if e.name == "zombie"]
            close_zombies = [z for z in zombies if z.distance < 4.0]
            if close_zombies:
                selected, reason, preferred, fallback = (
                    "DEFER", "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
                    "MOVE_AWAY", "ATTACK",
                )
            elif zombies:
                # The original S49 native movement gate also WAITs at >=4m.
                # A distant zombie is still not proof of global food safety.
                selected, reason, preferred, fallback = (
                    "WAIT", "DISTANT_ZOMBIE_MONITOR", None, None,
                )
            else:
                selected, reason, preferred, fallback = (
                    "DEFER", "UNQUALIFIED_NEARBY_ENTITY", None, None,
                )
        elif observed.selection == "EAT":
            # L0 requests consideration only. The S49 issuer must still
            # obtain separately scoped PROPOSE and ISSUE authorization.
            selected, reason, preferred, fallback = (
                "EAT", observed.reason, "EAT", None,
            )
        elif rest_requested:
            # REST is not yet backed by a genuine original native Action.
            selected, reason, preferred, fallback = (
                "DEFER", "REST_EXECUTOR_NOT_CONNECTED", "REST", None,
            )
        else:
            selected, reason, preferred, fallback = (
                "WAIT", observed.reason, None, None,
            )
        return BasicPriorityDecision(
            session_id=self.session_id, probe_seq=observed.probe_seq,
            selected=selected, reason=reason, preferred=preferred,
            fallback=fallback, food=observed.food, native_risk=risk.value,
            candidate_item=observed.choice.item_name,
            candidate_slot=observed.choice.item_slot,
        )
