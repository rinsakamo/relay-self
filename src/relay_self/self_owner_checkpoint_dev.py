"""#860 P0-D: typed bounded Self owner checkpoint and multi-Self exchange cut.

PersistentCognition remains its own owner/file. This encodes currently implemented
IntentCommitment, SkillExecution, learned PatternRegistry and completed peer
exchange receipts. NOT a complete cognitive resurrection: no WorldBody, L0
commands, GPU KV, communication transport or unmerged 3Self Recent owner.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    PatternRegistry,
    Predicate,
    SchemaPattern,
)
from relay_self.intent import (
    IntentCommitment,
    IntentEvent,
    IntentEventKind,
    ReconsiderationDecision,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillEvent, SkillExecution, SkillState


class SelfOwnerCheckpointError(ValueError):
    """Refuse ambiguous/malformed/unmatched owner cut or foreign peer message."""


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise SelfOwnerCheckpointError(f"{name} must be nonempty text")
    return value


def _nat(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise SelfOwnerCheckpointError(f"{name} must be nonnegative integer")
    return value


def _exact(value: object, keys: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SelfOwnerCheckpointError(f"{name} requires exact fields")
    return value


def _provenance(provenance: Provenance) -> dict[str, str]:
    return {"source": provenance.source, "reference": provenance.reference}


def _read_provenance(value: object) -> Provenance:
    fields = _exact(value, {"source", "reference"}, "provenance")
    return Provenance(_text(fields["source"], "source"), _text(fields["reference"], "reference"))


@dataclass(frozen=True, slots=True)
class PeerDelivery:
    """Immutable *completed* delivery, never a queued transport command."""

    message_id: str
    sender_self_id: str
    recipient_self_id: str
    sent_world_tick: int
    received_world_tick: int
    payload_ref: str

    def __post_init__(self) -> None:
        for name in ("message_id", "sender_self_id", "recipient_self_id", "payload_ref"):
            _text(getattr(self, name), name)
        if self.sender_self_id == self.recipient_self_id:
            raise SelfOwnerCheckpointError("self-to-self message is not a peer delivery")
        _nat(self.sent_world_tick, "send tick")
        _nat(self.received_world_tick, "receive tick")
        if self.received_world_tick < self.sent_world_tick:
            raise SelfOwnerCheckpointError("receive precedes send")


@dataclass(frozen=True, slots=True)
class SelfOwnerCut:
    """One quiesced Self's typed owner history, not physical Action permission."""

    generation_id: str
    self_id: str
    world_id: str
    branch_id: str
    former_native_session_id: str
    last_observed_world_tick: int
    intent_events: tuple[IntentEvent, ...]
    skill_executions: tuple[SkillExecution, ...]
    pattern_registry: PatternRegistry
    peer_deliveries: tuple[PeerDelivery, ...] = ()
    pending_question_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("generation_id", "self_id", "world_id", "branch_id",
                     "former_native_session_id"):
            _text(getattr(self, name), name)
        _nat(self.last_observed_world_tick, "last observed tick")
        if type(self.intent_events) is not tuple or any(
            not isinstance(e, IntentEvent) for e in self.intent_events
        ):
            raise SelfOwnerCheckpointError("typed Intent events required")
        if type(self.skill_executions) is not tuple or any(
            not isinstance(s, SkillExecution) or not s.is_current_snapshot
            for s in self.skill_executions
        ):
            raise SelfOwnerCheckpointError("only current Skill histories may be saved")
        if type(self.pattern_registry) is not PatternRegistry:
            raise SelfOwnerCheckpointError("typed learned Schema registry required")
        if (type(self.peer_deliveries) is not tuple
                or any(type(m) is not PeerDelivery for m in self.peer_deliveries)):
            raise SelfOwnerCheckpointError("typed peer delivery receipts required")
        if type(self.pending_question_refs) is not tuple or any(
            type(q) is not str or not q.strip() for q in self.pending_question_refs
        ):
            raise SelfOwnerCheckpointError("typed pending Question references required")
        if len(set(self.pending_question_refs)) != len(self.pending_question_refs):
            raise SelfOwnerCheckpointError("duplicate pending Question")
        if len({x.execution_id for x in self.skill_executions}) != len(self.skill_executions):
            raise SelfOwnerCheckpointError("duplicate Skill execution")
        if len({x.message_id for x in self.peer_deliveries}) != len(self.peer_deliveries):
            raise SelfOwnerCheckpointError("duplicate peer message in one Self")
        for m in self.peer_deliveries:
            if self.self_id not in (m.sender_self_id, m.recipient_self_id):
                raise SelfOwnerCheckpointError("foreign peer exchange")
            if m.received_world_tick > self.last_observed_world_tick:
                raise SelfOwnerCheckpointError("peer receipt after saved Self tick")
        owner = _replay_intent(self.intent_events)
        committed = {
            e.intent_id: e.at_ns for e in owner.events
            if e.kind is IntentEventKind.COMMITTED
        }
        for skill in self.skill_executions:
            if (skill.intent_id not in committed
                    or skill.events[0].at_ns < committed[skill.intent_id]):
                raise SelfOwnerCheckpointError("Skill history lacks earlier committed Intent")


