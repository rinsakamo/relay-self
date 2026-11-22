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
import math
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityHurt,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.physical_action_port import PhysicalActionBinding

if TYPE_CHECKING:
    from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
    from relay_self.skill_invocation import SkillInvocation


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
_MOVE_FIELDS = {
    "control", "started_position", "settled_position",
    "initial_stop_seq", "first_stable_seq",
    "initial_stop_tick", "first_stable_tick", "settled_tick",
    "displacement_m",
}
# Schema v2 is an additive, exact original-WAL extension for a selected PLACE
# parent MOVE. Old schema-v1 relative rows remain untouched and still valid.
_MOVE_PLACE_FIELDS = {
    "invocation_ref", "preset_ref", "target_contract_ref",
    "aim_yaw_rad", "target_position",
    "budget_actions", "budget_duration_ms", "budget_distance_m",
}
# Optional exact v2 MOVE_PLACE row extension; old persisted WALs have neither
# field and MUST continue to pass readback unchanged.
_MOVE_PLACE_GAIT_FIELDS = {"gait_mode", "gait_ack_seq"}


def _move_pos(value: object) -> tuple[float, float, float]:
    if (
        type(value) is not dict or set(value) != {"x", "y", "z"}
        or any(type(v) not in (int, float) or not math.isfinite(v)
               for v in value.values())
    ):
        raise PhysicalJournalError("MOVE persisted 3D position missing/nonfinite")
    return (float(value["x"]), float(value["y"]), float(value["z"]))



