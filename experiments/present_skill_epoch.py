from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

FLEE_SKILL_ID = "FLEE"
FLEE_REQUIRED_KEYS = ("threat_nearby", "health", "safe_destinations")


class DecisionKind(str, Enum):
    START = "start"
    ESCALATE = "escalate"
    DEFER = "defer"


class FixtureEvent(str, Enum):
    AMBIENT_OBSERVATION = "ambient_observation"
    ROUTE_OBSERVATION = "route_observation"
    SUPERVISION_DEADLINE = "supervision_deadline"
    SKILL_LOCAL_UNCERTAINTY = "skill_local_uncertainty"
    CONSEQUENCE_MISMATCH = "consequence_mismatch"
    QUIET = "quiet"


class EpochDisposition(str, Enum):
    IGNORE = "ignore"
    DECISION_EPOCH_NO_MODEL = "decision_epoch_no_model"
    DECISION_EPOCH_WITH_RELAYENGINE = "decision_epoch_with_relayengine"


@dataclass(frozen=True, slots=True)
class PresentFact:
    key: str
    value: object
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class PresentProjection:
    intent_id: str
    objective: str
    source_revision: int
    facts: tuple[PresentFact, ...]
    focus: str | None = None

    def fact(self, key: str) -> PresentFact | None:
        for fact in self.facts:
            if fact.key == key:
                return fact
        return None


@dataclass(frozen=True, slots=True)
class FleeDecision:
    kind: DecisionKind
    reason: str
    destination: str | None = None
    missing_keys: tuple[str, ...] = ()


def build_present(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int,
    facts: Iterable[PresentFact],
) -> PresentProjection:
    current = intent_commitment.current_intent
    if current is None:
        raise ValueError("Present projection requires a Current Intent")
    if source_revision < 0:
        raise ValueError("source_revision must be non-negative")
    return PresentProjection(
        intent_id=current.intent_id,
        objective=current.objective,
        source_revision=source_revision,
        facts=tuple(facts),
    )


def admit_flee_candidate(present: PresentProjection) -> bool:
    threat = present.fact("threat_nearby")
    return present.objective == "reach safety" and threat is not None and threat.value is True


def narrow_for_flee(
    present: PresentProjection,
    *,
    include_route_status: bool = True,
) -> PresentProjection:
    selected: list[PresentFact] = []
    for fact in present.facts:
        if fact.key in FLEE_REQUIRED_KEYS:
            selected.append(fact)
        elif include_route_status and fact.key.startswith("route_open:"):
            selected.append(fact)

    return PresentProjection(
        intent_id=present.intent_id,
        objective=present.objective,
        source_revision=present.source_revision,
        facts=tuple(selected),
        focus=FLEE_SKILL_ID,
    )


def bind_flee_destination(local: PresentProjection) -> FleeDecision:
    if local.focus != FLEE_SKILL_ID:
        return FleeDecision(
            kind=DecisionKind.ESCALATE,
            reason="FLEE binding requires FLEE-local Focus",
        )

    missing_required = tuple(
        key for key in FLEE_REQUIRED_KEYS if local.fact(key) is None
    )
    if missing_required:
        return FleeDecision(
            kind=DecisionKind.ESCALATE,
            reason="required FLEE-local facts are not projected",
            missing_keys=missing_required,
        )

    safe_destinations_fact = local.fact("safe_destinations")
    assert safe_destinations_fact is not None
    safe_destinations = safe_destinations_fact.value
    if not isinstance(safe_destinations, tuple) or not all(
        isinstance(destination, str) and destination
        for destination in safe_destinations
    ):
        return FleeDecision(
            kind=DecisionKind.ESCALATE,
            reason="safe_destinations is not a bounded tuple of destination ids",
        )

    route_keys = tuple(f"route_open:{destination}" for destination in safe_destinations)
    missing_routes = tuple(key for key in route_keys if local.fact(key) is None)
    if missing_routes:
        return FleeDecision(
            kind=DecisionKind.ESCALATE,
            reason="route evidence was omitted by the current narrow projection",
            missing_keys=missing_routes,
        )

    open_destinations = tuple(
        destination
        for destination in safe_destinations
        if local.fact(f"route_open:{destination}").value is True
    )
    if len(open_destinations) == 1:
        return FleeDecision(
            kind=DecisionKind.START,
            reason="one safe destination has explicit open-route evidence",
            destination=open_destinations[0],
        )
    if not open_destinations:
        return FleeDecision(
            kind=DecisionKind.ESCALATE,
            reason="no safe destination has explicit open-route evidence",
        )
    return FleeDecision(
        kind=DecisionKind.ESCALATE,
        reason="multiple feasible destinations require a bounded cognition decision",
    )


