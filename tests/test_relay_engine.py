import json

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
    ProviderDecision,
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
