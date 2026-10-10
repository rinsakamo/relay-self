"""B21 native frozen S17/S10 API witness cannot mint a C15/S11 production grant."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import empty_repertoire
from experiments.ac_b_b21_source_boundary import (
    BLOCKED,
    C15_FROZEN_DRAFT_HEAD,
    MISSING,
    NO_AUTHENTICATED_LINK,
    S17_LOCAL_CLASS,
    InvalidB21Chain,
    StaticC15Description,
    assess_production_s11_boundary,
    validate_typed_s17_s10,
)
from relay_self.action_feedback import (
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.learning import (
    InvalidLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from test_action_feedback_qualification import (
    executed_closed_chain,
    feedback_criterion,
    learning_authority,
    learning_rule,
    learning_state,
)


def sample_chain():
    """Original S17 fake Mineflayer, real S10 owner call, no S11 mutation."""
    *_, result, closed = executed_closed_chain()
    criterion = feedback_criterion()
    converted = interpret_action_outcome_as_learning_feedback(
        closed, result, criterion,
        provenance=Provenance("b21-test", "real-s17-api-interpreter"),
    )
    assert converted.status is LearningFeedbackInterpretationStatus.PRODUCED
    state = learning_state()
    proposal = propose_learning_update(
        state, converted.feedback, learning_rule(),
    )
    committed = commit_learning_update(
        state, proposal, learning_authority(),
        provenance=Provenance("b21-test", "real-native-s10-commit"),
    )
    return closed, result, converted, committed, criterion


def endpoint(closed, outcome, *, status="GOAL_REGION_OBSERVED"):
    return StaticC15Description(
        source_draft_head=C15_FROZEN_DRAFT_HEAD,
        status=status, session_id=outcome.session_id,
        start_action_id=closed.action_id,
        stop_action_id=f"{closed.action_id}-clear-controls",
        evidence=("claimed-probe", "claimed-start", "claimed-end"),
    )


def report(*, static=True, status="GOAL_REGION_OBSERVED"):
    chain = sample_chain()
    owner = empty_repertoire(label="b21-read-only-owner")
    original_revision = owner.revision
    r = assess_production_s11_boundary(
        *chain, owner,
        c15_static=endpoint(chain[0], chain[1], status=status) if static else None,
    )
    assert owner.revision == original_revision == 0
    assert owner.rules == ()
    return chain, owner, r


def test_actual_s17_to_s10_typed_fixture_and_separate_s11_gate():
    chain, owner, r = report()
    committed = chain[3]
    assert committed.previous_state.revision == 0
    assert committed.previous_state.value == 3
    assert committed.new_state.revision == 1
    assert committed.new_state.value == 4
    assert r.typed_local_chain.terminal_classification == S17_LOCAL_CLASS
    assert r.typed_local_chain.feedback_id == chain[2].feedback.feedback_id
    assert not r.typed_local_chain.physical_source_verified
    assert not r.typed_local_chain.task_goal_verified
    assert not r.typed_local_chain.authorizes_s11
    assert r.c15_static_description_seen
    assert r.c15_matches_claimed_strings is True
    assert r.static_endpoint_status == "GOAL_REGION_OBSERVED"
    assert r.real_c15_endpoint_signed_goal is False
    assert r.real_s17_source_attested is False
    assert r.production_s11_owner_authorized is False
    assert r.production_habit_acquired is False
    assert r.owner_revision_unchanged == owner.revision == 0
    assert r.reason == BLOCKED
    assert r.missing_witnesses == MISSING
    assert NO_AUTHENTICATED_LINK in (
        "NO_SHARED_AUTHENTICATED_PHYSICAL_ACTION_WITNESS",
    )


@pytest.mark.parametrize(
    "status",
    ["GOAL_REGION_OBSERVED", "ALTERNATIVE_REGION_OBSERVED", "UNDETERMINED"],
)
def test_all_static_c15_statuses_never_authorize_product_s11(status):
    _, _, r = report(status=status)
    assert r.c15_matches_claimed_strings is True
    assert r.static_endpoint_status == status
    assert r.reason == BLOCKED
    assert not r.production_s11_owner_authorized
    assert not r.production_habit_acquired


def test_no_c15_or_cross_session_static_c15_both_block():
    chain, owner, no_c15 = report(static=False)
    assert no_c15.static_endpoint_status is None
    assert no_c15.c15_matches_claimed_strings is False
    assert no_c15.reason == BLOCKED
    other = replace(
        endpoint(chain[0], chain[1]),
        session_id="another-session",
    )
    r = assess_production_s11_boundary(
        *chain, owner, c15_static=other,
    )
    assert not r.c15_matches_claimed_strings
    assert not r.production_habit_acquired


def test_swapped_action_and_intent_binding_rejected():
    chain = sample_chain()
    action, outcome, interpretation, committed, criterion = chain
    for bad_outcome in (
        replace(outcome, action_id="another-action"),
        replace(outcome, skill_execution_id="different-skill"),
        replace(outcome, binding_id="unissued-binding"),
        replace(outcome, session_id="different-fake-session"),
        replace(outcome, intent_id="different-intent"),
    ):
        with pytest.raises(InvalidB21Chain):
            validate_typed_s17_s10(
                action, bad_outcome, interpretation, committed, criterion,
            )
    with pytest.raises(InvalidB21Chain):
        validate_typed_s17_s10(
            action, outcome, interpretation, committed,
            feedback_criterion(direction=criterion.feedback_direction,
                               binding_id="wrong-binding"),
        )


def test_terminal_unknown_and_unavailable_cannot_be_called_executed():
    action, outcome, converted, commit, criterion = sample_chain()
    bad = replace(
        outcome, disposition=ActionOutcomeDisposition.UNAVAILABLE,
    )
    with pytest.raises(InvalidB21Chain, match="terminal"):
        validate_typed_s17_s10(
            action, bad, converted, commit, criterion,
        )
    bad = replace(
        outcome, disposition=ActionOutcomeDisposition.UNKNOWN,
    )
    with pytest.raises(InvalidB21Chain, match="terminal"):
        validate_typed_s17_s10(
            action, bad, converted, commit, criterion,
        )
    with pytest.raises(InvalidB21Chain, match="five actual"):
        validate_typed_s17_s10(
            action, None, converted, commit, criterion,
        )


def test_feedback_clones_equal_text_do_not_bind_original_s10_event():
    action, outcome, converted, committed, criterion = sample_chain()
    forged = replace(
        converted, feedback=replace(converted.feedback),
    )
    assert forged.feedback == converted.feedback
    assert forged.feedback is not converted.feedback
    with pytest.raises(InvalidB21Chain, match="original feedback"):
        validate_typed_s17_s10(
            action, outcome, forged, committed, criterion,
        )
    forged = replace(
        converted, action_outcome_provenance=Provenance(
            "forged", "same-looking-origin"
        ),
    )
    with pytest.raises(InvalidB21Chain, match="interpretation"):
        validate_typed_s17_s10(
            action, outcome, forged, committed, criterion,
        )


def test_malformed_owner_records_and_commits_fail_closed():
    action, outcome, converted, committed, criterion = sample_chain()
    tampered_commit = replace(
        committed, record=replace(
            committed.record, authority_id="other-owner",
        ),
    )
    with pytest.raises(InvalidB21Chain, match="native S10"):
        validate_typed_s17_s10(
            action, outcome, converted, tampered_commit, criterion,
        )
    with pytest.raises(InvalidB21Chain, match="five actual"):
        validate_typed_s17_s10(
            action, outcome, converted, None, criterion,
        )


def test_real_native_s10_denied_update_does_not_become_s11():
    action, outcome, converted, committed, criterion = sample_chain()
    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            committed.previous_state, committed.proposal,
            learning_authority(granted=False),
            provenance=Provenance("b21-test", "denied"),
        )
    assert validate_typed_s17_s10(
        action, outcome, converted, committed, criterion,
    ).new_revision == 1


@pytest.mark.parametrize("field,invalid", [
    ("source_draft_head", "f" * 40),
    ("status", "SIGNED_GOAL_SUCCEEDED"),
    ("session_id", ""),
    ("start_action_id", ""),
    ("stop_action_id", ""),
    ("live_qualification", "QUALIFIED"),
    ("signed_action_label", "SIGNED_GOAL"),
    ("evidence", ["not-original-tuple"]),
])
def test_wrong_c15_fake_product_authority_fields_denied(field, invalid):
    action, outcome, *_ = sample_chain()
    described = endpoint(action, outcome)
    with pytest.raises(InvalidB21Chain, match="C15 static"):
        replace(described, **{field: invalid})


def test_c15_positive_matching_action_strings_does_not_issue_any_rule():
    chain = sample_chain()
    owner = empty_repertoire(label="b21-original-empty")
    forged = endpoint(chain[0], chain[1])
    for _ in range(2):
        r = assess_production_s11_boundary(
            *chain, owner, c15_static=forged,
        )
        assert r.c15_matches_claimed_strings
        assert r.reason == BLOCKED
        assert r.owner_revision_unchanged == 0
        assert owner.rules == ()
    assert r.missing_witnesses[0].startswith("LIVE_S16_S17_")


def test_no_arbitrary_text_can_be_considered_real_c15_witness():
    chain = sample_chain()
    with pytest.raises(InvalidB21Chain, match="typed static"):
        assess_production_s11_boundary(
            *chain, empty_repertoire(), c15_static={
                "status": "GOAL_REGION_OBSERVED",
                "session_id": chain[1].session_id,
                "action_id": chain[0].action_id,
                "granted": True,
            },
        )
