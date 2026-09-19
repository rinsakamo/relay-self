from __future__ import annotations

from dataclasses import dataclass

from experiments.present_skill_epoch import (
    DecisionKind,
    FLEE_SKILL_ID,
    FleeDecision,
    PresentFact,
    PresentProjection,
    broaden_flee,
    build_present,
    narrow_for_flee,
    projection_is_current,
    start_flee_execution,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngine,
    RelayEngineResult,
)
from relay_self.skill import SkillExecution

MODEL_RELAY_SOURCE = "present-relay-seam"


class MissingPresentFactError(ValueError):
    def __init__(self, missing_keys: tuple[str, ...]) -> None:
        self.missing_keys = missing_keys
        super().__init__(
            "FLEE RelayEngine input is missing projected facts: "
            + ", ".join(missing_keys)
        )


@dataclass(frozen=True, slots=True)
class PresentRelayEpoch:
    broad: PresentProjection
    local: PresentProjection
    effective: PresentProjection
    request: BoundedChoiceRequest
    cognition: RelayEngineResult
    decision: FleeDecision
    execution: SkillExecution | None
    broadened: bool


def model_reference_facts(
    *,
    revision: int = 1,
) -> tuple[PresentFact, ...]:
    source = "fixture.world"
    return (
        PresentFact(
            "threat_nearby",
            True,
            Provenance(source=source, reference=f"rev:{revision}:threat"),
        ),
        PresentFact(
            "health",
            6,
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
            Provenance(
                source=source,
                reference=f"rev:{revision}:companion",
            ),
        ),
        PresentFact(
            "safe_destinations",
            ("cave", "ridge"),
            Provenance(
                source="fixture.memory",
                reference="safe-destinations:v1",
            ),
        ),
        PresentFact(
            "route_open:cave",
            True,
            Provenance(
                source=source,
                reference=f"rev:{revision}:route:cave",
            ),
        ),
        PresentFact(
            "route_open:ridge",
            True,
            Provenance(
                source=source,
                reference=f"rev:{revision}:route:ridge",
            ),
        ),
        PresentFact(
            "shelter:cave",
            True,
            Provenance(
                source=source,
                reference=f"rev:{revision}:shelter:cave",
            ),
        ),
        PresentFact(
            "shelter:ridge",
            False,
            Provenance(
                source=source,
                reference=f"rev:{revision}:shelter:ridge",
            ),
        ),
    )


def build_model_reference_present(
    *,
    intent_commitment: IntentCommitment,
    source_revision: int = 1,
) -> PresentProjection:
    return build_present(
        intent_commitment=intent_commitment,
        source_revision=source_revision,
        facts=model_reference_facts(revision=source_revision),
    )


def _required_destination_facts(
    local: PresentProjection,
) -> tuple[str, ...]:
    safe = local.fact("safe_destinations")
    if safe is None or not isinstance(safe.value, tuple):
        return ("safe_destinations",)
    destinations = tuple(
        destination
        for destination in safe.value
        if isinstance(destination, str) and destination
    )
    if len(destinations) != len(safe.value) or len(destinations) < 2:
        return ("safe_destinations",)
    required: list[str] = []
    for destination in destinations:
        required.extend(
            (
                f"route_open:{destination}",
                f"shelter:{destination}",
            )
        )
    return tuple(required)


def missing_flee_relay_keys(
    local: PresentProjection,
) -> tuple[str, ...]:
    required = (
        "threat_nearby",
        "health",
        "safe_destinations",
        *_required_destination_facts(local),
    )
    return tuple(
        key
        for key in required
        if local.fact(key) is None
    )


def build_flee_relay_request(
    local: PresentProjection,
    *,
    current_source_revision: int,
    request_id: str = "present-relay:00",
) -> BoundedChoiceRequest:
    if local.focus != FLEE_SKILL_ID:
        raise ValueError("FLEE RelayEngine request requires FLEE-local Focus")
    if not projection_is_current(
        local,
        current_source_revision=current_source_revision,
    ):
        raise ValueError(
            "stale Present projection cannot be sent to RelayEngine"
        )

    missing = missing_flee_relay_keys(local)
    if missing:
        raise MissingPresentFactError(missing)

    safe = local.fact("safe_destinations")
    assert safe is not None
    destinations = tuple(str(value) for value in safe.value)

    return BoundedChoiceRequest(
        request_id=request_id,
        instruction=(
            "Choose the safer currently reachable destination for the active "
            "FLEE skill. A destination is admissible only when its route_open "
            "fact is true. If both are reachable, prefer the destination whose "
            "shelter fact is true. If the supplied facts do not establish one "
            "unique preferred reachable destination, return unresolved. "
            "Use only supplied context."
        ),
        intent_id=local.intent_id,
        focus=local.focus,
        choices=tuple(
            BoundedChoice(
                destination,
                f"Destination {destination}",
            )
            for destination in destinations
        ),
        context=tuple(
            CognitionDatum.from_value(
                fact.key,
                fact.value,
                fact.provenance,
            )
            for fact in local.facts
        ),
    )


def relay_result_to_flee_decision(
    result: RelayEngineResult,
) -> FleeDecision:
    if (
        result.status is DecisionStatus.RESOLVED
        and result.choice_id is not None
    ):
        return FleeDecision(
            kind=DecisionKind.START,
            reason="RelayEngine resolved FLEE destination binding",
            destination=result.choice_id,
        )
    return FleeDecision(
        kind=DecisionKind.ESCALATE,
        reason="RelayEngine did not resolve FLEE destination binding",
    )


def run_flee_present_relay_epoch(
    *,
    engine: RelayEngine,
    broad: PresentProjection,
    local: PresentProjection,
    current_source_revision: int,
    intent_commitment: IntentCommitment,
    execution_id: str = "flee-present-relay-1",
    at_ns: int = 2,
) -> PresentRelayEpoch:
    if broad.intent_id != local.intent_id:
        raise ValueError(
            "broad and local Present projections require the same Current Intent"
        )
    if not projection_is_current(
        broad,
        current_source_revision=current_source_revision,
    ):
        raise ValueError("broad Present projection is stale")

    effective = local
    broadened = False
    try:
        request = build_flee_relay_request(
            effective,
            current_source_revision=current_source_revision,
        )
    except MissingPresentFactError:
        effective = broaden_flee(local, broad)
        broadened = True
        request = build_flee_relay_request(
            effective,
            current_source_revision=current_source_revision,
        )

    cognition = engine(request)
    decision = relay_result_to_flee_decision(cognition)
    execution = None
    if decision.kind is DecisionKind.START:
        execution = start_flee_execution(
            decision=decision,
            intent_commitment=intent_commitment,
            execution_id=execution_id,
            at_ns=at_ns,
            provenance=Provenance(
                source=MODEL_RELAY_SOURCE,
                reference="resolved-flee-binding",
            ),
        )

    return PresentRelayEpoch(
        broad=broad,
        local=local,
        effective=effective,
        request=request,
        cognition=cognition,
        decision=decision,
        execution=execution,
        broadened=broadened,
    )


def run_reference_epoch(
    engine: RelayEngine,
) -> PresentRelayEpoch:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-reach-safety",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(
            source=MODEL_RELAY_SOURCE,
            reference="intent:reach-safety",
        ),
    )
    broad = build_model_reference_present(
        intent_commitment=commitment,
        source_revision=1,
    )
    local = narrow_for_flee(broad)
    return run_flee_present_relay_epoch(
        engine=engine,
        broad=broad,
        local=local,
        current_source_revision=1,
        intent_commitment=commitment,
    )
