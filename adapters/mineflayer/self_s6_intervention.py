"""S6 controlled-target World intervention contract, not a source/Action grant.

Separate operator authorization and EULA are required for any physical run.
Static S31A server command is submitted once; only later Mineflayer-native
source events can establish target visibility and original S49 Action closure.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s31a_real_server_ci import _command
from adapters.mineflayer.self_continuous_host import AppendOnlySessionEvents

CONFIRM = "SELF-S6-CONTROLLED-TARGET-ONE-SESSION"
AUTHORITY_RE = re.compile(
    r"https://github\.com/rinsakamo/relay-self/issues/537#issuecomment-[1-9][0-9]*\Z"
)
# Reuse the EXACT controlled S31A native command; this is an intervention,
# NOT a natural Minecraft mob encounter or an autonomous Self decision.
CONTROLLED_COMMAND = (
    "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
    "{NoAI:1b,Silent:1b,PersistenceRequired:1b}"
)


class S6InterventionRejected(ValueError):
    """S6 is not an authorization to infer real target or to replay command."""


@dataclass(frozen=True, slots=True)
class S6ControlledPlan:
    authority_reference: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authority_reference, str)
            or AUTHORITY_RE.fullmatch(self.authority_reference) is None
        ):
            raise S6InterventionRejected("new #537 one-shot operator authority reference required")


class S6ControlledIntervention:
    """Exactly one client submission to the owned disposable server.

    Server stdin drain != Minecraft command execution ACK != native target
    observation; S49 continues to decide and grant independently.
    """

    def __init__(
        self, plan: S6ControlledPlan, spawn: MineflayerObservation,
        sink: AppendOnlySessionEvents,
    ) -> None:
        if (
            not isinstance(plan, S6ControlledPlan)
            or not isinstance(spawn, MineflayerObservation)
            or spawn.kind != "spawn"
            or spawn.session_id != sink.session_id
            or not isinstance(sink, AppendOnlySessionEvents)
            or not spawn.provenance.reference
        ):
            raise S6InterventionRejected("native spawned owner and fresh event sink required")
        self.plan = plan
        self.spawn = spawn
        self.sink = sink
        self._attempted = False

    @property
    def attempted(self) -> bool:
        return self._attempted

    async def submit_once(self, server: object) -> None:
        if self._attempted:
            raise S6InterventionRejected("controlled target may not be submitted twice")
        self._attempted = True
        self.sink.write(
            "controlled_target_submission_intent",
            mode="EXTERNAL_WORLD_INTERVENTION_NOT_SELF_ACTION",
            authority_reference=self.plan.authority_reference,
            native_spawn_seq=self.spawn.seq,
            native_spawn_source=self.spawn.provenance.reference,
            command=CONTROLLED_COMMAND,
            command_executed_attested=False,
            target_native_observed=False, natural_spawn_claimed=False,
            action_authorized=False, learning_updates=0, habit_grants=0,
        )
        # S31A original owner writes one fixed command to existing Java stdin.
        # On drain timeout the command might already have been transmitted:
        # no retry and no false success.
        _command(server, CONTROLLED_COMMAND)
        stdin = getattr(server, "stdin", None)
        if stdin is None or not callable(getattr(stdin, "drain", None)):
            raise S6InterventionRejected("owned Minecraft stdin missing")
        await asyncio.wait_for(stdin.drain(), timeout=3.0)
        self.sink.write(
            "controlled_target_stdin_drained_unconfirmed",
            mode="EXTERNAL_WORLD_INTERVENTION_NOT_SELF_ACTION",
            native_spawn_seq=self.spawn.seq,
            command_executed_attested=False,
            target_native_observed=False,
            natural_spawn_claimed=False,
            action_authorized=False, learning_updates=0, habit_grants=0,
        )
