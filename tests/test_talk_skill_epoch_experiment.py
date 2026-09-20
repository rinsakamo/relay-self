import pytest

from experiments.present_skill_epoch import build_present
from experiments.talk_skill_epoch import (
    TALK_SKILL_ID,
    TalkSurfaceError,
    admit_talk_candidate,
    missing_talk_keys,
    project_for_talk,
    reference_facts,
    reference_memories,
    start_talk_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillState


def _commit_conversation() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-reply-test",
        objective="respond to companion",
        at_ns=1,
        provenance=Provenance(source="test", reference="intent"),
    )
    return commitment


def test_talk_narrowing_reuses_present_and_preserves_fact_provenance() -> None:
    commitment = _commit_conversation()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )

    assert admit_talk_candidate(broad) is True

    surface = project_for_talk(broad)

    assert len(broad.facts) == 6
    assert len(surface.present.facts) == 3
    assert surface.present.focus == TALK_SKILL_ID
    assert surface.present.fact("hunger") is None
    assert surface.present.fact("threat_nearby") is None
    assert surface.present.fact("route_open:cave") is None

    latest = surface.present.fact("latest_utterance")
    assert latest is not None
    assert latest.provenance == broad.fact("latest_utterance").provenance


def test_talk_memory_bias_is_caller_selected_and_not_skill_partitioned() -> None:
    commitment = _commit_conversation()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )
    conversation, flee_shelter, resource_cache = reference_memories()

    surface = project_for_talk(
        broad,
        selected_memories=(conversation, flee_shelter),
    )

    assert [memory.memory_id for memory in surface.memories] == [
        "memory-conversation-style",
        "memory-flee-shelter",
    ]
    assert flee_shelter.source_provenance.reference == "flee:escape-7:outcome"
    assert resource_cache not in surface.memories


def test_omitted_talk_context_remains_missing_instead_of_becoming_false() -> None:
    commitment = _commit_conversation()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )

    surface = project_for_talk(
        broad,
        include_latest_utterance=False,
    )

    assert surface.present.fact("latest_utterance") is None
    assert missing_talk_keys(surface) == ("latest_utterance",)

    with pytest.raises(TalkSurfaceError, match="latest_utterance"):
        start_talk_execution(
            surface,
            intent_commitment=commitment,
            execution_id="talk-missing-1",
            at_ns=2,
            provenance=Provenance(source="test", reference="skill-start"),
        )


def test_talk_hands_off_to_existing_skill_execution_without_registry() -> None:
    commitment = _commit_conversation()
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(),
    )
    conversation, flee_shelter, _ = reference_memories()
    surface = project_for_talk(
        broad,
        selected_memories=(conversation, flee_shelter),
    )

    execution = start_talk_execution(
        surface,
        intent_commitment=commitment,
        execution_id="talk-test-1",
        at_ns=2,
        provenance=Provenance(source="test", reference="skill-start"),
    )

    assert execution.skill_id == TALK_SKILL_ID
    assert execution.intent_id == "intent-reply-test"
    assert execution.state is SkillState.STARTED
