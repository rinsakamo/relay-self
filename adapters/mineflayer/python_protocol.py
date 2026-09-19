from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

from relay_self.provenance import Provenance

MINEFLAYER_VERSION = "4.39.0"
MINEFLAYER_PROVENANCE_SOURCE = "mineflayer"

_OBSERVATION_KINDS = frozenset(
    {"spawn", "health", "move", "forcedMove", "death", "respawn"}
)
_EFFECTS = frozenset({"set_control", "clear_controls"})
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


@dataclass(frozen=True, slots=True)
class MineflayerSnapshot:
    health: float
    food: float
    oxygen_level: float
    position: MineflayerPosition

    def __post_init__(self) -> None:
        _require_non_negative_number("health", self.health)
        _require_non_negative_number("food", self.food)
        _require_non_negative_number("oxygen_level", self.oxygen_level)
        if not isinstance(self.position, MineflayerPosition):
            raise MineflayerAdapterProtocolError(
                "snapshot position must be MineflayerPosition"
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
        {"health", "food", "oxygen_level", "position"},
    )
    position = _require_mapping("position", payload["position"])
    _require_exact_keys("position", position, {"x", "y", "z"})
    return MineflayerSnapshot(
        health=_decoded_non_negative_number("health", payload["health"]),
        food=_decoded_non_negative_number("food", payload["food"]),
        oxygen_level=_decoded_non_negative_number(
            "oxygen_level",
            payload["oxygen_level"],
        ),
        position=MineflayerPosition(
            x=_decoded_number("position.x", position["x"]),
            y=_decoded_number("position.y", position["y"]),
            z=_decoded_number("position.z", position["z"]),
        ),
    )


def _require_mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MineflayerAdapterProtocolError(f"{name} must be an object")
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
