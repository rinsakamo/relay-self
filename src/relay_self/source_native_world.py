"""S27: exact Mineflayer protocol observation -> bounded postfailure evidence.

The boundary validates typed, source-native Mineflayer entity-registry facts
with exact Action3 session/sequence ancestry. It does NOT authenticate that
the bridge, network, timestamp, or physical Minecraft World is genuine.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MINEFLAYER_PROVENANCE_SOURCE,
    MineflayerEntityFact,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.postfailure_cognition import PostFailureWorldEvidence


class InvalidSourceNativeWorldEvidence(ValueError):
    """Typed Mineflayer observation, coverage, or freshness is not qualified."""


@dataclass(frozen=True, slots=True)
class SourceNativeThreatReceipt:
    """An audit view over one bounded, non-truncated target observation."""

    source: MineflayerObservation
    target_entity_id: int
    target_name: str
    parent_after_seq: int
    calculated_distance_m: float
    observed_at_ns: int
    inspected_at_ns: int
    max_age_ns: int
    evidence: PostFailureWorldEvidence


def project_source_native_threat(
    supervisor: ActionSupervisor,
    action: ActionLifecycle,
    consequence: WorldConsequence,
    observation: MineflayerObservation,
    *,
    target_entity_id: int,
    target_name: str,
    observed_at_ns: int,
    inspected_at_ns: int,
    max_age_ns: int,
) -> SourceNativeThreatReceipt:
    """Project one explicit entity id, never infer absence = safe.

    The adapter's recorded entity distance must agree with the Euclidean
    distance between the positions in the SAME source-native snapshot.
    Exactly identified entity and complete declared bounded coverage required.
    S24 can consume the resulting PostFailureWorldEvidence explicitly.
    """
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidSourceNativeWorldEvidence("requires the existing ActionSupervisor")
    if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
        raise InvalidSourceNativeWorldEvidence("requires a current Action snapshot")
    if action.state is not ActionState.OUTCOME:
        raise InvalidSourceNativeWorldEvidence("source Action must be OUTCOME")
    try:
        current = supervisor.get(action.action_id)
    except ValueError as exc:
        raise InvalidSourceNativeWorldEvidence("Action not supervised") from exc
    if current is not action:
        raise InvalidSourceNativeWorldEvidence("Action is not exact supervised terminal snapshot")
    if not isinstance(consequence, WorldConsequence):
        raise InvalidSourceNativeWorldEvidence("requires typed WorldConsequence")
    if consequence.status is not WorldConsequenceStatus.EXECUTED:
        raise InvalidSourceNativeWorldEvidence("WorldConsequence must be EXECUTED")
    if (
        consequence.action_id != action.action_id
        or consequence.session_id == ""
        or action.events[-1].provenance != consequence.provenance
        or consequence.after_observation is None
    ):
        raise InvalidSourceNativeWorldEvidence("Action/WorldConsequence lineage mismatch")
    after = consequence.after_observation
    if (
        after.session_id != consequence.session_id
        or after.kind != "probe"
        or after.provenance.source != MINEFLAYER_PROVENANCE_SOURCE
    ):
        raise InvalidSourceNativeWorldEvidence("parent World observation not source-native")
    if not isinstance(observation, MineflayerObservation):
        raise InvalidSourceNativeWorldEvidence("requires typed MineflayerObservation")
    if (
        observation.kind != "probe"
        or observation.session_id != consequence.session_id
        or observation.seq <= after.seq
        or observation.provenance.source != MINEFLAYER_PROVENANCE_SOURCE
        or observation.provenance == after.provenance
    ):
        raise InvalidSourceNativeWorldEvidence("stale, mismatched, or non-probe observation")
    if (
        not isinstance(target_entity_id, int)
        or isinstance(target_entity_id, bool)
        or target_entity_id < 0
    ):
        raise InvalidSourceNativeWorldEvidence("target entity id must be an integer")
    if target_name != "zombie":
        raise InvalidSourceNativeWorldEvidence("only exact caller-selected zombie is qualified")
    for name, value in (
        ("observed_at_ns", observed_at_ns),
        ("inspected_at_ns", inspected_at_ns),
        ("max_age_ns", max_age_ns),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise InvalidSourceNativeWorldEvidence(f"{name} must be nonnegative integer")
    if max_age_ns == 0:
        raise InvalidSourceNativeWorldEvidence("nonzero maximum age required")
    if observed_at_ns <= action.events[-1].at_ns:
        raise InvalidSourceNativeWorldEvidence("observation predates Action terminal")
    if not (observed_at_ns <= inspected_at_ns <= observed_at_ns + max_age_ns):
        raise InvalidSourceNativeWorldEvidence("stale or future observation")
    if supervisor.last_at_ns is None or inspected_at_ns < supervisor.last_at_ns:
        raise InvalidSourceNativeWorldEvidence("caller inspection clock moved backwards")

    coverage = observation.snapshot.nearby_entities_coverage
    if (
        coverage.source_scope != MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE
        or coverage.max_distance != MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE
        or coverage.truncated
        or coverage.candidate_count != len(observation.snapshot.nearby_entities)
    ):
        raise InvalidSourceNativeWorldEvidence("bounded entity coverage incomplete")
    matches = tuple(
        entity
        for entity in observation.snapshot.nearby_entities
        if entity.entity_id == target_entity_id
    )
    if len(matches) != 1:
        raise InvalidSourceNativeWorldEvidence("target absent or ambiguous: no safety inference")
    target: MineflayerEntityFact = matches[0]
    if target.name != target_name:
        raise InvalidSourceNativeWorldEvidence("entity identity/name changed")
    source = observation.snapshot.position
    target_pos = target.position
    calculated = math.dist(
        (source.x, source.y, source.z),
        (target_pos.x, target_pos.y, target_pos.z),
    )
    if (
        not math.isfinite(calculated)
        or calculated > coverage.max_distance
        or not math.isclose(target.distance, calculated, rel_tol=0, abs_tol=1e-6)
    ):
        raise InvalidSourceNativeWorldEvidence("adapter distance inconsistent with positions")
    # Deterministic round-half-up for the S24 integer-centimeter boundary.
    cm = math.floor(calculated * 100 + 0.5)
    projected = PostFailureWorldEvidence(
        evidence_id=f"mineflayer:{observation.session_id}:{observation.seq}:entity-{target_entity_id}",
        action_id=consequence.action_id,
        binding_id=consequence.binding_id,
        session_id=consequence.session_id,
        consequence_provenance=consequence.provenance,
        threat_clearance_cm=cm,
        observed_at_ns=observed_at_ns,
        provenance=observation.provenance,
    )
    return SourceNativeThreatReceipt(
        source=observation,
        target_entity_id=target_entity_id,
        target_name=target_name,
        parent_after_seq=after.seq,
        calculated_distance_m=calculated,
        observed_at_ns=observed_at_ns,
        inspected_at_ns=inspected_at_ns,
        max_age_ns=max_age_ns,
        evidence=projected,
    )
