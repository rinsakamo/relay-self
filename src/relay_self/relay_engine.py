from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from relay_self.provenance import Provenance


class RelayEngineError(ValueError):
    """Base error for the minimum transient RelayEngine contract."""


class InvalidRelayEngineData(RelayEngineError):
    """Raised when cognition data violates the current contract."""


class CognitionMode(str, Enum):
    BOUNDED = "bounded"
    THINK = "think"
    OPEN = "open"


class DecisionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ProviderCallFacts:
    """Content-free request/response facts for one provider call."""

    requested_max_output_tokens: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None

    def __post_init__(self) -> None:
        _require_optional_positive_int(
            "requested_max_output_tokens",
            self.requested_max_output_tokens,
        )
        _require_optional_non_negative_int("prompt_tokens", self.prompt_tokens)
        _require_optional_non_negative_int(
            "completion_tokens",
            self.completion_tokens,
        )
        _require_optional_non_negative_int("total_tokens", self.total_tokens)
        if self.finish_reason is not None:
            _require_text("finish_reason", self.finish_reason)


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
    soft_wall_time_budget_s: float | None = None
    think_allowed: bool = True

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
        if self.soft_wall_time_budget_s is not None:
            _require_positive_finite_number(
                "soft_wall_time_budget_s",
                self.soft_wall_time_budget_s,
            )
        if not isinstance(self.think_allowed, bool):
            raise InvalidRelayEngineData("think_allowed must be bool")


@dataclass(frozen=True, slots=True)
class OpenCognitionRequest:
    """Transient open-ended cognition request for one generated expression."""

    request_id: str
    instruction: str
    intent_id: str | None
    focus: str | None
    context: tuple[CognitionDatum, ...]

    def __post_init__(self) -> None:
        _require_text("request_id", self.request_id)
        _require_text("instruction", self.instruction)
        if self.intent_id is not None:
            _require_text("intent_id", self.intent_id)
        if self.focus is not None:
            _require_text("focus", self.focus)
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
    call_facts: ProviderCallFacts = field(default_factory=ProviderCallFacts)

    def __post_init__(self) -> None:
        if not isinstance(self.status, DecisionStatus):
            raise InvalidRelayEngineData(
                "provider decision status must be DecisionStatus"
            )
        if not isinstance(self.reason, str):
            raise InvalidRelayEngineData(
                "provider decision reason must be text"
            )
        if not isinstance(self.call_facts, ProviderCallFacts):
            raise InvalidRelayEngineData(
                "provider decision call_facts must be ProviderCallFacts"
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
        call_facts: ProviderCallFacts | None = None,
    ) -> "ProviderDecision":
        return cls(
            status=DecisionStatus.RESOLVED,
            choice_id=choice_id,
            reason=reason,
            call_facts=call_facts or ProviderCallFacts(),
        )

    @classmethod
    def unresolved(
        cls,
        *,
        reason: str = "",
        call_facts: ProviderCallFacts | None = None,
    ) -> "ProviderDecision":
        return cls(
            status=DecisionStatus.UNRESOLVED,
            choice_id=None,
            reason=reason,
            call_facts=call_facts or ProviderCallFacts(),
        )


@dataclass(frozen=True, slots=True)
class ProviderExpression:
    """Canonical provider output for one open generated expression."""

    text: str
    provenance: Provenance
    call_facts: ProviderCallFacts = field(default_factory=ProviderCallFacts)

    def __post_init__(self) -> None:
        _require_text("provider expression text", self.text)
        if not isinstance(self.provenance, Provenance):
            raise InvalidRelayEngineData(
                "provider expression provenance must be Provenance"
            )
        if not isinstance(self.call_facts, ProviderCallFacts):
            raise InvalidRelayEngineData(
                "provider expression call_facts must be ProviderCallFacts"
            )


class CognitionProvider(Protocol):
    def __call__(
        self,
        request: BoundedChoiceRequest | OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision | ProviderExpression: ...


@dataclass(frozen=True, slots=True)
class RelayEngineAttempt:
    mode: CognitionMode
    status: DecisionStatus
    choice_id: str | None
    reason: str
    elapsed_ns: int = 0
    call_facts: ProviderCallFacts = field(default_factory=ProviderCallFacts)

    def __post_init__(self) -> None:
        if (
            isinstance(self.elapsed_ns, bool)
            or not isinstance(self.elapsed_ns, int)
            or self.elapsed_ns < 0
        ):
            raise InvalidRelayEngineData(
                "RelayEngine attempt elapsed_ns must be a non-negative integer"
            )
        if not isinstance(self.call_facts, ProviderCallFacts):
            raise InvalidRelayEngineData(
                "RelayEngine attempt call_facts must be ProviderCallFacts"
            )

    @property
    def elapsed_s(self) -> float:
        return self.elapsed_ns / 1_000_000_000


@dataclass(frozen=True, slots=True)
class RelayEngineResult:
    """Transient result of one bounded request and optional explicit THINK."""

    status: DecisionStatus
    choice_id: str | None
    attempts: tuple[RelayEngineAttempt, ...]
    soft_wall_time_budget_s: float | None = None
    think_allowed: bool = True

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
        if self.soft_wall_time_budget_s is not None:
            _require_positive_finite_number(
                "soft_wall_time_budget_s",
                self.soft_wall_time_budget_s,
            )
        if not isinstance(self.think_allowed, bool):
            raise InvalidRelayEngineData(
                "RelayEngine result think_allowed must be bool"
            )

    @property
    def escalated(self) -> bool:
        return any(
            attempt.mode is CognitionMode.THINK
            for attempt in self.attempts
        )

    @property
    def provider_call_count(self) -> int:
        return len(self.attempts)

    @property
    def elapsed_ns(self) -> int:
        return sum(attempt.elapsed_ns for attempt in self.attempts)

    @property
    def elapsed_s(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    @property
    def soft_wall_time_budget_exceeded(self) -> bool:
        return (
            self.soft_wall_time_budget_s is not None
            and self.elapsed_s > self.soft_wall_time_budget_s
        )

    @property
    def observed_prompt_tokens(self) -> int | None:
        values = tuple(
            attempt.call_facts.prompt_tokens
            for attempt in self.attempts
        )
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)

    @property
    def observed_completion_tokens(self) -> int | None:
        values = tuple(
            attempt.call_facts.completion_tokens
            for attempt in self.attempts
        )
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)


