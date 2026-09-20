from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

from relay_self.provenance import Provenance

MINEFLAYER_VERSION = "4.39.0"
MINEFLAYER_PROVENANCE_SOURCE = "mineflayer"
MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE = "mineflayer_entity_registry"
MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE = 16.0
MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES = 16

_OBSERVATION_KINDS = frozenset(
    {
        "spawn",
        "health",
        "time",
        "inventory",
        "entities",
        "move",
        "forcedMove",
        "probe",
        "death",
        "respawn",
    }
)
_EFFECTS = frozenset(
    {"set_control", "clear_controls", "equip_item", "consume_held", "look"}
)
_EFFECT_RESULTS = frozenset({"applied", "rejected"})
_CONTROLS = frozenset(
    {"forward", "back", "left", "right", "jump", "sprint", "sneak"}
)


class MineflayerAdapterProtocolError(ValueError):
    """Raised when the target-local Mineflayer JSONL protocol is malformed."""


@dataclass(frozen=True, slots=True)
class MineflayerLaunchConfig:
    host: str = "127.0.0.1"
    port: int = 25565
    username: str = "RelaySelf"
    version: str | None = None

    def __post_init__(self) -> None:
        _require_text("host", self.host)
        _require_port(self.port)
        _require_text("username", self.username)
        if self.version is not None:
            _require_text("version", self.version)

    def argv(
        self,
        bridge_path: str | Path,
        *,
        node_executable: str = "node",
    ) -> tuple[str, ...]:
        _require_text("node_executable", node_executable)
        path = str(bridge_path)
        _require_text("bridge_path", path)
        values = [
            node_executable,
            path,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--username",
            self.username,
        ]
        if self.version is not None:
            values.extend(["--version", self.version])
        return tuple(values)


@dataclass(frozen=True, slots=True)
class MineflayerPosition:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        _require_number("position.x", self.x)
        _require_number("position.y", self.y)
        _require_number("position.z", self.z)


def mineflayer_yaw_to_target(
    current: MineflayerPosition,
    target: MineflayerPosition,
) -> float:
    """Map a target position into Mineflayer's target-native yaw convention."""

    if not isinstance(current, MineflayerPosition):
        raise MineflayerAdapterProtocolError(
            "current position must be MineflayerPosition"
        )
    if not isinstance(target, MineflayerPosition):
        raise MineflayerAdapterProtocolError(
            "target position must be MineflayerPosition"
        )
    dx = target.x - current.x
    dz = target.z - current.z
    if dx == 0 and dz == 0:
        raise MineflayerAdapterProtocolError(
            "cannot compute Mineflayer yaw for the current horizontal position"
        )
    return math.atan2(-dx, -dz)


@dataclass(frozen=True, slots=True)
class MineflayerTime:
    time_of_day: int
    day: int
    is_day: bool

    def __post_init__(self) -> None:
        _require_non_negative_int("time_of_day", self.time_of_day)
        _require_non_negative_int("day", self.day)
        _require_bool("is_day", self.is_day)


@dataclass(frozen=True, slots=True)
class MineflayerInventoryItem:
    name: str
    count: int
    slot: int

    def __post_init__(self) -> None:
        _require_text("inventory item name", self.name)
        _require_non_negative_int("inventory item count", self.count)
        _require_non_negative_int("inventory item slot", self.slot)


@dataclass(frozen=True, slots=True)
class MineflayerEntityFact:
    entity_id: int
    name: str | None
    entity_type: str | None
    distance: float
    position: MineflayerPosition

    def __post_init__(self) -> None:
        _require_non_negative_int("entity id", self.entity_id)
        if self.name is not None:
            _require_text("entity name", self.name)
        if self.entity_type is not None:
            _require_text("entity type", self.entity_type)
        _require_non_negative_number("entity distance", self.distance)
        if not isinstance(self.position, MineflayerPosition):
            raise MineflayerAdapterProtocolError(
                "entity position must be MineflayerPosition"
            )


