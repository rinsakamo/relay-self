from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.provenance import Provenance


class LearningError(ValueError):
    """Base error for bounded governed retained learning."""


class InvalidLearningData(LearningError):
    """Raised when learning state, feedback, rules, or proposals are malformed."""


class LearningTargetMismatch(LearningError):
    """Raised when feedback/proposal/authority targets another retained owner."""


class StaleLearningUpdate(LearningError):
    """Raised when a proposal no longer matches the owner's exact revision."""


class MissingLearningAuthority(LearningError):
    """Raised when a retained owner transition has no explicit authority."""


class InvalidLearningAuthority(LearningError):
    """Raised when supplied update authority is invalid or not granted."""


class ReplayLearningFeedback(LearningError):
    """Raised when the owner's immediately committed feedback is proposed again."""


class FeedbackDirection(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"


class LearningProposalStatus(str, Enum):
    UPDATED = "updated"
    UNCHANGED_HOLD = "unchanged_hold"
    UNCHANGED_AT_BOUND = "unchanged_at_bound"


@dataclass(frozen=True, slots=True)
class LearningFeedback:
    """One explicit structured feedback event for one retained target."""

    feedback_id: str
    target_id: str
    direction: FeedbackDirection
    provenance: Provenance
    consequence_ref: str | None = None

    def __post_init__(self) -> None:
        _require_identifier("feedback_id", self.feedback_id)
        _require_identifier("feedback target_id", self.target_id)
        if not isinstance(self.direction, FeedbackDirection):
            raise InvalidLearningData(
                "feedback direction must be FeedbackDirection"
            )
        _require_provenance("feedback provenance", self.provenance)
        if self.consequence_ref is not None:
            _require_text("consequence_ref", self.consequence_ref)


@dataclass(frozen=True, slots=True)
class LearningUpdateRule:
    """One explicit bounded deterministic scalar update transformation."""

    rule_id: str
    version: int
    step: int

    def __post_init__(self) -> None:
        _require_identifier("rule_id", self.rule_id)
        _require_positive_int("rule version", self.version)
        _require_positive_int("learning step", self.step)


@dataclass(frozen=True, slots=True)
class LearningUpdateAuthority:
    """Explicit permission to transition exactly one retained learning target."""

    authority_id: str
    target_id: str
    provenance: Provenance
    granted: bool = True

    def __post_init__(self) -> None:
        _require_identifier("authority_id", self.authority_id)
        _require_identifier("authority target_id", self.target_id)
        _require_provenance("authority provenance", self.provenance)
        if not isinstance(self.granted, bool):
            raise InvalidLearningData("authority granted must be bool")


@dataclass(frozen=True, slots=True)
class LearningUpdateProposal:
    """Pure deterministic proposal; creation never mutates retained state."""

    target_id: str
    expected_revision: int
    expected_value: int
    expected_minimum: int
    expected_maximum: int
    proposed_value: int
    feedback: LearningFeedback
    rule: LearningUpdateRule
    status: LearningProposalStatus

    def __post_init__(self) -> None:
        _require_identifier("proposal target_id", self.target_id)
        _require_nonnegative_int("expected_revision", self.expected_revision)
        _require_int("expected_value", self.expected_value)
        _require_int("expected_minimum", self.expected_minimum)
        _require_int("expected_maximum", self.expected_maximum)
        _require_int("proposed_value", self.proposed_value)
        if self.expected_minimum > self.expected_maximum:
            raise InvalidLearningData(
                "proposal minimum cannot exceed maximum"
            )
        if not (
            self.expected_minimum
            <= self.expected_value
            <= self.expected_maximum
        ):
            raise InvalidLearningData(
                "proposal expected value must be inside expected bounds"
            )
        if not (
            self.expected_minimum
            <= self.proposed_value
            <= self.expected_maximum
        ):
            raise InvalidLearningData(
                "proposal value must be inside expected bounds"
            )
        if not isinstance(self.feedback, LearningFeedback):
            raise InvalidLearningData(
                "proposal feedback must be LearningFeedback"
            )
        if not isinstance(self.rule, LearningUpdateRule):
            raise InvalidLearningData(
                "proposal rule must be LearningUpdateRule"
            )
        if not isinstance(self.status, LearningProposalStatus):
            raise InvalidLearningData(
                "proposal status must be LearningProposalStatus"
            )
        if self.feedback.target_id != self.target_id:
            raise LearningTargetMismatch(
                "proposal feedback target does not match proposal target"
            )

        changed = self.proposed_value != self.expected_value
        if self.status is LearningProposalStatus.UPDATED and not changed:
            raise InvalidLearningData(
                "UPDATED proposal must change the retained value"
            )
        if self.status is not LearningProposalStatus.UPDATED and changed:
            raise InvalidLearningData(
                "unchanged proposal status cannot change the retained value"
            )


@dataclass(frozen=True, slots=True)
class LearningCommitRecord:
    """Owner-local audit record for the most recent governed transition."""

    target_id: str
    feedback_id: str
    feedback_provenance: Provenance
    rule_id: str
    rule_version: int
    authority_id: str
    authority_provenance: Provenance
    update_provenance: Provenance
    previous_value: int
    resulting_value: int
    previous_revision: int
    committed_revision: int
    status: LearningProposalStatus

    def __post_init__(self) -> None:
        _require_identifier("record target_id", self.target_id)
        _require_identifier("record feedback_id", self.feedback_id)
        _require_provenance(
            "record feedback provenance",
            self.feedback_provenance,
        )
        _require_identifier("record rule_id", self.rule_id)
        _require_positive_int("record rule_version", self.rule_version)
        _require_identifier("record authority_id", self.authority_id)
        _require_provenance(
            "record authority provenance",
            self.authority_provenance,
        )
        _require_provenance(
            "record update provenance",
            self.update_provenance,
        )
        _require_int("record previous_value", self.previous_value)
        _require_int("record resulting_value", self.resulting_value)
        _require_nonnegative_int(
            "record previous_revision",
            self.previous_revision,
        )
        _require_nonnegative_int(
            "record committed_revision",
            self.committed_revision,
        )
        if self.committed_revision != self.previous_revision + 1:
            raise InvalidLearningData(
                "committed revision must increment exactly once"
            )
        if not isinstance(self.status, LearningProposalStatus):
            raise InvalidLearningData(
                "record status must be LearningProposalStatus"
            )


@dataclass(frozen=True, slots=True)
class LearningPreferenceState:
    """Immutable owner-local retained scalar preference snapshot."""

    target_id: str
    value: int
    minimum: int
    maximum: int
    revision: int
    origin_provenance: Provenance
    last_update: LearningCommitRecord | None = None

    def __post_init__(self) -> None:
        _require_identifier("learning target_id", self.target_id)
        _require_int("learning value", self.value)
        _require_int("learning minimum", self.minimum)
        _require_int("learning maximum", self.maximum)
        if self.minimum > self.maximum:
            raise InvalidLearningData(
                "learning minimum cannot exceed maximum"
            )
        if not self.minimum <= self.value <= self.maximum:
            raise InvalidLearningData(
                "learning value must be inside retained bounds"
            )
        _require_nonnegative_int("learning revision", self.revision)
        _require_provenance(
            "learning origin provenance",
            self.origin_provenance,
        )
        if self.last_update is not None:
            if not isinstance(self.last_update, LearningCommitRecord):
                raise InvalidLearningData(
                    "last_update must be LearningCommitRecord or None"
                )
            if self.last_update.target_id != self.target_id:
                raise LearningTargetMismatch(
                    "last update target does not match retained target"
                )
            if self.last_update.committed_revision != self.revision:
                raise InvalidLearningData(
                    "last update revision must match retained revision"
                )
            if self.last_update.resulting_value != self.value:
                raise InvalidLearningData(
                    "last update value must match retained value"
                )


@dataclass(frozen=True, slots=True)
class LearningCommitResult:
    """Immutable result of one authority-governed owner transition."""

    previous_state: LearningPreferenceState
    new_state: LearningPreferenceState
    proposal: LearningUpdateProposal
    record: LearningCommitRecord

    def __post_init__(self) -> None:
        if not isinstance(self.previous_state, LearningPreferenceState):
            raise InvalidLearningData(
                "previous_state must be LearningPreferenceState"
            )
        if not isinstance(self.new_state, LearningPreferenceState):
            raise InvalidLearningData(
                "new_state must be LearningPreferenceState"
            )
        if not isinstance(self.proposal, LearningUpdateProposal):
            raise InvalidLearningData(
                "proposal must be LearningUpdateProposal"
            )
        if not isinstance(self.record, LearningCommitRecord):
            raise InvalidLearningData(
                "record must be LearningCommitRecord"
            )


def propose_learning_update(
    state: LearningPreferenceState,
    feedback: LearningFeedback,
    rule: LearningUpdateRule,
) -> LearningUpdateProposal:
    """Purely derive one bounded proposal from structured feedback."""

    if not isinstance(state, LearningPreferenceState):
        raise InvalidLearningData(
            "state must be LearningPreferenceState"
        )
    if not isinstance(feedback, LearningFeedback):
        raise InvalidLearningData(
            "feedback must be LearningFeedback"
        )
    if not isinstance(rule, LearningUpdateRule):
        raise InvalidLearningData(
            "rule must be LearningUpdateRule"
        )
    if feedback.target_id != state.target_id:
        raise LearningTargetMismatch(
            "feedback target does not match retained target"
        )
    if (
        state.last_update is not None
        and state.last_update.feedback_id == feedback.feedback_id
    ):
        raise ReplayLearningFeedback(
            "feedback was already committed as the owner's latest update"
        )

    if feedback.direction is FeedbackDirection.HOLD:
        proposed_value = state.value
        status = LearningProposalStatus.UNCHANGED_HOLD
    elif feedback.direction is FeedbackDirection.INCREASE:
        proposed_value = min(state.maximum, state.value + rule.step)
        status = (
            LearningProposalStatus.UPDATED
            if proposed_value != state.value
            else LearningProposalStatus.UNCHANGED_AT_BOUND
        )
    else:
        proposed_value = max(state.minimum, state.value - rule.step)
        status = (
            LearningProposalStatus.UPDATED
            if proposed_value != state.value
            else LearningProposalStatus.UNCHANGED_AT_BOUND
        )

    return LearningUpdateProposal(
        target_id=state.target_id,
        expected_revision=state.revision,
        expected_value=state.value,
        expected_minimum=state.minimum,
        expected_maximum=state.maximum,
        proposed_value=proposed_value,
        feedback=feedback,
        rule=rule,
        status=status,
    )


def commit_learning_update(
    state: LearningPreferenceState,
    proposal: LearningUpdateProposal,
    authority: LearningUpdateAuthority | None,
    *,
    provenance: Provenance,
) -> LearningCommitResult:
    """Commit one proposal only against the exact owner snapshot and authority.

    Every accepted feedback event advances the owner revision, including HOLD
    and bound-clamped no-ops. This makes a committed proposal single-use:
    immediate replay fails stale revision even when the scalar value did not
    change.
    """

    if not isinstance(state, LearningPreferenceState):
        raise InvalidLearningData(
            "state must be LearningPreferenceState"
        )
    if not isinstance(proposal, LearningUpdateProposal):
        raise InvalidLearningData(
            "proposal must be LearningUpdateProposal"
        )
    if authority is None:
        raise MissingLearningAuthority(
            "learning owner transition requires explicit authority"
        )
    if not isinstance(authority, LearningUpdateAuthority):
        raise InvalidLearningAuthority(
            "authority must be LearningUpdateAuthority"
        )
    if not authority.granted:
        raise InvalidLearningAuthority(
            "learning update authority is not granted"
        )
    if proposal.target_id != state.target_id:
        raise LearningTargetMismatch(
            "proposal target does not match retained owner"
        )
    if authority.target_id != state.target_id:
        raise LearningTargetMismatch(
            "authority target does not match retained owner"
        )
    if proposal.expected_revision != state.revision:
        raise StaleLearningUpdate(
            "proposal expected revision does not match retained owner"
        )
    if proposal.expected_value != state.value:
        raise StaleLearningUpdate(
            "proposal expected value does not match retained owner"
        )
    if (
        proposal.expected_minimum != state.minimum
        or proposal.expected_maximum != state.maximum
    ):
        raise StaleLearningUpdate(
            "proposal expected bounds do not match retained owner"
        )
    if (
        state.last_update is not None
        and state.last_update.feedback_id == proposal.feedback.feedback_id
    ):
        raise ReplayLearningFeedback(
            "feedback was already committed as the owner's latest update"
        )
    _require_provenance("update provenance", provenance)

    next_revision = state.revision + 1
    record = LearningCommitRecord(
        target_id=state.target_id,
        feedback_id=proposal.feedback.feedback_id,
        feedback_provenance=proposal.feedback.provenance,
        rule_id=proposal.rule.rule_id,
        rule_version=proposal.rule.version,
        authority_id=authority.authority_id,
        authority_provenance=authority.provenance,
        update_provenance=provenance,
        previous_value=state.value,
        resulting_value=proposal.proposed_value,
        previous_revision=state.revision,
        committed_revision=next_revision,
        status=proposal.status,
    )
    next_state = LearningPreferenceState(
        target_id=state.target_id,
        value=proposal.proposed_value,
        minimum=state.minimum,
        maximum=state.maximum,
        revision=next_revision,
        origin_provenance=state.origin_provenance,
        last_update=record,
    )

    return LearningCommitResult(
        previous_state=state,
        new_state=next_state,
        proposal=proposal,
        record=record,
    )


def _require_positive_int(name: str, value: object) -> None:
    _require_int(name, value)
    assert isinstance(value, int)
    if value <= 0:
        raise InvalidLearningData(f"{name} must be positive")


def _require_nonnegative_int(name: str, value: object) -> None:
    _require_int(name, value)
    assert isinstance(value, int)
    if value < 0:
        raise InvalidLearningData(f"{name} must be non-negative")


def _require_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidLearningData(f"{name} must be an integer")


def _require_identifier(name: str, value: object) -> None:
    _require_text(name, value)
    assert isinstance(value, str)
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidLearningData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidLearningData(f"{name} must be Provenance")


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidLearningData(f"{name} must be a non-empty string")
