"""M0.2 exhaustibility specification and offline arithmetic (Issue #616).

This does NOT install a Paper plugin, mutate a Minecraft player, attest a World
source, or independently credit food. The *server* owns hunger/saturation/HP.
These helpers are a reference contract for a future S/R-owned Paper adapter.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

Unit = Literal["tick", "block", "event", "hp", "work"]

# ExhaustionReason enum, Paper Java 1.21.8. BASAL and COGNITION are synthetic.
# 'native' is necessary for events without one invariant numeric vanilla amount.
UNITS: dict[str, Unit] = {
    "BASAL": "tick",
    "WALK": "block",
    "CROUCH": "block",
    "SPRINT": "block",
    "SWIM": "block",
    "WALK_ON_WATER": "event",
    "WALK_UNDERWATER": "event",
    "JUMP": "event",
    "JUMP_SPRINT": "event",
    "ATTACK": "event",
    "DAMAGED": "event",
    "BLOCK_MINED": "event",
    "REGEN": "hp",
    "HUNGER_EFFECT": "event",
    "UNKNOWN": "event",
    "COGNITION": "work",
}
SYNTHETIC = frozenset(("BASAL", "COGNITION"))
EVENT_REASONS = frozenset(UNITS) - SYNTHETIC
PER_CENTIMETER = frozenset(("WALK", "CROUCH", "SPRINT", "SWIM"))
NATIVE_REQUIRED = frozenset(("WALK_ON_WATER", "WALK_UNDERWATER", "HUNGER_EFFECT", "UNKNOWN"))


class M02Rejected(ValueError):
    """A profile or event has a non-physical or unqualified shape."""


def _nonnegative(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _mapping(value: object, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise M02Rejected(f"unexpected or missing fields: expected {sorted(keys)}")
    return value


@dataclass(frozen=True)
class Rate:
    unit: Unit
    standard: float | Literal["native"]
    multiplier: float = 1.0
    additional: float = 0.0
    enabled: bool = True

    def validate(self, name: str) -> None:
        if name not in UNITS or self.unit != UNITS[name]:
            raise M02Rejected("unknown action/unit mismatch")
        if self.standard == "native":
            if name not in NATIVE_REQUIRED:
                raise M02Rejected("native standard only for variable vanilla events")
        elif not _nonnegative(self.standard):
            raise M02Rejected("standard must be finite and nonnegative")
        if not _nonnegative(self.multiplier) or not _nonnegative(self.additional):
            raise M02Rejected("multiplier/additional must be finite nonnegative")
        if type(self.enabled) is not bool:
            raise M02Rejected("enabled must be boolean")
        if name != "COGNITION" and not self.enabled:
            raise M02Rejected("only optional cognition can be disabled")
        if name == "COGNITION" and self.enabled and self.standard == 0 and self.additional == 0:
            raise M02Rejected("enabled cognition requires a real nonzero rate")


@dataclass(frozen=True)
class Profile:
    profile_id: str
    minecraft_version: str
    calibration_status: str
    standard_food: str
    rates: tuple[tuple[str, Rate], ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.profile_id, str) or not self.profile_id.strip()
            or self.minecraft_version != "1.21.8"
            or self.calibration_status not in ("candidate_uncalibrated", "qualified")
            or self.standard_food != "cooked_beef"
        ):
            raise M02Rejected("M0.2 requires named 1.21.8 steak ecology profile")
        if {name for name, _ in self.rates} != set(UNITS) or len(self.rates) != len(UNITS):
            raise M02Rejected("every known exhaustion kind must have one explicit rate")
        for name, rate in self.rates:
            rate.validate(name)

    def rule(self, name: str) -> Rate:
        for kind, rule in self.rates:
            if name == kind:
                return rule
        raise M02Rejected("unknown action type")

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "version": "M0.2",
            "profile_id": self.profile_id,
            "minecraft_version": self.minecraft_version,
            "calibration_status": self.calibration_status,
            "standard_food": self.standard_food,
            "actions": {
                name: {
                    "unit": rate.unit,
                    "standard": rate.standard,
                    "multiplier": rate.multiplier,
                    "additional": rate.additional,
                    "enabled": rate.enabled,
                }
                for name, rate in sorted(self.rates)
            },
        }

    @property
    def sha256(self) -> str:
        payload = json.dumps(self.canonical_dict(), sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_profile(document: object) -> Profile:
    data = _mapping(document, {
        "version", "profile_id", "minecraft_version", "calibration_status",
        "standard_food", "actions",
    })
    if data["version"] != "M0.2":
        raise M02Rejected("unsupported profile version")
    actions = data["actions"]
    if not isinstance(actions, dict) or set(actions) != set(UNITS):
        raise M02Rejected("all M0.2 action entries required")
    rows: list[tuple[str, Rate]] = []
    for name, value in sorted(actions.items()):
        fields = _mapping(value, {
            "unit", "standard", "multiplier", "additional", "enabled",
        })
        rate = Rate(**fields)
        rate.validate(name)
        rows.append((name, rate))
    return Profile(
        profile_id=data["profile_id"],
        minecraft_version=data["minecraft_version"],
        calibration_status=data["calibration_status"],
        standard_food=data["standard_food"],
        rates=tuple(rows),
    )


def load_profile(path: str | Path) -> Profile:
    try:
        # No implicit NaN/Infinity and no silently overridden duplicate JSON keys.
        def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise M02Rejected("duplicate configuration field")
                result[key] = value
            return result

        def invalid_constant(value: str) -> None:
            raise M02Rejected(f"invalid numeric constant {value}")

        document = json.loads(Path(path).read_text(encoding="utf-8"),
                              object_pairs_hook=unique_keys,
                              parse_constant=invalid_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M02Rejected("cannot read/parse M0.2 profile") from exc
    return parse_profile(document)


def cost(
    profile: Profile,
    action: str,
    quantity: float,
    *,
    native_event_exhaustion: float | None = None,
) -> float:
    """q * (standard * multiplier + additional), in Minecraft exhaustion.

    Event standard 'native' means actual observed vanilla event amount for a
    *single* event. Do not feed a per-cm amount then multiply by block distance.
    Cognition is OFF by default and its usage is not inferred from elapsed time.
    """
    rate = profile.rule(action)
    if not _nonnegative(quantity):
        raise M02Rejected("quantity must be finite nonnegative")
    if rate.unit in ("tick", "event") and (
        type(quantity) is not int or quantity < 0
    ):
        raise M02Rejected("tick/event quantity must be an integer")
    if action in NATIVE_REQUIRED:
        if rate.unit != "event" or quantity != 1:
            raise M02Rejected("native standard requires one original event")
        if not _nonnegative(native_event_exhaustion):
            raise M02Rejected("finite original native event exhaustion required")
        base = native_event_exhaustion
    else:
        if native_event_exhaustion is not None:
            if not _nonnegative(native_event_exhaustion):
                raise M02Rejected("invalid original event exhaustion")
            # Do not turn this input into an extra bill. Adapter must replace
            # the native event with cost(...), not add both.
        base = rate.standard
    if not rate.enabled:
        return 0.0
    value = quantity * (base * rate.multiplier + rate.additional)
    if not math.isfinite(value):
        raise M02Rejected("nonfinite computed exhaustion")
    return value


def paper_event_cost(
    profile: Profile,
    reason: str,
    *,
    native_event_exhaustion: float,
    distance_centimeters: float | None = None,
    healed_hp: float | None = None,
) -> float:
    """Reference event REPLACEMENT amount for future Paper listener.

    Paper movement reasons fire per centimeter. Guard unlike event dimensions
    so no one accidentally bills 100 times too much by treating cm as blocks.
    Unsupported/unhandled reasons are not silently coerced into custom costs.
    """
    if reason not in EVENT_REASONS:
        raise M02Rejected("not a supported Paper exhaustion reason")
    if not _nonnegative(native_event_exhaustion):
        raise M02Rejected("invalid native event exhaustion")
    if reason in PER_CENTIMETER:
        if not _nonnegative(distance_centimeters) or healed_hp is not None:
            raise M02Rejected("movement event requires distance in cm only")
        return cost(profile, reason, distance_centimeters / 100.0,
                    native_event_exhaustion=native_event_exhaustion)
    if reason == "REGEN":
        if not _nonnegative(healed_hp) or healed_hp <= 0 or distance_centimeters is not None:
            raise M02Rejected("REGEN requires observed restored HP")
        return cost(profile, reason, healed_hp,
                    native_event_exhaustion=native_event_exhaustion)
    if distance_centimeters is not None or healed_hp is not None:
        raise M02Rejected("nonmovement Paper reason cannot charge distance/HP")
    return cost(profile, reason, 1, native_event_exhaustion=native_event_exhaustion)


@dataclass(frozen=True)
class AuditState:
    """Offline-only deterministic cost diary; NOT a second energy ledger."""

    profile_sha256: str
    session_id: str
    world_tick: int
    paid_events: frozenset[str] = frozenset()
    total_exhaustion: float = 0.0


def start_audit(profile: Profile, session_id: str, world_tick: int) -> AuditState:
    if not isinstance(session_id, str) or not session_id:
        raise M02Rejected("session id required")
    if type(world_tick) is not int or world_tick < 0:
        raise M02Rejected("nonnegative monotonic World age required")
    return AuditState(profile.sha256, session_id, world_tick)


def bill_world_tick(profile: Profile, state: AuditState, world_tick: int) -> AuditState:
    if state.profile_sha256 != profile.sha256 or type(world_tick) is not int:
        raise M02Rejected("foreign profile / invalid World time")
    if world_tick != state.world_tick + 1:
        raise M02Rejected("missing, duplicate or nonmonotonic World tick")
    charge = cost(profile, "BASAL", 1)
    return replace(
        state, world_tick=world_tick,
        total_exhaustion=state.total_exhaustion + charge,
    )


def bill_event(
    profile: Profile, state: AuditState, *, session_id: str, world_tick: int,
    event_id: str, reason: str, native_event_exhaustion: float,
    distance_centimeters: float | None = None,
    healed_hp: float | None = None,
) -> AuditState:
    if state.profile_sha256 != profile.sha256 or session_id != state.session_id:
        raise M02Rejected("foreign profile / session")
    if type(world_tick) is not int or world_tick != state.world_tick:
        raise M02Rejected("World tick mismatch")
    if not isinstance(event_id, str) or not event_id or event_id in state.paid_events:
        raise M02Rejected("missing or duplicate event id")
    charge = paper_event_cost(
        profile, reason, native_event_exhaustion=native_event_exhaustion,
        distance_centimeters=distance_centimeters, healed_hp=healed_hp,
    )
    return replace(state, paid_events=state.paid_events | {event_id},
                   total_exhaustion=state.total_exhaustion + charge)
