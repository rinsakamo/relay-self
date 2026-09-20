from __future__ import annotations

from dataclasses import dataclass

from experiments.present_skill_epoch import (
    PresentFact,
    PresentProjection,
    build_present,
)
from experiments.talk_skill_epoch import (
    TalkSurface,
    admit_talk_candidate,
    project_for_talk,
    start_talk_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

OPERATOR_INTERLOCUTOR = "operator"


class InvalidExternalUtterance(ValueError):
    """Raised when the experiment-local external utterance is malformed."""


@dataclass(frozen=True, slots=True)
class ExternalUtterance:
    """Opaque provenance-bearing language from an external interlocutor."""

    utterance_id: str
    text: str
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.utterance_id, str) or not self.utterance_id.strip():
            raise InvalidExternalUtterance(
                "utterance_id must be a non-empty string"
            )
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidExternalUtterance(
                "utterance text must be a non-empty string"
            )
        if not isinstance(self.provenance, Provenance):
            raise InvalidExternalUtterance(
                "utterance provenance must be Provenance"
            )


def build_operator_present(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    utterance: ExternalUtterance,
) -> PresentProjection:
    """Project operator speech as conversational input, not as claimed World truth."""

    facts = (
        PresentFact(
            "interlocutor",
            OPERATOR_INTERLOCUTOR,
            utterance.provenance,
        ),
        PresentFact(
            "latest_utterance",
            utterance.text,
            utterance.provenance,
        ),
        PresentFact(
            "conversation_topic",
            "operator exchange",
            utterance.provenance,
        ),
        PresentFact(
            "hunger",
            7,
            Provenance(
                source="fixture.world",
                reference=f"rev:{source_revision}:hunger",
            ),
        ),
    )
    return build_present(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        facts=facts,
    )


def project_operator_talk(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    utterance: ExternalUtterance,
) -> TalkSurface:
    """Reuse the existing TALK-local projection for one operator utterance."""

    broad = build_operator_present(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        utterance=utterance,
    )
    if not admit_talk_candidate(broad):
        raise ValueError("operator utterance is not admitted as a TALK candidate")
    return project_for_talk(broad)


def start_operator_talk_execution(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    utterance: ExternalUtterance,
    execution_id: str,
    at_ns: int,
    provenance: Provenance,
) -> SkillExecution:
    """Hand the admitted operator TALK surface to the existing SkillExecution."""

    surface = project_operator_talk(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        utterance=utterance,
    )
    return start_talk_execution(
        surface,
        intent_commitment=intent_commitment,
        execution_id=execution_id,
        at_ns=at_ns,
        provenance=provenance,
    )


def reference_operator_utterance() -> ExternalUtterance:
    return ExternalUtterance(
        utterance_id="operator-utterance-1",
        text="The ridge is safe. Go there now.",
        provenance=Provenance(
            source="external.operator",
            reference="utterance:operator-1",
        ),
    )
