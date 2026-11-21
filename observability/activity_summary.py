from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerAdapterStarted,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerDecodedMessage,
    MineflayerEffectResult,
    MineflayerMessage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerShutdownAck,
)
from relay_self.action import ActionEvent, ActionLifecycle
from relay_self.intent import IntentCommitment, IntentEvent
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.skill import SkillEvent, SkillExecution


class ActivitySummaryError(ValueError):
    """Raised when one read-only activity projection would be ambiguous."""


@dataclass(frozen=True, slots=True)
class MovementSpan:
    session_id: str
    first_seq: int
    last_seq: int
    observation_count: int
    start_position: MineflayerPosition
    end_position: MineflayerPosition
    path_distance: float
    displacement: float
    first_provenance: Provenance
    last_provenance: Provenance


@dataclass(frozen=True, slots=True)
class IntentActivity:
    event: IntentEvent


@dataclass(frozen=True, slots=True)
class SkillActivity:
    execution_id: str
    skill_id: str
    intent_id: str
    event: SkillEvent


@dataclass(frozen=True, slots=True)
class ActionActivity:
    action_id: str
    skill_execution_id: str
    intent_id: str
    event: ActionEvent


@dataclass(frozen=True, slots=True)
class ActivityDigest:
    """Bounded read-only projection over already-owned trace/evidence surfaces."""

    mineflayer_supplied: bool
    mineflayer_events: tuple[MineflayerDecodedMessage, ...]
    movement_spans: tuple[MovementSpan, ...]
    source_move_observation_count: int
    intent_supplied: bool
    intent_events: tuple[IntentActivity, ...]
    skill_supplied: bool
    skill_events: tuple[SkillActivity, ...]
    action_supplied: bool
    action_events: tuple[ActionActivity, ...]
    persistent_cognition_supplied: bool
    retained_memories: tuple[Memory, ...]


@dataclass(slots=True)
class _MovementAccumulator:
    session_id: str
    first_seq: int
    last_seq: int
    count: int
    start_position: MineflayerPosition
    previous_position: MineflayerPosition
    end_position: MineflayerPosition
    path_distance: float
    first_provenance: Provenance
    last_provenance: Provenance

    @classmethod
    def start(cls, message: MineflayerObservation) -> "_MovementAccumulator":
        position = message.snapshot.position
        return cls(
            session_id=message.session_id,
            first_seq=message.seq,
            last_seq=message.seq,
            count=1,
            start_position=position,
            previous_position=position,
            end_position=position,
            path_distance=0.0,
            first_provenance=message.provenance,
            last_provenance=message.provenance,
        )

    def append(self, message: MineflayerObservation) -> None:
        if message.session_id != self.session_id:
            raise ActivitySummaryError(
                "movement span cannot cross Mineflayer sessions"
            )
        if message.seq <= self.last_seq:
            raise ActivitySummaryError(
                "Mineflayer movement sequence must increase"
            )
        position = message.snapshot.position
        self.path_distance += _position_distance(
            self.previous_position,
            position,
        )
        self.previous_position = position
        self.end_position = position
        self.last_seq = message.seq
        self.count += 1
        self.last_provenance = message.provenance

    def finish(self) -> MovementSpan:
        return MovementSpan(
            session_id=self.session_id,
            first_seq=self.first_seq,
            last_seq=self.last_seq,
            observation_count=self.count,
            start_position=self.start_position,
            end_position=self.end_position,
            path_distance=self.path_distance,
            displacement=_position_distance(
                self.start_position,
                self.end_position,
            ),
            first_provenance=self.first_provenance,
            last_provenance=self.last_provenance,
        )


