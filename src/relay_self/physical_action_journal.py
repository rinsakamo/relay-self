"""Physical ActionPort shared fsynced PRE-ISSUE journal (Cognitive v0.1 DEV).

Adapted from the #767 OriginalS49NonMotionFence/C1MotionJournal durable
write/lock/CAS pattern, without importing S49's L0, Intent or food chooser.
One canonical Self-owned journal file, across all sessions; NEVER an issuer.
An unresolved Action is never automatically retried or cleared on restart.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityHurt,
    MineflayerObservation,
    MineflayerPosition,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.move_destination_ref import move_destination_ref
from relay_self.physical_action_port import PhysicalActionBinding
from relay_self.provenance import Provenance


class PhysicalJournalError(ValueError):
    """A physical reservation is malformed, untrusted or not current."""


class PhysicalJournalUnresolved(PhysicalJournalError):
    """Potentially physical prior Action is UNKNOWN; never auto-retry."""


class PhysicalJournalReplay(PhysicalJournalError):
    """Reused identity, source, conflicting writer or old journal snapshot."""


def _text(value: object) -> str:
    if type(value) is not str or not value or any(x.isspace() for x in value):
        raise PhysicalJournalError("nonblank, whitespace-free identity required")
    return value


def _number(value: object) -> int:
    if type(value) is not int or value < 0:
        raise PhysicalJournalError("nonnegative integer required")
    return value


def _exact(value: object, names: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != names:
        raise PhysicalJournalError("exact persisted fields required")
    return value


_ROW = {
    "session_id", "intent_id", "skill_execution_id", "action_id",
    "capability", "target_ref", "probe_seq", "probe_request_id", "source_ref",
    "status", "effect_seqs", "after_seq", "food_before", "food_after",
    "count_before", "count_after",
}


_MOVE_ROW = _ROW | {"motion"}
_MOVE_MOTION = {
    "destination_id", "destination_source", "destination_reference",
    "start", "target", "progress_seq", "progress",
    "stop_probe_seqs", "stop_probe_positions",
}


def _xyz(value: object) -> tuple[float, float, float]:
    if type(value) is not list or len(value) != 3:
        raise PhysicalJournalError("native XYZ needs three coordinates")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise PhysicalJournalError("non-finite/malformed XYZ")
    return tuple(float(x) for x in value)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _spatial_distance(
    a: tuple[float, float, float], b: tuple[float, float, float],
) -> float:
    return math.dist(a, b)


def _position(position: MineflayerPosition) -> list[float]:
    return [float(position.x), float(position.y), float(position.z)]


def _move_motion(row: dict[str, Any]) -> dict[str, Any]:
    m = _exact(row["motion"], _MOVE_MOTION)
    dest_id = _text(m["destination_id"])
    src = Provenance(_text(m["destination_source"]),
                     _text(m["destination_reference"]))
    start = _xyz(m["start"])
    dest = _xyz(m["target"])
    try:
        ref = move_destination_ref(dest_id, MineflayerPosition(*dest), src)
    except ValueError as exc:
        raise PhysicalJournalError("invalid configured MOVE destination") from exc
    if ref != row["target_ref"]:
        raise PhysicalJournalError("MOVE target ref does not match persisted geometry")
    span = _distance(start, dest)
    if not .4 <= span <= 4 or abs(start[1] - dest[1]) > .25:
        raise PhysicalJournalError("DEV MOVE must be bounded and near-level")
    return m


def _validate(value: object) -> dict[str, Any]:
    body = _exact(value, {"schema", "self_id", "actions"})
    if body["schema"] != 1 or type(body["actions"]) is not list:
        raise PhysicalJournalError("unsupported journal schema")
    _text(body["self_id"])
    seen: set[str] = set()
    max_seq: dict[str, int] = {}
    for idx, entry in enumerate(body["actions"]):
        if type(entry) is not dict:
            raise PhysicalJournalError("persisted physical Action row missing")
        row = _exact(entry, _MOVE_ROW if entry.get("capability") == "MOVE" else _ROW)
        for field in (
            "session_id", "intent_id", "skill_execution_id", "action_id",
            "capability", "target_ref", "probe_request_id", "source_ref",
        ):
            _text(row[field])
        if row["capability"] == "EAT":
            if not row["target_ref"].startswith("inventory:"):
                raise PhysicalJournalError("EAT physical target must be inventory")
        elif row["capability"] == "MOVE":
            _move_motion(row)
        elif row["capability"] == "attack_entity":
            target = row["target_ref"].removeprefix("entity:")
            if (not row["target_ref"].startswith("entity:")
                    or not target.isascii() or not target.isdecimal()
                    or str(int(target)) != target):
                raise PhysicalJournalError("ATTACK needs canonical native entity ID")
        else:
            raise PhysicalJournalError("unregistered native physical capability")
        if row["action_id"] in seen:
            raise PhysicalJournalReplay("physical Action ID replay")
        seen.add(row["action_id"])
        seq = _number(row["probe_seq"])
        session = row["session_id"]
        if row["source_ref"] != f"{session}:{seq}" or seq <= max_seq.get(session, -1):
            raise PhysicalJournalReplay("stale or forged native source")
        if row["status"] == "PREPARED_UNRESOLVED":
            if row["capability"] == "MOVE":
                motion = _move_motion(row)
                if any(motion[k] is not None for k in (
                    "progress_seq", "progress", "stop_probe_seqs",
                    "stop_probe_positions",
                )):
                    raise PhysicalJournalError("unresolved MOVE must lack outcome evidence")
            if idx != len(body["actions"]) - 1 or any(
                row[k] is not None for k in (
                    "effect_seqs", "after_seq", "food_before", "food_after",
                    "count_before", "count_after",
                )
            ):
                raise PhysicalJournalError("unresolved Action must be last with no outcome")
            max_seq[session] = seq
        elif row["status"] == "NATIVE_EAT_OUTCOME":
            if row["capability"] != "EAT":
                raise PhysicalJournalError("EAT terminal capability mismatch")
            effects = row["effect_seqs"]
            if type(effects) is not list or len(effects) != 2:
                raise PhysicalJournalError("two native EAT effects required")
            equip, consume = [_number(x) for x in effects]
            after = _number(row["after_seq"])
            before_food = _number(row["food_before"])
            after_food = _number(row["food_after"])
            before_count = _number(row["count_before"])
            after_count = _number(row["count_after"])
            if not (
                seq < equip < consume < after
                and 0 <= before_food < after_food <= 20
                and before_count >= 1 and 0 <= after_count < before_count
            ):
                raise PhysicalJournalError("EAT native effect/outcome evidence invalid")
            max_seq[session] = after
        elif row["status"] == "NATIVE_MOVE_PROGRESS_STOP_READBACK":
            if row["capability"] != "MOVE":
                raise PhysicalJournalError("MOVE terminal capability mismatch")
            m = _move_motion(row)
            events = row["effect_seqs"]
            if type(events) is not list or len(events) != 3:
                raise PhysicalJournalError("MOVE requires look/forward/STOP ACKs")
            look, forward, stop = [_number(x) for x in events]
            progress_seq = _number(m["progress_seq"])
            progress = _xyz(m["progress"])
            stop_seqs = m["stop_probe_seqs"]
            stop_xyz = m["stop_probe_positions"]
            if (type(stop_seqs) is not list or len(stop_seqs) != 2
                    or type(stop_xyz) is not list or len(stop_xyz) != 2):
                raise PhysicalJournalError("two source-qualified post-stop probes needed")
            first, second = [_number(x) for x in stop_seqs]
            first_position, second_position = [_xyz(x) for x in stop_xyz]
            after = _number(row["after_seq"])
            before = _xyz(m["start"])
            target = _xyz(m["target"])
            if (
                not seq < look < forward < progress_seq < stop < first < second == after
                or _distance(before, target) - _distance(progress, target) < .25
                or _distance(before, progress) < .25
                or _spatial_distance(first_position, second_position) > .05
                or any(row[k] is not None for k in (
                    "food_before", "food_after", "count_before", "count_after",
                ))
            ):
                raise PhysicalJournalError("MOVE progression/STOP observations unqualified")
            max_seq[session] = after
        elif row["status"] == "NATIVE_ATTACK_HURT_CORRELATED":
            if row["capability"] != "attack_entity":
                raise PhysicalJournalError("ATTACK terminal capability mismatch")
            effects = row["effect_seqs"]
            if type(effects) is not list or len(effects) != 2:
                raise PhysicalJournalError("native ACK and hurt event sequences required")
            ack, hurt = [_number(x) for x in effects]
            after = _number(row["after_seq"])
            if (not seq < ack < after or not seq < hurt < after
                    or ack == hurt
                    or any(row[k] is not None for k in (
                        "food_before", "food_after", "count_before", "count_after",
                    ))):
                raise PhysicalJournalError("correlated ATTACK ACK/hurt ordering invalid")
            # Source/actor identity checks occur at the source-qualified close.
            # The journal does not claim Paper damage or kill.
            max_seq[session] = after
        else:
            raise PhysicalJournalError("unknown durable physical status")
    return body


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(body)).hexdigest()


@contextmanager
def _exclusive(path: Path) -> Iterator[None]:
    lock = path.with_name(path.name + ".lock")
    if (
        path.is_symlink() or path.parent.is_symlink() or lock.is_symlink()
        or not path.parent.is_dir()
    ):
        raise PhysicalJournalError("regular pre-existing safe journal directory required")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise PhysicalJournalError("physical lock could not be opened") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise PhysicalJournalError("physical journal lock must be regular")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _write(path: Path, body: dict[str, Any]) -> str:
    digest = _digest(body)
    data = _canonical({"body": body, "sha256": digest}) + b"\n"
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        Path(temp).unlink(missing_ok=True)
    return digest


def _read(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise PhysicalJournalError("existing regular journal required")
    try:
        envelope = _exact(json.loads(path.read_bytes()), {"body", "sha256"})
        body = _validate(envelope["body"])
        digest = _digest(body)
        if envelope["sha256"] != digest:
            raise PhysicalJournalError("physical journal checksum mismatch")
        return body, digest
    except PhysicalJournalError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PhysicalJournalError("cannot trust physical journal") from exc


class PhysicalActionJournal:
    """Self-owned CAS journal. Reservation precedes any physical effect."""

    def __init__(self, path: Path, body: dict[str, Any], digest: str):
        self.path = path
        self._body = body
        self.digest = digest

    @classmethod
    def create(cls, path: str | Path, *, self_id: str) -> PhysicalActionJournal:
        p = Path(path)
        body = _validate({"schema": 1, "self_id": _text(self_id), "actions": []})
        with _exclusive(p):
            if p.exists() or p.is_symlink():
                raise PhysicalJournalReplay("existing physical history must be restored")
            digest = _write(p, body)
        return cls(p, body, digest)

    @classmethod
    def restore(cls, path: str | Path, *, self_id: str) -> PhysicalActionJournal:
        p = Path(path)
        with _exclusive(p):
            body, digest = _read(p)
            if body["self_id"] != _text(self_id):
                raise PhysicalJournalError("foreign Self cannot restore physical history")
        return cls(p, body, digest)

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(x) for x in self._body["actions"])

    @property
    def unresolved(self) -> bool:
        return bool(
            self.records and self.records[-1]["status"] == "PREPARED_UNRESOLVED"
        )

    def require_clear(self) -> None:
        if self.unresolved:
            raise PhysicalJournalUnresolved("possible physical effect: STOP/UNKNOWN")

    def _commit(self, records: list[dict[str, Any]]) -> None:
        updated = _validate({**self._body, "actions": records})
        with _exclusive(self.path):
            old, digest = _read(self.path)
            if digest != self.digest or old != self._body:
                raise PhysicalJournalReplay("physical journal CAS writer conflict")
            new_digest = _write(self.path, updated)
        self._body, self.digest = updated, new_digest

    def prepare_eat(
        self, binding: PhysicalActionBinding, probe: MineflayerObservation,
    ) -> None:
        """fsync PREPARED_UNRESOLVED before supervisor.ISSUED or native IO."""
        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or binding.scope.self_id != self._body["self_id"]
            or binding.skill_id != "EAT"
            or binding.capability_ref != "EAT"
            or binding.target_kind != "FOOD"
            or not binding.target_ref.startswith("inventory:")
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.health <= 0
        ):
            raise PhysicalJournalError("exact EAT binding/native probe required")
        food = binding.target_ref.removeprefix("inventory:")
        if not any(i.name == food and i.count > 0 for i in probe.snapshot.inventory):
            raise PhysicalJournalError("selected food disappeared before reservation")
        self._commit([*self._body["actions"], {
            "session_id": probe.session_id,
            "intent_id": binding.intent_id,
            "skill_execution_id": binding.skill_execution_id,
            "action_id": binding.action_id,
            "capability": "EAT",
            "target_ref": binding.target_ref,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "effect_seqs": None,
            "after_seq": None,
            "food_before": None,
            "food_after": None,
            "count_before": None,
            "count_after": None,
        }])

    def close_eat(
        self, binding: PhysicalActionBinding, before: MineflayerObservation,
        equip: MineflayerEffectResult, consume: MineflayerEffectResult,
        after: MineflayerObservation, terminal: ActionLifecycle,
        supervisor: ActionSupervisor,
    ) -> None:
        """Seal only exact native child ACKs + physical food/inventory readback."""
        if not self.unresolved or not isinstance(binding, PhysicalActionBinding):
            raise PhysicalJournalError("no unresolved original EAT reservation")
        row = self._body["actions"][-1]
        if (
            not isinstance(before, MineflayerObservation)
            or not isinstance(equip, MineflayerEffectResult)
            or not isinstance(consume, MineflayerEffectResult)
            or not isinstance(after, MineflayerObservation)
            or not isinstance(terminal, ActionLifecycle)
            or not isinstance(supervisor, ActionSupervisor)
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["action_id"] != binding.action_id
            or row["target_ref"] != binding.target_ref
            or row["source_ref"] != binding.native_source.reference
            or row["probe_request_id"] != binding.native_request_id
            or before.session_id != row["session_id"]
            or before.seq != row["probe_seq"]
            or before.request_id != row["probe_request_id"]
            or before.provenance != binding.native_source
            or after.session_id != before.session_id
            or after.kind != "probe" or not after.request_id
            or after.request_id == before.request_id
            or after.snapshot.health <= 0
            or equip.session_id != before.session_id
            or consume.session_id != before.session_id
            or equip.action_id != binding.action_id + "-equip"
            or consume.action_id != binding.action_id + "-consume"
            or equip.effect != "equip_item" or consume.effect != "consume_held"
            or equip.result != "applied" or consume.result != "applied"
            or not before.seq < equip.seq < consume.seq < after.seq
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or terminal.intent_id != binding.intent_id
            or terminal.skill_execution_id != binding.skill_execution_id
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("EAT terminal / original native evidence mismatch")
        food = binding.target_ref.removeprefix("inventory:")
        before_count = sum(i.count for i in before.snapshot.inventory if i.name == food)
        after_count = sum(i.count for i in after.snapshot.inventory if i.name == food)
        if (
            before_count < 1 or after_count >= before_count
            or not before.snapshot.food < after.snapshot.food <= 20
        ):
            raise PhysicalJournalError("EAT food/inventory consequence not attested")
        self._commit([*self._body["actions"][:-1], {
            **row,
            "status": "NATIVE_EAT_OUTCOME",
            "effect_seqs": [equip.seq, consume.seq],
            "after_seq": after.seq,
            "food_before": int(before.snapshot.food),
            "food_after": int(after.snapshot.food),
            "count_before": before_count,
            "count_after": after_count,
        }])


    def prepare_attack(
        self, binding: PhysicalActionBinding, probe: MineflayerObservation,
    ) -> None:
        """Reserve one selected ATTACK before supervisor.ISSUED/native write."""
        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or binding.scope.self_id != self._body["self_id"]
            or binding.skill_id != "ATTACK" or binding.skill_version != 1
            or binding.capability_ref != "attack_entity"
            or binding.capability_version != 1
            or binding.target_kind != "ZOMBIE"
            or binding.body_channel != "hand"
            or not binding.target_ref.startswith("entity:")
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.health <= 0
            or probe.snapshot.oxygen_level == 0
        ):
            raise PhysicalJournalError("exact ATTACK parent/native source required")
        target = binding.target_ref.removeprefix("entity:")
        if not target.isascii() or not target.isdecimal() or str(int(target)) != target:
            raise PhysicalJournalError("malformed runtime attack entity ID")
        coverage = probe.snapshot.nearby_entities_coverage
        if (
            coverage.truncated or coverage.candidate_count != 1
            or len(probe.snapshot.nearby_entities) != 1
            or probe.snapshot.nearby_entities[0].entity_id != int(target)
            or probe.snapshot.nearby_entities[0].name != "zombie"
        ):
            raise PhysicalJournalError("source-qualified selected zombie absent")
        self._commit([*self._body["actions"], {
            "session_id": probe.session_id,
            "intent_id": binding.intent_id,
            "skill_execution_id": binding.skill_execution_id,
            "action_id": binding.action_id,
            "capability": "attack_entity",
            "target_ref": binding.target_ref,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "effect_seqs": None,
            "after_seq": None,
            "food_before": None,
            "food_after": None,
            "count_before": None,
            "count_after": None,
        }])

    def close_attack(
        self, binding: PhysicalActionBinding, before: MineflayerObservation,
        ack: MineflayerEffectResult, hurt: MineflayerEntityHurt,
        after: MineflayerObservation, terminal: ActionLifecycle,
        supervisor: ActionSupervisor,
    ) -> None:
        """Close *correlated native hurt*, not independently proven damage."""
        if not self.unresolved or not isinstance(binding, PhysicalActionBinding):
            raise PhysicalJournalError("no unresolved original ATTACK reservation")
        row = self._body["actions"][-1]
        target_id = int(binding.target_ref.removeprefix("entity:"))
        if (
            not isinstance(before, MineflayerObservation)
            or not isinstance(ack, MineflayerEffectResult)
            or not isinstance(hurt, MineflayerEntityHurt)
            or not isinstance(after, MineflayerObservation)
            or not isinstance(terminal, ActionLifecycle)
            or not isinstance(supervisor, ActionSupervisor)
            or row["capability"] != "attack_entity"
            or row["action_id"] != binding.action_id
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["target_ref"] != binding.target_ref
            or row["source_ref"] != binding.native_source.reference
            or before.session_id != row["session_id"]
            or before.seq != row["probe_seq"]
            or before.request_id != row["probe_request_id"]
            or before.provenance != binding.native_source
            or ack.session_id != before.session_id
            or ack.action_id != binding.action_id + "-attack"
            or ack.effect != "attack_entity" or ack.result != "applied"
            or hurt.session_id != before.session_id
            or hurt.entity_id != target_id
            or hurt.source_entity_id is None
            or hurt.source_entity_id != hurt.actor_entity_id
            or hurt.actor_entity_id == target_id
            or not before.seq < ack.seq < after.seq
            or not before.seq < hurt.seq < after.seq
            or ack.seq == hurt.seq
            or after.session_id != before.session_id
            or after.kind != "probe"
            or after.request_id != binding.action_id + "-after-attack-00"
            or after.snapshot.health <= 0
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or terminal.intent_id != binding.intent_id
            or terminal.skill_execution_id != binding.skill_execution_id
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("ATTACK native ACK/hurt source not correlated")
        self._commit([*self._body["actions"][:-1], {
            **row,
            "status": "NATIVE_ATTACK_HURT_CORRELATED",
            "effect_seqs": [ack.seq, hurt.seq],
            "after_seq": after.seq,
        }])


    def prepare_move(
        self, binding: PhysicalActionBinding, probe: MineflayerObservation,
        *, destination_id: str, destination: MineflayerPosition,
        destination_source: Provenance,
    ) -> None:
        """fsync a bounded source/geometry-bound MOVE before any motor IO."""
        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or binding.scope.self_id != self._body["self_id"]
            or binding.skill_id != "MOVE" or binding.skill_version != 1
            or binding.capability_ref != "MOVE" or binding.capability_version != 1
            or binding.target_kind != "DESTINATION"
            or binding.body_channel != "movement"
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.health <= 0 or probe.snapshot.oxygen_level == 0
            or not isinstance(destination, MineflayerPosition)
            or not isinstance(destination_source, Provenance)
            or move_destination_ref(
                destination_id, destination, destination_source,
            ) != binding.target_ref
        ):
            raise PhysicalJournalError("exact bounded MOVE/native target required")
        motion = {
            "destination_id": destination_id,
            "destination_source": destination_source.source,
            "destination_reference": destination_source.reference,
            "start": _position(probe.snapshot.position),
            "target": _position(destination),
            "progress_seq": None,
            "progress": None,
            "stop_probe_seqs": None,
            "stop_probe_positions": None,
        }
        row = {
            "session_id": probe.session_id,
            "intent_id": binding.intent_id,
            "skill_execution_id": binding.skill_execution_id,
            "action_id": binding.action_id,
            "capability": "MOVE",
            "target_ref": binding.target_ref,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "effect_seqs": None,
            "after_seq": None,
            "food_before": None,
            "food_after": None,
            "count_before": None,
            "count_after": None,
            "motion": motion,
        }
        self._commit([*self._body["actions"], row])

    def close_move(
        self, binding: PhysicalActionBinding, before: MineflayerObservation,
        look: MineflayerEffectResult, forward: MineflayerEffectResult,
        progress: MineflayerObservation, stop: MineflayerEffectResult,
        first_stop: MineflayerObservation, final_stop: MineflayerObservation,
        terminal: ActionLifecycle, supervisor: ActionSupervisor,
    ) -> None:
        """Close only observed progress and two post-STOP stable native probes.

        This is NOT a Paper tick settling attestation, obstacle clearance or
        arrival at destination. Failures leave the original WAL unresolved.
        """
        if not self.unresolved:
            raise PhysicalJournalError("no unresolved bounded MOVE reservation")
        row = self._body["actions"][-1]
        if not isinstance(binding, PhysicalActionBinding) or row["capability"] != "MOVE":
            raise PhysicalJournalError("no original MOVE parent to close")
        if (
            not isinstance(before, MineflayerObservation)
            or not isinstance(progress, MineflayerObservation)
            or not isinstance(first_stop, MineflayerObservation)
            or not isinstance(final_stop, MineflayerObservation)
            or not all(isinstance(x, MineflayerEffectResult) for x in (
                look, forward, stop,
            ))
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["action_id"] != binding.action_id
            or row["target_ref"] != binding.target_ref
            or row["source_ref"] != binding.native_source.reference
            or before.session_id != row["session_id"]
            or before.seq != row["probe_seq"]
            or before.request_id != row["probe_request_id"]
            or before.provenance != binding.native_source
            or any(
                msg.session_id != before.session_id
                for msg in (look, forward, progress, stop, first_stop, final_stop)
            )
            or any(
                (msg.action_id, msg.effect, msg.result) != (
                    binding.action_id + "-"+name, effect, "applied",
                )
                for msg, name, effect in (
                    (look, "look", "look"),
                    (forward, "forward", "set_control"),
                    (stop, "stop", "clear_controls"),
                )
            )
            or progress.kind != "move"
            or any(
                msg.kind != "probe" or msg.request_id != request_id
                or msg.snapshot.health <= 0
                for msg, request_id in (
                    (first_stop, binding.action_id + "-after-stop-00"),
                    (final_stop, binding.action_id + "-after-stop-01"),
                )
            )
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or terminal.intent_id != binding.intent_id
            or terminal.skill_execution_id != binding.skill_execution_id
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("MOVE original native Action/window mismatch")
        m = {
            **row["motion"],
            "progress_seq": progress.seq,
            "progress": _position(progress.snapshot.position),
            "stop_probe_seqs": [first_stop.seq, final_stop.seq],
            "stop_probe_positions": [
                _position(first_stop.snapshot.position),
                _position(final_stop.snapshot.position),
            ],
        }
        self._commit([*self._body["actions"][:-1], {
            **row,
            "status": "NATIVE_MOVE_PROGRESS_STOP_READBACK",
            "effect_seqs": [look.seq, forward.seq, stop.seq],
            "after_seq": final_stop.seq,
            "motion": m,
        }])
