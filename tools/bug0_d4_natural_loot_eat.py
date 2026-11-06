"""D4: actual Paper zombie rotten-flesh pickup then S49/S51 EAT in one World.

Strictly operator-staged melee position + hunger, not Self MOVE or an
autonomous hunting policy. The original S49 ActionSupervisor is the ONLY
physical ATTACK/EAT issuer. Actual dropped Item pickup is passive World
physics; Paper UUID and native inventory count remain independent sources.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalEatingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from relay_self.provenance import Provenance
from tools.bug0_pickup_d1_world import _inventory, _original_marker


class NaturalD4Rejected(RuntimeError):
    """Real natural-loot source or authentic S49-EAT outcome not established."""


def _rotten(read: Any) -> int:
    return sum(
        item.count for item in read.snapshot.inventory
        if item.name == "rotten_flesh"
    )


async def run_natural_loot_eat(
    session: Any, server: Any, owner: NormalSessionActionExecutor,
    report: dict[str, Any], log_path: Path, *,
    baseline: Any,
    natural_count: int,
) -> bool:
    """Return whether genuine natural meat was EATen; never synthesize loot.

    No physical movement is delegated here. Operator staged the original
    NoAI low-health zombie within immediate natural item-pickup range. A
    positive natural drop can still scatter out of reach; that fails closed.
    """
    sid = owner.session_id
    if (
        getattr(getattr(session, "started", None), "session_id", None) != sid
        or owner.supervisor.open_actions
        or type(natural_count) is not int
        or not 0 <= natural_count <= 2
        or baseline.session_id != sid
        or _rotten(baseline) != 0
        or not isinstance(log_path, Path)
        or not log_path.is_file()
    ):
        raise NaturalD4Rejected("original session/baseline/natural-drop source invalid")
    report["d4_natural_count"] = natural_count
    report["d4_native_before"] = _inventory(baseline)
    report["d4_self_move_for_item"] = False
    report["d4_item_manual_stage"] = False
    report["d4_operator_hunger_induced_for_dev"] = True
    report["d4_pickup_passive"] = False
    report["d4_eat_terminal"] = "NOT_ISSUED"
    report["d4_self_eat_issued"] = False
    report["d4_food_policy_trace"] = []

    if natural_count == 0:
        # Zero is a true random World outcome. No invented food/extra kills.
        probe = await _correlated_observe(session, "d4-zero-loot-native")
        report["d4_native_after_zero"] = _inventory(probe)
        if (
            probe.session_id != sid or probe.seq <= baseline.seq
            or _rotten(probe) != 0
        ):
            raise NaturalD4Rejected("genuine zero-loot cannot increase inventory")
        report["d4_stage"] = "ZERO_REAL_LOOT_NO_PICKUP_NO_EAT"
        return False

    report["d4_stage"] = "WAIT_REAL_PAPER_NATURAL_PICKUP"
    report["d4_paper_item_spawn"] = await _original_marker(
        log_path, "RSELF_NATURAL_DROP_SPAWN world=", budget=7,
    )
    report["d4_paper_item_pickup"] = await _original_marker(
        log_path, "RSELF_NATURAL_DROP_PICKUP world=", budget=12,
    )
    report["d4_stage"] = "NATIVE_INVENTORY_MATCHES_TRUE_DROP"
    native_after = None
    failed = []
    for index in range(1, 13):
        probe = await _correlated_observe(session, f"d4-real-meat-{index:02d}")
        state = _inventory(probe)
        if (
            probe.session_id == sid and probe.seq > baseline.seq
            and probe.snapshot.health > 0
            and _rotten(probe) == natural_count
        ):
            native_after = probe
            report["d4_native_after_pickup"] = state
            report["d4_native_pickup_attempt"] = index
            break
        failed.append(state)
        await asyncio.sleep(0.3)
    report["d4_unqualified_pickup_probes"] = failed
    if native_after is None:
        raise NaturalD4Rejected(
            "Paper pickup did not produce exact authentic native inventory gain"
        )
    report["d4_pickup_passive"] = True

    # DEV-only operator hunger stimulus was applied before combat; do not
    # conflate that environmental intervention with a Self-discovered Goal.
    # Original S49 native food L0 still independently chooses or refuses EAT.
    food = S49BasicPriorityL0(sid, max_decisions=64)
    earlier = None
    current = None
    report["d4_stage"] = "NATIVE_S49_ROTTEN_FLESH_FOOD_CHOICE"
    for index in range(22):
        probe = await _correlated_observe(session, f"d4-food-choice-{index:02d}")
        decision = food.decide(probe)
        report["d4_food_policy_trace"].append({
            "seq": probe.seq, "selected": decision.selected,
            "reason": decision.reason, "risk": decision.native_risk,
            "food": decision.food, "item": decision.candidate_item,
            "nearby": [
                {"id": entity.entity_id, "name": entity.name}
                for entity in probe.snapshot.nearby_entities
            ],
        })
        if decision.selected == "EAT" and decision.candidate_item == "rotten_flesh":
            earlier = probe
            break
        if decision.reason not in ("NOT_HUNGRY",):
            raise NaturalD4Rejected(
                "native L0 refused EAT due to observed risk/food: " + decision.reason
            )
        await asyncio.sleep(0.6)
    if earlier is None:
        raise NaturalD4Rejected("DEV World did not generate native food hunger")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    await asyncio.sleep(0.15)
    current = await _correlated_observe(session, "d4-rotten-preissue-fresh")
    later = food.decide(current)
    if (
        later.selected != "EAT"
        or later.candidate_item != "rotten_flesh"
        or later.candidate_slot is None
        or _rotten(current) != natural_count
    ):
        raise NaturalD4Rejected("fresh native S49 L0 declined natural rotten flesh")
    if any(
        abs(getattr(earlier.snapshot.position, axis)
            - getattr(current.snapshot.position, axis)) > 0.05
        for axis in ("x", "y", "z")
    ):
        raise NaturalD4Rejected("body not stationary at S49 food grant boundary")

    # Only the already-running original S49 supervisor is allowed to issue
    # one EAT; S51 receives a delegated native command via execute_eat.
    action_id = f"d4-s49-native-eat-{sid}"
    fields = dict(
        intent_id=owner.intent.current_intent.intent_id,
        session_id=sid,
        action_id=action_id,
        probe_seq=current.seq,
        probe_request_id=current.request_id,
        food_item="rotten_flesh",
        food_slot=later.candidate_slot,
        granted=True,
    )
    propose = NormalEatingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="d4-operator-eat-propose",
        provenance=Provenance("d4-operator-one-world", "eat-propose"),
        **fields,
    )
    issue = NormalEatingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="d4-operator-eat-issue",
        provenance=Provenance("d4-operator-one-world", "eat-issue"),
        **fields,
    )
    report["d4_stage"] = "ORIGINAL_S49_S51_REAL_ROTTEN_FLESH_EAT"
    owner.require_eating_authorizations(
        later if False else food.food.cursor.choose(
            await _correlated_observe(session, "d4-shadow-NEVER_USE")
        ), current, propose, issue, previous_probe=earlier,
    )
    raise NaturalD4Rejected("placeholder protection: grant binding not yet wired")
