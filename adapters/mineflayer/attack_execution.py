"""S49 owned ATTACK native effect execution, DEV only.

A Mineflayer effect_result(applied) proves only adapter command execution, not
damage, death, or physical attribution. No auto-retry of an unknown strike.
This module never constructs another ActionSupervisor or authorization.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityHurt,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.skill import SkillExecution, SkillState


class AttackExecutionRejected(ValueError):
    """Native command proof, target identity or S49 custody was unavailable."""


@dataclass(frozen=True, slots=True)
class AttackActionReceipt:
    terminal: ActionLifecycle
    effect: MineflayerEffectResult
    after_probe: MineflayerObservation
    target_entity_id: int
    observed_target_hurt: bool
    observed_hurt_source_entity_ids: tuple[int | None, ...]
    damage_attested: bool = False
    target_death_attested: bool = False
    source_independently_attested: bool = False


def _target_from(probe: MineflayerObservation, entity_id: int) -> object:
    if (
        not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe"
        or not probe.request_id
        or probe.snapshot.nearby_entities_coverage.truncated
        or probe.snapshot.nearby_entities_coverage.candidate_count != 1
        or len(probe.snapshot.nearby_entities) != 1
    ):
        raise AttackExecutionRejected("one complete native target is required")
    target = probe.snapshot.nearby_entities[0]
    if target.entity_id != entity_id or target.name != "zombie":
        raise AttackExecutionRejected("native attack target identity changed")
    return target


def verify_attack_effect(
    before: MineflayerObservation,
    effect: MineflayerEffectResult,
    after: MineflayerObservation,
    *, action_id: str, entity_id: int,
) -> None:
    """Verify just the original native command ACK and later target registry."""
    old = _target_from(before, entity_id)
    latest = _target_from(after, entity_id)
    if (
        before.session_id != after.session_id
        or not before.seq < effect.seq < after.seq
        or effect.session_id != before.session_id
        or effect.action_id != action_id
        or effect.effect != "attack_entity"
        or effect.result != "applied"
        or after.request_id == before.request_id
        or before.snapshot.health <= 0
        or after.snapshot.health <= 0
        or old.distance > 2.8
        or latest.distance > 16.0
        or any(
            abs(getattr(before.snapshot.position, k)
                - getattr(after.snapshot.position, k)) > 0.3
            for k in ("x", "y", "z")
        )
    ):
        raise AttackExecutionRejected("native ATTACK effect/current target unverified")


class IssuedAttackingExecutor:
    """Transport only. Caller is the original S49 ActionSupervisor."""

    def __init__(self) -> None:
        self._attempted: set[str] = set()

    async def execute(
        self, session: MineflayerProcessSession,
        supervisor: ActionSupervisor, issued: ActionLifecycle,
        before: MineflayerObservation, *, target_entity_id: int,
        skill_execution: SkillExecution, intent_commitment: IntentCommitment,
    ) -> AttackActionReceipt:
        if (
            not isinstance(session, MineflayerProcessSession)
            or not isinstance(supervisor, ActionSupervisor)
            or not isinstance(issued, ActionLifecycle)
            or not isinstance(skill_execution, SkillExecution)
            or not isinstance(intent_commitment, IntentCommitment)
            or session.process_returncode is not None
            or issued.state is not ActionState.ISSUED
            or not issued.is_current_snapshot
            or skill_execution.state is not SkillState.STARTED
            or not skill_execution.is_current_snapshot
            or skill_execution.skill_id != "attack"
            or intent_commitment.current_intent is None
            or intent_commitment.pending_reconsideration is not None
            or issued.intent_id != intent_commitment.current_intent.intent_id
            or skill_execution.intent_id != issued.intent_id
            or issued.skill_execution_id != skill_execution.execution_id
            or supervisor.get(issued.action_id) is not issued
            or supervisor.open_actions != (issued,)
            or issued.action_id in self._attempted
            or before.session_id != session.started.session_id
        ):
            raise AttackExecutionRejected("original issued S49 ATTACK Skill/Action required")
        _target_from(before, target_entity_id)
        if before.snapshot.nearby_entities[0].distance > 2.8:
            raise AttackExecutionRejected("target outside bounded native ATTACK reach")

        # Consume before IO: even a timeout/interrupt must NEVER repeat strike.
        self._attempted.add(issued.action_id)
        at_ns = (supervisor.last_at_ns or 0) + 1
        effect: MineflayerEffectResult | None = None
        after: MineflayerObservation | None = None
        hurt: list[MineflayerEntityHurt] = []
        try:
            await session.send_attack_entity(issued.action_id, entity_id=target_entity_id)
            for _ in range(120):
                frame = await asyncio.wait_for(session.receive(), timeout=9)
                if isinstance(frame, MineflayerEntityHurt):
                    hurt.append(frame)
                elif isinstance(frame, MineflayerEffectResult):
                    if (
                        effect is not None
                        or frame.action_id != issued.action_id
                        or frame.effect != "attack_entity"
                        or frame.result != "applied"
                    ):
                        raise AttackExecutionRejected("native ATTACK command not applied")
                    effect = frame
                    break
                elif not isinstance(frame, MineflayerObservation):
                    raise AttackExecutionRejected("native ATTACK source ended before ACK")
            if effect is None:
                raise AttackExecutionRejected("native ATTACK effect ACK absent")
            request_id = issued.action_id + "-after-attack"
            await session.send_observe(request_id)
            for _ in range(120):
                frame = await asyncio.wait_for(session.receive(), timeout=9)
                if isinstance(frame, MineflayerEntityHurt):
                    hurt.append(frame)
                elif isinstance(frame, MineflayerObservation):
                    if frame.kind == "probe":
                        if frame.request_id != request_id:
                            raise AttackExecutionRejected("foreign after-ATTACK native probe")
                        after = frame
                        break
                else:
                    raise AttackExecutionRejected("native ATTACK source ended after ACK")
            if after is None:
                raise AttackExecutionRejected("native after-ATTACK probe absent")
            verify_attack_effect(
                before, effect, after,
                action_id=issued.action_id, entity_id=target_entity_id,
            )
            terminal = supervisor.record_outcome(
                issued.action_id, at_ns=at_ns, provenance=after.provenance,
            )
            target_hurt = tuple(
                e.source_entity_id for e in hurt
                if e.session_id == before.session_id
                and before.seq < e.seq < after.seq
                and e.entity_id == target_entity_id
            )
            return AttackActionReceipt(
                terminal=terminal, effect=effect,
                after_probe=after, target_entity_id=target_entity_id,
                observed_target_hurt=bool(target_hurt),
                observed_hurt_source_entity_ids=target_hurt,
            )
        except BaseException:
            if supervisor.get(issued.action_id).state is ActionState.ISSUED:
                supervisor.mark_unknown(
                    issued.action_id, at_ns=at_ns, provenance=before.provenance,
                )
            raise
