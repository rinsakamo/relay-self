from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerAdapterStarted,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerPaperL0Shadow,
    MineflayerPaperSnapshot,
)
from adapters.mineflayer.s49_l0_interrupt_dev import (
    L0Interruption,
    classify_s49_l0_interrupt,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.provenance import Provenance

MOVE_BACKWARD_ACTION_REF = "MOVE_BACKWARD"
MOVE_BACKWARD_EFFECT = "set_control"
MOVE_BACKWARD_CONTROL = "back"
MOVE_BACKWARD_DURATION_S = 0.20
MOVE_BACKWARD_MINIMUM_DISTANCE = 0.05
# DEV 20-TPS watchdog: three nominal tick intervals, never a freshness proof.
L0_DEV_MAX_SILENCE_S = 0.15


class MineflayerExecutionError(ValueError):
    """Base error for S15 issued-action Mineflayer execution."""


class InvalidMineflayerExecutionData(MineflayerExecutionError):
    """Raised when S15 authority/binding data is malformed or mismatched."""


class WorldConsequenceStatus(str, Enum):
    EXECUTED = "executed"
    FAILED = "failed"
    UNDETERMINED = "undetermined"


class MineflayerExecutionSession(Protocol):
    @property
    def started(self) -> MineflayerAdapterStarted: ...

    async def receive(self): ...

    async def send_observe(self) -> None: ...

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None: ...

    async def send_clear_controls(self, action_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class MineflayerCommand:
    """Closed, bounded adapter command derived from exact issued authority."""

    action_id: str
    binding_id: str
    action_ref: str
    effect: str
    control: str
    state: bool
    duration_s: float
    cleanup_action_id: str

    def __post_init__(self) -> None:
        _require_identifier("action_id", self.action_id)
        _require_identifier("binding_id", self.binding_id)
        _require_identifier("action_ref", self.action_ref)
        _require_identifier("effect", self.effect)
        _require_identifier("control", self.control)
        _require_identifier("cleanup_action_id", self.cleanup_action_id)
        if self.action_ref != MOVE_BACKWARD_ACTION_REF:
            raise InvalidMineflayerExecutionData(
                f"unsupported S15 action_ref: {self.action_ref}"
            )
        if self.effect != MOVE_BACKWARD_EFFECT:
            raise InvalidMineflayerExecutionData(
                "MOVE_BACKWARD command effect must be set_control"
            )
        if self.control != MOVE_BACKWARD_CONTROL:
            raise InvalidMineflayerExecutionData(
                "MOVE_BACKWARD command control must be back"
            )
        if self.state is not True:
            raise InvalidMineflayerExecutionData(
                "MOVE_BACKWARD command must enable backward control"
            )
        _require_positive_number("duration_s", self.duration_s)
        if self.cleanup_action_id == self.action_id:
            raise InvalidMineflayerExecutionData(
                "cleanup action identity must be distinct from issued action"
            )


@dataclass(frozen=True, slots=True)
class WorldConsequence:
    """Structured environment result; never implicit cognition or learning."""

    action_id: str
    binding_id: str
    action_ref: str
    status: WorldConsequenceStatus
    session_id: str
    before_observation: MineflayerObservation | None
    dispatch_receipt: MineflayerEffectResult | None
    cleanup_receipt: MineflayerEffectResult | None
    after_observation: MineflayerObservation | None
    movement_distance: float | None
    cleanup_attempted: bool
    error: str | None
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("consequence action_id", self.action_id)
        _require_identifier("consequence binding_id", self.binding_id)
        _require_identifier("consequence action_ref", self.action_ref)
        if not isinstance(self.status, WorldConsequenceStatus):
            raise InvalidMineflayerExecutionData(
                "consequence status must be WorldConsequenceStatus"
            )
        _require_identifier("consequence session_id", self.session_id)
        if self.before_observation is not None and not isinstance(
            self.before_observation,
            MineflayerObservation,
        ):
            raise InvalidMineflayerExecutionData(
                "before_observation must be MineflayerObservation or None"
            )
        if self.dispatch_receipt is not None and not isinstance(
            self.dispatch_receipt,
            MineflayerEffectResult,
        ):
            raise InvalidMineflayerExecutionData(
                "dispatch_receipt must be MineflayerEffectResult or None"
            )
        if self.cleanup_receipt is not None and not isinstance(
            self.cleanup_receipt,
            MineflayerEffectResult,
        ):
            raise InvalidMineflayerExecutionData(
                "cleanup_receipt must be MineflayerEffectResult or None"
            )
        if self.after_observation is not None and not isinstance(
            self.after_observation,
            MineflayerObservation,
        ):
            raise InvalidMineflayerExecutionData(
                "after_observation must be MineflayerObservation or None"
            )
        if self.movement_distance is not None:
            _require_non_negative_number(
                "movement_distance",
                self.movement_distance,
            )
        if not isinstance(self.cleanup_attempted, bool):
            raise InvalidMineflayerExecutionData(
                "cleanup_attempted must be bool"
            )
        if self.error is not None:
            _require_text("consequence error", self.error)
        _require_provenance("consequence provenance", self.provenance)

        if self.status is WorldConsequenceStatus.EXECUTED:
            if self.error is not None:
                raise InvalidMineflayerExecutionData(
                    "EXECUTED consequence cannot carry an error"
                )
            _require_complete_execution_evidence(self)
            if (
                self.movement_distance is None
                or self.movement_distance < MOVE_BACKWARD_MINIMUM_DISTANCE
            ):
                raise InvalidMineflayerExecutionData(
                    "EXECUTED consequence requires observed movement"
                )
        elif self.status is WorldConsequenceStatus.UNDETERMINED:
            if self.error is not None:
                raise InvalidMineflayerExecutionData(
                    "UNDETERMINED consequence cannot carry an error"
                )
            _require_complete_execution_evidence(self)
        else:
            if self.error is None:
                raise InvalidMineflayerExecutionData(
                    "FAILED consequence requires an explicit error"
                )


def build_mineflayer_command(
    issued_action: ActionLifecycle,
    binding_result: ExecutionBindingResult,
) -> MineflayerCommand:
    """Purely join exact Action authority with S14 physical-action binding."""

    if not isinstance(issued_action, ActionLifecycle):
        raise InvalidMineflayerExecutionData(
            "issued_action must be ActionLifecycle"
        )
    if not isinstance(binding_result, ExecutionBindingResult):
        raise InvalidMineflayerExecutionData(
            "binding_result must be ExecutionBindingResult"
        )
    if issued_action.state is not ActionState.ISSUED:
        raise InvalidMineflayerExecutionData(
            "Mineflayer execution requires ISSUED ActionLifecycle"
        )
    if not issued_action.is_current_snapshot:
        raise InvalidMineflayerExecutionData(
            "Mineflayer execution requires current ISSUED Action snapshot"
        )
    if issued_action.events[-1].deadline_ns is None:
        raise InvalidMineflayerExecutionData(
            "ISSUED Action must carry its existing deadline"
        )
    if issued_action.action_id != binding_result.action_id:
        raise InvalidMineflayerExecutionData(
            "issued action_id does not match ExecutionBindingResult"
        )
    if issued_action.skill_execution_id != binding_result.skill_execution_id:
        raise InvalidMineflayerExecutionData(
            "issued skill_execution_id does not match ExecutionBindingResult"
        )
    if issued_action.intent_id != binding_result.intent_id:
        raise InvalidMineflayerExecutionData(
            "issued intent_id does not match ExecutionBindingResult"
        )
    if binding_result.action_ref != MOVE_BACKWARD_ACTION_REF:
        raise InvalidMineflayerExecutionData(
            f"unsupported S15 action_ref: {binding_result.action_ref}"
        )

    return MineflayerCommand(
        action_id=issued_action.action_id,
        binding_id=binding_result.binding_id,
        action_ref=binding_result.action_ref,
        effect=MOVE_BACKWARD_EFFECT,
        control=MOVE_BACKWARD_CONTROL,
        state=True,
        duration_s=MOVE_BACKWARD_DURATION_S,
        cleanup_action_id=f"{issued_action.action_id}-s15-clear",
    )


async def execute_mineflayer_command(
    adapter: MineflayerExecutionSession,
    command: MineflayerCommand,
    *,
    timeout_s: float = 2.0,
    provenance: Provenance,
    l0_interrupt_dev: bool = False,
) -> WorldConsequence:
    """Execute one bounded MOVE_BACKWARD command with structured observation.

    The function owns no Action lifecycle state. It sends one explicit
    backward-control command, clears controls exactly once on the normal path,
    and returns structured adapter evidence. It does not retry or reconnect.
    """

    if not isinstance(command, MineflayerCommand):
        raise InvalidMineflayerExecutionData(
            "command must be MineflayerCommand"
        )
    _require_positive_number("timeout_s", timeout_s)
    if type(l0_interrupt_dev) is not bool:
        raise InvalidMineflayerExecutionData("L0 interrupt DEV opt-in must be bool")
    _require_provenance("execution provenance", provenance)
    started = _require_adapter(adapter)
    session_id = started.session_id

    before: MineflayerObservation | None = None
    dispatch: MineflayerEffectResult | None = None
    cleanup: MineflayerEffectResult | None = None
    after: MineflayerObservation | None = None
    cleanup_attempted = False
    movement_command_attempted = False
    movement_distance: float | None = None

    try:
        await adapter.send_observe()
        before = await _receive_until(
            adapter,
            timeout_s=timeout_s,
            predicate=lambda message: (
                isinstance(message, MineflayerObservation)
                and message.kind == "probe"
            ),
            l0_interrupt_dev=l0_interrupt_dev,
            expected_session_id=session_id,
        )

        movement_command_attempted = True
        await adapter.send_set_control(
            command.action_id,
            control=command.control,
            state=command.state,
        )
        dispatch = await _receive_until(
            adapter,
            timeout_s=timeout_s,
            predicate=lambda message: (
                isinstance(message, MineflayerEffectResult)
                and message.action_id == command.action_id
                and message.effect == command.effect
            ),
            l0_interrupt_dev=l0_interrupt_dev,
            expected_session_id=session_id,
        )
        if dispatch.result != "applied":
            raise MineflayerExecutionError(
                "Mineflayer rejected MOVE_BACKWARD dispatch: "
                f"{dispatch.error}"
            )

        if l0_interrupt_dev:
            await _watch_l0_during_motor(
                adapter, duration_s=command.duration_s, session_id=session_id,
            )
        else:
            await asyncio.sleep(command.duration_s)

        cleanup_attempted = True
        await adapter.send_clear_controls(command.cleanup_action_id)
        cleanup = await _receive_until(
            adapter,
            timeout_s=timeout_s,
            predicate=lambda message: (
                isinstance(message, MineflayerEffectResult)
                and message.action_id == command.cleanup_action_id
                and message.effect == "clear_controls"
            ),
            l0_interrupt_dev=False,
        )
        if cleanup.result != "applied":
            raise MineflayerExecutionError(
                "Mineflayer rejected movement cleanup: "
                f"{cleanup.error}"
            )

        await adapter.send_observe()
        after = await _receive_until(
            adapter,
            timeout_s=timeout_s,
            predicate=lambda message: (
                isinstance(message, MineflayerObservation)
                and message.kind == "probe"
            ),
            l0_interrupt_dev=False,
        )
        movement_distance = _horizontal_distance(
            before.snapshot.position.x,
            before.snapshot.position.z,
            after.snapshot.position.x,
            after.snapshot.position.z,
        )

        status = (
            WorldConsequenceStatus.EXECUTED
            if movement_distance >= MOVE_BACKWARD_MINIMUM_DISTANCE
            else WorldConsequenceStatus.UNDETERMINED
        )
        return WorldConsequence(
            action_id=command.action_id,
            binding_id=command.binding_id,
            action_ref=command.action_ref,
            status=status,
            session_id=session_id,
            before_observation=before,
            dispatch_receipt=dispatch,
            cleanup_receipt=cleanup,
            after_observation=after,
            movement_distance=movement_distance,
            cleanup_attempted=True,
            error=None,
            provenance=provenance,
        )
    except Exception as exc:
        # The command ID is consumed at first dispatch. Never retry a clear
        # that might have reached the client but whose ACK was lost.
        if movement_command_attempted and cleanup is None and not cleanup_attempted:
            cleanup_attempted = True
            try:
                await adapter.send_clear_controls(command.cleanup_action_id)
                if l0_interrupt_dev:
                    # A client-side clear ACK is not a Paper stop witness.
                    # Failure to receive ACK leaves action outcome FAILED.
                    cleanup = await _receive_until(
                        adapter, timeout_s=timeout_s,
                        predicate=lambda message: (
                            isinstance(message, MineflayerEffectResult)
                            and message.action_id == command.cleanup_action_id
                            and message.effect == "clear_controls"
                        ),
                    )
            except Exception:
                pass
        return WorldConsequence(
            action_id=command.action_id,
            binding_id=command.binding_id,
            action_ref=command.action_ref,
            status=WorldConsequenceStatus.FAILED,
            session_id=session_id,
            before_observation=before,
            dispatch_receipt=dispatch,
            cleanup_receipt=cleanup,
            after_observation=after,
            movement_distance=movement_distance,
            cleanup_attempted=cleanup_attempted,
            error=f"{type(exc).__name__}: {exc}",
            provenance=provenance,
        )


async def _watch_l0_during_motor(
    adapter: MineflayerExecutionSession, *,
    duration_s: float,
    session_id: str,
) -> None:
    """DEV motor wait consuming the same native receiver, no second writer.

    A delivered cache-shadow can request interruption, never permit an Action.
    One shadow is required during this bounded interval; missing evidence
    fails closed rather than pretending the World was monitored.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + duration_s
    checked = 0
    last_shadow = None
    silence_deadline = loop.time() + L0_DEV_MAX_SILENCE_S
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        silence_remaining = silence_deadline - loop.time()
        if silence_remaining <= 0:
            raise MineflayerExecutionError("L0 DEV shadow stream stalled during motor")
        try:
            message = await asyncio.wait_for(
                adapter.receive(), timeout=min(remaining, silence_remaining),
            )
        except TimeoutError:
            if loop.time() >= silence_deadline:
                raise MineflayerExecutionError("L0 DEV shadow stream stalled during motor")
            break
        if _check_l0_interrupt(message, session_id=session_id):
            if last_shadow is not None and (
                message.paper_sample_index != last_shadow.paper_sample_index + 1
                or int(message.paper_server_tick) != int(last_shadow.paper_server_tick) + 1
                or message.paper_world != last_shadow.paper_world
                or message.paper_player != last_shadow.paper_player
            ):
                raise MineflayerExecutionError("L0 DEV shadow tick discontinuity")
            last_shadow = message
            silence_deadline = loop.time() + L0_DEV_MAX_SILENCE_S
            checked += 1
    if checked == 0:
        raise MineflayerExecutionError(
            "L0 DEV opt-in observed no shadow during motor interval"
        )


def _check_l0_interrupt(message: object, *, session_id: str) -> bool:
    """Typed cache-only L0 may abort an issued Action, never create one."""
    if isinstance(message, MineflayerConnectionEnd):
        raise MineflayerExecutionError("L0 DEV client connection ended")
    if isinstance(message, (MineflayerAdapterErrorMessage, MineflayerCommandError)):
        raise MineflayerExecutionError("L0 DEV receiver signalled failure")
    if isinstance(message, MineflayerPaperSnapshot):
        if message.session_id != session_id:
            raise MineflayerExecutionError("T1f foreign session")
        if (message.data["status"] != "ADMITTED"
                or message.data["assessment"] != "NO_KNOWN_URGENT_SIGNAL"):
            raise MineflayerExecutionError(
                f"T1f abort: {message.data['status']} / {message.data['assessment']}")
        return True
    if not isinstance(message, MineflayerPaperL0Shadow):
        return False
    if message.session_id != session_id:
        raise MineflayerExecutionError("L0 DEV shadow from foreign session")
    result = classify_s49_l0_interrupt(
        message.assessment,
        l0_shadow_evaluated=message.l0_shadow_evaluated,
        l0_fresh_world_tick_attested=message.l0_fresh_world_tick_attested,
        authorized_action_issued=message.authorized_action_issued,
        tps_admission_granted=message.tps_admission_granted,
    )
    if result is not L0Interruption.CONTINUE_UNVERIFIED:
        raise MineflayerExecutionError(f"L0 DEV abort request: {result.value}")
    return True


async def _receive_until(
    adapter: MineflayerExecutionSession,
    *,
    timeout_s: float,
    predicate,
    l0_interrupt_dev: bool = False,
    expected_session_id: str | None = None,
):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError(
                "timed out waiting for required Mineflayer execution evidence"
            )
        message = await asyncio.wait_for(adapter.receive(), timeout=remaining)
        if isinstance(message, MineflayerConnectionEnd):
            raise MineflayerExecutionError(
                f"Mineflayer connection ended: {message.reason}"
            )
        if isinstance(message, MineflayerAdapterErrorMessage):
            raise MineflayerExecutionError(
                f"Mineflayer adapter error: {message.message}"
            )
        if isinstance(message, MineflayerCommandError):
            raise MineflayerExecutionError(
                f"Mineflayer command error: {message.message}"
            )
        if l0_interrupt_dev:
            assert expected_session_id is not None
            _check_l0_interrupt(message, session_id=expected_session_id)
        if predicate(message):
            return message


def _require_adapter(adapter: object) -> MineflayerAdapterStarted:
    for name in (
        "receive",
        "send_observe",
        "send_set_control",
        "send_clear_controls",
    ):
        if not callable(getattr(adapter, name, None)):
            raise InvalidMineflayerExecutionData(
                "adapter must provide the existing Mineflayer session interface"
            )
    try:
        started = adapter.started
    except Exception as exc:
        raise InvalidMineflayerExecutionData(
            "adapter must expose a started Mineflayer session"
        ) from exc
    if not isinstance(started, MineflayerAdapterStarted):
        raise InvalidMineflayerExecutionData(
            "adapter.started must be MineflayerAdapterStarted"
        )
    return started


def _require_complete_execution_evidence(value: WorldConsequence) -> None:
    if (
        value.before_observation is None
        or value.dispatch_receipt is None
        or value.cleanup_receipt is None
        or value.after_observation is None
        or value.movement_distance is None
        or not value.cleanup_attempted
    ):
        raise InvalidMineflayerExecutionData(
            f"{value.status.value} consequence requires complete structured evidence"
        )
    if value.dispatch_receipt.result != "applied":
        raise InvalidMineflayerExecutionData(
            f"{value.status.value} consequence requires applied dispatch"
        )
    if value.cleanup_receipt.result != "applied":
        raise InvalidMineflayerExecutionData(
            f"{value.status.value} consequence requires applied cleanup"
        )


def _horizontal_distance(
    before_x: float,
    before_z: float,
    after_x: float,
    after_z: float,
) -> float:
    return math.sqrt(
        (after_x - before_x) ** 2
        + (after_z - before_z) ** 2
    )


def _require_identifier(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidMineflayerExecutionData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidMineflayerExecutionData(
            f"{name} must be a non-empty string"
        )


def _require_positive_number(name: str, value: object) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidMineflayerExecutionData(
            f"{name} must be a positive finite number"
        )


def _require_non_negative_number(name: str, value: object) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise InvalidMineflayerExecutionData(
            f"{name} must be a non-negative finite number"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidMineflayerExecutionData(f"{name} must be Provenance")