def _replay_intent(events: tuple[IntentEvent, ...]) -> IntentCommitment:
    """Reconstruct via existing real owner methods; reject impossible timelines."""
    owner = IntentCommitment()
    try:
        for e in events:
            kw = {"reason": e.reason, "at_ns": e.at_ns, "provenance": e.provenance}
            if e.kind is IntentEventKind.COMMITTED:
                owner.commit(e.intent_id, objective=e.objective, at_ns=e.at_ns,
                             provenance=e.provenance)
            elif e.kind is IntentEventKind.RECONSIDERATION_REQUESTED:
                owner.request_reconsideration(e.intent_id, **kw)
            elif e.kind in (
                IntentEventKind.RECONSIDERED_CONTINUE,
                IntentEventKind.RECONSIDERED_RELEASE,
            ):
                decision = (
                    ReconsiderationDecision.CONTINUE
                    if e.kind is IntentEventKind.RECONSIDERED_CONTINUE
                    else ReconsiderationDecision.RELEASE
                )
                owner.reconsider(e.intent_id, decision=decision, **kw)
            elif e.kind is IntentEventKind.COMPLETED:
                owner.complete(e.intent_id, **kw)
            elif e.kind is IntentEventKind.FAILED:
                owner.fail(e.intent_id, **kw)
            else:
                owner.invalidate(e.intent_id, **kw)
    except ValueError as exc:
        raise SelfOwnerCheckpointError("invalid historical Intent transition") from exc
    if owner.events != events:
        raise SelfOwnerCheckpointError("Intent event replay changed accepted history")
    return owner


def _serialize(cut: SelfOwnerCut) -> dict[str, Any]:
    return {
        "schema": 1,
        "generation_id": cut.generation_id, "self_id": cut.self_id,
        "world_id": cut.world_id, "branch_id": cut.branch_id,
        "former_native_session_id": cut.former_native_session_id,
        "last_observed_world_tick": cut.last_observed_world_tick,
        "intent_events": [
            {
                "kind": e.kind.value, "intent_id": e.intent_id,
                "objective": e.objective, "reason": e.reason, "at_ns": e.at_ns,
                "provenance": _provenance(e.provenance),
            } for e in cut.intent_events
        ],
        "skills": [
            {
                "execution_id": s.execution_id, "skill_id": s.skill_id,
                "intent_id": s.intent_id,
                "events": [
                    {
                        "state": e.state.value, "at_ns": e.at_ns,
                        "reason": e.reason, "provenance": _provenance(e.provenance),
                    } for e in s.events
                ],
            } for s in cut.skill_executions
        ],
        "pattern_registry": {
            "revision": cut.pattern_registry.revision,
            "patterns": [
                {
                    "pattern_id": p.pattern_id, "version": p.version,
                    "schema_id": p.schema_id, "kind": p.kind.value,
                    "predicate": p.predicate.value, "goal_id": p.goal_id,
                    "skill_id": p.skill_id, "skill_version": p.skill_version,
                    "target_kind": p.target_kind, "origin": p.origin.value,
                    "provenance": _provenance(p.provenance),
                } for p in cut.pattern_registry.patterns
            ],
        },
        "peer_deliveries": [
            {
                "message_id": m.message_id, "sender_self_id": m.sender_self_id,
                "recipient_self_id": m.recipient_self_id,
                "sent_world_tick": m.sent_world_tick,
                "received_world_tick": m.received_world_tick,
                "payload_ref": m.payload_ref,
            } for m in cut.peer_deliveries
        ],
        "pending_question_refs": list(cut.pending_question_refs),
    }


