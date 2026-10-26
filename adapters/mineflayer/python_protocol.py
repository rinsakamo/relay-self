from __future__ import annotations

import json
import math
import re
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
    {
        "set_control",
        "clear_controls",
        "equip_item",
        "consume_held",
        "look",
        "attack_entity",
    }
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
        if self.max_distance != MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE:
            raise MineflayerAdapterProtocolError(
                "nearby entity max_distance changed from the adapter contract"
            )
        if self.max_entities != MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES:
            raise MineflayerAdapterProtocolError(
                "nearby entity max_entities changed from the adapter contract"
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
    food_saturation: float
    oxygen_level: float | None
    position: MineflayerPosition
    time: MineflayerTime | None
    inventory: tuple[MineflayerInventoryItem, ...]
    nearby_entities: tuple[MineflayerEntityFact, ...]
    nearby_entities_coverage: MineflayerNearbyEntitiesCoverage

    def __post_init__(self) -> None:
        _require_non_negative_number("health", self.health)
        _require_non_negative_number("food", self.food)
        _require_non_negative_number("food_saturation", self.food_saturation)
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
    request_id: str | None = None

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
        if self.request_id is not None:
            _require_probe_request_id(self.request_id)
            if self.kind != "probe":
                raise MineflayerAdapterProtocolError(
                    "request_id is only supported on probe observations"
                )


@dataclass(frozen=True, slots=True)
class MineflayerNativeClockPacket(MineflayerMessage):
    """Original-shaped clientbound time sample, not command-effect authority."""

    source: str
    observation_precision: str
    world_age_ticks: str
    world_day_time_raw_ticks: str
    tick_day_time: bool
    host_monotonic_ns: str
    command_effect_tick_attested: bool

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        if (
            self.source != "minecraft_1_21_8_clientbound_update_time"
            or self.observation_precision != "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY"
            or type(self.world_age_ticks) is not str
            or re.fullmatch(r"(0|[1-9][0-9]*)", self.world_age_ticks) is None
            or int(self.world_age_ticks) >= 2**63
            or type(self.world_day_time_raw_ticks) is not str
            or re.fullmatch(r"(0|-?[1-9][0-9]*)", self.world_day_time_raw_ticks) is None
            or abs(int(self.world_day_time_raw_ticks)) >= 2**63
            or type(self.tick_day_time) is not bool
            or type(self.host_monotonic_ns) is not str
            or re.fullmatch(r"[1-9][0-9]*", self.host_monotonic_ns) is None
            or type(self.command_effect_tick_attested) is not bool
            or self.command_effect_tick_attested
        ):
            raise MineflayerAdapterProtocolError("unqualified native V6 clock packet")



@dataclass(frozen=True, slots=True)
class MineflayerPaperTickSample(MineflayerMessage):
    """Opt-in Paper clientbound delivery, not a checked Self L0 WorldTick.

    Identifiers are client-transport bound via MineflayerStreamDecoder,
    but native origin and same-tick decision completion are NOT attested.
    """

    source: str
    observation_precision: str
    index: int
    server_tick: str
    world_full_time: str
    wall_nanos: str
    world: str
    player: str
    bridge_recv_monotonic_ns: str
    l0_checked: bool
    action_bound: bool
    paper_native_source_authenticated: bool

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        if (
            self.source != "PAPER_SCHEDULER_CALLBACK_ONLY"
            or self.observation_precision != "PAPER_PLUGIN_MESSAGE_RECEIVED_LATER"
            or type(self.index) is not int or not 1 <= self.index <= 256
            or any(
                type(v) is not str
                or re.fullmatch(r"(0|[1-9][0-9]*)", v) is None
                or int(v) >= 2**63
                for v in (self.server_tick, self.world_full_time, self.wall_nanos)
            )
            or type(self.bridge_recv_monotonic_ns) is not str
            or re.fullmatch(r"[1-9][0-9]*", self.bridge_recv_monotonic_ns) is None
            or int(self.bridge_recv_monotonic_ns) >= 2**63
            or type(self.world) is not str
            or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", self.world) is None
            or type(self.player) is not str
            or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", self.player) is None
            or self.l0_checked is not False
            or self.action_bound is not False
            or self.paper_native_source_authenticated is not False
        ):
            raise MineflayerAdapterProtocolError("unqualified Paper tick transport sample")



@dataclass(frozen=True, slots=True)
class MineflayerPaperSnapshot(MineflayerMessage):
    data: dict

    def __post_init__(self):
        MineflayerMessage.__post_init__(self)
        from adapters.mineflayer.t1f_protocol import validate_result
        try:
            validate_result(self.data)
        except (ValueError, TypeError, KeyError) as exc:
            raise MineflayerAdapterProtocolError(str(exc)) from exc

    @property
    def paper_sample_index(self):
        return self.data["snapshot"]["index"]

    @property
    def paper_server_tick(self):
        return str(self.data["snapshot"]["tick"])

    @property
    def paper_world(self):
        return self.data["snapshot"]["world"]

    @property
    def paper_player(self):
        return self.data["snapshot"]["player"]


@dataclass(frozen=True, slots=True)
class MineflayerPaperL0Shadow(MineflayerMessage):
    """Synchronous client-cache scan after a delivered Paper tick.

    Source freshness, origin authentication and physical motor outcome are
    explicitly NOT claimed. Not an Action issuer nor T0 TPS admission.
    """

    source: str
    observation_precision: str
    paper_sample_index: int
    paper_server_tick: str
    paper_world: str
    paper_player: str
    evaluation_duration_ns: str
    assessment: str
    cached_body_observed: bool
    l0_shadow_evaluated: bool
    l0_fresh_world_tick_attested: bool
    authorized_action_issued: bool
    tps_admission_granted: bool

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        positive = r"(0|[1-9][0-9]*)"
        uuid = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
        if (
            self.source != "MINEFLAYER_CACHE_SHADOW_L0_DEV"
            or self.observation_precision != "CLIENT_CACHE_POST_PAPER_MESSAGE_NOT_EPOCH_FRESH"
            or type(self.paper_sample_index) is not int
            or not 1 <= self.paper_sample_index <= 256
            or type(self.paper_server_tick) is not str
            or re.fullmatch(positive, self.paper_server_tick) is None
            or int(self.paper_server_tick) >= 2**63
            or type(self.paper_world) is not str
            or re.fullmatch(uuid, self.paper_world) is None
            or type(self.paper_player) is not str
            or re.fullmatch(uuid, self.paper_player) is None
            or type(self.evaluation_duration_ns) is not str
            or re.fullmatch(positive, self.evaluation_duration_ns) is None
            or int(self.evaluation_duration_ns) >= 2**63
            or type(self.assessment) is not str
            or self.assessment not in {
                "UNKNOWN", "LOW_HEALTH", "LOW_FOOD",
                "KNOWN_NEAR_HOSTILE", "NO_KNOWN_URGENT_SIGNAL",
            }
            or type(self.cached_body_observed) is not bool
            or self.l0_shadow_evaluated is not True
            or self.l0_fresh_world_tick_attested is not False
            or self.authorized_action_issued is not False
            or self.tps_admission_granted is not False
            or (not self.cached_body_observed and self.assessment != "UNKNOWN")
        ):
            raise MineflayerAdapterProtocolError("unqualified Paper L0 cache shadow")


@dataclass(frozen=True, slots=True)
class MineflayerEntityHurt(MineflayerMessage):
    entity_id: int
    source_entity_id: int | None
    actor_entity_id: int

    def __post_init__(self) -> None:
        MineflayerMessage.__post_init__(self)
        _require_non_negative_int("hurt entity_id", self.entity_id)
        if self.source_entity_id is not None:
            _require_non_negative_int(
                "hurt source_entity_id",
                self.source_entity_id,
            )
        _require_non_negative_int(
            "hurt actor_entity_id",
            self.actor_entity_id,
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
    MineflayerNativeClockPacket,
    MineflayerPaperTickSample,
    MineflayerPaperL0Shadow,
    MineflayerPaperSnapshot,
    MineflayerEntityHurt,
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
        keys = {"type", "session_id", "seq", "kind", "snapshot"}
        if "request_id" in payload:
            keys.add("request_id")
            _require_probe_request_id(payload["request_id"])
        _require_exact_keys("observation", payload, keys)
        return MineflayerObservation(
            session_id=session_id,
            seq=seq,
            kind=_decoded_text("observation kind", payload["kind"]),
            snapshot=_decode_snapshot(payload["snapshot"]),
            request_id=payload.get("request_id"),
        )

    if message_type == "native_clock_packet":
        _require_exact_keys(
            "native_clock_packet", payload,
            {
                "type", "session_id", "seq", "source",
                "observation_precision", "world_age_ticks",
                "world_day_time_raw_ticks", "tick_day_time",
                "host_monotonic_ns", "command_effect_tick_attested",
            },
        )
        return MineflayerNativeClockPacket(
            session_id=session_id, seq=seq,
            source=payload["source"],
            observation_precision=payload["observation_precision"],
            world_age_ticks=payload["world_age_ticks"],
            world_day_time_raw_ticks=payload["world_day_time_raw_ticks"],
            tick_day_time=payload["tick_day_time"],
            host_monotonic_ns=payload["host_monotonic_ns"],
            command_effect_tick_attested=payload["command_effect_tick_attested"],
        )

    if message_type == "paper_snapshot":
        _require_exact_keys("paper_snapshot", payload, {"type", "session_id", "seq", "data"})
        return MineflayerPaperSnapshot(session_id=session_id, seq=seq, data=payload["data"])

    if message_type == "paper_tick_sample":
        _require_exact_keys(
            "paper_tick_sample", payload,
            {
                "type", "session_id", "seq", "source",
                "observation_precision", "index", "server_tick",
                "world_full_time", "wall_nanos", "world", "player",
                "bridge_recv_monotonic_ns", "l0_checked", "action_bound",
                "paper_native_source_authenticated",
            },
        )
        return MineflayerPaperTickSample(
            session_id=session_id, seq=seq,
            source=payload["source"],
            observation_precision=payload["observation_precision"],
            index=payload["index"],
            server_tick=payload["server_tick"],
            world_full_time=payload["world_full_time"],
            wall_nanos=payload["wall_nanos"],
            world=payload["world"], player=payload["player"],
            bridge_recv_monotonic_ns=payload["bridge_recv_monotonic_ns"],
            l0_checked=payload["l0_checked"],
            action_bound=payload["action_bound"],
            paper_native_source_authenticated=payload["paper_native_source_authenticated"],
        )

    if message_type == "paper_l0_shadow":
        _require_exact_keys(
            "paper_l0_shadow", payload,
            {
                "type", "session_id", "seq", "source",
                "observation_precision", "paper_sample_index",
                "paper_server_tick", "paper_world", "paper_player",
                "evaluation_duration_ns", "assessment", "cached_body_observed",
                "l0_shadow_evaluated", "l0_fresh_world_tick_attested",
                "authorized_action_issued", "tps_admission_granted",
            },
        )
        return MineflayerPaperL0Shadow(
            session_id=session_id, seq=seq,
            source=payload["source"],
            observation_precision=payload["observation_precision"],
            paper_sample_index=payload["paper_sample_index"],
            paper_server_tick=payload["paper_server_tick"],
            paper_world=payload["paper_world"],
            paper_player=payload["paper_player"],
            evaluation_duration_ns=payload["evaluation_duration_ns"],
            assessment=payload["assessment"],
            cached_body_observed=payload["cached_body_observed"],
            l0_shadow_evaluated=payload["l0_shadow_evaluated"],
            l0_fresh_world_tick_attested=payload["l0_fresh_world_tick_attested"],
            authorized_action_issued=payload["authorized_action_issued"],
            tps_admission_granted=payload["tps_admission_granted"],
        )

    if message_type == "entity_hurt":
        _require_exact_keys(
            "entity_hurt",
            payload,
            {
                "type",
                "session_id",
                "seq",
                "entity_id",
                "source_entity_id",
                "actor_entity_id",
            },
        )
        source_entity_id = payload["source_entity_id"]
        if source_entity_id is not None:
            source_entity_id = _decoded_non_negative_int(
                "hurt source_entity_id",
                source_entity_id,
            )
        return MineflayerEntityHurt(
            session_id=session_id,
            seq=seq,
            entity_id=_decoded_non_negative_int(
                "hurt entity_id",
                payload["entity_id"],
            ),
            source_entity_id=source_entity_id,
            actor_entity_id=_decoded_non_negative_int(
                "hurt actor_entity_id",
                payload["actor_entity_id"],
            ),
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


def encode_attack_entity(action_id: str, *, entity_id: int) -> str:
    _require_text("action_id", action_id)
    _require_non_negative_int("entity_id", entity_id)
    return _encode_command(
        {
            "type": "effect",
            "action_id": action_id,
            "effect": "attack_entity",
            "entity_id": entity_id,
        }
    )


def encode_observe(request_id: str | None = None) -> str:
    if request_id is None:
        return _encode_command({"type": "observe"})
    _require_probe_request_id(request_id)
    return _encode_command({"type": "observe", "request_id": request_id})


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
            "food_saturation",
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
        food_saturation=_decoded_non_negative_number(
            "food_saturation",
            payload["food_saturation"],
        ),
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


def _require_probe_request_id(value: object) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or not value[0].isascii()
        or not value[0].isalnum()
        or any(
            not char.isascii() or (
                not char.isalnum() and char not in "._:-"
            )
            for char in value
        )
    ):
        raise MineflayerAdapterProtocolError(
            "probe request_id must be 1..128 ASCII identifier characters"
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
