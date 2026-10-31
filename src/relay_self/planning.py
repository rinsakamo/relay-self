from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.prediction import PredictionResult, PredictionStatus
from relay_self.provenance import Provenance


class PlanningError(ValueError):
    """Base error for bounded deterministic candidate-plan selection."""


class InvalidPlanningData(PlanningError):
    """Raised when plan candidates, features, criteria, or selections are malformed."""


class PlanSourceUnavailable(PlanningError):
    """Raised when an explicitly prediction-dependent plan source is unavailable."""


class PlanningDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class PlanSelectionStatus(str, Enum):
    SELECTED = "selected"
    TIED = "tied"
    UNDETERMINED = "undetermined"


FeatureValue = bool | int | str


@dataclass(frozen=True, slots=True)
class PlanFeature:
    """One immutable structured candidate-outcome feature."""

    key: str
    value: FeatureValue

    def __post_init__(self) -> None:
        _require_token("plan feature key", self.key)
        _require_feature_value(self.value)


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    """One finite caller-supplied plan candidate with structured outcome features."""

    candidate_id: str
    outcome_features: tuple[PlanFeature, ...]
    provenance: Provenance
    prediction_ref: str | None = None
    source_refs: tuple[str, ...] = ()
    source_provenance: tuple[Provenance, ...] = ()
    action_ref: str | None = None

    def __post_init__(self) -> None:
        _require_identifier("candidate_id", self.candidate_id)
        _validate_features(
            "outcome_features",
            self.outcome_features,
            allow_empty=True,
        )
        if not isinstance(self.provenance, Provenance):
            raise InvalidPlanningData("candidate provenance must be Provenance")
        if self.prediction_ref is not None:
            _require_text("prediction_ref", self.prediction_ref)
        _validate_text_tuple("source_refs", self.source_refs)
        if not isinstance(self.source_provenance, tuple) or not all(
            isinstance(value, Provenance)
            for value in self.source_provenance
        ):
            raise InvalidPlanningData(
                "source_provenance must be a tuple of Provenance values"
            )
        if self.action_ref is not None:
            _require_text("action_ref", self.action_ref)

    def feature(self, key: str) -> PlanFeature | None:
        _require_token("plan feature key", key)
        return next(
            (feature for feature in self.outcome_features if feature.key == key),
            None,
        )


@dataclass(frozen=True, slots=True)
class PlanningCriterion:
    """One bounded explicit integer comparison criterion."""

    criterion_id: str
    feature_key: str
    direction: PlanningDirection

    def __post_init__(self) -> None:
        _require_identifier("criterion_id", self.criterion_id)
        _require_token("feature_key", self.feature_key)
        if not isinstance(self.direction, PlanningDirection):
            raise InvalidPlanningData(
                "planning direction must be PlanningDirection"
            )


