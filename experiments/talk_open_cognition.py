from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
from relay_self.relay_engine import CognitionDatum
from relay_self.skill import SkillExecution


class InvalidTalkOpenCognition(ValueError):
    """Raised when the experiment-local open TALK seam is malformed."""


@dataclass(frozen=True, slots=True)
class TalkOpenRequest:
    """Experiment-local open cognition request with no finite choice surface."""

    request_id: str
    instruction: str
    intent_id: str
    focus: str
    context: tuple[CognitionDatum, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("request_id", self.request_id),
            ("instruction", self.instruction),
            ("intent_id", self.intent_id),
            ("focus", self.focus),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidTalkOpenCognition(
                    f"{name} must be a non-empty string"
                )
        if self.focus != TALK_SKILL_ID:
            raise InvalidTalkOpenCognition(
                "open TALK request requires TALK focus"
            )
        if not isinstance(self.context, tuple) or not all(
            isinstance(datum, CognitionDatum)
            for datum in self.context
        ):
            raise InvalidTalkOpenCognition(
                "open TALK context must contain CognitionDatum values"
            )


@dataclass(frozen=True, slots=True)
class TalkOpenResult:
    """Transient generated expression; not World, Intent, Memory, or Action authority."""

    text: str
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidTalkOpenCognition(
                "open TALK result text must be non-empty"
            )
        if not isinstance(self.provenance, Provenance):
            raise InvalidTalkOpenCognition(
                "open TALK result provenance must be Provenance"
            )


class TalkOpenProvider(Protocol):
    def __call__(self, request: TalkOpenRequest) -> TalkOpenResult: ...


@dataclass(frozen=True, slots=True)
class ReferenceOpenTalk:
    intent_commitment: IntentCommitment
    cognition: PersistentCognition
    surface: TalkSurface
    execution: SkillExecution
    request: TalkOpenRequest


def build_talk_open_request(
    surface: TalkSurface,
    *,
    request_id: str = "talk-open:00",
) -> TalkOpenRequest:
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
    return TalkOpenRequest(
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
    request: TalkOpenRequest,
    *,
    provider: TalkOpenProvider,
) -> TalkOpenResult:
    """Call one fake/replaceable provider without acquiring semantic authority."""

    if not callable(provider):
        raise InvalidTalkOpenCognition("open TALK provider must be callable")
    result = provider(request)
    if not isinstance(result, TalkOpenResult):
        raise InvalidTalkOpenCognition(
            "open TALK provider must return TalkOpenResult"
        )
    return result


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
