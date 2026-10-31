from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.belief import BeliefAssessment
from relay_self.concept import ConceptRepresentation, ConceptStatus
from relay_self.provenance import Provenance


class PredictionError(ValueError):
    """Base error for bounded deterministic transition prediction."""


class InvalidPredictionData(PredictionError):
    """Raised when prediction state or transition data is malformed."""


class PredictionSourceUnavailable(PredictionError):
    """Raised when a source-dependent prediction bridge has no valid source."""


class PredictionStatus(str, Enum):
    PREDICTED = "predicted"
    NO_TRANSITION = "no_transition"
    UNDETERMINED = "undetermined"


VariableValue = bool | int | str


@dataclass(frozen=True, slots=True)
class StateVariable:
    """One immutable structured state variable."""

    key: str
    value: VariableValue

    def __post_init__(self) -> None:
        _require_token("state variable key", self.key)
        _require_variable_value(self.value)


@dataclass(frozen=True, slots=True)
class PredictionState:
    """Immutable structured state used only as an explicit PRD input/output value."""

    state_id: str
    variables: tuple[StateVariable, ...]
    provenance: Provenance
    step_index: int = 0
    source_refs: tuple[str, ...] = ()
    source_provenance: tuple[Provenance, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier("state_id", self.state_id)
        _validate_variables("state variables", self.variables, allow_empty=False)
        if not isinstance(self.provenance, Provenance):
            raise InvalidPredictionData("state provenance must be Provenance")
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or self.step_index < 0
        ):
            raise InvalidPredictionData(
                "step_index must be a non-negative integer"
            )
        _validate_text_tuple("source_refs", self.source_refs)
        if not isinstance(self.source_provenance, tuple) or not all(
            isinstance(value, Provenance)
            for value in self.source_provenance
        ):
            raise InvalidPredictionData(
                "source_provenance must be a tuple of Provenance values"
            )

    def variable(self, key: str) -> StateVariable | None:
        _require_token("state variable key", key)
        return next(
            (variable for variable in self.variables if variable.key == key),
            None,
        )


@dataclass(frozen=True, slots=True)
class TransitionRule:
    """One explicit declarative one-step deterministic transition rule."""

    rule_id: str
    preconditions: tuple[StateVariable, ...]
    assignments: tuple[StateVariable, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("rule_id", self.rule_id)
        _validate_variables(
            "transition preconditions",
            self.preconditions,
            allow_empty=False,
        )
        _validate_variables(
            "transition assignments",
            self.assignments,
            allow_empty=False,
        )
        if not isinstance(self.provenance, Provenance):
            raise InvalidPredictionData("transition provenance must be Provenance")


@dataclass(frozen=True, slots=True)
class PredictionResult:
    """Immutable one-step prediction result retaining exact source and rule objects."""

    source_state: PredictionState
    rule: TransitionRule
    status: PredictionStatus
    predicted_state: PredictionState | None
    matched_preconditions: tuple[StateVariable, ...]
    missing_precondition_keys: tuple[str, ...]
    mismatched_precondition_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_state, PredictionState):
            raise InvalidPredictionData(
                "prediction source_state must be PredictionState"
            )
        if not isinstance(self.rule, TransitionRule):
            raise InvalidPredictionData("prediction rule must be TransitionRule")
        if not isinstance(self.status, PredictionStatus):
            raise InvalidPredictionData("prediction status must be PredictionStatus")
        if self.predicted_state is not None and not isinstance(
            self.predicted_state,
            PredictionState,
        ):
            raise InvalidPredictionData(
                "predicted_state must be PredictionState or None"
            )
        _validate_variables(
            "matched_preconditions",
            self.matched_preconditions,
            allow_empty=True,
        )
        _validate_text_tuple(
            "missing_precondition_keys",
            self.missing_precondition_keys,
        )
        _validate_text_tuple(
            "mismatched_precondition_keys",
            self.mismatched_precondition_keys,
        )

        if self.status is PredictionStatus.PREDICTED:
            if self.predicted_state is None:
                raise InvalidPredictionData(
                    "PREDICTED result requires predicted_state"
                )
            if self.missing_precondition_keys or self.mismatched_precondition_keys:
                raise InvalidPredictionData(
                    "PREDICTED result cannot contain unresolved preconditions"
                )
        elif self.predicted_state is not None:
            raise InvalidPredictionData(
                "non-PREDICTED result cannot contain predicted_state"
            )

        if self.status is PredictionStatus.NO_TRANSITION:
            if not self.mismatched_precondition_keys:
                raise InvalidPredictionData(
                    "NO_TRANSITION requires an explicit mismatched precondition"
                )
        if self.status is PredictionStatus.UNDETERMINED:
            if self.mismatched_precondition_keys:
                raise InvalidPredictionData(
                    "UNDETERMINED cannot contain explicit mismatches"
                )
            if not self.missing_precondition_keys:
                raise InvalidPredictionData(
                    "UNDETERMINED requires at least one missing precondition"
                )