def _validate(value: object) -> dict[str, Any]:
    body = _exact(value, {"schema", "self_id", "actions"})
    if type(body["schema"]) is not int or body["schema"] not in (1, 2) or type(body["actions"]) is not list:
        raise PhysicalJournalError("unsupported journal schema")
    _text(body["self_id"])
    seen: set[str] = set()
    max_seq: dict[str, int] = {}
    for idx, entry in enumerate(body["actions"]):
        if type(entry) is not dict:
            raise PhysicalJournalError("physical journal row must be mapping")
        row = _exact(
            entry, (
                _ROW | _ATTACK_FIELDS
                if entry.get("capability") == "ATTACK"
                else (
                    _ROW | _MOVE_FIELDS | _MOVE_PLACE_FIELDS
                    | (_MOVE_PLACE_GAIT_FIELDS
                       if set(entry) & _MOVE_PLACE_GAIT_FIELDS else set())
                )
                if entry.get("capability") == "MOVE_PLACE"
                else _ROW | _MOVE_FIELDS
                if entry.get("capability") == "MOVE"
                else _ROW
            ),
        )
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
        elif row["capability"] == "MOVE":
            if (
                row["target_ref"] not in {
                    "relative:forward", "relative:back",
                    "relative:left", "relative:right",
                }
                or row["control"] != row["target_ref"].removeprefix("relative:")
            ):
                raise PhysicalJournalError("MOVE control not original relative target")
        elif row["capability"] == "MOVE_PLACE":
            if (
                body["schema"] != 2
                or not row["target_ref"].startswith("destination:")
                or row["control"] != "forward"
                or not row["invocation_ref"].startswith("skill-invocation:v1@")
                or not row["preset_ref"].startswith("skill-preset:v1@")
                or not row["target_contract_ref"].startswith("target-contract:v1@")
                or type(row["aim_yaw_rad"]) not in (float, int)
                or not math.isfinite(row["aim_yaw_rad"])
                or not -math.pi <= row["aim_yaw_rad"] <= math.pi
                or type(row["budget_actions"]) is not int
                or not 1 <= row["budget_actions"] <= 64
                or type(row["budget_duration_ms"]) is not int
                or not 1 <= row["budget_duration_ms"] <= 3600000
                or (
                    row["budget_distance_m"] is not None
                    and (
                        type(row["budget_distance_m"]) not in (float, int)
                        or not math.isfinite(row["budget_distance_m"])
                        or row["budget_distance_m"] <= 0
                    )
                )
            ):
                raise PhysicalJournalError("PLACE MOVE original Invocation/budget invalid")
            _move_pos(row["target_position"])
            if ("gait_mode" in row) != ("gait_ack_seq" in row):
                raise PhysicalJournalError("partial MOVE gait evidence fields")
            if "gait_mode" in row and (
                row["gait_mode"] not in ("WALK", "SNEAK")
                or ("gait_ack_seq" not in row)
            ):
                raise PhysicalJournalError("unrecognized original MOVE gait")
            if "gait_mode" in row and row["gait_mode"] == "WALK" and (
                row["gait_ack_seq"] is not None
            ):
                raise PhysicalJournalError("walking PLACE has no gait-mode effect")
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
            if row["capability"] == "MOVE_PLACE" and row.get("gait_ack_seq") is not None:
                raise PhysicalJournalError("unresolved gait cannot claim native effect")
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
            if row["capability"] in ("MOVE", "MOVE_PLACE"):
                _move_pos(row["started_position"])
                if any(row[k] is not None for k in (
                    "settled_position", "initial_stop_seq", "first_stable_seq",
                    "initial_stop_tick", "first_stable_tick", "settled_tick",
                    "displacement_m",
                )):
                    raise PhysicalJournalError("unresolved MOVE cannot claim stop/outcome")
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
        elif (
            row["capability"] == "MOVE_PLACE"
            and row["status"] in {
                "NATIVE_PLACE_MOVE_SETTLED", "NATIVE_PLACE_MOVE_NO_PROGRESS",
                "NATIVE_PLACE_MOVE_OVERSHOOT",
            }
        ):
            child_seq = row["effect_seqs"]
            start_pos = _move_pos(row["started_position"])
            end_pos = _move_pos(row["settled_position"])
            if type(child_seq) is not list or len(child_seq) != 3:
                raise PhysicalJournalError("PLACE MOVE needs look/start/stop ACKs")
            look_seq, start_seq, stop_seq = [_number(v) for v in child_seq]
            gait_seq = row.get("gait_ack_seq")
            if row.get("gait_mode") == "SNEAK":
                if gait_seq is None or not look_seq < _number(gait_seq) < start_seq:
                    raise PhysicalJournalError("SNEAK gait ACK missing or stale")
            elif gait_seq is not None:
                raise PhysicalJournalError("unrequested native gait ACK")
            initial = _number(row["initial_stop_seq"])
            first = _number(row["first_stable_seq"])
            final = _number(row["after_seq"])
            initial_tick = _number(row["initial_stop_tick"])
            first_tick = _number(row["first_stable_tick"])
            final_tick = _number(row["settled_tick"])
            delta = row["displacement_m"]
            if (
                type(delta) not in (int, float) or not math.isfinite(delta)
                or not 0 <= delta <= 8
                or abs(math.dist(start_pos, end_pos) - delta) > 1e-6
                or any(row[k] is not None for k in (
                    "food_before", "food_after", "count_before", "count_after",
                ))
                or not seq < look_seq < start_seq < stop_seq < initial < first < final
                or not 8 <= first_tick - initial_tick <= 200
                or not 8 <= final_tick - first_tick <= 200
                or not (
                    row["status"] == "NATIVE_PLACE_MOVE_NO_PROGRESS"
                    if delta < 0.1 else
                    row["status"] == "NATIVE_PLACE_MOVE_OVERSHOOT"
                    if row["budget_distance_m"] is not None
                    and delta > row["budget_distance_m"] + 1e-6 else
                    row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
                )
            ):
                raise PhysicalJournalError("PLACE MOVE original ACK/settle/budget invalid")
            max_seq[session] = final
        elif row["status"] in (
            "NATIVE_MOVE_SETTLED", "NATIVE_MOVE_NO_NET_DISPLACEMENT",
        ) and row["capability"] == "MOVE":
            child_seq = row["effect_seqs"]
            start_pos = _move_pos(row["started_position"])
            end_pos = _move_pos(row["settled_position"])
            if type(child_seq) is not list or len(child_seq) != 2:
                raise PhysicalJournalError("MOVE requires start+stop native ACK")
            start_seq, stop_seq = [_number(v) for v in child_seq]
            initial = _number(row["initial_stop_seq"])
            first = _number(row["first_stable_seq"])
            final = _number(row["after_seq"])
            initial_tick = _number(row["initial_stop_tick"])
            first_tick = _number(row["first_stable_tick"])
            final_tick = _number(row["settled_tick"])
            delta = row["displacement_m"]
            if (
                type(delta) not in (int, float) or not math.isfinite(delta)
                or not (
                    0.1 <= delta <= 8.0
                    if row["status"] == "NATIVE_MOVE_SETTLED"
                    else 0 <= delta < 0.1
                )
                or abs(math.dist(start_pos, end_pos) - delta) > 1e-6
                or row["food_before"] is not None or row["food_after"] is not None
                or row["count_before"] is not None or row["count_after"] is not None
                or not seq < start_seq < stop_seq < initial < first < final
                or not 8 <= first_tick - initial_tick <= 200
                or not 8 <= final_tick - first_tick <= 200
            ):
                raise PhysicalJournalError("MOVE original ACK/stop/settle chronology invalid")
            max_seq[session] = final
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
    def schema_version(self) -> int:
        """Current on-disk canonical WAL schema; never a physical capability."""
        return self._body["schema"]

    def certified_prefix_digest(
        self, count: int, *, source_schema: int | None = None,
    ) -> str:
        """Revalidate a canonical historical prefix, without source authentication.

        The optional source_schema=1 allows a separately held pre-upgrade v1
        S1 digest to be checked after an original v2 MOVE_PLACE append. A
        source_schema value is never evidence of historical custody by itself:
        only a previously retained independent Owner witness can establish
        that the digest was known BEFORE this journal changed. Neither form
        authorizes a physical Action or automatically resolves PREPARED.
        """
        # A captured original *empty initial* Q4 DEV WAL needs a zero-row
        # comparison AFTER the first v2 PLACE append. Only a previously
        # supplied source_schema can request count=0; this is a digest, not
        # a historical Action/physical authorization.
        if (
            type(count) is not int or not 0 <= count <= len(self._body["actions"])
            or count == 0 and source_schema is None
        ):
            raise PhysicalJournalError("nonempty canonical WAL prefix required")
        schema = self._body["schema"] if source_schema is None else source_schema
        if (
            type(schema) is not int
            or schema not in (1, 2)
            or schema > self._body["schema"]
        ):
            raise PhysicalJournalError("invalid canonical historical prefix schema")
        prefix = _validate({
            **self._body, "schema": schema,
            "actions": self._body["actions"][:count],
        })
        return _digest(prefix)

    @property
    def unresolved(self) -> bool:
        return bool(
            self.records and self.records[-1]["status"] == "PREPARED_UNRESOLVED"
        )

    def require_clear(self) -> None:
        if self.unresolved:
            raise PhysicalJournalUnresolved("possible physical effect: STOP/UNKNOWN")

    def _commit(
        self, records: list[dict[str, Any]], *, upgrade_to_v2: bool = False,
    ) -> None:
        updated = _validate({
            **self._body, "schema": 2 if upgrade_to_v2 else self._body["schema"],
            "actions": records,
        })
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


    def prepare_move(
        self, binding: PhysicalActionBinding, probe: MineflayerObservation,
    ) -> None:
        """Durably reserve the original Self WAL BEFORE any native MOVE effect."""
        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or binding.scope.self_id != self._body["self_id"]
            or binding.skill_id != "MOVE" or binding.skill_version != 1
            or binding.capability_ref != "MOVE" or binding.capability_version != 1
            or binding.body_channel != "locomotion"
            or binding.target_kind != "RELATIVE"
            or binding.target_ref not in {
                "relative:forward", "relative:back",
                "relative:left", "relative:right",
            }
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.time is None  # STOP evidence clock required
        ):
            raise PhysicalJournalError("original MOVE parent/native source not qualified")
        pos = probe.snapshot.position
        self._commit([*self._body["actions"], {
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
            "control": binding.target_ref.removeprefix("relative:"),
            "started_position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "settled_position": None,
            "initial_stop_seq": None,
            "first_stable_seq": None,
            "initial_stop_tick": None,
            "first_stable_tick": None,
            "settled_tick": None,
            "displacement_m": None,
        }])

    def close_move(
        self, binding: PhysicalActionBinding,
        before: MineflayerObservation,
        start_ack: MineflayerEffectResult,
        stop_ack: MineflayerEffectResult,
        initial_stop: MineflayerObservation,
        first_stable: MineflayerObservation,
        settled: MineflayerObservation,
        terminal: ActionLifecycle,
        supervisor: ActionSupervisor,
    ) -> None:
        """Only original two native ACKs and 8+8 tick settling seal MOVE.

        STOP drift <=0.06m is a stop qualification, NOT a navigation target
        tolerance. Net displacement merely witnesses movement; no Goal/Skill
        success or independent Paper causal attribution is claimed.
        """
        if not self.unresolved or not isinstance(binding, PhysicalActionBinding):
            raise PhysicalJournalError("MOVE canonical PREPARED reservation absent")
        row = self.records[-1]
        entries = (before, initial_stop, first_stable, settled)
        if (
            row["capability"] != "MOVE"
            or row["action_id"] != binding.action_id
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["source_ref"] != binding.native_source.reference
            or row["target_ref"] != binding.target_ref
            or any(not isinstance(x, MineflayerObservation) or x.kind != "probe"
                   or x.snapshot.time is None or not x.request_id
                   for x in entries)
            or any(x.session_id != row["session_id"] for x in entries)
            or before.seq != row["probe_seq"]
            or before.request_id != row["probe_request_id"]
            or not isinstance(start_ack, MineflayerEffectResult)
            or not isinstance(stop_ack, MineflayerEffectResult)
            or start_ack.session_id != before.session_id
            or stop_ack.session_id != before.session_id
            or start_ack.action_id != binding.action_id + "-start"
            or stop_ack.action_id != binding.action_id + "-stop"
            or start_ack.effect != "set_control"
            or stop_ack.effect != "clear_controls"
            or start_ack.result != "applied" or stop_ack.result != "applied"
            or not before.seq < start_ack.seq < stop_ack.seq
            or not stop_ack.seq < initial_stop.seq < first_stable.seq < settled.seq
            or len({x.request_id for x in entries}) != 4
            or not isinstance(terminal, ActionLifecycle)
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or not isinstance(supervisor, ActionSupervisor)
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("MOVE original native Action/stop evidence mismatch")
        def to_tick(item: MineflayerObservation) -> int:
            assert item.snapshot.time is not None
            return item.snapshot.time.day * 24000 + item.snapshot.time.time_of_day
        t0, t1, t2 = map(to_tick, (initial_stop, first_stable, settled))
        p0, p1 = first_stable.snapshot.position, settled.snapshot.position
        if (
            not 8 <= t1 - t0 <= 200
            or not 8 <= t2 - t1 <= 200
            or math.dist((p0.x, p0.y, p0.z), (p1.x, p1.y, p1.z)) > 0.06
        ):
            raise PhysicalJournalError("MOVE 8+8 tick native STOP settled proof missing")
        before_pos, after_pos = before.snapshot.position, settled.snapshot.position
        displacement = math.dist(
            (before_pos.x, before_pos.y, before_pos.z),
            (after_pos.x, after_pos.y, after_pos.z),
        )
        if not 0 <= displacement <= 8.0:
            raise PhysicalJournalError("MOVE observed displacement not qualified")
        # An actual selected Action can have no net displacement. This is a
        # terminal measured result, not a pretend successful MOVE. Strong
        # start/stop ACK + 8+8 tick settle proof is required in both cases.
        status = (
            "NATIVE_MOVE_SETTLED" if displacement >= 0.1
            else "NATIVE_MOVE_NO_NET_DISPLACEMENT"
        )
        self._commit([*self._body["actions"][:-1], {
            **row,
            "status": status,
            "effect_seqs": [start_ack.seq, stop_ack.seq],
            "after_seq": settled.seq,
            "settled_position": {
                "x": after_pos.x, "y": after_pos.y, "z": after_pos.z,
            },
            "initial_stop_seq": initial_stop.seq,
            "first_stable_seq": first_stable.seq,
            "initial_stop_tick": t0,
            "first_stable_tick": t1,
            "settled_tick": t2,
            "displacement_m": displacement,
        }])

    def prepare_place_move(
        self, binding: PhysicalActionBinding, probe: MineflayerObservation,
        invocation: "SkillInvocation", motion: "Stage27PlaceMotionPlan",
        *, precision_gait: str | None = None,
    ) -> None:
        """fsync selected original PLACE/Preset BEFORE any native LOOK/effect."""
        from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
        from relay_self.skill_invocation import SkillInvocation
        from relay_self.target_contract import TargetKind

        self.require_clear()
        if (
            not isinstance(binding, PhysicalActionBinding)
            or not isinstance(invocation, SkillInvocation)
            or not isinstance(motion, Stage27PlaceMotionPlan)
            or binding.scope.self_id != self._body["self_id"]
            or binding.scope != invocation.scope
            or binding.skill_id != "MOVE" or binding.skill_version != 1
            or binding.capability_ref != "MOVE" or binding.capability_version != 1
            or binding.body_channel != "locomotion"
            or binding.goal_id != invocation.goal_id
            or binding.target_kind != "DESTINATION"
            or binding.target_ref != invocation.target.ref
            or invocation.target.contract is None
            or invocation.target.contract.kind is not TargetKind.PLACE
            or invocation.target.contract.anchor is None
            or invocation.parameter_preset_ref is None
            or motion.invocation_ref != invocation.invocation_ref
            or motion.parameter_preset_ref != invocation.parameter_preset_ref
            or motion.target_contract_ref != invocation.target.contract.contract_ref
            or motion.target_ref != binding.target_ref
            or motion.self_id != binding.scope.self_id
            or motion.native_session_id != binding.scope.world_session_id
            or motion.native_probe_seq != binding.native_seq
            or motion.native_probe_request_id != binding.native_request_id
            or motion.observation_status != "OUTSIDE"
            or motion.next_step
            != "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE"
            or motion.desired_mineflayer_yaw_rad is None
            or motion.action_granted or motion.native_effect_issued
            or motion.world_goal_succeeded
            or precision_gait not in (None, "WALK", "SNEAK")
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.session_id != binding.scope.world_session_id
            or probe.seq != binding.native_seq
            or probe.request_id != binding.native_request_id
            or probe.provenance != binding.native_source
            or probe.snapshot.time is None or probe.snapshot.health <= 0
        ):
            raise PhysicalJournalError("selected original PLACE/Preset binding invalid")
        pos, target = probe.snapshot.position, invocation.target.contract.anchor
        self._commit([*self.records, {
            "session_id": probe.session_id,
            "intent_id": binding.intent_id,
            "skill_execution_id": binding.skill_execution_id,
            "action_id": binding.action_id,
            "capability": "MOVE_PLACE",
            "target_ref": binding.target_ref,
            "probe_seq": probe.seq,
            "probe_request_id": probe.request_id,
            "source_ref": probe.provenance.reference,
            "status": "PREPARED_UNRESOLVED",
            "effect_seqs": None,
            "after_seq": None,
            "food_before": None, "food_after": None,
            "count_before": None, "count_after": None,
            "control": "forward",
            "started_position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "settled_position": None,
            "initial_stop_seq": None, "first_stable_seq": None,
            "initial_stop_tick": None, "first_stable_tick": None,
            "settled_tick": None, "displacement_m": None,
            "invocation_ref": invocation.invocation_ref,
            "preset_ref": invocation.parameter_preset_ref,
            "target_contract_ref": motion.target_contract_ref,
            "target_position": {"x": target.x, "y": target.y, "z": target.z},
            "aim_yaw_rad": motion.desired_mineflayer_yaw_rad,
            "budget_actions": invocation.budget.max_actions,
            "budget_duration_ms": invocation.budget.max_duration_ms,
            "budget_distance_m": invocation.budget.max_distance_m,
            **({"gait_mode": precision_gait, "gait_ack_seq": None}
               if precision_gait is not None else {}),
        }], upgrade_to_v2=True)

    def close_place_move(
        self, binding: PhysicalActionBinding,
        invocation: "SkillInvocation",
        before: MineflayerObservation,
        look_ack: MineflayerEffectResult,
        start_ack: MineflayerEffectResult,
        stop_ack: MineflayerEffectResult,
        initial_stop: MineflayerObservation,
        first_stable: MineflayerObservation,
        settled: MineflayerObservation,
        terminal: ActionLifecycle,
        supervisor: ActionSupervisor,
        *, gait_ack: MineflayerEffectResult | None = None,
    ) -> str:
        """Seal original LOOK/(optional SNEAK)/start/STOP native readbacks."""
        from relay_self.skill_invocation import SkillInvocation

        if not self.unresolved or not isinstance(binding, PhysicalActionBinding):
            raise PhysicalJournalError("MOVE PLACE PREPARED original WAL missing")
        row = self.records[-1]
        entries = (before, initial_stop, first_stable, settled)
        if (
            not isinstance(invocation, SkillInvocation)
            or row["capability"] != "MOVE_PLACE"
            or row["intent_id"] != binding.intent_id
            or row["skill_execution_id"] != binding.skill_execution_id
            or row["action_id"] != binding.action_id
            or row["target_ref"] != binding.target_ref
            or row["invocation_ref"] != invocation.invocation_ref
            or row["preset_ref"] != invocation.parameter_preset_ref
            or row["target_contract_ref"] != invocation.target.contract.contract_ref
            or row["source_ref"] != binding.native_source.reference
            or any(not isinstance(x, MineflayerObservation) or x.kind != "probe"
                   or x.snapshot.time is None or not x.request_id
                   or x.snapshot.health <= 0 for x in entries)
            or any(x.session_id != row["session_id"] for x in entries)
            or before.seq != row["probe_seq"]
            or before.request_id != row["probe_request_id"]
            or any(not isinstance(x, MineflayerEffectResult)
                   for x in (look_ack, start_ack, stop_ack))
            or any(x.session_id != before.session_id
                   for x in (look_ack, start_ack, stop_ack))
            or look_ack.action_id != binding.action_id + "-look"
            or start_ack.action_id != binding.action_id + "-start"
            or stop_ack.action_id != binding.action_id + "-stop"
            or look_ack.effect != "look" or start_ack.effect != "set_control"
            or stop_ack.effect != "clear_controls"
            or any(x.result != "applied" for x in (look_ack, start_ack, stop_ack))
            or not before.seq < look_ack.seq < start_ack.seq < stop_ack.seq
            or (row.get("gait_mode") == "SNEAK" and (
                not isinstance(gait_ack, MineflayerEffectResult)
                or gait_ack.session_id != before.session_id
                or gait_ack.action_id != binding.action_id + "-sneak"
                or gait_ack.effect != "set_control" or gait_ack.result != "applied"
                or not look_ack.seq < gait_ack.seq < start_ack.seq
            ))
            or (row.get("gait_mode") != "SNEAK" and gait_ack is not None)
            or not stop_ack.seq < initial_stop.seq < first_stable.seq < settled.seq
            or len({x.request_id for x in entries}) != 4
            or not isinstance(terminal, ActionLifecycle)
            or terminal.state is not ActionState.OUTCOME
            or terminal.action_id != binding.action_id
            or not isinstance(supervisor, ActionSupervisor)
            or supervisor.get(binding.action_id) is not terminal
        ):
            raise PhysicalJournalError("MOVE PLACE original Action/native source mismatch")
        def to_tick(item: MineflayerObservation) -> int:
            assert item.snapshot.time is not None
            return item.snapshot.time.day * 24000 + item.snapshot.time.time_of_day

        t0, t1, t2 = map(to_tick, (initial_stop, first_stable, settled))
        p0, p1 = first_stable.snapshot.position, settled.snapshot.position
        if (
            not 8 <= t1 - t0 <= 200
            or not 8 <= t2 - t1 <= 200
            or math.dist((p0.x, p0.y, p0.z), (p1.x, p1.y, p1.z)) > 0.06
        ):
            raise PhysicalJournalError("PLACE MOVE STOP did not settle")
        before_pos, after_pos = before.snapshot.position, settled.snapshot.position
        delta = math.dist(
            (before_pos.x, before_pos.y, before_pos.z),
            (after_pos.x, after_pos.y, after_pos.z),
        )
        if not math.isfinite(delta) or delta > 8:
            raise PhysicalJournalError("PLACE MOVE displacement exceeds source bounds")
        budget = invocation.budget.max_distance_m
        status = (
            "NATIVE_PLACE_MOVE_NO_PROGRESS" if delta < 0.1
            else "NATIVE_PLACE_MOVE_OVERSHOOT"
            if budget is not None and delta > budget + 1e-6
            else "NATIVE_PLACE_MOVE_SETTLED"
        )
        self._commit([*self.records[:-1], {
            **row, "status": status,
            "effect_seqs": [look_ack.seq, start_ack.seq, stop_ack.seq],
            **({"gait_ack_seq": gait_ack.seq if gait_ack is not None else None}
               if "gait_mode" in row else {}),
            "after_seq": settled.seq,
            "settled_position": {
                "x": after_pos.x, "y": after_pos.y, "z": after_pos.z,
            },
            "initial_stop_seq": initial_stop.seq,
            "first_stable_seq": first_stable.seq,
            "initial_stop_tick": t0,
            "first_stable_tick": t1,
            "settled_tick": t2,
            "displacement_m": delta,
        }])
        return status

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
