"""One native Minecraft ATTACK from original S49 owner (DEV).

Operator stages a stationary zombie, but only the original owner observes,
checks native priority, and issues one separately authorized Action. No
independent combat AI, second supervisor or implied damage claims.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adapters.mineflayer.attack_execution import AttackActionReceipt
from adapters.mineflayer.s49_attack_server_health import (
    TARGET_TAG,
    sample_tagged_zombie_health,
)
from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from relay_self.provenance import Provenance


class S49AttackDevRejected(RuntimeError):
    """The one-shot native ATTACK was blocked or its issuer was unqualified."""


def attack_dev_source(reference: str) -> Provenance:
    return Provenance("s49-local-attack-operator-dev", reference)


async def run_s49_attack_dev(
    session: MineflayerProcessSession, server: object,
    owner: NormalSessionActionExecutor, report: dict[str, Any],
    *, health_log: Path | None = None,
) -> AttackActionReceipt:
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or not isinstance(session, MineflayerProcessSession)
        or session.started.session_id != owner.session_id
        or session.process_returncode is not None
        or getattr(server, "stdin", None) is None
        or owner._count != 0 or owner._dispatched
        or owner.supervisor.open_actions
        or owner._post_move_settling_unqualified
        or (health_log is not None and not isinstance(health_log, Path))
    ):
        raise S49AttackDevRejected("fresh original S49 sole issuer required")
    sid = owner.session_id
    report["stage"] = "BUG0_S49_ATTACK_NATIVE_STAGING"
    report["actual_native_actions"] = []
    report["attack_native_probes"] = []
    report["attack_effect_commands_issued"] = 0
    report["operator_world_commands"] = []
    report["independent_attack_principal_attested"] = False
    report["damage_attested"] = False
    report["target_death_attested"] = False
    report["real_model_calls"] = 0
    report["learning_in_world"] = False
    report["m_energy_credited"] = False
    report["automatic_goal_selection"] = False

    async def stage(*commands: str) -> None:
        for command in commands:
            _command(server, command)
            report["operator_world_commands"].append(command)
        await server.stdin.drain()

    # Natural mobs/items must not be silently ignored by the attack policy.
    # One fixed NoAI target is staged only after the native World is cleared.
    await stage(
        "gamerule doMobSpawning false",
        "gamerule doDaylightCycle false",
        "time set night",
        "kill @e[type=!minecraft:player]",
        "gamemode survival RelaySelf",
        "effect clear RelaySelf minecraft:hunger",
    )
    await asyncio.sleep(2)
    summon_nbt = (
        '{NoAI:1b,Silent:1b,PersistenceRequired:1b,'
        f'Tags:["{TARGET_TAG}"]}}'
        if health_log is not None
        else "{NoAI:1b,Silent:1b,PersistenceRequired:1b}"
    )
    await stage(
        "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
        + summon_nbt,
    )
    policy = S49BasicPriorityL0(sid, max_decisions=14)
    previous = None
    current = None
    for index in range(8):
        await asyncio.sleep(0.6)
        observed = await _correlated_observe(
            session, f"s49-bug0-attack-source-{index:02d}",
        )
        decision = policy.decide(observed)
        report["attack_native_probes"].append({
            "probe_seq": observed.seq,
            "request_id": observed.request_id,
            "native_nearby": [{
                "entity_id": e.entity_id, "name": e.name,
                "distance": e.distance,
            } for e in observed.snapshot.nearby_entities],
            "candidate_count": observed.snapshot.nearby_entities_coverage.candidate_count,
            "coverage_truncated": observed.snapshot.nearby_entities_coverage.truncated,
            "selected": decision.selected,
            "preferred": decision.preferred,
            "fallback": decision.fallback,
            "reason": decision.reason,
        })
        targets = observed.snapshot.nearby_entities
        if (
            decision.selected == "DEFER"
            and decision.preferred == "MOVE_AWAY"
            and decision.fallback == "ATTACK"
            and len(targets) == 1
            and targets[0].name == "zombie"
            and 0.1 <= targets[0].distance <= 2.8
            and not observed.snapshot.nearby_entities_coverage.truncated
            and observed.snapshot.nearby_entities_coverage.candidate_count == 1
        ):
            if previous is None:
                previous = observed
            else:
                current = observed
                break
        else:
            # Any observed non-zombie entity or truncated coverage blocks the
            # single-shot authorization, never yields an inferred safe arena.
            if targets or observed.snapshot.nearby_entities_coverage.truncated:
                raise S49AttackDevRejected(
                    "native target risk or multiple entities before ATTACK"
                )
    if previous is None or current is None:
        raise S49AttackDevRejected("two native near-zombie probes not obtained")
    target_id = current.snapshot.nearby_entities[0].entity_id
    report["stage"] = "BUG0_S49_ORIGINAL_ATTACK_ADMISSION"
    action_id = f"bug0-s49-attack-{sid}"
    shared = {
        "intent_id": owner.intent.current_intent.intent_id,
        "session_id": sid,
        "action_id": action_id,
        "probe_seq": current.seq,
        "probe_request_id": current.request_id,
        "target_entity_id": target_id,
        "granted": True,
    }
    propose = NormalAttackingAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="s49-attack-operator-propose",
        provenance=attack_dev_source("s49-attack-propose"),
        **shared,
    )
    issue = NormalAttackingAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="s49-attack-operator-issue",
        provenance=attack_dev_source("s49-attack-issue"),
        **shared,
    )
    # Check all sources before issuing; malformed target MUST use no IO.
    owner.require_attack_authorizations(
        previous, current, target_id, propose, issue,
    )
    # Independent Minecraft *server-side* Health sample. This is a distinct
    # read-only observation source, not an additional Action or grant. If it
    # fails, stop BEFORE issuing the one irreversible ATTACK.
    before_health = None
    nonce = sid.replace("-", "")[:20]
    if health_log is not None:
        report["attack_health_readback_scope"] = (
            "PAPER_OPERATOR_STAGED_TAGGED_ZOMBIE_ONLY"
        )
        report["attack_server_health_drop_observed"] = False
        before_health = await sample_tagged_zombie_health(
            server, health_log, stage="before", nonce=nonce,
        )
        report["attack_server_health_before"] = asdict(before_health)
        if before_health.health != 20.0:
            raise S49AttackDevRejected(
                "target already injured before original S49 ATTACK admission"
            )
    report["attack_action_id"] = action_id
    report["attack_target_entity_id"] = target_id
    report["attack_effect_commands_issued"] = "UNKNOWN_IF_INTERRUPTED"
    report["stage"] = "BUG0_S49_SUPERVISED_NATIVE_ATTACK"
    try:
        receipt = await owner.execute_attack(
            session, previous, current, target_id, propose, issue,
        )
    finally:
        try:
            report["attack_action_terminal"] = owner.supervisor.get(
                action_id,
            ).state.value
        except (KeyError, ValueError):
            report["attack_action_terminal"] = "NOT_ISSUED"
    if (
        receipt.terminal is not owner.supervisor.get(action_id)
        or receipt.terminal.state is not ActionState.OUTCOME
        or owner._count != 1 or owner.supervisor.open_actions
        or len(owner._dispatched) != 1
        or receipt.effect.action_id != action_id
        or receipt.effect.effect != "attack_entity"
        or receipt.effect.result != "applied"
        or receipt.target_entity_id != target_id
        or receipt.after_probe.seq <= receipt.effect.seq
    ):
        raise S49AttackDevRejected("original S49 native ATTACK effect not closed")
    report["actual_native_actions"] = [{
        "action_id": action_id,
        "kind": "ATTACK",
        "terminal": receipt.terminal.state.value,
        "same_supervisor": True,
        "session_id": sid,
        "target_entity_id": target_id,
    }]
    report["attack_effect_commands_issued"] = 1
    report["attack_evidence"] = {
        "before_probe_seq": current.seq,
        "effect_seq": receipt.effect.seq,
        "after_probe_seq": receipt.after_probe.seq,
        "target_entity_id": target_id,
        "effect": receipt.effect.effect,
        "native_effect_result": receipt.effect.result,
        "target_hurt_event_observed": receipt.observed_target_hurt,
        "hurt_source_entity_ids": list(receipt.observed_hurt_source_entity_ids),
        "damage_attested": False,
        "target_death_attested": False,
        "source_independently_attested": False,
        "outcome_scope": "ATTACK_COMMAND_EFFECT_APPLIED_ONLY",
    }
    if before_health is not None:
        # Wait for server-side combat ticks without replaying native ATTACK.
        # This does not qualify physical damage by itself: only the Paper
        # before/after data sample can show a measured Health difference.
        await asyncio.sleep(1.0)
        after_health = await sample_tagged_zombie_health(
            server, health_log, stage="after", nonce=nonce,
        )
        report["attack_server_health_after"] = asdict(after_health)
        damage_drop = before_health.health - after_health.health
        report["attack_server_health_delta"] = damage_drop
        report["attack_server_health_drop_observed"] = damage_drop > 0
        report["attack_evidence"]["server_health_drop_observed"] = damage_drop > 0
        report["attack_evidence"]["server_health_delta"] = damage_drop
        report["attack_evidence"]["server_health_source"] = (
            "ORIGINAL_PAPER_SERVER_CONSOLE"
        )
        # Do NOT promote this to independent causal/principal attestation.
        report["attack_evidence"]["damage_attested"] = False
        report["attack_evidence"]["target_death_attested"] = False
        report["attack_evidence"]["source_independently_attested"] = False
        report["attack_evidence"]["outcome_scope"] = (
            "ATTACK_COMMAND_ACK_PLUS_PAPER_HEALTH_READBACK"
        )
    report["stage"] = "BUG0_S49_ATTACK_EFFECT_CLOSED"
    return receipt
