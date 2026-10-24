"""#632 passive producer-local timing, no new reader/issuer or physical clock.

Instrument *only* a callback entered by the original S49 single-reader owner.
Elapsed time denotes Python callback processing, NOT cognition, actuator
start, Minecraft game time, attack windup, motion or Action execution.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from relay_self.self_body import SelfBodyView


class PassiveHostClockRejected(ValueError):
    """Unqualified caller view, cross-origin timing or invalid local sample."""


class HostClockOrigin(str, Enum):
    PYTHON_PROCESS_MONOTONIC = "PYTHON_PROCESS_MONOTONIC"
    SYNTHETIC_DEV_CLOCK = "SYNTHETIC_DEV_CLOCK"


@dataclass(frozen=True, slots=True)
class CallbackTicket:
    self_id: str
    session_id: str
    epoch_id: str
    native_seq: int
    request_id: str
    source_ref: str
    entered_ns: int
    origin: HostClockOrigin


@dataclass(frozen=True, slots=True)
class PassiveHostInterval:
    self_id: str
    session_id: str
    source_ref: str
    native_seq: int
    origin: HostClockOrigin
    callback_elapsed_ns: int
    callback_elapsed_ms: float
    sample_kind: str = "PASSIVE_CALLBACK_PROCESSING_ONLY"
    action_start_ns: None = None
    world_cue_onset_ns: None = None
    movement_speed_mps: None = None
    real_action_outcome_attested: bool = False
    allowed_to_act: bool = False

    def __post_init__(self) -> None:
        if (
            self.sample_kind != "PASSIVE_CALLBACK_PROCESSING_ONLY"
            or self.action_start_ns is not None
            or self.world_cue_onset_ns is not None
            or self.movement_speed_mps is not None
            or self.real_action_outcome_attested is not False
            or self.allowed_to_act is not False
        ):
            raise PassiveHostClockRejected(
                "Python callback interval cannot attest physical timing or Action"
            )
        if (
            not isinstance(self.origin, HostClockOrigin)
            or type(self.callback_elapsed_ns) is not int
            or self.callback_elapsed_ns < 0
            or not math.isfinite(self.callback_elapsed_ms)
            or self.callback_elapsed_ms < 0
            or self.callback_elapsed_ms != self.callback_elapsed_ns / 1_000_000
        ):
            raise PassiveHostClockRejected("invalid callback timing")


class PassiveHostCallbackTimer:
    """Ephemeral, one-at-a-time, same Python process clock bookkeeping.

    Externally injected clocks are *always* labelled synthetic; only the
    constructor's default time.monotonic_ns is labelled host monotonic.
    Neither label authenticates an arbitrary upstream Body observation.
    """

    def __init__(
        self, *, self_id: str, capacity: int = 16,
        clock: Callable[[], int] | None = None,
    ) -> None:
        if type(self_id) is not str or not self_id or self_id != self_id.strip():
            raise PassiveHostClockRejected("invalid Self identity")
        if type(capacity) is not int or capacity < 1 or capacity > 128:
            raise PassiveHostClockRejected("invalid bounded capacity")
        if clock is not None and not callable(clock):
            raise PassiveHostClockRejected("injected clock must be callable")
        self.self_id = self_id
        self.capacity = capacity
        self.origin = (
            HostClockOrigin.PYTHON_PROCESS_MONOTONIC
            if clock is None else HostClockOrigin.SYNTHETIC_DEV_CLOCK
        )
        self._clock = time.monotonic_ns if clock is None else clock
        self._active: CallbackTicket | None = None
        self._session: str | None = None
        self._last_seq = -1
        self._last_clock_ns: int | None = None
        self._rows: list[PassiveHostInterval] = []

    def _now(self) -> int:
        value = self._clock()
        if (
            type(value) is not int or value < 0 or value > (2**63 - 1)
            or (self._last_clock_ns is not None
                and value < self._last_clock_ns)
        ):
            raise PassiveHostClockRejected("bad or reversed local monotonic clock")
        self._last_clock_ns = value
        return value

    def enter(self, view: SelfBodyView) -> CallbackTicket:
        """Call after S49 has received ONE qualified probe, before observer work."""
        if type(view) is not SelfBodyView or view.self_id != self.self_id:
            raise PassiveHostClockRejected("foreign or overridden SelfBodyView")
        obs = view.observation
        if (
            obs is None or not view.session_id or not view.epoch_id
            or obs.session_id != view.session_id
            or obs.source_provenance.source != "mineflayer"
            or obs.source_provenance.reference
            != f"{view.session_id}:{obs.native_seq}"
            or type(obs.native_seq) is not int
            or obs.native_seq <= self._last_seq
            or type(obs.request_id) is not str or not obs.request_id
            or self._session not in (None, view.session_id)
        ):
            raise PassiveHostClockRejected("invalid native source or replay")
        if self._active is not None:
            raise PassiveHostClockRejected("overlapping callback timing")
        if len(self._rows) >= self.capacity:
            raise PassiveHostClockRejected("bounded callback budget exhausted")
        ticket = CallbackTicket(
            self_id=self.self_id,
            session_id=view.session_id,
            epoch_id=view.epoch_id,
            native_seq=obs.native_seq,
            request_id=obs.request_id,
            source_ref=obs.source_ref,
            entered_ns=self._now(),
            origin=self.origin,
        )
        self._active = ticket
        self._session = view.session_id
        self._last_seq = obs.native_seq
        return ticket

    def exit(self, ticket: CallbackTicket) -> PassiveHostInterval:
        """Close one callback with this recorder's same-process local clock."""
        if ticket is not self._active or self._active is None:
            raise PassiveHostClockRejected("foreign or duplicate callback ticket")
        ended_ns = self._now()
        delta = ended_ns - ticket.entered_ns
        if delta < 0 or not math.isfinite(delta / 1_000_000):
            raise PassiveHostClockRejected("invalid derived interval")
        review = PassiveHostInterval(
            self_id=ticket.self_id,
            session_id=ticket.session_id,
            source_ref=ticket.source_ref,
            native_seq=ticket.native_seq,
            origin=ticket.origin,
            callback_elapsed_ns=delta,
            callback_elapsed_ms=delta / 1_000_000,
        )
        self._rows.append(review)
        self._active = None
        return review

    def rows(self) -> tuple[PassiveHostInterval, ...]:
        """Return immutable snapshots; no native read, world write or motor grant."""
        return tuple(self._rows)
