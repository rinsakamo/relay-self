"""Read-only original-S49-shaped two-probe L1 Target handoff (offline DEV).

Does NOT import, instantiate or grant the original unmerged S49 Owner,
ActionSupervisor, S15/S16 or #767 durable physical fence. It emits only a
typed witness for a later original-owner validation. No native Action issuer.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.cognitive_minimal_dev import SchemaFrame, Selection


class S49ShadowRefusal(ValueError):
    """Read-only candidate is not source/target qualified; issue nothing."""


@dataclass(frozen=True, slots=True)
class S49ReadOnlyHandoff:
    """One L1-selected target + two exact native witnesses; NEVER a grant."""

    evidence_class: str
    skill_id: str
    skill_version: int
    goal_id: str
    target_ref: str
    self_id: str
    proposed_intent_id: str
    schema_registry_revision: int
    session_id: str
    previous_probe_seq: int
    previous_probe_request_id: str
    current_probe_seq: int
    current_probe_request_id: str
    current_source_ref: str
    food_item: str | None = None
    food_slot: int | None = None
    target_entity_id: int | None = None
    original_s49_authorized: bool = False
    original_s49_intent_committed: bool = False
    original_s49_policy_verified: bool = False
    physical_action_issued: bool = False


def _stable_body(first: MineflayerObservation, second: MineflayerObservation) -> bool:
    return all(
        abs(getattr(first.snapshot.position, axis)
            - getattr(second.snapshot.position, axis)) <= 0.05
        for axis in ("x", "y", "z")
    )


def assess_s49_readonly_handoff(
    selection: Selection,
    *,
    original_frame: SchemaFrame,
    current_frame: SchemaFrame,
    previous_probe: MineflayerObservation,
    current_probe: MineflayerObservation,
    proposed_intent_id: str,
) -> S49ReadOnlyHandoff:
    """Check *selected* Skill/Target against original-S49-like native witnesses.

    This is a bounded, strictly non-issuing compatibility *precheck*. Original
    S49 must independently check its own post-move settling, intent epoch,
    PROPOSE/ISSUE grants, Action count, source and durable journal. Passing
    does not make a reservation, confer a physical Skill, or infer World safety.
    """
    if (
        not isinstance(proposed_intent_id, str)
        or not proposed_intent_id.strip()
        or not isinstance(selection, Selection)
        or selection.status != "READY"
        or selection.option is None
        or not isinstance(original_frame, SchemaFrame)
        or not isinstance(current_frame, SchemaFrame)
        or selection.world_scope != original_frame.scope
        or current_frame.scope != original_frame.scope
        or not any(
            goal.goal_id == selection.option.goal_id
            and goal.schema_id == selection.option.schema_id
            and goal.skill_id == selection.option.skill_id
            and goal.skill_version == selection.option.skill_version
            and not goal.unresolved
            for goal in current_frame.goals
        )
        or selection.option not in original_frame.options
        or selection.option not in current_frame.options
        or not isinstance(previous_probe, MineflayerObservation)
        or not isinstance(current_probe, MineflayerObservation)
    ):
        raise S49ShadowRefusal("selected Goal/Skill/Target or frame is not current")

    option = selection.option
    session = current_frame.scope.world_session_id
    if (
        not session
        or previous_probe.kind != "probe"
        or current_probe.kind != "probe"
        or previous_probe.session_id != session
        or current_probe.session_id != session
        or original_frame.source.source != "mineflayer"
        or current_frame.source != current_probe.provenance
        or previous_probe.provenance.source != "mineflayer"
        or current_probe.provenance.source != "mineflayer"
        or not previous_probe.request_id
        or not current_probe.request_id
        or previous_probe.request_id == current_probe.request_id
        or not previous_probe.seq < current_probe.seq <= previous_probe.seq + 32
        or previous_probe.snapshot.health <= 0
        or current_probe.snapshot.health <= 0
        or previous_probe.snapshot.oxygen_level == 0
        or current_probe.snapshot.oxygen_level == 0
        or not _stable_body(previous_probe, current_probe)
    ):
        raise S49ShadowRefusal("two correlated same-session steady probes required")

    common = {
        "evidence_class": "OFFLINE_OR_SHADOW_S49_READONLY_NOT_AUTHORIZED",
        "skill_id": option.skill_id,
        "skill_version": option.skill_version,
        "goal_id": option.goal_id,
        "target_ref": option.target_ref,
        "self_id": current_frame.scope.self_id,
        "proposed_intent_id": proposed_intent_id,
        "schema_registry_revision": current_frame.registry_revision,
        "session_id": session,
        "previous_probe_seq": previous_probe.seq,
        "previous_probe_request_id": previous_probe.request_id,
        "current_probe_seq": current_probe.seq,
        "current_probe_request_id": current_probe.request_id,
        "current_source_ref": current_probe.provenance.reference,
    }
    if option.skill_id == "EAT" and option.target_kind == "FOOD":
        if not option.target_ref.startswith("inventory:"):
            raise S49ShadowRefusal("selected food reference malformed")
        name = option.target_ref[len("inventory:"):]
        if not name:
            raise S49ShadowRefusal("selected food item missing")
        for probe in (previous_probe, current_probe):
            coverage = probe.snapshot.nearby_entities_coverage
            if (
                coverage.truncated
                or coverage.candidate_count != 0
                or probe.snapshot.nearby_entities
            ):
                raise S49ShadowRefusal("EAT has nearby/unknown entity coverage")
        before = {
            item.slot for item in previous_probe.snapshot.inventory
            if item.name == name and item.count > 0
        }
        after = {
            item.slot for item in current_probe.snapshot.inventory
            if item.name == name and item.count > 0
        }
        shared = before & after
        if not shared or len(shared) != 1:
            raise S49ShadowRefusal("selected food item slot not stable/unique")
        return S49ReadOnlyHandoff(
            **common, food_item=name, food_slot=next(iter(shared)),
        )

    if option.skill_id == "ATTACK" and option.target_kind == "ZOMBIE":
        if not option.target_ref.startswith("entity:"):
            raise S49ShadowRefusal("selected entity reference malformed")
        value = option.target_ref[len("entity:"):]
        if not value.isascii() or not value.isdecimal() or value.startswith("0") and value != "0":
            raise S49ShadowRefusal("selected entity identity malformed")
        target_id = int(value)
        if not _stable_body(previous_probe, current_probe):
            raise S49ShadowRefusal("Self moved during target observation")
        entity_positions = []
        for probe in (previous_probe, current_probe):
            coverage = probe.snapshot.nearby_entities_coverage
            entities = probe.snapshot.nearby_entities
            if (
                coverage.truncated or coverage.candidate_count != 1
                or len(entities) != 1
                or entities[0].name != "zombie"
                or entities[0].entity_id != target_id
                or not 0.1 <= entities[0].distance <= 2.8
            ):
                raise S49ShadowRefusal("same single near zombie not established")
            entity_positions.append(entities[0].position)
        if any(
            abs(getattr(entity_positions[0], k) - getattr(entity_positions[1], k)) > 0.25
            for k in ("x", "y", "z")
        ):
            raise S49ShadowRefusal("selected zombie moved during admission window")
        return S49ReadOnlyHandoff(**common, target_entity_id=target_id)

    raise S49ShadowRefusal("selected Skill is not a supported S49 shadow target")
