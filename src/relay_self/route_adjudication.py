from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.habit import HabitSelection, HabitSelectionStatus
from relay_self.planning import PlanSelection, PlanSelectionStatus
from relay_self.provenance import Provenance


class RouteAdjudicationError(ValueError):
    """Base error for bounded stateless route adjudication."""


class InvalidRouteData(RouteAdjudicationError):
    """Raised when route inputs, criteria, candidates, or decisions are malformed."""


class RouteSource(str, Enum):
    PLAN = "plan"
    HABIT = "habit"


class RouteConflictPolicy(str, Enum):
    FAIL_CLOSED = "fail_closed"
    PLAN_WINS = "plan_wins"
    HABIT_WINS = "habit_wins"


class RouteDecisionStatus(str, Enum):
    SELECTED = "selected"
    AGREED = "agreed"
    CONFLICT = "conflict"
    NO_CANDIDATE = "no_candidate"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    """One immutable non-authoritative reference projected from a selected route."""

    source: RouteSource
    candidate_ref: str
    source_ref: str
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.source, RouteSource):
            raise InvalidRouteData("route candidate source must be RouteSource")
        _require_identifier("candidate_ref", self.candidate_ref)
        _require_identifier("source_ref", self.source_ref)
        _require_provenance("candidate provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class RouteCriterion:
    """Explicit route orientation; no precedence exists outside this value."""

    criterion_id: str
    conflict_policy: RouteConflictPolicy = RouteConflictPolicy.FAIL_CLOSED
    allow_single_source: bool = True

    def __post_init__(self) -> None:
        _require_identifier("criterion_id", self.criterion_id)
        if not isinstance(self.conflict_policy, RouteConflictPolicy):
            raise InvalidRouteData(
                "conflict_policy must be RouteConflictPolicy"
            )
        if not isinstance(self.allow_single_source, bool):
            raise InvalidRouteData("allow_single_source must be bool")


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Immutable non-authoritative result over already-produced route outputs."""

    status: RouteDecisionStatus
    criterion: RouteCriterion
    selected_candidate_ref: str | None
    selected_source: RouteSource | None
    plan_candidate: RouteCandidate | None
    habit_candidate: RouteCandidate | None
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.status, RouteDecisionStatus):
            raise InvalidRouteData("route status must be RouteDecisionStatus")
        if not isinstance(self.criterion, RouteCriterion):
            raise InvalidRouteData("route criterion must be RouteCriterion")
        _validate_optional_candidate(
            "plan_candidate",
            self.plan_candidate,
            RouteSource.PLAN,
        )
        _validate_optional_candidate(
            "habit_candidate",
            self.habit_candidate,
            RouteSource.HABIT,
        )
        _require_provenance("route decision provenance", self.provenance)

        if self.selected_candidate_ref is not None:
            _require_identifier(
                "selected_candidate_ref",
                self.selected_candidate_ref,
            )
        if self.selected_source is not None and not isinstance(
            self.selected_source,
            RouteSource,
        ):
            raise InvalidRouteData(
                "selected_source must be RouteSource or None"
            )

        if self.status is RouteDecisionStatus.AGREED:
            if self.plan_candidate is None or self.habit_candidate is None:
                raise InvalidRouteData(
                    "AGREED requires PLAN and HABIT candidates"
                )
            if (
                self.plan_candidate.candidate_ref
                != self.habit_candidate.candidate_ref
            ):
                raise InvalidRouteData(
                    "AGREED requires identical candidate references"
                )
            if self.selected_candidate_ref != self.plan_candidate.candidate_ref:
                raise InvalidRouteData(
                    "AGREED selected candidate must match both routes"
                )
            if self.selected_source is not None:
                raise InvalidRouteData(
                    "AGREED cannot assign one source exclusive authority"
                )
            return

        if self.status is RouteDecisionStatus.SELECTED:
            if self.selected_candidate_ref is None or self.selected_source is None:
                raise InvalidRouteData(
                    "SELECTED requires candidate and source"
                )
            chosen = (
                self.plan_candidate
                if self.selected_source is RouteSource.PLAN
                else self.habit_candidate
            )
            if chosen is None:
                raise InvalidRouteData(
                    "SELECTED source must have a usable candidate"
                )
            if chosen.candidate_ref != self.selected_candidate_ref:
                raise InvalidRouteData(
                    "selected candidate_ref does not match selected source"
                )
            if (
                self.plan_candidate is not None
                and self.habit_candidate is not None
                and self.plan_candidate.candidate_ref
                == self.habit_candidate.candidate_ref
            ):
                raise InvalidRouteData(
                    "identical PLAN/HABIT candidates must be AGREED"
                )
            return

        if self.selected_candidate_ref is not None or self.selected_source is not None:
            raise InvalidRouteData(
                f"{self.status.name} cannot contain a selected candidate"
            )

        if self.status is RouteDecisionStatus.CONFLICT:
            if self.plan_candidate is None or self.habit_candidate is None:
                raise InvalidRouteData(
                    "CONFLICT requires PLAN and HABIT candidates"
                )
            if (
                self.plan_candidate.candidate_ref
                == self.habit_candidate.candidate_ref
            ):
                raise InvalidRouteData(
                    "CONFLICT requires different candidate references"
                )
            if (
                self.criterion.conflict_policy
                is not RouteConflictPolicy.FAIL_CLOSED
            ):
                raise InvalidRouteData(
                    "CONFLICT is valid only under FAIL_CLOSED"
                )
            return

        if self.status is RouteDecisionStatus.NO_CANDIDATE:
            if self.plan_candidate is not None or self.habit_candidate is not None:
                raise InvalidRouteData(
                    "NO_CANDIDATE cannot contain usable candidates"
                )
            return

        usable_count = sum(
            candidate is not None
            for candidate in (self.plan_candidate, self.habit_candidate)
        )
        if usable_count != 1 or self.criterion.allow_single_source:
            raise InvalidRouteData(
                "UNDETERMINED requires one candidate with single-source admission disabled"
            )


@dataclass(frozen=True, slots=True)
class ControlCandidate:
    """Pure CTL-facing projection carrying no execution authority."""

    candidate_ref: str
    route_status: RouteDecisionStatus
    selected_source: RouteSource | None
    criterion_id: str
    plan_candidate_ref: str | None
    habit_candidate_ref: str | None
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("control candidate_ref", self.candidate_ref)
        if self.route_status not in {
            RouteDecisionStatus.SELECTED,
            RouteDecisionStatus.AGREED,
        }:
            raise InvalidRouteData(
                "ControlCandidate requires SELECTED or AGREED route status"
            )
        if self.route_status is RouteDecisionStatus.SELECTED:
            if not isinstance(self.selected_source, RouteSource):
                raise InvalidRouteData(
                    "SELECTED control candidate requires selected source"
                )
        elif self.selected_source is not None:
            raise InvalidRouteData(
                "AGREED control candidate cannot prefer one route source"
            )
        _require_identifier("control criterion_id", self.criterion_id)
        if self.plan_candidate_ref is not None:
            _require_identifier(
                "control plan_candidate_ref",
                self.plan_candidate_ref,
            )
        if self.habit_candidate_ref is not None:
            _require_identifier(
                "control habit_candidate_ref",
                self.habit_candidate_ref,
            )
        _require_provenance("control candidate provenance", self.provenance)


def route_candidate_from_plan(
    value: object,
) -> RouteCandidate | None:
    """Project only a uniquely SELECTED PLAN output into a route candidate."""

    if not isinstance(value, PlanSelection):
        raise InvalidRouteData(
            "PLAN route input must be PlanSelection"
        )
    if value.status is not PlanSelectionStatus.SELECTED:
        return None
    if value.selected is None:
        raise InvalidRouteData(
            "SELECTED PlanSelection must contain selected candidate"
        )
    return RouteCandidate(
        source=RouteSource.PLAN,
        candidate_ref=value.selected.candidate_id,
        source_ref=(
            f"plan:{value.criterion.criterion_id}:{value.selected.candidate_id}"
        ),
        provenance=value.selected.provenance,
    )


def route_candidate_from_habit(
    value: object,
) -> RouteCandidate | None:
    """Project only a uniquely SELECTED HABIT output into a route candidate."""

    if not isinstance(value, HabitSelection):
        raise InvalidRouteData(
            "HABIT route input must be HabitSelection"
        )
    if value.status is not HabitSelectionStatus.SELECTED:
        return None
    if value.selected_rule is None:
        raise InvalidRouteData(
            "SELECTED HabitSelection must contain selected rule"
        )
    return RouteCandidate(
        source=RouteSource.HABIT,
        candidate_ref=value.selected_rule.candidate_ref,
        source_ref=(
            f"habit:{value.repertoire.repertoire_id}:"
            f"rev:{value.repertoire.revision}:{value.selected_rule.habit_id}"
        ),
        provenance=value.selected_rule.provenance,
    )


def adjudicate_routes(
    plan_selection: PlanSelection | None,
    habit_selection: HabitSelection | None,
    criterion: RouteCriterion,
    *,
    provenance: Provenance,
) -> RouteDecision:
    """Admit, agree, reject, or leave unresolved already-produced selections.

    None means that route was not supplied for this bounded adjudication. A
    supplied PLAN TIED/UNDETERMINED or HABIT TIED/NO_MATCH value is not a
    negative vote and does not fabricate a candidate.
    """

    if plan_selection is not None and not isinstance(
        plan_selection,
        PlanSelection,
    ):
        raise InvalidRouteData(
            "plan_selection must be PlanSelection or None"
        )
    if habit_selection is not None and not isinstance(
        habit_selection,
        HabitSelection,
    ):
        raise InvalidRouteData(
            "habit_selection must be HabitSelection or None"
        )
    if not isinstance(criterion, RouteCriterion):
        raise InvalidRouteData("criterion must be RouteCriterion")
    _require_provenance("route decision provenance", provenance)

    plan_candidate = (
        None
        if plan_selection is None
        else route_candidate_from_plan(plan_selection)
    )
    habit_candidate = (
        None
        if habit_selection is None
        else route_candidate_from_habit(habit_selection)
    )

    if plan_candidate is None and habit_candidate is None:
        return RouteDecision(
            status=RouteDecisionStatus.NO_CANDIDATE,
            criterion=criterion,
            selected_candidate_ref=None,
            selected_source=None,
            plan_candidate=None,
            habit_candidate=None,
            provenance=provenance,
        )

    if plan_candidate is None or habit_candidate is None:
        available = (
            plan_candidate
            if plan_candidate is not None
            else habit_candidate
        )
        assert available is not None
        if not criterion.allow_single_source:
            return RouteDecision(
                status=RouteDecisionStatus.UNDETERMINED,
                criterion=criterion,
                selected_candidate_ref=None,
                selected_source=None,
                plan_candidate=plan_candidate,
                habit_candidate=habit_candidate,
                provenance=provenance,
            )
        return RouteDecision(
            status=RouteDecisionStatus.SELECTED,
            criterion=criterion,
            selected_candidate_ref=available.candidate_ref,
            selected_source=available.source,
            plan_candidate=plan_candidate,
            habit_candidate=habit_candidate,
            provenance=provenance,
        )

    if plan_candidate.candidate_ref == habit_candidate.candidate_ref:
        return RouteDecision(
            status=RouteDecisionStatus.AGREED,
            criterion=criterion,
            selected_candidate_ref=plan_candidate.candidate_ref,
            selected_source=None,
            plan_candidate=plan_candidate,
            habit_candidate=habit_candidate,
            provenance=provenance,
        )

    if criterion.conflict_policy is RouteConflictPolicy.FAIL_CLOSED:
        return RouteDecision(
            status=RouteDecisionStatus.CONFLICT,
            criterion=criterion,
            selected_candidate_ref=None,
            selected_source=None,
            plan_candidate=plan_candidate,
            habit_candidate=habit_candidate,
            provenance=provenance,
        )

    chosen = (
        plan_candidate
        if criterion.conflict_policy is RouteConflictPolicy.PLAN_WINS
        else habit_candidate
    )
    return RouteDecision(
        status=RouteDecisionStatus.SELECTED,
        criterion=criterion,
        selected_candidate_ref=chosen.candidate_ref,
        selected_source=chosen.source,
        plan_candidate=plan_candidate,
        habit_candidate=habit_candidate,
        provenance=provenance,
    )


def control_candidate_from_route_decision(
    value: object,
) -> ControlCandidate | None:
    """Purely project an admitted route result; never commits or executes it."""

    if not isinstance(value, RouteDecision):
        raise InvalidRouteData("value must be RouteDecision")
    if value.status not in {
        RouteDecisionStatus.SELECTED,
        RouteDecisionStatus.AGREED,
    }:
        return None
    assert value.selected_candidate_ref is not None
    return ControlCandidate(
        candidate_ref=value.selected_candidate_ref,
        route_status=value.status,
        selected_source=value.selected_source,
        criterion_id=value.criterion.criterion_id,
        plan_candidate_ref=(
            None
            if value.plan_candidate is None
            else value.plan_candidate.candidate_ref
        ),
        habit_candidate_ref=(
            None
            if value.habit_candidate is None
            else value.habit_candidate.candidate_ref
        ),
        provenance=value.provenance,
    )


def _validate_optional_candidate(
    name: str,
    value: object,
    expected_source: RouteSource,
) -> None:
    if value is None:
        return
    if not isinstance(value, RouteCandidate):
        raise InvalidRouteData(
            f"{name} must be RouteCandidate or None"
        )
    if value.source is not expected_source:
        raise InvalidRouteData(
            f"{name} must have source {expected_source.value}"
        )


def _require_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRouteData(f"{name} must be a non-empty string")
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidRouteData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidRouteData(f"{name} must be Provenance")
