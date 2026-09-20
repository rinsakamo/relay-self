from __future__ import annotations

import re
from dataclasses import dataclass

from experiments.focus_attention_epoch import (
    FleeAttentionResult,
    attend_flee,
    build_attention_present,
)
from experiments.present_skill_epoch import FLEE_SKILL_ID, narrow_for_flee
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance

FLEE_RETRIEVAL_CUES = frozenset(
    {
        "escape",
        "safe",
        "shelter",
        "threat",
    }
)


class FleeRetrievalDeferredError(ValueError):
    """Raised when current FLEE-local retrieval must defer to reconsideration."""


@dataclass(frozen=True, slots=True)
class FleeRetrievalResult:
    focus: str
    attention: FleeAttentionResult
    memories: tuple[Memory, ...]

    @property
    def memory_ids(self) -> tuple[str, ...]:
        return tuple(memory.memory_id for memory in self.memories)


def retrieve_flee_memories(
    *,
    attention: FleeAttentionResult,
    cognition: PersistentCognition,
    intent_commitment: IntentCommitment,
) -> FleeRetrievalResult:
    if attention.focus != FLEE_SKILL_ID:
        raise ValueError("FLEE retrieval requires FLEE Attention")
    if intent_commitment.pending_reconsideration is not None:
        raise FleeRetrievalDeferredError(
            "FLEE retrieval is deferred while Current Intent reconsideration is pending"
        )

    safe_destinations = next(
        (
            fact.value
            for fact in attention.attended_facts
            if fact.key == "safe_destinations"
        ),
        None,
    )
    if not isinstance(safe_destinations, tuple) or not all(
        isinstance(destination, str) and destination
        for destination in safe_destinations
    ):
        raise ValueError(
            "FLEE retrieval requires attended safe_destinations"
        )

    destination_terms = frozenset(destination.lower() for destination in safe_destinations)
    selected = tuple(
        memory
        for memory in cognition.memories
        if _memory_matches_flee_fixture(
            memory,
            destination_terms=destination_terms,
        )
    )

    return FleeRetrievalResult(
        focus=attention.focus,
        attention=attention,
        memories=selected,
    )


def _memory_matches_flee_fixture(
    memory: Memory,
    *,
    destination_terms: frozenset[str],
) -> bool:
    tokens = frozenset(
        re.findall(r"[a-z0-9_-]+", memory.content.lower())
    )
    return bool(tokens & destination_terms) and bool(tokens & FLEE_RETRIEVAL_CUES)


def reference_cognition() -> PersistentCognition:
    identity = IdentitySpecification(
        self_id="fixture-self",
        directives=("Preserve continued agency.",),
        provenance=Provenance(
            source="fixture.identity",
            reference="identity:v1",
        ),
    )
    memories = (
        Memory(
            memory_id="memory-flee-cave",
            content="The cave shelter kept us safe during the last escape.",
            source_provenance=Provenance(
                source="fixture.flee",
                reference="flee:episode-7:outcome",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:flee-cave",
            ),
        ),
        Memory(
            memory_id="memory-talk-cave",
            content="Alex said the cave is safe during storms.",
            source_provenance=Provenance(
                source="fixture.talk",
                reference="talk:exchange-4",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:talk-cave",
            ),
        ),
        Memory(
            memory_id="memory-cave-resource",
            content="A resource cache is stored inside the cave.",
            source_provenance=Provenance(
                source="fixture.gather",
                reference="gather:cache-2",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:cave-resource",
            ),
        ),
        Memory(
            memory_id="memory-style",
            content="Alex prefers concise answers.",
            source_provenance=Provenance(
                source="fixture.talk",
                reference="talk:style",
            ),
            integration_provenance=Provenance(
                source="fixture.integration",
                reference="memory:style",
            ),
        ),
    )
    return PersistentCognition(
        identity=identity,
        memories=memories,
    )


def run_reference_fixture() -> dict[str, object]:
    owner = IntentCommitment()
    owner.commit(
        "intent-retrieval",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(
            source="fixture",
            reference="intent:retrieval",
        ),
    )
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=False,
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
    result = retrieve_flee_memories(
        attention=attention,
        cognition=cognition,
        intent_commitment=owner,
    )

    return {
        "focus": result.focus,
        "attended_keys": attention.attended_keys,
        "candidate_count": len(cognition.memories),
        "selected_memory_ids": result.memory_ids,
        "selected_source_provenance": tuple(
            memory.source_provenance.reference
            for memory in result.memories
        ),
    }
