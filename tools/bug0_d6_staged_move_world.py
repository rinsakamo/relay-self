"""D6-C bounded ONE World: existing S49 MOVE toward actual staged item.

This is operator-staged ground food, explicitly NOT zombie-derived natural
loot. A genuine Mineflayer source item and W4 yaw must select each MOVE.
Only original S49 ActionSupervisor sends native S15; C1 pre-ISSUE MOVE is
fsynced outside the disposable World. No EAT after MOVE or L2/learning.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path

from adapters.mineflayer.d6_loot_approach import (
    D6LootApproachRejected,
    source_qualified_loot_approach,
)
from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalLootMoveAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from relay_self.action import ActionState
from relay_self.c1_physical_action_fence import (
    OriginalS49PhysicalFence,
    PhysicalReplay,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from tools.bug0_pickup_d1_world import qualify as d1_world_qualify


class D6StagedMoveRejected(RuntimeError):
    """No real source-qualified S49 item-approach outcome."""


def preflight_move_fence(path: Path) -> OriginalS49PhysicalFence:
    """Before Paper starts, never silently reset an earlier physical MOVE."""
    if (
        not isinstance(path, Path) or not path.parent.is_dir()
        or path.is_symlink() or path.parent.is_symlink()
        or path.with_name(path.name + ".lock").is_symlink()
    ):
        raise D6StagedMoveRejected("persistent original S49 MOVE path invalid")
    if path.exists():
        fence = OriginalS49PhysicalFence.restore(
            path, self_id="s49-original-self",
        )
        fence.require_clear()
        if fence.actions:
            raise PhysicalReplay("prior World MOVE history cannot be reseeded")
        return fence
    return OriginalS49PhysicalFence.create(path, self_id="s49-original-self")


def _meat(probe) -> int:
    return sum(
        item.count for item in probe.snapshot.inventory
        if item.name == "rotten_flesh"
    )


async def move_from_real_item(
    session, report: dict, log_path: Path, *,
    fence: OriginalS49PhysicalFence,
) -> None:
    sid = session.started.session_id
    intent = IntentCommitment()
    intent.commit(
        "collect-operator-staged-loot",
        objective="bounded native item approach with original S49 only",
        at_ns=1,
        provenance=Provenance("d6-dev-world", "first-intent"),
    )
    owner = NormalSessionActionExecutor(sid, intent)
    supervisor = owner.supervisor
    report["d6_original_s49_move_actions"] = []
    report["d6_item_origin"] = "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
    report["d6_native_orientation_optin"] = True
    report["d6_s14_generic_loot_route_admitted"] = False
    report["d6_original_s49_supervisor_kept"] = True
    report["d6_eat_after_move"] = False
    report["d6_learning_update"] = False
    # World-side staged item must settle enough to permit two fresh native
    # probes; its mere presence never identifies its actual food type.
    await asyncio.sleep(0.9)
    last_item_id = None
    for i in range(1, 5):
        before = await _correlated_observe(session, f"d6-item-{i}-before")
        await asyncio.sleep(0.3)
        current = await _correlated_observe(session, f"d6-item-{i}-current")
        if (
            before.session_id != sid or current.session_id != sid
            or before.snapshot.health <= 0 or current.snapshot.health <= 0
        ):
            raise D6StagedMoveRejected("native Self no longer viable")
        if _meat(current) > 0:
            if not report["d6_original_s49_move_actions"]:
                raise D6StagedMoveRejected("passive pickup before any original S49 MOVE")
            break
        items = [e for e in current.snapshot.nearby_entities if e.name == "item"]
        if len(items) != 1:
            # If an item vanished but inventory is still zero, do not infer pickup.
            raise D6StagedMoveRejected("native source cannot identify pending item")
        item_id = items[0].entity_id
        if last_item_id is not None and item_id != last_item_id:
            raise D6StagedMoveRejected("item entity changed across physical MOVE")
        last_item_id = item_id
        try:
            choice = source_qualified_loot_approach(
                before, current, item_entity_id=item_id,
            )
        except D6LootApproachRejected as exc:
            # If within pickup radius but not yet observed in inventory,
            # wait for genuine World physics rather than issue a blind MOVE.
            if (
                report["d6_original_s49_move_actions"]
                and items[0].distance < 1.2
            ):
                await asyncio.sleep(1.0)
                maybe = await _correlated_observe(
                    session, f"d6-item-{i}-pickup-recheck",
                )
                if _meat(maybe) > 0:
                    break
            raise D6StagedMoveRejected(
                "original D6 native item approach declined"
            ) from exc
        action_id = f"d6-s49-item-back-{i}-{sid}"
        fields = dict(
            intent_id=intent.current_intent.intent_id,
            session_id=sid, action_id=action_id,
            probe_seq=current.seq, probe_request_id=current.request_id,
            item_entity_id=item_id, granted=True,
        )
        propose = NormalLootMoveAuthorization(
            stage=NormalActionStage.PROPOSE,
            authority_id=f"operator-d6-item-propose-{i}",
            provenance=Provenance("d6-dev-scoped-physical-grant", f"propose-{i}"),
            **fields,
        )
        issue = NormalLootMoveAuthorization(
            stage=NormalActionStage.ISSUE,
            authority_id=f"operator-d6-item-issue-{i}",
            provenance=Provenance("d6-dev-scoped-physical-grant", f"issue-{i}"),
            **fields,
        )
        receipt = await owner.execute_d6_loot_move(
            session, before, current, choice, propose, issue,
            physical_fence=fence,
        )
        c = receipt.consequence
        if (
            receipt.terminal.state is not ActionState.OUTCOME
            or c.before_observation is None or c.after_observation is None
            or c.movement_distance is None or c.movement_distance < 0.05
            or owner.supervisor is not supervisor
            or owner.supervisor.open_actions
        ):
            raise D6StagedMoveRejected("original S15/S16 movement unqualified")
        source_pos = c.before_observation.snapshot.position
        after_pos = c.after_observation.snapshot.position
        distance_before = math.hypot(
            choice.target_x - source_pos.x, choice.target_z - source_pos.z,
        )
        distance_after = math.hypot(
            choice.target_x - after_pos.x, choice.target_z - after_pos.z,
        )
        if distance_after >= distance_before - 0.05:
            raise D6StagedMoveRejected("physical MOVE did not approach real native item")
        report["d6_original_s49_move_actions"].append({
            "action_id": receipt.terminal.action_id,
            "intent_id": receipt.terminal.intent_id,
            "session_id": sid,
            "item_entity_id": item_id,
            "decision_seq": current.seq,
            "decision_request_id": current.request_id,
            "native_source": current.provenance.reference,
            "target_distance_before_m": distance_before,
            "target_distance_after_m": distance_after,
            "movement_m": c.movement_distance,
            "terminal": receipt.terminal.state.value,
            "action_ref": c.action_ref,
            "s15_before_seq": c.before_observation.seq,
            "s15_dispatch_seq": c.dispatch_receipt.seq,
            "s15_clear_seq": c.cleanup_receipt.seq,
            "s15_after_seq": c.after_observation.seq,
            "food_identity_verified_by_entity": False,
            "pickup_verified_by_move_alone": False,
        })
        report["original_s49_actions"] = owner._count
        report["self_action_issued"] = True
        report["d6_post_move_eat_fenced"] = (
            owner._post_move_settling_unqualified
        )
        report["d6_original_fence_sha256"] = fence.sha256
        report["d6_original_fence_unresolved"] = fence.unresolved
        # A STOP ACK is not physical settling. This wait does not authorize EAT.
        await asyncio.sleep(0.65)
    if (
        not report["d6_original_s49_move_actions"]
        or not report["d6_post_move_eat_fenced"]
        or fence.unresolved
        or any(
            owner.supervisor.get(action_id).state is not ActionState.OUTCOME
            for action_id in owner._dispatched
        )
        or len(fence.actions) != owner._count
    ):
        raise D6StagedMoveRejected("original S49 bounded loot MOVEs did not close")
    report["d6_original_move_count"] = owner._count
    report["d6_item_native_id"] = last_item_id
    report["d6_same_supervisor"] = owner.supervisor is supervisor


async def run(report_path: Path, log_path: Path, fence_path: Path) -> int:
    if (
        os.environ.get("S49_REAL_SERVER_CI") != "1"
        or os.environ.get("BUG0_PICKUP_D1_DEV_ONLY") != "1"
        or os.environ.get("D6_STAGED_LOOT_MOVE_WORLD_ONLY") != "1"
        or report_path.parent.resolve() != fence_path.parent.resolve()
        or fence_path == report_path or fence_path == log_path
    ):
        return _blocked(report_path, "exclusive D6 original S49 World grant absent")
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        fence = preflight_move_fence(fence_path)
    except Exception as exc:
        return _blocked(report_path, f"{type(exc).__name__}: {exc}")
    async def on_staged(session, report, source_log):
        await move_from_real_item(session, report, source_log, fence=fence)
    return await d1_world_qualify(
        report_path, log_path, post_staged_move_dev=on_staged,
    )


def _blocked(path: Path, reason: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "status": "BLOCKED", "classification": "D6_PREWORLD_REFUSED",
        "failure": reason, "real_world_started": False,
        "original_s49_actions": 0, "physical_action_issued": False,
    }, sort_keys=True, indent=2) + "\n", encoding="utf8")
    return 2


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--server-log", required=True, type=Path)
    p.add_argument("--move-fence", required=True, type=Path)
    a = p.parse_args()
    raise SystemExit(asyncio.run(run(a.report, a.server_log, a.move_fence)))


if __name__ == "__main__":
    main()
