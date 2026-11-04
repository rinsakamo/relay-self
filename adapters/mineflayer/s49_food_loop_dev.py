"""Bug-0 DEV food-probe epochs from the ORIGINAL S49 World runner.

This module owns neither Mineflayer nor ActionSupervisor. The S49 caller
supplies its already-live native session and sole NormalSessionActionExecutor.
Only explicit operator-staged bread and local DEV grants are supported.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from adapters.mineflayer.bug0_first_eat_shadow import (
    handoff_authorized_first_eat,
    inspect_bug0_first_eat_shadow,
)
from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalEatingAuthorization,
    NormalFoodL0,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from relay_self.action import ActionState
from relay_self.provenance import Provenance


class S49FoodLoopRejected(RuntimeError):
    """A bounded native observation or original S49 EAT outcome was absent."""


def dev_source(ref: str) -> Provenance:
    return Provenance("s49-local-operator-dev", ref)


async def run_s49_food_loop(
    session: object, server: object, owner: NormalSessionActionExecutor,
    report: dict[str, Any],
) -> None:
    """Select EAT from native hunger, issue through S49, then select WAIT.

    The original S49 runner owns Java/Node launch/cleanup. This method never
    creates a second session, supervisor, Action ID, or independent S51 owner.
    """
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or getattr(getattr(session, "started", None), "session_id", None)
        != owner.session_id
        or getattr(server, "stdin", None) is None
        or owner._count != 0 or owner.supervisor.open_actions
    ):
        raise S49FoodLoopRejected("original fresh S49 owner/source required")
    sid = owner.session_id
    food = NormalFoodL0(sid, max_decisions=20)
    report["stage"] = "BUG0_S49_NATIVE_FOOD_L0"
    report["food_l0_trace"] = []
    report["food_commands_issued"] = 0
    report["learning_in_world"] = False
    report["m_energy_credited"] = False
    report["independent_eat_grant_attested"] = False
    report["automatic_goal_selection"] = False
    report["world_food_supply"] = "OPERATOR_GIVEN_BREAD"
    report["real_model_calls"] = 0
    report["actual_native_actions"] = []

    def remember(decision: object) -> None:
        report["food_l0_trace"].append({
            "probe_seq": decision.probe_seq,
            "food": decision.food,
            "selected": decision.selection,
            "reason": decision.reason,
            "risk": decision.risk.value,
            "item": decision.choice.item_name,
            "s49_action_count": owner._count,
        })

    _command(server, "gamerule doMobSpawning false")
    _command(server, "gamemode survival RelaySelf")
    _command(server, "give RelaySelf minecraft:bread 3")
    _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
    await server.stdin.drain()

    before = None
    # These are true, successive native probes, not a synthetic episode
    # or a fake normal-session entity event.
    for idx in range(16):
        await asyncio.sleep(2)
        reading = await _correlated_observe(
            session, f"s49-bug0-food-l0-{idx:02d}",
        )
        decision = food.decide(reading)
        remember(decision)
        if decision.selection == "EAT":
            before = reading
            break
        if decision.reason not in ("NOT_HUNGRY",):
            raise S49FoodLoopRejected(
                "native L0 refused food: " + decision.reason
            )
    if before is None:
        raise S49FoodLoopRejected("native hunger did not cause L0 EAT decision")
    # Remove operator-only hunger effect before a normal physical EAT.
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    fresh = await _correlated_observe(session, "s49-bug0-food-l0-preissue")
    selection = food.decide(fresh)
    remember(selection)
    if selection.selection != "EAT" or selection.choice.item_name != "bread":
        raise S49FoodLoopRejected("current source no longer selects bread EAT")
    shadow = inspect_bug0_first_eat_shadow(owner, before, fresh)
    if shadow.candidate_item != "bread" or (
        shadow.candidate_slot != selection.choice.item_slot
    ):
        raise S49FoodLoopRejected("original S49 DEV food candidate changed")
    report["bug0_first_eat_shadow"] = asdict(shadow)
    report["dev_authorization_scope"] = (
        "ONE_S49_WORLD_ONE_LOCAL_OPERATOR_APPROVED_EAT"
    )
    report["stage"] = "BUG0_S49_ORIGINAL_SUPERVISOR_TO_S51_EAT"
    action_id = f"bug0-s49-food-loop-{sid}"
    report["issued_action_id"] = action_id
    values = {
        "intent_id": owner.intent.current_intent.intent_id,
        "session_id": sid,
        "action_id": action_id,
        "probe_seq": fresh.seq,
        "probe_request_id": fresh.request_id,
        "food_item": "bread",
        "food_slot": shadow.candidate_slot,
        "granted": True,
    }
    propose = NormalEatingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="s49-bug0-local-dev-propose",
        provenance=dev_source("bug0-s49-propose"),
        **values,
    )
    issue = NormalEatingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="s49-bug0-local-dev-issue",
        provenance=dev_source("bug0-s49-issue"),
        **values,
    )
    # If either native child command starts and fails, the original Action
    # remains UNKNOWN; do NOT replay food and inspect exact native logs.
    report["food_commands_issued"] = "INSPECT_NATIVE_IF_INTERRUPTED"
    try:
        receipt = await handoff_authorized_first_eat(
            owner, session, before, fresh, shadow, propose, issue,
        )
    finally:
        try:
            report["action_terminal"] = owner.supervisor.get(action_id).state.value
        except (KeyError, ValueError):
            report["action_terminal"] = "NOT_ISSUED"
    if (
        receipt.terminal is not owner.supervisor.get(action_id)
        or receipt.terminal.state is not ActionState.OUTCOME
        or owner._count != 1
        or owner.supervisor.open_actions
    ):
        raise S49FoodLoopRejected("original S49 owner lacks terminal S51 EAT")
    food.acknowledge_verified_eat(receipt)
    report["native_eat_outcome"] = asdict(receipt.outcome)
    report["actual_native_actions"] = [{
        "action_id": action_id, "kind": "EAT",
        "terminal": receipt.terminal.state.value,
        "s49_owner": True, "same_supervisor": True,
    }]
    report["food_commands_issued"] = 2
    report["stage"] = "BUG0_S49_POST_EAT_NATIVE_REOBSERVATION"
    post = await _correlated_observe(session, "s49-bug0-food-l0-after")
    decision = food.decide(post)
    remember(decision)
    report["next_food_decision"] = {
        "selected": decision.selection,
        "reason": decision.reason,
        "probe_seq": decision.probe_seq,
        "food": decision.food,
        "native_provenance": post.provenance.reference,
    }
    if (
        post.seq <= receipt.outcome.after_probe_seq
        or decision.selection != "WAIT"
        or decision.reason != "NOT_HUNGRY"
        or decision.food < 14
        or receipt.outcome.food_after <= receipt.outcome.food_before
        or receipt.outcome.count_before - receipt.outcome.count_after != 1
        or owner._count != 1 or owner.supervisor.open_actions
    ):
        raise S49FoodLoopRejected(
            "post-EAT original S49 L0 did not enter observed NOT_HUNGRY WAIT"
        )
    report["before"] = {
        "food": receipt.outcome.food_before,
        "bread_count": receipt.outcome.count_before,
        "probe_seq": fresh.seq,
    }
    report["after"] = {
        "food": receipt.outcome.food_after,
        "bread_count": receipt.outcome.count_after,
        "probe_seq": receipt.outcome.after_probe_seq,
    }
    report["physical_eat_executed"] = True
