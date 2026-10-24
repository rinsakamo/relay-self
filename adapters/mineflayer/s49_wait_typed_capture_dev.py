"""DEV-only typed S49 S16 closure custody on the original Action executor.

The sole S49 executor still calls its unmodified execute() / ActionSupervisor.
The existing read-only closure tap yields original typed objects. This companion
accepts no source-free OUTCOME flag and grants neither physical WAIT nor P1.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer import normal_action as native_action_owner
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalActionReceipt,
    observe_closed_native_actions,
)
from adapters.mineflayer.s49_wait_fenced_executor_dev import S49WaitFencedExecutorDev
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.action import ActionState


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class S49TypedClosureProjectionDev:
    """Derived, never issuer-attested, evidence from existing typed objects."""

    action_id: str
    session_id: str
    terminal_ref: str
    clear_ref: str
    evidence_sha256: str
    decoded_evidence: dict
    physical_source_authenticated: bool = False
    wait_ticks_admitted: int = 0
    p1_fatigue_recovered: float = 0.0


class S49TypedClosureCaptureDev:
    """One-use original-execute observer; no new native reader or action issuer."""

    def __init__(self, executor: S49WaitFencedExecutorDev):
        if (not isinstance(executor, S49WaitFencedExecutorDev)
                or executor.wait_phase != "NEW"):
            raise BoundaryRejected("typed closure requires unused S49 DEV owner")
        self._executor = executor
        self._state = "NEW"
        self._projection: S49TypedClosureProjectionDev | None = None
        self._receipt: NormalActionReceipt | None = None
        self._readback: NormalActionClosedReadback | None = None
        self._probe: object | None = None
        self._supervisor: object | None = None
        self._dispatch_at_close: frozenset[str] = frozenset()
        self._count_at_close: int | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def projection(self) -> S49TypedClosureProjectionDev | None:
        return self._projection

    def _project(
        self, receipt: NormalActionReceipt,
        observations: list[NormalActionClosedReadback], *,
        expected_probe,
    ) -> S49TypedClosureProjectionDev:
        ex = self._executor
        if (not isinstance(receipt, NormalActionReceipt)
                or len(observations) != 1
                or not isinstance(observations[0], NormalActionClosedReadback)):
            raise BoundaryRejected("missing, duplicated or untyped original close")
        closed = observations[0]
        terminal = receipt.terminal
        consequence = receipt.consequence
        if (closed.terminal is not terminal
                or closed.consequence is not consequence
                or closed.original_probe is not expected_probe
                or terminal.state is not ActionState.OUTCOME
                or consequence.status is not WorldConsequenceStatus.EXECUTED
                or terminal.action_id != consequence.action_id
                or consequence.session_id != ex.session_id
                or terminal.action_id not in ex._dispatched
                or ex.supervisor.get(terminal.action_id) is not terminal
                or ex.supervisor.open_actions
                or consequence.cleanup_attempted is not True):
            raise BoundaryRejected("typed close not from sole bound S49 owner")
        # Reuses the existing strict S16 original-frame / cleanup ACK checker.
        # Values are decoded typed source objects, NOT original wire bytes.
        try:
            evidence = capture_native_action_evidence(consequence)
        except ValueError as exc:
            raise BoundaryRejected("typed S16 original frames not complete") from exc
        terminal_events = [
            {
                "state": event.state.value, "at_ns": event.at_ns,
                "authority": event.authority, "deadline_ns": event.deadline_ns,
                "source": event.provenance.source,
                "reference": event.provenance.reference,
            }
            for event in terminal.events
        ]
        return S49TypedClosureProjectionDev(
            action_id=terminal.action_id, session_id=ex.session_id,
            terminal_ref="derived-dev-s49-terminal-sha256:" + _hash(terminal_events),
            clear_ref="derived-dev-s16-clear-sha256:"
            + _hash(evidence["cleanup_receipt"]),
            evidence_sha256=_hash(evidence), decoded_evidence=evidence,
        )

    async def execute_owned(self, session, step, bound, probe, propose, issue):
        """Call original execute once and retain its own closure callback.

        If original execute cancels/raises, do not attempt recovery or replay.
        """
        if self._state != "NEW" or self._executor.wait_phase != "NEW":
            raise BoundaryRejected("original S49 Action capture is one-shot")
        # An outer Stage R/product observer must never be silently replaced.
        if native_action_owner._READ_ONLY_CLOSURE.get() is not None:
            raise BoundaryRejected("another original Action closure observer is active")
        self._state = "RUNNING"
        observations: list[NormalActionClosedReadback] = []

        def readback(value):
            observations.append(value)

        try:
            with observe_closed_native_actions(readback):
                receipt = await self._executor.execute(
                    session, step, bound, probe, propose, issue,
                )
            result = self._project(
                receipt, observations, expected_probe=probe,
            )
        except BaseException:
            self._state = "FAILED"
            self._projection = None
            raise
        self._receipt = receipt
        self._readback = observations[0]
        self._probe = probe
        self._supervisor = self._executor.supervisor
        self._dispatch_at_close = frozenset(self._executor._dispatched)
        self._count_at_close = self._executor._count
        self._projection = result
        self._state = "CAPTURED"
        return receipt

    def arm_owner_wait(self) -> S49TypedClosureProjectionDev:
        """Arm same Executor only AFTER a verified existing S16 closure."""
        if self._state != "CAPTURED" or self._projection is None:
            raise BoundaryRejected("missing captured original S49 typed OUTCOME")
        result = self._projection
        if (self._receipt is None or self._readback is None
                or self._executor.supervisor is not self._supervisor
                or frozenset(self._executor._dispatched) != self._dispatch_at_close
                or self._executor._count != self._count_at_close):
            raise BoundaryRejected("owner changed after typed S16 close")
        if self._project(
            self._receipt, [self._readback], expected_probe=self._probe,
        ) != result:
            raise BoundaryRejected("typed S16 capture changed after closure")
        self._executor.arm_after_original_outcome(
            closed_action_id=result.action_id,
            terminal_outcome_ref=result.terminal_ref,
            controls_clear_ref=result.clear_ref,
        )
        self._state = "ARMED"
        return result


def reject_incompatible_s50_control_action(
    projection: S49TypedClosureProjectionDev, *,
    source_session: str, action_id: str, commands: list[dict],
) -> None:
    """Reject aliasing a legacy forward S50 demo with a backward S49 Action.

    This is a negative interoperability gate, not proof of any source matching.
    """
    if (not isinstance(projection, S49TypedClosureProjectionDev)
            or projection.session_id != source_session
            or projection.action_id != action_id
            or not isinstance(commands, list)):
        raise BoundaryRejected("S49/S50 session or Action not identical")
    controlled = [
        c for c in commands
        if isinstance(c, dict) and c.get("effect") == "set_control"
    ]
    if (len(controlled) != 1
            or controlled[0].get("action_id") != action_id
            or controlled[0].get("control") != "back"
            or controlled[0].get("state") is not True):
        raise BoundaryRejected("S49 backward Action cannot alias S50 forward")
    raise BoundaryRejected(
        "S49/S50 native cleanup ACK wire binding not independently attested"
    )
