"""CPU-only, source-bound target acceptance conditions (Cognitive v0.1).

Target meaning/precision belongs to Goal+Target, not to the motor MOVE verb.
All assessments are *observational*: they never authorize a physical Action,
certify a World outcome, or convert a geometrical condition into Skill success.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance


class TargetContractRefusal(ValueError):
    """Target geometry, source, or requested evidence is invalid."""


class TargetKind(str, Enum):
    PLACE = "PLACE"
    RELATIVE_STEP = "RELATIVE_STEP"
    ENTITY_RANGE = "ENTITY_RANGE"


class ReferenceFrame(str, Enum):
    WORLD = "WORLD"
    SELF_AT_BIND = "SELF_AT_BIND"
    ENTITY_LIVE = "ENTITY_LIVE"


class TargetConditionStatus(str, Enum):
    OUTSIDE = "OUTSIDE"
    TOO_CLOSE = "TOO_CLOSE"
    VERTICAL_MISMATCH = "VERTICAL_MISMATCH"
    ALIGN_REQUIRED = "ALIGN_REQUIRED"
    BLOCKED = "BLOCKED"
    SETTLING = "SETTLING"
    CONDITION_OBSERVED = "CONDITION_OBSERVED"
    UNKNOWN = "UNKNOWN"


def _finite(name: str, value: float, *, minimum: float = 0,
            maximum: float = 1000) -> None:
    if (
        type(value) not in (int, float) or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise TargetContractRefusal(f"invalid {name}")


def _point(name: str, point: MineflayerPosition | None) -> None:
    if not isinstance(point, MineflayerPosition):
        raise TargetContractRefusal(f"{name} requires a finite world position")


def _id(name: str, value: str, *, target_ref: bool = False) -> None:
    permitted = r"[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}" if target_ref else (
        r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
    )
    if type(value) is not str or re.fullmatch(permitted, value) is None:
        raise TargetContractRefusal(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class ArrivalCondition:
    """Goal-demanded envelope, not a globally hardcoded motor tolerance.

    min/max_horizontal are distance from anchor (place/step) or live entity.
    max_still_drift_m is a *distinct* STOP stability requirement. A target
    requiring no standstill need not assert zero speed or 8 quiet ticks.
    """

    min_horizontal_m: float
    max_horizontal_m: float
    max_vertical_error_m: float
    still_ticks: int = 0
    max_still_drift_m: float | None = None
    max_speed_mps: float | None = None
    max_facing_error_rad: float | None = None
    require_line_of_sight: bool = False

    def __post_init__(self) -> None:
        _finite("minimum horizontal distance", self.min_horizontal_m, maximum=64)
        _finite("maximum horizontal distance", self.max_horizontal_m, maximum=64)
        _finite("vertical error", self.max_vertical_error_m, maximum=16)
        if self.max_horizontal_m < self.min_horizontal_m:
            raise TargetContractRefusal("inverted target distance interval")
        if type(self.still_ticks) is not int or not 0 <= self.still_ticks <= 200:
            raise TargetContractRefusal("invalid stillness interval")
        if self.still_ticks:
            if self.max_still_drift_m is None:
                raise TargetContractRefusal("stillness requires maximum drift")
            _finite("stillness drift", self.max_still_drift_m, maximum=1)
        elif self.max_still_drift_m is not None:
            raise TargetContractRefusal("drift cannot prove unspecified stillness")
        if self.max_speed_mps is not None:
            _finite("maximum body speed", self.max_speed_mps, maximum=40)
        if self.max_facing_error_rad is not None:
            _finite("maximum facing error", self.max_facing_error_rad,
                    maximum=math.pi)
        if type(self.require_line_of_sight) is not bool:
            raise TargetContractRefusal("invalid line-of-sight condition")


@dataclass(frozen=True, slots=True)
class TargetContract:
    """An immutable, digest-bound target-specific movement acceptance contract.

    A contract is not a selected L1 Option: any later issuer must independently
    bind the exact contract revision to the original selected Target/Goal.
    """

    scope: ScopeRef
    goal_id: str
    target_ref: str
    kind: TargetKind
    reference_frame: ReferenceFrame
    provenance: Provenance
    condition: ArrivalCondition
    bound_seq: int
    anchor: MineflayerPosition | None = None
    bound_origin: MineflayerPosition | None = None
    entity_id: str | None = None
    max_entity_age_seq: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise TargetContractRefusal("Self and World session scope required")
        _id("goal ID", self.goal_id)
        _id("selected target reference", self.target_ref, target_ref=True)
        if not isinstance(self.kind, TargetKind) or not isinstance(
            self.reference_frame, ReferenceFrame
        ):
            raise TargetContractRefusal("typed target kind and frame required")
        if not isinstance(self.provenance, Provenance) or not isinstance(
            self.condition, ArrivalCondition
        ):
            raise TargetContractRefusal("condition and original provenance required")
        if type(self.bound_seq) is not int or self.bound_seq < 0:
            raise TargetContractRefusal("invalid bound source sequence")
        if self.kind is TargetKind.PLACE:
            if (self.reference_frame is not ReferenceFrame.WORLD
                    or self.anchor is None or self.bound_origin is not None
                    or self.entity_id is not None or self.max_entity_age_seq is not None):
                raise TargetContractRefusal("PLACE needs only a source-bound world anchor")
            _point("place", self.anchor)
        elif self.kind is TargetKind.RELATIVE_STEP:
            if (self.reference_frame is not ReferenceFrame.SELF_AT_BIND
                    or self.anchor is None or self.bound_origin is None
                    or self.entity_id is not None or self.max_entity_age_seq is not None):
                raise TargetContractRefusal("STEP needs bound starting pose and endpoint")
            _point("relative step", self.anchor)
            _point("relative step origin", self.bound_origin)
            if math.dist(
                (self.anchor.x, self.anchor.y, self.anchor.z),
                (self.bound_origin.x, self.bound_origin.y, self.bound_origin.z),
            ) <= 0:
                raise TargetContractRefusal("relative STEP cannot be zero length")
            if self.condition.min_horizontal_m != 0:
                raise TargetContractRefusal("STEP endpoint requires zero minimum distance")
        elif self.kind is TargetKind.ENTITY_RANGE:
            if (self.reference_frame is not ReferenceFrame.ENTITY_LIVE
                    or self.anchor is not None or self.bound_origin is not None
                    or self.entity_id is None or self.max_entity_age_seq is None):
                raise TargetContractRefusal("ENTITY_RANGE needs live entity, not fixed XYZ")
            _id("entity ID", self.entity_id)
            if (type(self.max_entity_age_seq) is not int
                    or not 0 <= self.max_entity_age_seq <= 64
                    or not self.condition.require_line_of_sight):
                raise TargetContractRefusal("attack envelope needs range and live LOS")
        else:
            raise TargetContractRefusal("unknown target kind")

    @property
    def contract_ref(self) -> str:
        """Different precision/geometry/source/scope => a different contract."""
        c = self.condition
        values = (
            self.scope.self_id, self.scope.world_session_id,
            self.goal_id, self.target_ref, self.kind.value,
            self.reference_frame.value, self.provenance.source,
            self.provenance.reference, self.bound_seq,
            None if self.anchor is None else (
                float(self.anchor.x).hex(), float(self.anchor.y).hex(), float(self.anchor.z).hex(),
            ),
            None if self.bound_origin is None else (
                float(self.bound_origin.x).hex(), float(self.bound_origin.y).hex(),
                float(self.bound_origin.z).hex(),
            ),
            self.entity_id, self.max_entity_age_seq,
            float(c.min_horizontal_m).hex(), float(c.max_horizontal_m).hex(),
            float(c.max_vertical_error_m).hex(), c.still_ticks,
            None if c.max_still_drift_m is None else float(c.max_still_drift_m).hex(),
            None if c.max_speed_mps is None else float(c.max_speed_mps).hex(),
            None if c.max_facing_error_rad is None else float(c.max_facing_error_rad).hex(),
            c.require_line_of_sight,
        )
        payload = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode()
        return "target-contract:v1@" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class TargetBodyObservation:
    scope: ScopeRef
    seq: int
    provenance: Provenance
    position: MineflayerPosition
    speed_mps: float | None = None
    still_ticks: int | None = None
    max_still_drift_m: float | None = None
    facing_error_rad: float | None = None
    line_of_sight: bool | None = None
    entity_id: str | None = None
    entity_position: MineflayerPosition | None = None
    entity_observed_seq: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not isinstance(
            self.provenance, Provenance
        ):
            raise TargetContractRefusal("native source and scope required")
        if type(self.seq) is not int or self.seq < 0:
            raise TargetContractRefusal("invalid native sequence")
        _point("body", self.position)
        if self.speed_mps is not None:
            _finite("observed body speed", self.speed_mps, maximum=40)
        if self.still_ticks is not None and (
            type(self.still_ticks) is not int or not 0 <= self.still_ticks <= 2000
        ):
            raise TargetContractRefusal("invalid observed still ticks")
        if self.max_still_drift_m is not None:
            _finite("observed drift", self.max_still_drift_m, maximum=64)
        if self.facing_error_rad is not None:
            _finite("observed facing angle", self.facing_error_rad, maximum=math.pi)
        if self.line_of_sight is not None and type(self.line_of_sight) is not bool:
            raise TargetContractRefusal("unknown LOS must be null")
        if any(x is not None for x in (
            self.entity_id, self.entity_position, self.entity_observed_seq,
        )):
            if (self.entity_id is None or self.entity_position is None
                    or self.entity_observed_seq is None):
                raise TargetContractRefusal("partial entity observation forbidden")
            _id("entity observation ID", self.entity_id)
            _point("entity observation", self.entity_position)
            if type(self.entity_observed_seq) is not int or self.entity_observed_seq < 0:
                raise TargetContractRefusal("invalid entity observed sequence")


@dataclass(frozen=True, slots=True)
class TargetAssessment:
    status: TargetConditionStatus
    contract_ref: str
    gap_to_envelope_m: float | None
    reason: str
    condition_observed: bool = False
    goal_succeeded: bool = False
    physical_authorized: bool = False


def evaluate_target(
    contract: TargetContract, observed: TargetBodyObservation,
) -> TargetAssessment:
    """Read-only geometrical/consequence predicate; never World qualification."""
    if not isinstance(contract, TargetContract) or not isinstance(
        observed, TargetBodyObservation
    ):
        raise TargetContractRefusal("typed contract and native observation required")

    def answer(status: TargetConditionStatus, reason: str,
               gap: float | None = None) -> TargetAssessment:
        return TargetAssessment(
            status, contract.contract_ref, gap, reason,
            condition_observed=(status is TargetConditionStatus.CONDITION_OBSERVED),
        )

    if (contract.scope != observed.scope or observed.seq < contract.bound_seq
            or observed.provenance.source not in {"mineflayer", "paper"}):
        return answer(TargetConditionStatus.UNKNOWN, "foreign/stale WorldBody source")
    if contract.kind is TargetKind.ENTITY_RANGE:
        if (observed.entity_id != contract.entity_id
                or observed.entity_position is None
                or observed.entity_observed_seq is None
                or observed.entity_observed_seq > observed.seq
                or observed.entity_observed_seq < contract.bound_seq
                or observed.seq - observed.entity_observed_seq
                > contract.max_entity_age_seq):
            return answer(TargetConditionStatus.UNKNOWN, "entity target is stale/foreign")
        anchor = observed.entity_position
    else:
        anchor = contract.anchor
    assert anchor is not None
    distance = math.hypot(
        anchor.x - observed.position.x, anchor.z - observed.position.z,
    )
    if abs(anchor.y - observed.position.y) > contract.condition.max_vertical_error_m:
        return answer(TargetConditionStatus.VERTICAL_MISMATCH, "vertical approach needed")
    if distance < contract.condition.min_horizontal_m:
        return answer(
            TargetConditionStatus.TOO_CLOSE,
            "inside forbidden minimum range; forward MOVE is unsafe",
            contract.condition.min_horizontal_m - distance,
        )
    if distance > contract.condition.max_horizontal_m:
        return answer(
            TargetConditionStatus.OUTSIDE,
            "target envelope not reached",
            distance - contract.condition.max_horizontal_m,
        )
    condition = contract.condition
    if condition.max_facing_error_rad is not None:
        if observed.facing_error_rad is None:
            return answer(TargetConditionStatus.UNKNOWN, "missing facing evidence")
        if observed.facing_error_rad > condition.max_facing_error_rad:
            return answer(TargetConditionStatus.ALIGN_REQUIRED, "facing outside envelope")
    if condition.require_line_of_sight:
        if observed.line_of_sight is None:
            return answer(TargetConditionStatus.UNKNOWN, "missing line-of-sight evidence")
        if observed.line_of_sight is False:
            return answer(TargetConditionStatus.BLOCKED, "line of sight blocked")
    if condition.max_speed_mps is not None:
        if observed.speed_mps is None:
            return answer(TargetConditionStatus.UNKNOWN, "missing body speed evidence")
        if observed.speed_mps > condition.max_speed_mps:
            return answer(TargetConditionStatus.SETTLING, "body still moving")
    if condition.still_ticks:
        if observed.still_ticks is None or observed.max_still_drift_m is None:
            return answer(TargetConditionStatus.UNKNOWN, "no independent stillness window")
        if (
            observed.still_ticks < condition.still_ticks
            or observed.max_still_drift_m > condition.max_still_drift_m
        ):
            return answer(TargetConditionStatus.SETTLING, "stillness not established")
    return answer(
        TargetConditionStatus.CONDITION_OBSERVED,
        "goal geometry observed, but independent Goal/Action success not certified",
        0.0,
    )
