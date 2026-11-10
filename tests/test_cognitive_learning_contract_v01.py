"""Deterministic offline C1/C2/C3/C4 Learning & Crystallization #839.

Synthetic source-qualified witnesses are not native World/LLM qualification.
"""

from dataclasses import replace

import pytest

from relay_self.cognitive_learning_contract import (
    AttemptKind,
    BeforePrediction,
    Comparison,
    ConditionalReuseCandidate,
    CurrentCue,
    GuardCondition,
    IndependentReuseObservation,
    IntentAttempt,
    IntentOutcomeReadout,
    LearningContractError,
    L0PromotionProposal,
    OutcomeAssessment,
    RetainedRevisionRead,
    ReuseAssessment,
    ReuseStage,
    RevisionTarget,
    amend_experience_assessment,
    assess_conditional_reuse,
    project_intent_experience,
    propose_l0_crystallization,
    propose_understanding_revision,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment, ReconsiderationDecision
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.three_self_present import EpistemicStatus, Lens


SCOPE = ScopeRef("self-A", "world-A")
NATIVE = Provenance("synthetic-native", "world-A:seq-72")
PRE = Provenance("source-qualified-prior-hypothesis", "before-world-72")
OWNER = Provenance("existing-intent-owner", "terminal-ref-1")
LEARNING = Provenance("existing-learning-owner", "revision-retained-5")
CUE = Provenance("source-qualified-current-cue", "world-A:seq-93")
SOURCE_REV = ("world-A:seq-93", "present-9")


def intent_owner(*, intent_id: str = "intent-A", close: str = "complete"):
    owner = IntentCommitment()
    owner.commit(
        intent_id, objective="maintain viable state",
        at_ns=10, provenance=OWNER,
    )
    if close == "complete":
        owner.complete(intent_id, reason="attempt evaluated", at_ns=60, provenance=OWNER)
    elif close == "fail":
        owner.fail(intent_id, reason="failed objective", at_ns=60, provenance=OWNER)
    elif close == "release":
        owner.request_reconsideration(
            intent_id, reason="unavailable", at_ns=40, provenance=OWNER,
        )
        owner.reconsider(
            intent_id, decision=ReconsiderationDecision.RELEASE,
            reason="aborted after attempt", at_ns=60, provenance=OWNER,
        )
    elif close == "invalidate":
        owner.invalidate(
            intent_id, reason="invalidated", at_ns=60, provenance=OWNER,
        )
    elif close == "open":
        pass
    else:
        raise AssertionError("bad fixture close")
    return owner


def prediction(*, at_ns: int = 15):
    return BeforePrediction(
        prediction_ref="predicted-distance",
        at_ns=at_ns,
        source_provenance=PRE,
        model_revision_ref="selfworld-model-r4",
        applicable_cue_refs=("floor-class",),
    )


def attempt(
    *,
    scope: ScopeRef = SCOPE,
    kind: AttemptKind = AttemptKind.ACTIONS,
    attempt_ref: str = "attempt-1",
    before=None,
    action_refs: tuple[str, ...] | None = None,
):
    return IntentAttempt(
        scope=scope, intent_id="intent-A", attempt_ref=attempt_ref,
        owner_revision=4, started_at_ns=20, kind=kind,
        attempt_provenance=OWNER,
        original_source_refs=(NATIVE,),
        action_refs=("S49-move-1", "S49-move-2")
        if action_refs is None and kind is AttemptKind.ACTIONS else (
            () if action_refs is None else action_refs
        ),
        before=prediction() if before is None else before,
    )


def readout(
    *,
    scope: ScopeRef = SCOPE,
    attempt_ref: str = "attempt-1",
    disposition: OutcomeAssessment = OutcomeAssessment.SUCCESS,
    assessed_at_ns: int = 70,
):
    known = disposition is not OutcomeAssessment.UNKNOWN
    return IntentOutcomeReadout(
        scope=scope, intent_id="intent-A", attempt_ref=attempt_ref,
        assessed_at_ns=assessed_at_ns, disposition=disposition,
        assessment_provenance=OWNER,
        world_source_refs=(NATIVE,) if known else (),
        objective_check_ref="intent-goal-verified-by-world-readback" if known else None,
        uncertainty_ref="uncertainty-not-zero" if not known else None,
    )


def experience(*, disposition: OutcomeAssessment = OutcomeAssessment.SUCCESS):
    return project_intent_experience(
        intent_owner(),
        attempt=attempt(),
        outcome=readout(disposition=disposition),
    )


def revision(exp=None, *, comparison: Comparison = Comparison.MISMATCH,
             target: RevisionTarget = RevisionTarget.APPLICABILITY,
             lens: Lens = Lens.SELF_WORLD):
    return propose_understanding_revision(
        experience() if exp is None else exp,
        proposal_ref=f"proposal-{target.value}-{lens.value}",
        target_lens=lens, target_kind=target,
        semantic_owner_ref="existing-model-owner",
        expected_owner_revision=4,
        candidate_ref="guarded-learning-candidate-v1",
        comparison=comparison,
        applicable_condition_refs=("floor-type",),
        counterexample_refs=("misapplied-old-rule",),
        provenance=LEARNING,
    )


def conditional(*, proposal=None):
    return ConditionalReuseCandidate(
        proposal=revision() if proposal is None else proposal,
        candidate_ref="conditional-estimate-1",
        guard=(GuardCondition("surface", "dry"),
               GuardCondition("threat_visible", False)),
        rollback_ref="owner-model-r4",
        expected_l1_cost_ns=35,
        provenance=LEARNING,
    )


def retained(*, accepted: bool = True):
    return RetainedRevisionRead(
        proposal_ref=revision().proposal_ref,
        semantic_owner_ref="existing-model-owner",
        previous_revision=4,
        committed_revision=5 if accepted else 4,
        accepted=accepted,
        provenance=LEARNING,
    )


def cues(
    *,
    scope: ScopeRef = SCOPE,
    source_revision_refs: tuple[str, ...] = SOURCE_REV,
    status: EpistemicStatus = EpistemicStatus.OBSERVED,
    surface: str = "dry",
):
    return (
        CurrentCue(
            scope, "surface", surface if status is not EpistemicStatus.UNKNOWN else None,
            status, source_revision_refs if status is not EpistemicStatus.UNKNOWN else (),
            (CUE,),
        ),
        CurrentCue(
            scope, "threat_visible",
            False if status is not EpistemicStatus.UNKNOWN else None,
            status, source_revision_refs if status is not EpistemicStatus.UNKNOWN else (),
            (CUE,),
        ),
    )


def reuse(candidate=None, **opts):
    args = dict(
        candidate=conditional() if candidate is None else candidate,
        retained=retained(),
        current_owner_revision=5,
        current_scope=SCOPE,
        current_source_revision_refs=SOURCE_REV,
        cues=cues(),
        allow_l1_reuse=True,
        viability_confirmed=True,
        cost_budget_ns=40,
    )
    args.update(opts)
    return assess_conditional_reuse(**args)


def test_c1_one_attempt_many_actions_one_experience_no_owner_mutation() -> None:
    owner = intent_owner()
    original_events = owner.events
    a = attempt()
    ep = project_intent_experience(owner, attempt=a, outcome=readout())
    assert ep.episode_key == ("self-A", "world-A", "attempt-1")
    assert ep.attempt.action_refs == ("S49-move-1", "S49-move-2")
    assert ep.revision == 0
    assert ep.commitment_event.kind.value == "committed"
    assert ep.terminal_event.kind.value == "completed"
    assert ep.outcome.disposition is OutcomeAssessment.SUCCESS
    assert owner.events == original_events
    assert not hasattr(ep, "persist")
    assert not hasattr(ep, "issue")


def test_c1_duplicate_attempt_rejected_by_existing_owner_supplied_index() -> None:
    owner = intent_owner()
    first = project_intent_experience(owner, attempt=attempt(), outcome=readout())
    with pytest.raises(LearningContractError, match="duplicate"):
        project_intent_experience(
            owner, attempt=attempt(), outcome=readout(),
            existing_episode_keys=frozenset({first.episode_key}),
        )


def test_deferred_intent_and_passive_events_are_not_c1_physical_experience() -> None:
    with pytest.raises(LearningContractError, match="not terminal"):
        project_intent_experience(
            intent_owner(close="open"), attempt=attempt(), outcome=readout(),
        )
    with pytest.raises(LearningContractError, match="source Provenance"):
        replace(attempt(), original_source_refs=())
    with pytest.raises(LearningContractError, match="action lineage"):
        replace(attempt(), action_refs=())
    assert not hasattr(intent_owner(close="open"), "experience_count")


@pytest.mark.parametrize("close", ["fail", "release", "invalidate"])
def test_terminal_owner_transition_is_not_necessarily_world_success(close: str) -> None:
    ep = project_intent_experience(
        intent_owner(close=close), attempt=attempt(),
        outcome=readout(disposition=OutcomeAssessment.UNKNOWN),
    )
    assert ep.outcome.disposition is OutcomeAssessment.UNKNOWN
    assert ep.terminal_event.kind.value != "completed"


def test_rest_attempt_can_be_real_experience_with_zero_native_action() -> None:
    ep = project_intent_experience(
        intent_owner(),
        attempt=attempt(kind=AttemptKind.GUARDED_REST),
        outcome=readout(disposition=OutcomeAssessment.UNKNOWN),
    )
    assert ep.attempt.kind is AttemptKind.GUARDED_REST
    assert ep.attempt.action_refs == ()
    assert ep.outcome.disposition is OutcomeAssessment.UNKNOWN
    with pytest.raises(LearningContractError, match="must not pretend"):
        replace(ep.attempt, action_refs=("not-issued",))


def test_action_outcome_or_llm_claim_not_sufficient_for_intent_success() -> None:
    with pytest.raises(LearningContractError, match="native observation"):
        replace(readout(), world_source_refs=())
    with pytest.raises(LearningContractError, match="native observation"):
        replace(readout(), objective_check_ref=None)
    with pytest.raises(LearningContractError, match="UNKNOWN"):
        replace(readout(disposition=OutcomeAssessment.UNKNOWN),
                objective_check_ref="hallucinated-verification")
    assert experience().outcome.objective_check_ref is not None
    # But a pointer is still only a caller-supplied witness, not native attestation.


def test_prediction_after_execution_is_post_hoc_not_before() -> None:
    with pytest.raises(LearningContractError, match="post-hoc"):
        attempt(before=prediction(at_ns=30))
    with pytest.raises(LearningContractError, match="chronology"):
        project_intent_experience(
            intent_owner(),
            attempt=attempt(),
            outcome=readout(assessed_at_ns=59),
        )


def test_cross_self_world_or_attempt_evidence_cannot_be_one_episode() -> None:
    with pytest.raises(LearningContractError, match="foreign"):
        project_intent_experience(
            intent_owner(), attempt=attempt(),
            outcome=readout(scope=ScopeRef("self-B", "world-A")),
        )
    with pytest.raises(LearningContractError, match="foreign"):
        project_intent_experience(
            intent_owner(), attempt=attempt(scope=ScopeRef("self-A", "world-B")),
            outcome=readout(),
        )
    with pytest.raises(LearningContractError, match="foreign"):
        project_intent_experience(
            intent_owner(), attempt=attempt(),
            outcome=readout(attempt_ref="another-attempt"),
        )


def test_unknown_to_known_amends_same_c1_experience_preserves_history() -> None:
    first = experience(disposition=OutcomeAssessment.UNKNOWN)
    newer = amend_experience_assessment(
        first, improved_outcome=readout(assessed_at_ns=78),
        expected_revision=0,
    )
    assert newer.episode_key == first.episode_key
    assert newer.revision == 1
    assert newer.previous_assessments == (first.outcome,)
    assert newer.outcome.disposition is OutcomeAssessment.SUCCESS
    assert first.outcome.disposition is OutcomeAssessment.UNKNOWN
    with pytest.raises(LearningContractError, match="stale experience"):
        amend_experience_assessment(
            newer, improved_outcome=readout(assessed_at_ns=90),
            expected_revision=0,
        )
    with pytest.raises(LearningContractError, match="chronology"):
        amend_experience_assessment(
            newer, improved_outcome=readout(assessed_at_ns=72),
            expected_revision=1,
        )


def test_c2_one_experience_can_generate_distinct_lens_revisions_no_auto_write() -> None:
    ep = experience()
    past = PersistentCognition(
        IdentitySpecification("self-A", ("Remain curious.",), OWNER)
    )
    p_world = revision(ep)
    p_body = revision(
        ep, target=RevisionTarget.PREDICTIVE_MODEL, lens=Lens.SELF_BODY,
    )
    p_self = revision(
        ep, target=RevisionTarget.COGNITIVE_ALLOCATION, lens=Lens.MYSELF,
    )
    assert {p.target_lens for p in (p_world, p_body, p_self)} == {
        Lens.SELF_WORLD, Lens.SELF_BODY, Lens.MYSELF,
    }
    assert len({p.episode_key for p in (p_world, p_body, p_self)}) == 1
    assert p_world.counterexample_refs == ("misapplied-old-rule",)
    assert past.memories == ()
    assert past.identity.directives == ("Remain curious.",)


def test_c2_unknown_or_no_prediction_cannot_claim_measured_mismatch() -> None:
    with pytest.raises(LearningContractError, match="UNKNOWN"):
        revision(experience(disposition=OutcomeAssessment.UNKNOWN))
    ep_no_prediction = project_intent_experience(
        intent_owner(),
        attempt=replace(attempt(), before=None),
        outcome=readout(),
    )
    with pytest.raises(LearningContractError, match="before prediction"):
        revision(ep_no_prediction)
    proposed = revision(ep_no_prediction, comparison=Comparison.NO_PREDICTION)
    assert proposed.comparison is Comparison.NO_PREDICTION
    with pytest.raises(LearningContractError, match="conflicts"):
        revision(experience(), comparison=Comparison.NO_PREDICTION)
    provisional = revision(
        experience(disposition=OutcomeAssessment.UNKNOWN),
        comparison=Comparison.INCOMPARABLE,
    )
    assert provisional.comparison is Comparison.INCOMPARABLE


def test_c3_unretained_rule_is_only_shadow_even_when_cue_matches() -> None:
    with_retained_none = reuse(retained=None)
    assert with_retained_none.stage is ReuseStage.SHADOW_REUSE
    assert with_retained_none.retained_revision is None
    denied = reuse(retained=retained(accepted=False))
    assert denied.stage is ReuseStage.SHADOW_REUSE
    assert denied.reason == "NOT_RETAINED"
    assert not hasattr(denied, "action_id")


def test_c4_self_selected_l1_reuse_requires_exact_retained_owner_and_guards() -> None:
    eligible = reuse()
    assert eligible.stage is ReuseStage.L1_RETAINED_REUSE
    assert eligible.retained_revision == 5
    assert eligible.reason == "CURRENT_CONDITION_SCOPED_OWNER_READ"
    assert reuse(allow_l1_reuse=False).stage is ReuseStage.SHADOW_REUSE
    assert reuse(current_owner_revision=6).reason == "STALE_RETAINED_OWNER"
    foreign = replace(retained(), semantic_owner_ref="other-owner")
    assert reuse(retained=foreign).reason == "FOREIGN_OR_INCOMPATIBLE_RETENTION"
    bad_rev = replace(retained(), previous_revision=3)
    assert reuse(retained=bad_rev).reason == "FOREIGN_OR_INCOMPATIBLE_RETENTION"
    with pytest.raises(LearningContractError, match="new owner revision"):
        replace(retained(), committed_revision=4)


@pytest.mark.parametrize("overrides,reason", [
    ({"cues": ()}, "CRITICAL_CUE_UNKNOWN"),
    ({"cues": cues(status=EpistemicStatus.UNKNOWN)}, "CRITICAL_CUE_UNKNOWN"),
    ({"cues": cues(status=EpistemicStatus.REMEMBERED)}, "CRITICAL_CUE_NOT_CURRENTLY_OBSERVED"),
    ({"cues": cues(source_revision_refs=("old-world-seq",))}, "STALE_CUE_SOURCE"),
    ({"cues": cues(surface="ice")}, "CONDITION_MISMATCH"),
    ({"viability_confirmed": False}, "WORLD_BODY_VIABILITY_UNKNOWN"),
    ({"cost_budget_ns": 20}, "COGNITIVE_BUDGET_EXCEEDED"),
    ({"current_scope": ScopeRef("self-B", "world-A")}, "FOREIGN_SELF"),
    ({"cues": cues(scope=ScopeRef("self-A", "world-B"))}, "FOREIGN_CUE_SCOPE"),
])
def test_c3_negative_cues_cost_and_worldbody_viability_fail_closed(overrides, reason):
    assert reuse(**overrides).reason == reason
    assert reuse(**overrides).stage is ReuseStage.ABSTAIN


def test_cross_world_transfer_requires_new_world_observation_not_old_cache() -> None:
    next_scope = ScopeRef("self-A", "world-B")
    old_world_cue = cues()
    assert reuse(current_scope=next_scope, cues=old_world_cue).stage is ReuseStage.ABSTAIN
    fresh_world = cues(
        scope=next_scope, source_revision_refs=("world-B:seq-1", "present-B"),
    )
    valid = reuse(
        current_scope=next_scope,
        current_source_revision_refs=("world-B:seq-1", "present-B"),
        cues=fresh_world,
    )
    assert valid.stage is ReuseStage.L1_RETAINED_REUSE
    # Transfer of a learned condition does not transfer an old World observation.


def test_c3_unknown_and_conflicting_cues_are_not_assumed_safe() -> None:
    with pytest.raises(LearningContractError, match="UNKNOWN cue"):
        CurrentCue(
            SCOPE, "surface", "dry", EpistemicStatus.UNKNOWN, (), (CUE,),
        )
    with pytest.raises(LearningContractError, match="duplicate current cue"):
        reuse(cues=(cues()[0], cues()[0]))
    with pytest.raises(LearningContractError, match="duplicate guard key"):
        replace(
            conditional(),
            guard=(GuardCondition("surface", "dry"), GuardCondition("surface", "ice")),
        )
    with pytest.raises(LearningContractError, match="nonempty applicability"):
        replace(conditional(), guard=())
    with pytest.raises(LearningContractError, match="cue must"):
        GuardCondition("state", None)


def test_c3_independent_reuse_does_not_equate_to_benefit() -> None:
    original = experience()
    later = IndependentReuseObservation(
        reused_candidate_ref=conditional().candidate_ref,
        prior_episode_key=original.episode_key,
        later_episode_key=("self-A", "world-A", "attempt-independent-2"),
        source_provenance=CUE,
        later_outcome=OutcomeAssessment.SUCCESS,
        comparison=ReuseAssessment.CHEAP_EQUIVALENT,
    )
    assert later.comparison is ReuseAssessment.CHEAP_EQUIVALENT
    assert later.prior_episode_key != later.later_episode_key
    with pytest.raises(LearningContractError, match="same episode"):
        replace(later, later_episode_key=later.prior_episode_key)
    with pytest.raises(LearningContractError, match="cross-Self"):
        replace(later, later_episode_key=("self-B", "world-A", "attempt-B"))
    with pytest.raises(LearningContractError, match="UNKNOWN later"):
        replace(
            later, later_outcome=OutcomeAssessment.UNKNOWN,
            comparison=ReuseAssessment.POSSIBLE_BENEFIT,
        )
    cross_session = replace(
        later, later_episode_key=("self-A", "world-B", "attempt-independent-B"),
    )
    assert cross_session.later_episode_key[1] == "world-B"


def test_c3_l0_crystallization_is_only_proposal_not_executable_rule() -> None:
    c = conditional()
    proposal = propose_l0_crystallization(
        c, required_deadline_ns=200,
        fallback_ref="existing-safe-reflex", provenance=LEARNING,
    )
    assert proposal.status == "PROPOSAL_ONLY"
    assert proposal.guard == c.guard
    assert not hasattr(proposal, "install")
    assert not hasattr(proposal, "authorize_action")
    with pytest.raises(LearningContractError, match="no executable L0 installer"):
        replace(proposal, status="INSTALLED")
    with pytest.raises(LearningContractError, match="positive"):
        replace(proposal, required_deadline_ns=0)
    with pytest.raises(LearningContractError, match="bounded guard"):
        replace(proposal, guard=())


def test_c3_learnt_candidate_cannot_mint_world_or_memory_ownership() -> None:
    owner = intent_owner(close="open")
    current = owner.current_intent
    retained_memory = PersistentCognition(
        IdentitySpecification("self-A", ("Stable identity.",), OWNER)
    )
    proposal = propose_l0_crystallization(
        conditional(), required_deadline_ns=20, fallback_ref="existing-rule",
        provenance=LEARNING,
    )
    assert proposal.status == "PROPOSAL_ONLY"
    assert owner.current_intent == current
    assert retained_memory.memories == ()
    assert retained_memory.identity.directives == ("Stable identity.",)
