"""C Lane C1 bounded child SkillRun: deterministic owner+WAL adversarial tests."""
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.action import ActionLifecycle, ActionState
from relay_self.cognitive_learning_contract import (
    BeforePrediction,
    Comparison,
    ConditionalReuseCandidate,
    CurrentCue,
    EvidenceOrigin,
    GuardCondition,
    OutcomeAssessment,
    RetainedRevisionRead,
    RevisionTarget,
    UnderstandingProposal,
)
from relay_self.cognitive_learning_owner_adapter import (
    BoundedSkillRead,
    C1AdmissionError,
    TargetRead,
    WalActionRead,
    WalDisposition,
    WorldBodyRead,
    assemble_bounded_skill_experience,
    c3_shadow_l1_context,
    propose_c2_understanding,
    propose_existing_memory,
)
from relay_self.common_io import Clock, ClockStamp, ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice
from relay_self.skill import SkillExecution
from relay_self.three_self_present import EpistemicStatus, Lens

P = Provenance("test-owner", "original-readout")
SHA = "a" * 64


def make_read(*, count=4, run_id="skillrun-A", scope=None):
    scope = scope or ScopeRef("A", "paper-session-1")
    cognition = PersistentCognition(
        identity=IdentitySpecification(self_id="A", directives=("continue",), provenance=P)
    )
    owner = IntentCommitment()
    owner.commit("intent-1", objective="explore", at_ns=10, provenance=P)
    skill = SkillExecution.start(
        run_id, skill_id="MOVE", intent_commitment=owner, at_ns=20, provenance=P
    )
    actions, wal = [], []
    for idx in range(count):
        start = 30 + idx * 15
        action = ActionLifecycle.propose(
            f"{run_id}-a{idx}", skill_execution=skill,
            intent_commitment=owner, at_ns=start, provenance=P,
        )
        action = action.authorize(at_ns=start + 1, provenance=P, authority="original")
        action = action.issue(at_ns=start + 2, deadline_ns=start + 10, provenance=P)
        action = action.record_outcome(at_ns=start + 3, provenance=P)
        actions.append(action)
        wal.append(WalActionRead(
            action_id=action.action_id, scope=scope, world_id="world-1",
            disposition=WalDisposition.TERMINAL_OUTCOME, wal_ref=P, digest_sha256=SHA,
        ))
    skill = skill.succeed(reason="terminated", at_ns=120, provenance=P)
    before = WorldBodyRead(
        scope=scope, world_id="world-1", epoch=7, source_seq=40,
        clock=ClockStamp(Clock.WORLD_TICK, 100), source_refs=(P,),
        origin=EvidenceOrigin.WORLD_BODY_OBSERVED,
    )
    after = replace(
        before, epoch=8, source_seq=41, clock=ClockStamp(Clock.WORLD_TICK, 112)
    )
    return BoundedSkillRead(
        cognition=cognition, intent=owner, skill=skill, actions=tuple(actions),
        wal=tuple(wal), scope=scope, world_id="world-1",
        goal_ref="EXPLORE_WORLD", target_ref="PLACE:1", preset_ref="preset-fixed",
        bound_selection_ref=P, before=before, after=after,
        target=TargetRead(OutcomeAssessment.SUCCESS, check_ref=P, observed_after_ref=P),
    )


def test_one_committed_intent_four_physical_actions_one_experience():
    read = make_read(count=4)
    assert read.intent.current_intent is not None  # long parent stays ACTIVE
    exp = assemble_bounded_skill_experience(read)
    assert exp is not None
    assert exp.intent_id == "intent-1"
    assert exp.action_ids == tuple(a.action_id for a in read.actions)
    assert exp.target_outcome is OutcomeAssessment.SUCCESS
    assert len(exp.action_states) == 4
    assert exp.preset_ref == "preset-fixed"


def test_two_executed_children_same_active_parent_are_distinct():
    one = assemble_bounded_skill_experience(make_read(run_id="r1"))
    two = assemble_bounded_skill_experience(make_read(run_id="r2"))
    assert one.episode_key != two.episode_key
    assert one.memory_id != two.memory_id


