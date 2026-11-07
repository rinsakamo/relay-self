"""D7-E DEV only: original same S49 MOVE → Paper pickup → STOP → S51 EAT.

Original S49 owns the one-use admission and physical Action. This module
drives only a disposable operator-staged item World (not natural zombie loot).
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


class D7ERealEatRejected(RuntimeError):
    """No fresh, original source-qualified DEV STOP→EAT outcome."""


async def after_real_staged_pickup_eat(
    session, report: dict, log_path: Path, server, original: tuple,
    *, s50_sidecar: Path, nonmotion_fence: OriginalS49NonMotionFence,
) -> None:
    if (
        not isinstance(original, tuple) or len(original) != 2
        or not isinstance(original[0], NormalSessionActionExecutor)
        or not isinstance(nonmotion_fence, OriginalS49NonMotionFence)
        or nonmotion_fence.unresolved
        or nonmotion_fence.actions
        or report.get("item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("d7_staged_postpickup_passive_wait_seconds") != 1.0
        or not report.get("paper_staged")
        or not report.get("paper_pickup")
        or not report.get("d6_original_s49_move_actions")
        or len(report["d6_original_s49_move_actions"]) != 1
    ):
        raise D7ERealEatRejected("D7-E requires original successful staged S49 MOVE/PICKUP")
    owner, move_receipt = original
    sid = session.started.session_id
    if (
        owner.session_id != sid or session.process_returncode is not None
        or owner.supervisor.open_actions
        or not owner._post_move_settling_unqualified
        or len(owner._dispatched) != 1
    ):
        raise D7ERealEatRejected("D7-E original owner already lost physical identity")
    report["d7e_stage"] = "FRESH_NATIVE_L0_HUNGER_AND_RISK"
    report["d7e_original_EAT_issued"] = False
    report["d7e_eat_terminal"] = "NOT_ISSUED"
    report["d7e_operator_item_origin"] = "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
    report["d7e_post_move_source"] = "SAME_NATIVE_S49_S50_AND_PAPER_OWNED_TICKS"

    food = S49BasicPriorityL0(sid, max_decisions=64)
    earlier = None
    # R1 real World lowered Food only 20->15 in its 48 probes.
    # Keep vanilla World hunger law and the original L0 threshold intact;
    # allow the same bounded DEV observation 62 probes / <=34 seconds.
    for i in range(62):
        p = await _correlated_observe(session, f"d7e-food-before-{i:02d}")
        decision = food.decide(p)
        report.setdefault("d7e_food_choices", []).append({
            "seq": p.seq, "selected": decision.selected,
            "reason": decision.reason, "food": decision.food,
            "item": decision.candidate_item, "risk": decision.native_risk,
        })
        if decision.selected == "EAT" and decision.candidate_item == "rotten_flesh":
            earlier = p
            break
        if decision.selected == "DEFER" and decision.reason not in (
            "UNQUALIFIED_NEARBY_ENTITY", "ZOMBIE_PRESENT_NO_DEFENSE_ADMISSION",
        ):
            raise D7ERealEatRejected("native L0 deferred unsafe food selection")
        await asyncio.sleep(0.55)
    if earlier is None:
        raise D7ERealEatRejected("real hunger/inventory did not produce S49 EAT choice")

    # World operator may end the DEV hunger stimulus, but never sets
    # Self's current food or edits inventory/physics to fake the meal.
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    await asyncio.sleep(0.15)
    current = await _correlated_observe(session, "d7e-postmove-food-fresh")
    decision = food.decide(current)
    if (
        decision.selected != "EAT"
        or decision.candidate_item != "rotten_flesh"
        or decision.candidate_slot is None
        or current.snapshot.food >= 20
        or not any(
            item.name == "rotten_flesh" and item.count == 1
            for item in current.snapshot.inventory
        )
    ):
        raise D7ERealEatRejected("fresh original native S49 food source declined EAT")

    # Same S49 owner must qualify the LIVE physical post-pickup stationary
    # body from actual Paper and S50 while both are still RUNNING.
    stop = owner.admit_d7_live_staged_stop_dev(
        session, move_receipt,
        paper_log=log_path, s50_sidecar=s50_sidecar,
        paper_staged=report["paper_staged"],
        paper_pickup=report["paper_pickup"],
        native_before=earlier, native_after=current,
    )
    report["d7e_live_stop"] = asdict(stop)
    report["d7e_stop_original_owner_admitted_dev"] = True
    report["d7e_physical_server_effective_clear_tick_proven"] = False

    action_id = f"d7e-s49-eat-after-move-{sid}"
    choice = EatCursor(sid).choose(current)
    if (
        choice.status is not EatStatus.CANDIDATE
        or choice.item_name != decision.candidate_item
        or choice.item_slot != decision.candidate_slot
        or choice.probe_seq != current.seq
    ):
        raise D7ERealEatRejected("S49 native food decision/EatCursor disagree")
    props = dict(
        intent_id=owner.intent.current_intent.intent_id,
        session_id=sid, action_id=action_id,
        probe_seq=current.seq, probe_request_id=current.request_id,
        food_item="rotten_flesh", food_slot=choice.item_slot, granted=True,
    )
    propose = NormalEatingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="d7e-operator-propose",
        provenance=Provenance("d7e-operator-staged-dev", "one-eat-propose"),
        **props,
    )
    issue = NormalEatingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="d7e-operator-issue",
        provenance=Provenance("d7e-operator-staged-dev", "one-eat-issue"),
        **props,
    )
    owner.require_eating_authorizations(
        choice, current, propose, issue, previous_probe=earlier,
    )
    report["d7e_stage"] = "ORIGINAL_S49_S51_POSTMOVE_REAL_EAT"
    report["d7e_eat_action_id"] = action_id
    # Any post-issue uncertainty remains original nonmotion PREPARED.
    try:
        receipt = await owner.execute_eat(
            session, choice, current, propose, issue,
            previous_probe=earlier, physical_fence=nonmotion_fence,
        )
    finally:
        report["d7e_original_EAT_issued"] = action_id in owner._dispatched
        report["d7e_eat_terminal"] = (
            owner.supervisor.get(action_id).state.value
            if action_id in owner._dispatched else "NOT_ISSUED"
        )
    outcome = receipt.outcome
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or receipt.terminal is not owner.supervisor.get(action_id)
        or outcome.consumed_item != "rotten_flesh"
        or outcome.count_before != 1 or outcome.count_after != 0
        or outcome.food_after <= outcome.food_before
        or owner.supervisor.open_actions
        or nonmotion_fence.unresolved
        or len(nonmotion_fence.actions) != 1
        or len(owner._dispatched) != 2
        or owner._d7_dev_eat_credit != 0
        or not owner._post_move_settling_unqualified
    ):
        raise D7ERealEatRejected("original S49/S51 post-MOVE equip/consume source not qualified")
    food.acknowledge_verified_eat(receipt)
    report["d7e_original_eat_outcome"] = asdict(outcome)
    after = await _correlated_observe(session, "d7e-after-s51-real-eat")
    report["d7e_native_after_eat"] = _inventory(after)
    if (
        after.seq <= outcome.after_probe_seq
        or after.snapshot.food < outcome.food_after
        or any(item.name == "rotten_flesh" for item in after.snapshot.inventory)
    ):
        raise D7ERealEatRejected("current post-eat native food/inventory disagrees")
    report["d7e_original_nonmotion_fence_sha256"] = nonmotion_fence.sha256
    report["d7e_original_nonmotion_unresolved"] = nonmotion_fence.unresolved
    report["d7e_total_original_s49_action_count"] = owner._count
    report["d7e_stage"] = "ONE_REAL_STAGED_MOVE_PICKUP_STOP_EAT_DEV_PASS"