def predict_transition(
    state: PredictionState,
    rule: TransitionRule,
) -> PredictionResult:
    """Apply one explicit deterministic transition without selecting an action.

    Present-but-different precondition values produce NO_TRANSITION. If no
    explicit mismatch exists but required variables are absent, the result is
    UNDETERMINED. Only a full exact precondition match produces a predicted
    next state. Assignments overwrite exactly named variables; unmentioned
    variables remain unchanged.
    """

    if not isinstance(state, PredictionState):
        raise InvalidPredictionData("state must be PredictionState")
    if not isinstance(rule, TransitionRule):
        raise InvalidPredictionData("rule must be TransitionRule")

    by_key = {variable.key: variable for variable in state.variables}
    matched: list[StateVariable] = []
    missing: list[str] = []
    mismatched: list[str] = []

    for requirement in rule.preconditions:
        observed = by_key.get(requirement.key)
        if observed is None:
            missing.append(requirement.key)
            continue
        if observed.value != requirement.value:
            mismatched.append(requirement.key)
            continue
        matched.append(observed)

    if mismatched:
        return PredictionResult(
            source_state=state,
            rule=rule,
            status=PredictionStatus.NO_TRANSITION,
            predicted_state=None,
            matched_preconditions=tuple(matched),
            missing_precondition_keys=tuple(missing),
            mismatched_precondition_keys=tuple(mismatched),
        )

    if missing:
        return PredictionResult(
            source_state=state,
            rule=rule,
            status=PredictionStatus.UNDETERMINED,
            predicted_state=None,
            matched_preconditions=tuple(matched),
            missing_precondition_keys=tuple(missing),
            mismatched_precondition_keys=(),
        )

    assignments = {assignment.key: assignment for assignment in rule.assignments}
    next_variables: list[StateVariable] = []
    source_keys: set[str] = set()

    for variable in state.variables:
        source_keys.add(variable.key)
        next_variables.append(assignments.get(variable.key, variable))

    for assignment in rule.assignments:
        if assignment.key not in source_keys:
            next_variables.append(assignment)

    predicted = PredictionState(
        state_id=f"{state.state_id}@{rule.rule_id}@{state.step_index + 1}",
        variables=tuple(next_variables),
        provenance=Provenance(
            source="relay_self.prediction.predict_transition",
            reference=(
                f"{state.state_id}|{rule.rule_id}|step:{state.step_index + 1}"
            ),
        ),
        step_index=state.step_index + 1,
        source_refs=(
            *state.source_refs,
            f"state:{state.state_id}",
            f"rule:{rule.rule_id}",
        ),
        source_provenance=(
            *state.source_provenance,
            state.provenance,
            rule.provenance,
        ),
    )

    return PredictionResult(
        source_state=state,
        rule=rule,
        status=PredictionStatus.PREDICTED,
        predicted_state=predicted,
        matched_preconditions=tuple(matched),
        missing_precondition_keys=(),
        mismatched_precondition_keys=(),
    )


