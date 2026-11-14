"""Physical ActionPort fsynced PRE-ISSUE journal (Cognitive v0.1, EAT DEV).

Adapted from the #767 OriginalS49NonMotionFence/C1MotionJournal durable
write/lock/CAS pattern, without importing S49's L0, Intent or food chooser.
One canonical Self-owned journal file, across all sessions; NEVER an issuer.
An unresolved Action is never automatically retried or cleared on restart.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
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
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.physical_action_port import PhysicalActionBinding


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
_ATTACK_FIELDS = {"target_entity_id", "hurt_seq", "source_entity_id", "actor_entity_id"}


def _validate(value: object) -> dict[str, Any]:
    body = _exact(value, {"schema", "self_id", "actions"})
    if body["schema"] != 1 or type(body["actions"]) is not list:
        raise PhysicalJournalError("unsupported journal schema")
    _text(body["self_id"])
    seen: set[str] = set()
    max_seq: dict[str, int] = {}
    for idx, entry in enumerate(body["actions"]):
        if type(entry) is not dict:
            raise PhysicalJournalError("physical journal row must be mapping")
        row = _exact(entry, _ROW | _ATTACK_FIELDS if entry.get("capability") == "ATTACK"
                     else _ROW)
        for field in (
            "session_id", "intent_id", "skill_execution_id", "action_id",
            "capability", "target_ref", "probe_request_id", "source_ref",
        ):
            _text(row[field])
        if row["capability"] == "EAT":
            if not row["target_ref"].startswith("inventory:"):
                raise PhysicalJournalError("invalid EAT target reference")
        elif row["capability"] == "ATTACK":
            ref = row["target_ref"]
            if (
                type(ref) is not str or not ref.startswith("entity:")
                or not ref.removeprefix("entity:").isascii()
                or not ref.removeprefix("entity:").isdecimal()
                or str(int(ref.removeprefix("entity:"))) != ref.removeprefix("entity:")
                or row["target_entity_id"] != int(ref.removeprefix("entity:"))
            ):
                raise PhysicalJournalError("invalid ATTACK target identity")
            _number(row["target_entity_id"])
        else:
            raise PhysicalJournalError("unknown physical Action capability")
        if row["action_id"] in seen:
            raise PhysicalJournalReplay("physical Action ID replay")
        seen.add(row["action_id"])
        seq = _number(row["probe_seq"])
        session = row["session_id"]
        if row["source_ref"] != f"{session}:{seq}" or seq <= max_seq.get(session, -1):
            raise PhysicalJournalReplay("stale or forged native source")
        if row["status"] == "PREPARED_UNRESOLVED":
            if idx != len(body["actions"]) - 1 or any(
                row[k] is not None for k in (
                    "effect_seqs", "after_seq", "food_before", "food_after",
                    "count_before", "count_after",
                )
            ):
                raise PhysicalJournalError("unresolved Action must be last with no outcome")
            if row["capability"] == "ATTACK" and any(
                row[k] is not None for k in
                ("hurt_seq", "source_entity_id", "actor_entity_id")
            ):
                raise PhysicalJournalError("unresolved ATTACK cannot claim a hurt event")
            max_seq[session] = seq
        elif row["status"] == "NATIVE_EAT_OUTCOME" and row["capability"] == "EAT":
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
        elif (
            row["status"] == "NATIVE_ATTACK_HURT_OBSERVED"
            and row["capability"] == "ATTACK"
        ):
            effects = row["effect_seqs"]
            if type(effects) is not list or len(effects) != 1:
                raise PhysicalJournalError("one native ATTACK ACK required")
            ack_seq = _number(effects[0])
            hurt_seq = _number(row["hurt_seq"])
            after = _number(row["after_seq"])
            source_id = _number(row["source_entity_id"])
            actor_id = _number(row["actor_entity_id"])
            target_id = _number(row["target_entity_id"])
            if (
                not seq < min(ack_seq, hurt_seq)
                or max(ack_seq, hurt_seq) >= after
                or source_id != actor_id or target_id == actor_id
                or any(row[k] is not None for k in
                       ("food_before", "food_after", "count_before", "count_after"))
            ):
                raise PhysicalJournalError("ATTACK attributed hurt evidence invalid")
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
        """Durably reserve the same Self-owned physical WAL, before native ATTACK."""
        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or binding.scope.self_id != self._body["self_id"]
            or binding.skill_id != "ATTACK" or binding.skill_version != 1
            or binding.capability_ref != "ATTACK" or binding.capability_version != 1
            or binding.target_kind != "ZOMBIE" or binding.body_channel != "hand"
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.health <= 0 or probe.snapshot.oxygen_level == 0
        ):
            raise PhysicalJournalError("exact ATTACK binding/native source required")
        ref = binding.target_ref
        if (
            not ref.startswith("entity:")
            or not ref.removeprefix("entity:").isascii()
            or not ref.removeprefix("entity:").isdecimal()
        ):
            raise PhysicalJournalError("ATTACK target reference malformed")
        target_id = int(ref.removeprefix("entity:"))
        if str(target_id) != ref.removeprefix("entity:"):
            raise PhysicalJournalError("noncanonical ATTACK entity ID")
        coverage = probe.snapshot.nearby_entities_coverage
        entity = probe.snapshot.nearby_entities
        if (
            coverage.truncated or coverage.candidate_count != 1
            or len(entity) != 1 or entity[0].entity_id != target_id
            or entity[0].name != "zombie"
            or not 0.1 <= entity[0].distance <= 2.8
        ):
            raise PhysicalJournalError("ATTACK target not isolated and in range")
        if self.records and (
            self.records[-1]["session_id"] == probe.session_id
            and self.records[-1]["after_seq"] >= probe.seq
        ):
            raise PhysicalJournalReplay("ATTACK native source was already consumed")
        self._commit([*self._body["actions"], {
            "session_id": probe.session_id,
            "intent_id": binding.intent_id,
            "skill_execution_id": binding.skill_execution_id,
            "action_id": binding.action_id,
            "capability": "ATTACK",
            "target_ref": binding.target_ref,
            "target_entity_id": target_id,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "effect_seqs": None,
            "hurt_seq": None,
            "source_entity_id": None,
            "actor_entity_id": None,
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
        """Seal only correlated source-attributed hurt + applied ACK, not damage."""
        if (
            not self.unresolved or not isinstance(binding, PhysicalActionBinding)
            or not isinstance(before, MineflayerObservation)
            or not isinstance(ack, MineflayerEffectResult)
            or not isinstance(hurt, MineflayerEntityHurt)
            or not isinstance(after, MineflayerObservation)
            or not isinstance(terminal, ActionLifecycle)
            or not isinstance(supervisor, ActionSupervisor)
        ):
            raise PhysicalJournalError("ATTACK terminal evidence absent")
        row = self._body["actions"][-1]
        if (
            row["capability"] != "ATTACK"
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["action_id"] != binding.action_id
            or row["target_ref"] != binding.target_ref
            or row["source_ref"] != binding.native_source.reference
            or row["probe_seq"] != before.seq
            or row["probe_request_id"] != before.request_id
            or before.session_id != row["session_id"]
            or before.provenance != binding.native_source
            or ack.session_id != before.session_id
            or ack.action_id != binding.action_id + "-attack"
            or ack.effect != "attack_entity" or ack.result != "applied"
            or hurt.session_id != before.session_id
            or hurt.entity_id != row["target_entity_id"]
            or hurt.source_entity_id is None
            or hurt.source_entity_id != hurt.actor_entity_id
            or hurt.actor_entity_id == hurt.entity_id
            or after.kind != "probe" or not after.request_id
            or after.request_id == before.request_id
            or after.session_id != before.session_id
            or after.snapshot.health <= 0
            or not before.seq < min(ack.seq, hurt.seq)
            or not max(ack.seq, hurt.seq) < after.seq
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or terminal.intent_id != binding.intent_id
            or terminal.skill_execution_id != binding.skill_execution_id
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("ATTACK ACK/hurt/Outcome source mismatch")
        self._commit([*self._body["actions"][:-1], {
            **row,
            "status": "NATIVE_ATTACK_HURT_OBSERVED",
            "effect_seqs": [ack.seq],
            "hurt_seq": hurt.seq,
            "source_entity_id": hurt.source_entity_id,
            "actor_entity_id": hurt.actor_entity_id,
            "after_seq": after.seq,
        }])
