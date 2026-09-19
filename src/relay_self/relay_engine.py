from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from relay_self.provenance import Provenance


class RelayEngineError(ValueError):
    """Base error for the minimum transient RelayEngine contract."""


class InvalidRelayEngineData(RelayEngineError):
    """Raised when bounded cognition data violates the current contract."""


class CognitionMode(str, Enum):
    BOUNDED = "bounded"
    THINK = "think"


class DecisionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class BoundedChoice:
    choice_id: str
    description: str

    def __post_init__(self) -> None:
        _require_text("choice_id", self.choice_id)
        _require_text("choice description", self.description)


@dataclass(frozen=True, slots=True)
class CognitionDatum:
    """One transient model-facing datum with source provenance preserved."""

    key: str
    value_json: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_text("cognition datum key", self.key)
        _require_text("cognition datum value_json", self.value_json)
        if not isinstance(self.provenance, Provenance):
            raise InvalidRelayEngineData(
                "cognition datum provenance must be Provenance"
            )
        try:
            json.loads(self.value_json)
        except json.JSONDecodeError as exc:
            raise InvalidRelayEngineData(
                "cognition datum value_json must be valid JSON"
            ) from exc

    @classmethod
    def from_value(
        cls,
        key: str,
        value: object,
        provenance: Provenance,
    ) -> "CognitionDatum":
        try:
            rendered = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise InvalidRelayEngineData(
                "cognition datum value must be JSON serializable"
            ) from exc
        return cls(
            key=key,
            value_json=rendered,
            provenance=provenance,
        )


@dataclass(frozen=True, slots=True)
class BoundedChoiceRequest:
    """Transient finite-choice cognition request for one decision epoch."""

    request_id: str
    instruction: str
    intent_id: str | None
    focus: str | None
    choices: tuple[BoundedChoice, ...]
    context: tuple[CognitionDatum, ...]

    def __post_init__(self) -> None:
        _require_text("request_id", self.request_id)
        _require_text("instruction", self.instruction)
        if self.intent_id is not None:
            _require_text("intent_id", self.intent_id)
        if self.focus is not None:
            _require_text("focus", self.focus)
        if not isinstance(self.choices, tuple) or not all(
            isinstance(choice, BoundedChoice)
            for choice in self.choices
        ):
            raise InvalidRelayEngineData(
                "choices must be a tuple of BoundedChoice values"
            )
        if len(self.choices) < 2:
            raise InvalidRelayEngineData(
                "bounded choice request requires at least two choices"
            )
        choice_ids = tuple(choice.choice_id for choice in self.choices)
        if len(set(choice_ids)) != len(choice_ids):
            raise InvalidRelayEngineData("choice_id values must be unique")
        if not isinstance(self.context, tuple) or not all(
            isinstance(datum, CognitionDatum)
            for datum in self.context
        ):
            raise InvalidRelayEngineData(
                "context must be a tuple of CognitionDatum values"
            )


@dataclass(frozen=True, slots=True)
class ProviderDecision:
    """Canonical provider result before RelayEngine admissibility checking."""

    status: DecisionStatus
    choice_id: str | None
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, DecisionStatus):
            raise InvalidRelayEngineData(
                "provider decision status must be DecisionStatus"
            )
        if not isinstance(self.reason, str):
            raise InvalidRelayEngineData(
                "provider decision reason must be text"
            )
        if self.status is DecisionStatus.RESOLVED:
            if self.choice_id is None:
                raise InvalidRelayEngineData(
                    "resolved provider decision requires a choice_id"
                )
            _require_text("provider choice_id", self.choice_id)
        elif self.choice_id is not None:
            raise InvalidRelayEngineData(
                "unresolved provider decision cannot carry a choice_id"
            )

    @classmethod
    def resolved(
        cls,
        choice_id: str,
        *,
        reason: str = "",
    ) -> "ProviderDecision":
        return cls(
            status=DecisionStatus.RESOLVED,
            choice_id=choice_id,
            reason=reason,
        )

    @classmethod
    def unresolved(
        cls,
        *,
        reason: str = "",
    ) -> "ProviderDecision":
        return cls(
            status=DecisionStatus.UNRESOLVED,
            choice_id=None,
            reason=reason,
        )


class CognitionProvider(Protocol):
    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision: ...


@dataclass(frozen=True, slots=True)
class RelayEngineAttempt:
    mode: CognitionMode
    status: DecisionStatus
    choice_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class RelayEngineResult:
    """Transient result of one bounded request and optional explicit THINK."""

    status: DecisionStatus
    choice_id: str | None
    attempts: tuple[RelayEngineAttempt, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, DecisionStatus):
            raise InvalidRelayEngineData(
                "RelayEngine result status must be DecisionStatus"
            )
        if not self.attempts:
            raise InvalidRelayEngineData(
                "RelayEngine result requires at least one attempt"
            )
        if self.status is DecisionStatus.RESOLVED:
            if self.choice_id is None:
                raise InvalidRelayEngineData(
                    "resolved RelayEngine result requires a choice_id"
                )
        elif self.choice_id is not None:
            raise InvalidRelayEngineData(
                "unresolved RelayEngine result cannot carry a choice_id"
            )

    @property
    def escalated(self) -> bool:
        return any(
            attempt.mode is CognitionMode.THINK
            for attempt in self.attempts
        )


class RelayEngine:
    """Allocate one bounded cognition call and at most one explicit THINK call.

    The engine owns no Persistent Cognition, Present Projection, Current Intent,
    Skill, Action, external truth, or model state. The supplied provider is a
    replaceable execution mechanism. Provider output is checked only against the
    finite admissible choice surface; a resolved cognition result is still not
    Action authorization or World truth.
    """

    def __init__(self, provider: CognitionProvider) -> None:
        if not callable(provider):
            raise InvalidRelayEngineData("provider must be callable")
        self._provider = provider

    def __call__(self, request: BoundedChoiceRequest) -> RelayEngineResult:
        if not isinstance(request, BoundedChoiceRequest):
            raise InvalidRelayEngineData(
                "RelayEngine requires BoundedChoiceRequest"
            )

        bounded = self._attempt(
            request,
            mode=CognitionMode.BOUNDED,
        )
        if bounded.status is DecisionStatus.RESOLVED:
            return RelayEngineResult(
                status=DecisionStatus.RESOLVED,
                choice_id=bounded.choice_id,
                attempts=(bounded,),
            )

        think = self._attempt(
            request,
            mode=CognitionMode.THINK,
        )
        return RelayEngineResult(
            status=think.status,
            choice_id=think.choice_id,
            attempts=(bounded, think),
        )

    def _attempt(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> RelayEngineAttempt:
        decision = self._provider(request, mode=mode)
        if not isinstance(decision, ProviderDecision):
            raise InvalidRelayEngineData(
                "provider must return ProviderDecision"
            )

        allowed = {
            choice.choice_id
            for choice in request.choices
        }
        if (
            decision.status is DecisionStatus.RESOLVED
            and decision.choice_id not in allowed
        ):
            return RelayEngineAttempt(
                mode=mode,
                status=DecisionStatus.UNRESOLVED,
                choice_id=None,
                reason=(
                    "provider returned inadmissible choice_id: "
                    f"{decision.choice_id}"
                ),
            )

        return RelayEngineAttempt(
            mode=mode,
            status=decision.status,
            choice_id=decision.choice_id,
            reason=decision.reason,
        )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRelayEngineData(
            f"{name} must be a non-empty string"
        )
