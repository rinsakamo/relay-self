import pytest

from experiments.flee_memory_retrieval import (
    FleeRetrievalDeferredError,
    reference_cognition,
    retrieve_flee_memories,
    run_reference_fixture,
)
from experiments.focus_attention_epoch import (
    attend_flee,
    build_attention_present,
)
from experiments.present_skill_epoch import narrow_for_flee
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def _owner(intent_id: str = "intent-retrieval") -> IntentCommitment:
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


def _ordinary_attention(owner: IntentCommitment):
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=False,
    )
    local = narrow_for_flee(broad)
    return attend_flee(
        broad=broad,
        local=local,
        current_source_revision=1,
        intent_commitment=owner,
        at_ns=2,
    )


def test_flee_attention_reduces_existing_memory_set_without_mutation() -> None:
    owner = _owner()
    attention = _ordinary_attention(owner)
    cognition = reference_cognition()
    before = cognition.memories

    result = retrieve_flee_memories(
        attention=attention,
        cognition=cognition,
        intent_commitment=owner,
    )

    assert cognition.memories is before
    assert len(cognition.memories) == 4
    assert result.memory_ids == (
        "memory-flee-cave",
        "memory-talk-cave",
    )


def test_retrieval_is_non_exclusive_across_source_contexts() -> None:
    owner = _owner()
    attention = _ordinary_attention(owner)
    cognition = reference_cognition()

    result = retrieve_flee_memories(
        attention=attention,
        cognition=cognition,
        intent_commitment=owner,
    )

    flee_memory, talk_memory = result.memories
    assert flee_memory.source_provenance.source == "fixture.flee"
    assert talk_memory.source_provenance.source == "fixture.talk"
    assert talk_memory.source_provenance.reference == "talk:exchange-4"


def test_same_destination_but_irrelevant_memory_is_excluded() -> None:
    owner = _owner()
    attention = _ordinary_attention(owner)
    cognition = reference_cognition()

    result = retrieve_flee_memories(
        attention=attention,
        cognition=cognition,
        intent_commitment=owner,
    )

    assert "memory-cave-resource" not in result.memory_ids
    assert "memory-style" not in result.memory_ids


def test_retrieval_preserves_exact_memory_objects_and_provenance() -> None:
    owner = _owner()
    attention = _ordinary_attention(owner)
    cognition = reference_cognition()
    expected_flee = cognition.memories[0]
    expected_talk = cognition.memories[1]

    result = retrieve_flee_memories(
        attention=attention,
        cognition=cognition,
        intent_commitment=owner,
    )

    assert result.memories[0] is expected_flee
    assert result.memories[1] is expected_talk
    assert (
        result.memories[0].integration_provenance
        is expected_flee.integration_provenance
    )
    assert (
        result.memories[1].source_provenance
        is expected_talk.source_provenance
    )


def test_pending_reconsideration_defers_narrow_retrieval() -> None:
    owner = _owner()
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=True,
    )
    local = narrow_for_flee(broad)
    attention = attend_flee(
        broad=broad,
        local=local,
        current_source_revision=1,
        intent_commitment=owner,
        at_ns=2,
    )
    cognition = reference_cognition()
    before = cognition.memories

    assert owner.pending_reconsideration is not None
    assert attention.reconsideration_requested is True

    with pytest.raises(
        FleeRetrievalDeferredError,
        match="reconsideration is pending",
    ):
        retrieve_flee_memories(
            attention=attention,
            cognition=cognition,
            intent_commitment=owner,
        )

    assert cognition.memories is before


def test_reference_fixture_reports_cross_skill_retrieval() -> None:
    result = run_reference_fixture()

    assert result["focus"] == "FLEE"
    assert result["candidate_count"] == 4
    assert result["selected_memory_ids"] == (
        "memory-flee-cave",
        "memory-talk-cave",
    )
    assert result["selected_source_provenance"] == (
        "flee:episode-7:outcome",
        "talk:exchange-4",
    )
