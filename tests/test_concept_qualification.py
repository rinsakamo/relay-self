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
    ConceptSourceUnavailable,
    ConceptStatus,
    InvalidConceptData,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.concept_profile import (
    S7_CONCEPT_PROFILES,
    ConceptProfileId,
    s7_concept_profile,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    S7_CNC_CAPABILITY_SPEC,
    S7_CNC_CRITERION_DESCRIPTOR,
    S7_CNC_OPERATOR_DESCRIPTOR,
    S7_DESCRIPTOR_SET,
    CriterionKind,
    OperatorEffect,
    s7_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s7-concept-qualification", reference=reference)


def hostile_mob() -> ConceptKey:
    return ConceptKey(domain="entity", name="hostile_mob")


def contested_claim() -> ConceptKey:
    return ConceptKey(domain="epistemic", name="contested_claim")


def hostile_criterion() -> ConceptCriterion:
    return ConceptCriterion(
        criterion_id="hostile-and-alive",
        concept=hostile_mob(),
        required_features=(
            ConceptFeature("hostile", True),
            ConceptFeature("alive", True),
        ),
    )


def zombie_candidate() -> ConceptCandidate:
    return ConceptCandidate(
        candidate_id="entity:zombie-1",
        payload_ref="present:entity:zombie-1",
        features=(
            ConceptFeature("entity_kind", "zombie"),
            ConceptFeature("hostile", True),
            ConceptFeature("alive", True),
        ),
        provenance=provenance("candidate:zombie-1"),
        source_refs=("present:entity:zombie-1",),
        source_provenance=(provenance("world-observation:zombie-1"),),
    )


def proposition_p() -> PropositionKey:
    return PropositionKey(
        domain="route",
        subject="ridge",
        predicate="safe",
    )


def proposition_q() -> PropositionKey:
    return PropositionKey(
        domain="resource",
        subject="food",
        predicate="available",
    )


def belief_evidence(
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


def conflicted_belief() -> BeliefAssessment:
    p = proposition_p()
    return assess_belief(
        (
            belief_evidence(
                "E1",
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            ),
            belief_evidence(
                "E2",
                proposition=p,
                relation=EvidenceRelation.OPPOSE,
            ),
        ),
        BeliefCriterion("ridge-safety", p),
    )


def contested_criterion() -> ConceptCriterion:
    return ConceptCriterion(
        criterion_id="conflicted-belief-is-contested",
        concept=contested_claim(),
        required_features=(
            ConceptFeature("source_kind", "belief_assessment"),
            ConceptFeature("belief_status", "conflicted"),
        ),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s7",
        directives=("keep concepts separate from truth and authority",),
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
        "intent-s7",
        objective="reach the safe waypoint",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def test_package_exports_s7_concept_surface() -> None:
    assert relay_self.ConceptKey is ConceptKey
    assert relay_self.ConceptFeature is ConceptFeature
    assert relay_self.ConceptCandidate is ConceptCandidate
    assert relay_self.ConceptCriterion is ConceptCriterion
    assert relay_self.ConceptRepresentation is ConceptRepresentation
    assert relay_self.ConceptStatus is ConceptStatus
    assert relay_self.classify_concept is classify_concept
    assert relay_self.concept_candidate_from_belief is concept_candidate_from_belief
    assert relay_self.ConceptProfileId is ConceptProfileId
    assert relay_self.S7_CONCEPT_PROFILES is S7_CONCEPT_PROFILES
    assert relay_self.s7_concept_profile is s7_concept_profile


def test_s7_profiles_are_exactly_cnc_blf_cnc_and_att_blf_cnc() -> None:
    assert [profile.profile_id for profile in S7_CONCEPT_PROFILES] == [
        ConceptProfileId.CNC,
        ConceptProfileId.BLF_CNC,
        ConceptProfileId.ATT_BLF_CNC,
    ]
    assert s7_concept_profile(
        ConceptProfileId.CNC
    ).enabled_ids == frozenset({"CNC"})
    assert s7_concept_profile(
        ConceptProfileId.BLF_CNC
    ).enabled_ids == frozenset({"BLF", "CNC"})
    assert s7_concept_profile(
        ConceptProfileId.ATT_BLF_CNC
    ).enabled_ids == frozenset({"ATT", "BLF", "CNC"})


def test_cnc_descriptor_is_stateless_read_only_cognitive_orientation() -> None:
    assert S7_CNC_CAPABILITY_SPEC.state_scopes == ()
    assert S7_CNC_CAPABILITY_SPEC.dependencies == ()
    assert S7_CNC_OPERATOR_DESCRIPTOR.operator_id == "cnc.classify"
    assert S7_CNC_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S7_CNC_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert (
        S7_CNC_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.concept.classify_concept"
    )
    assert (
        S7_CNC_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert (
        S7_CNC_CRITERION_DESCRIPTOR.criterion_id
        == "cnc.explicit_membership_orientation"
    )
    assert all(
        descriptor.kind is CriterionKind.CONTRACT_GUARD
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )


@pytest.mark.parametrize(
    ("candidate", "expected", "missing", "mismatched"),
    [
        (
            zombie_candidate(),
            ConceptStatus.MATCHED,
            (),
            (),
        ),
        (
            ConceptCandidate(
                candidate_id="entity:cow-1",
                payload_ref="present:entity:cow-1",
                features=(
                    ConceptFeature("hostile", False),
                    ConceptFeature("alive", True),
                ),
                provenance=provenance("candidate:cow-1"),
            ),
            ConceptStatus.NOT_MATCHED,
            (),
            ("hostile",),
        ),
        (
            ConceptCandidate(
                candidate_id="entity:unknown-1",
                payload_ref="present:entity:unknown-1",
                features=(ConceptFeature("alive", True),),
                provenance=provenance("candidate:unknown-1"),
            ),
            ConceptStatus.UNDETERMINED,
            ("hostile",),
            (),
        ),
    ],
)
def test_explicit_membership_rule_has_three_deterministic_statuses(
    candidate: ConceptCandidate,
    expected: ConceptStatus,
    missing: tuple[str, ...],
    mismatched: tuple[str, ...],
) -> None:
    criterion = hostile_criterion()

    first = classify_concept(candidate, criterion)
    second = classify_concept(candidate, criterion)

    assert first == second
    assert first.status is expected
    assert first.source is candidate
    assert first.criterion is criterion
    assert first.missing_feature_keys == missing
    assert first.mismatched_feature_keys == mismatched


def test_explicit_mismatch_dominates_missing_without_fabricating_a_match() -> None:
    candidate = ConceptCandidate(
        candidate_id="entity:partial-cow",
        payload_ref="present:entity:partial-cow",
        features=(ConceptFeature("hostile", False),),
        provenance=provenance("candidate:partial-cow"),
    )

    representation = classify_concept(candidate, hostile_criterion())

    assert representation.status is ConceptStatus.NOT_MATCHED
    assert representation.mismatched_feature_keys == ("hostile",)
    assert representation.missing_feature_keys == ("alive",)


def test_source_identity_provenance_and_supporting_feature_identity_are_preserved() -> None:
    candidate = zombie_candidate()
    representation = classify_concept(candidate, hostile_criterion())

    assert representation.source is candidate
    assert representation.candidate_id == "entity:zombie-1"
    assert representation.source.provenance == provenance("candidate:zombie-1")
    assert representation.source.source_refs == ("present:entity:zombie-1",)
    assert representation.source.source_provenance == (
        provenance("world-observation:zombie-1"),
    )
    assert representation.supporting_features[0] is candidate.features[1]
    assert representation.supporting_features[1] is candidate.features[2]


def test_concept_values_are_immutable() -> None:
    candidate = zombie_candidate()
    representation = classify_concept(candidate, hostile_criterion())

    with pytest.raises(FrozenInstanceError):
        candidate.payload_ref = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        representation.status = ConceptStatus.NOT_MATCHED  # type: ignore[misc]


def test_malformed_keys_feature_values_and_duplicate_feature_keys_fail_closed() -> None:
    with pytest.raises(InvalidConceptData, match="structured token"):
        ConceptKey(domain="entity class", name="hostile_mob")

    with pytest.raises(InvalidConceptData, match="must not contain ':'"):
        ConceptKey(domain="entity", name="hostile:mob")

    with pytest.raises(InvalidConceptData, match="feature value"):
        ConceptFeature("hostile", ["yes"])  # type: ignore[arg-type]

    with pytest.raises(InvalidConceptData, match="feature keys must be unique"):
        ConceptCandidate(
            candidate_id="duplicate-features",
            payload_ref="present:duplicate",
            features=(
                ConceptFeature("hostile", True),
                ConceptFeature("hostile", False),
            ),
            provenance=provenance("duplicate-features"),
        )

    with pytest.raises(InvalidConceptData, match="feature keys must be unique"):
        ConceptCriterion(
            criterion_id="duplicate-requirements",
            concept=hostile_mob(),
            required_features=(
                ConceptFeature("alive", True),
                ConceptFeature("alive", False),
            ),
        )


def test_unsupported_input_type_and_provider_text_do_not_become_concepts() -> None:
    generated = ProviderExpression(
        text="That is a dangerous enemy.",
        provenance=provenance("provider-expression"),
    )

    with pytest.raises(InvalidConceptData, match="ConceptCandidate"):
        classify_concept(generated, hostile_criterion())  # type: ignore[arg-type]

    with pytest.raises(ConceptSourceUnavailable, match="BeliefAssessment"):
        concept_candidate_from_belief(
            generated,
            candidate_id="provider-text",
            payload_ref="provider:expression",
            provenance=provenance("provider-projection"),
        )


def test_cnc_on_executes_real_classification_with_zero_cognition_calls() -> None:
    box: dict[str, ConceptRepresentation] = {}
    candidate = zombie_candidate()
    criterion = hostile_criterion()

    def classify() -> None:
        box["concept"] = classify_concept(candidate, criterion)

    binding = EpochBinding("cnc-1", "cnc.classify", classify)
    plan = compile_epoch_plan(
        s7_concept_profile(ConceptProfileId.CNC).plan(),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "cnc-1",
                "cnc.classify",
                "structured-entity-candidate",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-cnc"),
    )

    assert box["concept"].status is ConceptStatus.MATCHED
    assert box["concept"].concept == hostile_mob()
    assert result.executed_work_ids == ("cnc-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_cnc_off_suppresses_only_cnc_while_blf_still_executes() -> None:
    box: dict[str, object] = {}
    p = proposition_p()

    def assess() -> None:
        box["belief"] = assess_belief(
            (
                belief_evidence(
                    "E1",
                    proposition=p,
                    relation=EvidenceRelation.SUPPORT,
                ),
            ),
            BeliefCriterion("ridge-safety", p),
        )

    binding = EpochBinding("blf-1", "blf.assess", assess)
    plan = compile_epoch_plan(
        s7_capability_plan(enabled_ids=frozenset({"BLF"})),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("blf-1", "blf.assess", "qualified-evidence"),
            EpochWorkItem("cnc-1", "cnc.classify", "concept-disabled"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-cnc-off"),
    )

    assert result.executed_work_ids == ("blf-1",)
    assert result.suppressed_work_ids == ("cnc-1",)
    assert isinstance(box["belief"], BeliefAssessment)
    assert box["belief"].status is BeliefStatus.SUPPORTED
    assert "concept" not in box
    assert result.cognition_requested is False


def test_blf_cnc_classifies_belief_without_changing_epistemic_status() -> None:
    box: dict[str, object] = {}
    p = proposition_p()

    def assess() -> None:
        box["belief"] = assess_belief(
            (
                belief_evidence(
                    "E1",
                    proposition=p,
                    relation=EvidenceRelation.SUPPORT,
                ),
                belief_evidence(
                    "E2",
                    proposition=p,
                    relation=EvidenceRelation.OPPOSE,
                ),
            ),
            BeliefCriterion("ridge-safety", p),
        )

    def classify_belief() -> None:
        assessment = box.get("belief")
        candidate = concept_candidate_from_belief(
            assessment,
            candidate_id="belief:ridge-safety",
            payload_ref="transient:belief:ridge-safety",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            candidate,
            contested_criterion(),
        )

    bindings = (
        EpochBinding("blf-1", "blf.assess", assess),
        EpochBinding("cnc-1", "cnc.classify", classify_belief),
    )
    plan = compile_epoch_plan(
        s7_concept_profile(ConceptProfileId.BLF_CNC).plan(),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("blf-1", "blf.assess", "qualified-evidence"),
            EpochWorkItem("cnc-1", "cnc.classify", "structured-belief"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-blf-cnc"),
    )

    belief = box["belief"]
    concept = box["concept"]
    assert isinstance(belief, BeliefAssessment)
    assert isinstance(concept, ConceptRepresentation)
    assert belief.status is BeliefStatus.CONFLICTED
    assert concept.status is ConceptStatus.MATCHED
    assert concept.concept == contested_claim()
    assert concept.source.features[1] == ConceptFeature(
        "belief_status",
        "conflicted",
    )
    assert belief.status is BeliefStatus.CONFLICTED
    assert result.executed_work_ids == ("blf-1", "cnc-1")
    assert result.cognition_requested is False


def test_blf_dependent_cnc_fails_closed_without_belief_assessment() -> None:
    box: dict[str, object] = {}

    def classify_belief() -> None:
        candidate = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:missing",
            payload_ref="transient:belief:missing",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            candidate,
            contested_criterion(),
        )

    binding = EpochBinding("cnc-1", "cnc.classify", classify_belief)
    plan = compile_epoch_plan(
        s7_capability_plan(enabled_ids=frozenset({"CNC"})),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "cnc-1",
                "cnc.classify",
                "explicit-blf-dependent-concept",
            ),
        ),
        bindings=(binding,),
    )

    with pytest.raises(ConceptSourceUnavailable):
        coordinate_planned_epoch(
            ActionSupervisor(),
            plan,
            bindings=(binding,),
            at_ns=10,
            provenance=provenance("epoch-missing-belief"),
        )

    assert "concept" not in box


def test_att_blf_cnc_forms_zero_call_deterministic_processing_chain() -> None:
    p = proposition_p()
    q = proposition_q()
    evidence_by_id = {
        "E1": belief_evidence(
            "E1",
            proposition=p,
            relation=EvidenceRelation.SUPPORT,
        ),
        "E2": belief_evidence(
            "E2",
            proposition=p,
            relation=EvidenceRelation.OPPOSE,
        ),
        "E3": belief_evidence(
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
            focus_keys=("belief:P",),
        ),
        AttentionCandidate(
            "E2",
            "belief-evidence:E2",
            provenance("attention:E2"),
            priority=1,
            focus_keys=("belief:P",),
        ),
        AttentionCandidate(
            "E3",
            "belief-evidence:E3",
            provenance("attention:E3"),
            priority=9,
            focus_keys=("belief:Q",),
        ),
    )
    original_candidates = source_candidates
    box: dict[str, object] = {}
    calls = {"ATT": 0, "BLF": 0, "CNC": 0}

    def attend() -> None:
        calls["ATT"] += 1
        box["selection"] = select_attention(
            source_candidates,
            AttentionCriterion(
                criterion_id="focus-P",
                focus_key="belief:P",
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
            BeliefCriterion("ridge-safety", p),
        )

    def classify_belief() -> None:
        calls["CNC"] += 1
        candidate = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:ridge-safety",
            payload_ref="transient:belief:ridge-safety",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            candidate,
            contested_criterion(),
        )

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", assess_selected),
        EpochBinding("cnc-1", "cnc.classify", classify_belief),
    )
    plan = compile_epoch_plan(
        s7_concept_profile(ConceptProfileId.ATT_BLF_CNC).plan(),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "candidate-evidence"),
            EpochWorkItem("blf-1", "blf.assess", "att-selected-evidence"),
            EpochWorkItem("cnc-1", "cnc.classify", "structured-belief"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-att-blf-cnc"),
    )

    selection = box["selection"]
    belief = box["belief"]
    concept = box["concept"]
    assert isinstance(selection, AttentionSelection)
    assert isinstance(belief, BeliefAssessment)
    assert isinstance(concept, ConceptRepresentation)
    assert selection.candidate_ids == ("E1", "E2")
    assert belief.evidence_ids == ("E1", "E2")
    assert "E3" not in belief.evidence_ids
    assert belief.status is BeliefStatus.CONFLICTED
    assert concept.status is ConceptStatus.MATCHED
    assert concept.concept == contested_claim()
    assert concept.source.features[1].value == "conflicted"
    assert belief.status is BeliefStatus.CONFLICTED
    assert source_candidates == original_candidates
    assert calls == {"ATT": 1, "BLF": 1, "CNC": 1}
    assert result.executed_work_ids == ("att-1", "blf-1", "cnc-1")
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_att_blf_cnc_fails_closed_if_required_attention_result_is_absent() -> None:
    box: dict[str, object] = {}
    p = proposition_p()

    def assess_selected() -> None:
        selection = require_attention_selection(box.get("selection"))
        admitted = tuple(
            belief_evidence(
                candidate.candidate_id,
                proposition=p,
                relation=EvidenceRelation.SUPPORT,
            )
            for candidate in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("ridge-safety", p),
        )

    def classify_belief() -> None:
        candidate = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:ridge-safety",
            payload_ref="transient:belief:ridge-safety",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(candidate, contested_criterion())

    bindings = (
        EpochBinding("blf-1", "blf.assess", assess_selected),
        EpochBinding("cnc-1", "cnc.classify", classify_belief),
    )
    plan = compile_epoch_plan(
        s7_capability_plan(enabled_ids=frozenset({"BLF", "CNC"})),
        S7_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "disabled"),
            EpochWorkItem(
                "blf-1",
                "blf.assess",
                "explicit-attention-dependent-belief",
            ),
            EpochWorkItem("cnc-1", "cnc.classify", "structured-belief"),
        ),
        bindings=bindings,
    )

    assert plan.suppressed == (
        EpochWorkItem("att-1", "att.select", "disabled"),
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
    assert "concept" not in box


def test_cnc_does_not_mutate_memory_intent_skill_action_belief_or_attention() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s7",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-s7",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action"),
    )
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )
    belief = conflicted_belief()
    attention_source = (
        AttentionCandidate(
            "belief-1",
            "transient:belief:ridge-safety",
            provenance("attention:belief-1"),
            focus_keys=("concept",),
        ),
    )
    selection = select_attention(
        attention_source,
        AttentionCriterion("concept-focus", focus_key="concept"),
    )

    before_intent_events = intent_owner.events
    before_skill_events = skill.events
    before_action_events = action.events
    before_memories = cognition.memories
    before_belief = belief
    before_selection = selection

    candidate = concept_candidate_from_belief(
        belief,
        candidate_id="belief:ridge-safety",
        payload_ref="transient:belief:ridge-safety",
        provenance=provenance("belief-to-concept"),
    )
    representation = classify_concept(candidate, contested_criterion())

    assert representation.status is ConceptStatus.MATCHED
    assert cognition.memories == before_memories
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s7"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert action.events == before_action_events
    assert action.state is ActionState.PROPOSED
    assert belief == before_belief
    assert belief.status is BeliefStatus.CONFLICTED
    assert selection == before_selection
    assert selection.candidate_ids == ("belief-1",)
