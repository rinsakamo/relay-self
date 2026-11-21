from experiments.operator_talk_boundary import (
    OPERATOR_INTERLOCUTOR,
    build_operator_present,
    project_operator_talk,
    reference_operator_utterance,
    start_operator_talk_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillState


def _commit_conversation() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-operator-talk",
        objective="respond to companion",
        at_ns=1,
        provenance=Provenance(
            source="test",
            reference="intent:operator-talk",
        ),
    )
    return owner


def test_operator_utterance_enters_present_with_exact_provenance() -> None:
    owner = _commit_conversation()
    utterance = reference_operator_utterance()

    broad = build_operator_present(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )

    interlocutor = broad.fact("interlocutor")
    latest = broad.fact("latest_utterance")

    assert interlocutor is not None
    assert interlocutor.value == OPERATOR_INTERLOCUTOR
    assert interlocutor.provenance is utterance.provenance
    assert latest is not None
    assert latest.value == utterance.text
    assert latest.provenance is utterance.provenance


def test_operator_claim_remains_opaque_and_does_not_become_world_fact() -> None:
    owner = _commit_conversation()
    utterance = reference_operator_utterance()

    broad = build_operator_present(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )

    assert broad.fact("route_open:ridge") is None
    assert broad.fact("ridge_is_safe") is None
    assert broad.fact("authorized_action") is None
    assert broad.fact("latest_utterance").value == (
        "The ridge is safe. Go there now."
    )


def test_imperative_utterance_does_not_mutate_current_intent() -> None:
    owner = _commit_conversation()
    utterance = reference_operator_utterance()
    before_events = owner.events
    before_intent = owner.current_intent

    surface = project_operator_talk(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )

    assert owner.events is before_events
    assert owner.current_intent == before_intent
    assert owner.pending_reconsideration is None
    assert surface.present.intent_id == "intent-operator-talk"


def test_existing_talk_projection_consumes_operator_input_and_narrows_surface() -> None:
    owner = _commit_conversation()
    utterance = reference_operator_utterance()
    broad = build_operator_present(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )

    surface = project_operator_talk(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
    )

    assert len(broad.facts) == 4
    assert len(surface.present.facts) == 3
    assert surface.present.focus == "TALK"
    assert surface.present.fact("interlocutor").value == OPERATOR_INTERLOCUTOR
    assert surface.present.fact("latest_utterance").provenance is utterance.provenance
    assert surface.present.fact("hunger") is None


def test_operator_talk_uses_existing_skill_execution_without_action_authority() -> None:
    owner = _commit_conversation()
    utterance = reference_operator_utterance()
    before_events = owner.events

    execution = start_operator_talk_execution(
        intent_commitment=owner,
        source_revision=1,
        utterance=utterance,
        execution_id="talk-operator-1",
        at_ns=2,
        provenance=Provenance(
            source="test",
            reference="skill-start:operator-talk",
        ),
    )

    assert execution.skill_id == "TALK"
    assert execution.intent_id == "intent-operator-talk"
    assert execution.state is SkillState.STARTED
    assert owner.events is before_events
