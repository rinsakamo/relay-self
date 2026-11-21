from __future__ import annotations

from dataclasses import dataclass

from experiments.present_skill_epoch import (
    FLEE_SKILL_ID,
    PresentFact,
    PresentProjection,
    build_present,
    narrow_for_flee,
    projection_is_current,
    reference_facts,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance

VIABILITY_INTERRUPT_KEY = "viability_breach_imminent"


@dataclass(frozen=True, slots=True)
class FleeAttentionResult:
    focus: str
    attended_facts: tuple[PresentFact, ...]
    interrupt_reason: str | None
    reconsideration_requested: bool

    @property
    def attended_keys(self) -> tuple[str, ...]:
        return tuple(fact.key for fact in self.attended_facts)


def build_attention_present(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    viability_breach_imminent: bool,
) -> PresentProjection:
    facts = (
        *reference_facts(revision=source_revision),
        PresentFact(
            VIABILITY_INTERRUPT_KEY,
            viability_breach_imminent,
            Provenance(
                source="fixture.viability",
                reference=f"rev:{source_revision}:viability-breach",
            ),
        ),
        PresentFact(
            "weather",
            "clear",
            Provenance(
                source="fixture.world",
                reference=f"rev:{source_revision}:weather",
            ),
        ),
    )
    return build_present(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        facts=facts,
    )


def attend_flee(
    *,
    broad: PresentProjection,
    local: PresentProjection,
    current_source_revision: int,
    intent_commitment: IntentCommitment,
    at_ns: int,
) -> FleeAttentionResult:
    if local.focus != FLEE_SKILL_ID:
        raise ValueError("FLEE attention requires FLEE-local Focus")
    if broad.intent_id != local.intent_id:
        raise ValueError("broad and local Present require the same Current Intent")
    if not projection_is_current(
        broad,
        current_source_revision=current_source_revision,
    ):
        raise ValueError("broad Present projection is stale")
    if not projection_is_current(
        local,
        current_source_revision=current_source_revision,
    ):
        raise ValueError("local Present projection is stale")

    current = intent_commitment.current_intent
    if current is None or current.intent_id != local.intent_id:
        raise ValueError("FLEE attention requires the matching Current Intent")

    attended = list(local.facts)
    interrupt = broad.fact(VIABILITY_INTERRUPT_KEY)
    interrupt_reason = None
    reconsideration_requested = False

    if interrupt is not None and interrupt.value is True:
        attended.append(interrupt)
        interrupt_reason = "viability breach penetrated FLEE-local Focus"
        intent_commitment.request_reconsideration(
            local.intent_id,
            reason=interrupt_reason,
            at_ns=at_ns,
            provenance=interrupt.provenance,
        )
        reconsideration_requested = True

    return FleeAttentionResult(
        focus=local.focus,
        attended_facts=tuple(attended),
        interrupt_reason=interrupt_reason,
        reconsideration_requested=reconsideration_requested,
    )


def run_reference_fixture() -> dict[str, object]:
    ordinary_owner = IntentCommitment()
    ordinary_owner.commit(
        "intent-attention-ordinary",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference="intent:ordinary"),
    )
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

    critical_owner = IntentCommitment()
    critical_owner.commit(
        "intent-attention-critical",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference="intent:critical"),
    )
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

    pending = critical_owner.pending_reconsideration

    return {
        "ordinary": {
            "focus": ordinary.focus,
            "local_keys": tuple(fact.key for fact in ordinary_local.facts),
            "attended_keys": ordinary.attended_keys,
            "reconsideration_requested": ordinary.reconsideration_requested,
        },
        "critical": {
            "focus": critical.focus,
            "local_keys": tuple(fact.key for fact in critical_local.facts),
            "attended_keys": critical.attended_keys,
            "interrupt_reason": critical.interrupt_reason,
            "reconsideration_requested": critical.reconsideration_requested,
            "pending_reconsideration_reason": (
                pending.reason if pending is not None else None
            ),
            "pending_reconsideration_reference": (
                pending.provenance.reference if pending is not None else None
            ),
        },
    }
