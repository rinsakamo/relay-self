from dataclasses import dataclass


class InvalidProvenanceData(ValueError):
    """Raised when shared provenance data is malformed."""


@dataclass(frozen=True, slots=True)
class Provenance:
    """Immutable source/reference evidence pointer shared across runtime owners."""

    source: str
    reference: str

    def __post_init__(self) -> None:
        _require_text("provenance source", self.source)
        _require_text("provenance reference", self.reference)


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidProvenanceData(f"{name} must be a non-empty string")
