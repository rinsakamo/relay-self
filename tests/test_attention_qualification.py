from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    AttentionSelection,
    AttentionSelectionUnavailable,
    InvalidAttentionData,
    require_attention_selection,
    select_attention,
)
from relay_self.attention_profile import (
    S5_ATTENTION_PROFILES,
    AttentionProfileId,
    s5_attention_profile,
)
from relay_self.epoch_plan import (
    CognitionInvocation,
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    S5_ATT_CAPABILITY_SPEC,
    S5_DESCRIPTOR_SET,
    CriterionKind,
    OperatorEffect,
    s5_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s5-attention-qualification", reference=reference)


def candidates() -> tuple[AttentionCandidate, ...]:
    return (
        AttentionCandidate(
            candidate_id="A",
            payload_ref="present:item:A",
            provenance=provenance("candidate:A"),
            priority=2,
            focus_keys=("threat",),
        ),
        AttentionCandidate(
            candidate_id="B",
            payload_ref="present:item:B",
            provenance=provenance("candidate:B"),
            priority=5,
            focus_keys=("navigation",),
        ),
        AttentionCandidate(
            candidate_id="C",
            payload_ref="present:item:C",
            provenance=provenance("candidate:C"),
            priority=1,
            focus_keys=("threat",),
        ),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s5",
        directives=("preserve explicit ownership boundaries",),
        provenance=provenance("identity"),
    )


def memory(memory_id: str) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=f"memory:{memory_id}",
        source_provenance=provenance(f"source:{memory_id}"),
        integration_provenance=provenance(f"integration:{memory_id}"),
    )


def committed_intent() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-s5",
        objective="reach the safe waypoint",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


@dataclass
class RecordingProvider:
    bounded_choice: str = "wait"

    def __post_init__(self) -> None:
        self.calls: list[tuple[object, CognitionMode]] = []

    def __call__(
        self,
        request: BoundedChoiceRequest | OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision | ProviderExpression:
        self.calls.append((request, mode))
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                text="Attention-gated transient expression.",
                provenance=provenance("open-provider"),
            )
        return ProviderDecision.resolved(
            self.bounded_choice,
            reason="fixture resolved",
        )


def open_request_from_selection(
    selection: AttentionSelection,
) -> OpenCognitionRequest:
    admitted = require_attention_selection(selection)
    return OpenCognitionRequest(
        request_id="open-s5-att-1",
        instruction="Describe only the explicitly attended context.",
        intent_id=None,
        focus="TALK",
        context=tuple(
            CognitionDatum.from_value(
                candidate.candidate_id,
                {"payload_ref": candidate.payload_ref},
                candidate.provenance,
            )
            for candidate in admitted.selected
        ),
    )


def bounded_request() -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id="bounded-s5-1",
        instruction="Choose one admitted control candidate.",
        intent_id=None,
        focus="CTL",
        choices=(
            BoundedChoice(choice_id="wait", description="Wait"),
            BoundedChoice(choice_id="flee", description="Flee"),
        ),
        context=(),
        think_allowed=False,
    )


def test_package_exports_s5_attention_surface() -> None:
    assert relay_self.AttentionCandidate is AttentionCandidate
    assert relay_self.AttentionCriterion is AttentionCriterion
    assert relay_self.AttentionSelection is AttentionSelection
    assert relay_self.select_attention is select_attention
    assert relay_self.AttentionProfileId is AttentionProfileId
    assert relay_self.S5_ATTENTION_PROFILES is S5_ATTENTION_PROFILES
    assert relay_self.s5_attention_profile is s5_attention_profile


def test_s5_profiles_are_exactly_att_and_att_talk() -> None:
    assert [profile.profile_id for profile in S5_ATTENTION_PROFILES] == [
        AttentionProfileId.ATT,
        AttentionProfileId.ATT_TALK,
    ]
    assert s5_attention_profile(
        AttentionProfileId.ATT
    ).enabled_ids == frozenset({"ATT"})
    assert s5_attention_profile(
        AttentionProfileId.ATT_TALK
    ).enabled_ids == frozenset({"ATT", "TALK"})


