from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerPosition,
)
from adapters.mineflayer.runtime_admission import coordinate_mineflayer_message
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState

QUALIFICATION_PROVENANCE_SOURCE = "mineflayer-live-qualification"


class MineflayerQualificationError(RuntimeError):
    """Raised when one live qualification condition is not established."""


class MineflayerQualificationSession(Protocol):
    @property
    def started(self): ...

    async def receive(self): ...

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None: ...

    async def send_clear_controls(self, action_id: str) -> None: ...

    async def shutdown(self, *, timeout_s: float = 5.0) -> int: ...


@dataclass(frozen=True, slots=True)
class MineflayerQualificationReport:
    session_id: str
    spawn_position: MineflayerPosition
    moved_position: MineflayerPosition
    movement_distance: float
    spawn_health: float
    spawn_food: float
    forward_action_state: str
    stop_action_state: str
    skill_state: str
    intent_id: str
    observed_kinds: tuple[str, ...]
    qualified: bool


class _MonotonicEpochClock:
    def __init__(self) -> None:
        self._last = -1

    def now_ns(self) -> int:
        current = time.monotonic_ns()
        if current <= self._last:
            current = self._last + 1
        self._last = current
        return current


def _provenance(reference: str) -> Provenance:
    return Provenance(
        source=QUALIFICATION_PROVENANCE_SOURCE,
        reference=reference,
    )


def _horizontal_position_distance(
    a: MineflayerPosition,
    b: MineflayerPosition,
) -> float:
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.z - b.z) ** 2
    )


def _new_supervised_action(
    *,
    action_id: str,
    skill: SkillExecution,
    commitment: IntentCommitment,
    supervisor: ActionSupervisor,
    clock: _MonotonicEpochClock,
    timeout_s: float,
) -> None:
    proposal = ActionLifecycle.propose(
        action_id,
        skill_execution=skill,
        intent_commitment=commitment,
        at_ns=clock.now_ns(),
        provenance=_provenance(f"{action_id}:proposal"),
    )
    authorized = proposal.authorize(
        at_ns=clock.now_ns(),
        provenance=_provenance(f"{action_id}:authorization"),
        authority="mineflayer-live-qualification",
    )
    issue_at = clock.now_ns()
    supervisor.issue(
        authorized,
        at_ns=issue_at,
        deadline_ns=issue_at + int(timeout_s * 1_000_000_000),
        provenance=_provenance(f"{action_id}:issue"),
    )


async def _receive_with_timeout(
    session: MineflayerQualificationSession,
    *,
    timeout_s: float,
):
    try:
        return await asyncio.wait_for(session.receive(), timeout=timeout_s)
    except TimeoutError as exc:
        raise MineflayerQualificationError(
            "timed out waiting for Mineflayer qualification evidence"
        ) from exc


def _raise_on_terminal_adapter_message(message: object) -> None:
    if isinstance(message, MineflayerConnectionEnd):
        raise MineflayerQualificationError(
            f"Mineflayer connection ended during qualification: {message.reason}"
        )
    if isinstance(message, MineflayerAdapterErrorMessage):
        raise MineflayerQualificationError(
            f"Mineflayer adapter error during qualification: {message.message}"
        )


