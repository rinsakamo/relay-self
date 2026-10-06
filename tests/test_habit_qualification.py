from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import AttentionCandidate, AttentionCriterion, select_attention
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    BeliefStatus,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.concept import (
    ConceptCriterion,
    ConceptFeature,
    ConceptKey,
    ConceptStatus,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    S11_DESCRIPTOR_SET,
    S11_HABIT_CAPABILITY_SPEC,
    S11_HABIT_CRITERION_DESCRIPTOR,
    S11_HABIT_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s11_capability_plan,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelection,
    HabitSelectionStatus,
    InvalidHabitData,
    select_habit,
)
from relay_self.habit_profile import (
    S11_HABIT_PROFILES,
    HabitProfileId,
    s11_habit_profile,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningData,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.planning import (
    PlanCandidate,
    PlanFeature,
    PlanningCriterion,
    PlanningDirection,
    PlanSelection,
    PlanSelectionStatus,
    select_plan,
)
from relay_self.prediction import (
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s11-habit-qualification", reference=reference)


def hostile_near_cue() -> HabitCue:
    return HabitCue(
        cue_id="cue-zombie-near",
        features=(
            CueFeature("entity_class", "hostile_mob"),
            CueFeature("distance_band", "near"),
        ),
        provenance=provenance("cue:zombie-near"),
    )


def habit_rule(
    habit_id: str,
    *,
    requirements: tuple[CueFeature, ...],
    candidate_ref: str,
    priority: int,
) -> HabitRule:
    return HabitRule(
        habit_id=habit_id,
        cue_requirements=requirements,
        candidate_ref=candidate_ref,
        priority=priority,
        provenance=provenance(f"habit:{habit_id}"),
    )


def repertoire(
    rules: tuple[HabitRule, ...] | None = None,
    *,
    revision: int = 7,
) -> HabitRepertoire:
    if rules is None:
        rules = (
            habit_rule(
                "H1",
                requirements=(
                    CueFeature("entity_class", "hostile_mob"),
                    CueFeature("distance_band", "near"),
                ),
                candidate_ref="MOVE_AWAY",
                priority=10,
            ),
            habit_rule(
                "H2",
                requirements=(
                    CueFeature("entity_class", "edible"),
                    CueFeature("distance_band", "near"),
                ),
                candidate_ref="EAT",
                priority=5,
            ),
        )
    return HabitRepertoire(
        repertoire_id="survival-habits",
        revision=revision,
        rules=rules,
        provenance=provenance("repertoire:survival"),
    )


def plan_selection(
    *,
    wait_score: int = 1,
    move_score: int = 5,
) -> PlanSelection:
    wait = PlanCandidate(
        candidate_id="WAIT",
        outcome_features=(PlanFeature("comparison_score", wait_score),),
        provenance=provenance("plan:wait"),
        action_ref="WAIT",
    )
    move = PlanCandidate(
        candidate_id="MOVE_AWAY",
        outcome_features=(PlanFeature("comparison_score", move_score),),
        provenance=provenance("plan:move-away"),
        action_ref="MOVE_BACKWARD",
    )
    return select_plan(
        (wait, move),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )


def learning_preference() -> LearningPreferenceState:
    return LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("learning:origin"),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s11",
        directives=("habit selection remains non-authoritative",),
        provenance=provenance("identity"),
    )


def memory(memory_id: str) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=f"memory:{memory_id}",
        source_provenance=provenance(f"memory-source:{memory_id}"),
        integration_provenance=provenance(f"memory-integration:{memory_id}"),
    )