def _read_skill(value: object) -> SkillExecution:
    s = _exact(value, {"execution_id", "skill_id", "intent_id", "events"}, "Skill")
    events: list[SkillEvent] = []
    if type(s["events"]) is not list or not s["events"]:
        raise SelfOwnerCheckpointError("Skill events required")
    for raw in s["events"]:
        e = _exact(raw, {"state", "at_ns", "reason", "provenance"}, "Skill event")
        events.append(SkillEvent(
            SkillState(e["state"]), _nat(e["at_ns"], "skill time"),
            _read_provenance(e["provenance"]), e["reason"],
        ))
    result = SkillExecution(
        execution_id=_text(s["execution_id"], "execution id"),
        skill_id=_text(s["skill_id"], "skill id"),
        intent_id=_text(s["intent_id"], "Skill Intent id"),
        _events=(events[0],),
    )
    for e in events[1:]:
        kw = {"reason": e.reason, "at_ns": e.at_ns, "provenance": e.provenance}
        if e.state is SkillState.SUCCEEDED:
            result = result.succeed(**kw)
        elif e.state is SkillState.FAILED:
            result = result.fail(**kw)
        elif e.state is SkillState.CANCELLED:
            result = result.cancel(**kw)
        else:
            raise SelfOwnerCheckpointError("Skill cannot start twice")
    if result.events != tuple(events) or not result.is_current_snapshot:
        raise SelfOwnerCheckpointError("Skill did not round-trip")
    return result


def _deserialize(value: object) -> SelfOwnerCut:
    payload = _exact(value, {
        "schema", "generation_id", "self_id", "world_id", "branch_id",
        "former_native_session_id", "last_observed_world_tick", "intent_events",
        "skills", "pattern_registry", "peer_deliveries", "pending_question_refs",
    }, "owner snapshot")
    if type(payload["schema"]) is not int or payload["schema"] != 1:
        raise SelfOwnerCheckpointError("unsupported owner checkpoint schema")
    try:
        if any(type(payload[k]) is not list for k in (
            "intent_events", "skills", "peer_deliveries", "pending_question_refs"
        )):
            raise SelfOwnerCheckpointError("owner record arrays required")
        intent_events = []
        for raw in payload["intent_events"]:
            e = _exact(raw, {
                "kind", "intent_id", "objective", "reason", "at_ns", "provenance",
            }, "Intent event")
            intent_events.append(IntentEvent(
                IntentEventKind(e["kind"]), _text(e["intent_id"], "intent id"),
                _nat(e["at_ns"], "Intent time"), _read_provenance(e["provenance"]),
                e["objective"], e["reason"],
            ))
        registry = _exact(payload["pattern_registry"], {
            "revision", "patterns",
        }, "pattern registry")
        if type(registry["patterns"]) is not list:
            raise SelfOwnerCheckpointError("pattern list required")
        patterns = []
        for raw in registry["patterns"]:
            p = _exact(raw, {
                "pattern_id", "version", "schema_id", "kind", "predicate",
                "goal_id", "skill_id", "skill_version", "target_kind", "origin",
                "provenance",
            }, "Schema pattern")
            patterns.append(SchemaPattern(
                pattern_id=p["pattern_id"], version=p["version"],
                schema_id=p["schema_id"], kind=PatternKind(p["kind"]),
                predicate=Predicate(p["predicate"]), goal_id=p["goal_id"],
                skill_id=p["skill_id"], skill_version=p["skill_version"],
                target_kind=p["target_kind"], origin=Origin(p["origin"]),
                provenance=_read_provenance(p["provenance"]),
            ))
        peers = []
        for raw in payload["peer_deliveries"]:
            m = _exact(raw, {
                "message_id", "sender_self_id", "recipient_self_id",
                "sent_world_tick", "received_world_tick", "payload_ref",
            }, "peer receipt")
            peers.append(PeerDelivery(**m))
        return SelfOwnerCut(
            generation_id=payload["generation_id"],
            self_id=payload["self_id"], world_id=payload["world_id"],
            branch_id=payload["branch_id"],
            former_native_session_id=payload["former_native_session_id"],
            last_observed_world_tick=_nat(
                payload["last_observed_world_tick"], "observed tick"
            ),
            intent_events=tuple(intent_events),
            skill_executions=tuple(_read_skill(s) for s in payload["skills"]),
            pattern_registry=PatternRegistry(
                _nat(registry["revision"], "registry revision"), tuple(patterns),
            ),
            peer_deliveries=tuple(peers),
            pending_question_refs=tuple(payload["pending_question_refs"]),
        )
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        if isinstance(exc, SelfOwnerCheckpointError):
            raise
        raise SelfOwnerCheckpointError("invalid typed Self owner checkpoint") from exc


