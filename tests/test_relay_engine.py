import json
from dataclasses import replace

import pytest

from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    InvalidRelayEngineData,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.runtime_coordination import coordinate_decision_epoch
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="relay-engine-test", reference=reference)


def request() -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id="flee-destination-1",
        instruction="Choose the safer reachable destination.",
        intent_id="intent-safe",
        focus="FLEE",
        choices=(
            BoundedChoice("cave", "Known sheltered cave"),
            BoundedChoice("ridge", "Open ridge route"),
        ),
        context=(
            CognitionDatum.from_value(
                "health",
                8,
                provenance("health"),
            ),
            CognitionDatum.from_value(
                "route_open:cave",
                True,
                provenance("route-cave"),
            ),
            CognitionDatum.from_value(
                "route_open:ridge",
                True,
                provenance("route-ridge"),
            ),
        ),
    )


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.calls: list[tuple[BoundedChoiceRequest, CognitionMode]] = []

    def __call__(
        self,
        received: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        self.calls.append((received, mode))
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        return self.decisions.pop(0)


def test_cognition_datum_preserves_json_type_and_provenance() -> None:
    datum = CognitionDatum.from_value(
        "safe_destinations",
        ["cave", "ridge"],
        provenance("destinations"),
    )

    assert json.loads(datum.value_json) == ["cave", "ridge"]
    assert datum.provenance.reference == "destinations"


def test_request_requires_finite_unique_choices() -> None:
    with pytest.raises(InvalidRelayEngineData, match="at least two"):
        BoundedChoiceRequest(
            request_id="x",
            instruction="choose",
            intent_id=None,
            focus=None,
            choices=(BoundedChoice("a", "A"),),
            context=(),
        )

    with pytest.raises(InvalidRelayEngineData, match="unique"):
        BoundedChoiceRequest(
            request_id="x",
            instruction="choose",
            intent_id=None,
            focus=None,
            choices=(
                BoundedChoice("a", "A"),
                BoundedChoice("a", "Again"),
            ),
            context=(),
        )


def test_bounded_resolution_does_not_escalate() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave", reason="bounded sufficient")]
    )
    engine = RelayEngine(provider)

    result = engine(request())

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "cave"
    assert result.escalated is False
    assert [attempt.mode for attempt in result.attempts] == [
        CognitionMode.BOUNDED
    ]
    assert [mode for _, mode in provider.calls] == [CognitionMode.BOUNDED]


def test_unresolved_bounded_call_explicitly_escalates_to_think() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.resolved("ridge", reason="think resolved"),
        ]
    )
    engine = RelayEngine(provider)

    result = engine(request())

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "ridge"
    assert result.escalated is True
    assert [attempt.mode for attempt in result.attempts] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert [mode for _, mode in provider.calls] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]


def test_inadmissible_bounded_choice_becomes_unresolved_then_think() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.resolved("lava"),
            ProviderDecision.resolved("cave"),
        ]
    )

    result = RelayEngine(provider)(request())

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "cave"
    assert result.attempts[0].status is DecisionStatus.UNRESOLVED
    assert "inadmissible" in result.attempts[0].reason
    assert result.attempts[1].mode is CognitionMode.THINK


def test_inadmissible_think_choice_fails_closed_as_unresolved() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.resolved("lava"),
        ]
    )

    result = RelayEngine(provider)(request())

    assert result.status is DecisionStatus.UNRESOLVED
    assert result.choice_id is None
    assert result.escalated is True
    assert result.attempts[-1].status is DecisionStatus.UNRESOLVED
    assert "inadmissible" in result.attempts[-1].reason


def test_engine_never_retries_or_calls_think_after_think_unresolved() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.unresolved(reason="think uncertainty"),
        ]
    )

    result = RelayEngine(provider)(request())

    assert result.status is DecisionStatus.UNRESOLVED
    assert [mode for _, mode in provider.calls] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert len(result.attempts) == 2


def test_runtime_coordinator_receives_engine_result_without_owner_mutation() -> None:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe",
        objective="reach safety",
        at_ns=1,
        provenance=provenance("intent"),
    )
    skill = SkillExecution.start(
        "skill-flee",
        skill_id="FLEE",
        intent_commitment=commitment,
        at_ns=2,
        provenance=provenance("skill"),
    )
    supervisor = ActionSupervisor()
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave", reason="bounded sufficient")]
    )
    engine = RelayEngine(provider)

    epoch = coordinate_decision_epoch(
        supervisor,
        at_ns=3,
        provenance=provenance("epoch"),
        decision_step=request,
        relay_engine=engine,
    )

    assert epoch.cognition_requested is True
    assert epoch.cognition_result is not None
    assert epoch.cognition_result.status is DecisionStatus.RESOLVED
    assert epoch.cognition_result.choice_id == "cave"
    assert commitment.current_intent is not None
    assert commitment.current_intent.intent_id == "intent-safe"
    assert skill.state is SkillState.STARTED
    assert supervisor.open_actions == ()


def test_provider_decision_cannot_claim_resolved_without_choice() -> None:
    with pytest.raises(InvalidRelayEngineData, match="resolved"):
        ProviderDecision(
            status=DecisionStatus.RESOLVED,
            choice_id=None,
            reason="bad provider contract",
        )


def test_context_rejects_invalid_json_without_interpreting_it() -> None:
    with pytest.raises(InvalidRelayEngineData, match="valid JSON"):
        CognitionDatum(
            key="bad",
            value_json="{not-json}",
            provenance=provenance("bad"),
        )


