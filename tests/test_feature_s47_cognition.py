"""S47 deterministic fake-provider tests exercise real RelayEngine accounting."""
from __future__ import annotations

import test_postmain_s42_world_contrast as s42
from relay_self.cognitive_allocation import (
    AllocationPath,
    CognitionBudget,
    allocate_cognition,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0Step
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.world_conditioned_choice import select_world_conditioned_choice


def req():
    return BoundedChoiceRequest(
        request_id="allocation-1", instruction="select", intent_id="intent",
        focus=None, choices=(BoundedChoice("a", "A"), BoundedChoice("b", "B")),
        context=(),
    )


def test_l0_needs_zero_model_calls():
    retained, near, _, event, _ = s42._pair()
    choice = select_world_conditioned_choice(
        near, retained, expected_session_id=near.observation.session_id,
        expected_entity_id=near.entity_id,
    )
    step = L0Step(choice, event.seq, None, None)
    out = allocate_cognition(budget=CognitionBudget(0), l0=step)
    assert out.model_calls == 0 and out.path is AllocationPath.L0


def test_bounded_only_when_one_call_budget():
    calls = []
    def provider(request, *, mode):
        calls.append(mode)
        return ProviderDecision(DecisionStatus.UNRESOLVED, None, "missing")
    out = allocate_cognition(
        budget=CognitionBudget(1, allow_think=True),
        bounded=req(), engine=RelayEngine(provider),
    )
    assert calls == [CognitionMode.BOUNDED]
    assert out.unresolved and out.model_calls == 1


def test_unresolved_may_escalate_once_to_think():
    calls = []
    def provider(request, *, mode):
        calls.append(mode)
        return ProviderDecision(
            DecisionStatus.RESOLVED if mode is CognitionMode.THINK
            else DecisionStatus.UNRESOLVED,
            "a" if mode is CognitionMode.THINK else None, "valid",
        )
    out = allocate_cognition(
        budget=CognitionBudget(2, allow_think=True),
        bounded=req(), engine=RelayEngine(provider),
    )
    assert calls == [CognitionMode.BOUNDED, CognitionMode.THINK]
    assert out.path is AllocationPath.THINK
    assert out.choice_id == "a" and out.model_calls == 2


def test_open_is_explicit_and_never_a_accepted_action_choice():
    calls = []
    def provider(request, *, mode):
        calls.append(mode)
        if mode is CognitionMode.OPEN:
            return ProviderExpression("maybe bridge", Provenance("model", "open-1"))
        return ProviderDecision(DecisionStatus.UNRESOLVED, None, "unresolved")
    opened = OpenCognitionRequest(
        request_id="new-hypothesis", instruction="propose",
        intent_id="intent", focus=None, context=(),
    )
    out = allocate_cognition(
        budget=CognitionBudget(2, allow_open=True),
        bounded=req(), open_request=opened, engine=RelayEngine(provider),
    )
    assert out.path is AllocationPath.OPEN and out.choice_id is None
    assert out.open_result.text == "maybe bridge"
    assert out.model_calls == 2
    assert calls == [CognitionMode.BOUNDED, CognitionMode.OPEN]