@dataclass(frozen=True, slots=True)
class MineflayerNearbyEntitiesCoverage:
    source_scope: str
    max_distance: float
    max_entities: int
    candidate_count: int
    truncated: bool

    def __post_init__(self) -> None:
        _require_text("nearby entity source_scope", self.source_scope)
        if self.source_scope != MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE:
            raise MineflayerAdapterProtocolError(
                "nearby entity source_scope must identify Mineflayer's entity registry"
            )
        _require_non_negative_number("nearby entity max_distance", self.max_distance)
        _require_non_negative_int("nearby entity max_entities", self.max_entities)
        if self.max_entities == 0:
            raise MineflayerAdapterProtocolError(
                "nearby entity max_entities must be positive"
            )
        _require_non_negative_int(
            "nearby entity candidate_count",
            self.candidate_count,
        )
        _require_bool("nearby entity truncated", self.truncated)


@dataclass(frozen=True, slots=True)
class MineflayerSnapshot:
    health: float
    food: float
    oxygen_level: float | None
    position: MineflayerPosition
    time: MineflayerTime | None
    inventory: tuple[MineflayerInventoryItem, ...]
    nearby_entities: tuple[MineflayerEntityFact, ...]
    nearby_entities_coverage: MineflayerNearbyEntitiesCoverage

    def __post_init__(self) -> None:
        _require_non_negative_number("health", self.health)
        _require_non_negative_number("food", self.food)
        if self.oxygen_level is not None:
            _require_non_negative_number("oxygen_level", self.oxygen_level)
        if not isinstance(self.position, MineflayerPosition):
            raise MineflayerAdapterProtocolError(
                "snapshot position must be MineflayerPosition"
            )
        if self.time is not None and not isinstance(self.time, MineflayerTime):
            raise MineflayerAdapterProtocolError(
                "snapshot time must be MineflayerTime or None"
            )
        if not isinstance(self.inventory, tuple) or not all(
            isinstance(item, MineflayerInventoryItem) for item in self.inventory
        ):
            raise MineflayerAdapterProtocolError(
                "snapshot inventory must be MineflayerInventoryItem tuple"
            )
        if not isinstance(self.nearby_entities, tuple) or not all(
            isinstance(entity, MineflayerEntityFact)
            for entity in self.nearby_entities
        ):
            raise MineflayerAdapterProtocolError(
                "snapshot nearby_entities must be MineflayerEntityFact tuple"
            )
        if not isinstance(
            self.nearby_entities_coverage,
            MineflayerNearbyEntitiesCoverage,
        ):
            raise MineflayerAdapterProtocolError(
                "snapshot nearby_entities_coverage must be "
                "MineflayerNearbyEntitiesCoverage"
            )
        coverage = self.nearby_entities_coverage
        observed_count = len(self.nearby_entities)
        if observed_count > coverage.max_entities:
            raise MineflayerAdapterProtocolError(
                "snapshot nearby_entities exceeds declared max_entities"
            )
        if coverage.candidate_count < observed_count:
            raise MineflayerAdapterProtocolError(
                "nearby entity candidate_count cannot be smaller than observed count"
            )
        if coverage.truncated:
            if (
                coverage.candidate_count <= coverage.max_entities
                or observed_count != coverage.max_entities
            ):
                raise MineflayerAdapterProtocolError(
                    "truncated nearby entity coverage is inconsistent with counts"
                )
        elif coverage.candidate_count != observed_count:
            raise MineflayerAdapterProtocolError(
                "non-truncated nearby entity coverage must include every candidate"
            )


@dataclass(frozen=True, slots=True)
class MineflayerMessage:
    session_id: str
    seq: int

    def __post_init__(self) -> None:
        _require_text("session_id", self.session_id)
        _require_seq(self.seq)

    @property
    def provenance(self) -> Provenance:
        return Provenance(
            source=MINEFLAYER_PROVENANCE_SOURCE,
            reference=f"{self.session_id}:{self.seq}",
        )


