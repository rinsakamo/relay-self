from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.route_adjudication import (
    ControlCandidate,
    RouteDecision,
    RouteDecisionStatus,
    RouteSource,
    control_candidate_from_route_decision,
)


class ExecutionAdmissionError(ValueError):
    """Base error for stateless execution-boundary admission."""


class InvalidExecutionAdmissionData(ExecutionAdmissionError):
    """Raised when admission inputs, guards, or decisions are malformed."""


class AdmissionPolicy(str, Enum):
    """Supported explicit execution-entry guard policies."""

    CURRENT_INTENT_ALLOW_LIST = "current_intent_allow_list"


class AdmissionDecisionStatus(str, Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"
    UNDETERMINED = "undetermined"


class AdmissionReason(str, Enum):
    ADMITTED = "admitted"
    MISSING_CURRENT_INTENT = "missing_current_intent"
    CURRENT_INTENT_MISMATCH = "current_intent_mismatch"
    CANDIDATE_NOT_ALLOWED = "candidate_not_allowed"
    ROUTE_NOT_ADMISSIBLE = "route_not_admissible"
    CONTROL_ROUTE_MISMATCH = "control_route_mismatch"


@dataclass(frozen=True, slots=True)
class ExecutionAdmissionCriterion:
    """Explicit non-cognitive guard for entry into later execution handling."""

    criterion_id: str
    policy: AdmissionPolicy
    required_intent_id: str
    allowed_candidate_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_identifier("criterion_id", self.criterion_id)
        if not isinstance(self.policy, AdmissionPolicy):
            raise InvalidExecutionAdmissionData(
                "admission policy must be AdmissionPolicy"
            )
        _require_identifier("required_intent_id", self.required_intent_id)
        _validate_identifier_tuple(
            "allowed_candidate_refs",
            self.allowed_candidate_refs,
            allow_empty=False,
        )


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    """Immutable admission result that transfers no execution authority."""

    status: AdmissionDecisionStatus
    candidate_ref: str
    route_status: RouteDecisionStatus
    selected_source: RouteSource | None
    route_criterion_id: str
    control_criterion_id: str
    admission_criterion_id: str
    current_intent_id: str | None
    reason: AdmissionReason
    control_provenance: Provenance
    route_provenance: Provenance
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.status, AdmissionDecisionStatus):
            raise InvalidExecutionAdmissionData(
                "admission status must be AdmissionDecisionStatus"
            )
        _require_identifier("candidate_ref", self.candidate_ref)
        if not isinstance(self.route_status, RouteDecisionStatus):
            raise InvalidExecutionAdmissionData(
                "route_status must be RouteDecisionStatus"
            )
        if self.selected_source is not None and not isinstance(
            self.selected_source,
            RouteSource,
        ):
            raise InvalidExecutionAdmissionData(
                "selected_source must be RouteSource or None"
            )
        _require_identifier("route_criterion_id", self.route_criterion_id)
        _require_identifier("control_criterion_id", self.control_criterion_id)
        _require_identifier(
            "admission_criterion_id",
            self.admission_criterion_id,
        )
        if self.current_intent_id is not None:
            _require_identifier(
                "current_intent_id",
                self.current_intent_id,
            )
        if not isinstance(self.reason, AdmissionReason):
            raise InvalidExecutionAdmissionData(
                "admission reason must be AdmissionReason"
            )
        _require_provenance("control provenance", self.control_provenance)
        _require_provenance("route provenance", self.route_provenance)
        _require_provenance("admission provenance", self.provenance)

        if self.status is AdmissionDecisionStatus.ADMITTED:
            if self.reason is not AdmissionReason.ADMITTED:
                raise InvalidExecutionAdmissionData(
                    "ADMITTED requires ADMITTED reason"
                )
            if self.current_intent_id is None:
                raise InvalidExecutionAdmissionData(
                    "ADMITTED requires a current intent identity"
                )
            if self.route_status not in {
                RouteDecisionStatus.SELECTED,
                RouteDecisionStatus.AGREED,
            }:
                raise InvalidExecutionAdmissionData(
                    "ADMITTED requires an executable S12 route status"
                )
            return

        if self.status is AdmissionDecisionStatus.UNDETERMINED:
            if self.reason is not AdmissionReason.MISSING_CURRENT_INTENT:
                raise InvalidExecutionAdmissionData(
                    "UNDETERMINED requires missing-current-intent reason"
                )
            if self.current_intent_id is not None:
                raise InvalidExecutionAdmissionData(
                    "missing-current-intent result cannot contain current intent"
                )
            return

        if self.reason not in {
            AdmissionReason.CURRENT_INTENT_MISMATCH,
            AdmissionReason.CANDIDATE_NOT_ALLOWED,
            AdmissionReason.ROUTE_NOT_ADMISSIBLE,
            AdmissionReason.CONTROL_ROUTE_MISMATCH,
        }:
            raise InvalidExecutionAdmissionData(
                "REJECTED requires an explicit rejection reason"
            )


