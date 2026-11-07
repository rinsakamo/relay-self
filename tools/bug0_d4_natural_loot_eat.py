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
from relay_self.eat_hunger import EatCursor, EatStatus
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
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
    physical_fence: OriginalS49NonMotionFence | None = None,
    natural_loot_move_dev=None,
    d7f_natural_eat_dev=None,
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
    if natural_loot_move_dev is not None:
        if (
            not callable(natural_loot_move_dev)
            or physical_fence is None
            or owner.supervisor.open_actions
        ):
            raise NaturalD4Rejected("D6 physical natural loot source/owner absent")
        # The callback consumes only fresh native item geometry. It may
        # execute the SAME existing S49's bounded MOVE via C1 journal.
        # Unlike D4, pickup must occur AFTER at least one original MOVE.
        report["d4_stage"] = "D6_NATURAL_ITEM_NATIVE_S49_MOVE"
        original_move = await natural_loot_move_dev(
            session, owner, report, log_path,
        )
        if d7f_natural_eat_dev is not None and (
            not callable(d7f_natural_eat_dev)
            or not isinstance(original_move, tuple)
            or len(original_move) != 2
            or original_move[0] is not owner
        ):
            raise NaturalD4Rejected("D7-F live original natural MOVE receipt absent")
        if (
            not report.get("d6_original_s49_move_actions")
            or owner.supervisor.open_actions
            or not owner._post_move_settling_unqualified
        ):
            raise NaturalD4Rejected("no original S49 native source MOVE before pickup")
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
    report["d4_pickup_passive"] = natural_loot_move_dev is None
    if natural_loot_move_dev is not None:
        report["d4_self_move_for_item"] = True
        # A real pickup after MOVE does not establish tick-aligned physical
        # STOP or authorize EAT. Leave S49 post-move fence untouched.
        if d7f_natural_eat_dev is not None:
            # D7-F new DEV opt-in only: no EAT until original live owner
            # qualifies source-bound Paper/S50 physical quiescence.
            if natural_count not in (1, 2):
                report["d7f_natural_eat_classification"] = (
                    "NOT_EXERCISED_NATURAL_COUNT_ZERO_OR_INVALID"
                )
                return False
            return await d7f_natural_eat_dev(
                session, server, owner, report, log_path,
                original_move=original_move,
                native_pickup=native_after,
            )
        report["d4_stage"] = "D6_NATURAL_MEAT_SELF_MOVED_PICKED_EAT_BLOCKED"
        report["d4_eat_terminal"] = "NOT_ISSUED_AFTER_MOVE"
        report["d4_self_eat_issued"] = False
        return False

    # DEV-only operator hunger stimulus was applied before combat; do not
    # conflate that environmental intervention with a Self-discovered Goal.
    # Original S49 native food L0 still independently chooses or refuses EAT.
    food = S49BasicPriorityL0(sid, max_decisions=64)
    earlier = None
    current = None
    report["d4_stage"] = "NATIVE_S49_ROTTEN_FLESH_FOOD_CHOICE"
    # A killed zombie can remain temporarily in the native entity cache.
    # NEVER treat Paper death/loot as a SelfWorld safety certificate. Simply
    # reobserve authentic native source; only S49's unchanged food L0 can
    # admit EAT when it genuinely sees NO nearby entity and is hungry.
    for index in range(36):
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
        if decision.reason not in (
            "NOT_HUNGRY",
            "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
            "DISTANT_ZOMBIE_MONITOR",
            "UNQUALIFIED_NEARBY_ENTITY",
            "COVERAGE_INCOMPLETE",
        ):
            raise NaturalD4Rejected(
                "native L0 refuses unqualified food: " + decision.reason
            )
        # WAIT/DEFER only. No attack, stop override, EAT grant, or
        # risk-suppression between genuine native probes.
        await asyncio.sleep(0.5)
    if earlier is None:
        raise NaturalD4Rejected("DEV World did not generate native food hunger")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    await asyncio.sleep(0.15)
    current = await _correlated_observe(session, "d4-rotten-preissue-fresh")
    later = food.decide(current)
    report["d4_preissue_choice"] = {
        "selected": later.selected,
        "item": later.candidate_item,
        "seq": later.probe_seq,
        "reason": later.reason,
        "risk": later.native_risk,
    }
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
    native_choice = EatCursor(sid).choose(current)
    if (
        native_choice.status is not EatStatus.CANDIDATE
        or native_choice.item_name != later.candidate_item
        or native_choice.item_slot != later.candidate_slot
        or native_choice.probe_seq != later.probe_seq
    ):
        raise NaturalD4Rejected("current S49/EatCursor native food source disagrees")
    owner.require_eating_authorizations(
        native_choice, current, propose, issue, previous_probe=earlier,
    )
    report["d4_eat_action_id"] = action_id
    report["d4_self_eat_issued"] = True
    try:
        receipt = await owner.execute_eat(
            session, native_choice, current,
            propose, issue, previous_probe=earlier,
            physical_fence=physical_fence,
        )
    finally:
        report["d4_eat_terminal"] = (
            owner.supervisor.get(action_id).state.value
            if action_id in owner._dispatched else "NOT_ISSUED"
        )
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or receipt.terminal is not owner.supervisor.get(action_id)
        or receipt.outcome.consumed_item != "rotten_flesh"
        or receipt.outcome.count_before != natural_count
        or receipt.outcome.count_after != natural_count - 1
        or receipt.outcome.food_after <= receipt.outcome.food_before
        or owner.supervisor.open_actions
    ):
        raise NaturalD4Rejected("native rotten flesh EAT outcome unqualified")
    food.acknowledge_verified_eat(receipt)
    report["d4_eat_outcome"] = asdict(receipt.outcome)
    post = await _correlated_observe(session, "d4-native-post-eat-epoch")
    next_decision = food.decide(post)
    report["d4_post_eat"] = _inventory(post)
    report["d4_next_food_decision"] = {
        "selected": next_decision.selected,
        "reason": next_decision.reason,
        "food": next_decision.food,
        "seq": next_decision.probe_seq,
    }
    if (
        post.seq <= receipt.outcome.after_probe_seq
        or _rotten(post) != natural_count - 1
        or not (
            next_decision.selected == "WAIT"
            and next_decision.reason in (
                "NOT_HUNGRY", "ONE_EAT_BUDGET_USED", "NO_INVENTORY_FOOD",
            )
        )
        or owner.supervisor.open_actions
    ):
        raise NaturalD4Rejected("post-EAT original source epoch not safely closed")
    report["d4_stage"] = "NATURAL_MEAT_PICKED_AND_EATEN_ONE_EPOCH"
    return True