@dataclass(frozen=True, slots=True)
class PlanSelection:
    """Immutable result of comparing one finite explicit candidate set."""

    criterion: PlanningCriterion
    candidates: tuple[PlanCandidate, ...]
    status: PlanSelectionStatus
    selected: PlanCandidate | None
    best_candidates: tuple[PlanCandidate, ...]
    unrankable_candidate_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.criterion, PlanningCriterion):
            raise InvalidPlanningData(
                "selection criterion must be PlanningCriterion"
            )
        _validate_candidates(self.candidates)
        if not isinstance(self.status, PlanSelectionStatus):
            raise InvalidPlanningData(
                "selection status must be PlanSelectionStatus"
            )
        if self.selected is not None and not isinstance(
            self.selected,
            PlanCandidate,
        ):
            raise InvalidPlanningData(
                "selected must be PlanCandidate or None"
            )
        if not isinstance(self.best_candidates, tuple) or not all(
            isinstance(value, PlanCandidate)
            for value in self.best_candidates
        ):
            raise InvalidPlanningData(
                "best_candidates must be a tuple of PlanCandidate values"
            )
        _validate_text_tuple(
            "unrankable_candidate_ids",
            self.unrankable_candidate_ids,
        )

        candidate_ids = {candidate.candidate_id for candidate in self.candidates}
        if any(
            candidate.candidate_id not in candidate_ids
            for candidate in self.best_candidates
        ):
            raise InvalidPlanningData(
                "best_candidates must come from candidates"
            )
        if any(
            candidate_id not in candidate_ids
            for candidate_id in self.unrankable_candidate_ids
        ):
            raise InvalidPlanningData(
                "unrankable candidate identity must come from candidates"
            )

        if self.status is PlanSelectionStatus.SELECTED:
            if self.selected is None or self.best_candidates != (self.selected,):
                raise InvalidPlanningData(
                    "SELECTED requires exactly one selected best candidate"
                )
            if self.unrankable_candidate_ids:
                raise InvalidPlanningData(
                    "SELECTED cannot contain unrankable candidates"
                )
        elif self.status is PlanSelectionStatus.TIED:
            if self.selected is not None or len(self.best_candidates) < 2:
                raise InvalidPlanningData(
                    "TIED requires at least two best candidates and no selection"
                )
            if self.unrankable_candidate_ids:
                raise InvalidPlanningData(
                    "TIED cannot contain unrankable candidates"
                )
        else:
            if self.selected is not None or self.best_candidates:
                raise InvalidPlanningData(
                    "UNDETERMINED cannot contain a selected/best candidate"
                )
            if not self.unrankable_candidate_ids:
                raise InvalidPlanningData(
                    "UNDETERMINED requires at least one unrankable candidate"
                )

    @property
    def compared_candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.candidate_id for candidate in self.candidates)


def select_plan(
    candidates: tuple[PlanCandidate, ...],
    criterion: PlanningCriterion,
) -> PlanSelection:
    """Select a unique best candidate under one explicit integer criterion.

    All candidates must expose the criterion feature before any selection can
    be made. Missing comparison input yields UNDETERMINED rather than assuming
    zero, false, best, or worst. Equal best scores produce TIED; caller order
    never breaks a tie.
    """

    _validate_candidates(candidates)
    if not isinstance(criterion, PlanningCriterion):
        raise InvalidPlanningData(
            "criterion must be PlanningCriterion"
        )

    scored: list[tuple[PlanCandidate, int]] = []
    unrankable: list[str] = []

    for candidate in candidates:
        feature = candidate.feature(criterion.feature_key)
        if feature is None:
            unrankable.append(candidate.candidate_id)
            continue
        if isinstance(feature.value, bool) or not isinstance(feature.value, int):
            raise InvalidPlanningData(
                "planning comparison feature must contain an integer value"
            )
        scored.append((candidate, feature.value))

    if unrankable:
        return PlanSelection(
            criterion=criterion,
            candidates=candidates,
            status=PlanSelectionStatus.UNDETERMINED,
            selected=None,
            best_candidates=(),
            unrankable_candidate_ids=tuple(unrankable),
        )

    scores = tuple(score for _, score in scored)
    if criterion.direction is PlanningDirection.MINIMIZE:
        best_score = min(scores)
    else:
        best_score = max(scores)

    winners = tuple(
        candidate
        for candidate, score in scored
        if score == best_score
    )
    if len(winners) == 1:
        return PlanSelection(
            criterion=criterion,
            candidates=candidates,
            status=PlanSelectionStatus.SELECTED,
            selected=winners[0],
            best_candidates=winners,
            unrankable_candidate_ids=(),
        )

    return PlanSelection(
        criterion=criterion,
        candidates=candidates,
        status=PlanSelectionStatus.TIED,
        selected=None,
        best_candidates=winners,
        unrankable_candidate_ids=(),
    )


