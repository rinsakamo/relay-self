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
    S7_DESCRIPTOR_SET,
    S8_DESCRIPTOR_SET,
    S8_PRD_CAPABILITY_SPEC,
    S8_PRD_OPERATOR_DESCRIPTOR,
    OperatorEffect,
    s8_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.prediction import (
    InvalidPredictionData,
    PredictionResult,
    PredictionSourceUnavailable,
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
    prediction_state_from_belief,
    prediction_state_from_concept,
)
from relay_self.prediction_profile import (
    S8_PREDICTION_PROFILES,
    PredictionProfileId,
    s8_prediction_profile,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s8-prediction-qualification", reference=reference)


def threat_state(
    *,
    distance_band: str = "near",
    moving_toward_self: bool | None = True,
) -> PredictionState:
    variables = [StateVariable("distance_band", distance_band)]
    if moving_toward_self is not None:
        variables.append(
            StateVariable("moving_toward_self", moving_toward_self)
        )
    return PredictionState(
        state_id="threat:0",
        variables=tuple(variables),
        provenance=provenance("state:threat:0"),
    )


def approach_rule() -> TransitionRule:
    return TransitionRule(
        rule_id="threat:near-to-immediate",
        preconditions=(
            StateVariable("distance_band", "near"),
            StateVariable("moving_toward_self", True),
        ),
        assignments=(
            StateVariable("distance_band", "immediate"),
        ),
        provenance=provenance("rule:near-to-immediate"),
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
    candidate = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    return classify_concept(candidate, nearby_threat_criterion())


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s8",
        directives=("keep prediction separate from truth and action",),
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
        "intent-s8",
        objective="maintain current objective",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def test_package_exports_s8_prediction_surface() -> None:
    assert relay_self.StateVariable is StateVariable
    assert relay_self.PredictionState is PredictionState
    assert relay_self.TransitionRule is TransitionRule
    assert relay_self.PredictionResult is PredictionResult
    assert relay_self.PredictionStatus is PredictionStatus
    assert relay_self.predict_transition is predict_transition
    assert relay_self.prediction_state_from_concept is prediction_state_from_concept
    assert relay_self.prediction_state_from_belief is prediction_state_from_belief
    assert relay_self.PredictionProfileId is PredictionProfileId
    assert relay_self.S8_PREDICTION_PROFILES is S8_PREDICTION_PROFILES
    assert relay_self.s8_prediction_profile is s8_prediction_profile


def test_s8_profiles_are_exactly_prd_cnc_prd_and_full_chain() -> None:
    assert [profile.profile_id for profile in S8_PREDICTION_PROFILES] == [
        PredictionProfileId.PRD,
        PredictionProfileId.CNC_PRD,
        PredictionProfileId.ATT_BLF_CNC_PRD,
    ]
    assert s8_prediction_profile(
        PredictionProfileId.PRD
    ).enabled_ids == frozenset({"PRD"})
    assert s8_prediction_profile(
        PredictionProfileId.CNC_PRD
    ).enabled_ids == frozenset({"CNC", "PRD"})
    assert s8_prediction_profile(
        PredictionProfileId.ATT_BLF_CNC_PRD
    ).enabled_ids == frozenset({"ATT", "BLF", "CNC", "PRD"})


def test_prd_descriptor_is_stateless_read_only_without_forced_cognitive_criterion() -> None:
    assert S8_PRD_CAPABILITY_SPEC.state_scopes == ()
    assert S8_PRD_CAPABILITY_SPEC.dependencies == ()
    assert S8_PRD_CAPABILITY_SPEC.criterion_ids == ()
    assert S8_PRD_OPERATOR_DESCRIPTOR.operator_id == "prd.predict"
    assert S8_PRD_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S8_PRD_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert (
        S8_PRD_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.prediction.predict_transition"
    )
    assert S8_PRD_OPERATOR_DESCRIPTOR.writes == (
        "transient.prediction_result",
    )
    assert S8_DESCRIPTOR_SET.criteria == S7_DESCRIPTOR_SET.criteria
    assert all(
        descriptor.capability_id != "PRD"
        for descriptor in S8_DESCRIPTOR_SET.criteria
    )


def test_transition_applies_and_preserves_unmentioned_variables() -> None:
    source = threat_state()
    rule = approach_rule()

    result = predict_transition(source, rule)

    assert result.status is PredictionStatus.PREDICTED
    assert result.source_state is source
    assert result.rule is rule
    assert result.predicted_state is not None
    assert result.predicted_state.step_index == 1
    assert result.predicted_state.variable("distance_band") == StateVariable(
        "distance_band",
        "immediate",
    )
    assert result.predicted_state.variable(
        "moving_toward_self"
    ) is source.variables[1]
    assert result.matched_preconditions == source.variables
    assert result.predicted_state.provenance.source == (
        "relay_self.prediction.predict_transition"
    )
    assert result.predicted_state.source_provenance[-2:] == (
        source.provenance,
        rule.provenance,
    )


def test_explicit_precondition_failure_is_no_transition() -> None:
    source = threat_state(distance_band="far")

    result = predict_transition(source, approach_rule())

    assert result.status is PredictionStatus.NO_TRANSITION
    assert result.predicted_state is None
    assert result.mismatched_precondition_keys == ("distance_band",)
    assert result.missing_precondition_keys == ()


def test_missing_required_variable_is_undetermined_not_false() -> None:
    source = threat_state(moving_toward_self=None)

    result = predict_transition(source, approach_rule())

    assert result.status is PredictionStatus.UNDETERMINED
    assert result.predicted_state is None
    assert result.missing_precondition_keys == ("moving_toward_self",)
    assert result.mismatched_precondition_keys == ()


def test_explicit_mismatch_dominates_missing() -> None:
    source = PredictionState(
        state_id="threat:partial",
        variables=(StateVariable("distance_band", "far"),),
        provenance=provenance("state:partial"),
    )

    result = predict_transition(source, approach_rule())

    assert result.status is PredictionStatus.NO_TRANSITION
    assert result.mismatched_precondition_keys == ("distance_band",)
    assert result.missing_precondition_keys == ("moving_toward_self",)


def test_same_state_and_rule_yield_same_immutable_prediction() -> None:
    source = threat_state()
    rule = approach_rule()

    first = predict_transition(source, rule)
    second = predict_transition(source, rule)

    assert first == second
    assert source == threat_state()
    with pytest.raises(FrozenInstanceError):
        source.step_index = 4  # type: ignore[misc]
    assert first.predicted_state is not None
    with pytest.raises(FrozenInstanceError):
        first.predicted_state.step_index = 4  # type: ignore[misc]


def test_malformed_state_rule_and_variables_fail_closed() -> None:
    with pytest.raises(InvalidPredictionData, match="structured identifier"):
        PredictionState(
            state_id="bad state",
            variables=(StateVariable("x", 1),),
            provenance=provenance("bad-state"),
        )

    with pytest.raises(InvalidPredictionData, match="keys must be unique"):
        PredictionState(
            state_id="duplicate-state",
            variables=(
                StateVariable("x", 1),
                StateVariable("x", 2),
            ),
            provenance=provenance("duplicate-state"),
        )

    with pytest.raises(InvalidPredictionData, match="state variable value"):
        StateVariable("x", {"mutable": True})  # type: ignore[arg-type]

    with pytest.raises(InvalidPredictionData, match="must not be empty"):
        TransitionRule(
            rule_id="empty-preconditions",
            preconditions=(),
            assignments=(StateVariable("x", 1),),
            provenance=provenance("empty-preconditions"),
        )

    with pytest.raises(InvalidPredictionData, match="keys must be unique"):
        TransitionRule(
            rule_id="duplicate-precondition",
            preconditions=(
                StateVariable("x", 1),
                StateVariable("x", 2),
            ),
            assignments=(StateVariable("y", 1),),
            provenance=provenance("duplicate-precondition"),
        )

    with pytest.raises(InvalidPredictionData, match="keys must be unique"):
        TransitionRule(
            rule_id="duplicate-assignment",
            preconditions=(StateVariable("x", 1),),
            assignments=(
                StateVariable("y", 1),
                StateVariable("y", 2),
            ),
            provenance=provenance("duplicate-assignment"),
        )


def test_provider_expression_is_not_prediction_state_or_transition_rule() -> None:
    generated = ProviderExpression(
        text="The zombie will reach you next.",
        provenance=provenance("provider-expression"),
    )

    with pytest.raises(InvalidPredictionData, match="PredictionState"):
        predict_transition(generated, approach_rule())  # type: ignore[arg-type]

    with pytest.raises(InvalidPredictionData, match="TransitionRule"):
        predict_transition(
            threat_state(),
            generated,  # type: ignore[arg-type]
        )


def test_concept_and_belief_bridges_fail_closed_without_required_source() -> None:
    with pytest.raises(PredictionSourceUnavailable, match="ConceptRepresentation"):
        prediction_state_from_concept(
            None,
            state_id="missing-concept",
            extra_variables=(),
            provenance=provenance("missing-concept"),
        )

    with pytest.raises(PredictionSourceUnavailable, match="BeliefAssessment"):
        prediction_state_from_belief(
            None,
            state_id="missing-belief",
            extra_variables=(),
            provenance=provenance("missing-belief"),
        )

    unmatched = ConceptRepresentation(
        source=ConceptCandidate(
            candidate_id="cow",
            payload_ref="present:cow",
            features=(ConceptFeature("hostile", False),),
            provenance=provenance("cow"),
        ),
        criterion=ConceptCriterion(
            criterion_id="hostile",
            concept=ConceptKey("entity", "hostile_mob"),
            required_features=(ConceptFeature("hostile", True),),
        ),
        status=ConceptStatus.NOT_MATCHED,
        supporting_features=(),
        missing_feature_keys=(),
        mismatched_feature_keys=("hostile",),
    )
    with pytest.raises(PredictionSourceUnavailable, match="MATCHED"):
        prediction_state_from_concept(
            unmatched,
            state_id="unmatched-concept",
            extra_variables=(),
            provenance=provenance("unmatched-concept"),
        )


def test_prd_on_executes_real_prediction_with_zero_cognition_calls() -> None:
    box: dict[str, PredictionResult] = {}
    source = threat_state()
    rule = approach_rule()

    def predict() -> None:
        box["prediction"] = predict_transition(source, rule)

    binding = EpochBinding("prd-1", "prd.predict", predict)
    plan = compile_epoch_plan(
        s8_prediction_profile(PredictionProfileId.PRD).plan(),
        S8_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "prd-1",
                "prd.predict",
                "explicit-transition-rule",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-prd"),
    )

    assert box["prediction"].status is PredictionStatus.PREDICTED
    assert result.executed_work_ids == ("prd-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_prd_off_suppresses_only_prd_while_cnc_still_executes() -> None:
    box: dict[str, object] = {}
    candidate = ConceptCandidate(
        candidate_id="entity:zombie-1",
        payload_ref="present:zombie-1",
        features=(ConceptFeature("hostile", True),),
        provenance=provenance("candidate:zombie-1"),
    )
    criterion = ConceptCriterion(
        criterion_id="hostile",
        concept=ConceptKey("entity", "hostile_mob"),
        required_features=(ConceptFeature("hostile", True),),
    )

    def classify() -> None:
        box["concept"] = classify_concept(candidate, criterion)

    binding = EpochBinding("cnc-1", "cnc.classify", classify)
    plan = compile_epoch_plan(
        s8_capability_plan(enabled_ids=frozenset({"CNC"})),
        S8_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("cnc-1", "cnc.classify", "structured-candidate"),
            EpochWorkItem("prd-1", "prd.predict", "prediction-disabled"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-prd-off"),
    )

    assert result.executed_work_ids == ("cnc-1",)
    assert result.suppressed_work_ids == ("prd-1",)
    assert isinstance(box["concept"], ConceptRepresentation)
    assert box["concept"].status is ConceptStatus.MATCHED
    assert "prediction" not in box
    assert result.cognition_requested is False


def test_cnc_prd_projects_matched_concept_without_reclassifying_it() -> None:
    box: dict[str, object] = {}
    representation = matched_nearby_threat()

    def classify_existing() -> None:
        box["concept"] = representation

    def predict_from_concept() -> None:
        concept = box.get("concept")
        state = prediction_state_from_concept(
            concept,
            state_id="threat-from-concept",
            extra_variables=(
                StateVariable("distance_band", "near"),
                StateVariable("moving_toward_self", True),
            ),
            provenance=provenance("concept-to-prediction"),
        )
        rule = TransitionRule(
            rule_id="nearby-threat-to-immediate",
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
                StateVariable("distance_band", "near"),
                StateVariable("moving_toward_self", True),
            ),
            assignments=(StateVariable("distance_band", "immediate"),),
            provenance=provenance("rule:nearby-threat-to-immediate"),
        )
        box["prediction_state"] = state
        box["prediction"] = predict_transition(state, rule)

    bindings = (
        EpochBinding("cnc-1", "cnc.classify", classify_existing),
        EpochBinding("prd-1", "prd.predict", predict_from_concept),
    )
    plan = compile_epoch_plan(
        s8_prediction_profile(PredictionProfileId.CNC_PRD).plan(),
        S8_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("cnc-1", "cnc.classify", "matched-concept"),
            EpochWorkItem("prd-1", "prd.predict", "concept-derived-state"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-cnc-prd"),
    )

    concept = box["concept"]
    prediction = box["prediction"]
    assert concept is representation
    assert isinstance(prediction, PredictionResult)
    assert prediction.status is PredictionStatus.PREDICTED
    assert prediction.predicted_state is not None
    assert prediction.predicted_state.variable("distance_band") == StateVariable(
        "distance_band",
        "immediate",
    )
    assert representation.status is ConceptStatus.MATCHED
    assert result.executed_work_ids == ("cnc-1", "prd-1")
    assert result.cognition_requested is False


def test_att_blf_cnc_prd_forms_zero_call_deterministic_chain() -> None:
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
    calls = {"ATT": 0, "BLF": 0, "CNC": 0, "PRD": 0}

    def attend() -> None:
        calls["ATT"] += 1
        box["selection"] = select_attention(
            source_candidates,
            AttentionCriterion(
                criterion_id="focus-zombie-1",
                focus_key="zombie-1",
            ),
        )

    def assess_selected() -> None:
        calls["BLF"] += 1
        selection = require_attention_selection(box.get("selection"))
        admitted = tuple(
            evidence_by_id[candidate.candidate_id]
            for candidate in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("zombie-nearby", p),
        )

    def classify_belief() -> None:
        calls["CNC"] += 1
        candidate = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            candidate,
            nearby_threat_criterion(),
        )

    def predict_from_concept() -> None:
        calls["PRD"] += 1
        state = prediction_state_from_concept(
            box.get("concept"),
            state_id="threat:zombie-1",
            extra_variables=(
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            provenance=provenance("concept-to-prediction"),
        )
        rule = TransitionRule(
            rule_id="nearby-threat-approaches",
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            assignments=(StateVariable("threat_state", "immediate"),),
            provenance=provenance("rule:nearby-threat-approaches"),
        )
        box["prediction_state"] = state
        box["prediction_rule"] = rule
        box["prediction"] = predict_transition(state, rule)

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", assess_selected),
        EpochBinding("cnc-1", "cnc.classify", classify_belief),
        EpochBinding("prd-1", "prd.predict", predict_from_concept),
    )
    plan = compile_epoch_plan(
        s8_prediction_profile(
            PredictionProfileId.ATT_BLF_CNC_PRD
        ).plan(),
        S8_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "candidate-evidence"),
            EpochWorkItem("blf-1", "blf.assess", "att-selected-evidence"),
            EpochWorkItem("cnc-1", "cnc.classify", "structured-belief"),
            EpochWorkItem("prd-1", "prd.predict", "concept-derived-state"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-att-blf-cnc-prd"),
    )

    selection = box["selection"]
    belief = box["belief"]
    concept = box["concept"]
    prediction = box["prediction"]
    assert isinstance(selection, AttentionSelection)
    assert isinstance(belief, BeliefAssessment)
    assert isinstance(concept, ConceptRepresentation)
    assert isinstance(prediction, PredictionResult)
    assert selection.candidate_ids == ("E1", "E2")
    assert belief.evidence_ids == ("E1", "E2")
    assert "E3" not in belief.evidence_ids
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept.status is ConceptStatus.MATCHED
    assert concept.concept == ConceptKey("spatial", "nearby_threat")
    assert prediction.status is PredictionStatus.PREDICTED
    assert prediction.predicted_state is not None
    assert prediction.predicted_state.variable("threat_state") == StateVariable(
        "threat_state",
        "immediate",
    )
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept.status is ConceptStatus.MATCHED
    assert source_candidates == original_candidates
    assert calls == {"ATT": 1, "BLF": 1, "CNC": 1, "PRD": 1}
    assert result.executed_work_ids == (
        "att-1",
        "blf-1",
        "cnc-1",
        "prd-1",
    )
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_full_chain_fails_closed_if_attention_result_is_missing() -> None:
    box: dict[str, object] = {}
    p = proposition_p()

    def assess_selected() -> None:
        selection = require_attention_selection(box.get("selection"))
        admitted = tuple(
            evidence(
                candidate.candidate_id,
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            )
            for candidate in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("zombie-nearby", p),
        )

    bindings = (
        EpochBinding("blf-1", "blf.assess", assess_selected),
    )
    plan = compile_epoch_plan(
        s8_capability_plan(enabled_ids=frozenset({"BLF"})),
        S8_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "disabled"),
            EpochWorkItem(
                "blf-1",
                "blf.assess",
                "explicit-attention-dependent-belief",
            ),
        ),
        bindings=bindings,
    )

    with pytest.raises(AttentionSelectionUnavailable):
        coordinate_planned_epoch(
            ActionSupervisor(),
            plan,
            bindings=bindings,
            at_ns=10,
            provenance=provenance("epoch-missing-attention"),
        )

    assert "belief" not in box


def test_prd_does_not_mutate_any_upstream_or_authority_owner() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s8",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-s8",
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
    selection = select_attention(
        attention_source,
        AttentionCriterion("zombie-focus", focus_key="zombie-1"),
    )
    state = prediction_state_from_concept(
        concept,
        state_id="threat:zombie-1",
        extra_variables=(
            StateVariable("distance_band", "near"),
            StateVariable("moving_toward_self", True),
        ),
        provenance=provenance("concept-to-prediction"),
    )
    rule = TransitionRule(
        rule_id="approach",
        preconditions=(
            StateVariable("distance_band", "near"),
            StateVariable("moving_toward_self", True),
        ),
        assignments=(StateVariable("distance_band", "immediate"),),
        provenance=provenance("rule:approach"),
    )

    before_memories = cognition.memories
    before_intent_events = intent_owner.events
    before_skill_events = skill.events
    before_action_events = action.events
    before_selection = selection
    before_belief = belief
    before_concept = concept
    before_state = state

    prediction = predict_transition(state, rule)

    assert prediction.status is PredictionStatus.PREDICTED
    assert cognition.memories == before_memories
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s8"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert action.events == before_action_events
    assert action.state is ActionState.PROPOSED
    assert selection == before_selection
    assert belief == before_belief
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept == before_concept
    assert concept.status is ConceptStatus.MATCHED
    assert state == before_state
