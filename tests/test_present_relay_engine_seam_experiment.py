import pytest

from experiments.present_relay_engine_seam import (
    FLEE_SKILL_ID,
    build_flee_relay_request,
    build_model_reference_present,
    missing_flee_relay_keys,
    run_flee_present_relay_epoch,
    run_reference_epoch,
)
from experiments.present_skill_epoch import narrow_for_flee
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngine,
)
from relay_self.skill import SkillState


class RecordingProvider:
    def __init__(self, decisions: list[ProviderDecision]) -> None:
        self.decisions = list(decisions)
        self.requests = []
        self.modes: list[CognitionMode] = []

    def __call__(self, request, *, mode: CognitionMode) -> ProviderDecision:
        self.requests.append(request)
        self.modes.append(mode)
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        return self.decisions.pop(0)


def _commit() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-reach-safety",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="test", reference="intent"),
    )
    return commitment


def test_present_to_request_preserves_provenance_and_narrows_surface() -> None:
    commitment = _commit()
    broad = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=1,
    )
    local = narrow_for_flee(broad)
    request = build_flee_relay_request(
        local,
        current_source_revision=1,
    )

    assert len(broad.facts) == 9
    assert len(local.facts) == 7
    assert request.intent_id == broad.intent_id
    assert request.focus == FLEE_SKILL_ID
    assert [datum.key for datum in request.context] == [
        fact.key for fact in local.facts
    ]
    assert "hunger" not in {datum.key for datum in request.context}
    assert "companion_speaking" not in {
        datum.key for datum in request.context
    }

    for datum in request.context:
        fact = local.fact(datum.key)
        assert fact is not None
        assert datum.provenance == fact.provenance


def test_stale_projection_is_rejected_before_provider_call() -> None:
    commitment = _commit()
    broad = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=1,
    )
    local = narrow_for_flee(broad)

    with pytest.raises(ValueError, match="stale Present projection"):
        build_flee_relay_request(
            local,
            current_source_revision=2,
        )


def test_missing_shelter_is_missing_not_false_and_broadens_before_model() -> None:
    commitment = _commit()
    broad = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=1,
    )
    misleading = narrow_for_flee(
        broad,
        include_shelter_status=False,
    )

    assert missing_flee_relay_keys(misleading) == (
        "shelter:cave",
        "shelter:ridge",
    )

    provider = RecordingProvider(
        [ProviderDecision.resolved("cave")]
    )
    epoch = run_flee_present_relay_epoch(
        engine=RelayEngine(provider),
        broad=broad,
        local=misleading,
        current_source_revision=1,
        intent_commitment=commitment,
    )

    assert epoch.broadened is True
    assert len(provider.requests) == 1
    sent_keys = {
        datum.key for datum in provider.requests[0].context
    }
    assert "shelter:cave" in sent_keys
    assert "shelter:ridge" in sent_keys
    assert epoch.effective.fact("shelter:cave").value is True
    assert epoch.effective.fact("shelter:ridge").value is False


def test_broadening_rejects_different_source_revision() -> None:
    commitment = _commit()
    broad = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=2,
    )
    old = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=1,
    )
    misleading = narrow_for_flee(
        old,
        include_shelter_status=False,
    )
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave")]
    )

    with pytest.raises(ValueError, match="source revision"):
        run_flee_present_relay_epoch(
            engine=RelayEngine(provider),
            broad=broad,
            local=misleading,
            current_source_revision=2,
            intent_commitment=commitment,
        )

    assert provider.requests == []


def test_resolved_model_binding_starts_existing_skill_execution() -> None:
    provider = RecordingProvider(
        [ProviderDecision.resolved("cave")]
    )
    epoch = run_reference_epoch(RelayEngine(provider))

    assert epoch.cognition.choice_id == "cave"
    assert epoch.decision.destination == "cave"
    assert epoch.execution is not None
    assert epoch.execution.skill_id == "FLEE"
    assert epoch.execution.intent_id == "intent-reach-safety"
    assert epoch.execution.state is SkillState.STARTED
    assert epoch.broadened is False
    assert provider.modes == [CognitionMode.BOUNDED]


def test_unresolved_model_result_does_not_start_skill_execution() -> None:
    provider = RecordingProvider(
        [
            ProviderDecision.unresolved(reason="bounded"),
            ProviderDecision.unresolved(reason="think"),
        ]
    )
    epoch = run_reference_epoch(RelayEngine(provider))

    assert epoch.cognition.choice_id is None
    assert epoch.execution is None
    assert provider.modes == [
        CognitionMode.BOUNDED,
        CognitionMode.THINK,
    ]