def plan_candidate_from_prediction(
    value: object,
    *,
    candidate_id: str,
    feature_keys: tuple[str, ...],
    provenance: Provenance,
    action_ref: str | None = None,
) -> PlanCandidate:
    """Explicitly project selected structured PRD state variables into PLAN input.

    The bridge does not rerun PRD, infer utility, or reinterpret prediction as
    truth. The caller explicitly names which already-predicted variables become
    candidate outcome features.
    """

    if not isinstance(value, PredictionResult):
        raise PlanSourceUnavailable(
            "PRD-dependent PLAN work requires an explicit PredictionResult"
        )
    if value.status is not PredictionStatus.PREDICTED:
        raise PlanSourceUnavailable(
            "PRD-dependent PLAN projection requires a PREDICTED result"
        )
    if value.predicted_state is None:
        raise PlanSourceUnavailable(
            "PREDICTED result must contain predicted_state"
        )
    if not isinstance(feature_keys, tuple) or not feature_keys:
        raise InvalidPlanningData(
            "feature_keys must be a non-empty tuple"
        )
    for key in feature_keys:
        _require_token("feature key", key)
    if len(set(feature_keys)) != len(feature_keys):
        raise InvalidPlanningData(
            "feature_keys must be unique"
        )
    if not isinstance(provenance, Provenance):
        raise InvalidPlanningData(
            "projection provenance must be Provenance"
        )
    if action_ref is not None:
        _require_text("action_ref", action_ref)

    projected: list[PlanFeature] = []
    for key in feature_keys:
        variable = value.predicted_state.variable(key)
        if variable is None:
            raise PlanSourceUnavailable(
                f"predicted state is missing requested plan feature: {key}"
            )
        projected.append(
            PlanFeature(
                key=variable.key,
                value=variable.value,
            )
        )

    return PlanCandidate(
        candidate_id=candidate_id,
        outcome_features=tuple(projected),
        provenance=provenance,
        prediction_ref=(
            f"{value.source_state.state_id}|{value.rule.rule_id}|"
            f"{value.predicted_state.state_id}"
        ),
        source_refs=(
            f"prediction-source-state:{value.source_state.state_id}",
            f"prediction-rule:{value.rule.rule_id}",
            f"predicted-state:{value.predicted_state.state_id}",
        ),
        source_provenance=(
            *value.predicted_state.source_provenance,
            value.predicted_state.provenance,
        ),
        action_ref=action_ref,
    )


def _validate_candidates(values: object) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(value, PlanCandidate)
        for value in values
    ):
        raise InvalidPlanningData(
            "candidates must be a tuple of PlanCandidate values"
        )
    if not values:
        raise InvalidPlanningData(
            "candidate set must not be empty"
        )
    ids = tuple(value.candidate_id for value in values)
    if len(set(ids)) != len(ids):
        raise InvalidPlanningData(
            "candidate_id values must be unique"
        )


def _validate_features(
    name: str,
    values: object,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(value, PlanFeature)
        for value in values
    ):
        raise InvalidPlanningData(
            f"{name} must be a tuple of PlanFeature values"
        )
    if not allow_empty and not values:
        raise InvalidPlanningData(f"{name} must not be empty")
    keys = tuple(value.key for value in values)
    if len(set(keys)) != len(keys):
        raise InvalidPlanningData(
            f"{name} keys must be unique"
        )


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidPlanningData(f"{name} must be a tuple")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidPlanningData(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_feature_value(value: object) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, str):
        if not value or value != value.strip() or any(
            character.isspace()
            for character in value
        ):
            raise InvalidPlanningData(
                "string plan feature values must be one structured token"
            )
        return
    raise InvalidPlanningData(
        "plan feature value must be bool, int, or one structured string token"
    )


def _require_identifier(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidPlanningData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_token(name: str, value: object) -> None:
    _require_identifier(name, value)
    assert isinstance(value, str)
    if ":" in value:
        raise InvalidPlanningData(f"{name} must not contain ':'")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidPlanningData(f"{name} must be a non-empty string")
