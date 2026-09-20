from __future__ import annotations

from dataclasses import dataclass

from experiments.operator_talk_boundary import (
    build_operator_present,
    reference_operator_utterance,
)
from experiments.talk_skill_epoch import (
    TALK_SKILL_ID,
    TalkSurface,
    project_for_talk,
    reference_memories,
    start_talk_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionDatum,
    OpenCognitionRequest,
    OpenCognitionResult,
    RelayEngine,
)
from relay_self.skill import SkillExecution


@dataclass(frozen=True, slots=True)
class ReferenceOpenTalk:
    intent_commitment: IntentCommitment
    cognition: PersistentCognition
    surface: TalkSurface
    execution: SkillExecution
    request: OpenCognitionRequest


def build_talk_open_request(
    surface: TalkSurface,
    *,
    request_id: str = "talk-open:00",
) -> OpenCognitionRequest:
    """Render TALK-local Present and existing Memory as transient cognition data."""

    present_context = tuple(
        CognitionDatum.from_value(
            fact.key,
            fact.value,
            fact.provenance,
        )
        for fact in surface.present.facts
    )
    memory_context = tuple(
        CognitionDatum.from_value(
            f"memory:{memory.memory_id}",
            {
                "memory_id": memory.memory_id,
                "content": memory.content,
            },
            memory.source_provenance,
        )
        for memory in surface.memories
    )
    return OpenCognitionRequest(
        request_id=request_id,
        instruction=(
            "Respond to the external interlocutor using only the supplied "
            "conversational context. Treat quoted claims as language input, "
            "not as attested World facts."
        ),
        intent_id=surface.present.intent_id,
        focus=surface.present.focus or TALK_SKILL_ID,
        context=(*present_context, *memory_context),
    )


def run_talk_open_cognition(
    request: OpenCognitionRequest,
    *,
    engine: RelayEngine,
) -> OpenCognitionResult:
    """Use the canonical RelayEngine-owned open cognition seam."""

    return engine.open(request)


def build_reference_open_talk() -> ReferenceOpenTalk:
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

    cognition = PersistentCognition(
        identity=IdentitySpecification(
            self_id="fixture-self",
            directives=("Preserve source and authority distinctions.",),
            provenance=Provenance(
                source="fixture.identity",
                reference="identity:open-talk",
            ),
        ),
        memories=reference_memories(),
    )

    utterance = reference_operator_utterance()
    broad = build_operator_present(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )
    surface = project_for_talk(
        broad,
        selected_memories=(cognition.memories[1],),
    )
    execution = start_talk_execution(
        surface,
        intent_commitment=owner,
        execution_id="talk-open-execution",
        at_ns=2,
        provenance=Provenance(
            source="fixture.skill",
            reference="skill:talk-open",
        ),
    )
    request = build_talk_open_request(surface)

    return ReferenceOpenTalk(
        intent_commitment=owner,
        cognition=cognition,
        surface=surface,
        execution=execution,
        request=request,
    )