@dataclass(frozen=True, slots=True)
class MineflayerAdapterStarted(MineflayerMessage):
    mineflayer_version: str
    config: MineflayerLaunchConfig

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_text("mineflayer_version", self.mineflayer_version)
        if self.mineflayer_version != MINEFLAYER_VERSION:
            raise MineflayerAdapterProtocolError(
                "unexpected Mineflayer version: "
                f"{self.mineflayer_version}; expected {MINEFLAYER_VERSION}"
            )
        if not isinstance(self.config, MineflayerLaunchConfig):
            raise MineflayerAdapterProtocolError(
                "adapter config must be MineflayerLaunchConfig"
            )


@dataclass(frozen=True, slots=True)
class MineflayerObservation(MineflayerMessage):
    kind: str
    snapshot: MineflayerSnapshot

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        if self.kind not in _OBSERVATION_KINDS:
            raise MineflayerAdapterProtocolError(
                f"unsupported observation kind: {self.kind}"
            )
        if not isinstance(self.snapshot, MineflayerSnapshot):
            raise MineflayerAdapterProtocolError(
                "observation snapshot must be MineflayerSnapshot"
            )


@dataclass(frozen=True, slots=True)
class MineflayerEffectResult(MineflayerMessage):
    action_id: str
    effect: str
    result: str
    error: str | None

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_text("action_id", self.action_id)
        if self.effect not in _EFFECTS:
            raise MineflayerAdapterProtocolError(
                f"unsupported effect result: {self.effect}"
            )
        if self.result not in _EFFECT_RESULTS:
            raise MineflayerAdapterProtocolError(
                f"unsupported effect result status: {self.result}"
            )
        if self.error is not None:
            _require_text("effect error", self.error)
        if self.result == "applied" and self.error is not None:
            raise MineflayerAdapterProtocolError(
                "applied effect result cannot carry an error"
            )
        if self.result == "rejected" and self.error is None:
            raise MineflayerAdapterProtocolError(
                "rejected effect result requires an error"
            )


@dataclass(frozen=True, slots=True)
class MineflayerConnectionEnd(MineflayerMessage):
    reason: str

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_text("connection end reason", self.reason)


@dataclass(frozen=True, slots=True)
class MineflayerAdapterErrorMessage(MineflayerMessage):
    message: str

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_text("adapter error message", self.message)


@dataclass(frozen=True, slots=True)
class MineflayerCommandError(MineflayerMessage):
    message: str

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_text("command error message", self.message)


@dataclass(frozen=True, slots=True)
class MineflayerShutdownAck(MineflayerMessage):
    pass


MineflayerDecodedMessage = Union[
    MineflayerAdapterStarted,
    MineflayerObservation,
    MineflayerEffectResult,
    MineflayerConnectionEnd,
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerShutdownAck,
]


class MineflayerStreamDecoder:
    """Validate one bridge process stream without creating World authority."""

    def __init__(self) -> None:
        self._session_id: str | None = None
        self._next_seq = 0

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def next_seq(self) -> int:
        return self._next_seq

    def decode(self, line: str) -> MineflayerDecodedMessage:
        message = parse_mineflayer_line(line)

        if self._session_id is None:
            if not isinstance(message, MineflayerAdapterStarted):
                raise MineflayerAdapterProtocolError(
                    "first bridge message must be adapter_started"
                )
            if message.seq != 0:
                raise MineflayerAdapterProtocolError(
                    "first bridge message must have seq 0"
                )
            self._session_id = message.session_id
            self._next_seq = 1
            return message

        if message.session_id != self._session_id:
            raise MineflayerAdapterProtocolError(
                "bridge session_id changed within one stream"
            )
        if message.seq != self._next_seq:
            raise MineflayerAdapterProtocolError(
                f"bridge sequence mismatch: expected {self._next_seq}, "
                f"got {message.seq}"
            )

        self._next_seq += 1
        return message


