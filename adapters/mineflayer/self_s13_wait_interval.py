"""S13: original bridge evidence for *nonissued* WAIT World observation interval.

The S7 raw Mineflayer Python-side sent/received capture is a reviewable
source boundary; it is not Minecraft TCP, authoritative silence from other
clients, or proof of a World task Goal. WAIT has NO S16 ActionOutcome.

No process, command, World, Memory, Action, clock, or file side effects.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerAdapterStarted,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerEntityHurt,
    MineflayerObservation,
    MineflayerShutdownAck,
    MineflayerStreamDecoder,
)
from adapters.mineflayer.self_s7_native_receipt import (
    MAX_RECEIVED_BYTES,
    MAX_RECEIVED_LINES,
    MAX_SENT_BYTES,
    MAX_SENT_LINES,
)


class S13NonissuanceRejected(ValueError):
    """The captured source cannot qualify an S-owned nonissued interval."""


@dataclass(frozen=True, slots=True)
class S13NonissuedReview:
    classification: str
    session_id: str
    target_entity_id: int
    pre_seq: int
    post_seq: int
    elapsed_world_ticks: int
    health_before: float
    health_after: float
    food_before: float
    food_after: float
    before_position: tuple[float, float, float]
    after_position: tuple[float, float, float]
    received_original_sha256: str
    sent_original_sha256: str
    sent_observes: int
    sent_effects: int = 0
    s16_action_receipt_created: bool = False
    external_goal_attested: bool = False
    world_goal_success_claimed: bool = False
    independently_authenticated_minecraft_tcp: bool = False
    external_actor_silence_proven: bool = False
    action_authority: bool = False
    new_physical_runs: int = 0
    science_qualified: bool = False


def _bounded_jsonl(raw: bytes, *, incoming: bool) -> tuple[str, ...]:
    size_limit = MAX_RECEIVED_BYTES if incoming else MAX_SENT_BYTES
    lines_limit = MAX_RECEIVED_LINES if incoming else MAX_SENT_LINES
    if (
        not isinstance(raw, bytes) or not raw or len(raw) > size_limit
        or not raw.endswith(b"\n") or b"\r" in raw
    ):
        raise S13NonissuanceRejected("complete bounded original bridge JSONL required")
    lines = raw.splitlines(keepends=True)
    if not 1 <= len(lines) <= lines_limit or any(
        not item.endswith(b"\n") or not 0 < len(item) <= 1024 * 1024
        for item in lines
    ):
        raise S13NonissuanceRejected("complete untruncated original line bound required")
    try:
        return tuple(line.decode("utf-8") for line in lines)
    except UnicodeDecodeError as exc:
        raise S13NonissuanceRejected("original stream was not UTF-8") from exc


def _read_incoming(raw: bytes):
    decoder = MineflayerStreamDecoder()
    messages = []
    for line in _bounded_jsonl(raw, incoming=True):
        messages.append(decoder.decode(line))
    if (
        len(messages) < 5
        or not isinstance(messages[0], MineflayerAdapterStarted)
        or not isinstance(messages[-1], MineflayerShutdownAck)
        or any(isinstance(x, (
            MineflayerAdapterErrorMessage, MineflayerCommandError,
            MineflayerEffectResult, MineflayerEntityHurt,
            MineflayerConnectionEnd,
        )) for x in messages)
        or sum(isinstance(x, MineflayerShutdownAck) for x in messages) != 1
    ):
        raise S13NonissuanceRejected("startup, complete correlated interval and shutdown ACK required")
    return messages


def _read_outgoing(raw: bytes) -> tuple[str, str]:
    commands = []
    for line in _bounded_jsonl(raw, incoming=False):
        try:
            item = json.loads(line)
        except (ValueError, TypeError) as exc:
            raise S13NonissuanceRejected("unparsable original outbound") from exc
        if not isinstance(item, dict):
            raise S13NonissuanceRejected("non-object original outbound")
        commands.append(item)
    # All captured commands, not just a filtered subrange. No other client
    # or other owner is claimed silent from observing this one owner stream.
    if (
        len(commands) != 3
        or commands[0].get("type") != "observe"
        or commands[1].get("type") != "observe"
        or commands[2] != {"type": "shutdown"}
        or any(set(x) != {"type", "request_id"} for x in commands[:2])
    ):
        raise S13NonissuanceRejected("entire owned stream must contain two probes and shutdown only")
    first, second = (x["request_id"] for x in commands[:2])
    if not all(isinstance(x, str) and x and len(x) <= 128 for x in (first, second)):
        raise S13NonissuanceRejected("two original correlated observe requests required")
    if first == second:
        raise S13NonissuanceRejected("reused original probe request")
    return first, second


def review_nonissued_wait_interval(
    *,
    received_original: bytes,
    sent_original: bytes,
    owner: NormalSessionActionExecutor,
    expected_session_id: str,
    expected_target_id: int,
    min_world_ticks: int = 1,
    max_world_ticks: int = 200,
) -> S13NonissuedReview:
    """Only a bounded synthetic/offline source-shaped owner audit, never a GO.

    For a future *real* original byte study R/V must qualify physical source,
    immutable capture closure, actual World start, possible external actors,
    goal and matched control independently. This class makes none of those
    qualifications merely by receiving bytes or a live owner object.
    """
    if (
        not isinstance(owner, NormalSessionActionExecutor)
        or not isinstance(expected_session_id, str) or not expected_session_id
        or owner.session_id != expected_session_id
        or type(expected_target_id) is not int or expected_target_id < 0
        or type(min_world_ticks) is not int or type(max_world_ticks) is not int
        or not 1 <= min_world_ticks <= max_world_ticks <= 1200
        or owner._count != 0 or owner._dispatched
        or owner.supervisor._lifecycles or owner.supervisor.open_actions
        or owner.intent.current_intent is None
        or owner.intent.pending_reconsideration is not None
    ):
        raise S13NonissuanceRejected("same current S49 owner must have no issued Action")
    try:
        msgs = _read_incoming(received_original)
        pre_id, post_id = _read_outgoing(sent_original)
    except (ValueError, TypeError) as exc:
        raise S13NonissuanceRejected("original native stream not qualified") from exc
    if msgs[0].session_id != expected_session_id:
        raise S13NonissuanceRejected("foreign original session")
    probes = [
        x for x in msgs if isinstance(x, MineflayerObservation)
        and x.kind == "probe" and x.request_id is not None
    ]
    if (
        len(probes) != 2 or [x.request_id for x in probes] != [pre_id, post_id]
        or probes[0].seq >= probes[1].seq
        or any(isinstance(x, MineflayerObservation)
               and x.kind in ("death", "respawn", "forcedMove")
               for x in msgs)
    ):
        raise S13NonissuanceRejected("original pre/post probe order or uninterrupted World scope missing")
    pre, post = probes
    a, b = pre.snapshot, post.snapshot
    if (
        a.nearby_entities_coverage.truncated or b.nearby_entities_coverage.truncated
        or a.time is None or b.time is None
        or a.time.time_of_day >= 24000 or b.time.time_of_day >= 24000
    ):
        raise S13NonissuanceRejected("full native pre/post World and time required")
    before_z = [e for e in a.nearby_entities if e.name == "zombie"]
    after_z = [e for e in b.nearby_entities if e.name == "zombie"]
    if (
        len(before_z) != 1 or len(after_z) != 1
        or before_z[0].entity_id != expected_target_id
        or after_z[0].entity_id != expected_target_id
        or before_z[0].distance > 16 or after_z[0].distance > 16
    ):
        raise S13NonissuanceRejected("same independent bounded native target not present")
    elapsed = (
        b.time.day * 24000 + b.time.time_of_day
        - a.time.day * 24000 - a.time.time_of_day
    )
    if not min_world_ticks <= elapsed <= max_world_ticks:
        raise S13NonissuanceRejected("genuine bounded World tick interval not witnessed")
    return S13NonissuedReview(
        classification="S13_ORIGINAL_SHAPED_NONISSUED_WORLD_INTERVAL_REVIEW_ONLY",
        session_id=expected_session_id,
        target_entity_id=expected_target_id,
        pre_seq=pre.seq, post_seq=post.seq,
        elapsed_world_ticks=elapsed,
        health_before=a.health, health_after=b.health,
        food_before=a.food, food_after=b.food,
        before_position=(a.position.x, a.position.y, a.position.z),
        after_position=(b.position.x, b.position.y, b.position.z),
        received_original_sha256=hashlib.sha256(received_original).hexdigest(),
        sent_original_sha256=hashlib.sha256(sent_original).hexdigest(),
        sent_observes=2,
    )
