import json

from experiments.operator_talk_boundary import (
    build_operator_present,
    reference_operator_utterance,
)
from experiments.talk_open_cognition import (
    build_reference_open_talk,
    build_talk_open_request,
    run_talk_open_cognition,
)
from experiments.talk_skill_epoch import (
    project_for_talk,
    reference_memories,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderExpression,
    RelayEngine,
)
from relay_self.skill import SkillState


class RecordingOpenProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[OpenCognitionRequest, CognitionMode]] = []

    def __call__(
        self,
        request: OpenCognitionRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderExpression:
        self.calls.append((request, mode))
        return ProviderExpression(
            text=(
                "I remember the cave sheltered us before, but the operator's "
                "message alone does not establish that the ridge is safe."
            ),
            provenance=Provenance(
                source="fixture.fake-provider",
                reference="generation:talk-open-1",
            ),
            call_facts=ProviderCallFacts(
                requested_max_output_tokens=256,
                prompt_tokens=30,
                completion_tokens=16,
                total_tokens=46,
                finish_reason="stop",
            ),
        )


def test_open_talk_request_preserves_operator_and_memory_provenance() -> None:
    fixture = build_reference_open_talk()

    by_key = {datum.key: datum for datum in fixture.request.context}
    latest = by_key["latest_utterance"]
    memory = by_key["memory:memory-flee-shelter"]

    assert json.loads(latest.value_json) == "The ridge is safe. Go there now."
    assert latest.provenance.source == "external.operator"
    assert latest.provenance.reference == "utterance:operator-1"

    memory_value = json.loads(memory.value_json)
    assert memory_value["memory_id"] == "memory-flee-shelter"
    assert memory.provenance.source == "fixture.experience"
    assert memory.provenance.reference == "flee:escape-7:outcome"


def test_open_talk_shape_has_no_fake_finite_choice_surface() -> None:
    fixture = build_reference_open_talk()

    assert fixture.request.focus == "TALK"
    assert not hasattr(fixture.request, "choices")
    assert not hasattr(fixture.request, "choice_id")
    assert not hasattr(fixture.request, "status")


def test_fake_provider_returns_one_transient_expression() -> None:
    fixture = build_reference_open_talk()
    provider = RecordingOpenProvider()

    result = run_talk_open_cognition(
        fixture.request,
        engine=RelayEngine(provider),
    )

    assert provider.calls == [(fixture.request, CognitionMode.OPEN)]
    assert result.request_id == fixture.request.request_id
    assert result.text.startswith("I remember the cave")
    assert result.provenance.source == "fixture.fake-provider"
    assert result.provenance.reference == "generation:talk-open-1"
    assert result.provider_call_count == 1
    assert result.observed_prompt_tokens == 30
    assert result.observed_completion_tokens == 16


def test_open_generation_does_not_mutate_existing_semantic_owners() -> None:
    fixture = build_reference_open_talk()
    provider = RecordingOpenProvider()

    events_before = fixture.intent_commitment.events
    current_before = fixture.intent_commitment.current_intent
    memories_before = fixture.cognition.memories
    execution_before = fixture.execution

    result = run_talk_open_cognition(
        fixture.request,
        engine=RelayEngine(provider),
    )

    assert fixture.intent_commitment.events is events_before
    assert fixture.intent_commitment.current_intent == current_before
    assert fixture.cognition.memories is memories_before
    assert fixture.execution is execution_before
    assert fixture.execution.state is SkillState.STARTED
    assert not hasattr(result, "action_id")
    assert not hasattr(result, "world_state")


def test_generated_text_does_not_reinterpret_operator_claim_as_attested_fact() -> None:
    fixture = build_reference_open_talk()
    provider = RecordingOpenProvider()

    result = run_talk_open_cognition(
        fixture.request,
        engine=RelayEngine(provider),
    )

    context_keys = {datum.key for datum in fixture.request.context}
    assert "route_open:ridge" not in context_keys
    assert "ridge_is_safe" not in context_keys
    assert "operator's message alone does not establish" in result.text


def test_open_talk_cognition_does_not_require_started_skill_execution() -> None:
    owner = IntentCommitment()
    owner.commit(
        "intent-open-talk",
        objective="respond to companion",
        at_ns=1,
        provenance=Provenance(
            source="fixture.intent",
            reference="intent:open-talk",
        ),
    )
    utterance = reference_operator_utterance()
    broad = build_operator_present(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )
    surface = project_for_talk(
        broad,
        selected_memories=(reference_memories()[1],),
    )

    request_without_execution = build_talk_open_request(surface)
    reference_with_execution = build_reference_open_talk()

    assert request_without_execution == reference_with_execution.request
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-open-talk"

    provider = RecordingOpenProvider()
    result = run_talk_open_cognition(
        request_without_execution,
        engine=RelayEngine(provider),
    )

    assert provider.calls == [
        (request_without_execution, CognitionMode.OPEN)
    ]
    assert result.request_id == request_without_execution.request_id
    assert result.text.startswith("I remember the cave")
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-open-talk"
