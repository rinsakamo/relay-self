from __future__ import annotations

from dataclasses import dataclass

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.capability_profile import (
    S4_PROFILES,
    CapabilityProfileId,
    s4_capability_profile,
)
from relay_self.epoch_plan import (
    CognitionInvocation,
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import S2_DESCRIPTOR_SET
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
    CognitionMode,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s4-profile-qualification", reference=reference)


@dataclass
class RecordingProvider:
    bounded_choice: str = "flee"

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
                text="Transient qualified expression.",
                provenance=provenance("open-provider"),
            )
        return ProviderDecision.resolved(
            self.bounded_choice,
            reason="fixture resolved",
        )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s4",
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


def bounded_request() -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id="bounded-s4-1",
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


def open_request() -> OpenCognitionRequest:
    return OpenCognitionRequest(
        request_id="open-s4-1",
        instruction="Generate one transient expression.",
        intent_id=None,
        focus="TALK",
        context=(),
    )


def committed_intent() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-s4",
        objective="reach the safe waypoint",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def test_package_exports_frozen_s4_profiles() -> None:
    assert relay_self.CapabilityProfileId is CapabilityProfileId
    assert relay_self.S4_PROFILES is S4_PROFILES
    assert relay_self.s4_capability_profile is s4_capability_profile


def test_s4_profile_set_is_exactly_the_frozen_six_profiles() -> None:
    assert [profile.profile_id for profile in S4_PROFILES] == [
        CapabilityProfileId.MEM,
        CapabilityProfileId.CTL,
        CapabilityProfileId.CTL_SKL,
        CapabilityProfileId.TALK,
        CapabilityProfileId.MEM_CTL_SKL,
        CapabilityProfileId.MEM_TALK,
    ]

    assert s4_capability_profile(
        CapabilityProfileId.CTL_SKL
    ).enabled_ids == frozenset({"CTL", "SKL"})
    assert s4_capability_profile(
        CapabilityProfileId.MEM_CTL_SKL
    ).enabled_ids == frozenset({"MEM", "CTL", "SKL"})


def test_mem_profile_qualifies_real_persistent_cognition_owner_transition() -> None:
    box = {"cognition": PersistentCognition(identity=identity())}
    candidate = memory("memory-qualified")

    def retain() -> None:
        box["cognition"] = box["cognition"].retain_memory(candidate)

    binding = EpochBinding(
        work_id="mem-1",
        operator_id="mem.retain",
        invoke=retain,
    )
    plan = compile_epoch_plan(
        s4_capability_profile(CapabilityProfileId.MEM).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="mem-1",
                operator_id="mem.retain",
                trigger_ref="governed-memory-admission",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-mem"),
    )

    assert [value.memory_id for value in box["cognition"].memories] == [
        "memory-qualified"
    ]
    assert result.executed_work_ids == ("mem-1",)
    assert result.cognition_requested is False


def test_ctl_profile_qualifies_real_bounded_relay_engine_exactly_once() -> None:
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = bounded_request()
    binding = EpochBinding(
        work_id="ctl-1",
        operator_id="ctl.bounded_cognition",
        invoke=lambda: CognitionInvocation(
            request=request,
            runner=engine,
        ),
    )
    plan = compile_epoch_plan(
        s4_capability_profile(CapabilityProfileId.CTL).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="ctl-1",
                operator_id="ctl.bounded_cognition",
                trigger_ref="explicit-unresolved-control",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-ctl"),
    )

    assert provider.calls == [(request, CognitionMode.BOUNDED)]
    assert result.cognition_requested is True
    assert result.cognition_result is not None
    assert result.cognition_result.choice_id == "flee"
    assert result.cognition_result.provider_call_count == 1


