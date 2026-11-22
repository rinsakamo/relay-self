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
    try:
        return await asyncio.wait_for(issue_original(), timeout=watchdog_s)
    except BaseException:
        # wait_for cancels the run/lease; abort MUST operate without the lease.
        await abort_original_place_after_start(
            bridge=bridge, self_id=self_id, stop_action_id=stop_action_id,
        )
        raise