def committed_intent() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-s11",
        objective="maintain current objective",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def upstream_objects():
    p = PropositionKey("entity", "zombie-1", "nearby")
    belief = assess_belief(
        (
            BeliefEvidence(
                "E1",
                p,
                EvidenceRelation.SUPPORT,
                provenance("evidence:E1"),
            ),
        ),
        BeliefCriterion("zombie-nearby", p),
    )
    concept_input = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    concept = classify_concept(
        concept_input,
        ConceptCriterion(
            criterion_id="supported-nearby",
            concept=ConceptKey("spatial", "nearby_threat"),
            required_features=(
                ConceptFeature("belief_status", "supported"),
                ConceptFeature("proposition", p.canonical),
            ),
        ),
    )
    prediction = predict_transition(
        PredictionState(
            state_id="threat:0",
            variables=(
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            provenance=provenance("prediction-source"),
        ),
        TransitionRule(
            rule_id="threat-approaches",
            preconditions=(
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            assignments=(StateVariable("threat_state", "immediate"),),
            provenance=provenance("transition-rule"),
        ),
    )
    attention = select_attention(
        (
            AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                provenance("attention:E1"),
                focus_keys=("zombie-1",),
            ),
        ),
        AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    plan = plan_selection(wait_score=8, move_score=3)
    return attention, belief, concept, prediction, plan


def test_package_exports_s11_habit_surface() -> None:
    assert relay_self.CueFeature is CueFeature
    assert relay_self.HabitCue is HabitCue
    assert relay_self.HabitRule is HabitRule
    assert relay_self.HabitRepertoire is HabitRepertoire
    assert relay_self.HabitSelection is HabitSelection
    assert relay_self.HabitSelectionStatus is HabitSelectionStatus
    assert relay_self.select_habit is select_habit
    assert relay_self.HabitProfileId is HabitProfileId
    assert relay_self.S11_HABIT_PROFILES is S11_HABIT_PROFILES
    assert relay_self.s11_habit_profile is s11_habit_profile


def test_s11_profiles_are_exactly_habit_and_plan_habit() -> None:
    assert [profile.profile_id for profile in S11_HABIT_PROFILES] == [
        HabitProfileId.HABIT,
        HabitProfileId.PLAN_HABIT,
    ]
    assert s11_habit_profile(
        HabitProfileId.HABIT
    ).enabled_ids == frozenset({"HABIT"})
    assert s11_habit_profile(
        HabitProfileId.PLAN_HABIT
    ).enabled_ids == frozenset({"PLAN", "HABIT"})


def test_habit_descriptor_reads_narrow_retained_scope_without_hidden_state() -> None:
    assert S11_HABIT_CAPABILITY_SPEC.state_scopes == (
        "owner_local.habit_repertoire",
    )
    assert S11_HABIT_CAPABILITY_SPEC.dependencies == ()
    assert S11_HABIT_OPERATOR_DESCRIPTOR.operator_id == "habit.select"
    assert S11_HABIT_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S11_HABIT_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert (
        S11_HABIT_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.habit.select_habit"
    )
    assert (
        S11_HABIT_CRITERION_DESCRIPTOR.criterion_id
        == "habit.explicit_priority_orientation"
    )
    assert (
        S11_HABIT_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert all(
        item.kind is CriterionKind.CONTRACT_GUARD
        for item in S2_DESCRIPTOR_SET.criteria
    )


def test_unique_highest_priority_matching_rule_is_selected() -> None:
    owner = repertoire()
    cue = hostile_near_cue()
    selection = select_habit(owner, cue)
    assert selection.status is HabitSelectionStatus.SELECTED
    assert selection.selected_rule is owner.rules[0]
    assert selection.selected_candidate_ref == "MOVE_AWAY"
    assert selection.matching_rules == (owner.rules[0],)
    assert selection.repertoire is owner
    assert selection.cue is cue


def test_no_matching_rule_is_explicit_no_match() -> None:
    cue = HabitCue(
        cue_id="cue-tree",
        features=(
            CueFeature("entity_class", "tree"),
            CueFeature("distance_band", "near"),
        ),
        provenance=provenance("cue:tree"),
    )
    selection = select_habit(repertoire(), cue)
    assert selection.status is HabitSelectionStatus.NO_MATCH
    assert selection.selected_rule is None
    assert selection.selected_candidate_ref is None
    assert selection.matching_rules == ()


def test_missing_required_cue_feature_is_non_match() -> None:
    cue = HabitCue(
        cue_id="cue-partial",
        features=(CueFeature("entity_class", "hostile_mob"),),
        provenance=provenance("cue:partial"),
    )
    selection = select_habit(repertoire(), cue)
    assert selection.status is HabitSelectionStatus.NO_MATCH


def test_equal_highest_priority_is_tied_without_order_fallback() -> None:
    first = habit_rule(
        "H1",
        requirements=(CueFeature("entity_class", "hostile_mob"),),
        candidate_ref="MOVE_AWAY",
        priority=10,
    )
    second = habit_rule(
        "H2",
        requirements=(CueFeature("distance_band", "near"),),
        candidate_ref="LOOK_AT_THREAT",
        priority=10,
    )
    selection = select_habit(
        repertoire((first, second)),
        hostile_near_cue(),
    )
    assert selection.status is HabitSelectionStatus.TIED
    assert selection.selected_rule is None
    assert selection.selected_candidate_ref is None
    assert selection.matching_rules == (first, second)


def test_lower_priority_matching_rule_loses() -> None:
    high = habit_rule(
        "H-high",
        requirements=(CueFeature("entity_class", "hostile_mob"),),
        candidate_ref="MOVE_AWAY",
        priority=10,
    )
    low = habit_rule(
        "H-low",
        requirements=(CueFeature("distance_band", "near"),),
        candidate_ref="LOOK_AT_THREAT",
        priority=5,
    )
    selection = select_habit(
        repertoire((low, high)),
        hostile_near_cue(),
    )
    assert selection.status is HabitSelectionStatus.SELECTED
    assert selection.selected_rule is high


def test_same_input_is_deterministic_immutable_and_read_only() -> None:
    owner = repertoire()
    cue = hostile_near_cue()
    original_rules = owner.rules
    original_revision = owner.revision
    first = select_habit(owner, cue)
    second = select_habit(owner, cue)
    assert first == second
    assert owner.rules == original_rules
    assert owner.revision == original_revision
    with pytest.raises(FrozenInstanceError):
        owner.revision = 8  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.status = HabitSelectionStatus.NO_MATCH  # type: ignore[misc]


def test_empty_repertoire_returns_no_match_without_revision_change() -> None:
    owner = repertoire(())
    selection = select_habit(owner, hostile_near_cue())
    assert selection.status is HabitSelectionStatus.NO_MATCH
    assert owner.revision == 7


def test_validation_fail_closed() -> None:
    with pytest.raises(InvalidHabitData, match="structured identifier"):
        HabitRepertoire(
            repertoire_id="bad repertoire",
            revision=0,
            rules=(),
            provenance=provenance("bad-repertoire"),
        )

    duplicate = habit_rule(
        "H1",
        requirements=(CueFeature("x", 1),),
        candidate_ref="WAIT",
        priority=1,
    )
    with pytest.raises(InvalidHabitData, match="habit_id values must be unique"):
        repertoire((duplicate, duplicate))

    with pytest.raises(InvalidHabitData, match="structured identifier"):
        habit_rule(
            "bad habit",
            requirements=(CueFeature("x", 1),),
            candidate_ref="WAIT",
            priority=1,
        )

    with pytest.raises(InvalidHabitData, match="keys must be unique"):
        habit_rule(
            "H-duplicate",
            requirements=(CueFeature("x", 1), CueFeature("x", 2)),
            candidate_ref="WAIT",
            priority=1,
        )

    with pytest.raises(InvalidHabitData, match="structured identifier"):
        habit_rule(
            "H-bad-ref",
            requirements=(CueFeature("x", 1),),
            candidate_ref="MOVE AWAY",
            priority=1,
        )

    with pytest.raises(InvalidHabitData, match="non-empty string"):
        HabitRule(
            habit_id="H-mutable-ref",
            cue_requirements=(CueFeature("x", 1),),
            candidate_ref=["MOVE_AWAY"],  # type: ignore[arg-type]
            priority=1,
            provenance=provenance("mutable-ref"),
        )

    with pytest.raises(InvalidHabitData, match="non-negative integer"):
        habit_rule(
            "H-bad-priority",
            requirements=(CueFeature("x", 1),),
            candidate_ref="WAIT",
            priority=-1,
        )

    with pytest.raises(InvalidHabitData, match="structured identifier"):
        HabitCue(
            cue_id="bad cue",
            features=(CueFeature("x", 1),),
            provenance=provenance("bad-cue"),
        )

    with pytest.raises(InvalidHabitData, match="keys must be unique"):
        HabitCue(
            cue_id="duplicate-cue",
            features=(CueFeature("x", 1), CueFeature("x", 2)),
            provenance=provenance("duplicate-cue"),
        )

    with pytest.raises(InvalidHabitData, match="cue feature value"):
        CueFeature("x", ["mutable"])  # type: ignore[arg-type]


def test_missing_repertoire_and_provider_text_fail_closed() -> None:
    cue = hostile_near_cue()
    generated_rule = ProviderExpression(
        text="Whenever you see a zombie, run away.",
        provenance=provenance("provider-rule"),
    )
    generated_selection = ProviderExpression(
        text="Run away now.",
        provenance=provenance("provider-selection"),
    )
    with pytest.raises(InvalidHabitData, match="HabitRepertoire"):
        select_habit(None, cue)  # type: ignore[arg-type]
    with pytest.raises(InvalidHabitData, match="HabitRepertoire"):
        select_habit(generated_rule, cue)  # type: ignore[arg-type]
    with pytest.raises(InvalidHabitData, match="HabitCue"):
        select_habit(repertoire(), generated_selection)  # type: ignore[arg-type]


def test_habit_selection_is_not_learning_feedback() -> None:
    owner = repertoire()
    selection = select_habit(owner, hostile_near_cue())
    learned = learning_preference()
    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            selection,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-preference-step",
                version=1,
                step=1,
            ),
        )
    assert owner.revision == 7
    assert learned.value == 3
    assert learned.revision == 0


def test_habit_on_executes_real_selection_with_zero_cognition() -> None:
    box: dict[str, object] = {}
    owner = repertoire()

    def choose_habit() -> None:
        box["habit"] = select_habit(owner, hostile_near_cue())

    binding = EpochBinding("habit-1", "habit.select", choose_habit)
    epoch = compile_epoch_plan(
        s11_habit_profile(HabitProfileId.HABIT).plan(),
        S11_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("habit-1", "habit.select", "explicit-cue"),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-habit"),
    )
    selection = box["habit"]
    assert isinstance(selection, HabitSelection)
    assert selection.selected_candidate_ref == "MOVE_AWAY"
    assert owner.revision == 7
    assert result.executed_work_ids == ("habit-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_plan_on_habit_off_preserves_repertoire() -> None:
    owner = repertoire()
    box: dict[str, object] = {}

    def choose_plan() -> None:
        box["plan"] = plan_selection(wait_score=8, move_score=3)

    binding = EpochBinding("plan-1", "plan.select", choose_plan)
    epoch = compile_epoch_plan(
        s11_capability_plan(enabled_ids=frozenset({"PLAN"})),
        S11_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "explicit-plan-input"),
            EpochWorkItem("habit-1", "habit.select", "habit-disabled"),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-habit-off"),
    )
    assert isinstance(box["plan"], PlanSelection)
    assert result.executed_work_ids == ("plan-1",)
    assert result.suppressed_work_ids == ("habit-1",)
    assert "habit" not in box
    assert owner.revision == 7
    assert result.cognition_requested is False


def test_habit_on_plan_off_is_independent() -> None:
    box: dict[str, object] = {}

    def choose_habit() -> None:
        box["habit"] = select_habit(repertoire(), hostile_near_cue())

    binding = EpochBinding("habit-1", "habit.select", choose_habit)
    epoch = compile_epoch_plan(
        s11_capability_plan(enabled_ids=frozenset({"HABIT"})),
        S11_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "plan-disabled"),
            EpochWorkItem("habit-1", "habit.select", "explicit-cue"),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-plan-off"),
    )
    assert box["habit"].selected_candidate_ref == "MOVE_AWAY"
    assert result.suppressed_work_ids == ("plan-1",)
    assert result.executed_work_ids == ("habit-1",)
    assert "plan" not in box
    assert result.cognition_requested is False


