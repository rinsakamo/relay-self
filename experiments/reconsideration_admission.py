from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum

from experiments.present_skill_epoch import (
    PresentFact,
    PresentProjection,
    build_present,
)
from relay_self.intent import (
    IntentCommitment,
    IntentEvent,
    ReconsiderationDecision,
)
from relay_self.provenance import Provenance


class ReconsiderationAdmissionKind(str, Enum):
    KEEP_INTENT = "keep_intent"
    LOCAL_RECOVERY = "local_recovery"
    REQUEST_RECONSIDERATION = "request_reconsideration"


@dataclass(frozen=True, slots=True)
class ReconsiderationAdmission:
    kind: ReconsiderationAdmissionKind
    reason: str
    trigger_key: str | None = None


def _require_bool_fact(present: PresentProjection, key: str) -> bool:
    fact = present.fact(key)
    if fact is None or not isinstance(fact.value, bool):
        raise ValueError(f"{key} must be a projected boolean fact")
    return fact.value


def _require_text_fact(present: PresentProjection, key: str) -> str:
    fact = present.fact(key)
    if fact is None or not isinstance(fact.value, str) or not fact.value:
        raise ValueError(f"{key} must be a projected non-empty text fact")
    return fact.value


def _safe_destinations(present: PresentProjection) -> tuple[str, ...]:
    fact = present.fact("safe_destinations")
    if (
        fact is None
        or not isinstance(fact.value, tuple)
        or not fact.value
        or not all(isinstance(value, str) and value for value in fact.value)
    ):
        raise ValueError("safe_destinations must be a projected tuple of ids")
    return fact.value


def assess_reach_safety_reconsideration(
    present: PresentProjection,
    *,
    material_change_key: str,
) -> ReconsiderationAdmission:
    if present.objective != "reach safety":
        raise ValueError("fixture only evaluates the reach-safety Current Intent")
    if present.fact(material_change_key) is None:
        raise ValueError("material change must reference a projected fact")

    if not _require_bool_fact(present, "viability_acceptable"):
        return ReconsiderationAdmission(
            kind=ReconsiderationAdmissionKind.REQUEST_RECONSIDERATION,
            reason="current escape path is no longer acceptable under viability evidence",
            trigger_key="viability_acceptable",
        )

    destinations = _safe_destinations(present)
    current_destination = _require_text_fact(present, "current_destination")
    if current_destination not in destinations:
        raise ValueError("current_destination must belong to safe_destinations")

    route_status = {
        destination: _require_bool_fact(present, f"route_open:{destination}")
        for destination in destinations
    }
    open_destinations = tuple(
        destination for destination in destinations if route_status[destination]
    )

    if route_status[current_destination]:
        return ReconsiderationAdmission(
            kind=ReconsiderationAdmissionKind.KEEP_INTENT,
            reason="current local route remains feasible",
        )

    if open_destinations:
        return ReconsiderationAdmission(
            kind=ReconsiderationAdmissionKind.LOCAL_RECOVERY,
            reason="another local route remains feasible under the same Current Intent",
        )

    if _require_bool_fact(present, "route_catalog_complete"):
        return ReconsiderationAdmission(
            kind=ReconsiderationAdmissionKind.REQUEST_RECONSIDERATION,
            reason="grounded route evidence leaves no feasible local path",
            trigger_key=material_change_key,
        )

    return ReconsiderationAdmission(
        kind=ReconsiderationAdmissionKind.LOCAL_RECOVERY,
        reason="route evidence is incomplete; broaden local cognition before Intent-level reconsideration",
    )


def admit_reach_safety_reconsideration(
    *,
    present: PresentProjection,
    commitment: IntentCommitment,
    material_change_key: str,
    at_ns: int,
) -> tuple[ReconsiderationAdmission, IntentEvent | None]:
    current = commitment.current_intent
    if current is None or current.intent_id != present.intent_id:
        raise ValueError("Present must reference the actual Current Intent")

    admission = assess_reach_safety_reconsideration(
        present,
        material_change_key=material_change_key,
    )
    if admission.kind is not ReconsiderationAdmissionKind.REQUEST_RECONSIDERATION:
        return admission, None

    assert admission.trigger_key is not None
    trigger_fact = present.fact(admission.trigger_key)
    assert trigger_fact is not None
    request = commitment.request_reconsideration(
        current.intent_id,
        reason=admission.reason,
        at_ns=at_ns,
        provenance=trigger_fact.provenance,
    )
    return admission, request


