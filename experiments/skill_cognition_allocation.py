from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from experiments.present_relay_engine_seam import build_flee_relay_request
from experiments.present_skill_epoch import (
    DecisionKind,
    FleeDecision,
    PresentFact,
    PresentProjection,
    bind_flee_destination,
    broaden_flee,
    build_present,
    narrow_for_flee,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
    RelayEngineResult,
)


class AllocationPath(str, Enum):
    DIRECT_SKILL_BINDING = "direct_skill_binding"
    CLOSED_SYSTEM_ONE = "closed_system_one"
    CLOSED_SYSTEM_TWO = "closed_system_two"
    BROADEN_WITHOUT_OPEN = "broaden_without_open"


@dataclass(frozen=True, slots=True)
class AllocationObservation:
    path: AllocationPath
    local_decision: FleeDecision
    final_decision: FleeDecision
    provider_modes: tuple[CognitionMode, ...]
    request_choice_ids: tuple[str, ...] = ()
    relay_result: RelayEngineResult | None = None


class RecordingProvider:
    """Experiment-local provider that records the same request across bounded escalation."""

    def __init__(self, *, bounded_choice: str | None, think_choice: str | None) -> None:
        self.bounded_choice = bounded_choice
        self.think_choice = think_choice
        self.calls: list[tuple[BoundedChoiceRequest, CognitionMode]] = []

    def __call__(
        self,
        request: BoundedChoiceRequest,
        *,
        mode: CognitionMode,
    ) -> ProviderDecision:
        self.calls.append((request, mode))
        if mode is CognitionMode.BOUNDED:
            if self.bounded_choice is None:
                return ProviderDecision.unresolved(reason="bounded fixture unresolved")
            return ProviderDecision.resolved(
                self.bounded_choice,
                reason="bounded fixture resolved",
            )
        if mode is CognitionMode.THINK:
            if self.think_choice is None:
                return ProviderDecision.unresolved(reason="think fixture unresolved")
            return ProviderDecision.resolved(
                self.think_choice,
                reason="think fixture resolved",
            )
        raise AssertionError("this bounded allocation fixture must never invoke OPEN")


def _commitment() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-mode-allocation",
        objective="reach safety",
        at_ns=1,
        provenance=Provenance(
            source="fixture",
            reference="intent:mode-allocation",
        ),
    )
    return owner


def _broad_present(
    *,
    one_open_route: bool,
) -> tuple[IntentCommitment, PresentProjection]:
    owner = _commitment()
    facts = (
        PresentFact(
            "threat_nearby",
            True,
            Provenance(source="fixture.world", reference="threat"),
        ),
        PresentFact(
            "health",
            6,
            Provenance(source="fixture.body", reference="health"),
        ),
        PresentFact(
            "safe_destinations",
            ("cave", "ridge"),
            Provenance(source="fixture.memory", reference="safe-destinations"),
        ),
        PresentFact(
            "route_open:cave",
            True,
            Provenance(source="fixture.world", reference="route:cave"),
        ),
        PresentFact(
            "route_open:ridge",
            not one_open_route,
            Provenance(source="fixture.world", reference="route:ridge"),
        ),
        PresentFact(
            "shelter:cave",
            True,
            Provenance(source="fixture.world", reference="shelter:cave"),
        ),
        PresentFact(
            "shelter:ridge",
            False,
            Provenance(source="fixture.world", reference="shelter:ridge"),
        ),
    )
    return owner, build_present(
        intent_commitment=owner,
        source_revision=1,
        facts=facts,
    )


def direct_binding_observation() -> AllocationObservation:
    """One grounded feasible destination should avoid model cognition entirely."""

    _, broad = _broad_present(one_open_route=True)
    local = narrow_for_flee(broad)
    decision = bind_flee_destination(local)
    if decision.kind is not DecisionKind.START:
        raise AssertionError("reference direct-binding case must resolve locally")
    return AllocationObservation(
        path=AllocationPath.DIRECT_SKILL_BINDING,
        local_decision=decision,
        final_decision=decision,
        provider_modes=(),
    )