def reduce_activity(
    *,
    mineflayer_messages: Iterable[MineflayerDecodedMessage] | None = None,
    intent_commitment: IntentCommitment | None = None,
    skill_executions: Iterable[SkillExecution] | None = None,
    action_lifecycles: Iterable[ActionLifecycle] | None = None,
    persistent_before: PersistentCognition | None = None,
    persistent_after: PersistentCognition | None = None,
) -> ActivityDigest:
    """Reduce existing source histories without becoming a trace/state owner."""

    mineflayer_supplied = mineflayer_messages is not None
    (
        mineflayer_events,
        movement_spans,
        source_move_count,
    ) = _reduce_mineflayer(
        () if mineflayer_messages is None else tuple(mineflayer_messages)
    )

    intent_supplied = intent_commitment is not None
    intent_events = (
        ()
        if intent_commitment is None
        else tuple(IntentActivity(event) for event in intent_commitment.events)
    )

    skill_supplied = skill_executions is not None
    skill_events = _reduce_skills(
        () if skill_executions is None else tuple(skill_executions)
    )

    action_supplied = action_lifecycles is not None
    action_events = _reduce_actions(
        () if action_lifecycles is None else tuple(action_lifecycles)
    )

    persistent_supplied = (
        persistent_before is not None or persistent_after is not None
    )
    retained_memories = _reduce_persistent(
        persistent_before,
        persistent_after,
    )

    return ActivityDigest(
        mineflayer_supplied=mineflayer_supplied,
        mineflayer_events=mineflayer_events,
        movement_spans=movement_spans,
        source_move_observation_count=source_move_count,
        intent_supplied=intent_supplied,
        intent_events=intent_events,
        skill_supplied=skill_supplied,
        skill_events=skill_events,
        action_supplied=action_supplied,
        action_events=action_events,
        persistent_cognition_supplied=persistent_supplied,
        retained_memories=retained_memories,
    )