def admit_control_candidate(
    candidate: ControlCandidate,
    route_decision: RouteDecision,
    intent_commitment: IntentCommitment | None,
    criterion: ExecutionAdmissionCriterion,
    *,
    provenance: Provenance,
) -> AdmissionDecision:
    """Evaluate one ControlCandidate at the existing Intent authority boundary.

    This function never commits or replaces Intent, starts SkillExecution,
    proposes/authorizes/issues Action, mutates Memory/LRN, or invokes a model.
    The actual IntentCommitment owner is read only to determine whether the
    explicitly required Current Intent is present.
    """

    if not isinstance(candidate, ControlCandidate):
        raise InvalidExecutionAdmissionData(
            "candidate must be ControlCandidate"
        )
    if not isinstance(route_decision, RouteDecision):
        raise InvalidExecutionAdmissionData(
            "route_decision must be RouteDecision"
        )
    if intent_commitment is not None and not isinstance(
        intent_commitment,
        IntentCommitment,
    ):
        raise InvalidExecutionAdmissionData(
            "intent_commitment must be IntentCommitment or None"
        )
    if not isinstance(criterion, ExecutionAdmissionCriterion):
        raise InvalidExecutionAdmissionData(
            "criterion must be ExecutionAdmissionCriterion"
        )
    _require_provenance("admission provenance", provenance)

    current_intent = (
        None
        if intent_commitment is None
        else intent_commitment.current_intent
    )
    current_intent_id = (
        None
        if current_intent is None
        else current_intent.intent_id
    )

    expected_control = control_candidate_from_route_decision(route_decision)
    if expected_control is None:
        return _decision(
            AdmissionDecisionStatus.REJECTED,
            AdmissionReason.ROUTE_NOT_ADMISSIBLE,
            candidate,
            route_decision,
            criterion,
            current_intent_id=current_intent_id,
            provenance=provenance,
        )

    if candidate != expected_control:
        return _decision(
            AdmissionDecisionStatus.REJECTED,
            AdmissionReason.CONTROL_ROUTE_MISMATCH,
            candidate,
            route_decision,
            criterion,
            current_intent_id=current_intent_id,
            provenance=provenance,
        )

    if current_intent is None:
        return _decision(
            AdmissionDecisionStatus.UNDETERMINED,
            AdmissionReason.MISSING_CURRENT_INTENT,
            candidate,
            route_decision,
            criterion,
            current_intent_id=None,
            provenance=provenance,
        )

    if current_intent.intent_id != criterion.required_intent_id:
        return _decision(
            AdmissionDecisionStatus.REJECTED,
            AdmissionReason.CURRENT_INTENT_MISMATCH,
            candidate,
            route_decision,
            criterion,
            current_intent_id=current_intent.intent_id,
            provenance=provenance,
        )

    if candidate.candidate_ref not in criterion.allowed_candidate_refs:
        return _decision(
            AdmissionDecisionStatus.REJECTED,
            AdmissionReason.CANDIDATE_NOT_ALLOWED,
            candidate,
            route_decision,
            criterion,
            current_intent_id=current_intent.intent_id,
            provenance=provenance,
        )

    return _decision(
        AdmissionDecisionStatus.ADMITTED,
        AdmissionReason.ADMITTED,
        candidate,
        route_decision,
        criterion,
        current_intent_id=current_intent.intent_id,
        provenance=provenance,
    )


def _decision(
    status: AdmissionDecisionStatus,
    reason: AdmissionReason,
    candidate: ControlCandidate,
    route_decision: RouteDecision,
    criterion: ExecutionAdmissionCriterion,
    *,
    current_intent_id: str | None,
    provenance: Provenance,
) -> AdmissionDecision:
    return AdmissionDecision(
        status=status,
        candidate_ref=candidate.candidate_ref,
        route_status=route_decision.status,
        selected_source=candidate.selected_source,
        route_criterion_id=route_decision.criterion.criterion_id,
        control_criterion_id=candidate.criterion_id,
        admission_criterion_id=criterion.criterion_id,
        current_intent_id=current_intent_id,
        reason=reason,
        control_provenance=candidate.provenance,
        route_provenance=route_decision.provenance,
        provenance=provenance,
    )


def _validate_identifier_tuple(
    name: str,
    values: object,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(values, tuple):
        raise InvalidExecutionAdmissionData(f"{name} must be a tuple")
    if not allow_empty and not values:
        raise InvalidExecutionAdmissionData(f"{name} must not be empty")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_identifier(f"{name}[{index}]", value)
        assert isinstance(value, str)
        if value in seen:
            raise InvalidExecutionAdmissionData(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidExecutionAdmissionData(
            f"{name} must be a non-empty string"
        )
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidExecutionAdmissionData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidExecutionAdmissionData(f"{name} must be Provenance")
