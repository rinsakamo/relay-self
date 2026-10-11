"""Bounded, foreground one-session Minecraft L0 owner + append-only RelayUI feed.

Uses existing NormalWorldL0 for decisions and existing NormalActionReceipt for
action closure. The caller, not this module, supplies independent S49 source-
scoped grants, correlated probes and the existing NormalSessionActionExecutor
dispatch callback. No server/model launcher, background daemon or new authority.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt, NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from adapters.mineflayer.self_s2_candidates import S2CandidateReview
from relay_self.action import ActionState
from relay_self.reactive_l0 import L0ActionGrant, L0Step
from relay_self.world_conditioned_choice import WorldChoiceKind, WorldConditionedChoice


class SessionRunRejected(ValueError):
    """A live source, resource limit, or Action closure cannot be trusted."""


@dataclass(frozen=True, slots=True)
class SessionBudget:
    max_events: int = 12
    max_actions: int = 3
    max_frames: int = 500
    max_seconds: float = 180.0
    poll_seconds: float = 0.25

    def __post_init__(self) -> None:
        if (
            type(self.max_events) is not int or not 1 <= self.max_events <= 100
            or type(self.max_actions) is not int
            or not 1 <= self.max_actions <= self.max_events
            or type(self.max_frames) is not int
            or not self.max_events <= self.max_frames <= 10000
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 1 <= self.max_seconds <= 600
            or type(self.poll_seconds) not in (int, float)
            or not math.isfinite(self.poll_seconds)
            or not 0.02 <= self.poll_seconds <= 2
        ):
            raise SessionRunRejected("explicit bounded one-session budget required")


class AppendOnlySessionEvents:
    """One new source-tagged JSONL file. Flush before external Action callbacks."""

    def __init__(self, path: Path, session_id: str) -> None:
        if (
            not isinstance(path, Path)
            or not path.is_absolute() or path.exists() or path.is_symlink()
            or not path.parent.is_dir() or path.parent.is_symlink()
            or not isinstance(session_id, str) or not session_id
        ):
            raise SessionRunRejected("new physical event sink outside prior evidence required")
        self.path = path
        self.session_id = session_id
        self._number = 0
        self._closed = False
        self._stream = path.open("x", encoding="utf-8")

    def write(self, kind: str, **data: object) -> None:
        if self._closed:
            raise SessionRunRejected("closed session event stream")
        row = {
            "schema": "SELF1_BOUNDED_WORLD_EVENT_V1",
            "session": self.session_id,
            "index": self._number,
            "kind": kind,
            "source": "S49_OWNER_EXPLICIT_REAL_OR_SYNTHETIC",
            **data,
        }
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)
        self._stream.write(encoded + "\n")
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._number += 1

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._stream.close()


class BoundedSessionDriver:
    """Controls the foreground session lifetime; never authorizes movement.

    The on_action callback MUST delegate to existing S49/S16 Action execution
    and return its typed NormalActionReceipt. Other callback results are UNKNOWN.
    Caller still owns Mineflayer/Java shutdown; stop() never relaunches them.
    """

    def __init__(
        self, host: NormalWorldL0, session: object,
        budget: SessionBudget, events: AppendOnlySessionEvents,
    ) -> None:
        if (
            not isinstance(host, NormalWorldL0)
            or not isinstance(budget, SessionBudget)
            or not isinstance(events, AppendOnlySessionEvents)
            or events.session_id != host.session_id
            or getattr(getattr(session, "started", None), "session_id", None)
            != host.session_id
            or not callable(getattr(session, "receive", None))
            or host.max_events != budget.max_events
            or host.max_action_requests != budget.max_actions
            or host.events != 0 or host.action_requests != 0
        ):
            raise SessionRunRejected("fresh existing S49 host/session/budget required")
        self.host = host
        self.session = session
        self.budget = budget
        self.events = events
        self._paused = False
        self._stopped = False
        self._used = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True

    async def run(
        self, *,
        probe: Callable[[MineflayerObservation], Awaitable[MineflayerObservation]],
        grant: Callable[[WorldConditionedChoice, int], L0ActionGrant | None],
        on_action: Callable[[L0Step], Awaitable[NormalActionReceipt]],
        on_candidate: Callable[[WorldConditionedChoice, int], S2CandidateReview] | None = None,
        on_l2_probe: Callable[[MineflayerObservation], Awaitable[None]] | None = None,
    ) -> dict[str, object]:
        if (self._used or not all(callable(x) for x in (probe, grant, on_action))
                or (on_candidate is not None and not callable(on_candidate))
                or (on_l2_probe is not None and not callable(on_l2_probe))):
            raise SessionRunRejected("one invocation and explicit S49 callbacks required")
        self._used = True
        start = time.monotonic()
        end = start + self.budget.max_seconds
        frames = 0
        closures = 0
        terminal = "BUDGET_OR_STOP_NOT_REACHED"
        self.events.write("session_started", max_seconds=self.budget.max_seconds,
                          max_events=self.budget.max_events,
                          max_actions=self.budget.max_actions)
        try:
            while frames < self.budget.max_frames:
                remaining = end - time.monotonic()
                if self._stopped:
                    terminal = "OPERATOR_STOP"
                    break
                if remaining <= 0:
                    terminal = "TIME_BUDGET_ENDED"
                    break
                if self.host.events >= self.budget.max_events:
                    terminal = "EVENT_BUDGET_ENDED"
                    break
                if self.host.action_requests >= self.budget.max_actions:
                    terminal = "ACTION_BUDGET_ENDED"
                    break
                if self._paused:
                    await asyncio.sleep(min(self.budget.poll_seconds, remaining))
                    continue
                try:
                    frame = await asyncio.wait_for(
                        self.session.receive(),
                        timeout=min(self.budget.poll_seconds, remaining),
                    )
                except TimeoutError:
                    # An empty native stream is not evidence of safety.
                    continue
                frames += 1
                if not isinstance(frame, MineflayerObservation):
                    raise SessionRunRejected("invalid native observation or connection ended")
                if frame.session_id != self.host.session_id:
                    raise SessionRunRejected("foreign native World session")
                if frame.kind != "entities":
                    continue
                if not any(e.name == "zombie" for e in frame.snapshot.nearby_entities):
                    continue
                # No Action, grant or token can be minted until the re-probe is
                # independently received from the same current native source.
                remaining = end - time.monotonic()
                if remaining <= 0 or self._stopped:
                    terminal = "TIME_OR_OPERATOR_STOP_BEFORE_PROBE"
                    break
                reading = await asyncio.wait_for(probe(frame), timeout=min(10, remaining))
                if self._stopped or time.monotonic() >= end:
                    terminal = "TIME_OR_OPERATOR_STOP_AFTER_PROBE"
                    break
                if self._paused:
                    # Never resume an old probe as if the World had not moved.
                    terminal = "PAUSED_AFTER_PROBE_NO_ACTION"
                    break
                choice = self.host._check(frame, reading)
                # The original S49 grant/decision remains independent of L1/L2.
                if on_l2_probe is not None:
                    try:
                        await asyncio.wait_for(
                            on_l2_probe(reading), timeout=min(.1, max(.001, end-time.monotonic())),
                        )
                        self.events.write(
                            "l2_probe_observed", event_seq=frame.seq,
                            probe_seq=reading.seq, native_source=reading.provenance.reference,
                            used_as_action=False, authorized_actions=0,
                        )
                    except Exception as exc:
                        # Advisory failure cannot prevent hard L0 survival.
                        self.events.write(
                            "l2_probe_unavailable", event_seq=frame.seq,
                            probe_seq=reading.seq, reason_type=type(exc).__name__,
                            used_as_action=False, authorized_actions=0,
                        )
                permit = grant(choice, frame.seq) if choice.selection is WorldChoiceKind.MOVE_AWAY else None
                step = self.host.decide(frame, reading, grant=permit)
                self.events.write(
                    "world_decision", epoch=self.host.events,
                    event_seq=frame.seq, probe_seq=reading.seq,
                    event_source=frame.provenance.reference,
                    probe_source=reading.provenance.reference,
                    probe_request_id=reading.request_id,
                    source_type="MINEFLAYER_NATIVE",
                    entity_id=choice.entity_id, distance_m=choice.distance_m,
                    layer="L0", selection=choice.selection.value,
                    action_request_id=step.action_request_id,
                    retained_revision=self.host.retained.revision,
                    goal_success_attested=False,
                )
                if on_candidate is not None:
                    try:
                        review = on_candidate(choice, frame.seq)
                        if (
                            not isinstance(review, S2CandidateReview)
                            or review.session_id != self.host.session_id
                            or review.event_seq != frame.seq
                            or review.probe_seq != reading.seq
                            or review.l0_selection != choice.selection.value
                            or review.effective_selection != choice.selection.value
                            or review.action_authorized_by_l1
                            or review.learned_habit_claimed
                            or review.l2_used_for_action
                        ):
                            raise SessionRunRejected("untrusted L1 candidate")
                        self.events.write(
                            "l1_candidate_review", epoch=self.host.events,
                            event_seq=frame.seq, probe_seq=reading.seq,
                            source_provenance=review.l1_source,
                            l0_selection=review.l0_selection,
                            l1_candidate=review.l1_candidate,
                            l1_status=review.l1_status,
                            l1_repertoire_revision=review.l1_repertoire_revision,
                            effective_selection=review.effective_selection,
                            l1_authorized_actions=0, learned_habit=False,
                            l2_used_as_action=False,
                        )
                    except Exception as exc:
                        self.events.write(
                            "l1_candidate_unavailable", epoch=self.host.events,
                            event_seq=frame.seq, probe_seq=reading.seq,
                            reason_type=type(exc).__name__,
                            effective_selection=choice.selection.value,
                            l1_authorized_actions=0,
                        )
                if not step.asks_for_action:
                    continue
                # Before any potentially irreversible command, flush the exact
                # source and authorized request ID to durable JSONL.
                self.events.write(
                    "action_requested_not_yet_issued", epoch=self.host.events,
                    action_id=step.action_request_id, event_seq=frame.seq,
                    probe_seq=reading.seq, authority_id=step.grant.authority_id,
                )
                try:
                    remaining = end - time.monotonic()
                    if remaining <= 0 or self._stopped or self._paused:
                        terminal = "ACTION_NOT_DISPATCHED_TIME_PAUSE_OR_STOP"
                        self.events.write(
                            "action_not_dispatched",
                            action_id=step.action_request_id,
                            physical_outcome="NOT_ISSUED",
                            safe_to_replay=False,
                        )
                        break
                    receipt = await asyncio.wait_for(
                        on_action(step), timeout=min(15, remaining),
                    )
                    if (
                        not isinstance(receipt, NormalActionReceipt)
                        or receipt.terminal.state is not ActionState.OUTCOME
                        or receipt.terminal.action_id != step.action_request_id
                        or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
                        or receipt.consequence.action_id != step.action_request_id
                        or receipt.consequence.session_id != self.host.session_id
                        or receipt.source != reading.provenance
                        or not receipt.terminal.is_current_snapshot
                        or receipt.consequence.movement_distance is None
                        or receipt.consequence.movement_distance < 0.05
                    ):
                        raise SessionRunRejected("unqualified S49 native Action terminal")
                    # Preserve and hash original decoded S49 evidence before
                    # admitting a positive closure into the RelayUI stream.
                    native_evidence = capture_native_action_evidence(receipt.consequence)
                    native_bytes = json.dumps(
                        native_evidence, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False, allow_nan=False,
                    ).encode("utf-8")
                except BaseException as exc:
                    self.events.write(
                        "action_outcome_unknown", action_id=step.action_request_id,
                        error_type=type(exc).__name__, physical_outcome="UNKNOWN",
                        safe_to_replay=False,
                    )
                    raise
                self.events.write(
                    "action_outcome", epoch=self.host.events,
                    action_id=receipt.terminal.action_id,
                    original_action_state=receipt.terminal.state.value,
                    original_world_status=receipt.consequence.status.value,
                    original_source_session=receipt.consequence.session_id,
                    source_provenance=receipt.source.reference,
                    before_seq=receipt.consequence.before_observation.seq,
                    after_seq=receipt.consequence.after_observation.seq,
                    native_execution_evidence=native_evidence,
                    native_execution_sha256=hashlib.sha256(native_bytes).hexdigest(),
                    physical_outcome="outcome",
                    movement_m=receipt.consequence.movement_distance,
                    goal_success_attested=False,
                    learning_feedback_qualified=False,
                    habit_granted=False,
                )
                closures += 1
            else:
                terminal = "FRAME_BUDGET_ENDED"
            summary: dict[str, object] = {
                "classification": "BOUNDED_S49_SESSION_TERMINATED_NOT_AUTONOMY_PROOF",
                "terminal": terminal, "session": self.host.session_id,
                "events": self.host.events, "action_requests": self.host.action_requests,
                "closed_outcomes": closures, "frames": frames,
                "learning_updates": 0, "habit_grants": 0,
                "l2_attempts": 0, "model_stop_ack": False,
            }
            self.events.write("session_terminal", **summary)
            return summary
        except BaseException as exc:
            self.events.write(
                "session_failed", reason=type(exc).__name__,
                action_requests=self.host.action_requests,
                closed_outcomes=closures, physical_outcome="UNKNOWN_IF_IN_FLIGHT",
                no_replay=True, learning_updates=0, habit_grants=0,
            )
            raise
        finally:
            self.events.close()