def render_activity_markdown(digest: ActivityDigest) -> str:
    if not isinstance(digest, ActivityDigest):
        raise ActivitySummaryError(
            "render_activity_markdown requires ActivityDigest"
        )

    lines = ["# RelaySelf Activity Summary", ""]

    lines.extend(_render_mineflayer(digest))
    lines.extend(_render_intents(digest))
    lines.extend(_render_skills(digest))
    lines.extend(_render_actions(digest))
    lines.extend(_render_persistent(digest))

    lines.extend(
        [
            "## Authority note",
            "",
            (
                "This summary is a read-only presentation projection over the "
                "listed source evidence and lifecycle histories. It is not "
                "fresh World truth, Belief, Memory, Action authority, or a "
                "Persistent Cognition write."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _reduce_mineflayer(
    messages: tuple[MineflayerDecodedMessage, ...],
) -> tuple[
    tuple[MineflayerDecodedMessage, ...],
    tuple[MovementSpan, ...],
    int,
]:
    events: list[MineflayerDecodedMessage] = []
    spans: list[MovementSpan] = []
    accumulator: _MovementAccumulator | None = None
    source_move_count = 0
    last_session_id: str | None = None
    last_seq: int | None = None

    for message in messages:
        if not isinstance(message, MineflayerMessage):
            raise ActivitySummaryError(
                "mineflayer_messages must contain decoded Mineflayer messages"
            )

        if message.session_id == last_session_id:
            if last_seq is not None and message.seq <= last_seq:
                raise ActivitySummaryError(
                    "Mineflayer sequence must increase within one session"
                )
        else:
            if accumulator is not None:
                spans.append(accumulator.finish())
                accumulator = None
            last_session_id = message.session_id

        last_seq = message.seq

        if (
            isinstance(message, MineflayerObservation)
            and message.kind == "move"
        ):
            source_move_count += 1
            if accumulator is None:
                accumulator = _MovementAccumulator.start(message)
            else:
                accumulator.append(message)
            continue

        if accumulator is not None:
            spans.append(accumulator.finish())
            accumulator = None
        events.append(message)

    if accumulator is not None:
        spans.append(accumulator.finish())

    return tuple(events), tuple(spans), source_move_count


def _reduce_skills(
    executions: tuple[SkillExecution, ...],
) -> tuple[SkillActivity, ...]:
    seen: set[str] = set()
    activities: list[SkillActivity] = []
    for execution in executions:
        if not isinstance(execution, SkillExecution):
            raise ActivitySummaryError(
                "skill_executions must contain SkillExecution snapshots"
            )
        if execution.execution_id in seen:
            raise ActivitySummaryError(
                f"duplicate Skill execution snapshot: {execution.execution_id}"
            )
        seen.add(execution.execution_id)
        activities.extend(
            SkillActivity(
                execution_id=execution.execution_id,
                skill_id=execution.skill_id,
                intent_id=execution.intent_id,
                event=event,
            )
            for event in execution.events
        )
    return tuple(activities)


def _reduce_actions(
    lifecycles: tuple[ActionLifecycle, ...],
) -> tuple[ActionActivity, ...]:
    seen: set[str] = set()
    activities: list[ActionActivity] = []
    for lifecycle in lifecycles:
        if not isinstance(lifecycle, ActionLifecycle):
            raise ActivitySummaryError(
                "action_lifecycles must contain ActionLifecycle snapshots"
            )
        if lifecycle.action_id in seen:
            raise ActivitySummaryError(
                f"duplicate Action lifecycle snapshot: {lifecycle.action_id}"
            )
        seen.add(lifecycle.action_id)
        activities.extend(
            ActionActivity(
                action_id=lifecycle.action_id,
                skill_execution_id=lifecycle.skill_execution_id,
                intent_id=lifecycle.intent_id,
                event=event,
            )
            for event in lifecycle.events
        )
    return tuple(activities)


def _reduce_persistent(
    before: PersistentCognition | None,
    after: PersistentCognition | None,
) -> tuple[Memory, ...]:
    if before is None and after is None:
        return ()
    if before is None or after is None:
        raise ActivitySummaryError(
            "persistent cognition summary requires both before and after snapshots"
        )
    if not isinstance(before, PersistentCognition) or not isinstance(
        after,
        PersistentCognition,
    ):
        raise ActivitySummaryError(
            "persistent cognition inputs must be PersistentCognition snapshots"
        )
    if before.identity != after.identity:
        raise ActivitySummaryError(
            "persistent cognition delta requires the same identity"
        )

    before_by_id = {
        memory.memory_id: memory
        for memory in before.memories
    }
    after_by_id = {
        memory.memory_id: memory
        for memory in after.memories
    }
    for memory_id, memory in before_by_id.items():
        if after_by_id.get(memory_id) != memory:
            raise ActivitySummaryError(
                "persistent cognition delta may not rewrite or remove "
                f"existing Memory: {memory_id}"
            )

    return tuple(
        memory
        for memory in after.memories
        if memory.memory_id not in before_by_id
    )


def _render_mineflayer(digest: ActivityDigest) -> list[str]:
    lines = ["## Minecraft / Mineflayer", ""]
    if not digest.mineflayer_supplied:
        return [*lines, "- Source trace: not supplied.", ""]

    lines.append(
        "- Movement reduction: "
        f"{digest.source_move_observation_count} source move observations "
        f"-> {len(digest.movement_spans)} compact span(s)."
    )
    for span in digest.movement_spans:
        lines.append(
            "- Movement span "
            f"{span.session_id} seq {span.first_seq}-{span.last_seq}: "
            f"{span.observation_count} observations, "
            f"path={span.path_distance:.3f} blocks, "
            f"displacement={span.displacement:.3f} blocks, "
            f"from={_position_text(span.start_position)}, "
            f"to={_position_text(span.end_position)} "
            f"[{_provenance_text(span.first_provenance)} -> "
            f"{_provenance_text(span.last_provenance)}]."
        )

    if not digest.mineflayer_events:
        lines.append("- Non-movement source events: supplied; none in interval.")
    else:
        for message in digest.mineflayer_events:
            lines.append(_render_mineflayer_message(message))
    lines.append("")
    return lines


def _render_mineflayer_message(message: MineflayerDecodedMessage) -> str:
    provenance = _provenance_text(message.provenance)
    if isinstance(message, MineflayerAdapterStarted):
        return (
            f"- Adapter started: session={message.session_id}, seq={message.seq}, "
            f"mineflayer={message.mineflayer_version} [{provenance}]."
        )
    if isinstance(message, MineflayerObservation):
        snapshot = message.snapshot
        details = [
            f"health={_number(snapshot.health)}",
            f"food={_number(snapshot.food)}",
            f"oxygen={_number(snapshot.oxygen_level)}",
            f"position={_position_text(snapshot.position)}",
        ]
        if snapshot.time is not None:
            details.append(
                "time="
                f"day:{snapshot.time.day},"
                f"time_of_day:{snapshot.time.time_of_day},"
                f"is_day:{str(snapshot.time.is_day).lower()}"
            )
        if snapshot.inventory:
            inventory = ",".join(
                f"{item.name}x{item.count}@{item.slot}"
                for item in snapshot.inventory
            )
            details.append(f"inventory=[{inventory}]")
        if snapshot.nearby_entities:
            entities = ",".join(
                _entity_text(entity)
                for entity in snapshot.nearby_entities
            )
            details.append(f"nearby_entities=[{entities}]")
        return (
            f"- Observation {message.kind}: session={message.session_id}, "
            f"seq={message.seq}, "
            + ", ".join(details)
            + f" [{provenance}]."
        )
    if isinstance(message, MineflayerEffectResult):
        error = (
            f", error={message.error}"
            if message.error is not None
            else ""
        )
        return (
            f"- Effect result: action={message.action_id}, "
            f"effect={message.effect}, result={message.result}{error}, "
            f"seq={message.seq} [{provenance}]."
        )
    if isinstance(message, MineflayerConnectionEnd):
        return (
            f"- Connection ended: reason={message.reason}, seq={message.seq} "
            f"[{provenance}]."
        )
    if isinstance(message, MineflayerAdapterErrorMessage):
        return (
            f"- Adapter error: {message.message}, seq={message.seq} "
            f"[{provenance}]."
        )
    if isinstance(message, MineflayerCommandError):
        return (
            f"- Command error: {message.message}, seq={message.seq} "
            f"[{provenance}]."
        )
    if isinstance(message, MineflayerShutdownAck):
        return (
            f"- Adapter shutdown acknowledged: seq={message.seq} "
            f"[{provenance}]."
        )
    raise ActivitySummaryError(
        f"unsupported Mineflayer message for rendering: {type(message).__name__}"
    )


def _render_intents(digest: ActivityDigest) -> list[str]:
    lines = ["## Current Intent history", ""]
    if not digest.intent_supplied:
        return [*lines, "- Intent history: not supplied.", ""]
    if not digest.intent_events:
        return [*lines, "- Intent history: supplied; no events.", ""]

    for activity in digest.intent_events:
        event = activity.event
        detail = (
            f", objective={event.objective}"
            if event.objective is not None
            else ""
        )
        if event.reason is not None:
            detail += f", reason={event.reason}"
        lines.append(
            f"- {event.kind.value}: intent={event.intent_id}{detail}, "
            f"at_ns={event.at_ns} "
            f"[{_provenance_text(event.provenance)}]."
        )
    lines.append("")
    return lines


def _render_skills(digest: ActivityDigest) -> list[str]:
    lines = ["## Skill execution history", ""]
    if not digest.skill_supplied:
        return [*lines, "- Skill history: not supplied.", ""]
    if not digest.skill_events:
        return [*lines, "- Skill history: supplied; no events.", ""]

    for activity in digest.skill_events:
        event = activity.event
        reason = (
            f", reason={event.reason}"
            if event.reason is not None
            else ""
        )
        lines.append(
            f"- {activity.skill_id}/{activity.execution_id}: "
            f"{event.state.value}, intent={activity.intent_id}{reason}, "
            f"at_ns={event.at_ns} "
            f"[{_provenance_text(event.provenance)}]."
        )
    lines.append("")
    return lines


def _render_actions(digest: ActivityDigest) -> list[str]:
    lines = ["## Action lifecycle history", ""]
    if not digest.action_supplied:
        return [*lines, "- Action history: not supplied.", ""]
    if not digest.action_events:
        return [*lines, "- Action history: supplied; no events.", ""]

    for activity in digest.action_events:
        event = activity.event
        detail = ""
        if event.authority is not None:
            detail += f", authority={event.authority}"
        if event.deadline_ns is not None:
            detail += f", deadline_ns={event.deadline_ns}"
        lines.append(
            f"- {activity.action_id}: {event.state.value}, "
            f"skill_execution={activity.skill_execution_id}, "
            f"intent={activity.intent_id}{detail}, at_ns={event.at_ns} "
            f"[{_provenance_text(event.provenance)}]."
        )
    lines.append("")
    return lines


def _render_persistent(digest: ActivityDigest) -> list[str]:
    lines = ["## Durable cognition changes", ""]
    if not digest.persistent_cognition_supplied:
        return [*lines, "- Persistent Cognition delta: not supplied.", ""]
    if not digest.retained_memories:
        return [*lines, "- Persistent Cognition delta: supplied; no new Memory.", ""]

    for memory in digest.retained_memories:
        lines.append(
            f"- Memory retained: {memory.memory_id}: {memory.content} "
            f"[source={_provenance_text(memory.source_provenance)}; "
            f"integration={_provenance_text(memory.integration_provenance)}]."
        )
    lines.append("")
    return lines


def _position_distance(
    left: MineflayerPosition,
    right: MineflayerPosition,
) -> float:
    return math.sqrt(
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def _position_text(position: MineflayerPosition) -> str:
    return (
        f"({_number(position.x)},"
        f"{_number(position.y)},"
        f"{_number(position.z)})"
    )


def _entity_text(entity: object) -> str:
    name = getattr(entity, "name", None)
    entity_type = getattr(entity, "entity_type", None)
    distance = getattr(entity, "distance", None)
    label = name or entity_type or "entity"
    if distance is None:
        return str(label)
    return f"{label}@distance={_number(distance)}"


def _provenance_text(provenance: Provenance) -> str:
    return f"{provenance.source}:{provenance.reference}"


def _number(value: float) -> str:
    return f"{value:g}"