def test_plan_and_habit_are_independent_when_outputs_disagree() -> None:
    box: dict[str, object] = {}

    def choose_plan() -> None:
        box["plan"] = plan_selection(wait_score=1, move_score=5)

    def choose_habit() -> None:
        box["habit"] = select_habit(repertoire(), hostile_near_cue())

    bindings = (
        EpochBinding("plan-1", "plan.select", choose_plan),
        EpochBinding("habit-1", "habit.select", choose_habit),
    )
    epoch = compile_epoch_plan(
        s11_habit_profile(HabitProfileId.PLAN_HABIT).plan(),
        S11_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "transient-plan-input"),
            EpochWorkItem("habit-1", "habit.select", "retained-habit-input"),
        ),
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-plan-habit"),
    )
    plan = box["plan"]
    habit = box["habit"]
    assert isinstance(plan, PlanSelection)
    assert isinstance(habit, HabitSelection)
    assert plan.selected is not None
    assert plan.selected.candidate_id == "WAIT"
    assert habit.selected_candidate_ref == "MOVE_AWAY"
    assert result.executed_work_ids == ("plan-1", "habit-1")
    assert result.cognition_requested is False


def test_no_match_does_not_fallback_to_plan() -> None:
    box: dict[str, object] = {}

    def choose_habit() -> None:
        box["habit"] = select_habit(repertoire(()), hostile_near_cue())

    binding = EpochBinding("habit-1", "habit.select", choose_habit)
    epoch = compile_epoch_plan(
        s11_capability_plan(enabled_ids=frozenset({"HABIT"})),
        S11_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("habit-1", "habit.select", "empty-repertoire"),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-no-match"),
    )
    assert box["habit"].status is HabitSelectionStatus.NO_MATCH
    assert "plan" not in box
    assert result.cognition_requested is False