def parse_mineflayer_line(line: str) -> MineflayerDecodedMessage:
    if not isinstance(line, str) or not line.strip():
        raise MineflayerAdapterProtocolError(
            "Mineflayer bridge line must be non-empty text"
        )
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise MineflayerAdapterProtocolError(
            f"Mineflayer bridge line is invalid JSON: {exc.msg}"
        ) from exc

    payload = _require_mapping("message", raw)
    message_type = _decoded_text("message type", payload.get("type"))
    session_id = _decoded_text("session_id", payload.get("session_id"))
    seq = _decoded_seq(payload.get("seq"))

    if message_type == "adapter_started":
        _require_exact_keys(
            "adapter_started",
            payload,
            {
                "type",
                "session_id",
                "seq",
                "mineflayer_version",
                "config",
            },
        )
        return MineflayerAdapterStarted(
            session_id=session_id,
            seq=seq,
            mineflayer_version=_decoded_text(
                "mineflayer_version",
                payload["mineflayer_version"],
            ),
            config=_decode_launch_config(payload["config"]),
        )

    if message_type == "observation":
        _require_exact_keys(
            "observation",
            payload,
            {"type", "session_id", "seq", "kind", "snapshot"},
        )
        return MineflayerObservation(
            session_id=session_id,
            seq=seq,
            kind=_decoded_text("observation kind", payload["kind"]),
            snapshot=_decode_snapshot(payload["snapshot"]),
        )

    if message_type == "effect_result":
        _require_exact_keys(
            "effect_result",
            payload,
            {
                "type",
                "session_id",
                "seq",
                "action_id",
                "effect",
                "result",
                "error",
            },
        )
        error = payload["error"]
        if error is not None:
            error = _decoded_text("effect error", error)
        return MineflayerEffectResult(
            session_id=session_id,
            seq=seq,
            action_id=_decoded_text("action_id", payload["action_id"]),
            effect=_decoded_text("effect", payload["effect"]),
            result=_decoded_text("effect result", payload["result"]),
            error=error,
        )

    if message_type == "connection_end":
        _require_exact_keys(
            "connection_end",
            payload,
            {"type", "session_id", "seq", "reason"},
        )
        return MineflayerConnectionEnd(
            session_id=session_id,
            seq=seq,
            reason=_decoded_text("connection end reason", payload["reason"]),
        )

    if message_type == "adapter_error":
        _require_exact_keys(
            "adapter_error",
            payload,
            {"type", "session_id", "seq", "message"},
        )
        return MineflayerAdapterErrorMessage(
            session_id=session_id,
            seq=seq,
            message=_decoded_text("adapter error message", payload["message"]),
        )

    if message_type == "command_error":
        _require_exact_keys(
            "command_error",
            payload,
            {"type", "session_id", "seq", "message"},
        )
        return MineflayerCommandError(
            session_id=session_id,
            seq=seq,
            message=_decoded_text("command error message", payload["message"]),
        )

    if message_type == "shutdown_ack":
        _require_exact_keys(
            "shutdown_ack",
            payload,
            {"type", "session_id", "seq"},
        )
        return MineflayerShutdownAck(session_id=session_id, seq=seq)

    raise MineflayerAdapterProtocolError(
        f"unsupported Mineflayer bridge message type: {message_type}"
    )


def encode_set_control(
    action_id: str,
    *,
    control: str,
    state: bool,
) -> str:
    _require_text("action_id", action_id)
    if control not in _CONTROLS:
        raise MineflayerAdapterProtocolError(
            f"unsupported Mineflayer control: {control}"
        )
    if not isinstance(state, bool):
        raise MineflayerAdapterProtocolError(
            "Mineflayer control state must be boolean"
        )
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "set_control",
            "control": control,
            "state": state,
        }
    )


def encode_clear_controls(action_id: str) -> str:
    _require_text("action_id", action_id)
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "clear_controls",
        }
    )


def encode_equip_item(action_id: str, *, item_name: str) -> str:
    _require_text("action_id", action_id)
    _require_text("item_name", item_name)
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "equip_item",
            "item_name": item_name,
        }
    )