def closed_system_one_observation() -> AllocationObservation:
    """Multiple grounded candidates enter CLOSED cognition and resolve cheaply."""

    _, broad = _broad_present(one_open_route=False)
    local = narrow_for_flee(broad)
    local_decision = bind_flee_destination(local)
    if local_decision.kind is not DecisionKind.ESCALATE:
        raise AssertionError("multi-route case must require bounded cognition")

    request = build_flee_relay_request(
        local,
        current_source_revision=1,
        request_id="mode-allocation:s1",
    )
    provider = RecordingProvider(bounded_choice="cave", think_choice=None)
    result = RelayEngine(provider)(request)
    final = FleeDecision(
        kind=(
            DecisionKind.START
            if result.status is DecisionStatus.RESOLVED
            else DecisionKind.ESCALATE
        ),
        reason="fixture RelayEngine result",
        destination=result.choice_id,
    )
    return AllocationObservation(
        path=AllocationPath.CLOSED_SYSTEM_ONE,
        local_decision=local_decision,
        final_decision=final,
        provider_modes=tuple(mode for _, mode in provider.calls),
        request_choice_ids=tuple(choice.choice_id for choice in request.choices),
        relay_result=result,
    )


def closed_system_two_observation() -> AllocationObservation:
    """The same CLOSED request escalates only execution depth when S1 is unresolved."""

    _, broad = _broad_present(one_open_route=False)
    local = narrow_for_flee(broad)
    local_decision = bind_flee_destination(local)
    request = build_flee_relay_request(
        local,
        current_source_revision=1,
        request_id="mode-allocation:s2",
    )
    provider = RecordingProvider(bounded_choice=None, think_choice="cave")
    result = RelayEngine(provider)(request)

    if len(provider.calls) != 2:
        raise AssertionError("reference S2 case must make exactly two bounded calls")
    first_request, first_mode = provider.calls[0]
    second_request, second_mode = provider.calls[1]
    if first_request is not second_request or first_request is not request:
        raise AssertionError("S1 -> S2 must preserve the same bounded request object")
    if (
        first_mode is not CognitionMode.BOUNDED
        or second_mode is not CognitionMode.THINK
    ):
        raise AssertionError("reference S2 case must preserve BOUNDED -> THINK order")

    final = FleeDecision(
        kind=(
            DecisionKind.START
            if result.status is DecisionStatus.RESOLVED
            else DecisionKind.ESCALATE
        ),
        reason="fixture RelayEngine result",
        destination=result.choice_id,
    )
    return AllocationObservation(
        path=AllocationPath.CLOSED_SYSTEM_TWO,
        local_decision=local_decision,
        final_decision=final,
        provider_modes=tuple(mode for _, mode in provider.calls),
        request_choice_ids=tuple(choice.choice_id for choice in request.choices),
        relay_result=result,
    )


def broaden_without_open_observation() -> AllocationObservation:
    """Missing projected evidence broadens first; it does not imply OPEN cognition."""

    _, broad = _broad_present(one_open_route=True)
    incomplete = narrow_for_flee(broad, include_route_status=False)
    local_decision = bind_flee_destination(incomplete)
    if local_decision.kind is not DecisionKind.ESCALATE:
        raise AssertionError("missing route evidence must not force a local winner")

    recovered = broaden_flee(incomplete, broad)
    final = bind_flee_destination(recovered)
    if final.kind is not DecisionKind.START:
        raise AssertionError("broadening should recover the grounded direct binding")

    return AllocationObservation(
        path=AllocationPath.BROADEN_WITHOUT_OPEN,
        local_decision=local_decision,
        final_decision=final,
        provider_modes=(),
    )


def run_reference_fixture() -> tuple[AllocationObservation, ...]:
    return (
        direct_binding_observation(),
        closed_system_one_observation(),
        closed_system_two_observation(),
        broaden_without_open_observation(),
    )