def reach_safety_facts(
    *,
    revision: int,
    current_destination: str,
    routes: dict[str, bool],
    viability_acceptable: bool = True,
    route_catalog_complete: bool = True,
) -> tuple[PresentFact, ...]:
    destinations = tuple(routes)
    facts: list[PresentFact] = [
        PresentFact(
            "safe_destinations",
            destinations,
            Provenance(
                source="fixture.memory",
                reference=f"rev:{revision}:safe-destinations",
            ),
        ),
        PresentFact(
            "current_destination",
            current_destination,
            Provenance(
                source="fixture.control",
                reference=f"rev:{revision}:current-destination",
            ),
        ),
        PresentFact(
            "route_catalog_complete",
            route_catalog_complete,
            Provenance(
                source="fixture.world",
                reference=f"rev:{revision}:route-catalog-complete",
            ),
        ),
        PresentFact(
            "viability_acceptable",
            viability_acceptable,
            Provenance(
                source="fixture.body",
                reference=f"rev:{revision}:viability",
            ),
        ),
    ]
    facts.extend(
        PresentFact(
            f"route_open:{destination}",
            is_open,
            Provenance(
                source="fixture.world",
                reference=f"rev:{revision}:route:{destination}",
            ),
        )
        for destination, is_open in routes.items()
    )
    return tuple(facts)


def _project(
    commitment: IntentCommitment,
    *,
    revision: int,
    current_destination: str,
    routes: dict[str, bool],
    viability_acceptable: bool = True,
    route_catalog_complete: bool = True,
) -> PresentProjection:
    return build_present(
        intent_commitment=commitment,
        source_revision=revision,
        facts=reach_safety_facts(
            revision=revision,
            current_destination=current_destination,
            routes=routes,
            viability_acceptable=viability_acceptable,
            route_catalog_complete=route_catalog_complete,
        ),
    )


def _step_row(
    *,
    event_id: str,
    admission: ReconsiderationAdmission,
    request: IntentEvent | None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "admission": admission.kind.value,
        "reason": admission.reason,
        "request_created": request is not None,
        "request_provenance": (
            {
                "source": request.provenance.source,
                "reference": request.provenance.reference,
            }
            if request is not None
            else None
        ),
    }


def run_reference_fixture() -> dict[str, object]:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-safe-107",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(source="fixture", reference="intent:reach-safety"),
    )

    steps: list[dict[str, object]] = []

    present = _project(
        commitment,
        revision=1,
        current_destination="cave",
        routes={"cave": False, "ridge": True},
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:cave",
        at_ns=2,
    )
    steps.append(
        _step_row(event_id="route_a_blocked", admission=admission, request=request)
    )

    present = _project(
        commitment,
        revision=2,
        current_destination="ridge",
        routes={"cave": False, "ridge": True},
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:ridge",
        at_ns=2,
    )
    steps.append(
        _step_row(event_id="route_b_still_available", admission=admission, request=request)
    )

    present = _project(
        commitment,
        revision=3,
        current_destination="ridge",
        routes={"cave": False, "ridge": False},
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:ridge",
        at_ns=2,
    )
    steps.append(
        _step_row(event_id="all_local_routes_lost", admission=admission, request=request)
    )
    first_request = commitment.pending_reconsideration
    assert first_request is not None
    commitment.reconsider(
        "intent-safe-107",
        decision=ReconsiderationDecision.CONTINUE,
        reason="objective remains valid while waiting for new route evidence",
        at_ns=3,
        provenance=Provenance(
            source="fixture.policy",
            reference="decision:continue:wait-for-route",
        ),
    )

    present = _project(
        commitment,
        revision=4,
        current_destination="ridge",
        routes={"cave": False, "ridge": False, "tower": True},
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="route_open:tower",
        at_ns=3,
    )
    steps.append(
        _step_row(event_id="new_safe_route_appears", admission=admission, request=request)
    )

    present = _project(
        commitment,
        revision=5,
        current_destination="tower",
        routes={"cave": False, "ridge": False, "tower": True},
        viability_acceptable=False,
    )
    admission, request = admit_reach_safety_reconsideration(
        present=present,
        commitment=commitment,
        material_change_key="viability_acceptable",
        at_ns=4,
    )
    steps.append(
        _step_row(event_id="viability_deteriorates", admission=admission, request=request)
    )
    second_request = commitment.pending_reconsideration
    assert second_request is not None
    commitment.reconsider(
        "intent-safe-107",
        decision=ReconsiderationDecision.RELEASE,
        reason="continued escape attempt is no longer acceptable under viability evidence",
        at_ns=5,
        provenance=Provenance(
            source="fixture.policy",
            reference="decision:release:viability",
        ),
    )

    return {
        "steps": steps,
        "intent_events": [
            {
                "kind": event.kind.value,
                "source": event.provenance.source,
                "reference": event.provenance.reference,
            }
            for event in commitment.events
        ],
        "first_request_reference": first_request.provenance.reference,
        "first_decision_reference": commitment.events[2].provenance.reference,
        "second_request_reference": second_request.provenance.reference,
        "second_decision_reference": commitment.events[-1].provenance.reference,
        "final_current_intent": (
            commitment.current_intent.intent_id
            if commitment.current_intent is not None
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic reconsideration-admission fixture."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    result = run_reference_fixture()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Reconsideration-admission fixture")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