def encode_consume_held(action_id: str) -> str:
    _require_text("action_id", action_id)
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "consume_held",
        }
    )


def encode_look(
    action_id: str,
    *,
    yaw: float,
    pitch: float,
) -> str:
    _require_text("action_id", action_id)
    _require_number("yaw", yaw)
    _require_number("pitch", pitch)
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "look",
            "yaw": yaw,
            "pitch": pitch,
        }
    )


def encode_observe() -> str:
    return _encode_command({"type": "observe"})


def encode_shutdown() -> str:
    return _encode_command({"type": "shutdown"})


def _encode_command(value: dict[str, object]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def _decode_launch_config(value: object) -> MineflayerLaunchConfig:
    payload = _require_mapping("adapter config", value)
    _require_exact_keys(
        "adapter config",
        payload,
        {"host", "port", "username", "version"},
    )
    version = payload["version"]
    if version is not None:
        version = _decoded_text("version", version)
    return MineflayerLaunchConfig(
        host=_decoded_text("host", payload["host"]),
        port=_decoded_port(payload["port"]),
        username=_decoded_text("username", payload["username"]),
        version=version,
    )


def _decode_snapshot(value: object) -> MineflayerSnapshot:
    payload = _require_mapping("snapshot", value)
    _require_exact_keys(
        "snapshot",
        payload,
        {
            "health",
            "food",
            "oxygen_level",
            "position",
            "time",
            "inventory",
            "nearby_entities",
            "nearby_entities_coverage",
        },
    )
    position = _decode_position("position", payload["position"])
    time_value = payload["time"]
    time = None if time_value is None else _decode_time(time_value)
    inventory = tuple(
        _decode_inventory_item(item)
        for item in _require_list("inventory", payload["inventory"])
    )
    nearby_entities = tuple(
        _decode_entity_fact(entity)
        for entity in _require_list(
            "nearby_entities",
            payload["nearby_entities"],
        )
    )
    nearby_entities_coverage = _decode_nearby_entities_coverage(
        payload["nearby_entities_coverage"]
    )
    return MineflayerSnapshot(
        health=_decoded_non_negative_number("health", payload["health"]),
        food=_decoded_non_negative_number("food", payload["food"]),
        oxygen_level=(
            None
            if payload["oxygen_level"] is None
            else _decoded_non_negative_number(
                "oxygen_level",
                payload["oxygen_level"],
            )
        ),
        position=position,
        time=time,
        inventory=inventory,
        nearby_entities=nearby_entities,
        nearby_entities_coverage=nearby_entities_coverage,
    )


def _decode_position(name: str, value: object) -> MineflayerPosition:
    payload = _require_mapping(name, value)
    _require_exact_keys(name, payload, {"x", "y", "z"})
    return MineflayerPosition(
        x=_decoded_number(f"{name}.x", payload["x"]),
        y=_decoded_number(f"{name}.y", payload["y"]),
        z=_decoded_number(f"{name}.z", payload["z"]),
    )


def _decode_time(value: object) -> MineflayerTime:
    payload = _require_mapping("time", value)
    _require_exact_keys(
        "time",
        payload,
        {"time_of_day", "day", "is_day"},
    )
    return MineflayerTime(
        time_of_day=_decoded_non_negative_int(
            "time_of_day",
            payload["time_of_day"],
        ),
        day=_decoded_non_negative_int("day", payload["day"]),
        is_day=_decoded_bool("is_day", payload["is_day"]),
    )


def _decode_inventory_item(value: object) -> MineflayerInventoryItem:
    payload = _require_mapping("inventory item", value)
    _require_exact_keys(
        "inventory item",
        payload,
        {"name", "count", "slot"},
    )
    return MineflayerInventoryItem(
        name=_decoded_text("inventory item name", payload["name"]),
        count=_decoded_non_negative_int(
            "inventory item count",
            payload["count"],
        ),
        slot=_decoded_non_negative_int("inventory item slot", payload["slot"]),
    )


def _decode_nearby_entities_coverage(
    value: object,
) -> MineflayerNearbyEntitiesCoverage:
    payload = _require_mapping("nearby_entities_coverage", value)
    _require_exact_keys(
        "nearby_entities_coverage",
        payload,
        {
            "source_scope",
            "max_distance",
            "max_entities",
            "candidate_count",
            "truncated",
        },
    )
    return MineflayerNearbyEntitiesCoverage(
        source_scope=_decoded_text(
            "nearby entity source_scope",
            payload["source_scope"],
        ),
        max_distance=_decoded_non_negative_number(
            "nearby entity max_distance",
            payload["max_distance"],
        ),
        max_entities=_decoded_non_negative_int(
            "nearby entity max_entities",
            payload["max_entities"],
        ),
        candidate_count=_decoded_non_negative_int(
            "nearby entity candidate_count",
            payload["candidate_count"],
        ),
        truncated=_decoded_bool(
            "nearby entity truncated",
            payload["truncated"],
        ),
    )


def _decode_entity_fact(value: object) -> MineflayerEntityFact:
    payload = _require_mapping("nearby entity", value)
    _require_exact_keys(
        "nearby entity",
        payload,
        {"id", "name", "type", "distance", "position"},
    )
    name = payload["name"]
    if name is not None:
        name = _decoded_text("entity name", name)
    entity_type = payload["type"]
    if entity_type is not None:
        entity_type = _decoded_text("entity type", entity_type)
    return MineflayerEntityFact(
        entity_id=_decoded_non_negative_int("entity id", payload["id"]),
        name=name,
        entity_type=entity_type,
        distance=_decoded_non_negative_number(
            "entity distance",
            payload["distance"],
        ),
        position=_decode_position("entity position", payload["position"]),
    )


def _require_mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MineflayerAdapterProtocolError(f"{name} must be an object")
    return value


def _require_list(name: str, value: object) -> list[Any]:
    if not isinstance(value, list):
        raise MineflayerAdapterProtocolError(f"{name} must be an array")
    return value


def _require_exact_keys(
    name: str,
    value: dict[str, Any],
    expected: set[str],
) -> None:
    actual = set(value)
    if actual != expected:
        raise MineflayerAdapterProtocolError(
            f"{name} fields are invalid; "
            f"missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MineflayerAdapterProtocolError(
            f"{name} must be a non-empty string"
        )


def _decoded_text(name: str, value: object) -> str:
    _require_text(name, value)
    return value


def _require_seq(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MineflayerAdapterProtocolError(
            "seq must be a non-negative integer"
        )


def _decoded_seq(value: object) -> int:
    _require_seq(value)
    return value


def _require_port(value: object) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > 65535
    ):
        raise MineflayerAdapterProtocolError(
            "port must be an integer in 1..65535"
        )


def _decoded_port(value: object) -> int:
    _require_port(value)
    return value


def _require_bool(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise MineflayerAdapterProtocolError(f"{name} must be boolean")


def _decoded_bool(name: str, value: object) -> bool:
    _require_bool(name, value)
    return value


def _require_non_negative_int(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MineflayerAdapterProtocolError(
            f"{name} must be a non-negative integer"
        )


def _decoded_non_negative_int(name: str, value: object) -> int:
    _require_non_negative_int(name, value)
    return value


def _require_number(name: str, value: object) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise MineflayerAdapterProtocolError(
            f"{name} must be a finite number"
        )


def _decoded_number(name: str, value: object) -> float:
    _require_number(name, value)
    return float(value)


def _require_non_negative_number(name: str, value: object) -> None:
    _require_number(name, value)
    if value < 0:
        raise MineflayerAdapterProtocolError(
            f"{name} must be non-negative"
        )


def _decoded_non_negative_number(name: str, value: object) -> float:
    _require_non_negative_number(name, value)
    return float(value)
