"""DEV-only read-only zombie melee cue review over existing native probe Present.

This module deliberately does NOT infer a visible raised arm, a confirmed
attack, future damage, or an authorized Action. A Mineflayer entitySwingArm
event is not yet wired to this product protocol and its timing relative to
damage is not established. The optional motion cue is SYNTHETIC ONLY.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from adapters.mineflayer.present_projection import (
    MinecraftEntityPresent,
    MinecraftPresent,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
)

_MOTION_SOURCE = "SYNTHETIC_EVENT"


class MeleeCueRejected(ValueError):
    """Unbounded, stale, foreign, or invented cue provenance."""


class L0ContactStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    POSSIBLE_CONTACT = "POSSIBLE_CONTACT"
    NOT_INDICATED = "NOT_INDICATED"


class L1MotionStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    ARM_SWING_OBSERVED_SYNTHETIC = "ARM_SWING_OBSERVED_SYNTHETIC"


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise MeleeCueRejected(f"invalid {name}")


def _integer(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise MeleeCueRejected(f"invalid {name}")


def _position_distance(entity: MinecraftEntityPresent,
                       current: MinecraftPresent) -> float:
    ex, ey, ez = entity.position
    bx, by, bz = current.body_position
    if not all(math.isfinite(v) for v in (ex, ey, ez, bx, by, bz)):
        raise MeleeCueRejected("non-finite native position")
    d = math.dist((ex, ey, ez), (bx, by, bz))
    if not math.isfinite(entity.distance_m) or (
        abs(d - entity.distance_m) > 0.02
    ):
        raise MeleeCueRejected("inconsistent native distance")
    return d


@dataclass(frozen=True, slots=True)
class ZombieMeleeFrame:
    """One already projected correlated native probe, not World authority."""

    self_id: str
    present: MinecraftPresent

    def __post_init__(self) -> None:
        _text("self_id", self.self_id)
        if not isinstance(self.present, MinecraftPresent):
            raise MeleeCueRejected("existing typed MinecraftPresent required")
        p = self.present
        _text("session_id", p.session_id)
        _text("request_id", p.request_id)
        _integer("native seq", p.seq)
        if p.provenance.source != "mineflayer" or (
            p.provenance.reference != f"{p.session_id}:{p.seq}"
        ):
            raise MeleeCueRejected("uncorrelated Mineflayer source")
        n = len(p.observed_entities)
        if (
            p.coverage_scope != MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE
            or p.coverage_radius_m != MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE
            or p.coverage_cap != MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES
            or p.coverage_candidates < n
            or n > p.coverage_cap
        ):
            raise MeleeCueRejected("unqualified bounded entity coverage")
        if p.coverage_truncated:
            if n != p.coverage_cap or (
                p.coverage_candidates <= p.coverage_cap
            ):
                raise MeleeCueRejected("inconsistent truncated coverage")
        elif p.coverage_candidates != n:
            raise MeleeCueRejected("inconsistent full coverage")

    @property
    def source_ref(self) -> str:
        p = self.present
        return f"present:{p.session_id}:{p.seq}:{p.request_id}"


@dataclass(frozen=True, slots=True)
class SyntheticArmSwing:
    """A fixture stand-in for a NOT-YET-ADMITTED native motion event.

    Neither attack wind-up, swing-before-contact timing nor hostile intent
    are established by this signal.
    """

    self_id: str
    session_id: str
    entity_id: int
    event_seq: int
    event_ref: str
    source_scope: Literal["SYNTHETIC_EVENT"] = _MOTION_SOURCE

    def __post_init__(self) -> None:
        for name in ("self_id", "session_id", "event_ref"):
            _text(name, getattr(self, name))
        _integer("entity_id", self.entity_id)
        _integer("event_seq", self.event_seq)
        if self.source_scope != _MOTION_SOURCE:
            raise MeleeCueRejected("native animation evidence not established")


@dataclass(frozen=True, slots=True)
class ZombieMeleeCueReview:
    self_id: str
    session_id: str
    target_entity_id: int
    current_source_ref: str
    prior_source_ref: str | None
    arm_source_ref: str | None
    l0_contact: L0ContactStatus
    l1_motion: L1MotionStatus
    observed_distance_m: float | None
    contact_radius_m: float
    # Read-only assessment, not Action authorization or learning.


def _observed_zombie(
    frame: ZombieMeleeFrame, entity_id: int,
) -> MinecraftEntityPresent | None:
    matches = [
        e for e in frame.present.observed_entities
        if e.entity_id == entity_id
    ]
    if len(matches) > 1:
        raise MeleeCueRejected("duplicate entity identity")
    if not matches or matches[0].name != "zombie":
        return None
    return matches[0]


def review_zombie_melee(
    *,
    current: ZombieMeleeFrame,
    target_entity_id: int,
    prior: ZombieMeleeFrame | None = None,
    arm_swing: SyntheticArmSwing | None = None,
    contact_radius_m: float,
    max_native_seq_gap: int = 12,
) -> ZombieMeleeCueReview:
    """Estimate *possible* approach/contact and a distinct synthetic arm cue.

    Native seq gap bounds ordering, not physical elapsed time. Contact radius
    is an experimenter-supplied hypothesis, NOT measured zombie attack range.
    A missing entity or motion event never means 'safe' or 'no attack'.
    """
    if not isinstance(current, ZombieMeleeFrame):
        raise MeleeCueRejected("current native frame required")
    _integer("target_entity_id", target_entity_id)
    _integer("max_native_seq_gap", max_native_seq_gap)
    if max_native_seq_gap < 1:
        raise MeleeCueRejected("positive bounded native seq gap required")
    if (type(contact_radius_m) not in (int, float)
            or not math.isfinite(contact_radius_m)
            or contact_radius_m <= 0):
        raise MeleeCueRejected("positive finite contact threshold required")

    if prior is not None:
        if not isinstance(prior, ZombieMeleeFrame):
            raise MeleeCueRejected("typed prior frame required")
        if (prior.self_id != current.self_id
                or prior.present.session_id != current.present.session_id):
            raise MeleeCueRejected("cross-Self/session frame")
        if prior.present.seq >= current.present.seq:
            raise MeleeCueRejected("stale or repeated frame")
        if prior.present.request_id == current.present.request_id:
            raise MeleeCueRejected("repeated probe request")

    if arm_swing is not None:
        if not isinstance(arm_swing, SyntheticArmSwing):
            raise MeleeCueRejected("typed synthetic motion evidence required")
        if (arm_swing.self_id != current.self_id
                or arm_swing.session_id != current.present.session_id
                or arm_swing.entity_id != target_entity_id):
            raise MeleeCueRejected("foreign arm event")
        if arm_swing.event_seq > current.present.seq or (
            prior is not None and arm_swing.event_seq <= prior.present.seq
        ):
            raise MeleeCueRejected("future/stale synthetic arm event")
        if arm_swing.event_ref in (
            current.source_ref,
            prior.source_ref if prior is not None else None,
        ):
            raise MeleeCueRejected("arm event replayed native probe source")

    now = _observed_zombie(current, target_entity_id)
    l0 = L0ContactStatus.UNKNOWN
    l1 = L1MotionStatus.UNKNOWN
    distance = None
    if now is not None:
        distance = _position_distance(now, current.present)
        if prior is not None and (
            current.present.seq - prior.present.seq <= max_native_seq_gap
        ):
            earlier = _observed_zombie(prior, target_entity_id)
            if earlier is not None:
                earlier_d = _position_distance(earlier, prior.present)
                if distance <= contact_radius_m and distance < earlier_d - 0.01:
                    l0 = L0ContactStatus.POSSIBLE_CONTACT
                else:
                    l0 = L0ContactStatus.NOT_INDICATED
        if arm_swing is not None:
            l1 = L1MotionStatus.ARM_SWING_OBSERVED_SYNTHETIC
    return ZombieMeleeCueReview(
        self_id=current.self_id,
        session_id=current.present.session_id,
        target_entity_id=target_entity_id,
        current_source_ref=current.source_ref,
        prior_source_ref=prior.source_ref if prior is not None else None,
        arm_source_ref=arm_swing.event_ref if arm_swing is not None else None,
        l0_contact=l0,
        l1_motion=l1,
        observed_distance_m=distance,
        contact_radius_m=float(contact_radius_m),
    )