async def qualify_mineflayer_session(
    session: MineflayerQualificationSession,
    *,
    evidence_timeout_s: float = 10.0,
    action_timeout_s: float = 5.0,
    minimum_movement_distance: float = 0.05,
) -> MineflayerQualificationReport:
    """Qualify one already-started Mineflayer session through canonical owners."""

    if evidence_timeout_s <= 0 or action_timeout_s <= 0:
        raise MineflayerQualificationError("qualification timeouts must be positive")
    if minimum_movement_distance <= 0:
        raise MineflayerQualificationError(
            "minimum_movement_distance must be positive"
        )

    clock = _MonotonicEpochClock()
    observed_kinds: list[str] = []

    spawn: MineflayerObservation | None = None
    while spawn is None:
        message = await _receive_with_timeout(
            session,
            timeout_s=evidence_timeout_s,
        )
        _raise_on_terminal_adapter_message(message)
        if isinstance(message, MineflayerObservation):
            observed_kinds.append(message.kind)
            if message.kind == "spawn":
                spawn = message

    commitment = IntentCommitment()
    commitment.commit(
        "intent-live-qualification",
        objective="verify concrete Mineflayer causal execution",
        at_ns=clock.now_ns(),
        provenance=_provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-live-qualification",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=clock.now_ns(),
        provenance=_provenance("skill"),
    )
    supervisor = ActionSupervisor()

    forward_action_id = "action-live-forward"
    _new_supervised_action(
        action_id=forward_action_id,
        skill=skill,
        commitment=commitment,
        supervisor=supervisor,
        clock=clock,
        timeout_s=action_timeout_s,
    )
    await session.send_set_control(
        forward_action_id,
        control="forward",
        state=True,
    )

    forward_applied = False
    moved_position: MineflayerPosition | None = None
    while not forward_applied or moved_position is None:
        message = await _receive_with_timeout(
            session,
            timeout_s=evidence_timeout_s,
        )
        _raise_on_terminal_adapter_message(message)

        if isinstance(message, MineflayerObservation):
            observed_kinds.append(message.kind)
            if (
                forward_applied
                and message.kind == "move"
                and _horizontal_position_distance(
                    spawn.snapshot.position,
                    message.snapshot.position,
                )
                >= minimum_movement_distance
            ):
                moved_position = message.snapshot.position

        result = coordinate_mineflayer_message(
            message,
            supervisor,
            at_ns=clock.now_ns(),
        )
        if (
            isinstance(message, MineflayerEffectResult)
            and message.action_id == forward_action_id
        ):
            if message.result != "applied":
                raise MineflayerQualificationError(
                    "forward control was rejected by Mineflayer: "
                    f"{message.error}"
                )
            forward_applied = True
            if result is None or result.action_closure is None:
                raise MineflayerQualificationError(
                    "forward effect result did not close the supervised Action"
                )

    forward_lifecycle = supervisor.get(forward_action_id)
    if forward_lifecycle.state is not ActionState.OUTCOME:
        raise MineflayerQualificationError(
            "forward Action did not close as OUTCOME"
        )

    stop_action_id = "action-live-stop"
    _new_supervised_action(
        action_id=stop_action_id,
        skill=skill,
        commitment=commitment,
        supervisor=supervisor,
        clock=clock,
        timeout_s=action_timeout_s,
    )
    await session.send_clear_controls(stop_action_id)

    stop_applied = False
    while not stop_applied:
        message = await _receive_with_timeout(
            session,
            timeout_s=evidence_timeout_s,
        )
        _raise_on_terminal_adapter_message(message)
        if isinstance(message, MineflayerObservation):
            observed_kinds.append(message.kind)

        result = coordinate_mineflayer_message(
            message,
            supervisor,
            at_ns=clock.now_ns(),
        )
        if (
            isinstance(message, MineflayerEffectResult)
            and message.action_id == stop_action_id
        ):
            if message.result != "applied":
                raise MineflayerQualificationError(
                    "clear-controls effect was rejected by Mineflayer: "
                    f"{message.error}"
                )
            stop_applied = True
            if result is None or result.action_closure is None:
                raise MineflayerQualificationError(
                    "stop effect result did not close the supervised Action"
                )

    stop_lifecycle = supervisor.get(stop_action_id)
    if stop_lifecycle.state is not ActionState.OUTCOME:
        raise MineflayerQualificationError(
            "stop Action did not close as OUTCOME"
        )
    if skill.state is not SkillState.STARTED:
        raise MineflayerQualificationError(
            "primitive Action qualification mutated Skill terminal state"
        )
    if commitment.current_intent is None:
        raise MineflayerQualificationError(
            "primitive Action qualification released Current Intent"
        )

    assert moved_position is not None
    distance = _horizontal_position_distance(
        spawn.snapshot.position,
        moved_position,
    )
    return MineflayerQualificationReport(
        session_id=session.started.session_id,
        spawn_position=spawn.snapshot.position,
        moved_position=moved_position,
        movement_distance=distance,
        spawn_health=spawn.snapshot.health,
        spawn_food=spawn.snapshot.food,
        forward_action_state=forward_lifecycle.state.value,
        stop_action_state=stop_lifecycle.state.value,
        skill_state=skill.state.value,
        intent_id=commitment.current_intent.intent_id,
        observed_kinds=tuple(observed_kinds),
        qualified=True,
    )


async def run_live_qualification(
    config: MineflayerLaunchConfig,
    *,
    bridge_path: str | Path | None = None,
    node_executable: str = "node",
    startup_timeout_s: float = 10.0,
    evidence_timeout_s: float = 10.0,
    action_timeout_s: float = 5.0,
    minimum_movement_distance: float = 0.05,
) -> MineflayerQualificationReport:
    session = await MineflayerProcessSession.launch(
        config,
        bridge_path=bridge_path,
        node_executable=node_executable,
        startup_timeout_s=startup_timeout_s,
    )
    try:
        return await qualify_mineflayer_session(
            session,
            evidence_timeout_s=evidence_timeout_s,
            action_timeout_s=action_timeout_s,
            minimum_movement_distance=minimum_movement_distance,
        )
    finally:
        await session.shutdown()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the RelaySelf Mineflayer live qualification transaction."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=25565)
    parser.add_argument("--username", default="RelaySelf")
    parser.add_argument("--version")
    parser.add_argument("--node", default="node")
    parser.add_argument("--bridge")
    parser.add_argument("--startup-timeout-s", type=float, default=10.0)
    parser.add_argument("--evidence-timeout-s", type=float, default=10.0)
    parser.add_argument("--action-timeout-s", type=float, default=5.0)
    parser.add_argument("--minimum-movement-distance", type=float, default=0.05)
    return parser


async def _async_main() -> int:
    args = _parser().parse_args()
    report = await run_live_qualification(
        MineflayerLaunchConfig(
            host=args.host,
            port=args.port,
            username=args.username,
            version=args.version,
        ),
        bridge_path=args.bridge,
        node_executable=args.node,
        startup_timeout_s=args.startup_timeout_s,
        evidence_timeout_s=args.evidence_timeout_s,
        action_timeout_s=args.action_timeout_s,
        minimum_movement_distance=args.minimum_movement_distance,
    )
    print(
        json.dumps(
            asdict(report),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
