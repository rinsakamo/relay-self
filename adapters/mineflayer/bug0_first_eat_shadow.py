"""Non-issuing first-EAT source check using the *existing* S49 owner.

This module has no native send, grant creation, STOP promotion or learning
authority. A fresh local S49 ActionSupervisor is not proof that no other
physical issuer acted in the World; external one-issuer custody is separate.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.normal_action import (
    NormalEatingAuthorization,
    NormalEatingObservationStatus,
    NormalSessionActionExecutor,
    assess_normal_eating_observation,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.eat_hunger import EatCursor, EatStatus


class Bug0FirstEatShadowRejected(ValueError):
    """Unavailable or unsafe original-native first-EAT observation."""


@dataclass(frozen=True, slots=True)
class Bug0FirstEatShadow:
    session_id: str
    intent_id: str
    earlier_probe_seq: int
    current_probe_seq: int
    current_probe_request_id: str
    food_before: float
    candidate_item: str
    candidate_slot: int
    earlier_risk: str
    current_risk: str
    position_delta_max_m: float
    owner_prior_issued_actions: int = 0
    native_eat_commands_issued: int = 0
    s49_action_issued: bool = False
    independent_eat_grant_attested: bool = False
    complete_idle_world_ticks_attested: bool = False
    world_source_independently_attested: bool = False
    physical_eat_authorized: bool = False
    decision_status: str = "FOOD_SOURCE_CANDIDATE_NO_ACTION"


def inspect_bug0_first_eat_shadow(
    owner: NormalSessionActionExecutor,
    earlier: MineflayerObservation,
    current: MineflayerObservation,
) -> Bug0FirstEatShadow:
    """Observe one initial no-MOVE S49 owner, NEVER dispatch EAT.

    Two native probes are necessary, not full-tick idle or global safety
    evidence. The real EAT owner must independently check its authentic
    operator grant and native currentness at the actual issuance boundary.
    """
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or not isinstance(earlier, MineflayerObservation)
        or not isinstance(current, MineflayerObservation)
        or owner.intent.current_intent is None
        or owner.intent.pending_reconsideration is not None
        or owner._count != 0
        or owner._dispatched
        or owner._last_issued_probe_seq != -1
        or owner._post_move_settling_unqualified
        or owner.supervisor.open_actions
        or earlier.kind != "probe"
        or current.kind != "probe"
        or not earlier.request_id
        or not current.request_id
        or earlier.request_id == current.request_id
        or earlier.session_id != owner.session_id
        or current.session_id != owner.session_id
        or earlier.provenance.source != "mineflayer"
        or current.provenance.source != "mineflayer"
        or not earlier.seq < current.seq <= earlier.seq + 32
    ):
        raise Bug0FirstEatShadowRejected("fresh one-owner two-probe source required")
    try:
        earlier_risk = assess_normal_eating_observation(earlier)
        current_risk = assess_normal_eating_observation(current)
    except ValueError as exc:
        raise Bug0FirstEatShadowRejected("invalid native food risk source") from exc
    if (
        earlier_risk is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
        or current_risk is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
    ):
        raise Bug0FirstEatShadowRejected("native source contains observed food risk")
    delta = max(
        abs(getattr(earlier.snapshot.position, axis)
            - getattr(current.snapshot.position, axis))
        for axis in ("x", "y", "z")
    )
    if delta > 0.05:
        raise Bug0FirstEatShadowRejected("native body position changed before food")
    # Reuse original S46/EatCursor priority and hunger gate; do not
    # fabricate a new learned policy or automatically use rotten flesh.
    selection = EatCursor(owner.session_id).choose(current)
    if (
        selection.status is not EatStatus.CANDIDATE
        or selection.item_name is None
        or selection.item_slot is None
        or not any(
            item.name == selection.item_name
            and item.slot == selection.item_slot
            and item.count > 0
            for item in current.snapshot.inventory
        )
    ):
        raise Bug0FirstEatShadowRejected("no eligible food in current native source")
    previous_count = sum(
        item.count
        for item in earlier.snapshot.inventory
        if item.name == selection.item_name and item.slot == selection.item_slot
    )
    current_count = sum(
        item.count
        for item in current.snapshot.inventory
        if item.name == selection.item_name and item.slot == selection.item_slot
    )
    if previous_count <= 0 or current_count != previous_count:
        raise Bug0FirstEatShadowRejected(
            "food inventory changed between original pre-EAT probes"
        )
    return Bug0FirstEatShadow(
        session_id=owner.session_id,
        intent_id=owner.intent.current_intent.intent_id,
        earlier_probe_seq=earlier.seq,
        current_probe_seq=current.seq,
        current_probe_request_id=current.request_id,
        food_before=selection.food_before,
        candidate_item=selection.item_name,
        candidate_slot=selection.item_slot,
        earlier_risk=earlier_risk.value,
        current_risk=current_risk.value,
        position_delta_max_m=delta,
    )



async def handoff_authorized_first_eat(
    owner: NormalSessionActionExecutor,
    session: MineflayerProcessSession,
    earlier: MineflayerObservation,
    current: MineflayerObservation,
    observed: Bug0FirstEatShadow,
    propose: NormalEatingAuthorization,
    issue: NormalEatingAuthorization,
) -> EatingActionReceipt:
    """Use the existing S49 issuer and S51 verifier; NEVER manufacture grants.

    This is deliberately NOT called by S51's first-EAT shadow runner.
    Approval is externally owned, and these typed grant objects are NOT
    independent principal attestation. The S owner must verify their actual
    source before admitting any physical DEV World EAT through this function.
    """
    if (
        not isinstance(observed, Bug0FirstEatShadow)
        or not isinstance(propose, NormalEatingAuthorization)
        or not isinstance(issue, NormalEatingAuthorization)
    ):
        raise Bug0FirstEatShadowRejected(
            "external EAT authorizations and source-bound shadow required"
        )
    # Freshly recompute from the same original observation pair to prevent
    # callers reusing an old candidate after hunger/inventory/threat changes.
    actual = inspect_bug0_first_eat_shadow(owner, earlier, current)
    if observed != actual:
        raise Bug0FirstEatShadowRejected("EAT approval references stale shadow")
    if (
        proposed_action_id := propose.action_id
    ) != issue.action_id or not proposed_action_id:
        raise Bug0FirstEatShadowRejected("distinct grant action identities")
    for grant in (propose, issue):
        if (
            grant.session_id != observed.session_id
            or grant.intent_id != observed.intent_id
            or grant.probe_seq != observed.current_probe_seq
            or grant.probe_request_id != observed.current_probe_request_id
            or grant.food_item != observed.candidate_item
            or grant.food_slot != observed.candidate_slot
        ):
            raise Bug0FirstEatShadowRejected(
                "EAT grant not scoped to original native candidate"
            )
    choice = EatCursor(owner.session_id).choose(current)
    if (
        choice.status is not EatStatus.CANDIDATE
        or choice.item_name != observed.candidate_item
        or choice.item_slot != observed.candidate_slot
        or choice.food_before != observed.food_before
    ):
        raise Bug0FirstEatShadowRejected("current EAT choice differs from shadow")
    return await owner.execute_eat(
        session, choice, current, propose, issue, previous_probe=earlier,
    )
