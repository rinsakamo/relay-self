from __future__ import annotations

from dataclasses import dataclass

from relay_self.provenance import Provenance


class AttentionError(ValueError):
    """Base error for bounded attention selection."""


class InvalidAttentionData(AttentionError):
    """Raised when attention candidates or criteria are malformed."""


class AttentionSelectionUnavailable(AttentionError):
    """Raised when downstream work requires an ATT result that does not exist."""


@dataclass(frozen=True, slots=True)
class AttentionCandidate:
    """Immutable reference to caller-owned candidate data.

    ATT does not own the referenced payload. The payload_ref is an opaque stable
    reference supplied by the caller/source, while provenance remains explicit.
    """

    candidate_id: str
    payload_ref: str
    provenance: Provenance
    priority: int = 0
    focus_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("candidate_id", self.candidate_id)
        _require_text("payload_ref", self.payload_ref)
        if not isinstance(self.provenance, Provenance):
            raise InvalidAttentionData("candidate provenance must be Provenance")
        _require_int("priority", self.priority)
        _validate_text_tuple("focus_keys", self.focus_keys)


@dataclass(frozen=True, slots=True)
class AttentionCriterion:
    """Explicit structured orientation criterion for one bounded selection."""

    criterion_id: str
    focus_key: str | None = None
    minimum_priority: int | None = None
    top_k: int | None = None

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        if self.focus_key is not None:
            _require_text("focus_key", self.focus_key)
        if self.minimum_priority is not None:
            _require_int("minimum_priority", self.minimum_priority)
        if self.top_k is not None:
            if (
                isinstance(self.top_k, bool)
                or not isinstance(self.top_k, int)
                or self.top_k <= 0
            ):
                raise InvalidAttentionData("top_k must be a positive integer or None")


@dataclass(frozen=True, slots=True)
class AttentionSelection:
    """Transient immutable result; it owns no source payload or durable state."""

    criterion_id: str
    selected: tuple[AttentionCandidate, ...]
    considered_count: int

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        if not isinstance(self.selected, tuple) or not all(
            isinstance(value, AttentionCandidate)
            for value in self.selected
        ):
            raise InvalidAttentionData(
                "selected must be a tuple of AttentionCandidate values"
            )
        if (
            isinstance(self.considered_count, bool)
            or not isinstance(self.considered_count, int)
            or self.considered_count < 0
        ):
            raise InvalidAttentionData(
                "considered_count must be a non-negative integer"
            )
        if len(self.selected) > self.considered_count:
            raise InvalidAttentionData(
                "selected candidates cannot exceed considered candidates"
            )

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.candidate_id for candidate in self.selected)


def select_attention(
    candidates: tuple[AttentionCandidate, ...],
    criterion: AttentionCriterion,
) -> AttentionSelection:
    """Filter and rank already-available candidates without acquiring ownership.

    Selection is deterministic. Higher priority sorts first, while equal
    priorities preserve caller/source order. Focus and minimum-priority filters
    are explicit; no semantic relevance is inferred from free text.
    """

    if not isinstance(candidates, tuple) or not all(
        isinstance(value, AttentionCandidate)
        for value in candidates
    ):
        raise InvalidAttentionData(
            "candidates must be a tuple of AttentionCandidate values"
        )
    if not isinstance(criterion, AttentionCriterion):
        raise InvalidAttentionData("criterion must be AttentionCriterion")

    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(set(candidate_ids)) != len(candidate_ids):
        raise InvalidAttentionData("candidate_id values must be unique")

    selected = [
        candidate
        for candidate in candidates
        if (
            criterion.focus_key is None
            or criterion.focus_key in candidate.focus_keys
        )
        and (
            criterion.minimum_priority is None
            or candidate.priority >= criterion.minimum_priority
        )
    ]
    selected.sort(key=lambda candidate: candidate.priority, reverse=True)

    if criterion.top_k is not None:
        selected = selected[: criterion.top_k]

    return AttentionSelection(
        criterion_id=criterion.criterion_id,
        selected=tuple(selected),
        considered_count=len(candidates),
    )


def require_attention_selection(value: object) -> AttentionSelection:
    """Fail closed when an explicitly ATT-dependent route has no ATT result."""

    if not isinstance(value, AttentionSelection):
        raise AttentionSelectionUnavailable(
            "ATT-dependent downstream work requires an explicit AttentionSelection"
        )
    return value


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidAttentionData(f"{name} must be a tuple")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidAttentionData(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidAttentionData(f"{name} must be an integer")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidAttentionData(f"{name} must be a non-empty string")