def broaden_flee(local: PresentProjection, broad: PresentProjection) -> PresentProjection:
    if local.intent_id != broad.intent_id:
        raise ValueError("cannot broaden across different Current Intents")
    if local.source_revision != broad.source_revision:
        raise ValueError("cannot broaden from a stale or different source revision")
    return narrow_for_flee(broad, include_route_status=True)


def projection_is_current(
    projection: PresentProjection,
    *,
    current_source_revision: int,
) -> bool:
    return projection.source_revision == current_source_revision


def start_flee_execution(
    *,
    decision: FleeDecision,
    intent_commitment: IntentCommitment,
    execution_id: str,
    at_ns: int,
    provenance: Provenance,
) -> SkillExecution:
    if decision.kind is not DecisionKind.START or decision.destination is None:
        raise ValueError("only a resolved START decision may start FLEE")
    return SkillExecution.start(
        execution_id,
        skill_id=FLEE_SKILL_ID,
        intent_commitment=intent_commitment,
        at_ns=at_ns,
        provenance=provenance,
    )


def classify_event(event: FixtureEvent) -> EpochDisposition:
    if event in {FixtureEvent.AMBIENT_OBSERVATION, FixtureEvent.QUIET}:
        return EpochDisposition.IGNORE
    if event in {
        FixtureEvent.ROUTE_OBSERVATION,
        FixtureEvent.SUPERVISION_DEADLINE,
    }:
        return EpochDisposition.DECISION_EPOCH_NO_MODEL
    if event in {
        FixtureEvent.SKILL_LOCAL_UNCERTAINTY,
        FixtureEvent.CONSEQUENCE_MISMATCH,
    }:
        return EpochDisposition.DECISION_EPOCH_WITH_RELAYENGINE
    raise ValueError(f"unsupported fixture event: {event}")


def reference_facts(*, revision: int = 1) -> tuple[PresentFact, ...]:
    source = "fixture.world"
    return (
        PresentFact(
            "threat_nearby",
            True,
            Provenance(source=source, reference=f"rev:{revision}:threat"),
        ),
        PresentFact(
            "health",
            8,
            Provenance(source=source, reference=f"rev:{revision}:health"),
        ),
        PresentFact(
            "hunger",
            12,
            Provenance(source=source, reference=f"rev:{revision}:hunger"),
        ),
        PresentFact(
            "companion_speaking",
            True,
            Provenance(source=source, reference=f"rev:{revision}:companion"),
        ),
        PresentFact(
            "safe_destinations",
            ("cave", "ridge"),
            Provenance(source="fixture.memory", reference="safe-destinations:v1"),
        ),
        PresentFact(
            "route_open:cave",
            True,
            Provenance(source=source, reference=f"rev:{revision}:route:cave"),
        ),
        PresentFact(
            "route_open:ridge",
            False,
            Provenance(source=source, reference=f"rev:{revision}:route:ridge"),
        ),
    )


def run_reference_fixture() -> dict[str, object]:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe-1",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference="intent:reach-safety"),
    )
    broad = build_present(
        intent_commitment=commitment,
        source_revision=1,
        facts=reference_facts(revision=1),
    )
    local = narrow_for_flee(broad)
    decision = bind_flee_destination(local)
    misleading = narrow_for_flee(broad, include_route_status=False)
    misleading_decision = bind_flee_destination(misleading)
    recovered = bind_flee_destination(broaden_flee(misleading, broad))
    execution = start_flee_execution(
        decision=decision,
        intent_commitment=commitment,
        execution_id="flee-exec-1",
        at_ns=2,
        provenance=Provenance(source="fixture", reference="flee:start"),
    )

    epoch_matrix = {
        event.value: classify_event(event).value
        for event in FixtureEvent
    }
    return {
        "broad_fact_count": len(broad.facts),
        "narrow_fact_count": len(local.facts),
        "candidate_admitted": admit_flee_candidate(broad),
        "decision": {
            "kind": decision.kind.value,
            "destination": decision.destination,
            "reason": decision.reason,
        },
        "misleading_narrow": {
            "kind": misleading_decision.kind.value,
            "missing_keys": misleading_decision.missing_keys,
            "recovered_kind": recovered.kind.value,
            "recovered_destination": recovered.destination,
        },
        "skill_execution": {
            "execution_id": execution.execution_id,
            "skill_id": execution.skill_id,
            "intent_id": execution.intent_id,
            "state": execution.state.value,
        },
        "epoch_matrix": epoch_matrix,
        "old_projection_is_current_after_revision_advance": projection_is_current(
            local,
            current_source_revision=2,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Present / FLEE / decision-epoch fixture."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = run_reference_fixture()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Present / FLEE / decision-epoch fixture")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