def test_attention_criterion_is_real_cognitive_orientation_not_contract_guard() -> None:
    descriptor = next(
        value
        for value in S5_DESCRIPTOR_SET.criteria
        if value.criterion_id == "att.explicit_orientation"
    )
    operator = next(
        value
        for value in S5_DESCRIPTOR_SET.operators
        if value.operator_id == "att.select"
    )

    assert descriptor.kind is CriterionKind.COGNITIVE_ORIENTATION
    assert descriptor.implementation_ref == "relay_self.attention.select_attention"
    assert all(
        value.kind is CriterionKind.CONTRACT_GUARD
        for value in S2_DESCRIPTOR_SET.criteria
    )
    assert operator.effect is OperatorEffect.READ_ONLY
    assert operator.hidden_persistent_state is False
    assert S5_ATT_CAPABILITY_SPEC.state_scopes == ()
    assert S5_ATT_CAPABILITY_SPEC.dependencies == ()


def test_attention_is_deterministic_and_preserves_identity_provenance_and_source_order() -> None:
    source = candidates()
    criterion = AttentionCriterion(
        criterion_id="priority-top-2",
        top_k=2,
    )

    first = select_attention(source, criterion)
    second = select_attention(source, criterion)

    assert first == second
    assert first.candidate_ids == ("B", "A")
    assert first.selected[0] is source[1]
    assert first.selected[1] is source[0]
    assert first.selected[0].provenance == provenance("candidate:B")
    assert source == candidates()

    tied = (
        AttentionCandidate(
            "X",
            "present:item:X",
            provenance("candidate:X"),
            priority=3,
        ),
        AttentionCandidate(
            "Y",
            "present:item:Y",
            provenance("candidate:Y"),
            priority=3,
        ),
    )
    assert select_attention(
        tied,
        AttentionCriterion("stable-tie"),
    ).candidate_ids == ("X", "Y")


def test_attention_can_filter_explicit_focus_without_free_text_inference() -> None:
    selection = select_attention(
        candidates(),
        AttentionCriterion(
            criterion_id="threat-focus",
            focus_key="threat",
        ),
    )

    assert selection.candidate_ids == ("A", "C")


def test_attention_candidate_rejects_mutable_payload_ownership() -> None:
    with pytest.raises(InvalidAttentionData, match="payload_ref"):
        AttentionCandidate(
            candidate_id="bad",
            payload_ref={"mutable": True},  # type: ignore[arg-type]
            provenance=provenance("bad"),
        )


def test_attention_values_are_immutable() -> None:
    candidate = candidates()[0]
    selection = select_attention(
        (candidate,),
        AttentionCriterion("immutable"),
    )

    with pytest.raises(FrozenInstanceError):
        candidate.priority = 99  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        selection.considered_count = 99  # type: ignore[misc]


def test_att_on_executes_real_selection_with_zero_cognition_calls() -> None:
    box: dict[str, AttentionSelection] = {}
    criterion = AttentionCriterion("priority-top-2", top_k=2)

    def attend() -> None:
        box["selection"] = select_attention(candidates(), criterion)

    binding = EpochBinding("att-1", "att.select", attend)
    plan = compile_epoch_plan(
        s5_attention_profile(AttentionProfileId.ATT).plan(),
        S5_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "structured-candidates"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-att"),
    )

    assert box["selection"].candidate_ids == ("B", "A")
    assert result.executed_work_ids == ("att-1",)
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_attention_does_not_mutate_intent_skill_action_or_persistent_cognition() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s5",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    action = ActionLifecycle.propose(
        "action-s5",
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

    selection = select_attention(
        candidates(),
        AttentionCriterion("threat-focus", focus_key="threat"),
    )

    assert selection.candidate_ids == ("A", "C")
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s5"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert action.events == before_action_events
    assert action.state is ActionState.PROPOSED
    assert cognition.memories == before_memories


