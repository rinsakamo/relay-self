import pytest

from experiments.focus_attention_epoch import (
    VIABILITY_INTERRUPT_KEY,
    attend_flee,
    build_attention_present,
    run_reference_fixture,
)
from experiments.present_skill_epoch import narrow_for_flee
from relay_self.intent import IntentCommitment, IntentEventKind
from relay_self.provenance import Provenance


def _owner(intent_id: str = "intent-focus") -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="test", reference=f"{intent_id}:commit"),
    )
    return owner


def test_same_flee_focus_has_different_attention_when_viability_changes() -> None:
    ordinary_owner = _owner("intent-ordinary")
    ordinary_broad = build_attention_present(
        intent_commitment=ordinary_owner,
        source_revision=1,
        viability_breach_imminent=False,
    )
    ordinary_local = narrow_for_flee(ordinary_broad)
    ordinary = attend_flee(
        broad=ordinary_broad,
        local=ordinary_local,
        current_source_revision=1,
        intent_commitment=ordinary_owner,
        at_ns=2,
    )

    critical_owner = _owner("intent-critical")
    critical_broad = build_attention_present(
        intent_commitment=critical_owner,
        source_revision=1,
        viability_breach_imminent=True,
    )
    critical_local = narrow_for_flee(critical_broad)
    critical = attend_flee(
        broad=critical_broad,
        local=critical_local,
        current_source_revision=1,
        intent_commitment=critical_owner,
        at_ns=2,
    )

    assert ordinary.focus == critical.focus == "FLEE"
    assert ordinary_local.facts == critical_local.facts
    assert ordinary.attended_keys == tuple(fact.key for fact in ordinary_local.facts)
    assert VIABILITY_INTERRUPT_KEY not in ordinary.attended_keys
    assert VIABILITY_INTERRUPT_KEY in critical.attended_keys
    assert ordinary.reconsideration_requested is False
    assert critical.reconsideration_requested is True


def test_attention_suppresses_ordinary_unrelated_broad_facts() -> None:
    owner = _owner()
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

    assert "route_open:cave" in attention.attended_keys
    assert "route_open:ridge" in attention.attended_keys
    assert "health" in attention.attended_keys
    assert "hunger" not in attention.attended_keys
    assert "companion_speaking" not in attention.attended_keys
    assert "weather" not in attention.attended_keys


def test_viability_interrupt_preserves_provenance_and_uses_existing_reconsideration_owner() -> None:
    owner = _owner()
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=True,
    )
    local = narrow_for_flee(broad)
    interrupt = broad.fact(VIABILITY_INTERRUPT_KEY)
    assert interrupt is not None

    attention = attend_flee(
        broad=broad,
        local=local,
        current_source_revision=1,
        intent_commitment=owner,
        at_ns=2,
    )

    attended_interrupt = next(
        fact
        for fact in attention.attended_facts
        if fact.key == VIABILITY_INTERRUPT_KEY
    )
    pending = owner.pending_reconsideration

    assert attended_interrupt is interrupt
    assert attended_interrupt.provenance == interrupt.provenance
    assert pending is not None
    assert pending.kind is IntentEventKind.RECONSIDERATION_REQUESTED
    assert pending.provenance == interrupt.provenance
    assert pending.reason == attention.interrupt_reason
    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "intent-focus"


def test_attention_does_not_mutate_skill_local_projection() -> None:
    owner = _owner()
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=True,
    )
    local = narrow_for_flee(broad)
    before = local.facts

    attention = attend_flee(
        broad=broad,
        local=local,
        current_source_revision=1,
        intent_commitment=owner,
        at_ns=2,
    )

    assert local.facts is before
    assert local.fact(VIABILITY_INTERRUPT_KEY) is None
    assert VIABILITY_INTERRUPT_KEY in attention.attended_keys


def test_stale_local_projection_fails_before_reconsideration_mutation() -> None:
    owner = _owner()
    broad = build_attention_present(
        intent_commitment=owner,
        source_revision=2,
        viability_breach_imminent=True,
    )
    stale = build_attention_present(
        intent_commitment=owner,
        source_revision=1,
        viability_breach_imminent=False,
    )
    stale_local = narrow_for_flee(stale)
    before = owner.events

    with pytest.raises(ValueError, match="local Present projection is stale"):
        attend_flee(
            broad=broad,
            local=stale_local,
            current_source_revision=2,
            intent_commitment=owner,
            at_ns=2,
        )

    assert owner.events is before
    assert owner.pending_reconsideration is None


def test_reference_fixture_reports_focus_stability_and_attention_shift() -> None:
    result = run_reference_fixture()

    assert result["ordinary"]["focus"] == "FLEE"
    assert result["critical"]["focus"] == "FLEE"
    assert result["ordinary"]["local_keys"] == result["critical"]["local_keys"]
    assert result["ordinary"]["reconsideration_requested"] is False
    assert result["critical"]["reconsideration_requested"] is True
    assert VIABILITY_INTERRUPT_KEY in result["critical"]["attended_keys"]
    assert (
        result["critical"]["pending_reconsideration_reference"]
        == "rev:1:viability-breach"
    )
