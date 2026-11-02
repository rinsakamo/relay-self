"""L Zombie v0: bounded same-entity, exact-tick, read-only prediction shadow.

A position pair is a *candidate* only. Original Mineflayer nearby-entity
snapshots carry entity_id but no stable spawn instance or authoritative tick;
neither native seq nor host monotonic time can be treated as a World tick.
A future physical observer must independently witness entity UUID/spawn
continuity and source-bound tick/position before admitting these rows.

No Action, entity spawn/kill, physics edit, training, model calls or I/O here.
Never count offline examples as a real zombie or B1 achievement.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass

HORIZON_TICKS = 20
MAX_PRIOR_GAP_TICKS = 40
MAX_HORIZONTAL_SPEED_M_PER_TICK = 1.5
MAX_POSITION_M = 30_000_000
MAX_FORECAST_DISPLACEMENT_M = 40.0
SOURCE_KIND = "EXACT_SERVER_TICK_ZOMBIE_POSITION_V0"
MAX_RAW_BYTES = 4096


class ZombieSourceRejected(ValueError):
    """Identity, time, observation, prediction or temporal order isn't qualified."""


@dataclass(frozen=True, slots=True)
class ZombiePosition:
    """Parsed source row; the PAPER authority must be *separately* authenticated."""

    world_uuid: str
    session_id: str
    entity_uuid: str
    entity_id: int
    spawn_instance: int
    native_seq: int
    server_tick: int
    x_m: float
    y_m: float
    z_m: float
    source_sha256: str
    source_kind: str = SOURCE_KIND
    complete_coverage: bool = True
    externally_authenticated: bool = False

    @property
    def identity(self) -> tuple[str, str, str, int, int]:
        return (
            self.world_uuid, self.session_id, self.entity_uuid,
            self.entity_id, self.spawn_instance,
        )


@dataclass(frozen=True, slots=True)
class ZombieForecast:
    """Frozen at pre-outcome tick, never retroactively re-evaluated."""

    identity: tuple[str, str, str, int, int]
    issued_server_tick: int
    target_server_tick: int
    target_kind: str
    predicted_x_m: float | None
    predicted_z_m: float | None
    forecast_status: str
    model_label: str
    prior_source_sha256: tuple[str, str]
    proposal_sha256: str
    action_authority: bool = False
    learning_authority: bool = False


@dataclass(frozen=True, slots=True)
class ZombiePredictionReview:
    forecast_sha256: str
    actual_source_sha256: str
    source_identity_matched: bool
    target_tick_exact: bool
    horizontal_error_m: float | None
    forecast_status: str
    source_authenticated: bool
    result: str
    action_authority: bool = False
    learning_admitted: bool = False


def _strict_uuid(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = uuid.UUID(value)
        return parsed.version in (1, 2, 3, 4, 5) and str(parsed) == value
    except (ValueError, AttributeError):
        return False


def _finite_coordinate(value: object) -> bool:
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and abs(value) <= MAX_POSITION_M
    )


def _token(value: object) -> bool:
    return (
        type(value) is str and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value)
        is not None
    )


def parse_zombie_source(raw: bytes, *, claimed_sha256: str) -> ZombiePosition:
    """Strictly read exact ORIGINAL-shaped row bytes, without granting authority.

    An attacker can create perfectly shaped fake Paper bytes. Raw row SHA
    does NOT establish a true Paper source; a separate independent auditor
    must verify the origin and its pre-outcome/after-outcome capture boundary.
    """
    if (
        type(raw) is not bytes or not 0 < len(raw) <= MAX_RAW_BYTES
        or not raw.endswith(b"\n")
        or type(claimed_sha256) is not str
        or not re.fullmatch(r"[a-f0-9]{64}", claimed_sha256)
        or hashlib.sha256(raw).hexdigest() != claimed_sha256
    ):
        raise ZombieSourceRejected("missing original-shaped bounded exact bytes/SHA")
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ZombieSourceRejected("invalid original-shaped source JSON") from exc
    keys = {
        "source_kind", "world_uuid", "session_id", "entity_uuid",
        "entity_id", "spawn_instance", "native_seq", "server_tick",
        "x_m", "y_m", "z_m", "complete_coverage",
    }
    if type(obj) is not dict or set(obj) != keys:
        raise ZombieSourceRejected("missing/extra original source keys")
    if (
        obj["source_kind"] != SOURCE_KIND
        or not _strict_uuid(obj["world_uuid"])
        or not _strict_uuid(obj["entity_uuid"])
        or not _token(obj["session_id"])
        or type(obj["entity_id"]) is not int
        or not 0 <= obj["entity_id"] < (2**31)
        or type(obj["spawn_instance"]) is not int
        or not 0 < obj["spawn_instance"] < (2**31)
        or type(obj["native_seq"]) is not int
        or not 0 <= obj["native_seq"] < (2**63)
        or type(obj["server_tick"]) is not int
        or not 0 <= obj["server_tick"] < (2**63)
        or not all(_finite_coordinate(obj[key]) for key in ("x_m", "y_m", "z_m"))
        or obj["complete_coverage"] is not True
    ):
        raise ZombieSourceRejected("unqualified entity/world/tick/position/coverage")
    return ZombiePosition(
        **{key: value for key, value in obj.items() if key != "source_kind"},
        source_sha256=claimed_sha256,
    )


