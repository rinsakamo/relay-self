"""Q4 DEV only: bounded place watchdog and host fail-stop receipt.

This module does not mint Skill/Intent, physical Action, journal commits, World
source authenticity or native ACK. Host must use the ORIGINAL owned bridge.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar

Q4_MAX_FORWARD_MS = 800
Q4_MAX_DISPLACEMENT_M = 1.0
Q4_MAX_HOST_WATCHDOG_S = 2.0

_T = TypeVar("_T")


class Q4PlaceAbortHold(RuntimeError):
    """The original process was not proved disconnected after a dirty cut."""


@dataclass(slots=True)
class Q4DevOperatorPermit:
    """One-use LOCAL DEV intent, not an authenticated operator identity."""

    self_id: str
    native_session_id: str
    _consumed: bool = field(default=False, init=False, repr=False)

    def consume(self, *, self_id: str, native_session_id: str) -> None:
        if (
            self._consumed or type(self.self_id) is not str
            or type(self.native_session_id) is not str
            or not self.self_id or not self.native_session_id
            or self.self_id != self_id
            or self.native_session_id != native_session_id
        ):
            raise Q4PlaceAbortHold("missing, reused or foreign Q4 DEV operator permit")
        self._consumed = True


@dataclass(frozen=True, slots=True)
class Q4PlaceAbortReceipt:
    self_id: str
    native_session_id: str
    stop_action_id: str
    stop_attempted: bool
    process_terminated: bool
    stop_ack_attested: bool = False
    wal_resolved: bool = False
    world_settled_attested: bool = False


async def abort_original_place_after_start(
    *, bridge: object, self_id: str, stop_action_id: str,
    stop_timeout_s: float = 0.25, terminate_timeout_s: float = 0.5,
) -> Q4PlaceAbortReceipt:
    """Revoke the original issuer and kill the owned Native if STOP is uncertain.

    Works even after original PLACE lease's finally cleared its binding.
    This is a host-owned isolated bot termination, NOT a clean STOP proof.
    It never writes an unresolved WAL, creates a second issuer or retries START.
    """
    if (
        type(self_id) is not str or not self_id
        or type(stop_action_id) is not str or not stop_action_id
        or type(stop_timeout_s) not in (int, float)
        or not 0 < stop_timeout_s <= 0.5
        or type(terminate_timeout_s) not in (int, float)
        or not 0 < terminate_timeout_s <= 1.0
    ):
        raise Q4PlaceAbortHold("invalid original place abort scope or time bound")
    sessions = bridge.sessions
    session = sessions.get(self_id)
    if session is None or bridge.physical is None:
        raise Q4PlaceAbortHold("no original owned Native process to abort")
    native_id = session.started.session_id
    if bridge.physical.current_native_sessions.get(self_id) != native_id:
        raise Q4PlaceAbortHold("old/foreign physical Native session cannot be aborted")

    # Fence admission synchronously BEFORE any await; original own bridge
    # quarantine also fences cognitive/GPU and lifecycle where available.
    try:
        bridge.quarantine(self_id)
    except Exception:
        # If gate has been closed/poisoned, never re-open it. A process might
        # still move: try to terminate this already verified owned session.
        bridge.physical.hold_for_operator()

    stop_attempted = False
    try:
        if session.process_returncode is None:
            stop_attempted = True
            try:
                await asyncio.wait_for(
                    session.send_clear_controls(stop_action_id),
                    timeout=stop_timeout_s,
                )
            except (Exception, asyncio.CancelledError):
                pass
        # A StreamWriter.drain is not an effect ACK. Terminate even when the
        # STOP bytes were buffered; no claim that the body was settled.
    finally:
        # Cancellation of the original caller does not leave the old issuer
        # live; the original session owns this native-process kill path.
        try:
            if hasattr(session, "force_terminate_owned"):
                await session.force_terminate_owned(timeout_s=terminate_timeout_s)
            else:
                await asyncio.wait_for(
                    session.terminate(), timeout=terminate_timeout_s,
                )
        except (Exception, asyncio.CancelledError) as exc:
            bridge.physical.hold_for_operator()
            raise Q4PlaceAbortHold("owned Native termination not confirmed") from exc
    if session.process_returncode is None:
        bridge.physical.hold_for_operator()
        raise Q4PlaceAbortHold("Native process remains unconfirmed after abort")
    return Q4PlaceAbortReceipt(
        self_id, native_id, stop_action_id, stop_attempted, True,
    )


async def run_q4_dev_place_with_watchdog(
    *, bridge: object, self_id: str, stop_action_id: str,
    issue_original: Callable[[], Awaitable[_T]],
    operator_permit: Q4DevOperatorPermit,
    watchdog_s: float = Q4_MAX_HOST_WATCHDOG_S,
) -> _T:
    """DEV orchestrator wrapper around the EXISTING original Skill issuer.

    Timeout, task cancellation or Native error after an attempted run always
    revokes the issuer and disconnects the old bot via a host-owned abort.
    Passing this wrapper alone can never authorize a real physical issue.
    """
    if (
        not isinstance(operator_permit, Q4DevOperatorPermit)
        or type(watchdog_s) not in (int, float)
        or not 0 < watchdog_s <= Q4_MAX_HOST_WATCHDOG_S
        or not callable(issue_original)
    ):
        raise Q4PlaceAbortHold("explicit one-time DEV opt-in and bounded run required")
    session = bridge.sessions.get(self_id)
    if (
        session is None
        or getattr(session, "bounded_place_dev_mode", False) is not True
        or sum(
            x.process_returncode is None for x in bridge.sessions.values()
        ) != 1
    ):
        raise Q4PlaceAbortHold(
            "isolated single Self with explicitly bounded Native launch required"
        )
    operator_permit.consume(
        self_id=self_id, native_session_id=session.started.session_id,
    )
    work = asyncio.create_task(issue_original())
    try:
        # wait_for() may wait arbitrarily long for a task that suppresses
        # cancellation, defeating a host motor watchdog. asyncio.wait() gives
        # the host its own deadline, independently of Skill cleanup.
        done, _ = await asyncio.wait({work}, timeout=watchdog_s)
        if work not in done:
            raise TimeoutError("Q4 original PLACE host watchdog elapsed")
        return await work
    except BaseException:
        if not work.done():
            work.cancel()
        # The revoked physical gate and owned bot termination do NOT depend
        # on the still-running coroutine reaching its old lease finally.
        await abort_original_place_after_start(
            bridge=bridge, self_id=self_id, stop_action_id=stop_action_id,
        )
        raise


class Q4DevMotorBoundary:
    """In-process original executor milestone, never a motor or ACK grant.

    Only the wrapper-owned coroutine can mark START and exact Native ACKs.
    A typed ACK is still NOT an independently authenticated original source.
    """

    def __init__(self, *, self_id: str, session_id: str, action_id: str) -> None:
        if any(type(x) is not str or not x for x in (
            self_id, session_id, action_id,
        )):
            raise Q4PlaceAbortHold("Q4 motor milestone identity required")
        self.self_id = self_id
        self.session_id = session_id
        self.action_id = action_id
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()
        self.started_at: float | None = None
        self.stopped_at: float | None = None
        self._runner: asyncio.Task | None = None
        self._start_seq: int | None = None

    def bind_runner(self, runner: asyncio.Task) -> None:
        if self._runner is not None or not isinstance(runner, asyncio.Task):
            raise Q4PlaceAbortHold("Q4 original runner already bound")
        self._runner = runner

    def _require_runner(self) -> None:
        if asyncio.current_task() is not self._runner:
            raise Q4PlaceAbortHold("Q4 motor boundary invoked outside original runner")

    def before_native_start(self, *, action_id: str, session_id: str) -> None:
        """Arm BEFORE awaiting original final native forward command."""
        self._require_runner()
        if (
            action_id != self.action_id + "-start"
            or session_id != self.session_id
            or self.started.is_set() or self.stopped.is_set()
        ):
            raise Q4PlaceAbortHold("Q4 START source/replay invalid")
        self.started_at = asyncio.get_running_loop().time()
        self.started.set()

    def accept_start_ack(self, ack: object) -> None:
        self._require_runner()
        if (
            not self.started.is_set() or self.stopped.is_set()
            or self._start_seq is not None
            or not self._matches_ack(
                ack, self.action_id + "-start", "set_control",
            )
        ):
            raise Q4PlaceAbortHold("Q4 original START ACK missing or invalid")
        self._start_seq = ack.seq

    def accept_stop_ack(self, ack: object) -> None:
        self._require_runner()
        if (
            self._start_seq is None or self.stopped.is_set()
            or not self._matches_ack(
                ack, self.action_id + "-stop", "clear_controls",
            )
            or ack.seq <= self._start_seq
        ):
            raise Q4PlaceAbortHold("Q4 original STOP ACK missing or invalid")
        self.stopped_at = asyncio.get_running_loop().time()
        self.stopped.set()

    def _matches_ack(self, ack: object, action_id: str, effect: str) -> bool:
        # Verify typed Native callback shape, but do not call it Paper proof.
        from adapters.mineflayer.python_protocol import MineflayerEffectResult

        return (
            isinstance(ack, MineflayerEffectResult)
            and ack.session_id == self.session_id
            and ack.action_id == action_id
            and ack.effect == effect
            and ack.result == "applied"
            and ack.error is None
        )


async def run_q4_dev_place_with_motor_deadline(
    *,
    bridge: object,
    self_id: str,
    action_id: str,
    issue_original: Callable[[Q4DevMotorBoundary], Awaitable[_T]],
    operator_permit: Q4DevOperatorPermit,
    pre_start_s: float = Q4_MAX_HOST_WATCHDOG_S,
    motor_s: float = Q4_MAX_HOST_WATCHDOG_S,
    settlement_s: float = 30.0,
) -> _T:
    """Separate START→STOP ACK host deadline from 8+8 tick settling.

    The caller MUST use the ORIGINAL PLACE issuer and pass the same boundary
    into its shared Stage27 motor executor. A fake caller callback cannot
    authenticate source, and this API grants no physical action on its own.
    A missing/failing STOP, timeout, cancellation or settlement failure
    quarantines the original Self and force-terminates its owned Native.
    """
    def valid(value: object, cap: float) -> bool:
        return type(value) in (int, float) and 0 < value <= cap

    if (
        not isinstance(operator_permit, Q4DevOperatorPermit)
        or type(self_id) is not str or not self_id
        or type(action_id) is not str or not action_id
        or not callable(issue_original)
        or not valid(pre_start_s, Q4_MAX_HOST_WATCHDOG_S)
        or not valid(motor_s, Q4_MAX_HOST_WATCHDOG_S)
        or not valid(settlement_s, 120.0)
    ):
        raise Q4PlaceAbortHold("Q4 phased host requires bounded original opt-in")
    session = bridge.sessions.get(self_id)
    if (
        session is None
        or getattr(session, "bounded_place_dev_mode", False) is not True
        or sum(
            x.process_returncode is None for x in bridge.sessions.values()
        ) != 1
        or bridge.physical.current_native_sessions.get(self_id)
        != session.started.session_id
    ):
        raise Q4PlaceAbortHold("Q4 phased host requires one bounded owned Native")
    operator_permit.consume(
        self_id=self_id, native_session_id=session.started.session_id,
    )
    boundary = Q4DevMotorBoundary(
        self_id=self_id, session_id=session.started.session_id,
        action_id=action_id,
    )
    work = asyncio.create_task(issue_original(boundary))
    boundary.bind_runner(work)
    signals: list[asyncio.Task] = []
    try:
        start_signal = asyncio.create_task(boundary.started.wait())
        signals.append(start_signal)
        done, _ = await asyncio.wait(
            {work, start_signal},
            timeout=pre_start_s,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if work in done:
            # Propagate the original failure, if any. Completing successfully
            # before its true START is NEVER a qualified physical result.
            await work
            raise Q4PlaceAbortHold("original PLACE returned without START")
        if start_signal not in done or boundary.started_at is None:
            raise TimeoutError("Q4 pre-START host watchdog elapsed")

        stop_signal = asyncio.create_task(boundary.stopped.wait())
        signals.append(stop_signal)
        deadline = boundary.started_at + motor_s
        done, _ = await asyncio.wait(
            {work, stop_signal},
            timeout=max(0.0, deadline - asyncio.get_running_loop().time()),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if work in done and stop_signal not in done:
            await work
            raise Q4PlaceAbortHold("original PLACE returned before STOP ACK")
        if (
            stop_signal not in done or boundary.stopped_at is None
            or boundary.stopped_at > deadline
        ):
            raise TimeoutError("Q4 START-to-STOP host motor watchdog elapsed")

        # Post-STOP 8+8 tick settling is allowed independently of motor_s.
        # A terminal WAL is still required by the original issuer; the host
        # cannot infer settled WorldBody merely from this timer.
        done, _ = await asyncio.wait({work}, timeout=settlement_s)
        if work not in done:
            raise TimeoutError("Q4 post-STOP settlement watchdog elapsed")
        return await work
    except BaseException:
        if not work.done():
            work.cancel()
        # Do not await a possibly cancellation-resistant original issuer.
        # No physical issue remains authorized after quarantine.
        await abort_original_place_after_start(
            bridge=bridge, self_id=self_id,
            stop_action_id=action_id + "-stop",
        )
        raise
    finally:
        for signal in signals:
            if not signal.done():
                signal.cancel()
