from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.provenance import Provenance


class HabitError(ValueError):
    """Base error for bounded retained cue-conditioned habit selection."""


class InvalidHabitData(HabitError):
    """Raised when a repertoire, rule, cue, or selection is malformed."""


class HabitSelectionStatus(str, Enum):
    SELECTED = "selected"
    TIED = "tied"
    NO_MATCH = "no_match"


CueValue = bool | int | str


@dataclass(frozen=True, slots=True)
class CueFeature:
    key: str
    value: CueValue

    def __post_init__(self) -> None:
        _require_token("cue feature key", self.key)
        _require_cue_value(self.value)


@dataclass(frozen=True, slots=True)
class HabitCue:
    cue_id: str
    features: tuple[CueFeature, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("cue_id", self.cue_id)
        _validate_features("cue features", self.features, allow_empty=False)
        _require_provenance("cue provenance", self.provenance)

    def feature(self, key: str) -> CueFeature | None:
        _require_token("cue feature key", key)
        return next((item for item in self.features if item.key == key), None)


@dataclass(frozen=True, slots=True)
class HabitRule:
    habit_id: str
    cue_requirements: tuple[CueFeature, ...]
    candidate_ref: str
    priority: int
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("habit_id", self.habit_id)
        _validate_features(
            "habit cue requirements",
            self.cue_requirements,
            allow_empty=False,
        )
        _require_identifier("candidate_ref", self.candidate_ref)
        _require_nonnegative_int("habit priority", self.priority)
        _require_provenance("habit rule provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class HabitRepertoire:
    repertoire_id: str
    revision: int
    rules: tuple[HabitRule, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("repertoire_id", self.repertoire_id)
        _require_nonnegative_int("repertoire revision", self.revision)
        if not isinstance(self.rules, tuple) or not all(
            isinstance(item, HabitRule) for item in self.rules
        ):
            raise InvalidHabitData("rules must be a tuple of HabitRule values")
        ids = tuple(item.habit_id for item in self.rules)
        if len(set(ids)) != len(ids):
            raise InvalidHabitData("habit_id values must be unique")
        _require_provenance("repertoire provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class HabitSelection:
    repertoire: HabitRepertoire
    cue: HabitCue
    status: HabitSelectionStatus
    matching_rules: tuple[HabitRule, ...]
    selected_rule: HabitRule | None

    def __post_init__(self) -> None:
        if not isinstance(self.repertoire, HabitRepertoire):
            raise InvalidHabitData("selection repertoire must be HabitRepertoire")
        if not isinstance(self.cue, HabitCue):
            raise InvalidHabitData("selection cue must be HabitCue")
        if not isinstance(self.status, HabitSelectionStatus):
            raise InvalidHabitData(
                "selection status must be HabitSelectionStatus"
            )
        if not isinstance(self.matching_rules, tuple) or not all(
            isinstance(item, HabitRule) for item in self.matching_rules
        ):
            raise InvalidHabitData(
                "matching_rules must be a tuple of HabitRule values"
            )

        repertoire_ids = {item.habit_id for item in self.repertoire.rules}
        if any(item.habit_id not in repertoire_ids for item in self.matching_rules):
            raise InvalidHabitData(
                "matching rules must come from the repertoire"
            )

        if self.status is HabitSelectionStatus.SELECTED:
            if self.selected_rule is None:
                raise InvalidHabitData("SELECTED requires selected_rule")
            if self.selected_rule not in self.matching_rules:
                raise InvalidHabitData(
                    "selected rule must be one of matching_rules"
                )
            top = max(item.priority for item in self.matching_rules)
            top_rules = tuple(
                item for item in self.matching_rules if item.priority == top
            )
            if top_rules != (self.selected_rule,):
                raise InvalidHabitData(
                    "SELECTED requires one unique highest-priority rule"
                )
        elif self.status is HabitSelectionStatus.TIED:
            if self.selected_rule is not None:
                raise InvalidHabitData("TIED cannot contain selected_rule")
            if len(self.matching_rules) < 2:
                raise InvalidHabitData(
                    "TIED requires at least two matching rules"
                )
            top = max(item.priority for item in self.matching_rules)
            if sum(item.priority == top for item in self.matching_rules) < 2:
                raise InvalidHabitData(
                    "TIED requires multiple highest-priority rules"
                )
        else:
            if self.selected_rule is not None or self.matching_rules:
                raise InvalidHabitData(
                    "NO_MATCH cannot contain matching or selected rules"
                )

    @property
    def selected_candidate_ref(self) -> str | None:
        return (
            None
            if self.selected_rule is None
            else self.selected_rule.candidate_ref
        )


def select_habit(
    repertoire: HabitRepertoire,
    cue: HabitCue,
) -> HabitSelection:
    """Read retained cue-conditioned rules without mutating or executing them."""

    if not isinstance(repertoire, HabitRepertoire):
        raise InvalidHabitData("repertoire must be HabitRepertoire")
    if not isinstance(cue, HabitCue):
        raise InvalidHabitData("cue must be HabitCue")

    cue_by_key = {item.key: item for item in cue.features}
    matches: list[HabitRule] = []
    for habit_rule in repertoire.rules:
        if all(
            (
                observed := cue_by_key.get(requirement.key)
            ) is not None
            and observed.value == requirement.value
            for requirement in habit_rule.cue_requirements
        ):
            matches.append(habit_rule)

    if not matches:
        return HabitSelection(
            repertoire=repertoire,
            cue=cue,
            status=HabitSelectionStatus.NO_MATCH,
            matching_rules=(),
            selected_rule=None,
        )

    matching_rules = tuple(matches)
    top_priority = max(item.priority for item in matching_rules)
    top_rules = tuple(
        item for item in matching_rules if item.priority == top_priority
    )
    if len(top_rules) == 1:
        return HabitSelection(
            repertoire=repertoire,
            cue=cue,
            status=HabitSelectionStatus.SELECTED,
            matching_rules=matching_rules,
            selected_rule=top_rules[0],
        )

    return HabitSelection(
        repertoire=repertoire,
        cue=cue,
        status=HabitSelectionStatus.TIED,
        matching_rules=matching_rules,
        selected_rule=None,
    )


def _validate_features(
    name: str,
    values: object,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(item, CueFeature) for item in values
    ):
        raise InvalidHabitData(
            f"{name} must be a tuple of CueFeature values"
        )
    if not allow_empty and not values:
        raise InvalidHabitData(f"{name} must not be empty")
    keys = tuple(item.key for item in values)
    if len(set(keys)) != len(keys):
        raise InvalidHabitData(f"{name} keys must be unique")


def _require_cue_value(value: object) -> None:
    if isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, str):
        if (
            value
            and value == value.strip()
            and not any(character.isspace() for character in value)
        ):
            return
    raise InvalidHabitData(
        "cue feature value must be bool, int, or one structured string token"
    )


def _require_nonnegative_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidHabitData(
            f"{name} must be a non-negative integer"
        )


def _require_identifier(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidHabitData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_token(name: str, value: object) -> None:
    _require_identifier(name, value)
    assert isinstance(value, str)
    if ":" in value:
        raise InvalidHabitData(f"{name} must not contain ':'")


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidHabitData(f"{name} must be Provenance")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidHabitData(f"{name} must be a non-empty string")