def prediction_state_from_concept(
    value: object,
    *,
    state_id: str,
    extra_variables: tuple[StateVariable, ...],
    provenance: Provenance,
) -> PredictionState:
    """Explicitly project one MATCHED CNC result into structured PRD state."""

    if not isinstance(value, ConceptRepresentation):
        raise PredictionSourceUnavailable(
            "CNC-dependent PRD work requires an explicit ConceptRepresentation"
        )
    if value.status is not ConceptStatus.MATCHED:
        raise PredictionSourceUnavailable(
            "CNC-dependent PRD projection requires a MATCHED ConceptRepresentation"
        )
    if not isinstance(provenance, Provenance):
        raise InvalidPredictionData("projection provenance must be Provenance")
    _validate_variables("extra_variables", extra_variables, allow_empty=True)

    return PredictionState(
        state_id=state_id,
        variables=(
            StateVariable("source_kind", "concept_representation"),
            StateVariable("concept", value.concept.canonical),
            StateVariable("concept_status", value.status.value),
            *extra_variables,
        ),
        provenance=provenance,
        source_refs=(
            f"concept:{value.concept.canonical}",
            f"concept-criterion:{value.criterion.criterion_id}",
            f"concept-candidate:{value.candidate_id}",
        ),
        source_provenance=(
            value.source.provenance,
            *value.source.source_provenance,
        ),
    )


def prediction_state_from_belief(
    value: object,
    *,
    state_id: str,
    extra_variables: tuple[StateVariable, ...],
    provenance: Provenance,
) -> PredictionState:
    """Explicitly project an existing BLF result without re-assessing evidence."""

    if not isinstance(value, BeliefAssessment):
        raise PredictionSourceUnavailable(
            "BLF-dependent PRD work requires an explicit BeliefAssessment"
        )
    if not isinstance(provenance, Provenance):
        raise InvalidPredictionData("projection provenance must be Provenance")
    _validate_variables("extra_variables", extra_variables, allow_empty=True)

    return PredictionState(
        state_id=state_id,
        variables=(
            StateVariable("source_kind", "belief_assessment"),
            StateVariable("belief_status", value.status.value),
            StateVariable("proposition", value.proposition.canonical),
            *extra_variables,
        ),
        provenance=provenance,
        source_refs=(
            f"belief:{value.criterion_id}",
            f"proposition:{value.proposition.canonical}",
            *(f"evidence:{item.evidence_id}" for item in value.evidence),
        ),
        source_provenance=tuple(
            item.provenance
            for item in value.evidence
        ),
    )


def _validate_variables(
    name: str,
    values: object,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(value, StateVariable)
        for value in values
    ):
        raise InvalidPredictionData(
            f"{name} must be a tuple of StateVariable values"
        )
    if not allow_empty and not values:
        raise InvalidPredictionData(f"{name} must not be empty")

    keys = tuple(value.key for value in values)
    if len(set(keys)) != len(keys):
        raise InvalidPredictionData(f"{name} keys must be unique")


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidPredictionData(f"{name} must be a tuple")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidPredictionData(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_variable_value(value: object) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, str):
        if not value or value != value.strip() or any(
            character.isspace()
            for character in value
        ):
            raise InvalidPredictionData(
                "string variable values must be one non-empty structured token"
            )
        return
    raise InvalidPredictionData(
        "state variable value must be bool, int, or one structured string token"
    )


def _require_identifier(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidPredictionData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_token(name: str, value: object) -> None:
    _require_identifier(name, value)
    assert isinstance(value, str)
    if ":" in value:
        raise InvalidPredictionData(f"{name} must not contain ':'")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidPredictionData(f"{name} must be a non-empty string")
