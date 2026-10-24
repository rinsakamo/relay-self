"""#632 SelfBody timing/kinematics DEV view, read-only and intentionally untrusted.

Derives no physical speed from S49 probe sequence and never authorizes a move.
The future attack deadline, cognitive latency and body movement model are
EXPLICITLY synthetic hypotheses, not measured Minecraft capabilities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import BodyOrigin, SelfBodyView


class TimingReviewRejected(ValueError):
    """Malformed or cross-source SelfBody timing input."""


class DodgeBudgetStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    WITHIN_HYPOTHETICAL_BUDGET = "WITHIN_HYPOTHETICAL_BUDGET"
    LATE_UNDER_HYPOTHESIS = "LATE_UNDER_HYPOTHESIS"


class BodyDisplacementStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    SOURCE_CORRELATED_POSITION_DELTA = "SOURCE_CORRELATED_POSITION_DELTA"


class TimingEvidenceOrigin(str, Enum):
    SYNTHETIC_DEV_HYPOTHESIS = "SYNTHETIC_DEV_HYPOTHESIS"


def _finite(name: str, value: object, *, positive: bool = False) -> None:
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        raise TimingReviewRejected(f"invalid {name}")


def _name(name: str, value: object) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise TimingReviewRejected(f"invalid {name}")


def _check_view(view: SelfBodyView, self_id: str) -> None:
    if not isinstance(view, SelfBodyView):
        raise TimingReviewRejected("typed SelfBodyView required")
    if view.self_id != self_id:
        raise TimingReviewRejected("foreign or unspecified Self identity")
    _name("Self ID", self_id)
    _name("session", view.session_id)
    if view.observation is not None:
        obs = view.observation
        if obs.session_id != view.session_id or (
            obs.source_provenance.source != "mineflayer"
            or obs.source_provenance.reference
            != f"{obs.session_id}:{obs.native_seq}"
        ):
            raise TimingReviewRejected("uncorrelated native Body source")


@dataclass(frozen=True, slots=True)
class BodyTimingHypothesis:
    """All quantities are synthetic *conditional estimates*, in milliseconds.

    The attack impact horizon is measured from the World cue's occurrence;
    detect/decide/issue/actuator/travel must share that same starting point.
    No native clock measurements are conveyed by this type.
    """

    self_id: str
    session_id: str
    body_source_ref: str
    attack_horizon_ms: float | None
    detection_ms: float | None
    cognition_ms: float | None
    authorization_issue_ms: float | None
    actuator_start_ms: float | None
    required_clearance_m: float | None
    assumed_body_speed_mps: float | None
    origin: TimingEvidenceOrigin = (
        TimingEvidenceOrigin.SYNTHETIC_DEV_HYPOTHESIS
    )

    def __post_init__(self) -> None:
        for name in ("self_id", "session_id", "body_source_ref"):
            _name(name, getattr(self, name))
        if self.origin is not TimingEvidenceOrigin.SYNTHETIC_DEV_HYPOTHESIS:
            raise TimingReviewRejected("hypothesis cannot claim native evidence")
        for field in (
            "attack_horizon_ms", "detection_ms", "cognition_ms",
            "authorization_issue_ms", "actuator_start_ms",
            "required_clearance_m", "assumed_body_speed_mps",
        ):
            value = getattr(self, field)
            if value is not None:
                _finite(field, value, positive=field == "assumed_body_speed_mps")


@dataclass(frozen=True, slots=True)
class DodgeBudgetReview:
    self_id: str
    session_id: str
    body_source_ref: str
    status: DodgeBudgetStatus
    travel_ms: float | None
    total_response_ms: float | None
    headroom_ms: float | None
    origin: TimingEvidenceOrigin
    allowed_to_act: bool = False
    physical_success_attested: bool = False

    def __post_init__(self) -> None:
        if self.allowed_to_act is not False or (
            self.physical_success_attested is not False
        ):
            raise TimingReviewRejected("timing prediction cannot grant Action")
        if self.origin is not TimingEvidenceOrigin.SYNTHETIC_DEV_HYPOTHESIS:
            raise TimingReviewRejected("synthetic result cannot be physical")


def predict_hypothetical_dodge(
    body: SelfBodyView,
    hypothesis: BodyTimingHypothesis,
) -> DodgeBudgetReview:
    """Compare synthetic time budgets, NEVER classify World as safe."""
    if not isinstance(hypothesis, BodyTimingHypothesis):
        raise TimingReviewRejected("typed timing hypothesis required")
    _check_view(body, hypothesis.self_id)
    if body.session_id != hypothesis.session_id:
        raise TimingReviewRejected("foreign session timing hypothesis")
    if body.observation is None:
        if hypothesis.body_source_ref != "UNKNOWN":
            raise TimingReviewRejected("invented Body observation source")
    elif body.observation.source_ref != hypothesis.body_source_ref:
        raise TimingReviewRejected("foreign or stale Body source ref")

    quantities = (
        hypothesis.attack_horizon_ms, hypothesis.detection_ms,
        hypothesis.cognition_ms, hypothesis.authorization_issue_ms,
        hypothesis.actuator_start_ms, hypothesis.required_clearance_m,
        hypothesis.assumed_body_speed_mps,
    )
    status = DodgeBudgetStatus.UNKNOWN
    travel_ms = total_ms = headroom_ms = None
    if (
        body.observation is not None
        and _position(body) is not None
        and all(value is not None for value in quantities)
    ):
        assert hypothesis.attack_horizon_ms is not None
        assert hypothesis.detection_ms is not None
        assert hypothesis.cognition_ms is not None
        assert hypothesis.authorization_issue_ms is not None
        assert hypothesis.actuator_start_ms is not None
        assert hypothesis.required_clearance_m is not None
        assert hypothesis.assumed_body_speed_mps is not None
        travel_ms = 1000 * (
            hypothesis.required_clearance_m
            / hypothesis.assumed_body_speed_mps
        )
        total_ms = (
            hypothesis.detection_ms + hypothesis.cognition_ms
            + hypothesis.authorization_issue_ms
            + hypothesis.actuator_start_ms + travel_ms
        )
        headroom_ms = hypothesis.attack_horizon_ms - total_ms
        status = (
            DodgeBudgetStatus.WITHIN_HYPOTHETICAL_BUDGET
            if headroom_ms > 0
            else DodgeBudgetStatus.LATE_UNDER_HYPOTHESIS
        )
    return DodgeBudgetReview(
        self_id=hypothesis.self_id,
        session_id=hypothesis.session_id,
        body_source_ref=hypothesis.body_source_ref,
        status=status,
        travel_ms=travel_ms,
        total_response_ms=total_ms,
        headroom_ms=headroom_ms,
        origin=hypothesis.origin,
    )


@dataclass(frozen=True, slots=True)
class BodyDisplacementReview:
    """Producer-local position delta; NOT a velocity or verified motor model."""

    self_id: str
    session_id: str
    status: BodyDisplacementStatus
    before_source_ref: str | None
    after_source_ref: str | None
    action_id: str | None
    horizontal_distance_m: float | None
    elapsed_s: None = None
    speed_mps: None = None
    authorized_to_move: bool = False

    def __post_init__(self) -> None:
        if (
            self.elapsed_s is not None or self.speed_mps is not None
            or self.authorized_to_move is not False
        ):
            raise TimingReviewRejected(
                "source seq and Action readback do not measure physical speed"
            )


def _position(body: SelfBodyView) -> tuple[float, float, float] | None:
    items = tuple(body.observed(key) for key in (
        "position_x", "position_y", "position_z",
    ))
    if any(item.origin is not BodyOrigin.OBSERVATION for item in items):
        return None
    values = tuple(item.value for item in items)
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise TimingReviewRejected("invalid native Body position")
    return values  # type: ignore[return-value]


def review_body_position_delta(
    before: SelfBodyView, after: SelfBodyView, *, self_id: str,
) -> BodyDisplacementReview:
    """Read an ordered same-session action-following pair, never speed."""
    _check_view(before, self_id)
    _check_view(after, self_id)
    if before.session_id != after.session_id:
        raise TimingReviewRejected("cross-session Body pair")
    a = before.observation
    b = after.observation
    if a is not None and b is not None and (
        a.native_seq >= b.native_seq
        or a.request_id == b.request_id
    ):
        raise TimingReviewRejected("stale, duplicate or unordered Body pair")
    status = BodyDisplacementStatus.UNKNOWN
    horizontal_distance = None
    action_id = None
    if (
        a is not None and b is not None
        and before.outcome is None
        and after.outcome is not None
        and after.outcome.disposition is ActionOutcomeDisposition.OUTCOME
        and after.outcome.reason_code == "observed_execution"
        and b.action_id == after.outcome.action_id
        and b.consequence_provenance == after.outcome.world_provenance
    ):
        start = _position(before)
        end = _position(after)
        if start is not None and end is not None:
            horizontal_distance = math.hypot(
                end[0] - start[0], end[2] - start[2]
            )
            status = BodyDisplacementStatus.SOURCE_CORRELATED_POSITION_DELTA
            action_id = b.action_id
    return BodyDisplacementReview(
        self_id=self_id,
        session_id=before.session_id,
        status=status,
        before_source_ref=a.source_ref if a is not None else None,
        after_source_ref=b.source_ref if b is not None else None,
        action_id=action_id,
        horizontal_distance_m=horizontal_distance,
    )