def test_soft_wall_time_budget_is_observational_and_preserves_resolution(
    monkeypatch,
) -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave", reason="bounded sufficient")]
    )
    timed_request = replace(
        request(),
        soft_wall_time_budget_s=0.5,
    )
    clock = iter((1_000_000_000, 1_700_000_000))
    monkeypatch.setattr(
        "relay_self.relay_engine.time.perf_counter_ns",
        lambda: next(clock),
    )

    result = RelayEngine(provider)(timed_request)

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "cave"
    assert result.provider_call_count == 1
    assert result.elapsed_ns == 700_000_000
    assert result.elapsed_s == pytest.approx(0.7)
    assert result.soft_wall_time_budget_s == 0.5
    assert result.soft_wall_time_budget_exceeded is True


def test_soft_budget_overrun_does_not_prevent_explicit_think(
    monkeypatch,
) -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded uncertainty"),
            ProviderDecision.resolved("ridge", reason="think resolved"),
        ]
    )
    timed_request = replace(
        request(),
        soft_wall_time_budget_s=0.5,
    )
    clock = iter(
        (
            1_000_000_000,
            1_400_000_000,
            1_500_000_000,
            2_100_000_000,
        )
    )
    monkeypatch.setattr(
        "relay_self.relay_engine.time.perf_counter_ns",
        lambda: next(clock),
    )

    result = RelayEngine(provider)(timed_request)

    assert result.status is DecisionStatus.RESOLVED
    assert result.choice_id == "ridge"
    assert result.escalated is True
    assert result.elapsed_ns == 1_000_000_000
    assert result.soft_wall_time_budget_exceeded is True


def test_caller_can_disallow_think_without_relabelling_unresolved() -> None:
    provider = RecordingProvider(
        [ProviderDecision.unresolved(reason="bounded uncertainty")]
    )

    result = RelayEngine(provider)(
        replace(request(), think_allowed=False)
    )

    assert result.status is DecisionStatus.UNRESOLVED
    assert result.escalated is False
    assert result.think_allowed is False
    assert result.provider_call_count == 1
    assert [mode for _, mode in provider.calls] == [CognitionMode.BOUNDED]


def test_provider_call_facts_are_preserved_without_becoming_semantics() -> None:
    facts = ProviderCallFacts(
        requested_max_output_tokens=48,
        prompt_tokens=120,
        completion_tokens=5,
        total_tokens=125,
        finish_reason="stop",
    )
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave", call_facts=facts)]
    )

    result = RelayEngine(provider)(request())

    assert result.status is DecisionStatus.RESOLVED
    assert result.attempts[0].call_facts == facts
    assert result.observed_prompt_tokens == 120
    assert result.observed_completion_tokens == 5


def test_request_rejects_invalid_soft_wall_time_budget() -> None:
    with pytest.raises(
        InvalidRelayEngineData,
        match="soft_wall_time_budget_s",
    ):
        replace(request(), soft_wall_time_budget_s=0)



def open_request() -> OpenCognitionRequest:
    return OpenCognitionRequest(
        request_id="talk-open-1",
        instruction="Respond to the interlocutor from the supplied context.",
        intent_id="intent-talk",
        focus="TALK",
        context=(
            CognitionDatum.from_value(
                "latest_utterance",
                "Are you there?",
                provenance("utterance"),
            ),
        ),
    )


class RecordingMixedProvider:
    def __init__(self) -> None:
        self.calls: list[
            tuple[BoundedChoiceRequest | OpenCognitionRequest, CognitionMode]
        ] = []

    def __call__(
        self,
        received: BoundedChoiceRequest | OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision | ProviderExpression:
        self.calls.append((received, mode))
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                text="I am here.",
                provenance=provenance("open-expression"),
                call_facts=ProviderCallFacts(
                    requested_max_output_tokens=256,
                    prompt_tokens=20,
                    completion_tokens=4,
                    total_tokens=24,
                    finish_reason="stop",
                ),
            )
        return ProviderDecision.resolved("cave")


def test_open_request_has_no_finite_choice_or_think_surface() -> None:
    opened = open_request()

    assert not hasattr(opened, "choices")
    assert not hasattr(opened, "think_allowed")
    assert opened.context[0].provenance.reference == "utterance"


def test_open_cognition_uses_same_owned_provider_exactly_once_without_think(
    monkeypatch,
) -> None:
    provider = RecordingMixedProvider()
    engine = RelayEngine(provider)
    clock = iter(
        (
            1_000_000_000,
            1_050_000_000,
            2_000_000_000,
            2_250_000_000,
        )
    )
    monkeypatch.setattr(
        "relay_self.relay_engine.time.perf_counter_ns",
        lambda: next(clock),
    )

    bounded = engine(request())
    opened = engine.open(open_request())

    assert bounded.status is DecisionStatus.RESOLVED
    assert opened.request_id == "talk-open-1"
    assert opened.text == "I am here."
    assert opened.provenance.reference == "open-expression"
    assert opened.provider_call_count == 1
    assert opened.elapsed_ns == 250_000_000
    assert opened.observed_prompt_tokens == 20
    assert opened.observed_completion_tokens == 4
    assert [mode for _, mode in provider.calls] == [
        CognitionMode.BOUNDED,
        CognitionMode.OPEN,
    ]


def test_open_provider_wrong_result_type_fails_closed_without_retry() -> None:
    calls: list[CognitionMode] = []

    def bad_provider(
        _request: BoundedChoiceRequest | OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        calls.append(mode)
        return ProviderDecision.unresolved(reason="wrong result family")

    with pytest.raises(
        InvalidRelayEngineData,
        match="open provider must return ProviderExpression",
    ):
        RelayEngine(bad_provider).open(open_request())

    assert calls == [CognitionMode.OPEN]


def test_open_provider_expression_requires_non_empty_text() -> None:
    with pytest.raises(InvalidRelayEngineData, match="expression text"):
        ProviderExpression(
            text="   ",
            provenance=provenance("empty"),
        )
