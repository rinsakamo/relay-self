"""D7-F: true Paper zombie rotten flesh -> original S49 MOVE -> STOP -> S51 EAT.

The source item is naturally dropped by a genuine Paper Self-killed zombie,
not an operator-staged item. All physical ATTACK/MOVE/EAT remain on the same
original S49 supervisor and use pre-ISSUE fsynced original ledgers.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

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
from tools.bug0_pickup_d1_world import _inventory


class D7FNaturalEatRejected(RuntimeError):
    """The same genuine Paper natural source never qualified original EAT."""


async def after_real_natural_pickup_eat(
    session, server, owner, report: dict, log_path: Path, *,
    original_move: tuple,
    native_pickup,
    nonmotion_fence: OriginalS49NonMotionFence,
    s50_sidecar: Path,
) -> bool:
    """One positive first generation, one actual rotten item, no forged RNG.

    Zero genuine natural meat is a separate legitimate no-EAT World outcome.
    Two natural meat items are not part of this narrow initial qualification.
    """
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or not isinstance(original_move, tuple) or len(original_move) != 2
        or original_move[0] is not owner
        or not isinstance(nonmotion_fence, OriginalS49NonMotionFence)
        or nonmotion_fence.unresolved
        or len(nonmotion_fence.actions) != owner._attack_count
        or owner._attack_count < 1
        or not 1 <= owner._count - owner._attack_count <= 4
        or len(owner._dispatched) != owner._count
        or owner.supervisor.open_actions
        or not owner._post_move_settling_unqualified
        or not report.get("self_attack_principal_attested")
        or report.get("real_rotten_flesh_count") != 1
        or report.get("d4_natural_count") != 1
        or not report.get("d4_precombat_hunger_qualified")
        or not report.get("d7f_operator_hunger_effect_dev")
        or report.get("d6_item_origin") != "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
        or not report.get("d6_d_same_attack_move_supervisor")
        or not 1 <= len(report.get("d6_original_s49_move_actions", ())) <= 4
        or original_move[1].terminal.action_id != (
            report["d6_original_s49_move_actions"][-1]["action_id"]
        )
        or not report.get("d4_paper_item_spawn")
        or not report.get("d4_paper_item_pickup")
        or "killer_is_relay_self=true" not in report.get("paper_loot_death", "")
        or native_pickup.session_id != owner.session_id
        or sum(
            item.count for item in native_pickup.snapshot.inventory
            if item.name == "rotten_flesh"
        ) != 1
        or not isinstance(s50_sidecar, Path)
        or not s50_sidecar.is_file()
        or s50_sidecar.is_symlink()
    ):
        raise D7FNaturalEatRejected("genuine original S49 ATTACK/MOVE natural pickup absent")
    sid = owner.session_id
    report["d7f_stage"] = "FRESH_NATIVE_NATURAL_ITEM_FOOD_CHOICE"
    report["d7f_original_eat_issued"] = False
    report["d7f_eat_terminal"] = "NOT_ISSUED"
    report["d7f_natural_source_only"] = True
    report["d7f_operator_staged_item"] = False
    food = S49BasicPriorityL0(sid, max_decisions=64)
    earlier = None
    for index in range(32):
        probe = await _correlated_observe(
            session, f"d7f-natural-food-before-{index:02d}",
        )
        decision = food.decide(probe)
        report.setdefault("d7f_food_decisions", []).append({
            "seq": probe.seq,
            "selected": decision.selected,
            "reason": decision.reason,
            "food": decision.food,
            "item": decision.candidate_item,
            "risk": decision.native_risk,
        })
        if decision.selected == "EAT" and decision.candidate_item == "rotten_flesh":
            earlier = probe
            break
        if decision.selected == "DEFER" and decision.reason not in (
            "UNQUALIFIED_NEARBY_ENTITY",
            "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
        ):
            raise D7FNaturalEatRejected("genuine native food policy refused EAT")
        await asyncio.sleep(0.25)
    if earlier is None:
        raise D7FNaturalEatRejected("no fresh safe native S49 L0 food choice")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    await asyncio.sleep(0.15)
    current = await _correlated_observe(session, "d7f-natural-food-preissue-fresh")
    decision = food.decide(current)
    if (
        decision.selected != "EAT"
        or decision.candidate_item != "rotten_flesh"
        or decision.candidate_slot is None
        or not 0 < current.snapshot.food < 14
    ):
        raise D7FNaturalEatRejected("fresh original S49 L0 food choice changed")

    stop = owner.admit_d7_live_staged_stop_dev(
        session, original_move[1],
        paper_log=log_path, s50_sidecar=s50_sidecar,
        paper_staged=report["d4_paper_item_spawn"],
        paper_pickup=report["d4_paper_item_pickup"],
        paper_natural_death=report["paper_loot_death"],
        natural_source_dev=True,
        native_before=earlier, native_after=current,
    )
    if (
        stop.classification != "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
        or stop.paper_pickup_tick <= 0
    ):
        raise D7FNaturalEatRejected("natural STOP source was not original Paper")
    report["d7f_live_natural_stop"] = asdict(stop)
    report["d7f_stop_original_owner_admitted_dev"] = True
    report["d7f_server_effective_s15_clear_tick_attested"] = False

    action_id = f"d7f-s49-real-natural-eat-{sid}"
    choice = EatCursor(sid).choose(current)
    if (
        choice.status is not EatStatus.CANDIDATE
        or choice.item_name != decision.candidate_item
        or choice.item_slot != decision.candidate_slot
        or choice.probe_seq != current.seq
    ):
        raise D7FNaturalEatRejected("S49 L0 and native EatCursor disagreed")
    fields = dict(
        intent_id=owner.intent.current_intent.intent_id,
        session_id=sid,
        action_id=action_id,
        probe_seq=current.seq,
        probe_request_id=current.request_id,
        food_item="rotten_flesh",
        food_slot=choice.item_slot,
        granted=True,
    )
    propose = NormalEatingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="d7f-natural-world-propose",
        provenance=Provenance("d7f-natural-dev-operator", "eat-propose"),
        **fields,
    )
    issue = NormalEatingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="d7f-natural-world-issue",
        provenance=Provenance("d7f-natural-dev-operator", "eat-issue"),
        **fields,
    )
    owner.require_eating_authorizations(
        choice, current, propose, issue, previous_probe=earlier,
    )
    report["d7f_stage"] = "ISSUE_S51_TRUE_NATURAL_ROTTEN_EAT"
    report["d7f_eat_action_id"] = action_id
    try:
        result = await owner.execute_eat(
            session, choice, current, propose, issue,
            previous_probe=earlier, physical_fence=nonmotion_fence,
        )
    finally:
        report["d7f_original_eat_issued"] = action_id in owner._dispatched
        report["d7f_eat_terminal"] = (
            owner.supervisor.get(action_id).state.value
            if action_id in owner._dispatched else "NOT_ISSUED"
        )
    outcome = result.outcome
    if (
        result.terminal.state is not ActionState.OUTCOME
        or result.terminal is not owner.supervisor.get(action_id)
        or outcome.consumed_item != "rotten_flesh"
        or outcome.count_before != 1 or outcome.count_after != 0
        or outcome.food_after <= outcome.food_before
        or owner.supervisor.open_actions
        or nonmotion_fence.unresolved
        or len(nonmotion_fence.actions) != owner._attack_count + 1
        or len(owner._dispatched) != owner._count
        or owner._count != (
            owner._attack_count + len(report["d6_original_s49_move_actions"]) + 1
        )
        or owner._d7_dev_eat_credit != 0
        or not owner._post_move_settling_unqualified
    ):
        raise D7FNaturalEatRejected("same S49/S51 natural EAT food or ledger unqualified")
    food.acknowledge_verified_eat(result)
    report["d7f_eat_outcome"] = asdict(outcome)
    report["d4_eat_action_id"] = action_id
    report["d4_self_eat_issued"] = True
    report["d4_eat_terminal"] = "outcome"
    report["d4_eat_outcome"] = asdict(outcome)
    post = await _correlated_observe(session, "d7f-natural-food-after-eat")
    report["d7f_native_after_eat"] = _inventory(post)
    if (
        post.seq <= outcome.after_probe_seq
        or post.snapshot.food < outcome.food_after
        or any(item.name == "rotten_flesh" for item in post.snapshot.inventory)
    ):
        raise D7FNaturalEatRejected("new native source contradicts true S51 EAT")
    report["d7f_nonmotion_sha256"] = nonmotion_fence.sha256
    report["d7f_nonmotion_unresolved"] = nonmotion_fence.unresolved
    report["d7f_original_total_actions"] = owner._count
    report["d7f_original_attack_count"] = owner._attack_count
    report["d7f_stage"] = "S49_NATURAL_ATTACK_MOVE_STOP_S51_EAT_ONE_CYCLE_DEV"
    return True