def test_ctl_skill_profile_starts_skill_and_only_proposes_action() -> None:
    intent_owner = committed_intent()
    box: dict[str, object] = {}

    def start_skill() -> None:
        box["skill"] = SkillExecution.start(
            "skill-exec-s4",
            skill_id="FLEE",
            intent_commitment=intent_owner,
            at_ns=2,
            provenance=provenance("skill-start"),
        )

    def propose_action() -> None:
        skill = box["skill"]
        assert isinstance(skill, SkillExecution)
        box["action"] = ActionLifecycle.propose(
            "action-s4",
            skill_execution=skill,
            intent_commitment=intent_owner,
            at_ns=3,
            provenance=provenance("action-proposal"),
        )

    bindings = (
        EpochBinding(
            work_id="skill-start",
            operator_id="skl.start_execution",
            invoke=start_skill,
        ),
        EpochBinding(
            work_id="action-propose",
            operator_id="skl.propose_action",
            invoke=propose_action,
        ),
    )
    plan = compile_epoch_plan(
        s4_capability_profile(CapabilityProfileId.CTL_SKL).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="skill-start",
                operator_id="skl.start_execution",
                trigger_ref="current-intent",
            ),
            EpochWorkItem(
                work_id="action-propose",
                operator_id="skl.propose_action",
                trigger_ref="started-skill",
            ),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-ctl-skl"),
    )

    skill = box["skill"]
    action = box["action"]
    assert isinstance(skill, SkillExecution)
    assert isinstance(action, ActionLifecycle)
    assert skill.state is SkillState.STARTED
    assert action.state is ActionState.PROPOSED
    assert action.intent_id == "intent-s4"
    assert action.skill_execution_id == "skill-exec-s4"
    assert result.cognition_requested is False
    assert result.executed_work_ids == ("skill-start", "action-propose")


def test_talk_profile_qualifies_real_open_relay_engine_exactly_once() -> None:
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = open_request()
    binding = EpochBinding(
        work_id="talk-1",
        operator_id="talk.open_cognition",
        invoke=lambda: CognitionInvocation(
            request=request,
            runner=engine.open,
        ),
    )
    plan = compile_epoch_plan(
        s4_capability_profile(CapabilityProfileId.TALK).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                work_id="talk-1",
                operator_id="talk.open_cognition",
                trigger_ref="explicit-expression-request",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-talk"),
    )

    assert provider.calls == [(request, CognitionMode.OPEN)]
    assert result.cognition_requested is True
    assert result.cognition_result is not None
    assert result.cognition_result.text == "Transient qualified expression."
    assert result.cognition_result.provider_call_count == 1
    assert not hasattr(result.cognition_result, "action_id")


def test_mem_ctl_skill_profile_composes_owner_transitions_without_new_authority() -> None:
    cognition_box = {"cognition": PersistentCognition(identity=identity())}
    intent_owner = committed_intent()
    box: dict[str, object] = {}
    candidate = memory("memory-composed")

    def retain() -> None:
        cognition_box["cognition"] = cognition_box["cognition"].retain_memory(
            candidate
        )

    def start_skill() -> None:
        box["skill"] = SkillExecution.start(
            "skill-exec-composed",
            skill_id="FLEE",
            intent_commitment=intent_owner,
            at_ns=2,
            provenance=provenance("skill-composed"),
        )

    def propose_action() -> None:
        skill = box["skill"]
        assert isinstance(skill, SkillExecution)
        box["action"] = ActionLifecycle.propose(
            "action-composed",
            skill_execution=skill,
            intent_commitment=intent_owner,
            at_ns=3,
            provenance=provenance("action-composed"),
        )

    bindings = (
        EpochBinding("mem-1", "mem.retain", retain),
        EpochBinding("skill-1", "skl.start_execution", start_skill),
        EpochBinding("action-1", "skl.propose_action", propose_action),
    )
    plan = compile_epoch_plan(
        s4_capability_profile(CapabilityProfileId.MEM_CTL_SKL).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("mem-1", "mem.retain", "retention"),
            EpochWorkItem("skill-1", "skl.start_execution", "current-intent"),
            EpochWorkItem("action-1", "skl.propose_action", "started-skill"),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-composed"),
    )

    assert [m.memory_id for m in cognition_box["cognition"].memories] == [
        "memory-composed"
    ]
    action = box["action"]
    assert isinstance(action, ActionLifecycle)
    assert action.state is ActionState.PROPOSED
    assert result.executed_work_ids == ("mem-1", "skill-1", "action-1")


