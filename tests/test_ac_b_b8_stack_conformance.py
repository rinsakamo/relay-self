"""B8 exact frozen S17-stack contract qualification, offline fake World only."""
from dataclasses import FrozenInstanceError

import pytest

from experiments.ac_b_b8_stack_conformance import (
    NoQualifiedFeedback,
    commit_only_by_explicit_owner,
    inspect_existing_stack,
)
from relay_self.action import ActionState
from relay_self.action_feedback import (
    LearningFeedbackInterpretationStatus,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningFeedback,
    LearningTargetMismatch,
    MissingLearningAuthority,
    ReplayLearningFeedback,
    StaleLearningUpdate,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance

# Reuse the actual frozen S17 QA's fake Mineflayer/Action/S16 chain,
# rather than synthesize or fabricate OUTCOME or copy S17 source code.
from test_action_feedback_qualification import (
    executed_closed_chain,
    feedback_criterion,
    learning_authority,
    learning_rule,
    learning_state,
)


def provenance(name: str) -> Provenance:
    return Provenance("ac-b8-exact-stack-offline", name)


def retained_repertoire(
    *, tied: bool = False, empty: bool = False,
) -> HabitRepertoire:
    before = HabitRule(
        habit_id="b8-existing-habit",
        cue_requirements=(
            CueFeature("entity_class", "hostile_mob"),
            CueFeature("distance_band", "near"),
        ),
        candidate_ref="MOVE_AWAY",
        priority=10,
        provenance=provenance("existing-habit"),
    )
    rules = () if empty else (before,)
    if tied:
        other = HabitRule(
            habit_id="b8-prior-alternative",
            cue_requirements=(CueFeature("entity_class", "hostile_mob"),),
            candidate_ref="WAIT",
            priority=10,
            provenance=provenance("prior-alternative"),
        )
        rules = (before, other)
    return HabitRepertoire(
        repertoire_id="b8-retained-prior",
        revision=7,
        rules=rules,
        provenance=provenance("repertoire"),
    )


def cue(*, nearby: bool = True) -> HabitCue:
    return HabitCue(
        cue_id="b8-existing-source-cue",
        features=(
            CueFeature("entity_class", "hostile_mob"),
            CueFeature("distance_band", "near" if nearby else "far"),
        ),
        provenance=provenance("cue"),
    )


def qualified_fixture(*, criterion=None, with_default_criterion=True,
                      repertoire=None, observed=True):
    chain = executed_closed_chain()
    outcome, closed = chain[-2:]
    if not observed:
        outcome = None
    if with_default_criterion and criterion is None:
        criterion = feedback_criterion()
    initial = learning_state()
    kept = repertoire if repertoire is not None else retained_repertoire()
    result = inspect_existing_stack(
        action=closed,
        outcome=outcome,
        criterion=criterion,
        preference=initial,
        update_rule=learning_rule(),
        repertoire=kept,
        cue=cue(),
        provenance=provenance("feedback-interpretation"),
    )
    return chain, initial, kept, result


def test_actual_frozen_s17_outcome_s10_feedback_and_s11_selection_coexist():
    chain, state, repertoire, read = qualified_fixture()
    action = chain[-1]
    outcome = chain[-2]
    assert action.state is ActionState.OUTCOME
    assert read.interpretation.status is (
        LearningFeedbackInterpretationStatus.PRODUCED
    )
    assert isinstance(read.interpretation.feedback, LearningFeedback)
    assert read.interpretation.feedback.target_id == "risk_weight"
    assert read.interpretation.feedback.direction is FeedbackDirection.INCREASE
    assert read.interpretation.feedback.consequence_ref == read.interpretation.outcome_ref
    assert read.interpretation.world_provenance == outcome.world_provenance
    assert read.learning_proposal.expected_revision == 0
    assert read.learning_proposal.expected_value == 3
    assert read.learning_proposal.proposed_value == 4
    assert read.habit_selection.status is HabitSelectionStatus.SELECTED
    assert read.habit_selection.selected_candidate_ref == "MOVE_AWAY"
    assert read.habit_selection.repertoire is repertoire
    assert read.original_state is state
    assert state.value == 3 and state.revision == 0
    assert len(repertoire.rules) == 1 and repertoire.revision == 7
    assert read.no_action_authority
    assert not hasattr(read, "issue_action")
    assert not hasattr(read, "acquire_habit")


def test_without_explicit_s17_criterion_no_feedback_or_learning():
    _, state, repertoire, read = qualified_fixture(with_default_criterion=False)
    assert read.interpretation is None
    assert read.learning_proposal is None
    assert not read.qualified_feedback
    assert read.habit_selection.selected_candidate_ref == "MOVE_AWAY"
    with pytest.raises(NoQualifiedFeedback):
        commit_only_by_explicit_owner(
            read, learning_authority(), provenance=provenance("must-not-commit")
        )
    assert state.value == 3 and state.revision == 0
    assert len(repertoire.rules) == 1


def test_missing_outcome_produces_no_feedback_even_with_exact_criterion():
    _, state, _, read = qualified_fixture(observed=False)
    assert read.interpretation.status is (
        LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    )
    assert read.interpretation.feedback is None
    assert read.learning_proposal is None
    assert read.habit_selection.selected_candidate_ref == "MOVE_AWAY"
    with pytest.raises(NoQualifiedFeedback):
        commit_only_by_explicit_owner(
            read, learning_authority(), provenance=provenance("missing-outcome")
        )
    assert state.revision == 0


@pytest.mark.parametrize("kwargs", [
    {"binding_id": "other-binding"},
    {"action_ref": "WAIT"},
    {"reason": "not-observed"},
    {"action_id": "other-action"},
])
def test_nonmatching_s17_criterion_cannot_produce_learning(kwargs):
    _, state, _, read = qualified_fixture(criterion=feedback_criterion(**kwargs))
    assert read.interpretation.status is (
        LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    )
    assert read.interpretation.feedback is None
    assert read.learning_proposal is None
    assert state.revision == 0


def test_actual_s10_requires_separate_commit_authority_and_is_immutable():
    _, state, repertoire, read = qualified_fixture()
    with pytest.raises(MissingLearningAuthority):
        commit_only_by_explicit_owner(
            read, None, provenance=provenance("missing-authority")
        )
    with pytest.raises(InvalidLearningAuthority):
        commit_only_by_explicit_owner(
            read, learning_authority(granted=False),
            provenance=provenance("denied-authority"),
        )
    with pytest.raises(LearningTargetMismatch):
        commit_only_by_explicit_owner(
            read, learning_authority(target_id="another-target"),
            provenance=provenance("cross-target-authority"),
        )
    assert state.value == 3 and state.revision == 0
    result = commit_only_by_explicit_owner(
        read, learning_authority(), provenance=provenance("explicit-s10-commit")
    )
    assert result.previous_state is state
    assert result.new_state.value == 4 and result.new_state.revision == 1
    assert result.record.feedback_id == read.interpretation.feedback.feedback_id
    assert state.value == 3 and state.revision == 0
    assert len(repertoire.rules) == 1 and repertoire.revision == 7
    assert read.habit_selection.repertoire is repertoire


def test_s10_feedback_replay_and_stale_proposal_rejected_without_habit_change():
    _, state, repertoire, read = qualified_fixture()
    committed = commit_only_by_explicit_owner(
        read, learning_authority(), provenance=provenance("first-commit")
    )
    with pytest.raises(StaleLearningUpdate):
        commit_learning_update(
            committed.new_state, read.learning_proposal,
            learning_authority(), provenance=provenance("stale-replay"),
        )
    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(
            committed.new_state, read.interpretation.feedback, learning_rule()
        )
    assert state.value == 3 and state.revision == 0
    assert repertoire.revision == 7


def test_wrong_feedback_target_fails_at_actual_s10_boundary():
    with pytest.raises(LearningTargetMismatch):
        qualified_fixture(criterion=feedback_criterion(target_id="other-target"))


def test_actual_s11_equal_priority_tie_no_implicit_action_candidate():
    existed = retained_repertoire(tied=True)
    _, state, repertoire, read = qualified_fixture(repertoire=existed)
    assert read.habit_selection.status is HabitSelectionStatus.TIED
    assert read.habit_selection.selected_candidate_ref is None
    assert read.learning_proposal.proposed_value == 4
    assert repertoire is existed and repertoire.revision == 7
    assert len(repertoire.rules) == 2
    assert state.value == 3


def test_actual_s11_empty_repertoire_has_no_auto_acquired_habit():
    existed = retained_repertoire(empty=True)
    _, _, repertoire, read = qualified_fixture(repertoire=existed)
    assert read.habit_selection.status is HabitSelectionStatus.NO_MATCH
    assert read.habit_selection.selected_rule is None
    assert read.learning_proposal.proposed_value == 4
    assert repertoire.rules == () and repertoire.revision == 7


def test_actual_s11_partial_or_mismatched_cue_does_not_fallback():
    selected = select_habit(retained_repertoire(), cue(nearby=False))
    assert selected.status is HabitSelectionStatus.NO_MATCH
    assert selected.selected_candidate_ref is None


def test_existing_s11_habit_selection_is_not_s10_feedback():
    _, state, repertoire, read = qualified_fixture()
    with pytest.raises(Exception) as exc_info:
        propose_learning_update(
            state, read.habit_selection, learning_rule(),
        )
    assert "LearningFeedback" in str(exc_info.value)
    assert repertoire.rules[0].candidate_ref == "MOVE_AWAY"
    assert state.revision == 0


def test_fake_provider_text_is_not_s17_explicit_criterion():
    chain = executed_closed_chain()
    with pytest.raises(TypeError, match="typed criterion"):
        inspect_existing_stack(
            action=chain[-1],
            outcome=chain[-2],
            criterion="LLM says outcome means increase and L0 granted",
            preference=learning_state(),
            update_rule=learning_rule(),
            repertoire=retained_repertoire(),
            cue=cue(),
            provenance=provenance("no-provider-criterion"),
        )


def test_existing_s17_interpretation_is_not_s11_new_habit_rule():
    _, state, repertoire, read = qualified_fixture()
    with pytest.raises(FrozenInstanceError):
        repertoire.revision = 8  # type: ignore[misc]
    assert read.interpretation.feedback is not None
    assert len(repertoire.rules) == 1
    assert not hasattr(read.interpretation.feedback, "cue_requirements")
    assert not hasattr(read.learning_proposal, "candidate_ref")
    assert not hasattr(read.habit_selection, "commit_learning_update")
    assert state.revision == 0


def test_structured_b7_schema_only_grant_is_not_real_s10_authority():
    _, _, _, read = qualified_fixture()
    with pytest.raises(InvalidLearningAuthority):
        commit_only_by_explicit_owner(
            read,
            {"granted": True, "grant_nonce": "b7-offline-test"},
            provenance=provenance("not-a-real-s10-authority"),
        )