def test_duplicate_terminal_receipt_and_existing_memory_owner_dedup(tmp_path: Path):
    read = make_read()
    first = assemble_bounded_skill_experience(read)
    repeated = assemble_bounded_skill_experience(read)
    assert repeated.memory_id == first.memory_id
    candidate = propose_existing_memory(read.cognition, first, integration_provenance=P)
    retained = read.cognition.retain_memory(candidate)  # ONLY Self-owner opt-in call
    assert propose_existing_memory(retained, repeated, integration_provenance=P) is None
    path = tmp_path / "checkpoint.json"
    save_persistent_cognition(path, retained)
    recovered = load_persistent_cognition(path)
    assert recovered.memories == retained.memories
    assert propose_existing_memory(recovered, repeated, integration_provenance=P) is None


def test_unresolved_wal_and_unissued_action_never_create_physical_episode():
    read = make_read()
    pending = replace(read.wal[0], disposition=WalDisposition.PREPARED_UNRESOLVED)
    assert assemble_bounded_skill_experience(
        replace(read, wal=(pending, *read.wal[1:]))
    ) is None
    nonissued = make_read(count=0)
    assert assemble_bounded_skill_experience(nonissued) is None


def test_unknown_after_and_unknown_action_are_not_goal_success():
    read = make_read(count=1)
    assert assemble_bounded_skill_experience(
        replace(read, after=None, target=None)
    ).target_outcome is OutcomeAssessment.UNKNOWN
    with pytest.raises(C1AdmissionError, match="target check"):
        assemble_bounded_skill_experience(replace(read, after=None))
    with pytest.raises(C1AdmissionError, match="agreement"):
        assemble_bounded_skill_experience(replace(
            read, wal=(replace(read.wal[0], disposition=WalDisposition.TERMINAL_UNKNOWN),)
        ))
    # Original Skill may say SUCCEEDED; without independent Goal/Target check -> UNKNOWN.
    assert assemble_bounded_skill_experience(
        replace(read, target=TargetRead(OutcomeAssessment.UNKNOWN))
    ).target_outcome is OutcomeAssessment.UNKNOWN


def test_old_session_foreign_self_clock_domain_and_replayed_action_refused():
    read = make_read(count=1)
    wrong_session = replace(read.after, scope=ScopeRef("A", "stale-session"))
    with pytest.raises(C1AdmissionError, match="after observation"):
        assemble_bounded_skill_experience(replace(read, after=wrong_session))
    with pytest.raises(C1AdmissionError, match="foreign Self"):
        assemble_bounded_skill_experience(
            replace(read, scope=ScopeRef("B", "paper-session-1"))
        )
    with pytest.raises(C1AdmissionError, match="cross-clock"):
        assemble_bounded_skill_experience(replace(
            read, after=replace(read.after, clock=ClockStamp(Clock.HOST_MONOTONIC_NS, 10))
        ))
    with pytest.raises(C1AdmissionError, match="foreign WAL"):
        assemble_bounded_skill_experience(replace(
            read, wal=(replace(read.wal[0], scope=ScopeRef("A", "old-native-session")),)
        ))
    with pytest.raises(C1AdmissionError, match="duplicate child"):
        assemble_bounded_skill_experience(replace(
            read, actions=(read.actions[0], read.actions[0]),
            wal=(read.wal[0], read.wal[0]),
        ))


