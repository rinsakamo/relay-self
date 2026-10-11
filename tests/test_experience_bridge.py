"""L Lane L1: deterministic typed/offline evidence-retention-reuse controls.

Source-shaped fixtures are not a physical World or real goal attestation.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relay_self.action import ActionEvent, ActionLifecycle, ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.experience_bridge import (
    CognitiveHint,
    ExperienceRejected,
    ReuseQuery,
    ReuseStatus,
    cheap_tag_baseline,
    qualify_episode,
    retain_observation,
    retrieve_experience,
)
from relay_self.learning import FeedbackDirection
from relay_self.persistent_cognition import (
    DuplicateMemoryIdentity,
    IdentitySpecification,
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
TAGS = ("near_zombie", "night")


def identity() -> PersistentCognition:
    p = Provenance("test-self", "identity")
    return PersistentCognition(IdentitySpecification("test-self", ("remember facts",), p))


def terminal(
    *,
    action_id: str = "action-1",
    session: str = "session-1",
    world_reason: str = "observed_execution",
    unknown: bool = False,
    action_ref: str = "MOVE_BACKWARD",
):
    world = Provenance("fixture-world-only", f"{session}:{action_id}")
    start = ActionLifecycle(
        action_id, "skill-1", "intent-1",
        (ActionEvent(ActionState.PROPOSED, 1, Provenance("fixture", "propose")),),
    )
    issued = start.authorize(
        at_ns=2, provenance=Provenance("fixture", "authorized"), authority="fixture-grant"
    ).issue(at_ns=3, deadline_ns=100, provenance=Provenance("fixture", "issued"))
    action = (issued.mark_unknown(at_ns=4, provenance=world) if unknown
              else issued.record_outcome(at_ns=4, provenance=world))
    outcome = ActionOutcomeInterpretation(
        action_id=action_id, binding_id="binding-1", action_ref=action_ref,
        skill_execution_id="skill-1", intent_id="intent-1", session_id=session,
        source_status="unknown" if unknown else "executed",
        disposition=(ActionOutcomeDisposition.UNKNOWN if unknown
                     else ActionOutcomeDisposition.OUTCOME),
        reason_code=world_reason, world_provenance=world,
        provenance=Provenance("fixture", "s16"),
    )
    return action, outcome


def qualified(*, action_id="action-1", session="session-1",
              reason="observed_execution", unknown=False,
              digest=DIGEST_A, revision=1, feedback=None):
    action, outcome = terminal(
        action_id=action_id, session=session, world_reason=reason, unknown=unknown
    )
    return qualify_episode(
        action, outcome, world_revision=revision,
        evidence_sha256=digest, cue_tags=TAGS, feedback=feedback,
        hypothesis="MOVE_BACKWARD may help" if not unknown else None,
    )


def query(*, session="session-1", revision=1, admitted=frozenset({DIGEST_A}),
          tags=TAGS, lag=0):
    return ReuseQuery(session, revision, tags, admitted, lag)


def stored(*episodes) -> PersistentCognition:
    snapshot = identity()
    for episode in episodes:
        snapshot = retain_observation(
            snapshot, episode, integration_provenance=Provenance("fixture", "retain")
        )
    return snapshot


def test_original_owner_retains_episode_without_learning_or_habit(tmp_path):
    initial = identity()
    q = qualified()
    snapshot = stored(q)
    assert initial.memories == ()
    assert len(snapshot.memories) == 1
    assert q.feedback is None
    assert snapshot.appraisal_dispositions == initial.appraisal_dispositions
    assert snapshot.memories[0].source_provenance == q.episode.source_provenance
    assert "MOVE_BACKWARD may help" in snapshot.memories[0].content
    assert "goal_success" not in snapshot.memories[0].content
    path = tmp_path / "existing-owner.json"
    save_persistent_cognition(path, snapshot)
    assert load_persistent_cognition(path) == snapshot
    assert retrieve_experience(snapshot, query()).status is ReuseStatus.RECALL
    with pytest.raises(DuplicateMemoryIdentity):
        retain_observation(
            snapshot, q, integration_provenance=Provenance("fixture", "retain")
        )


def test_zero_retention_versus_tag_and_qualified_reuse_is_equal_when_simple():
    base = retrieve_experience(identity(), query())
    snapshot = stored(qualified())
    cheap = cheap_tag_baseline(snapshot, query())
    qualified_hint = retrieve_experience(snapshot, query())
    assert base.status is ReuseStatus.UNKNOWN
    assert cheap == qualified_hint
    assert qualified_hint.status is ReuseStatus.RECALL
    assert qualified_hint.observed_action_refs == ("MOVE_BACKWARD",)
    assert qualified_hint.reason == "observation_only_not_goal_or_learning"
    # A read-only source reference is NOT an Action issuer or goal-success label.
    assert isinstance(qualified_hint, CognitiveHint)
    assert len(snapshot.memories) == 1


@pytest.mark.parametrize(("case", "expected"), [
    ({"session": "foreign"}, ReuseStatus.UNKNOWN),
    ({"revision": 0}, ReuseStatus.STALE),
    ({"revision": 3}, ReuseStatus.STALE),
    ({"admitted": frozenset()}, ReuseStatus.UNVERIFIED),
    ({"tags": ("other",)}, ReuseStatus.UNKNOWN),
])
def test_scope_source_revision_and_attested_digest_negatives(case, expected):
    snapshot = stored(qualified())
    assert retrieve_experience(snapshot, query(**case)).status is expected
    assert retrieve_experience(snapshot, query(revision=2, lag=1)).status is ReuseStatus.RECALL


def test_unknown_and_contradiction_do_not_upgrade_into_action_or_learning():
    unknown = stored(qualified(unknown=True))
    hint = retrieve_experience(unknown, query())
    assert hint.status is ReuseStatus.RECONSIDER
    assert hint.observed_action_refs == ()
    contradictory = stored(
        qualified(action_id="one", digest=DIGEST_A, reason="observed_execution"),
        qualified(action_id="two", digest=DIGEST_B, reason="observed_collision"),
    )
    hint = retrieve_experience(
        contradictory, query(admitted=frozenset({DIGEST_A, DIGEST_B}))
    )
    assert hint.status is ReuseStatus.CONTRADICTORY
    assert hint.observed_action_refs == ()


def test_malformed_retained_schema_fail_closed_even_with_valid_other_memory():
    snapshot = stored(qualified())
    bad = Memory(
        "l1:session-1:invalid:1", '{"schema":"L1_SOURCE_EPISODE_V1"}',
        Provenance("untrusted", "bad"), Provenance("fixture", "bad")
    )
    broken = snapshot.retain_memory(bad)
    assert retrieve_experience(broken, query()).status is ReuseStatus.UNKNOWN
    assert retrieve_experience(broken, query()).reason == "invalid_retained_episode"
    legacy = identity().retain_memory(
        Memory("observed:session-1:action-old", json.dumps({
            "type": "S49_OBSERVED_ACTION_OUTCOME",
            "movement_m": 0.627,
            "goal_success_attested": False,
            "learning_feedback_qualified": False,
        }), Provenance("old", "source"), Provenance("old", "integration"))
    )
    assert retrieve_experience(legacy, query()).status is ReuseStatus.UNKNOWN


def test_s17_produced_is_separate_from_memory_and_s10_authority():
    action, outcome = terminal()
    criterion = ActionFeedbackCriterion(
        criterion_id="test-risk-only", target_id="risk_weight",
        required_action_id=action.action_id, required_binding_id=outcome.binding_id,
        required_action_ref=outcome.action_ref, required_action_state=ActionState.OUTCOME,
        required_outcome_disposition=ActionOutcomeDisposition.OUTCOME,
        required_outcome_reason=outcome.reason_code,
        feedback_direction=FeedbackDirection.INCREASE,
        provenance=Provenance("fixture", "criterion"),
    )
    feedback = interpret_action_outcome_as_learning_feedback(
        action, outcome, criterion, provenance=Provenance("fixture", "s17")
    )
    assert feedback.status is LearningFeedbackInterpretationStatus.PRODUCED
    q = qualify_episode(
        action, outcome, world_revision=1, evidence_sha256=DIGEST_A,
        cue_tags=TAGS, feedback=feedback
    )
    assert q.feedback == feedback.feedback
    # No LearningPreferenceState / propose_learning_update / authority or commit here.
    snapshot = stored(q)
    assert "risk_weight" not in snapshot.memories[0].content
    assert retrieve_experience(snapshot, query()).status is ReuseStatus.RECALL
    with pytest.raises(ExperienceRejected, match="lineage"):
        qualify_episode(
            action, outcome, world_revision=1, evidence_sha256=DIGEST_A,
            cue_tags=TAGS, feedback=replace(feedback, action_ref="forged")
        )
    with pytest.raises(ExperienceRejected, match="typed S17"):
        qualify_episode(
            action, outcome, world_revision=1, evidence_sha256=DIGEST_A,
            cue_tags=TAGS, feedback="yes, learn now"
        )


def test_unknown_s17_never_promotes_and_nonterminal_refused():
    action, outcome = terminal(unknown=True)
    criterion = ActionFeedbackCriterion(
        criterion_id="unknown-test", target_id="risk_weight",
        required_action_id=action.action_id, required_binding_id=outcome.binding_id,
        required_action_ref=outcome.action_ref, required_action_state=ActionState.UNKNOWN,
        required_outcome_disposition=ActionOutcomeDisposition.UNKNOWN,
        required_outcome_reason=outcome.reason_code,
        feedback_direction=FeedbackDirection.INCREASE,
        provenance=Provenance("fixture", "criterion"),
    )
    feedback = interpret_action_outcome_as_learning_feedback(
        action, outcome, criterion, provenance=Provenance("fixture", "unknown")
    )
    assert feedback.status is LearningFeedbackInterpretationStatus.PRODUCED
    with pytest.raises(ExperienceRejected, match="non-observed"):
        qualify_episode(
            action, outcome, world_revision=1, evidence_sha256=DIGEST_A,
            cue_tags=TAGS, feedback=feedback
        )
    assert qualified(unknown=True).feedback is None
    with pytest.raises(ExperienceRejected, match="mismatch"):
        qualify_episode(
            action, replace(outcome, action_id="foreign"),
            world_revision=1, evidence_sha256=DIGEST_A, cue_tags=TAGS
        )
    with pytest.raises(ExperienceRejected, match="mismatch"):
        qualify_episode(
            action, replace(outcome, disposition=ActionOutcomeDisposition.OUTCOME),
            world_revision=1, evidence_sha256=DIGEST_A, cue_tags=TAGS
        )


@pytest.mark.parametrize("bad", [
    {"world_revision": -1},
    {"evidence_sha256": "wrong"},
    {"cue_tags": ("night", "near_zombie")},
    {"cue_tags": ("night", "night")},
])
def test_source_validation_fails_closed(bad):
    action, outcome = terminal()
    inputs = dict(world_revision=1, evidence_sha256=DIGEST_A, cue_tags=TAGS)
    inputs.update(bad)
    with pytest.raises(ExperienceRejected):
        qualify_episode(action, outcome, **inputs)


def test_stale_action_owner_is_rejected():
    p = Provenance("fixture", "p")
    stale = ActionLifecycle(
        "old-action", "skill", "intent",
        (ActionEvent(ActionState.PROPOSED, 1, p),),
    )
    authorized = stale.authorize(at_ns=2, provenance=p, authority="grant")
    issued = authorized.issue(at_ns=3, deadline_ns=100, provenance=p)
    final = issued.record_outcome(at_ns=4, provenance=p)
    outcome = ActionOutcomeInterpretation(
        "old-action", "binding", "MOVE", "skill", "intent", "s", "executed",
        ActionOutcomeDisposition.OUTCOME, "observed", p, p
    )
    with pytest.raises(ExperienceRejected, match="current"):
        qualify_episode(
            stale, outcome, world_revision=1, evidence_sha256=DIGEST_A, cue_tags=TAGS
        )
    assert final.is_current_snapshot
