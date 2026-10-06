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
    BeliefPropositionMismatch,
    BeliefStatus,
    EvidenceRelation,
    InvalidBeliefData,
    PropositionKey,
    assess_belief,
)
from relay_self.belief_profile import (
    S6_BELIEF_PROFILES,
    BeliefProfileId,
    s6_belief_profile,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    S6_BLF_CAPABILITY_SPEC,
    S6_BLF_CRITERION_DESCRIPTOR,
    S6_BLF_OPERATOR_DESCRIPTOR,
    S6_DESCRIPTOR_SET,
    CriterionKind,
    OperatorEffect,
    s6_capability_plan,
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
    return Provenance(source="s6-belief-qualification", reference=reference)


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


def support_p(evidence_id: str = "E1") -> BeliefEvidence:
    return evidence(
        evidence_id,
        proposition=proposition_p(),
        relation=EvidenceRelation.SUPPORT,
    )


def oppose_p(evidence_id: str = "E2") -> BeliefEvidence:
    return evidence(
        evidence_id,
        proposition=proposition_p(),
        relation=EvidenceRelation.OPPOSE,
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s6",
        directives=("preserve evidence-belief-truth boundaries",),
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
        "intent-s6",
        objective="reach the safe waypoint",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def test_package_exports_s6_belief_surface() -> None:
    assert relay_self.PropositionKey is PropositionKey
    assert relay_self.BeliefEvidence is BeliefEvidence
    assert relay_self.BeliefCriterion is BeliefCriterion
    assert relay_self.BeliefAssessment is BeliefAssessment
    assert relay_self.BeliefStatus is BeliefStatus
    assert relay_self.EvidenceRelation is EvidenceRelation
    assert relay_self.assess_belief is assess_belief
    assert relay_self.BeliefProfileId is BeliefProfileId
    assert relay_self.S6_BELIEF_PROFILES is S6_BELIEF_PROFILES
    assert relay_self.s6_belief_profile is s6_belief_profile


def test_s6_profiles_are_exactly_blf_and_att_blf() -> None:
    assert [profile.profile_id for profile in S6_BELIEF_PROFILES] == [
        BeliefProfileId.BLF,
        BeliefProfileId.ATT_BLF,
    ]
    assert s6_belief_profile(
        BeliefProfileId.BLF
    ).enabled_ids == frozenset({"BLF"})
    assert s6_belief_profile(
        BeliefProfileId.ATT_BLF
    ).enabled_ids == frozenset({"ATT", "BLF"})


def test_blf_descriptor_is_stateless_read_only_cognitive_orientation() -> None:
    assert S6_BLF_CAPABILITY_SPEC.state_scopes == ()
    assert S6_BLF_CAPABILITY_SPEC.dependencies == ()
    assert S6_BLF_OPERATOR_DESCRIPTOR.operator_id == "blf.assess"
    assert S6_BLF_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S6_BLF_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert (
        S6_BLF_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.belief.assess_belief"
    )
    assert (
        S6_BLF_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert (
        S6_BLF_CRITERION_DESCRIPTOR.criterion_id
        == "blf.evidence_support_orientation"
    )
    assert all(
        descriptor.kind is CriterionKind.CONTRACT_GUARD
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )


@pytest.mark.parametrize(
    ("admitted", "expected"),
    [
        ((support_p(),), BeliefStatus.SUPPORTED),
        ((oppose_p(),), BeliefStatus.UNSUPPORTED),
        ((support_p(), oppose_p()), BeliefStatus.CONFLICTED),
        ((), BeliefStatus.UNDETERMINED),
    ],
)
def test_belief_status_rule_is_explicit_and_deterministic(
    admitted: tuple[BeliefEvidence, ...],
    expected: BeliefStatus,
) -> None:
    criterion = BeliefCriterion("ridge-safety", proposition_p())

    first = assess_belief(admitted, criterion)
    second = assess_belief(admitted, criterion)

    assert first == second
    assert first.status is expected
    assert first.evidence == admitted


def test_conflict_is_not_erased_by_evidence_order() -> None:
    criterion = BeliefCriterion("ridge-safety", proposition_p())

    forward = assess_belief(
        (support_p("support"), oppose_p("oppose")),
        criterion,
    )
    reverse = assess_belief(
        (oppose_p("oppose"), support_p("support")),
        criterion,
    )

    assert forward.status is BeliefStatus.CONFLICTED
    assert reverse.status is BeliefStatus.CONFLICTED
    assert forward.evidence_ids == ("support", "oppose")
    assert reverse.evidence_ids == ("oppose", "support")


def test_evidence_identity_and_provenance_are_preserved() -> None:
    source = support_p()
    assessment = assess_belief(
        (source,),
        BeliefCriterion("ridge-safety", proposition_p()),
    )

    assert assessment.evidence[0] is source
    assert assessment.evidence[0].provenance == provenance("evidence:E1")
    assert assessment.evidence_ids == ("E1",)


def test_structured_proposition_identity_rejects_free_text_shape() -> None:
    with pytest.raises(InvalidBeliefData, match="structured token"):
        PropositionKey(
            domain="route",
            subject="the ridge",
            predicate="safe",
        )

    with pytest.raises(InvalidBeliefData, match="must not contain ':'"):
        PropositionKey(
            domain="route",
            subject="ridge",
            predicate="safe:probably",
        )


def test_duplicate_and_mismatched_evidence_fail_closed() -> None:
    criterion = BeliefCriterion("ridge-safety", proposition_p())
    duplicate = support_p("same")

    with pytest.raises(InvalidBeliefData, match="evidence_id values must be unique"):
        assess_belief((duplicate, duplicate), criterion)

    unrelated = evidence(
        "Q1",
        proposition=proposition_q(),
        relation=EvidenceRelation.SUPPORT,
    )
    with pytest.raises(BeliefPropositionMismatch, match="different proposition"):
        assess_belief((support_p(), unrelated), criterion)


def test_assessment_values_are_immutable() -> None:
    assessment = assess_belief(
        (support_p(),),
        BeliefCriterion("ridge-safety", proposition_p()),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.status = BeliefStatus.UNSUPPORTED  # type: ignore[misc]


def test_blf_on_executes_real_assessment_with_zero_cognition_calls() -> None:
    box: dict[str, BeliefAssessment] = {}
    criterion = BeliefCriterion("ridge-safety", proposition_p())

    def assess() -> None:
        box["belief"] = assess_belief(
            (support_p(), oppose_p()),
            criterion,
        )

    binding = EpochBinding("blf-1", "blf.assess", assess)
    plan = compile_epoch_plan(
        s6_belief_profile(BeliefProfileId.BLF).plan(),
        S6_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "blf-1",
                "blf.assess",
                "qualified-ridge-evidence",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-blf"),
    )

    assert box["belief"].status is BeliefStatus.CONFLICTED
    assert result.executed_work_ids == ("blf-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_blf_off_suppresses_only_blf_and_leaves_unrelated_mem_route_available() -> None:
    cognition_box = {
        "cognition": PersistentCognition(
            identity=identity(),
            memories=(memory("existing"),),
        )
    }
    new_memory = memory("new-memory")
    assessment_box: dict[str, BeliefAssessment] = {}

    def retain() -> None:
        cognition_box["cognition"] = cognition_box["cognition"].retain_memory(
            new_memory
        )

    binding = EpochBinding("mem-1", "mem.retain", retain)
    plan = compile_epoch_plan(
        s6_capability_plan(enabled_ids=frozenset({"MEM"})),
        S6_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("blf-1", "blf.assess", "belief-disabled"),
            EpochWorkItem("mem-1", "mem.retain", "explicit-retention"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-blf-off"),
    )

    assert result.suppressed_work_ids == ("blf-1",)
    assert result.executed_work_ids == ("mem-1",)
    assert assessment_box == {}
    assert [item.memory_id for item in cognition_box["cognition"].memories] == [
        "existing",
        "new-memory",
    ]
    assert result.cognition_requested is False


def test_blf_does_not_mutate_memory_intent_skill_or_action_authority() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s6",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-s6",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action"),
    )
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )

    before_intent_events = intent_owner.events
    before_skill_events = skill.events
    before_action_events = action.events
    before_memories = cognition.memories

    assessment = assess_belief(
        (support_p(),),
        BeliefCriterion("ridge-safety", proposition_p()),
    )

    assert assessment.status is BeliefStatus.SUPPORTED
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s6"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert action.events == before_action_events
    assert action.state is ActionState.PROPOSED
    assert cognition.memories == before_memories


def test_provider_expression_is_not_belief_evidence_or_automatic_belief() -> None:
    generated = ProviderExpression(
        text="The ridge is safe.",
        provenance=provenance("provider-expression"),
    )
    criterion = BeliefCriterion("ridge-safety", proposition_p())

    with pytest.raises(InvalidBeliefData, match="BeliefEvidence"):
        assess_belief((generated,), criterion)  # type: ignore[arg-type]


def test_att_blf_profile_filters_evidence_then_assesses_only_selected_proposition() -> None:
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
            relation=EvidenceRelation.OPPOSE,
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
    box: dict[str, object] = {}
    calls = {"attention": 0, "belief": 0}

    def attend() -> None:
        calls["attention"] += 1
        box["selection"] = select_attention(
            source_candidates,
            AttentionCriterion(
                criterion_id="focus-P",
                focus_key="belief:P",
            ),
        )

    def assess_selected() -> None:
        calls["belief"] += 1
        selection = require_attention_selection(box.get("selection"))
        admitted = tuple(
            evidence_by_id[candidate.candidate_id]
            for candidate in selection.selected
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("ridge-safety", p),
        )

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", assess_selected),
    )
    plan = compile_epoch_plan(
        s6_belief_profile(BeliefProfileId.ATT_BLF).plan(),
        S6_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "candidate-evidence"),
            EpochWorkItem("blf-1", "blf.assess", "att-selected-evidence"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-att-blf"),
    )

    selection = box["selection"]
    belief = box["belief"]
    assert isinstance(selection, AttentionSelection)
    assert isinstance(belief, BeliefAssessment)
    assert selection.candidate_ids == ("E1", "E2")
    assert belief.evidence_ids == ("E1", "E2")
    assert belief.status is BeliefStatus.CONFLICTED
    assert "E3" not in belief.evidence_ids
    assert calls == {"attention": 1, "belief": 1}
    assert result.executed_work_ids == ("att-1", "blf-1")
    assert result.cognition_requested is False


def test_att_dependent_blf_fails_closed_when_att_is_off_without_evidence_fallback() -> None:
    full = s6_belief_profile(BeliefProfileId.ATT_BLF).plan()
    blf_only = full.with_enabled("ATT", enabled=False)
    box: dict[str, object] = {}
    full_evidence = (support_p(), oppose_p())

    def assess_selected() -> None:
        selection = require_attention_selection(box.get("selection"))
        admitted_ids = selection.candidate_ids
        admitted = tuple(
            item
            for item in full_evidence
            if item.evidence_id in admitted_ids
        )
        box["belief"] = assess_belief(
            admitted,
            BeliefCriterion("ridge-safety", proposition_p()),
        )

    binding = EpochBinding("blf-1", "blf.assess", assess_selected)
    plan = compile_epoch_plan(
        blf_only,
        S6_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "disabled"),
            EpochWorkItem(
                "blf-1",
                "blf.assess",
                "explicit-attention-dependent-belief",
            ),
        ),
        bindings=(binding,),
    )

    assert plan.suppressed == (
        EpochWorkItem("att-1", "att.select", "disabled"),
    )

    with pytest.raises(AttentionSelectionUnavailable):
        coordinate_planned_epoch(
            ActionSupervisor(),
            plan,
            bindings=(binding,),
            at_ns=10,
            provenance=provenance("epoch-att-dependent-blf-off"),
        )

    assert "belief" not in box
