"""S8: operator-owned, TWO controlled encounters in ONE S49 World session.

Only an external experimental intervention. Never grants Self Action, certifies
Minecraft command execution or natural mobs, or promotes Memory to learning.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command
from adapters.mineflayer.self_continuous_host import AppendOnlySessionEvents
from adapters.mineflayer.self_s6_intervention import AUTHORITY_RE
from relay_self.reactive_l0 import L0Step

TAG = "relay_s8_controlled"
SUMMON = (
    'execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ '
    '{NoAI:1b,Silent:1b,PersistenceRequired:1b,Tags:["relay_s8_controlled"]}'
)
CLEAR = f"kill @e[type=minecraft:zombie,tag={TAG}]"


class S8InterventionRejected(ValueError):
    """Never silently replay an uncertain external command."""


@dataclass(frozen=True, slots=True)
class S8TwoEpochPlan:
    authority_reference: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authority_reference, str)
            or AUTHORITY_RE.fullmatch(self.authority_reference) is None
        ):
            raise S8InterventionRejected("new #537 S8 physical authority required")


class S8TwoEpochIntervention:
    """Three at-most-once server stdin command attempts, same owned server.

    First controlled target follows native spawn and a durable session_started.
    Only after an independently closed S49 Action OUTCOME *and* existing S3
    Memory retention, clear the tagged target and introduce the second.
    Clear/summon submission is NOT a native server ACK. No third encounter.
    """

    def __init__(
        self, plan: S8TwoEpochPlan, spawn: MineflayerObservation,
        sink: AppendOnlySessionEvents,
    ) -> None:
        if (
            not isinstance(plan, S8TwoEpochPlan)
            or not isinstance(sink, AppendOnlySessionEvents)
            or not isinstance(spawn, MineflayerObservation)
            or spawn.kind != "spawn" or spawn.session_id != sink.session_id
            or not spawn.provenance.reference
        ):
            raise S8InterventionRejected("qualified native spawn and session owner required")
        self.plan = plan
        self.spawn = spawn
        self.sink = sink
        self.commands_attempted = 0
        self._first_ready = False
        self._second_started = False
        self._first_entity_id: int | None = None
        self._first_action_id: str | None = None
        self._second_closed = False

    @property
    def second_closed(self) -> bool:
        return self._second_closed

    async def _submit(self, server: object, command: str, *, stage: str) -> None:
        # Record intent BEFORE the potentially irreversible server write.
        # A write or drain failure may already have sent the command. No retry.
        self.commands_attempted += 1
        self.sink.write(
            "s8_external_command_intent", stage=stage,
            command_number=self.commands_attempted, command=command,
            authority_reference=self.plan.authority_reference,
            source_spawn=self.spawn.provenance.reference,
            external_intervention=True, command_executed_attested=False,
            native_target_identity_attested=False, action_authorized=False,
            learning_updates=0, habit_grants=0,
        )
        _command(server, command)
        stdin = getattr(server, "stdin", None)
        if stdin is None or not callable(getattr(stdin, "drain", None)):
            raise S8InterventionRejected("owned Minecraft server stdin missing")
        await asyncio.wait_for(stdin.drain(), timeout=3.0)
        self.sink.write(
            "s8_external_stdin_drained_unconfirmed",
            stage=stage, command_number=self.commands_attempted,
            command_executed_attested=False, native_target_identity_attested=False,
            action_authorized=False, learning_updates=0, habit_grants=0,
        )

    async def submit_first(self, server: object) -> None:
        if self.commands_attempted:
            raise S8InterventionRejected("first controlled target already attempted")
        # A failed/ambiguous send still consumes the at-most-once attempt.
        await self._submit(server, SUMMON, stage="epoch1_summon")
        self._first_ready = True

    async def after_action_closed(
        self, server: object, step: L0Step, receipt: NormalActionReceipt, *,
        memory_count: int,
    ) -> None:
        if not self._first_ready or not isinstance(receipt, NormalActionReceipt):
            raise S8InterventionRejected("no original S49 closed Action after first target")
        if receipt.terminal.action_id != step.action_request_id:
            raise S8InterventionRejected("foreign first or second Action")
        if not self._second_started:
            if self.commands_attempted != 1 or memory_count < 1:
                raise S8InterventionRejected("S3 observation not retained after first closure")
            self._first_entity_id = step.choice.entity_id
            self._first_action_id = receipt.terminal.action_id
            self._second_started = True  # no retry, including ambiguous clear
            self.sink.write(
                "s8_epoch1_closed_memory_retained",
                first_action_id=receipt.terminal.action_id,
                first_entity_id=self._first_entity_id,
                retained_observations=memory_count, goal_success_attested=False,
                learning_updates=0, habit_grants=0,
            )
            await self._submit(server, CLEAR, stage="clear_tagged_epoch1")
            await self._submit(server, SUMMON, stage="epoch2_summon")
            return
        if self._second_closed:
            raise S8InterventionRejected("more than two closed Actions forbidden")
        if (
            self.commands_attempted != 3
            or step.choice.entity_id == self._first_entity_id
            or receipt.terminal.action_id == self._first_action_id
        ):
            raise S8InterventionRejected("second distinct native target not established")
        if memory_count < 2:
            raise S8InterventionRejected("second S3 observation not retained")
        self._second_closed = True
        self.sink.write(
            "s8_epoch2_closed_distinct_target",
            second_action_id=receipt.terminal.action_id,
            second_entity_id=step.choice.entity_id,
            retained_observations=memory_count,
            memory_caused_action=False, goal_success_attested=False,
            learning_updates=0, habit_grants=0,
        )
