from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from experiments.present_skill_epoch import (
    PresentFact,
    PresentProjection,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import Memory
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

TALK_SKILL_ID = "TALK"
TALK_REQUIRED_KEYS = ("interlocutor", "latest_utterance")
TALK_LOCAL_KEYS = (
    "interlocutor",
    "latest_utterance",
    "conversation_topic",
)


class TalkSurfaceError(ValueError):
    """Raised when the experiment-local TALK surface is not usable."""


@dataclass(frozen=True, slots=True)
class TalkSurface:
    """Transient TALK-local projection over existing Present and Memory values."""

    present: PresentProjection
    memories: tuple[Memory, ...]

    def __post_init__(self) -> None:
        if self.present.focus != TALK_SKILL_ID:
            raise TalkSurfaceError("TALK surface requires a TALK-focused Present projection")
        if not all(isinstance(memory, Memory) for memory in self.memories):
            raise TalkSurfaceError("TALK surface memories must be existing Memory values")


def admit_talk_candidate(present: PresentProjection) -> bool:
    """Admit TALK only for the bounded conversational fixture."""

    return (
        present.objective == "respond to companion"
        and present.fact("interlocutor") is not None
        and present.fact("latest_utterance") is not None
    )


def project_for_talk(
    present: PresentProjection,
    *,
    selected_memories: Iterable[Memory] = (),
    include_latest_utterance: bool = True,
) -> TalkSurface:
    """Build one transient TALK-local surface without owning retrieval or Memory."""

    local_keys = set(TALK_LOCAL_KEYS)
    if not include_latest_utterance:
        local_keys.remove("latest_utterance")

    facts = tuple(fact for fact in present.facts if fact.key in local_keys)
    memories = tuple(selected_memories)

    return TalkSurface(
        present=PresentProjection(
            intent_id=present.intent_id,
            objective=present.objective,
            source_revision=present.source_revision,
            facts=facts,
            focus=TALK_SKILL_ID,
        ),
        memories=memories,
    )


def missing_talk_keys(surface: TalkSurface) -> tuple[str, ...]:
    """Report missing required context without synthesizing negative facts."""

    return tuple(
        key
        for key in TALK_REQUIRED_KEYS
        if surface.present.fact(key) is None
    )


def start_talk_execution(
    surface: TalkSurface,
    *,
    intent_commitment: IntentCommitment,
    execution_id: str,
    at_ns: int,
    provenance: Provenance,
) -> SkillExecution:
    """Hand a valid TALK selection to the existing SkillExecution lifecycle."""

    missing = missing_talk_keys(surface)
    if missing:
        raise TalkSurfaceError(
            "TALK surface is missing required context: " + ", ".join(missing)
        )

    return SkillExecution.start(
        execution_id,
        skill_id=TALK_SKILL_ID,
        intent_commitment=intent_commitment,
        at_ns=at_ns,
        provenance=provenance,
    )


def reference_facts() -> tuple[PresentFact, ...]:
    """Broad fixture facts containing conversational and unrelated information."""

    source = "fixture.world"
    return (
        PresentFact(
            "interlocutor",
            "Alex",
            Provenance(source=source, reference="rev:1:interlocutor"),
        ),
        PresentFact(
            "latest_utterance",
            "Do you remember which shelter worked last time?",
            Provenance(source=source, reference="rev:1:utterance"),
        ),
        PresentFact(
            "conversation_topic",
            "prior shelter",
            Provenance(source=source, reference="rev:1:topic"),
        ),
        PresentFact(
            "hunger",
            8,
            Provenance(source=source, reference="rev:1:hunger"),
        ),
        PresentFact(
            "threat_nearby",
            False,
            Provenance(source=source, reference="rev:1:threat"),
        ),
        PresentFact(
            "route_open:cave",
            True,
            Provenance(source=source, reference="rev:1:route:cave"),
        ),
    )


def reference_memories() -> tuple[Memory, ...]:
    """Existing Memories with no TALK-owned partition or tagging field."""

    return (
        Memory(
            memory_id="memory-conversation-style",
            content="Alex prefers concise answers.",
            source_provenance=Provenance(
                source="fixture.conversation",
                reference="exchange:4",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:conversation-style",
            ),
        ),
        Memory(
            memory_id="memory-flee-shelter",
            content="The cave sheltered us during the last escape.",
            source_provenance=Provenance(
                source="fixture.experience",
                reference="flee:escape-7:outcome",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:flee-shelter",
            ),
        ),
        Memory(
            memory_id="memory-resource-cache",
            content="A resource cache exists near the ridge.",
            source_provenance=Provenance(
                source="fixture.experience",
                reference="gather:cache-2:outcome",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:resource-cache",
            ),
        ),
    )
