"""D6-D bounded genuine zombie death -> natural drop -> SAME original S49 MOVE.

Distinct from D5 first kill/passive pickup/EAT and D6-C staged item MOVE.
Both original S49 ATTACK nonmotion and MOVE C1 journals are preflighted
before World, and written in a persistent evidence directory outside World.
Two separate ledgers do NOT create cross-file atomic exactly-once delivery.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from adapters.mineflayer.d6_loot_approach import D6LootApproachRejected
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from tools.bug0_d4_oneworld import run as d4_real_world
from tools.bug0_d6_staged_move_world import move_from_real_item


async def source_qualified_natural_move(
    session, owner: NormalSessionActionExecutor,
    report: dict, original_paper_log: Path, *,
    motion_fence: OriginalS49PhysicalFence,
    d7f_live_eat_dev: bool = False,
) -> tuple | None:
    """No new Intent, no second supervisor, no operator MOVE or teleport."""
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or owner.session_id != session.started.session_id
        or owner.supervisor.open_actions
        or not owner._dispatched
        or report.get(
            "d6_multigen_active_natural_count",
            report.get("d4_natural_count", 0),
        ) <= 0
        or not isinstance(motion_fence, OriginalS49PhysicalFence)
    ):
        raise D6LootApproachRejected("original physical ATTACK closure required")
    if "RSELF_NATURAL_DROP_PICKUP world=" in original_paper_log.read_text(
        encoding="utf8"
    ):
        raise D6LootApproachRejected("natural item was picked up before original MOVE")
    report["d6_d_paper_pickup_absent_before_move"] = True
    old_supervisor = owner.supervisor
    old_ids = frozenset(owner._dispatched)
    old_actions = owner._count
    live_result = await move_from_real_item(
        session, report, original_paper_log,
        fence=motion_fence,
        owner=owner,
        item_origin="ACTUAL_PAPER_ZOMBIE_DEATH_EVENT",
        allow_experience_orbs=True,
        d7_return_live_owner_dev=d7f_live_eat_dev,
    )
    if (
        old_supervisor is not owner.supervisor
        or not old_ids.issubset(owner._dispatched)
        or owner._count != old_actions + report["d6_original_move_count"]
        or report["d6_original_move_count"] > 4
        or owner.supervisor.open_actions
        or not owner._post_move_settling_unqualified
    ):
        raise D6LootApproachRejected("original ATTACK->MOVE S49 owner history changed")
    report["d6_d_original_attack_action_ids_before_move"] = sorted(old_ids)
    report["d6_d_original_count_before_move"] = old_actions
    report["d6_d_same_attack_move_supervisor"] = True
    report["d6_d_world_natural_loot_moved"] = True
    report["d6_d_no_postmove_eat_grant"] = True
    if d7f_live_eat_dev:
        if (
            live_result is None
            or live_result[0] is not owner
            or len(report["d6_original_s49_move_actions"]) != 1
            or owner._count != owner._attack_count + 1
        ):
            raise D6LootApproachRejected("D7-F original natural live STOP source absent")
        report["d7f_same_original_attack_move_owner"] = True
        return live_result
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--nonmotion-fence", type=Path, required=True)
    parser.add_argument("--motion-fence", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(
        d4_real_world(
            args.report, args.server_log,
            nonmotion_fence_path=args.nonmotion_fence,
            post_death_loot_move_dev=source_qualified_natural_move,
            motion_fence_path=args.motion_fence,
        ),
    ))


if __name__ == "__main__":
    main()
