"""Single DEV real Paper World: original S49 owner repeatedly ATTACKs a staged zombie.

Dev arena operator stages a managed AI-disabled low-health target. Only
original NormalSessionActionExecutor issues physical ATTACKs. An independent
Paper source must identify the exact real zombie death and killer as RelaySelf.
No claim of autonomous threat selection, natural food pickup, EAT or learning.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE
from relay_self.action import ActionState
from relay_self.eat_hunger import EatCursor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import (
    NonMotionReplay,
    OriginalS49NonMotionFence,
)
from tools.bug0_d4_natural_loot_eat import run_natural_loot_eat
from tools.bug0_natural_drop_d2_world import CONFIG, RESPAWN_JAR, WITNESS_JAR
from tools.bug0_pickup_d1_world import _artifact, _inventory, _original_marker
from tools.bug0_zombie_respawn_r1_world import _native_probe


class S49D3Rejected(RuntimeError):
    """A physically issued or source-qualified combat fact is not established."""


def paper_death_seen(log: str) -> bool:
    """Operator-only terminal gate: do not attempt a next strike on a corpse.

    No Paper World truth is projected to the Self's native L0 policy.
    The independent post-audit still must establish actual killer identity.
    """
    hits = [
        line for line in log.splitlines()
        if "RSELF_NATURAL_DROP_DEATH world=" in line
    ]
    if len(hits) > 1:
        raise S49D3Rejected("duplicated original Paper death marker")
    return len(hits) == 1


def _target(probe, entity_id=None):
    cov = probe.snapshot.nearby_entities_coverage
    nearby = probe.snapshot.nearby_entities
    if (
        probe.kind != "probe" or not probe.request_id
        or probe.provenance.source != "mineflayer"
        or cov.truncated or cov.candidate_count != 1
        or len(nearby) != 1 or nearby[0].name != "zombie"
        or not 0.1 <= nearby[0].distance <= 2.8
        or (entity_id is not None and nearby[0].entity_id != entity_id)
        or probe.snapshot.health <= 0
    ):
        raise S49D3Rejected("one complete original native melee zombie is required")
    return nearby[0]


def qualified_native_precombat_hunger(
    observation: MineflayerObservation, session_id: str,
) -> bool:
    """Read-only DEV gate before the original S49 combat; never issue EAT.

    The operator uses vanilla Hunger; this predicate does not mutate food
    or weaken the original S46/S49 appetite threshold. The zombie is still
    alive and threatening here, so this is deliberately not an EAT grant.
    """
    if (
        not isinstance(observation, MineflayerObservation)
        or observation.kind != "probe"
        or not observation.request_id
        or observation.session_id != session_id
        or observation.provenance.source != "mineflayer"
        or observation.snapshot.health <= 15
        or observation.snapshot.oxygen_level == 0
        or observation.snapshot.nearby_entities_coverage.truncated
    ):
        raise S49D3Rejected("precombat hunger requires viable original native source")
    return 0 < observation.snapshot.food < EatCursor(session_id).threshold


def preflight_original_nonmotion_fence(path: Path) -> tuple[OriginalS49NonMotionFence, bool]:
    """Restore before ANY World; never reset previous physical history.

    A sealed journal from an older World is NOT a transferable Action grant.
    Only an empty, independently restored journal may start a new World.
    """
    if not isinstance(path, Path) or not path.parent.is_dir():
        raise S49D3Rejected("preexisting persistent evidence directory required")
    if path.exists() or path.is_symlink():
        fence = OriginalS49NonMotionFence.restore(
            path, self_id="s49-original-self",
        )
        fence.require_clear()
        if fence.actions:
            raise NonMotionReplay("prior World physical history cannot be reseeded")
        return fence, True
    return OriginalS49NonMotionFence.create(
        path, self_id="s49-original-self",
    ), False


async def run(
    report_path: Path, log_path: Path, *, post_respawn_dev=None,
    nonmotion_fence_path: Path | None = None,
) -> int:
    report = {
        "stage": "NOT_STARTED", "status": "BLOCKED",
        "classification": "D4_WORLD_NOT_RUN",
        "s49_actions": [], "original_action_issuer": "S49",
        "operator_world_staging": [],
        "operator_world_kill": False,
        "operator_zombie_health_pinned_for_dev": 1.6,
        "operator_staged_no_ai": True,
        "self_goal_selected_autonomously": False,
        "self_attack_principal_attested": False,
        "self_move_to_loot": False, "self_eat": False,
        "d4_natural_food_pickup_eat_proven": False,
        "d4_operator_removed_only_nonzombie_entities": True,
        "real_model_calls": 0, "learning_updated": False,
    }
    server = collector = session = temp = None
    nonmotion_fence = None
    rc = 2
    try:
        if (
            os.environ.get("S49_REAL_SERVER_CI") != "1"
            or os.environ.get("BUG0_S49_D4_ONE_WORLD_ONLY") != "1"
            or os.environ.get("NODE_OPTIONS")
        ):
            raise S49D3Rejected("exclusive source-bound S49 D3 World approval absent")
        if nonmotion_fence_path is not None:
            if (
                os.environ.get("S49_D5_NONMOTION_FENCE_DEV_ONLY") != "1"
                or not isinstance(nonmotion_fence_path, Path)
                or nonmotion_fence_path.parent.resolve()
                != report_path.parent.resolve()
                or nonmotion_fence_path == report_path
                or nonmotion_fence_path == log_path
            ):
                raise S49D3Rejected("explicit fenced D5 World gate and evidence path required")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            nonmotion_fence, restored = preflight_original_nonmotion_fence(
                nonmotion_fence_path,
            )
            report["nonmotion_fence_preflight"] = {
                "checked_before_world": True,
                "restored_existing_empty": restored,
                "prior_actions": len(nonmotion_fence.actions),
                "filename": nonmotion_fence_path.name,
            }
        paper = _artifact(
            "BUG0_D4_PAPER_JAR", sha=PAPER_1218_SHA256, size=PAPER_1218_SIZE,
        )
        respawn = _artifact(
            "BUG0_D4_RESPAWN_JAR", sha=os.environ.get("BUG0_D4_RESPAWN_SHA256", ""),
        )
        witness = _artifact(
            "BUG0_D4_WITNESS_JAR", sha=os.environ.get("BUG0_D4_WITNESS_SHA256", ""),
        )
        if (
            respawn.name != RESPAWN_JAR or witness.name != WITNESS_JAR
            or len({paper, respawn, witness}) != 3
        ):
            raise S49D3Rejected("unexpected artifact or World fixture")
        temp = tempfile.TemporaryDirectory(prefix="bug0-d4-natural-meat-eat-")
        root = Path(temp.name)
        _write_config(root)
        shutil.copyfile(paper, root / "minecraft.jar")
        plugins = root / "plugins"
        plugins.mkdir()
        for jar, name in (
            (respawn, "RelayZombieRespawnDev"),
            (witness, "RelayZombieDropWitnessDev"),
        ):
            shutil.copyfile(jar, plugins / jar.name)
            cfg = plugins / name
            cfg.mkdir()
            (cfg / "config.yml").write_text(CONFIG, encoding="utf8")

        report["stage"] = "PAPER_WORLD_STARTED"
        server, collector, _ = await _ready_server(
            root, root / "minecraft.jar", log_path,
        )
        report["real_world_started"] = True
        report["stage"] = "AUTHENTIC_MINEFLAYER_SESSION"
        session = await _new_session()
        sid = session.started.session_id
        report["session_id"] = sid
        await _original_marker(log_path, "RSELF_RESPAWN_READY", budget=12)
        await _original_marker(log_path, "RSELF_NATURAL_DROP_READY", budget=12)
        report["initial_paper"] = await _original_marker(
            log_path, "RSELF_RESPAWN_INITIAL world=", budget=12,
        )
        report["native_initial"] = await _native_probe(session, "d4-managed-initial")
        d4_baseline = await _correlated_observe(session, "d4-before-combat-food")
        report["d4_baseline_inventory"] = _inventory(d4_baseline)
        if report["d4_baseline_inventory"]["rotten_flesh"] != 0:
            raise S49D3Rejected("native Self already had rotten flesh before kill")

        intent = IntentCommitment()
        intent.commit(
            "escape-threat", objective="bounded S49 physical ATTACK fallback only",
            at_ns=1, provenance=Provenance("d3-real-operator-scope", "committed-intent"),
        )
        owner = NormalSessionActionExecutor(
            sid, intent, max_sequential_attacks=8,
            max_intent_epochs=2 if post_respawn_dev is not None else 1,
        )
        policy = S49BasicPriorityL0(sid, max_decisions=30)

        # Operator configures only the arena's target; it never sends a bot
        # ATTACK or creates a second S49 issuer.
        report["stage"] = "OPERATOR_PREPARES_SINGLE_NEAR_LETHAL_TARGET"
        basic_commands = (
            "gamerule doMobSpawning false",
            "gamerule doMobLoot true",
            "gamemode survival RelaySelf",
            "tag @e[type=minecraft:zombie,limit=1] add RelaySelfAttackTarget",
            "execute at RelaySelf run tp "
            "@e[type=minecraft:zombie,tag=RelaySelfAttackTarget,limit=1] ~0.65 ~ ~",
            "data merge entity "
            "@e[type=minecraft:zombie,tag=RelaySelfAttackTarget,limit=1] "
            "{NoAI:1b,Silent:1b,Health:1.6f}",
            "effect give RelaySelf minecraft:hunger 70 20 true",
        )
        # Operator cleanup must never remove the Paper-owned zombie. For
        # D5 only, defer nonzombie cleanup until just before the first S49
        # admission: R2 observed two native nearby entities despite the
        # older early cleanup, with no ATTACK issued. Suppress mob drops
        # from this fixture-only cleanup; restore real mob loot for the
        # later actual zombie death.
        nonzombie_clear = "kill @e[type=!minecraft:player,type=!minecraft:zombie]"
        if post_respawn_dev is None:
            before_hunger = basic_commands[:3] + (nonzombie_clear,) + basic_commands[3:]
            after_hunger = ()
        else:
            before_hunger = basic_commands
            after_hunger = (
                "gamerule doMobLoot false",
                nonzombie_clear,
                "gamerule doMobLoot true",
            )
        report["operator_world_staging"] = list(before_hunger + after_hunger)
        for cmd in before_hunger:
            _command(server, cmd)
        await server.stdin.drain()
        await asyncio.sleep(0.8)

        # The earlier D4 original World showed food 20 -> 14 while L0
        # correctly refused to EAT (threshold 14 is exclusive). Do not
        # change L0, fabricate inventory, alter WorldBody coefficients or
        # extend combat across the 600tick next-zombie spawn. Qualify the
        # vanilla operator-induced hunger *before* the first strike, when
        # there is no World-side respawn countdown yet.
        report["stage"] = "OPERATOR_DEV_PRECOMBAT_NATIVE_HUNGER_WINDOW"
        report["d4_precombat_hunger_probes"] = []
        report["d4_precombat_hunger_qualified"] = False
        for attempt in range(1, 81):
            source = await _correlated_observe(
                session, f"d4-precombat-native-hunger-{attempt:02d}",
            )
            report["d4_precombat_hunger_probes"].append({
                "request_id": source.request_id,
                "seq": source.seq,
                "food": source.snapshot.food,
                "health": source.snapshot.health,
                "source": source.provenance.reference,
            })
            if qualified_native_precombat_hunger(source, sid):
                report["d4_precombat_hunger_qualified"] = True
                report["d4_precombat_hunger_last"] = {
                    "seq": source.seq,
                    "food": source.snapshot.food,
                    "session_id": source.session_id,
                    "request_id": source.request_id,
                }
                break
            await asyncio.sleep(0.55)
        if not report["d4_precombat_hunger_qualified"]:
            raise S49D3Rejected(
                "DEV native hunger never crossed original S49 EAT threshold"
            )

        if after_hunger:
            report["stage"] = "D5_DEV_LATE_NONZOMBIE_WORLD_CLEANUP"
            for cmd in after_hunger:
                _command(server, cmd)
            await server.stdin.drain()
            await asyncio.sleep(0.3)
            report["d5_operator_late_cleanup_done"] = True

        report["stage"] = "ORIGINAL_S49_BOUNDED_NATIVE_ATTACKS"
        target_id = None
        death_logged = False
        for i in range(1, 9):
            # After every previous strike's OUTCOME, collect *new* native
            # witnesses. Do not reissue on UNKNOWN or stale/risky input.
            if owner.supervisor.open_actions:
                raise S49D3Rejected("S49 unresolved prior Action blocks attack")
            await asyncio.sleep(0.75)
            if i > 1 and paper_death_seen(log_path.read_text(encoding="utf8")):
                death_logged = True
                break
            previous = await _correlated_observe(session, f"d3-hit-{i}-pre")
            await asyncio.sleep(0.25)
            current = await _correlated_observe(session, f"d3-hit-{i}-fresh")
            if i > 1 and paper_death_seen(log_path.read_text(encoding="utf8")):
                death_logged = True
                break
            try:
                mob = _target(previous, target_id)
                _target(current, mob.entity_id)
            except S49D3Rejected:
                if i > 1:
                    # The Paper death can arrive after native after-attack ACK
                    # but before the next native melee target sample settles.
                    await asyncio.sleep(0.25)
                    if paper_death_seen(log_path.read_text(encoding="utf8")):
                        death_logged = True
                        break
                raise
            target_id = mob.entity_id
            chosen = policy.decide(current)
            if (
                chosen.selected != "DEFER"
                or chosen.preferred != "MOVE_AWAY"
                or chosen.fallback != "ATTACK"
            ):
                raise S49D3Rejected("source does not permit operator combat fallback")
            action_id = f"d3-s49-attack-{i}-{sid}"
            common = dict(
                intent_id=intent.current_intent.intent_id,
                session_id=sid, action_id=action_id,
                probe_seq=current.seq, probe_request_id=current.request_id,
                target_entity_id=target_id, granted=True,
            )
            propose = NormalAttackingAuthorization(
                stage=NormalActionStage.PROPOSE,
                authority_id=f"operator-d3-propose-{i}",
                provenance=Provenance("d3-operator-physical-grant", f"propose-{i}"),
                **common,
            )
            issue = NormalAttackingAuthorization(
                stage=NormalActionStage.ISSUE,
                authority_id=f"operator-d3-issue-{i}",
                provenance=Provenance("d3-operator-physical-grant", f"issue-{i}"),
                **common,
            )
            owner.require_attack_authorizations(
                previous, current, target_id, propose, issue,
            )
            report["stage"] = f"ORIGINAL_S49_PHYSICAL_ATTACK_{i}"
            # If interrupted after admission, record UNKNOWN; never retry ID.
            try:
                receipt = await owner.execute_attack(
                    session, previous, current, target_id, propose, issue,
                    allow_target_disappearance=True,
                    physical_fence=nonmotion_fence,
                )
            finally:
                report["owner_action_count"] = owner._count
                report["owner_attack_count"] = owner._attack_count
                report["original_supervisor_open_count"] = len(
                    owner.supervisor.open_actions,
                )
            if (
                receipt.terminal.state is not ActionState.OUTCOME
                or receipt.effect.result != "applied"
                or receipt.target_entity_id != target_id
                or receipt.after_probe.seq <= receipt.effect.seq
            ):
                raise S49D3Rejected("original native ATTACK terminal unqualified")
            report["s49_actions"].append({
                "action_id": action_id, "session_id": sid,
                "target_entity_id": target_id,
                "previous_seq": previous.seq, "admitted_seq": current.seq,
                "effect_seq": receipt.effect.seq,
                "after_seq": receipt.after_probe.seq,
                "terminal": receipt.terminal.state.value,
                "ack": receipt.effect.result,
                "native_target_missing": receipt.target_missing_in_native_view,
                "kill_attested_by_effect_ack": False,
                "scope": "ORIGINAL_S49_NATIVE_ATTACK_COMMAND_ONLY",
            })
            if paper_death_seen(log_path.read_text(encoding="utf8")):
                death_logged = True
                break
            if receipt.target_missing_in_native_view:
                report["stage"] = "WAIT_INDEPENDENT_WORLD_DEATH_SOURCE"
                report["paper_loot_death"] = await _original_marker(
                    log_path, "RSELF_NATURAL_DROP_DEATH world=", budget=6,
                )
                death_logged = True
                break
        if not death_logged or not report["s49_actions"]:
            raise S49D3Rejected("no genuine Paper death after bounded S49 ATTACKs")

        report["stage"] = "PAPER_SOURCE_KILLER_ATTESTATION"
        report["paper_loot_death"] = await _original_marker(
            log_path, "RSELF_NATURAL_DROP_DEATH world=", budget=8,
        )
        report["paper_respawn_death"] = await _original_marker(
            log_path, "RSELF_RESPAWN_DEATH world=", budget=8,
        )
        if "killer_is_relay_self=true" not in report["paper_loot_death"]:
            raise S49D3Rejected("Paper independently did not identify RelaySelf killer")
        report["self_attack_principal_attested"] = True
        report["attack_count"] = len(report["s49_actions"])
        report["native_last_action"] = report["s49_actions"][-1]["action_id"]

        # Original Paper death is the only World evidence for natural food.
        # The native Self must independently observe the actual inventory
        # before/after real pickup; no operator meat staging or teleport
        # is allowed after death, and S49 alone issues optional real EAT.
        report["real_rotten_flesh_count"] = int(
            report["paper_loot_death"].split("rotten_count=")[1].split()[0]
        )
        report["d4_combat_closed_action_count"] = owner._count
        report["stage"] = "D4_ORIGINAL_NATURAL_MEAT_PICKUP_AND_S49_EAT"
        d4_eaten = await run_natural_loot_eat(
            session, server, owner, report, log_path,
            baseline=d4_baseline,
            natural_count=report["real_rotten_flesh_count"],
            physical_fence=nonmotion_fence,
        )
        report["self_eat"] = d4_eaten
        report["d4_natural_food_pickup_eat_proven"] = d4_eaten
        report["stage"] = "WAIT_WORLD_600TICK_NEW_GENERATION"
        report["paper_respawn"] = await _original_marker(
            log_path, "RSELF_RESPAWN_SPAWN world=", budget=86,
        )
        report["native_respawn"] = await _native_probe(session, "d4-new-generation")
        if (
            report["native_initial"]["session_id"]
            != report["native_respawn"]["session_id"]
            or report["native_initial"]["zombie_entity_id"]
            == report["native_respawn"]["zombie_entity_id"]
            or owner.supervisor.open_actions
            or owner._attack_count != report["attack_count"]
            or owner._count != owner._attack_count + int(d4_eaten)
        ):
            raise S49D3Rejected("same original S49 ATTACK/EAT owner or new World generation invalid")
        report["d4_final_action_count"] = owner._count
        report["d4_final_supervisor_open_count"] = len(owner.supervisor.open_actions)
        report["stage"] = "D4_WORLD_SOURCE_CLOSED"
        report["status"] = "PASS_DEV"
        report["classification"] = (
            "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS"
            if d4_eaten
            else "D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS"
        )
        if post_respawn_dev is not None:
            # Optional D5 child only. D4's original no-hook entrypoint and
            # source/eat evidence remain unchanged and reusable by audit.
            # A genuine zero-loot death is a valid World outcome. Do not
            # require or fabricate EAT before the next independent Intent.
            if nonmotion_fence is None:
                await post_respawn_dev(session, server, owner, report, log_path)
            else:
                await post_respawn_dev(
                    session, server, owner, report, log_path,
                    physical_fence=nonmotion_fence,
                )
            report["classification"] = "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS"
        rc = 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["classification"] = (
            "D5_SECOND_INTENT_UNQUALIFIED"
            if post_respawn_dev is not None else "D4_NATURAL_EAT_UNQUALIFIED"
        )
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = repr(exc)
                try:
                    report["node_exit"] = await session.terminate()
                except Exception as second:
                    report["node_terminate_error"] = repr(second)
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
            except Exception as exc:
                report["server_cleanup_error"] = repr(exc)
                if server.returncode is None:
                    server.kill()
                    await server.wait()
                report["java_exit"] = server.returncode
        if temp is not None:
            temp.cleanup()
        if (
            report.get("node_exit") != 0
            or report.get("java_exit") != 0
            or any(key.endswith("_error") for key in report)
        ):
            report["classification"] = "D4_CLEANUP_UNQUALIFIED"
            report["status"] = "FAIL"
            rc = 2
        report["cleanup_done"] = True
        if nonmotion_fence_path is not None:
            try:
                persisted = OriginalS49NonMotionFence.restore(
                    nonmotion_fence_path, self_id="s49-original-self",
                )
                report["nonmotion_fence"] = {
                    "sha256": persisted.sha256,
                    "unresolved": persisted.unresolved,
                    "action_ids": [x["action_id"] for x in persisted.actions],
                    "kinds": [x["kind"] for x in persisted.actions],
                    "statuses": [x["status"] for x in persisted.actions],
                    "physical_exactly_once_attested": False,
                }
                if report["status"] == "PASS_DEV":
                    persisted.require_clear()
                    if not persisted.actions:
                        raise S49D3Rejected("fenced physical run issued no Actions")
            except Exception as exc:
                report["nonmotion_fence_readback_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
                report["status"] = "FAIL"
                report["classification"] = "D5_NONMOTION_FENCE_UNQUALIFIED"
                rc = 2
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf8",
        )
    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--server-log", required=True, type=Path)
    args = p.parse_args()
    raise SystemExit(asyncio.run(run(args.report, args.server_log)))


if __name__ == "__main__":
    main()