@dataclass(frozen=True, slots=True)
class OpenCognitionResult:
    """Transient result of exactly one open cognition provider call."""

    request_id: str
    text: str
    provenance: Provenance
    elapsed_ns: int = 0
    call_facts: ProviderCallFacts = field(default_factory=ProviderCallFacts)

    def __post_init__(self) -> None:
        _require_text("open cognition request_id", self.request_id)
        _require_text("open cognition text", self.text)
        if not isinstance(self.provenance, Provenance):
            raise InvalidRelayEngineData(
                "open cognition provenance must be Provenance"
            )
        if (
            isinstance(self.elapsed_ns, bool)
            or not isinstance(self.elapsed_ns, int)
            or self.elapsed_ns < 0
        ):
            raise InvalidRelayEngineData(
                "open cognition elapsed_ns must be a non-negative integer"
            )
        if not isinstance(self.call_facts, ProviderCallFacts):
            raise InvalidRelayEngineData(
                "open cognition call_facts must be ProviderCallFacts"
            )

    @property
    def provider_call_count(self) -> int:
        return 1

    @property
    def elapsed_s(self) -> float:
        return self.elapsed_ns / 1_000_000_000

    @property
    def observed_prompt_tokens(self) -> int | None:
        return self.call_facts.prompt_tokens

    @property
    def observed_completion_tokens(self) -> int | None:
        return self.call_facts.completion_tokens


class RelayEngine:
    """Own bounded decisions and one-call open transient cognition.

    The engine owns no Persistent Cognition, Present Projection, Current Intent,
    Skill, Action, external truth, conversation state, or model state. The
    supplied provider is one replaceable execution mechanism shared by bounded
    and open requests.

    Bounded requests preserve the existing BOUNDED -> optional THINK allocation
    rule. Open requests make exactly one explicit OPEN provider call and do not
    acquire hidden THINK escalation, Action authority, World truth, persistence,
    or proof of external delivery.
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
        if bounded.status is DecisionStatus.RESOLVED or not request.think_allowed:
            return RelayEngineResult(
                status=bounded.status,
                choice_id=bounded.choice_id,
                attempts=(bounded,),
                soft_wall_time_budget_s=request.soft_wall_time_budget_s,
                think_allowed=request.think_allowed,
            )

        think = self._attempt(
            request,
            mode=CognitionMode.THINK,
        )
        return RelayEngineResult(
            status=think.status,
            choice_id=think.choice_id,
            attempts=(bounded, think),
            soft_wall_time_budget_s=request.soft_wall_time_budget_s,
            think_allowed=request.think_allowed,
        )

    def open(self, request: OpenCognitionRequest) -> OpenCognitionResult:
        """Generate one transient expression through the owned provider."""

        if not isinstance(request, OpenCognitionRequest):
            raise InvalidRelayEngineData(
                "RelayEngine.open requires OpenCognitionRequest"
            )

        started_ns = time.perf_counter_ns()
        expression = self._provider(
            request,
            mode=CognitionMode.OPEN,
        )
        elapsed_ns = time.perf_counter_ns() - started_ns

        if not isinstance(expression, ProviderExpression):
            raise InvalidRelayEngineData(
                "open provider must return ProviderExpression"
            )

        return OpenCognitionResult(
            request_id=request.request_id,
            text=expression.text,
            provenance=expression.provenance,
            elapsed_ns=elapsed_ns,
            call_facts=expression.call_facts,
        )

    def _attempt(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> RelayEngineAttempt:
        started_ns = time.perf_counter_ns()
        decision = self._provider(request, mode=mode)
        elapsed_ns = time.perf_counter_ns() - started_ns
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
                elapsed_ns=elapsed_ns,
                call_facts=decision.call_facts,
            )

        return RelayEngineAttempt(
            mode=mode,
            status=decision.status,
            choice_id=decision.choice_id,
            reason=decision.reason,
            elapsed_ns=elapsed_ns,
            call_facts=decision.call_facts,
        )


def _require_optional_non_negative_int(
    name: str,
    value: int | None,
) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidRelayEngineData(
            f"{name} must be a non-negative integer or None"
        )


def _require_optional_positive_int(
    name: str,
    value: int | None,
) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidRelayEngineData(
            f"{name} must be a positive integer or None"
        )


def _require_positive_finite_number(name: str, value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise InvalidRelayEngineData(
            f"{name} must be a finite positive number"
        )


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRelayEngineData(
            f"{name} must be a non-empty string"
        )
