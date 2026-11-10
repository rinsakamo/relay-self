"""C1/C2/C3/C4 Learning and Crystallization v0.1 — pure contract (Issue #839).

This module references existing Intent/Memory/Action owners. It DOES NOT
aggregate live S49 events, authenticate WorldBody evidence, own durable
Experience/Memory/Habit state, install L0 rules, or issue physical Actions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment, IntentEvent, IntentEventKind
from relay_self.provenance import Provenance
from relay_self.three_self_present import EpistemicStatus, Lens


class LearningContractError(ValueError):
    """Incorrect scope, owner lineage, evidence or reuse admission."""


class EvidenceOrigin(str, Enum):
    WORLD_BODY_OBSERVED = "WORLD_BODY_OBSERVED"
    COGNITION_ONLY = "COGNITION_ONLY"
    UNKNOWN = "UNKNOWN"


class AttemptKind(str, Enum):
    ACTIONS = "ACTIONS"
    GUARDED_REST = "GUARDED_REST"


class OutcomeAssessment(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class RevisionTarget(str, Enum):
    PREDICTIVE_MODEL = "PREDICTIVE_MODEL"
    APPLICABILITY = "APPLICABILITY"
    PLAN_TENDENCY = "PLAN_TENDENCY"
    COGNITIVE_ALLOCATION = "COGNITIVE_ALLOCATION"


class Comparison(str, Enum):
    MISMATCH = "MISMATCH"
    CONSISTENT = "CONSISTENT"
    NO_PREDICTION = "NO_PREDICTION"
    INCOMPARABLE = "INCOMPARABLE"


class ReuseStage(str, Enum):
    CANDIDATE = "CANDIDATE"
    SHADOW_REUSE = "SHADOW_REUSE"
    L1_RETAINED_REUSE = "L1_RETAINED_REUSE"
    ABSTAIN = "ABSTAIN"


class ReuseAssessment(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    REUSED_OUTCOME_UNKNOWN = "REUSED_OUTCOME_UNKNOWN"
    CHEAP_EQUIVALENT = "CHEAP_EQUIVALENT"
    POSSIBLE_BENEFIT = "POSSIBLE_BENEFIT"
    WORSE_OUTCOME = "WORSE_OUTCOME"


_TERMINAL = frozenset({
    IntentEventKind.COMPLETED,
    IntentEventKind.FAILED,
    IntentEventKind.INVALIDATED,
    IntentEventKind.RECONSIDERED_RELEASE,
})


@dataclass(frozen=True, slots=True)
class BeforePrediction:
    """Source-bound hypothesis recorded BEFORE an actual Intent attempt."""

    prediction_ref: str
    at_ns: int
    source_provenance: Provenance
    model_revision_ref: str
    applicable_cue_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("prediction_ref", self.prediction_ref)
        _nonnegative("prediction at_ns", self.at_ns)
        _provenance(self.source_provenance)
        _text("model_revision_ref", self.model_revision_ref)
        _refs("applicable_cue_refs", self.applicable_cue_refs)


@dataclass(frozen=True, slots=True)
class IntentAttempt:
    """Claim of a *real attempt*, to be checked by the existing physical owner."""

    scope: ScopeRef
    intent_id: str
    attempt_ref: str
    owner_revision: int
    started_at_ns: int
    kind: AttemptKind
    attempt_provenance: Provenance
    original_source_refs: tuple[Provenance, ...]
    evidence_origin: EvidenceOrigin
    action_refs: tuple[str, ...] = ()
    before: BeforePrediction | None = None

    def __post_init__(self) -> None:
        _scope(self.scope)
        _text("intent_id", self.intent_id)
        _text("attempt_ref", self.attempt_ref)
        _nonnegative("owner_revision", self.owner_revision)
        _nonnegative("started_at_ns", self.started_at_ns)
        if not isinstance(self.kind, AttemptKind):
            raise LearningContractError("invalid Intent attempt kind")
        _provenance(self.attempt_provenance)
        _provenances("original_source_refs", self.original_source_refs, required=True)
        if self.evidence_origin is not EvidenceOrigin.WORLD_BODY_OBSERVED:
            raise LearningContractError("Intent attempt requires WorldBody evidence, not L2 text")
        _refs("action_refs", self.action_refs)
        if self.kind is AttemptKind.ACTIONS and not self.action_refs:
            raise LearningContractError("ACTIONS attempt requires action lineage")
        if self.kind is AttemptKind.GUARDED_REST and self.action_refs:
            raise LearningContractError("GUARDED_REST must not pretend native Actions")
        if self.before is not None:
            if not isinstance(self.before, BeforePrediction):
                raise LearningContractError("invalid before prediction")
            if self.before.at_ns > self.started_at_ns:
                raise LearningContractError("post-hoc prediction cannot be BEFORE")


@dataclass(frozen=True, slots=True)
class IntentOutcomeReadout:
    """Intent-level assessment, NOT S16 Action OUTCOME or owner transition."""

    scope: ScopeRef
    intent_id: str
    attempt_ref: str
    assessed_at_ns: int
    disposition: OutcomeAssessment
    assessment_provenance: Provenance
    evidence_origin: EvidenceOrigin
    world_source_refs: tuple[Provenance, ...] = ()
    objective_check_ref: str | None = None
    uncertainty_ref: str | None = None

    def __post_init__(self) -> None:
        _scope(self.scope)
        _text("intent_id", self.intent_id)
        _text("attempt_ref", self.attempt_ref)
        _nonnegative("assessed_at_ns", self.assessed_at_ns)
        if not isinstance(self.disposition, OutcomeAssessment):
            raise LearningContractError("invalid Intent outcome assessment")
        _provenance(self.assessment_provenance)
        _provenances("world_source_refs", self.world_source_refs)
        if self.disposition is not OutcomeAssessment.UNKNOWN:
            if self.evidence_origin is not EvidenceOrigin.WORLD_BODY_OBSERVED:
                raise LearningContractError("known outcome requires WorldBody evidence, not L2 text")
            if not self.world_source_refs or self.objective_check_ref is None:
                raise LearningContractError(
                    "known Intent result requires native observation and objective check"
                )
            _text("objective_check_ref", self.objective_check_ref)
        elif self.objective_check_ref is not None:
            raise LearningContractError("UNKNOWN cannot claim verified objective check")
        if not isinstance(self.evidence_origin, EvidenceOrigin):
            raise LearningContractError("invalid outcome evidence origin")
        if self.uncertainty_ref is not None:
            _text("uncertainty_ref", self.uncertainty_ref)


@dataclass(frozen=True, slots=True)
class IntentExperience:
    """One immutable episode *readout*, not persisted Memory or a ledger write."""

    scope: ScopeRef
    attempt: IntentAttempt
    commitment_event: IntentEvent
    terminal_event: IntentEvent
    outcome: IntentOutcomeReadout
    revision: int = 0
    previous_assessments: tuple[IntentOutcomeReadout, ...] = ()

    @property
    def episode_key(self) -> tuple[str, str, str]:
        return (
            self.scope.self_id,
            self.scope.world_session_id or "",
            self.attempt.attempt_ref,
        )

    def __post_init__(self) -> None:
        _scope(self.scope)
        if (
            self.attempt.scope != self.scope
            or self.outcome.scope != self.scope
            or self.attempt.intent_id != self.outcome.intent_id
            or self.attempt.attempt_ref != self.outcome.attempt_ref
        ):
            raise LearningContractError("foreign Intent/attempt/source in C1 episode")
        if (
            self.commitment_event.kind is not IntentEventKind.COMMITTED
            or self.terminal_event.kind not in _TERMINAL
            or self.commitment_event.intent_id != self.attempt.intent_id
            or self.terminal_event.intent_id != self.attempt.intent_id
        ):
            raise LearningContractError("Intent episode needs original terminal owner event")
        if not (
            self.commitment_event.at_ns
            <= self.attempt.started_at_ns
            <= self.terminal_event.at_ns
            <= self.outcome.assessed_at_ns
        ):
            raise LearningContractError("C1 chronology or post-hoc assessment mismatch")
        _nonnegative("experience revision", self.revision)
        if not isinstance(self.previous_assessments, tuple) or not all(
            isinstance(v, IntentOutcomeReadout) for v in self.previous_assessments
        ):
            raise LearningContractError("invalid earlier assessments")


def project_intent_experience(
    owner: IntentCommitment,
    *,
    attempt: IntentAttempt,
    outcome: IntentOutcomeReadout,
    existing_episode_keys: frozenset[tuple[str, str, str]] = frozenset(),
) -> IntentExperience:
    """Read original Intent owner history; return C1 reference only once.

    The authoritative owner must atomically deduplicate by episode key at write
    time. This in-memory supplied set is a negative-control seam, not a DB.
    """
    if not isinstance(owner, IntentCommitment) or not isinstance(attempt, IntentAttempt):
        raise LearningContractError("existing Intent owner and attempted evidence required")
    if not isinstance(outcome, IntentOutcomeReadout):
        raise LearningContractError("outcome must be typed Intent assessment")
    if not isinstance(existing_episode_keys, frozenset):
        raise LearningContractError("existing episode keys must be owner supplied")
    key = (
        attempt.scope.self_id, attempt.scope.world_session_id or "",
        attempt.attempt_ref,
    )
    if key in existing_episode_keys:
        raise LearningContractError("duplicate attempted-Intent experience key")
    relevant = tuple(e for e in owner.events if e.intent_id == attempt.intent_id)
    commits = tuple(e for e in relevant if e.kind is IntentEventKind.COMMITTED)
    terminals = tuple(e for e in relevant if e.kind in _TERMINAL)
    if len(commits) != 1 or len(terminals) != 1:
        raise LearningContractError("attempt not terminal under existing Intent owner")
    if relevant[-1] != terminals[0]:
        raise LearningContractError("Intent terminal history is not current")
    return IntentExperience(
        scope=attempt.scope,
        attempt=attempt,
        commitment_event=commits[0],
        terminal_event=terminals[0],
        outcome=outcome,
    )


def amend_experience_assessment(
    experience: IntentExperience,
    *,
    improved_outcome: IntentOutcomeReadout,
    expected_revision: int,
) -> IntentExperience:
    """New evidence updates the SAME episode readout, not another experience."""
    if not isinstance(experience, IntentExperience):
        raise LearningContractError("experience must be typed")
    if expected_revision != experience.revision:
        raise LearningContractError("stale experience revision")
    if (
        improved_outcome.scope != experience.scope
        or improved_outcome.intent_id != experience.attempt.intent_id
        or improved_outcome.attempt_ref != experience.attempt.attempt_ref
        or improved_outcome.assessed_at_ns <= experience.outcome.assessed_at_ns
    ):
        raise LearningContractError("amendment scope or chronology mismatched")
    if improved_outcome == experience.outcome:
        raise LearningContractError("replayed assessment")
    return replace(
        experience, revision=experience.revision + 1,
        outcome=improved_outcome,
        previous_assessments=(*experience.previous_assessments, experience.outcome),
    )


@dataclass(frozen=True, slots=True)
class UnderstandingProposal:
    """C2 hypothetical *candidate*, not an authorized Memory/Learning write."""

    proposal_ref: str
    episode_key: tuple[str, str, str]
    episode_revision: int
    target_lens: Lens
    target_kind: RevisionTarget
    semantic_owner_ref: str
    expected_owner_revision: int
    candidate_ref: str
    comparison: Comparison
    applicable_condition_refs: tuple[str, ...]
    counterexample_refs: tuple[str, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in ("proposal_ref", "semantic_owner_ref", "candidate_ref"):
            _text(name, getattr(self, name))
        _nonnegative("episode_revision", self.episode_revision)
        _nonnegative("expected_owner_revision", self.expected_owner_revision)
        if not isinstance(self.target_lens, Lens) or not isinstance(
            self.target_kind, RevisionTarget
        ) or not isinstance(self.comparison, Comparison):
            raise LearningContractError("invalid understanding target/comparison")
        _refs("applicable_condition_refs", self.applicable_condition_refs)
        _refs("counterexample_refs", self.counterexample_refs)
        _provenance(self.provenance)


def propose_understanding_revision(
    experience: IntentExperience,
    *,
    proposal_ref: str,
    target_lens: Lens,
    target_kind: RevisionTarget,
    semantic_owner_ref: str,
    expected_owner_revision: int,
    candidate_ref: str,
    comparison: Comparison,
    applicable_condition_refs: tuple[str, ...] = (),
    counterexample_refs: tuple[str, ...] = (),
    provenance: Provenance,
) -> UnderstandingProposal:
    if not isinstance(experience, IntentExperience):
        raise LearningContractError("no original C1 experience")
    if comparison in (Comparison.MISMATCH, Comparison.CONSISTENT):
        if experience.attempt.before is None:
            raise LearningContractError("comparison needs genuine before prediction")
        if experience.outcome.disposition is OutcomeAssessment.UNKNOWN:
            raise LearningContractError("comparison cannot treat UNKNOWN as observed")
    if comparison is Comparison.NO_PREDICTION and experience.attempt.before is not None:
        raise LearningContractError("NO_PREDICTION conflicts with recorded before")
    return UnderstandingProposal(
        proposal_ref=proposal_ref,
        episode_key=experience.episode_key,
        episode_revision=experience.revision,
        target_lens=target_lens,
        target_kind=target_kind,
        semantic_owner_ref=semantic_owner_ref,
        expected_owner_revision=expected_owner_revision,
        candidate_ref=candidate_ref,
        comparison=comparison,
        applicable_condition_refs=applicable_condition_refs,
        counterexample_refs=counterexample_refs,
        provenance=provenance,
    )


@dataclass(frozen=True, slots=True)
class RetainedRevisionRead:
    """Record supplied by the existing semantic owner; not a new write API."""

    proposal_ref: str
    semantic_owner_ref: str
    previous_revision: int
    committed_revision: int
    accepted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        _text("proposal_ref", self.proposal_ref)
        _text("semantic_owner_ref", self.semantic_owner_ref)
        _nonnegative("previous_revision", self.previous_revision)
        _nonnegative("committed_revision", self.committed_revision)
        _bool("accepted", self.accepted)
        _provenance(self.provenance)
        if self.accepted and self.committed_revision <= self.previous_revision:
            raise LearningContractError("accepted retention needs new owner revision")


CueValue = bool | int | str


@dataclass(frozen=True, slots=True)
class GuardCondition:
    key: str
    expected_value: CueValue

    def __post_init__(self) -> None:
        _text("guard cue key", self.key)
        _cue_value(self.expected_value)


@dataclass(frozen=True, slots=True)
class CurrentCue:
    scope: ScopeRef
    key: str
    value: CueValue | None
    status: EpistemicStatus
    source_revision_refs: tuple[str, ...]
    provenance: tuple[Provenance, ...]

    def __post_init__(self) -> None:
        _scope(self.scope)
        _text("cue key", self.key)
        if not isinstance(self.status, EpistemicStatus):
            raise LearningContractError("invalid epistemic cue status")
        _refs("source_revision_refs", self.source_revision_refs)
        _provenances("cue provenance", self.provenance)
        if self.status is EpistemicStatus.UNKNOWN:
            if self.value is not None or self.source_revision_refs:
                raise LearningContractError("UNKNOWN cue cannot assert value")
        else:
            _cue_value(self.value)
            if not self.provenance:
                raise LearningContractError("non-UNKNOWN cue needs source provenance")
        if self.status is EpistemicStatus.OBSERVED and not self.source_revision_refs:
            raise LearningContractError("observed cue needs source revision")


@dataclass(frozen=True, slots=True)
class ConditionalReuseCandidate:
    proposal: UnderstandingProposal
    candidate_ref: str
    guard: tuple[GuardCondition, ...]
    rollback_ref: str
    expected_l1_cost_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, UnderstandingProposal):
            raise LearningContractError("reuse must reference C2 proposal")
        _text("candidate_ref", self.candidate_ref)
        _text("rollback_ref", self.rollback_ref)
        if not isinstance(self.guard, tuple) or not self.guard or not all(
            isinstance(g, GuardCondition) for g in self.guard
        ):
            raise LearningContractError("reuse needs typed nonempty applicability guard")
        if len({g.key for g in self.guard}) != len(self.guard):
            raise LearningContractError("duplicate guard key")
        _positive("expected_l1_cost_ns", self.expected_l1_cost_ns)
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class ReuseReadout:
    candidate_ref: str
    stage: ReuseStage
    reason: str
    retained_revision: int | None = None

    def __post_init__(self) -> None:
        _text("candidate_ref", self.candidate_ref)
        if not isinstance(self.stage, ReuseStage):
            raise LearningContractError("invalid reuse stage")
        _text("reason", self.reason)
        if self.retained_revision is not None:
            _nonnegative("retained_revision", self.retained_revision)


def assess_conditional_reuse(
    candidate: ConditionalReuseCandidate,
    *,
    retained: RetainedRevisionRead | None,
    current_owner_revision: int | None,
    current_scope: ScopeRef,
    current_source_revision_refs: tuple[str, ...],
    cues: tuple[CurrentCue, ...],
    allow_l1_reuse: bool,
    viability_confirmed: bool,
    cost_budget_ns: int,
    current_contradiction_refs: tuple[str, ...] = (),
) -> ReuseReadout:
    """Admit read-only candidate *consideration*, never actual Habit/Action use."""
    if not isinstance(candidate, ConditionalReuseCandidate):
        raise LearningContractError("reuse candidate required")
    _scope(current_scope)
    _refs("current_source_revision_refs", current_source_revision_refs)
    _refs("current_contradiction_refs", current_contradiction_refs)
    _nonnegative("cost_budget_ns", cost_budget_ns)
    _bool("allow_l1_reuse", allow_l1_reuse)
    _bool("viability_confirmed", viability_confirmed)
    if not isinstance(cues, tuple) or not all(isinstance(c, CurrentCue) for c in cues):
        raise LearningContractError("typed current cue tuple required")
    if len({c.key for c in cues}) != len(cues):
        raise LearningContractError("duplicate current cue")
    def readout(stage: ReuseStage, reason: str) -> ReuseReadout:
        return ReuseReadout(
            candidate_ref=candidate.candidate_ref, stage=stage, reason=reason,
            retained_revision=retained.committed_revision
            if isinstance(retained, RetainedRevisionRead) and retained.accepted else None,
        )

    if candidate.proposal.episode_key[0] != current_scope.self_id:
        return readout(ReuseStage.ABSTAIN, "FOREIGN_SELF")
    if any(c.scope != current_scope for c in cues):
        return readout(ReuseStage.ABSTAIN, "FOREIGN_CUE_SCOPE")
    if current_contradiction_refs:
        return readout(ReuseStage.ABSTAIN, "CURRENT_COUNTEREXAMPLE")
    if not viability_confirmed:
        return readout(ReuseStage.ABSTAIN, "WORLD_BODY_VIABILITY_UNKNOWN")
    if candidate.expected_l1_cost_ns > cost_budget_ns:
        return readout(ReuseStage.ABSTAIN, "COGNITIVE_BUDGET_EXCEEDED")

    current = {c.key: c for c in cues}
    for guard in candidate.guard:
        cue = current.get(guard.key)
        if cue is None or cue.status is EpistemicStatus.UNKNOWN:
            return readout(ReuseStage.ABSTAIN, "CRITICAL_CUE_UNKNOWN")
        if cue.status is not EpistemicStatus.OBSERVED:
            return readout(ReuseStage.ABSTAIN, "CRITICAL_CUE_NOT_CURRENTLY_OBSERVED")
        if cue.source_revision_refs != current_source_revision_refs:
            return readout(ReuseStage.ABSTAIN, "STALE_CUE_SOURCE")
        if type(cue.value) is not type(guard.expected_value) or (
            cue.value != guard.expected_value
        ):
            return readout(ReuseStage.ABSTAIN, "CONDITION_MISMATCH")

    if retained is None or not retained.accepted:
        return readout(ReuseStage.SHADOW_REUSE, "NOT_RETAINED")
    if (
        retained.proposal_ref != candidate.proposal.proposal_ref
        or retained.semantic_owner_ref != candidate.proposal.semantic_owner_ref
        or retained.previous_revision != candidate.proposal.expected_owner_revision
    ):
        return readout(ReuseStage.ABSTAIN, "FOREIGN_OR_INCOMPATIBLE_RETENTION")
    if current_owner_revision is None or (
        retained.committed_revision != current_owner_revision
    ):
        return readout(ReuseStage.ABSTAIN, "STALE_RETAINED_OWNER")
    if not allow_l1_reuse:
        return readout(ReuseStage.SHADOW_REUSE, "SELF_CHOSE_SHADOW")
    return readout(ReuseStage.L1_RETAINED_REUSE, "CURRENT_CONDITION_SCOPED_OWNER_READ")


@dataclass(frozen=True, slots=True)
class IndependentReuseObservation:
    """Next actually attempted Intent, distinct from the training C1 episode."""

    reused_candidate_ref: str
    prior_episode_key: tuple[str, str, str]
    later_episode_key: tuple[str, str, str]
    source_provenance: Provenance
    later_outcome: OutcomeAssessment
    comparison: ReuseAssessment

    def __post_init__(self) -> None:
        _text("reused_candidate_ref", self.reused_candidate_ref)
        _provenance(self.source_provenance)
        if self.prior_episode_key == self.later_episode_key:
            raise LearningContractError("same episode cannot prove independent reuse")
        if self.prior_episode_key[0] != self.later_episode_key[0]:
            raise LearningContractError("cross-Self reuse is not a self learning claim")
        if not isinstance(self.later_outcome, OutcomeAssessment):
            raise LearningContractError("invalid later outcome")
        if not isinstance(self.comparison, ReuseAssessment):
            raise LearningContractError("invalid reuse comparison")
        if self.later_outcome is OutcomeAssessment.UNKNOWN and self.comparison not in (
            ReuseAssessment.REUSED_OUTCOME_UNKNOWN, ReuseAssessment.NOT_TESTED
        ):
            raise LearningContractError("UNKNOWN later result cannot prove benefit")
        if self.comparison is ReuseAssessment.POSSIBLE_BENEFIT and (
            self.later_outcome is not OutcomeAssessment.SUCCESS
        ):
            raise LearningContractError("benefit requires positive later Intent outcome")


@dataclass(frozen=True, slots=True)
class L0PromotionProposal:
    """Self may propose future bounded L0 technique; this never installs it."""

    candidate_ref: str
    guard: tuple[GuardCondition, ...]
    required_deadline_ns: int
    rollback_ref: str
    fallback_ref: str
    source_provenance: Provenance
    status: str = "PROPOSAL_ONLY"

    def __post_init__(self) -> None:
        _text("candidate_ref", self.candidate_ref)
        if not isinstance(self.guard, tuple) or not self.guard or not all(
            isinstance(g, GuardCondition) for g in self.guard
        ):
            raise LearningContractError("L0 promotion needs a bounded guard")
        _positive("required_deadline_ns", self.required_deadline_ns)
        _text("rollback_ref", self.rollback_ref)
        _text("fallback_ref", self.fallback_ref)
        _provenance(self.source_provenance)
        if self.status != "PROPOSAL_ONLY":
            raise LearningContractError("no executable L0 installer in this contract")


def propose_l0_crystallization(
    candidate: ConditionalReuseCandidate,
    *,
    required_deadline_ns: int,
    fallback_ref: str,
    provenance: Provenance,
) -> L0PromotionProposal:
    if not isinstance(candidate, ConditionalReuseCandidate):
        raise LearningContractError("requires known conditional candidate")
    return L0PromotionProposal(
        candidate_ref=candidate.candidate_ref,
        guard=candidate.guard,
        required_deadline_ns=required_deadline_ns,
        rollback_ref=candidate.rollback_ref,
        fallback_ref=fallback_ref,
        source_provenance=provenance,
    )


def _scope(value: object) -> None:
    if not isinstance(value, ScopeRef) or value.world_session_id is None:
        raise LearningContractError("experience needs exact Self and World session")


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise LearningContractError(f"{name} requires nonempty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise LearningContractError(f"{name} requires nonnegative integer")


def _positive(name: str, value: object) -> None:
    _nonnegative(name, value)
    if value == 0:
        raise LearningContractError(f"{name} requires positive integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise LearningContractError("typed source Provenance required")


def _provenances(name: str, values: object, *, required: bool = False) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(v, Provenance) for v in values
    ) or (required and not values):
        raise LearningContractError(f"{name} requires tuple of source Provenance")


def _refs(name: str, values: object) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(v, str) or not v.strip() for v in values
    ) or len(set(values)) != len(values):
        raise LearningContractError(f"{name} requires unique typed ref tuple")


def _bool(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise LearningContractError(f"{name} must be bool")


def _cue_value(value: object) -> None:
    if type(value) not in (bool, int, str) or (
        isinstance(value, str) and not value.strip()
    ):
        raise LearningContractError("cue must be bool, int or nonempty string")