def test_mem_talk_profile_executes_memory_then_one_open_call() -> None:
    cognition_box = {"cognition": PersistentCognition(identity=identity())}
    candidate = memory("memory-before-talk")
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = open_request()

    def retain() -> None:
        cognition_box["cognition"] = cognition_box["cognition"].retain_memory(
            candidate
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
        s4_capability_profile(CapabilityProfileId.MEM_TALK).plan(),
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("mem-1", "mem.retain", "retention"),
            EpochWorkItem(
                "talk-1",
                "talk.open_cognition",
                "explicit-expression",
            ),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-mem-talk"),
    )

    assert [m.memory_id for m in cognition_box["cognition"].memories] == [
        "memory-before-talk"
    ]
    assert provider.calls == [(request, CognitionMode.OPEN)]
    assert result.executed_work_ids == ("mem-1", "talk-1")
    assert result.cognition_result is not None
    assert result.cognition_result.provider_call_count == 1


def test_turning_mem_off_suppresses_only_memory_and_preserves_existing_memory() -> None:
    existing = memory("existing-memory")
    cognition = PersistentCognition(
        identity=identity(),
        memories=(existing,),
    )
    provider = RecordingProvider()
    engine = RelayEngine(provider)
    request = open_request()

    full = s4_capability_profile(CapabilityProfileId.MEM_TALK).plan()
    talk_only = full.with_enabled("MEM", enabled=False)
    talk_binding = EpochBinding(
        "talk-1",
        "talk.open_cognition",
        lambda: CognitionInvocation(request=request, runner=engine.open),
    )
    plan = compile_epoch_plan(
        talk_only,
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("mem-1", "mem.retain", "new-retention"),
            EpochWorkItem("talk-1", "talk.open_cognition", "expression"),
        ),
        bindings=(talk_binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(talk_binding,),
        at_ns=10,
        provenance=provenance("epoch-talk-only"),
    )

    assert [item.work_id for item in plan.suppressed] == ["mem-1"]
    assert result.executed_work_ids == ("talk-1",)
    assert result.suppressed_work_ids == ("mem-1",)
    assert [m.memory_id for m in cognition.memories] == ["existing-memory"]
    assert provider.calls == [(request, CognitionMode.OPEN)]


def test_turning_talk_off_suppresses_only_talk_and_makes_zero_model_calls() -> None:
    cognition_box = {"cognition": PersistentCognition(identity=identity())}
    candidate = memory("memory-no-talk")
    provider = RecordingProvider()

    full = s4_capability_profile(CapabilityProfileId.MEM_TALK).plan()
    mem_only = full.with_enabled("TALK", enabled=False)

    def retain() -> None:
        cognition_box["cognition"] = cognition_box["cognition"].retain_memory(
            candidate
        )

    mem_binding = EpochBinding("mem-1", "mem.retain", retain)
    plan = compile_epoch_plan(
        mem_only,
        S2_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("mem-1", "mem.retain", "retention"),
            EpochWorkItem("talk-1", "talk.open_cognition", "expression"),
        ),
        bindings=(mem_binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(mem_binding,),
        at_ns=10,
        provenance=provenance("epoch-mem-only"),
    )

    assert [item.work_id for item in plan.suppressed] == ["talk-1"]
    assert result.executed_work_ids == ("mem-1",)
    assert result.suppressed_work_ids == ("talk-1",)
    assert [m.memory_id for m in cognition_box["cognition"].memories] == [
        "memory-no-talk"
    ]
    assert provider.calls == []
    assert result.cognition_requested is False