def test_att_off_suppresses_only_att_while_mem_and_talk_remain_available() -> None:
    cognition_box = {
        "cognition": PersistentCognition(
            identity=identity(),
            memories=(memory("existing"),),
        )
    }
    candidate_memory = memory("new-memory")
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = OpenCognitionRequest(
        request_id="open-independent",
        instruction="Generate an unrelated transient expression.",
        intent_id=None,
        focus="TALK",
        context=(),
    )

    def retain() -> None:
        cognition_box["cognition"] = cognition_box["cognition"].retain_memory(
            candidate_memory
        )

    bindings = (
        EpochBinding("mem-1", "mem.retain", retain),
        EpochBinding(
            "talk-1",
            "talk.open_cognition",
            lambda: CognitionInvocation(request=request, runner=engine.open),
        ),
    )
    plan = compile_epoch_plan(
        s5_capability_plan(enabled_ids=frozenset({"MEM", "TALK"})),
        S5_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "not-enabled"),
            EpochWorkItem("mem-1", "mem.retain", "retention"),
            EpochWorkItem("talk-1", "talk.open_cognition", "independent-talk"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-att-off-mem-talk"),
    )

    assert result.suppressed_work_ids == ("att-1",)
    assert result.executed_work_ids == ("mem-1", "talk-1")
    assert [item.memory_id for item in cognition_box["cognition"].memories] == [
        "existing",
        "new-memory",
    ]
    assert provider.calls == [(request, CognitionMode.OPEN)]


def test_att_off_leaves_unrelated_ctl_cognition_available() -> None:
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = bounded_request()
    binding = EpochBinding(
        "ctl-1",
        "ctl.bounded_cognition",
        lambda: CognitionInvocation(request=request, runner=engine),
    )
    plan = compile_epoch_plan(
        s5_capability_plan(enabled_ids=frozenset({"CTL"})),
        S5_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "not-enabled"),
            EpochWorkItem("ctl-1", "ctl.bounded_cognition", "explicit-control"),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-att-off-ctl"),
    )

    assert result.suppressed_work_ids == ("att-1",)
    assert result.executed_work_ids == ("ctl-1",)
    assert provider.calls == [(request, CognitionMode.BOUNDED)]
    assert result.cognition_result is not None
    assert result.cognition_result.provider_call_count == 1


def test_att_talk_profile_gates_context_then_makes_exactly_one_downstream_call() -> None:
    box: dict[str, AttentionSelection] = {}
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    criterion = AttentionCriterion("priority-top-2", top_k=2)

    def attend() -> None:
        assert provider.calls == []
        box["selection"] = select_attention(candidates(), criterion)

    def talk() -> CognitionInvocation:
        selection = require_attention_selection(box.get("selection"))
        request = open_request_from_selection(selection)
        return CognitionInvocation(request=request, runner=engine.open)

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("talk-1", "talk.open_cognition", talk),
    )
    plan = compile_epoch_plan(
        s5_attention_profile(AttentionProfileId.ATT_TALK).plan(),
        S5_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "structured-candidates"),
            EpochWorkItem(
                "talk-1",
                "talk.open_cognition",
                "explicit-attention-dependent-talk",
            ),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-att-talk"),
    )

    assert box["selection"].candidate_ids == ("B", "A")
    assert len(provider.calls) == 1
    request, mode = provider.calls[0]
    assert isinstance(request, OpenCognitionRequest)
    assert mode is CognitionMode.OPEN
    assert [datum.key for datum in request.context] == ["B", "A"]
    assert result.executed_work_ids == ("att-1", "talk-1")
    assert result.cognition_result is not None
    assert result.cognition_result.provider_call_count == 1


def test_att_dependent_talk_fails_closed_when_att_is_off_without_full_set_fallback() -> None:
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    full = s5_attention_profile(AttentionProfileId.ATT_TALK).plan()
    talk_only = full.with_enabled("ATT", enabled=False)
    box: dict[str, AttentionSelection] = {}

    def talk() -> CognitionInvocation:
        selection = require_attention_selection(box.get("selection"))
        request = open_request_from_selection(selection)
        return CognitionInvocation(request=request, runner=engine.open)

    binding = EpochBinding("talk-1", "talk.open_cognition", talk)
    plan = compile_epoch_plan(
        talk_only,
        S5_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "disabled"),
            EpochWorkItem(
                "talk-1",
                "talk.open_cognition",
                "explicit-attention-dependent-talk",
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
            provenance=provenance("epoch-att-dependent-talk-off"),
        )

    assert provider.calls == []
