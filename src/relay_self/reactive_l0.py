"""S44 bounded L0 World-event decisions, with no model call or Action authority.

An external operator supplies an intent-bound, independently scoped Action grant.
This gate *requests* an Action; execution and physical OUTCOME remain separately
owned by the existing Action supervisor/adapter. No automatic reconnect.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from relay_self.learning import LearningPreferenceState
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldConditionedChoice,
    select_world_conditioned_choice,
)


class ReactiveL0Rejected(ValueError):
    """Missing fresh World observation, grant or bounded capacity."""


@dataclass(frozen=True, slots=True)
class L0ActionGrant:
    authority_id: str
    action_id: str
    intent_id: str
    session_id: str
    event_seq: int
    probe_seq: int
    entity_id: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not all(isinstance(s, str) and s for s in (
                self.authority_id, self.action_id, self.intent_id, self.session_id,
            ))
            or not all(type(n) is int and n >= 0 for n in (
                self.event_seq, self.probe_seq, self.entity_id,
            ))
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise ReactiveL0Rejected("typed independently sourced Action grant required")


@dataclass(frozen=True, slots=True)
class L0Step:
    choice: WorldConditionedChoice
    event_seq: int
    action_request_id: str | None
    grant: L0ActionGrant | None

    @property
    def asks_for_action(self) -> bool:
        return self.action_request_id is not None


class ReactiveL0:
    """One session, owner-local cursor, explicit budgets; no implicit Action issue."""

    def __init__(
        self, session_id: str, intent_id: str,
        retained: LearningPreferenceState, *, max_events: int = 8,
        max_action_requests: int = 3,
    ) -> None:
        if (
            not isinstance(session_id, str) or not session_id
            or not isinstance(intent_id, str) or not intent_id
            or not isinstance(retained, LearningPreferenceState)
            or type(max_events) is not int or not 1 <= max_events <= 100
            or type(max_action_requests) is not int
            or not 1 <= max_action_requests <= max_events
        ):
            raise ReactiveL0Rejected("explicit source/intent/retention/budget required")
        self.session_id = session_id
        self.intent_id = intent_id
        self.retained = retained
        self.max_events = max_events
        self.max_action_requests = max_action_requests
        self.events = 0
        self.action_requests = 0
        self._last_seq = -1
        self._seen_entities: set[int] = set()
        self._used_action_ids: set[str] = set()

    def _check(
        self, event: MineflayerObservation, probe: MineflayerObservation,
    ) -> WorldConditionedChoice:
        if (
            not isinstance(event, MineflayerObservation)
            or not isinstance(probe, MineflayerObservation)
            or event.kind != "entities" or event.request_id is not None
            or probe.kind != "probe" or not probe.request_id
            or event.session_id != self.session_id
            or probe.session_id != self.session_id
            or event.seq <= self._last_seq or probe.seq <= event.seq
            or event.provenance.source != "mineflayer"
            or probe.provenance.source != "mineflayer"
            or event.snapshot.nearby_entities_coverage.truncated
            or probe.snapshot.nearby_entities_coverage.truncated
            or self.events >= self.max_events
        ):
            raise ReactiveL0Rejected("foreign, stale or incomplete native observation")
        e = event.snapshot.nearby_entities
        p = probe.snapshot.nearby_entities
        if (
            len(e) != 1 or len(p) != 1
            or e[0].name != "zombie" or p[0].name != "zombie"
            or e[0].entity_id != p[0].entity_id
            or e[0].entity_id in self._seen_entities
            or not math.isclose(e[0].distance, p[0].distance, abs_tol=1e-6)
        ):
            raise ReactiveL0Rejected("fresh uniquely identified zombie not evidenced")
        native = _native_threat(
            probe, probe.request_id, expected_entity_id=p[0].entity_id,
        )
        return select_world_conditioned_choice(
            native, self.retained,
            expected_session_id=self.session_id, expected_entity_id=p[0].entity_id,
        )

    def decide(
        self, event: MineflayerObservation, probe: MineflayerObservation,
        *, grant: L0ActionGrant | None = None,
    ) -> L0Step:
        choice = self._check(event, probe)
        if choice.selection is WorldChoiceKind.WAIT:
            if grant is not None:
                raise ReactiveL0Rejected("WAIT may not request or authorize Action")
            action_id = None
        else:
            if (
                not isinstance(grant, L0ActionGrant) or not grant.granted
                or grant.session_id != self.session_id
                or grant.intent_id != self.intent_id
                or grant.event_seq != event.seq
                or grant.probe_seq != probe.seq
                or grant.entity_id != choice.entity_id
                or grant.action_id in self._used_action_ids
                or self.action_requests >= self.max_action_requests
            ):
                raise ReactiveL0Rejected("MOVE requires fresh independent Action grant")
            action_id = grant.action_id
        # Count a decision only after every precondition succeeds.
        self.events += 1
        self._last_seq = probe.seq
        self._seen_entities.add(choice.entity_id)
        if action_id is not None:
            self.action_requests += 1
            self._used_action_ids.add(action_id)
        return L0Step(choice, event.seq, action_id, grant)

    async def run_session(
        self, session: object, *,
        probe: Callable[[MineflayerObservation], Awaitable[MineflayerObservation]],
        grant: Callable[[WorldConditionedChoice, int], L0ActionGrant | None],
        on_action_request: Callable[[L0Step], Awaitable[None]],
        max_frames: int = 100,
    ) -> tuple[L0Step, ...]:
        """Consume native events automatically; caller still owns Action authority.

        This is a bounded foreground loop, not a daemon. A timeout, broken
        transport or Action callback failure propagates; never replay an Action.
        """
        if (
            getattr(getattr(session, "started", None), "session_id", None)
            != self.session_id
            or type(max_frames) is not int or not 1 <= max_frames <= 10000
        ):
            raise ReactiveL0Rejected("live source mismatch or unbounded frame budget")
        result: list[L0Step] = []
        for _ in range(max_frames):
            if self.events >= self.max_events:
                break
            frame = await asyncio.wait_for(session.receive(), timeout=20)
            if not isinstance(frame, MineflayerObservation):
                raise ReactiveL0Rejected("non-observation/connection-end must fail closed")
            if frame.session_id != self.session_id:
                raise ReactiveL0Rejected("foreign source frame")
            if frame.kind != "entities":
                continue
            # Disappearance is not a claim of safety and consumes no policy step.
            if not frame.snapshot.nearby_entities:
                continue
            reading = await asyncio.wait_for(probe(frame), timeout=10)
            choice = self._check(frame, reading)
            permit = (
                grant(choice, frame.seq)
                if choice.selection is WorldChoiceKind.MOVE_AWAY
                else None
            )
            step = self.decide(frame, reading, grant=permit)
            result.append(step)
            if step.asks_for_action:
                await on_action_request(step)
        return tuple(result)