def test_prediction_must_precede_execution_and_c2_never_upgrades_hypothesis():
    read = make_read(count=1)
    exp = assemble_bounded_skill_experience(read)
    proposal = propose_c2_understanding(
        exp, lens=Lens.SELF_BODY, interpretation="displacement may differ",
        hypothesis="conditions could affect future displacement",
        uncertainty="one bounded sample", counterexample_refs=("counterexample:1",),
    )
    assert proposal.epistemic_status is EpistemicStatus.HYPOTHETICAL
    assert proposal.prior_prediction_ref is None
    assert proposal.observed_refs == exp.evidence_refs
    assert proposal.counterexample_refs == ("counterexample:1",)
    bad_pred = BeforePrediction(
        prediction_ref="future-claim", at_ns=21,
        source_provenance=P, model_revision_ref="model-r1",
    )
    with pytest.raises(C1AdmissionError, match="post-hoc"):
        assemble_bounded_skill_experience(replace(read, before_prediction=bad_pred))
    prediction = replace(bad_pred, at_ns=19)
    predicted = assemble_bounded_skill_experience(replace(read, before_prediction=prediction))
    assert predicted.prediction_ref == "future-claim"


def _c3_candidate(exp):
    proposal = UnderstandingProposal(
        proposal_ref="c2-p1", episode_key=exp.episode_key,
        episode_revision=0, target_lens=Lens.SELF_BODY,
        target_kind=RevisionTarget.APPLICABILITY,
        semantic_owner_ref="original-memory-owner", expected_owner_revision=4,
        candidate_ref="fixed-choice-1", comparison=Comparison.NO_PREDICTION,
        applicable_condition_refs=("condition:surface",),
        counterexample_refs=(), provenance=P,
    )
    return ConditionalReuseCandidate(
        proposal=proposal, candidate_ref="fixed-choice-1",
        guard=(GuardCondition("surface", "stone"),),
        rollback_ref="rollback-r1", expected_l1_cost_ns=10, provenance=P,
    )


def test_c3_considers_only_owner_retained_episode_matching_fresh_condition():
    read = make_read(count=1)
    exp = assemble_bounded_skill_experience(read)
    cand = _c3_candidate(exp)
    retained = RetainedRevisionRead(
        proposal_ref="c2-p1", semantic_owner_ref="original-memory-owner",
        previous_revision=4, committed_revision=5, accepted=True, provenance=P,
    )
    choices = (BoundedChoice("1", "MOVE fixed"), BoundedChoice("2", "DEFER"))
    cue = CurrentCue(
        scope=read.scope, key="surface", value="stone",
        status=EpistemicStatus.OBSERVED, source_revision_refs=("fresh-7",),
        provenance=(P,),
    )
    kwargs = dict(
        candidate=cand, retained=retained, current_scope=read.scope,
        current_source_revision_refs=("fresh-7",), cues=(cue,),
        choice_set=choices, current_owner_revision=5,
        viability_confirmed=True, cost_budget_ns=20,
    )
    # Mere proposed C1, without Self Memory acceptance, cannot be reused.
    assert c3_shadow_l1_context(read.cognition, **kwargs) == (choices, None)
    mem = propose_existing_memory(read.cognition, exp, integration_provenance=P)
    cognition = read.cognition.retain_memory(mem)
    preserved, datum = c3_shadow_l1_context(cognition, **kwargs)
    assert preserved == choices
    assert datum is not None and '"L1_RETAINED_REUSE"' in datum.value_json
    # C3 never changes number, identity or parameters of pre-bound choices.
    for changed in (
        {"cues": (replace(cue, value="dirt"),)},
        {"cues": (replace(cue, status=EpistemicStatus.UNKNOWN,
                          value=None, source_revision_refs=()),)},
        {"cues": (replace(cue, source_revision_refs=("stale-3",)),)},
        {"contradictions": ("opposite-result",)},
        {"viability_confirmed": False},
        {"current_owner_revision": 99},
    ):
        _, blocked = c3_shadow_l1_context(cognition, **(kwargs | changed))
        assert blocked is None


def test_no_memory_write_action_grant_or_gpu_operation_in_assembly():
    read = make_read(count=1)
    prior = read.cognition
    prior_events = read.intent.events
    exp = assemble_bounded_skill_experience(read)
    _ = propose_existing_memory(prior, exp, integration_provenance=P)
    assert prior.memories == ()
    assert read.intent.events == prior_events
    assert all(a.state is ActionState.OUTCOME for a in read.actions)
