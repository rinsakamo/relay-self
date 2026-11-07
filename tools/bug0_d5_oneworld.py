"""D5: continue the D4 real World into a second genuine S49 Intent ATTACK.

The new zombie is observed only through fresh native source; Paper's
respawn clock is operator-only audit evidence. Second attack is one bounded
physical effect, NOT a second completed kill/loot/eat experience.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d4_oneworld import S49D3Rejected, _target, run


async def second_intent_after_real_respawn(
    session, server, owner: NormalSessionActionExecutor,
    report: dict, log_path: Path, *,
    physical_fence: OriginalS49NonMotionFence | None = None,
) -> None:
    """One original supervisor, fresh next-generation native target, one ATTACK."""
    sid = owner.session_id
    previous_id = report["native_initial"]["zombie_entity_id"]
    next_id = report["native_respawn"]["zombie_entity_id"]
    saved_supervisor = owner.supervisor
    saved_action_ids = frozenset(owner._dispatched)
    first_count = owner._count
    old = owner.intent.current_intent
    if (
        old is None or type(report.get("d4_natural_food_pickup_eat_proven")) is not bool
        or report.get("d4_final_action_count") != first_count
        or previous_id == next_id
        or owner.supervisor.open_actions
        or len(saved_action_ids) != first_count
        or any(owner.supervisor.get(a).state is not ActionState.OUTCOME
               for a in saved_action_ids)
    ):
        raise S49D3Rejected("D5 cannot close unqualified first Intent")
    report["stage"] = "D5_FRESH_NATIVE_SECOND_ZOMBIE_BEFORE_REARM"
    next_native = await _correlated_observe(session, "d5-epoch2-rearm-native")
    coverage = next_native.snapshot.nearby_entities_coverage
    zombie_ids = [
        entity.entity_id for entity in next_native.snapshot.nearby_entities
        if entity.name == "zombie"
    ]
    if (
        next_native.session_id != sid or next_native.kind != "probe"
        or coverage.truncated
        or coverage.candidate_count != len(next_native.snapshot.nearby_entities)
        or zombie_ids != [next_id]
        or next_native.seq <= report["native_respawn"]["seq"]
        or next_native.snapshot.health <= 0
    ):
        raise S49D3Rejected("D5 second zombie not source-qualified")
    report["d5_new_zombie_native"] = {
        "session_id": sid,
        "seq": next_native.seq,
        "request_id": next_native.request_id,
        "source": next_native.provenance.reference,
        "zombie_entity_id": next_id,
        "candidate_count": coverage.candidate_count,
        "truncated": coverage.truncated,
    }
    # Lifecycle is performed by the existing IntentCommitment owner, not
    # the operator granting a second physical Action by elapsed time.
    owner.intent.complete(
        old.intent_id, reason="first real combat and conditional loot/EAT outcomes closed",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("bug0-d5-original-owner", "completed-first"),
    )
    second = owner.intent.commit(
        "bug0-d5-second-zombie-encounter",
        objective="one bounded new-generation physical ATTACK",
        at_ns=owner.intent.last_at_ns + 1,
        provenance=Provenance("bug0-d5-original-owner", "committed-second"),
    )
    rearm = owner.advance_intent_epoch(
        next_native, previous_zombie_entity_id=previous_id,
    )
    report["d5_rearm"] = {
        "session_id": rearm.session_id,
        "completed_intent_id": rearm.completed_intent_id,
        "next_intent_id": rearm.next_intent_id,
        "completed_action_count": rearm.completed_action_count,
        "next_epoch": rearm.next_epoch,
        "previous_zombie_entity_id": rearm.previous_zombie_entity_id,
        "next_zombie_entity_id": rearm.next_zombie_entity_id,
        "next_source": rearm.next_native_source.reference,
        "physically_issued": rearm.physically_issued,
    }
    if (
        owner.supervisor is not saved_supervisor
        or owner._dispatched != saved_action_ids
        or second.intent_id != rearm.next_intent_id
        or rearm.completed_action_count != first_count
        or rearm.physically_issued
    ):
        raise S49D3Rejected("D5 rearm altered original Action history")
    # Operator may move ONLY the real World-owned next zombie into melee
    # range, with no target health reduction: this is not a second kill.
    # This DEV fixture is not an autonomous Self MOVE or normal combat.
    report["stage"] = "D5_OPERATOR_SECOND_ZOMBIE_MELEE_STAGING"
    commands = (
        "execute at RelaySelf run tp @e[type=minecraft:zombie,limit=1] ~0.65 ~ ~",
        "data merge entity @e[type=minecraft:zombie,limit=1] "
        "{NoAI:1b,Silent:1b}",
    )
    for cmd in commands:
        _command(server, cmd)
    report["d5_operator_world_staging"] = list(commands)
    await server.stdin.drain()
    await asyncio.sleep(0.8)

    report["stage"] = "D5_SAME_OWNER_NEW_ACTION_PROPOSE_ISSUE"
    previous = await _correlated_observe(session, "d5-second-attack-pre")
    await asyncio.sleep(0.25)
    current = await _correlated_observe(session, "d5-second-attack-fresh")
    _target(previous, next_id)
    _target(current, next_id)
    chosen = S49BasicPriorityL0(sid, max_decisions=3).decide(current)
    if (
        chosen.selected != "DEFER"
        or chosen.preferred != "MOVE_AWAY"
        or chosen.fallback != "ATTACK"
    ):
        raise S49D3Rejected("original L0 did not authorize second encounter")
    action_id = f"d5-s49-epoch2-attack-1-{sid}"
    fields = dict(
        intent_id=second.intent_id, session_id=sid, action_id=action_id,
        probe_seq=current.seq, probe_request_id=current.request_id,
        target_entity_id=next_id, granted=True,
    )
    propose = NormalAttackingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="operator-d5-epoch2-propose",
        provenance=Provenance("bug0-d5-physical-grant", "epoch2-propose"),
        **fields,
    )
    issue = NormalAttackingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="operator-d5-epoch2-issue",
        provenance=Provenance("bug0-d5-physical-grant", "epoch2-issue"),
        **fields,
    )
    owner.require_attack_authorizations(
        previous, current, next_id, propose, issue,
    )
    report["stage"] = "D5_SAME_ORIGINAL_S49_PHYSICAL_ATTACK"
    try:
        receipt = await owner.execute_attack(
            session, previous, current, next_id, propose, issue,
            physical_fence=physical_fence,
        )
    finally:
        report["d5_owner_total_action_count"] = owner._count
        report["d5_supervisor_open_count"] = len(owner.supervisor.open_actions)
        report["d5_retained_old_actions"] = all(
            owner.supervisor.get(a).state is ActionState.OUTCOME
            for a in saved_action_ids
        )
        report["d5_same_supervisor_identity"] = owner.supervisor is saved_supervisor
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or receipt.effect.result != "applied"
        or receipt.target_entity_id != next_id
        or receipt.after_probe.seq <= receipt.effect.seq
        or owner._count != first_count + 1
        or owner.supervisor.open_actions
        or owner._dispatched != saved_action_ids | {action_id}
    ):
        raise S49D3Rejected("second Intent original S49 terminal unqualified")
    report["d5_second_action"] = {
        "action_id": action_id,
        "intent_id": second.intent_id,
        "session_id": sid,
        "target_entity_id": next_id,
        "previous_seq": previous.seq,
        "admitted_seq": current.seq,
        "effect_seq": receipt.effect.seq,
        "after_seq": receipt.after_probe.seq,
        "ack": receipt.effect.result,
        "terminal": receipt.terminal.state.value,
    }
    report["d5_second_experience_completed"] = False
    report["d5_second_kill_attested"] = False
    report["d5_self_move_to_loot"] = False
    report["stage"] = "D5_SECOND_INTENT_ACTION_CLOSED_NO_SECOND_CYCLE_CLAIM"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--server-log", required=True, type=Path)
    parser.add_argument("--nonmotion-fence", type=Path)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(
        run(args.report, args.server_log,
            post_respawn_dev=second_intent_after_real_respawn,
            nonmotion_fence_path=args.nonmotion_fence),
    ))


if __name__ == "__main__":
    main()
