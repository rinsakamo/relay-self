"""Offline DEV-only optional S49 live_probe callback composition.

This object does not install an S49 hook. Its sole input is an already-received
MineflayerObservation passed by the original S49 owner; no native I/O or Action.
The timer measures only optional Python callback work AFTER Present projection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_product_passive_views import (
    DEV_SELF_ID,
    MAX_PROBES,
    PassiveSelfViews,
)
from experiments.self_body_host_clock_passive_dev import PassiveHostCallbackTimer
from relay_self.self_body import SelfBodyView, compose_self_body_view


class S49PassiveClockJoinRejected(ValueError):
    """Producer-local source join failed; never a physical timing verdict."""


@dataclass(frozen=True, slots=True)
class PassiveProbeFailure:
    stage: str
    error_type: str
    session_id: str | None
    native_seq: int | None
    cancelled_or_interrupted: bool


async def _default_read_only(view: SelfBodyView) -> None:
    """Optional callback work; no L0/Action or native reader available."""
    view.observed("health")
    view.observed("food")


class S49PassiveHostClockDEV:
    """Advisory composition, not a real-world runner or an Action authority.

    Ordinary observer/clock exceptions are recorded and cannot veto S49's
    original L0. BaseException cancellation/system interruption is recorded,
    aborts its timing ticket when present, and propagates to original cleanup.
    """

    def __init__(
        self, *,
        timer: PassiveHostCallbackTimer | None = None,
        observer: Callable[[SelfBodyView], Awaitable[None]] | None = None,
        views: PassiveSelfViews | None = None,
    ) -> None:
        if timer is not None and type(timer) is not PassiveHostCallbackTimer:
            raise S49PassiveClockJoinRejected("original bounded clock required")
        if views is not None and type(views) is not PassiveSelfViews:
            raise S49PassiveClockJoinRejected("original passive views required")
        if observer is not None and not callable(observer):
            raise S49PassiveClockJoinRejected("passive observer must be callable")
        self.timer = timer if timer is not None else PassiveHostCallbackTimer(
            self_id=DEV_SELF_ID, capacity=MAX_PROBES,
        )
        if self.timer.self_id != DEV_SELF_ID:
            raise S49PassiveClockJoinRejected("timer bound to different Self")
        self.views = views if views is not None else PassiveSelfViews()
        self._observer = observer if observer is not None else _default_read_only
        self._failures: list[PassiveProbeFailure] = []
        self._overflow = 0

    def _failure(
        self, stage: str, exc: BaseException, reading: object,
    ) -> None:
        sid = getattr(reading, "session_id", None)
        seq = getattr(reading, "seq", None)
        row = PassiveProbeFailure(
            stage=stage,
            error_type=type(exc).__name__,
            session_id=sid if type(sid) is str else None,
            native_seq=seq if type(seq) is int else None,
            cancelled_or_interrupted=not isinstance(exc, Exception),
        )
        if len(self._failures) < MAX_PROBES + 1:
            self._failures.append(row)
        else:
            self._overflow += 1

    @staticmethod
    def _view(reading: MineflayerObservation, row: dict) -> SelfBodyView:
        if type(reading) is not MineflayerObservation or reading.kind != "probe":
            raise S49PassiveClockJoinRejected("exact received native probe required")
        present = project_mineflayer_present(reading)
        observation = project_body_present(present)
        view = compose_self_body_view(
            self_id=DEV_SELF_ID,
            session_id=reading.session_id,
            epoch_id=f"native-probe-{reading.seq}",
            observation=observation,
        )
        if (
            row.get("session_id") != reading.session_id
            or row.get("native_seq") != reading.seq
            or row.get("request_id") != reading.request_id
            or row.get("body_source_ref") != observation.source_ref
            or row.get("world_source_ref")
            != f"present:{reading.session_id}:{reading.seq}:{reading.request_id}"
            or row.get("body_world_exact_source_join") is not True
            or row.get("action_issued") is not False
            or row.get("action_authorized") is not False
        ):
            raise S49PassiveClockJoinRejected("existing Body/World source mismatch")
        return view

    async def observe(self, reading: MineflayerObservation) -> None:
        """S49-compatible awaitable callback, never an independent receiver."""
        previous_count = len(self.views.rows())
        try:
            # The pre-existing product observer is authoritative for admission.
            # A timer failure cannot suppress that observer's original work.
            self.views.observe(reading)
        except Exception as exc:
            self.views.record_error(exc)
            self._failure("legacy-admission", exc, reading)
            return
        except BaseException as exc:
            self._failure("legacy-interrupted", exc, reading)
            raise

        ticket = None
        stage = "typed-view"
        try:
            rows = self.views.rows()
            if len(rows) != previous_count + 1:
                raise S49PassiveClockJoinRejected("passive row not uniquely admitted")
            view = self._view(reading, rows[-1])
            stage = "clock-enter"
            ticket = self.timer.enter(view)
            stage = "callback"
            await self._observer(view)
            stage = "clock-exit"
            self.timer.exit(ticket)
        except BaseException as exc:
            if ticket is not None:
                # Failure/CancelledError must NOT become a completed interval.
                # abort() does not clear a terminal clock failure.
                self.timer.abort(ticket)
            self._failure(stage, exc, reading)
            if isinstance(exc, Exception):
                self.views.record_error(exc)
                return
            raise

    def failures(self) -> tuple[PassiveProbeFailure, ...]:
        return tuple(self._failures)

    def summary(self) -> dict:
        return {
            "classification": "DEV_ONLY_NOT_QUALIFIED",
            "sample_kind": "PASSIVE_CALLBACK_PROCESSING_ONLY",
            "native_probes_joined": len(self.views.rows()),
            "clock_samples": len(self.timer.rows()),
            "aborted_callbacks": len(self.timer.aborted_tickets()),
            "advisory_failures": len(self._failures),
            "failure_overflow": self._overflow,
            "action_issuer": "EXISTING_S49_ONLY",
            "additional_native_receives": 0,
            "additional_native_probes": 0,
            "physical_timing_attested": False,
            "cognition_time_attested": False,
            "s10_updates": 0,
            "memory_writes": 0,
        }