def _bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def save_self_owner_cut(path: Path, cut: SelfOwnerCut) -> None:
    """Exclusive fsynced generation file, no silent overwrite of old cognition."""
    if not isinstance(cut, SelfOwnerCut):
        raise SelfOwnerCheckpointError("typed owner cut required")
    path = Path(path)
    if path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
        raise SelfOwnerCheckpointError("unsafe owner checkpoint parent")
    payload = _serialize(cut)
    digest = hashlib.sha256(_bytes(payload)).hexdigest()
    data = _bytes({"payload": payload, "sha256": digest})
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(data)
        while view:
            length = os.write(fd, view)
            if length <= 0:
                raise SelfOwnerCheckpointError("short owner snapshot write")
            view = view[length:]
        os.fsync(fd)
    finally:
        os.close(fd)
    fd_dir = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd_dir)
    finally:
        os.close(fd_dir)


def load_self_owner_cut(path: Path) -> SelfOwnerCut:
    """Read-only digest AND semantic validation; never reissues an old Action."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SelfOwnerCheckpointError("typed owner snapshot unavailable")
    try:
        envelope = _exact(json.loads(path.read_bytes()), {
            "payload", "sha256",
        }, "owner checkpoint envelope")
        digest = hashlib.sha256(_bytes(envelope["payload"])).hexdigest()
        if envelope["sha256"] != digest:
            raise SelfOwnerCheckpointError("owner checkpoint digest mismatch")
        return _deserialize(envelope["payload"])
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        if isinstance(exc, SelfOwnerCheckpointError):
            raise
        raise SelfOwnerCheckpointError("invalid owner checkpoint bytes") from exc


def verify_peer_cohort(
    cuts: tuple[SelfOwnerCut, ...], *, generation_id: str,
    world_id: str, branch_id: str,
) -> None:
    """All delivered messages must occur at sender AND receiver in one cut."""
    roster = {c.self_id for c in cuts}
    if not cuts or len(roster) != len(cuts):
        raise SelfOwnerCheckpointError("missing/duplicate Self owner in cohort")
    sessions = {c.former_native_session_id for c in cuts}
    if len(sessions) != len(cuts):
        raise SelfOwnerCheckpointError("duplicate native session in cohort")
    messages: dict[str, tuple[PeerDelivery, set[str]]] = {}
    for c in cuts:
        if (c.generation_id != generation_id
                or c.world_id != world_id or c.branch_id != branch_id):
            raise SelfOwnerCheckpointError("foreign World/generation owner")
        for msg in c.peer_deliveries:
            if {msg.sender_self_id, msg.recipient_self_id} - roster:
                raise SelfOwnerCheckpointError("peer outside checkpoint roster")
            if msg.message_id not in messages:
                messages[msg.message_id] = (msg, set())
            first, witnesses = messages[msg.message_id]
            if first != msg or c.self_id in witnesses:
                raise SelfOwnerCheckpointError("inconsistent peer exchange identity")
            witnesses.add(c.self_id)
    for msg, witnesses in messages.values():
        if witnesses != {msg.sender_self_id, msg.recipient_self_id}:
            raise SelfOwnerCheckpointError("unpaired peer delivery across Self cuts")


@dataclass(frozen=True, slots=True)
class RehydratedSelfOwner:
    """Inert ready-for-reevaluation owner state, NOT an Action-port grant."""

    cut: SelfOwnerCut
    intent: IntentCommitment
    skill_histories: tuple[SkillExecution, ...]
    pattern_registry: PatternRegistry
    old_native_session_invalid: bool = True
    old_skill_resume_authorized: bool = False
    old_message_redelivery_authorized: bool = False
    new_physical_action_issue_authorized: bool = False


def rehydrate_self_owner(cut: SelfOwnerCut) -> RehydratedSelfOwner:
    """Materialize owners for a NEW branch; no Skill or Intent gets issued."""
    if not isinstance(cut, SelfOwnerCut):
        raise SelfOwnerCheckpointError("typed owner cut required")
    return RehydratedSelfOwner(
        cut=cut, intent=_replay_intent(cut.intent_events),
        skill_histories=tuple(_read_skill({
            "execution_id": skill.execution_id, "skill_id": skill.skill_id,
            "intent_id": skill.intent_id,
            "events": [{
                "state": e.state.value, "at_ns": e.at_ns,
                "reason": e.reason, "provenance": _provenance(e.provenance),
            } for e in skill.events],
        }) for skill in cut.skill_executions),
        pattern_registry=cut.pattern_registry,
    )
