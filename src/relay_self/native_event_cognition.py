"""S35 bounded native entity event -> explicit cognition request admission.

This module has no Mineflayer IO, no automatic scheduler, no Skill selection,
no Action/authorization/issue capability, and no model/LLM invocation.
The caller alone drives events, probes, admission and cognition. The
owner-local ledger is not global/restart-persistent or concurrency-safe.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
)
from relay_self.provenance import Provenance


class InvalidEventCognitionEvidence(ValueError):
    """Reject missing, forged, stale or ambiguous event/probe evidence."""


class EventCognitionNotAdmitted(ValueError):
    """No independent one-shot trigger authority; do not request cognition."""


MAX_EVENT_THREAT_DISTANCE_M = 4.0
NATIVE_COVERAGE_SCOPE = "mineflayer_entity_registry"
NATIVE_COVERAGE_MAX_DISTANCE_M = 16.0


@dataclass(frozen=True, slots=True)
class NativeEventCognitionCandidate:
    candidate_id: str
    session_id: str
    event_seq: int
    target_entity_id: int
    distance_m: float
    source_provenance: Provenance


@dataclass(frozen=True, slots=True)
class EventCognitionTriggerGrant:
    authority_id: str
    candidate_id: str
    session_id: str
    event_seq: int
    target_entity_id: int
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        if not self.authority_id or not isinstance(self.authority_id, str):
            raise EventCognitionNotAdmitted("nonempty separate grant authority required")
        if not self.candidate_id or not isinstance(self.candidate_id, str):
            raise EventCognitionNotAdmitted("exact event candidate ID required")
        if not isinstance(self.session_id, str) or not self.session_id:
            raise EventCognitionNotAdmitted("exact source session ID required")
        if (
            type(self.event_seq) is not int or self.event_seq < 0
            or type(self.target_entity_id) is not int or self.target_entity_id < 0
            or type(self.granted) is not bool
            or not isinstance(self.provenance, Provenance)
        ):
            raise EventCognitionNotAdmitted("malformed cognition grant or provenance")


@dataclass(frozen=True, slots=True)
class AdmittedNativeCognitionTicket:
    candidate: NativeEventCognitionCandidate
    correlated_probe: MineflayerObservation
    probe_request_id: str
    grant: EventCognitionTriggerGrant

    @property
    def event_id(self) -> str:
        return self.candidate.candidate_id


class EventCognitionLedger:
    """One-shot caller-exclusive event ledger; no automatic reentry.

    The caller must serialize admission and own this in memory, not infer a
    global replay lock or a cross-process exactly-once guarantee.
    """

    def __init__(self) -> None:
        self._seen_ids: set[str] = set()
        self._last_event_seq: dict[str, int] = {}

    def admit(
        self,
        candidate: NativeEventCognitionCandidate,
        probe: MineflayerObservation,
        grant: EventCognitionTriggerGrant,
        *,
        request_id: str,
    ) -> AdmittedNativeCognitionTicket:
        if (
            not isinstance(candidate, NativeEventCognitionCandidate)
            or not isinstance(probe, MineflayerObservation)
            or not isinstance(grant, EventCognitionTriggerGrant)
        ):
            raise EventCognitionNotAdmitted("typed candidate, probe, and grant required")
        if (
            not grant.granted
            or candidate.candidate_id != grant.candidate_id
            or candidate.session_id != grant.session_id
            or candidate.event_seq != grant.event_seq
            or candidate.target_entity_id != grant.target_entity_id
            or grant.provenance == candidate.source_provenance
        ):
            raise EventCognitionNotAdmitted("independent exact event trigger grant denied")
        if (
            not isinstance(request_id, str) or not request_id
            or probe.kind != "probe"
            or probe.request_id != request_id
            or probe.session_id != candidate.session_id
            or probe.seq <= candidate.event_seq
            or probe.provenance == candidate.source_provenance
            or probe.provenance.source != "mineflayer"
        ):
            raise InvalidEventCognitionEvidence(
                "probe not a newer separately correlated same-session World reading"
            )
        target = _single_native_zombie(probe)
        if (
            target is None
            or target.entity_id != candidate.target_entity_id
            or target.distance >= MAX_EVENT_THREAT_DISTANCE_M
        ):
            raise InvalidEventCognitionEvidence(
                "native target identity or nearby threat changed before cognition"
            )
        if candidate.candidate_id in self._seen_ids:
            raise EventCognitionNotAdmitted("replayed already-admitted event")
        last = self._last_event_seq.get(candidate.session_id, -1)
        if candidate.event_seq <= last:
            raise EventCognitionNotAdmitted("out of order event session cursor")
        self._seen_ids.add(candidate.candidate_id)
        self._last_event_seq[candidate.session_id] = candidate.event_seq
        return AdmittedNativeCognitionTicket(
            candidate=candidate, correlated_probe=probe,
            probe_request_id=request_id, grant=grant,
        )


def native_entity_event_to_cognition_candidate(
    event: MineflayerObservation,
) -> NativeEventCognitionCandidate | None:
    """Only an unsolicited real entity observation can request cognition.

    Nonentity events, empty/too-far coverage and disappearance are NOT
    evidence that the World is safe, and create no cognition request.
    Ambiguous or incomplete native source facts fail closed.
    """
    if not isinstance(event, MineflayerObservation):
        raise InvalidEventCognitionEvidence("typed native observation required")
    if event.kind != "entities":
        return None
    if event.request_id is not None or event.provenance.source != "mineflayer":
        raise InvalidEventCognitionEvidence("unsolicited native event provenance required")
    target = _single_native_zombie(event)
    if target is None or target.distance >= MAX_EVENT_THREAT_DISTANCE_M:
        return None
    return NativeEventCognitionCandidate(
        candidate_id=f"mineflayer-event:{event.session_id}:{event.seq}:entity-{target.entity_id}",
        session_id=event.session_id,
        event_seq=event.seq,
        target_entity_id=target.entity_id,
        distance_m=target.distance,
        source_provenance=event.provenance,
    )


def _single_native_zombie(
    observation: MineflayerObservation,
):
    coverage = observation.snapshot.nearby_entities_coverage
    entities = observation.snapshot.nearby_entities
    if (
        coverage.source_scope != NATIVE_COVERAGE_SCOPE
        or coverage.max_distance != NATIVE_COVERAGE_MAX_DISTANCE_M
        or coverage.truncated
        or coverage.candidate_count != len(entities)
    ):
        raise InvalidEventCognitionEvidence("native entity registry incomplete")
    zombies = tuple(entity for entity in entities if entity.name == "zombie")
    if not zombies:
        return None
    if len(zombies) != 1:
        raise InvalidEventCognitionEvidence("ambiguous zombie identity")
    target = zombies[0]
    origin = observation.snapshot.position
    pos = target.position
    d = math.dist((origin.x, origin.y, origin.z), (pos.x, pos.y, pos.z))
    if (
        not math.isfinite(d)
        or d > coverage.max_distance
        or not math.isclose(d, target.distance, rel_tol=0, abs_tol=1e-6)
    ):
        raise InvalidEventCognitionEvidence("entity distance/position mismatch")
    return target
