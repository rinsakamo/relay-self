import json

import pytest

from experiments.flee_memory_retrieval import FleeRetrievalDeferredError
from experiments.flee_think_pipeline import (
    build_pipeline_present,
    run_flee_cognition_pipeline,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from relay_self.skill import SkillState


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.calls: list[tuple[BoundedChoiceRequest, CognitionMode]] = []

    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        self.calls.append((request, mode))
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        return self.decisions.pop(0)


def _owner(intent_id: str = "intent-pipeline") -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(
            source="test",
            reference=f"{intent_id}:commit",
        ),
    )
    return owner


def _run(
    decisions: list[ProviderDecision],
):
    owner = _owner()
    broad = build_pipeline_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=False,
    )
    provider = RecordingProvider(decisions)
    epoch = run_flee_cognition_pipeline(
        engine=RelayEngine(provider),
        intent_commitment=owner,
        broad=broad,
        current_source_revision=1,
    )
    return owner, provider, epoch


def test_bounded_success_does_not_spend_think() -> None:
    owner, provider, epoch = _run(
        [ProviderDecision.resolved("cave", reason="bounded sufficient")]
    )

    assert [mode for _, mode in provider.calls] == [CognitionMode.BOUNDED]
    assert epoch.cognition.escalated is False
    assert epoch.cognition.status is DecisionStatus.RESOLVED
    assert epoch.cognition.choice_id == "cave"
    assert epoch.execution is not None
    assert epoch.execution.state is SkillState.STARTED
    assert epoch.execution.skill_id == "FLEE"
    assert owner.current_intent is not None


def test_bounded_unresolved_spends_exactly_one_explicit_think() -> None:
    _, provider, epoch = _run(
        [
            ProviderDecision.unresolved(reason="bounded insufficient"),
            ProviderDecision.resolved("cave", reason="think resolved"),
        ]
    )

    assert [mode for _, mode in provider.calls] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert epoch.cognition.escalated is True
    assert epoch.cognition.provider_call_count == 2
    assert epoch.cognition.choice_id == "cave"
    assert epoch.execution is not None
    assert epoch.execution.state is SkillState.STARTED


def test_think_unresolved_does_not_force_winner_or_start_skill() -> None:
    _, provider, epoch = _run(
        [
            ProviderDecision.unresolved(reason="bounded insufficient"),
            ProviderDecision.unresolved(reason="think still insufficient"),
        ]
    )

    assert [mode for _, mode in provider.calls] == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
    assert epoch.cognition.status is DecisionStatus.UNRESOLVED
    assert epoch.cognition.choice_id is None
    assert epoch.execution is None


def test_selected_memories_enter_transient_request_with_source_provenance() -> None:
    _, provider, epoch = _run(
        [ProviderDecision.resolved("cave", reason="bounded sufficient")]
    )

    assert len(provider.calls) == 1
    request, _ = provider.calls[0]
    memory_data = tuple(
        datum
        for datum in request.context
        if datum.key.startswith("memory:")
    )

    assert [datum.key for datum in memory_data] == [
        "memory:memory-flee-cave",
        "memory:memory-talk-cave",
    ]
    assert [datum.provenance.source for datum in memory_data] == [
        "fixture.flee",
        "fixture.talk",
    ]
    assert json.loads(memory_data[0].value_json)["memory_id"] == "memory-flee-cave"
    assert json.loads(memory_data[1].value_json)["memory_id"] == "memory-talk-cave"
    assert "memory:memory-cave-resource" not in {
        datum.key for datum in request.context
    }
    assert epoch.retrieval.memory_ids == (
        "memory-flee-cave",
        "memory-talk-cave",
    )


def test_viability_interrupt_stops_before_retrieval_and_provider_call() -> None:
    owner = _owner("intent-interrupt")
    broad = build_pipeline_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=True,
    )
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave", reason="must not be used")]
    )

    with pytest.raises(
        FleeRetrievalDeferredError,
        match="reconsideration is pending",
    ):
        run_flee_cognition_pipeline(
            engine=RelayEngine(provider),
            intent_commitment=owner,
            broad=broad,
            current_source_revision=1,
        )

    assert provider.calls == []
    assert owner.pending_reconsideration is not None
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-interrupt"
