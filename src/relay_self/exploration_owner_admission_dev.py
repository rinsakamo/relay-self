"""D2 Owner admission adapter: Goal review and actual original IntentCommitment.

The Present/Intent owner supplies all revisions, decisions and history. This
module has no own state, no Goal database, no SkillRunner, no ActionPort and no
native issuance. The owner must explicitly publish an adopted Goal to Present
BEFORE separately starting an Intent using the original IntentCommitment.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relay_self.cognitive_minimal_dev import Option, resolve_l1_choice
from relay_self.common_io import ScopeRef
from relay_self.exploration_goal_dev import ExplorationRound
from relay_self.intent import CurrentIntent, IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import RelayEngineResult


class ExplorationOwnerError(ValueError):
    """An unqualified or stale owner decision, not a World/Skill outcome."""


class GoalDisposition(str, Enum):
    ADOPT = "ADOPT"
    HOLD = "HOLD"
    CONTINUE = "CONTINUE"


class GoalReviewStatus(str, Enum):
    ADOPTION_PROPOSED = "ADOPTION_PROPOSED"
    HELD = "HELD"
    CONTINUED = "CONTINUED"


@dataclass(frozen=True, slots=True)
class OwnerGoalReadout:
    """Immutable **existing Self owner** view; not a new Goal owner/ledger.

    Incumbent strength, horizon, and transition time come from owner history.
    A missing incumbent must not be synthesized from the candidate.
    """

    scope: ScopeRef
    revision: int
    incumbent_goal_ref: str | None
    incumbent_intensity: float | None
    last_goal_transition_ns: int | None
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not isinstance(
            self.provenance, Provenance
        ):
            raise ExplorationOwnerError("owner scope and provenance required")
        _nonnegative("owner revision", self.revision)
        if self.incumbent_goal_ref is None:
            if self.incumbent_intensity is not None:
                raise ExplorationOwnerError("no strength without incumbent")
        elif (not isinstance(self.incumbent_goal_ref, str)
              or not self.incumbent_goal_ref.strip()):
            raise ExplorationOwnerError("incumbent Goal reference missing")
        if self.incumbent_intensity is not None:
            _fraction("incumbent intensity", self.incumbent_intensity)
        if self.last_goal_transition_ns is not None:
            _nonnegative("last goal transition", self.last_goal_transition_ns)


@dataclass(frozen=True, slots=True)
class GoalReviewPolicy:
    """Caller-supplied *Goal reconsideration* policy, NOT an Action permission."""

    min_hold_ns: int = 0
    switch_margin: float = 0.0

    def __post_init__(self) -> None:
        _nonnegative("Goal hold duration", self.min_hold_ns)
        _fraction("Goal switch margin", self.switch_margin)


@dataclass(frozen=True, slots=True)
class OwnerGoalReview:
    """Current round + exact owner view; a receipt, never durable adoption."""

    scope: ScopeRef
    goal_ref: str
    question_refs: tuple[str, ...]
    signal_ref: str
    source_revision_refs: tuple[str, ...]
    frame_revision: int
    schema_revision: int
    owner_revision: int
    intent_event_count: int
    intent_last_at_ns: int | None
    status: GoalReviewStatus
    reason: str
    reviewed_at_ns: int
    provenance: Provenance


def _nonnegative(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise ExplorationOwnerError(f"{name} must be nonnegative integer")


def _fraction(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ExplorationOwnerError(f"{name} must be finite 0..1")
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ExplorationOwnerError(f"{name} must be finite 0..1")


def review_exploration_goal(
    round_: ExplorationRound,
    *,
    goal_ref: str,
    disposition: GoalDisposition,
    owner: OwnerGoalReadout,
    intent_owner: IntentCommitment,
    policy: GoalReviewPolicy,
    current_present_revision: int,
    current_schema_revision: int,
    current_source_revision_refs: tuple[str, ...],
    now_ns: int,
) -> OwnerGoalReview:
    """Review **owner-requested** ADOPT/HOLD/CONTINUE, not select for Self.

    A live different Intent can only be reconsidered/released through the
    original IntentCommitment, never by changing a D Schema signal. FAST L0
    and independent urgent Needs bypass this non-emergency Goal review.
    """
    if not isinstance(round_, ExplorationRound) or not isinstance(
        owner, OwnerGoalReadout
    ) or not isinstance(intent_owner, IntentCommitment) or not isinstance(
        policy, GoalReviewPolicy
    ) or not isinstance(disposition, GoalDisposition):
        raise ExplorationOwnerError("typed round/owner/policy/decision required")
    for name, value in (
        ("current Present revision", current_present_revision),
        ("current Schema revision", current_schema_revision),
        ("review time", now_ns),
    ):
        _nonnegative(name, value)
    present = round_.present
    scope = present.three_self.scope
    if (
        owner.scope != scope
        or owner.revision != round_.owner_revision
        or present.frame_revision != current_present_revision
        or present.registry_revision != current_schema_revision
        or present.three_self.source_revision_refs != current_source_revision_refs
        or round_.frame.scope != scope
        or round_.frame.source not in round_.need.signal.envelope.source_refs
        or round_.need.signal.envelope.event_id not in {
            s.envelope.event_id for s in present.signals
        }
    ):
        raise ExplorationOwnerError("stale/foreign Owner/Present/Schema source")
    if owner.incumbent_goal_ref is not None and (
        owner.incumbent_goal_ref not in present.active_goal_refs
    ):
        raise ExplorationOwnerError("incumbent Goal absent from original Present")
    if owner.last_goal_transition_ns is not None and (
        owner.last_goal_transition_ns > now_ns
    ):
        raise ExplorationOwnerError("Goal transition is from the future")
    if (intent_owner.last_at_ns is not None
            and intent_owner.last_at_ns > now_ns):
        raise ExplorationOwnerError("Intent Owner is from the future")
    matched = tuple(p for p in round_.proposals if p.goal.goal_id == goal_ref)
    if len(matched) != 1:
        raise ExplorationOwnerError("Goal is not an eligible exploratory proposal")
    candidate = matched[0]
    current = intent_owner.current_intent
    # Requests are explicit; D NEVER auto chooses a winner.
    status, reason = GoalReviewStatus.HELD, "OWNER_HELD"
    if disposition is GoalDisposition.CONTINUE:
        if owner.incumbent_goal_ref != goal_ref:
            raise ExplorationOwnerError("cannot CONTINUE an unadopted Goal")
        status, reason = GoalReviewStatus.CONTINUED, "OWNER_CONTINUED"
    elif disposition is GoalDisposition.ADOPT:
        if owner.incumbent_goal_ref == goal_ref:
            status, reason = GoalReviewStatus.CONTINUED, "ALREADY_ADOPTED"
        elif current is not None and current.objective != goal_ref:
            reason = "INCUMBENT_INTENT_MUST_BE_RECONSIDERED"
        elif (owner.incumbent_goal_ref is not None
              and policy.min_hold_ns > 0
              and owner.last_goal_transition_ns is None):
            reason = "GOAL_TENURE_UNKNOWN"
        elif (owner.incumbent_goal_ref is not None
              and owner.last_goal_transition_ns is not None
              and now_ns - owner.last_goal_transition_ns < policy.min_hold_ns):
            reason = "GOAL_HYSTERESIS_HOLD"
        elif (owner.incumbent_goal_ref is not None
              and owner.incumbent_intensity is None):
            reason = "INCUMBENT_STRENGTH_UNKNOWN"
        elif (owner.incumbent_goal_ref is not None
              and owner.incumbent_intensity is not None
              and candidate.intensity < owner.incumbent_intensity + policy.switch_margin):
            reason = "GOAL_MARGIN_HOLD"
        else:
            status, reason = GoalReviewStatus.ADOPTION_PROPOSED, "OWNER_MAY_PUBLISH_GOAL"
    return OwnerGoalReview(
        scope=scope,
        goal_ref=goal_ref, question_refs=candidate.question_refs,
        signal_ref=candidate.need_signal_ref,
        source_revision_refs=current_source_revision_refs,
        frame_revision=current_present_revision,
        schema_revision=current_schema_revision,
        owner_revision=owner.revision,
        intent_event_count=len(intent_owner.events),
        intent_last_at_ns=intent_owner.last_at_ns,
        status=status, reason=reason, reviewed_at_ns=now_ns,
        provenance=owner.provenance,
    )


def begin_adopted_exploration_intent(
    *,
    admission: OwnerGoalReview,
    refreshed: ExplorationRound,
    l1_result: RelayEngineResult,
    intent_owner: IntentCommitment,
    intent_id: str,
    current_owner_revision: int,
    current_source_revision_refs: tuple[str, ...],
    available_skills: frozenset[tuple[str, int]],
    at_ns: int,
    provenance: Provenance,
) -> CurrentIntent:
    """Explicit second stage: original owner commits, no Skill/Action issue.

    Caller must first publish adopted Goal/Question through the actual Present
    owner and rebuild CURRENT Schema/L1; the earlier Goal review is NOT enough.
    The new L1 must choose a complete option and original Intent Owner must
    remain unchanged since review. No automatic Goal->Intent transition.
    """
    if not isinstance(admission, OwnerGoalReview) or not isinstance(
        refreshed, ExplorationRound
    ) or not isinstance(intent_owner, IntentCommitment) or not isinstance(
        l1_result, RelayEngineResult
    ) or not isinstance(provenance, Provenance):
        raise ExplorationOwnerError("typed original owner/start evidence required")
    _nonnegative("current Owner revision", current_owner_revision)
    _nonnegative("Intent start time", at_ns)
    present = refreshed.present
    if (
        admission.status is not GoalReviewStatus.ADOPTION_PROPOSED
        or present.three_self.scope != admission.scope
        or refreshed.frame.scope != admission.scope
        or refreshed.owner_revision != current_owner_revision
        or current_owner_revision != admission.owner_revision + 1
        or present.three_self.source_revision_refs != current_source_revision_refs
        or current_source_revision_refs != admission.source_revision_refs
        or present.registry_revision != admission.schema_revision
        or admission.goal_ref not in present.active_goal_refs
        or not set(admission.question_refs).issubset(present.active_question_refs)
        or not any(p.goal.goal_id == admission.goal_ref
                   for p in refreshed.proposals)
        or intent_owner.current_intent is not None
        or len(intent_owner.events) != admission.intent_event_count
        or intent_owner.last_at_ns != admission.intent_last_at_ns
        or at_ns < admission.reviewed_at_ns
    ):
        raise ExplorationOwnerError("Goal not owner-published or stale/mutated owner")
    selection = resolve_l1_choice(
        refreshed.l1, l1_result, current_frame=refreshed.frame,
        intent_owner=intent_owner, available_skills=available_skills,
    )
    option = selection.option
    if (selection.status != "READY"
            or option is None
            or not isinstance(option, Option)
            or option.schema_id != "exploration"
            or option.goal_id != admission.goal_ref
            or option.invocation is None
            or selection.world_scope != admission.scope):
        raise ExplorationOwnerError("new L1 did not select current adopted invocation")
    # The ONLY write is to the existing original IntentCommitment. The original
    # Skill/Action owners remain separate; WorldBody has not been contacted.
    return intent_owner.commit(
        intent_id, objective=option.goal_id, at_ns=at_ns,
        provenance=provenance,
    )