def _prior_pair(first: ZombiePosition, second: ZombiePosition) -> None:
    if not isinstance(first, ZombiePosition) or not isinstance(second, ZombiePosition):
        raise ZombieSourceRejected("typed two-prior original positions required")
    if (
        first.identity != second.identity
        or not first.complete_coverage or not second.complete_coverage
        or first.source_sha256 == second.source_sha256
        or second.native_seq <= first.native_seq
        or not 0 < second.server_tick-first.server_tick <= MAX_PRIOR_GAP_TICKS
    ):
        raise ZombieSourceRejected("entity was replaced, lost or time source not ordered")
    speed = math.hypot(second.x_m-first.x_m, second.z_m-first.z_m) / (
        second.server_tick-first.server_tick
    )
    if not math.isfinite(speed) or speed > MAX_HORIZONTAL_SPEED_M_PER_TICK:
        raise ZombieSourceRejected("teleport or identity discontinuity, not a motion sample")


def _freeze(
    first: ZombiePosition, second: ZombiePosition, *,
    forecast_status: str, model_label: str,
    predicted_x_m: float | None, predicted_z_m: float | None,
) -> ZombieForecast:
    _prior_pair(first, second)
    numeric = forecast_status == "NUMERIC_ESTIMATE"
    if (
        forecast_status not in {"NUMERIC_ESTIMATE", "ABSTAIN_UNQUALIFIED"}
        or (numeric != (predicted_x_m is not None and predicted_z_m is not None))
        or (numeric and not (
            _finite_coordinate(predicted_x_m) and _finite_coordinate(predicted_z_m)
        ))
        or (not numeric and (predicted_x_m is not None or predicted_z_m is not None))
    ):
        raise ZombieSourceRejected("numeric point or explicit abstention required")
    if numeric and math.hypot(
        predicted_x_m-second.x_m, predicted_z_m-second.z_m
    ) > MAX_FORECAST_DISPLACEMENT_M:
        raise ZombieSourceRejected("candidate 20 tick motion exceeds conservative bound")
    details = dict(
        identity=second.identity,
        issued_server_tick=second.server_tick,
        target_server_tick=second.server_tick+HORIZON_TICKS,
        target_kind="ZOMBIE_HORIZONTAL_POSITION_XZ_METERS",
        predicted_x_m=predicted_x_m,
        predicted_z_m=predicted_z_m,
        forecast_status=forecast_status,
        model_label=model_label,
        prior_source_sha256=(first.source_sha256, second.source_sha256),
    )
    digest = hashlib.sha256(json.dumps(
        details, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode()).hexdigest()
    return ZombieForecast(**details, proposal_sha256=digest)


def baseline_forecasts(
    first: ZombiePosition, second: ZombiePosition,
) -> tuple[ZombieForecast, ZombieForecast]:
    """CHEAP controls: stationary vs 2-sample constant velocity; NOT learned."""
    _prior_pair(first, second)
    delta_tick = second.server_tick-first.server_tick
    x_delta = second.x_m-first.x_m
    z_delta = second.z_m-first.z_m
    return (
        _freeze(first, second, forecast_status="NUMERIC_ESTIMATE",
                model_label="CHEAP_STATIONARY",
                predicted_x_m=second.x_m, predicted_z_m=second.z_m),
        _freeze(first, second, forecast_status="NUMERIC_ESTIMATE",
                model_label="CHEAP_CONSTANT_VELOCITY",
                predicted_x_m=second.x_m + x_delta*HORIZON_TICKS/delta_tick,
                predicted_z_m=second.z_m + z_delta*HORIZON_TICKS/delta_tick),
    )


def shadow_forecast(
    first: ZombiePosition, second: ZombiePosition, *,
    predicted_x_m: float | None, predicted_z_m: float | None,
) -> ZombieForecast:
    """Read-only L2 candidate, no native L2 call and no World permission."""
    return _freeze(
        first, second,
        forecast_status=(
            "ABSTAIN_UNQUALIFIED" if predicted_x_m is None and predicted_z_m is None
            else "NUMERIC_ESTIMATE"
        ),
        model_label="L2_UNADMITTED_SHADOW",
        predicted_x_m=predicted_x_m, predicted_z_m=predicted_z_m,
    )


def review_forecast(
    forecast: ZombieForecast, actual: ZombiePosition,
) -> ZombiePredictionReview:
    """Only an EXACT target tick and SAME real spawn can score a forecast."""
    if not isinstance(forecast, ZombieForecast) or not isinstance(actual, ZombiePosition):
        raise ZombieSourceRejected("typed frozen forecast and future sample required")
    if (
        actual.identity != forecast.identity
        or not actual.complete_coverage
        or actual.server_tick != forecast.target_server_tick
        or actual.source_sha256 in forecast.prior_source_sha256
    ):
        raise ZombieSourceRejected("target zombie replaced, missed or not exact 20 ticks")
    if forecast.forecast_status == "ABSTAIN_UNQUALIFIED":
        error = None
        result = "ABSTAIN_NO_NUMERIC_ERROR"
    elif forecast.forecast_status == "NUMERIC_ESTIMATE":
        error = math.hypot(
            forecast.predicted_x_m-actual.x_m,
            forecast.predicted_z_m-actual.z_m,
        )
        result = "SCORED_OFFLINE_ONLY"
    else:
        raise ZombieSourceRejected("unknown forecast revision/status")
    return ZombiePredictionReview(
        forecast_sha256=forecast.proposal_sha256,
        actual_source_sha256=actual.source_sha256,
        source_identity_matched=True,
        target_tick_exact=True,
        horizontal_error_m=error,
        forecast_status=forecast.forecast_status,
        source_authenticated=False,  # never infer Paper authenticity from a hash
        result=result,
    )


def report_json(review: ZombiePredictionReview) -> str:
    """Read-only synthetic review export; contains zero runtime/model claims."""
    return json.dumps(asdict(review), ensure_ascii=False, sort_keys=True)
