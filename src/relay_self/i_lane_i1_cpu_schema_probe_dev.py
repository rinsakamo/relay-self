"""I1 partial: source-bound CPU Schema probe from the original B Owner.

No verified Action catalog or target binding exists in this slice: it can only
form bounded *cognitive* L1 proposals, never an executable physical option.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.cognitive_minimal_dev import (
    L1Round,
    SchemaFrame,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
)
from relay_self.i_lane_cpu_readout_dev import I0OwnerCPUReadout, read_i0_owner_cpu
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class I1CPUProbeHold(RuntimeError):
    """No coherent original-owned CPU Schema input was qualified."""


@dataclass(frozen=True, slots=True)
class I1CPUProbe:
    original: I0OwnerCPUReadout
    percept: WorldPercept
    schema: SchemaFrame
    l1_proposal: L1Round
    action_issue_authorized: bool = False
    model_invoked: bool = False


def _exact_food(value: object) -> int | None:
    # Do not manufacture a discrete hunger observation by rounding sensor data.
    if type(value) is int and 0 <= value <= 20:
        return value
    if type(value) is float and value.is_integer() and 0 <= value <= 20:
        return int(value)
    return None


def prepare_i1_cpu_schema_probe(*, bridge, boot, world, links, self_id: str,
                                i1_require_correlated_sense: bool = False,
                                i2b_read_attached_lane: bool = False) -> I1CPUProbe:
    """Current original native probe -> CPU Schema -> *unissued* L1 options.

    A missing qualified Action catalog intentionally yields no executable
    Skill/Target binding. This does not connect E SENSE, normal scheduling,
    provider inference, or the physical issuer.
    """
    resident = getattr(bridge, "cognitive_work", None)
    if not isinstance(resident, ResidentCognitiveWorkOwner):
        raise I1CPUProbeHold("original cognitive resident required")
    with resident.lock:
        original = read_i0_owner_cpu(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i1_complete_paper_prefix=True,
            i1_require_correlated_sense=i1_require_correlated_sense,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        owner = bridge.owners[self_id]
        original_probe = owner.current_worldbody_observation
        if not isinstance(original_probe, MineflayerObservation):
            raise I1CPUProbeHold("original native WorldBody observation required")
        sense = (bridge.current_i1_correlated_sense(self_id)
                 if i1_require_correlated_sense else bridge.current_sense(self_id))
        if i1_require_correlated_sense and sense is None:
            raise I1CPUProbeHold("I1 exact matched observe reply missing or stale")
        # E is a native observation and must share the exact B Present revision.
        # It cannot authorize a Target or physical Action; it can update
        # the *current* CPU percept without rewriting the original login probe.
        if sense is None:
            if len(original.source_revision_refs) != 2:
                raise I1CPUProbeHold("SENSE lost after original Present projection")
            observation = original_probe
        else:
            if (len(original.source_revision_refs) != 3
                    or original.source_revision_refs[-1] != sense.source_revision_ref
                    or sense.scope != original.present.present.three_self.scope
                    or sense.observation.session_id != original.present.source.native_session_id):
                raise I1CPUProbeHold("current SENSE and qualified B Present disagree")
            observation = sense.observation
        snapshot = observation.snapshot
        # A recognized native entity is a possible defensive cue only;
        # it is NOT a Target, Action capability, or verified physical threat.
        threat_cue = any(
            entity.name == "zombie" or entity.entity_type == "zombie"
            for entity in snapshot.nearby_entities
        )
        percept = WorldPercept(
            scope=original.present.present.three_self.scope,
            source=observation.provenance,
            sequence=observation.seq,
            hunger=_exact_food(snapshot.food),
            fatigue_high=None,
            targets=(),
            threat_cue=threat_cue,
            exploration_need=original.present.exploration_need is not None,
            oxygen_reserve=snapshot.oxygen_level,
        )
        schema = cpu_schema_epoch(
            percept, owner.pattern_registry,
            allowed_skills=frozenset(),  # NO verified executable catalog.
            epoch=original.present.source.resident_epoch,
        )
        l1_proposal = assemble_l1_select(
            schema, intent_owner=owner.intent, recent_3self=(),
        )
        after = read_i0_owner_cpu(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i1_complete_paper_prefix=True,
            i1_require_correlated_sense=i1_require_correlated_sense,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        if (after != original
                or owner.current_worldbody_observation is not original_probe
                or (bridge.current_i1_correlated_sense(self_id)
                    if i1_require_correlated_sense else bridge.current_sense(self_id)) is not sense):
            raise I1CPUProbeHold("original WorldBody/SENSE/Present changed during CPU probe")
        return I1CPUProbe(original, percept, schema, l1_proposal)
