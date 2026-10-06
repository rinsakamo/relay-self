from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    AttentionSelection,
    AttentionSelectionUnavailable,
    require_attention_selection,
    select_attention,
)
from relay_self.belief import (
    BeliefAssessment,
    BeliefCriterion,
    BeliefEvidence,
    BeliefStatus,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.concept import (
    ConceptCandidate,
    ConceptCriterion,
    ConceptFeature,
    ConceptKey,
    ConceptRepresentation,
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
    S9_DESCRIPTOR_SET,
    S9_PLAN_CAPABILITY_SPEC,
    S9_PLAN_CRITERION_DESCRIPTOR,
    S9_PLAN_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s9_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.planning import (
    InvalidPlanningData,
    PlanCandidate,
    PlanFeature,
    PlanSelection,
    PlanSelectionStatus,
    PlanSourceUnavailable,
    PlanningCriterion,
    PlanningDirection,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.planning_profile import (
    S9_PLANNING_PROFILES,
    PlanningProfileId,
    s9_planning_profile,
)
from relay_self.prediction import (
    PredictionResult,
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
    prediction_state_from_concept,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s9-planning-qualification", reference=reference)


def candidate(
    candidate_id: str,
    score: int | None,
    *,
    action_ref: str | None = None,
) -> PlanCandidate:
    features = (
        ()
        if score is None
        else (PlanFeature("comparison_score", score),)
    )
    return PlanCandidate(
        candidate_id=candidate_id,
        outcome_features=features,
        provenance=provenance(f"candidate:{candidate_id}"),
        action_ref=action_ref,
    )


def minimize_score() -> PlanningCriterion:
    return PlanningCriterion(
        criterion_id="minimize-comparison-score",
        feature_key="comparison_score",
        direction=PlanningDirection.MINIMIZE,
    )


def proposition_p() -> PropositionKey:
    return PropositionKey(
        domain="entity",
        subject="zombie-1",
        predicate="nearby",
    )


def proposition_q() -> PropositionKey:
    return PropositionKey(
        domain="resource",
        subject="food",
        predicate="available",
    )


def evidence(
    evidence_id: str,
    *,
    proposition: PropositionKey,
    relation: EvidenceRelation,
) -> BeliefEvidence:
    return BeliefEvidence(
        evidence_id=evidence_id,
        proposition=proposition,
        relation=relation,
        provenance=provenance(f"evidence:{evidence_id}"),
    )


def nearby_threat_criterion() -> ConceptCriterion:
    return ConceptCriterion(
        criterion_id="supported-nearby-is-nearby-threat",
        concept=ConceptKey(domain="spatial", name="nearby_threat"),
        required_features=(
            ConceptFeature("source_kind", "belief_assessment"),
            ConceptFeature("belief_status", "supported"),
            ConceptFeature("proposition", proposition_p().canonical),
        ),
    )


def matched_nearby_threat() -> ConceptRepresentation:
    p = proposition_p()
    belief = assess_belief(
        (
            evidence(
                "E1",
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            ),
        ),
        BeliefCriterion("zombie-nearby", p),
    )
    structured = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    return classify_concept(structured, nearby_threat_criterion())


def prediction_for_score(
    score: int,
    *,
    rule_id: str,
) -> PredictionResult:
    concept = matched_nearby_threat()
    state = prediction_state_from_concept(
        concept,
        state_id=f"planning-source:{rule_id}",
        extra_variables=(
            StateVariable("comparison_score", 99),
        ),
        provenance=provenance(f"concept-to-prediction:{rule_id}"),
    )
    rule = TransitionRule(
        rule_id=rule_id,
        preconditions=(
            StateVariable("concept", "spatial:nearby_threat"),
        ),
        assignments=(
            StateVariable("comparison_score", score),
        ),
        provenance=provenance(f"rule:{rule_id}"),
    )
    return predict_transition(state, rule)


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s9",
        directives=("plan selection is not intent or action authority",),
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
        "intent-s9",
        objective="maintain current objective",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def test_package_exports_s9_planning_surface() -> None:
    assert relay_self.PlanFeature is PlanFeature
    assert relay_self.PlanCandidate is PlanCandidate
    assert relay_self.PlanningCriterion is PlanningCriterion
    assert relay_self.PlanningDirection is PlanningDirection
    assert relay_self.PlanSelection is PlanSelection
    assert relay_self.PlanSelectionStatus is PlanSelectionStatus
    assert relay_self.plan_candidate_from_prediction is plan_candidate_from_prediction
    assert relay_self.select_plan is select_plan
    assert relay_self.PlanningProfileId is PlanningProfileId
    assert relay_self.S9_PLANNING_PROFILES is S9_PLANNING_PROFILES
    assert relay_self.s9_planning_profile is s9_planning_profile


def test_s9_profiles_are_exactly_plan_prd_plan_and_full_chain() -> None:
    assert [profile.profile_id for profile in S9_PLANNING_PROFILES] == [
        PlanningProfileId.PLAN,
        PlanningProfileId.PRD_PLAN,
        PlanningProfileId.ATT_BLF_CNC_PRD_PLAN,
    ]
    assert s9_planning_profile(
        PlanningProfileId.PLAN
    ).enabled_ids == frozenset({"PLAN"})
    assert s9_planning_profile(
        PlanningProfileId.PRD_PLAN
    ).enabled_ids == frozenset({"PRD", "PLAN"})
    assert s9_planning_profile(
        PlanningProfileId.ATT_BLF_CNC_PRD_PLAN
    ).enabled_ids == frozenset({"ATT", "BLF", "CNC", "PRD", "PLAN"})


def test_plan_descriptor_is_stateless_read_only_cognitive_orientation() -> None:
    assert S9_PLAN_CAPABILITY_SPEC.state_scopes == ()
    assert S9_PLAN_CAPABILITY_SPEC.dependencies == ()
    assert S9_PLAN_OPERATOR_DESCRIPTOR.operator_id == "plan.select"
    assert S9_PLAN_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S9_PLAN_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert (
        S9_PLAN_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.planning.select_plan"
    )
    assert (
        S9_PLAN_CRITERION_DESCRIPTOR.criterion_id
        == "plan.explicit_preference_orientation"
    )
    assert (
        S9_PLAN_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert all(
        descriptor.kind is CriterionKind.CONTRACT_GUARD
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )


def test_standalone_minimize_selects_unique_best_candidate() -> None:
    wait = candidate("WAIT", 8)
    move = candidate("MOVE_AWAY", 3)

    selection = select_plan((wait, move), minimize_score())

    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is move
    assert selection.best_candidates == (move,)
    assert selection.compared_candidate_ids == ("WAIT", "MOVE_AWAY")


def test_standalone_maximize_selects_unique_best_candidate() -> None:
    low = candidate("LOW", 2)
    high = candidate("HIGH", 7)
    criterion = PlanningCriterion(
        criterion_id="maximize-score",
        feature_key="comparison_score",
        direction=PlanningDirection.MAXIMIZE,
    )

    selection = select_plan((low, high), criterion)

    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is high


def test_equal_best_score_is_explicit_tie_without_first_candidate_fallback() -> None:
    first = candidate("A", 3)
    second = candidate("B", 3)

    selection = select_plan((first, second), minimize_score())

    assert selection.status is PlanSelectionStatus.TIED
    assert selection.selected is None
    assert selection.best_candidates == (first, second)


def test_missing_comparison_input_is_undetermined_for_whole_comparison() -> None:
    rankable = candidate("A", 2)
    missing = candidate("B", None)

    selection = select_plan((rankable, missing), minimize_score())

    assert selection.status is PlanSelectionStatus.UNDETERMINED
    assert selection.selected is None
    assert selection.best_candidates == ()
    assert selection.unrankable_candidate_ids == ("B",)


def test_all_candidates_unrankable_is_undetermined() -> None:
    selection = select_plan(
        (candidate("A", None), candidate("B", None)),
        minimize_score(),
    )

    assert selection.status is PlanSelectionStatus.UNDETERMINED
    assert selection.unrankable_candidate_ids == ("A", "B")


def test_same_candidates_and_criterion_yield_same_immutable_result() -> None:
    wait = candidate("WAIT", 8)
    move = candidate("MOVE_AWAY", 3)
    criterion = minimize_score()

    first = select_plan((wait, move), criterion)
    second = select_plan((wait, move), criterion)

    assert first == second
    assert first.selected is move
    with pytest.raises(FrozenInstanceError):
        move.action_ref = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.status = PlanSelectionStatus.TIED  # type: ignore[misc]


def test_validation_fail_closed_for_empty_duplicate_malformed_and_noninteger_score() -> None:
    with pytest.raises(InvalidPlanningData, match="must not be empty"):
        select_plan((), minimize_score())

    duplicate = candidate("same", 1)
    with pytest.raises(InvalidPlanningData, match="candidate_id values must be unique"):
        select_plan((duplicate, duplicate), minimize_score())

    with pytest.raises(InvalidPlanningData, match="keys must be unique"):
        PlanCandidate(
            candidate_id="duplicate-features",
            outcome_features=(
                PlanFeature("comparison_score", 1),
                PlanFeature("comparison_score", 2),
            ),
            provenance=provenance("duplicate-features"),
        )

    with pytest.raises(InvalidPlanningData, match="plan feature value"):
        PlanFeature("comparison_score", {"score": 1})  # type: ignore[arg-type]

    with pytest.raises(InvalidPlanningData, match="structured identifier"):
        PlanningCriterion(
            criterion_id="bad criterion",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        )

    bad = PlanCandidate(
        candidate_id="categorical",
        outcome_features=(PlanFeature("comparison_score", "low"),),
        provenance=provenance("categorical"),
    )
    with pytest.raises(InvalidPlanningData, match="integer"):
        select_plan((bad,), minimize_score())


def test_prediction_bridge_preserves_prediction_lineage_and_action_is_metadata_only() -> None:
    prediction = prediction_for_score(3, rule_id="move-away")

    plan = plan_candidate_from_prediction(
        prediction,
        candidate_id="MOVE_AWAY",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:move-away"),
        action_ref="MOVE_BACKWARD",
    )

    assert plan.outcome_features == (PlanFeature("comparison_score", 3),)
    assert plan.action_ref == "MOVE_BACKWARD"
    assert plan.prediction_ref is not None
    assert "move-away" in plan.prediction_ref
    assert plan.source_refs[-1].startswith("predicted-state:")
    assert prediction.predicted_state is not None
    assert plan.source_provenance[-1] == prediction.predicted_state.provenance
    assert prediction.status is PredictionStatus.PREDICTED


def test_prediction_bridge_fails_closed_without_predicted_result_or_requested_feature() -> None:
    with pytest.raises(PlanSourceUnavailable, match="PredictionResult"):
        plan_candidate_from_prediction(
            None,
            candidate_id="missing",
            feature_keys=("comparison_score",),
            provenance=provenance("missing"),
        )

    no_transition = predict_transition(
        PredictionState(
            state_id="source:no-transition",
            variables=(StateVariable("x", 0),),
            provenance=provenance("source:no-transition"),
        ),
        TransitionRule(
            rule_id="requires-one",
            preconditions=(StateVariable("x", 1),),
            assignments=(StateVariable("comparison_score", 1),),
            provenance=provenance("rule:requires-one"),
        ),
    )
    assert no_transition.status is PredictionStatus.NO_TRANSITION
    with pytest.raises(PlanSourceUnavailable, match="PREDICTED"):
        plan_candidate_from_prediction(
            no_transition,
            candidate_id="no-transition",
            feature_keys=("comparison_score",),
            provenance=provenance("no-transition"),
        )

    predicted = prediction_for_score(3, rule_id="move-away")
    with pytest.raises(PlanSourceUnavailable, match="missing requested plan feature"):
        plan_candidate_from_prediction(
            predicted,
            candidate_id="move-away",
            feature_keys=("missing_score",),
            provenance=provenance("missing-feature"),
        )


def test_provider_expression_is_not_plan_candidate_or_plan_selection() -> None:
    generated = ProviderExpression(
        text="You should run away.",
        provenance=provenance("provider-expression"),
    )

    with pytest.raises(InvalidPlanningData, match="PlanCandidate"):
        select_plan((generated,), minimize_score())  # type: ignore[arg-type]

    with pytest.raises(PlanSourceUnavailable, match="PredictionResult"):
        plan_candidate_from_prediction(
            generated,
            candidate_id="provider-plan",
            feature_keys=("comparison_score",),
            provenance=provenance("provider-plan"),
        )


def test_plan_on_executes_real_selection_with_zero_cognition_calls() -> None:
    box: dict[str, PlanSelection] = {}
    candidates = (candidate("WAIT", 8), candidate("MOVE_AWAY", 3))

    def choose() -> None:
        box["selection"] = select_plan(candidates, minimize_score())

    binding = EpochBinding("plan-1", "plan.select", choose)
    plan = compile_epoch_plan(
        s9_planning_profile(PlanningProfileId.PLAN).plan(),
        S9_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "plan-1",
                "plan.select",
                "finite-candidate-comparison",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-plan"),
    )

    assert box["selection"].status is PlanSelectionStatus.SELECTED
    assert box["selection"].selected is candidates[1]
    assert result.executed_work_ids == ("plan-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_plan_off_suppresses_only_plan_while_prd_still_executes() -> None:
    box: dict[str, object] = {}
    source = PredictionState(
        state_id="source:wait",
        variables=(StateVariable("comparison_score", 99),),
        provenance=provenance("source:wait"),
    )
    rule = TransitionRule(
        rule_id="wait",
        preconditions=(StateVariable("comparison_score", 99),),
        assignments=(StateVariable("comparison_score", 8),),
        provenance=provenance("rule:wait"),
    )

    def predict() -> None:
        box["prediction"] = predict_transition(source, rule)

    binding = EpochBinding("prd-1", "prd.predict", predict)
    plan = compile_epoch_plan(
        s9_capability_plan(enabled_ids=frozenset({"PRD"})),
        S9_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("prd-1", "prd.predict", "explicit-transition"),
            EpochWorkItem("plan-1", "plan.select", "planning-disabled"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-plan-off"),
    )

    assert isinstance(box["prediction"], PredictionResult)
    assert box["prediction"].status is PredictionStatus.PREDICTED
    assert result.executed_work_ids == ("prd-1",)
    assert result.suppressed_work_ids == ("plan-1",)
    assert "selection" not in box
    assert result.cognition_requested is False


def test_prd_plan_compares_two_explicit_prediction_results_without_rerunning_prd() -> None:
    box: dict[str, object] = {}
    invocations = {"PRD": 0, "PLAN": 0}

    def predict_wait() -> None:
        invocations["PRD"] += 1
        box["wait_prediction"] = prediction_for_score(8, rule_id="wait")

    def predict_move() -> None:
        invocations["PRD"] += 1
        box["move_prediction"] = prediction_for_score(3, rule_id="move-away")

    def choose() -> None:
        invocations["PLAN"] += 1
        wait = plan_candidate_from_prediction(
            box.get("wait_prediction"),
            candidate_id="WAIT",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:wait"),
            action_ref="WAIT",
        )
        move = plan_candidate_from_prediction(
            box.get("move_prediction"),
            candidate_id="MOVE_AWAY",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:move-away"),
            action_ref="MOVE_BACKWARD",
        )
        box["candidates"] = (wait, move)
        box["selection"] = select_plan((wait, move), minimize_score())

    bindings = (
        EpochBinding("prd-wait", "prd.predict", predict_wait),
        EpochBinding("prd-move", "prd.predict", predict_move),
        EpochBinding("plan-1", "plan.select", choose),
    )
    plan = compile_epoch_plan(
        s9_planning_profile(PlanningProfileId.PRD_PLAN).plan(),
        S9_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("prd-wait", "prd.predict", "wait-transition"),
            EpochWorkItem("prd-move", "prd.predict", "move-transition"),
            EpochWorkItem("plan-1", "plan.select", "compare-predictions"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-prd-plan"),
    )

    selection = box["selection"]
    assert isinstance(selection, PlanSelection)
    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is not None
    assert selection.selected.candidate_id == "MOVE_AWAY"
    assert selection.selected.action_ref == "MOVE_BACKWARD"
    assert invocations == {"PRD": 2, "PLAN": 1}
    assert result.executed_work_ids == ("prd-wait", "prd-move", "plan-1")
    assert result.cognition_requested is False


def test_att_blf_cnc_prd_plan_forms_zero_provider_call_deterministic_chain() -> None:
    p = proposition_p()
    q = proposition_q()
    evidence_by_id = {
        "E1": evidence(
            "E1",
            proposition=p,
            relation=EvidenceRelation.SUPPORT,
        ),
        "E2": evidence(
            "E2",
            proposition=p,
            relation=EvidenceRelation.SUPPORT,
        ),
        "E3": evidence(
            "E3",
            proposition=q,
            relation=EvidenceRelation.SUPPORT,
        ),
    }
    source_candidates = (
        AttentionCandidate(
            "E1",
            "belief-evidence:E1",
            provenance("attention:E1"),
            priority=2,
            focus_keys=("zombie-1",),
        ),
        AttentionCandidate(
            "E2",
            "belief-evidence:E2",
            provenance("attention:E2"),
            priority=1,
            focus_keys=("zombie-1",),
        ),
        AttentionCandidate(
            "E3",
            "belief-evidence:E3",
            provenance("attention:E3"),
            priority=9,
            focus_keys=("other",),
        ),
    )
    original_candidates = source_candidates
    box: dict[str, object] = {}
    stage_invocations = {"ATT": 0, "BLF": 0, "CNC": 0, "PRD": 0, "PLAN": 0}

    def attend() -> None:
        stage_invocations["ATT"] += 1
        box["attention"] = select_attention(
            source_candidates,
            AttentionCriterion(
                criterion_id="focus-zombie-1",
                focus_key="zombie-1",
            ),
        )

    def assess_selected() -> None:
        stage_invocations["BLF"] += 1
        selection = require_attention_selection(box.get("attention"))
        admitted = tuple(
            evidence_by_id[item.candidate_id]
            for item in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("zombie-nearby", p),
        )

    def classify_belief() -> None:
        stage_invocations["CNC"] += 1
        structured = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            structured,
            nearby_threat_criterion(),
        )

    def base_prediction_state() -> PredictionState:
        return prediction_state_from_concept(
            box.get("concept"),
            state_id="planning:threat:zombie-1",
            extra_variables=(
                StateVariable("comparison_score", 99),
            ),
            provenance=provenance("concept-to-prediction"),
        )

    def predict_wait() -> None:
        stage_invocations["PRD"] += 1
        box["wait_prediction"] = predict_transition(
            base_prediction_state(),
            TransitionRule(
                rule_id="wait",
                preconditions=(
                    StateVariable("concept", "spatial:nearby_threat"),
                ),
                assignments=(
                    StateVariable("comparison_score", 8),
                ),
                provenance=provenance("rule:wait"),
            ),
        )

    def predict_move() -> None:
        stage_invocations["PRD"] += 1
        box["move_prediction"] = predict_transition(
            base_prediction_state(),
            TransitionRule(
                rule_id="move-away",
                preconditions=(
                    StateVariable("concept", "spatial:nearby_threat"),
                ),
                assignments=(
                    StateVariable("comparison_score", 3),
                ),
                provenance=provenance("rule:move-away"),
            ),
        )

    def choose() -> None:
        stage_invocations["PLAN"] += 1
        wait = plan_candidate_from_prediction(
            box.get("wait_prediction"),
            candidate_id="WAIT",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:wait"),
            action_ref="WAIT",
        )
        move = plan_candidate_from_prediction(
            box.get("move_prediction"),
            candidate_id="MOVE_AWAY",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:move-away"),
            action_ref="MOVE_BACKWARD",
        )
        box["plan_candidates"] = (wait, move)
        box["plan_selection"] = select_plan(
            (wait, move),
            minimize_score(),
        )

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", assess_selected),
        EpochBinding("cnc-1", "cnc.classify", classify_belief),
        EpochBinding("prd-wait", "prd.predict", predict_wait),
        EpochBinding("prd-move", "prd.predict", predict_move),
        EpochBinding("plan-1", "plan.select", choose),
    )
    plan = compile_epoch_plan(
        s9_planning_profile(
            PlanningProfileId.ATT_BLF_CNC_PRD_PLAN
        ).plan(),
        S9_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "candidate-evidence"),
            EpochWorkItem("blf-1", "blf.assess", "att-selected-evidence"),
            EpochWorkItem("cnc-1", "cnc.classify", "structured-belief"),
            EpochWorkItem("prd-wait", "prd.predict", "wait-prediction"),
            EpochWorkItem("prd-move", "prd.predict", "move-prediction"),
            EpochWorkItem("plan-1", "plan.select", "finite-plan-comparison"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-full-plan-chain"),
    )

    attention = box["attention"]
    belief = box["belief"]
    concept = box["concept"]
    wait_prediction = box["wait_prediction"]
    move_prediction = box["move_prediction"]
    selection = box["plan_selection"]

    assert isinstance(attention, AttentionSelection)
    assert isinstance(belief, BeliefAssessment)
    assert isinstance(concept, ConceptRepresentation)
    assert isinstance(wait_prediction, PredictionResult)
    assert isinstance(move_prediction, PredictionResult)
    assert isinstance(selection, PlanSelection)

    assert attention.candidate_ids == ("E1", "E2")
    assert belief.evidence_ids == ("E1", "E2")
    assert "E3" not in belief.evidence_ids
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept.status is ConceptStatus.MATCHED
    assert concept.concept == ConceptKey("spatial", "nearby_threat")
    assert wait_prediction.status is PredictionStatus.PREDICTED
    assert move_prediction.status is PredictionStatus.PREDICTED
    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is not None
    assert selection.selected.candidate_id == "MOVE_AWAY"
    assert selection.selected.action_ref == "MOVE_BACKWARD"

    assert belief.status is BeliefStatus.SUPPORTED
    assert concept.status is ConceptStatus.MATCHED
    assert wait_prediction.status is PredictionStatus.PREDICTED
    assert move_prediction.status is PredictionStatus.PREDICTED
    assert source_candidates == original_candidates
    assert stage_invocations == {
        "ATT": 1,
        "BLF": 1,
        "CNC": 1,
        "PRD": 2,
        "PLAN": 1,
    }
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_integrated_route_fails_closed_if_attention_result_is_missing() -> None:
    box: dict[str, object] = {}
    p = proposition_p()

    def assess_selected() -> None:
        selection = require_attention_selection(box.get("attention"))
        admitted = tuple(
            evidence(
                item.candidate_id,
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            )
            for item in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("zombie-nearby", p),
        )

    binding = EpochBinding("blf-1", "blf.assess", assess_selected)
    plan = compile_epoch_plan(
        s9_capability_plan(enabled_ids=frozenset({"BLF"})),
        S9_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "disabled"),
            EpochWorkItem(
                "blf-1",
                "blf.assess",
                "attention-dependent-belief",
            ),
        ),
        bindings=(binding,),
    )

    with pytest.raises(AttentionSelectionUnavailable):
        coordinate_planned_epoch(
            ActionSupervisor(),
            plan,
            bindings=(binding,),
            at_ns=10,
            provenance=provenance("epoch-missing-attention"),
        )

    assert "belief" not in box
    assert "plan_selection" not in box


def test_plan_selection_does_not_mutate_upstream_or_authority_owners() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s9",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-s9",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action"),
    )
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )

    p = proposition_p()
    belief = assess_belief(
        (
            evidence(
                "E1",
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            ),
        ),
        BeliefCriterion("zombie-nearby", p),
    )
    concept_candidate = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    concept = classify_concept(
        concept_candidate,
        nearby_threat_criterion(),
    )
    attention_source = (
        AttentionCandidate(
            "E1",
            "belief-evidence:E1",
            provenance("attention:E1"),
            focus_keys=("zombie-1",),
        ),
    )
    attention = select_attention(
        attention_source,
        AttentionCriterion("zombie-focus", focus_key="zombie-1"),
    )
    wait_prediction = prediction_for_score(8, rule_id="wait")
    move_prediction = prediction_for_score(3, rule_id="move-away")
    wait = plan_candidate_from_prediction(
        wait_prediction,
        candidate_id="WAIT",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:wait"),
        action_ref="WAIT",
    )
    move = plan_candidate_from_prediction(
        move_prediction,
        candidate_id="MOVE_AWAY",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:move-away"),
        action_ref="MOVE_BACKWARD",
    )

    before_memories = cognition.memories
    before_intent_events = intent_owner.events
    before_skill_events = skill.events
    before_action_events = action.events
    before_attention = attention
    before_belief = belief
    before_concept = concept
    before_wait_prediction = wait_prediction
    before_move_prediction = move_prediction
    before_wait = wait
    before_move = move

    selection = select_plan((wait, move), minimize_score())

    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is move
    assert cognition.memories == before_memories
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s9"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert action.events == before_action_events
    assert action.state is ActionState.PROPOSED
    assert attention == before_attention
    assert belief == before_belief
    assert concept == before_concept
    assert wait_prediction == before_wait_prediction
    assert move_prediction == before_move_prediction
    assert wait == before_wait
    assert move == before_move
    assert selection.selected.action_ref == "MOVE_BACKWARD"
    assert intent_owner.current_intent.intent_id != selection.selected.candidate_id