def test_habit_selection_does_not_mutate_other_authorities() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s11",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    proposed_action = ActionLifecycle.propose(
        "action-proposed",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action-proposed"),
    )
    authorized_action = ActionLifecycle.propose(
        "action-authorized",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=4,
        provenance=provenance("action-authorized-proposed"),
    ).authorize(
        at_ns=5,
        provenance=provenance("action-authorized"),
        authority="action-authority",
    )
    issued_action = ActionLifecycle.propose(
        "action-issued",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=6,
        provenance=provenance("action-issued-proposed"),
    ).authorize(
        at_ns=7,
        provenance=provenance("action-issued-authorized"),
        authority="action-authority",
    ).issue(
        at_ns=8,
        deadline_ns=100,
        provenance=provenance("action-issued"),
    )
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )
    attention, belief, concept, prediction, plan = upstream_objects()
    learned = learning_preference()
    owner = repertoire()
    before = (
        cognition.memories,
        intent_owner.events,
        skill.events,
        proposed_action.events,
        authorized_action.events,
        issued_action.events,
        attention,
        belief,
        concept,
        prediction,
        plan,
        learned,
        owner.rules,
        owner.revision,
    )

    selection = select_habit(owner, hostile_near_cue())

    assert selection.selected_candidate_ref == "MOVE_AWAY"
    assert cognition.memories == before[0]
    assert intent_owner.events == before[1]
    assert skill.events == before[2]
    assert skill.state is SkillState.STARTED
    assert proposed_action.events == before[3]
    assert proposed_action.state is ActionState.PROPOSED
    assert authorized_action.events == before[4]
    assert authorized_action.state is ActionState.AUTHORIZED
    assert issued_action.events == before[5]
    assert issued_action.state is ActionState.ISSUED
    assert attention == before[6]
    assert belief == before[7]
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept == before[8]
    assert concept.status is ConceptStatus.MATCHED
    assert prediction == before[9]
    assert prediction.status is PredictionStatus.PREDICTED
    assert plan == before[10]
    assert learned == before[11]
    assert owner.rules == before[12]
    assert owner.revision == before[13]


def test_explicit_lrn_update_does_not_change_habit_repertoire() -> None:
    owner = repertoire()
    cue = hostile_near_cue()
    before_selection = select_habit(owner, cue)
    learned = learning_preference()
    signal = LearningFeedback(
        feedback_id="fb-explicit",
        target_id="risk_weight",
        direction=FeedbackDirection.INCREASE,
        provenance=provenance("learning-feedback"),
        consequence_ref="consequence:explicit",
    )
    proposal = propose_learning_update(
        learned,
        signal,
        LearningUpdateRule(
            rule_id="bounded-preference-step",
            version=1,
            step=1,
        ),
    )
    result = commit_learning_update(
        learned,
        proposal,
        LearningUpdateAuthority(
            authority_id="learning-owner-authority",
            target_id="risk_weight",
            provenance=provenance("learning-authority"),
        ),
        provenance=provenance("learning-commit"),
    )
    after_selection = select_habit(owner, cue)
    assert result.new_state.value == 4
    assert result.new_state.revision == 1
    assert owner.revision == 7
    assert before_selection == after_selection
