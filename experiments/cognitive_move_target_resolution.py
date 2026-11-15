"""Resolve an L1-selected MOVE destination without claiming physical locomotion.

This is a CPU-only *binding* seam. ControlledDestination is an explicitly
configured source claim, not a Minecraft/Paper observation, path, permission,
motion primitive, or reachability result. MOVE issuer and STOP/settling remain
unqualified; no ActionPort, network, WAL or native controls are invoked.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerPosition,
    mineflayer_yaw_to_target,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
)
from relay_self.cognitive_minimal_dev import (
    SchemaFrame,
    Selection,
    WorldPercept,
)
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance


class MoveTargetRefusal(ValueError):
    """Cannot bind selected MOVE to a current distinct configured position."""


@dataclass(frozen=True, slots=True)
class ResolvedMoveTarget:
    """Geometric L1 MOVE target, explicitly NOT a physical Action authorization."""

    scope: ScopeRef
    goal_id: str
    skill_id: str
    skill_version: int
    target_ref: str
    destination_position: MineflayerPosition
    native_position: MineflayerPosition
    yaw_rad: float
    horizontal_distance: float
    vertical_delta: float
    destination_provenance: Provenance
    native_probe_provenance: Provenance
    native_seq: int
    native_request_id: str
    status: str = "TARGET_BOUND_NO_PHYSICAL_MOVE_CAPABILITY"
    physical_issued: bool = False
    reached: bool = False
    stop_settled_attested: bool = False


def resolve_selected_move_target(
    selection: Selection,
    *,
    frame: SchemaFrame,
    percept: WorldPercept,
    current_probe: MineflayerObservation,
    scenario: ControlledScenario,
) -> ResolvedMoveTarget:
    """Bind an *existing L1-selected Option* to a configured DESTINATION.

    No automatically generated destination. No fallback on unknown/expired
    target. Destination provenance is distinct from the Mineflayer body
    observation; exact identity and current session/sequence are required.
    """
    if (
        not isinstance(selection, Selection)
        or selection.status != "READY"
        or selection.option is None
        or not isinstance(frame, SchemaFrame)
        or not isinstance(percept, WorldPercept)
        or not isinstance(current_probe, MineflayerObservation)
        or not isinstance(scenario, ControlledScenario)
    ):
        raise MoveTargetRefusal("resolved L1 MOVE selection and typed evidence required")
    chosen = selection.option
    if (
        chosen.skill_id != "MOVE" or chosen.skill_version != 1
        or chosen.goal_id != "EXPLORE_WORLD"
        or chosen.target_kind != "DESTINATION"
        or chosen.schema_id != "exploration"
        or chosen.pattern_id != "exploration-move"
        or not re.fullmatch(
            r"destination:[A-Za-z0-9][A-Za-z0-9._:-]{0,89}",
            chosen.target_ref,
        )
        or selection.world_scope != frame.scope
        or percept.scope != frame.scope
        or not frame.scope.world_session_id
        or chosen not in frame.options
        or not any(
            g.goal_id == chosen.goal_id
            and g.schema_id == chosen.schema_id
            and g.skill_id == chosen.skill_id and g.skill_version == 1
            and not g.unresolved
            for g in frame.goals
        )
        or percept.source != frame.source
        or frame.source != current_probe.provenance
        or percept.sequence != current_probe.seq
        or current_probe.session_id != frame.scope.world_session_id
        or current_probe.kind != "probe"
        or not current_probe.request_id
        or current_probe.snapshot.health <= 0
        or current_probe.snapshot.oxygen_level == 0
        or not percept.exploration_need
    ):
        raise MoveTargetRefusal("MOVE Goal/Target/WorldBody observation stale or unselected")
    destination_id = chosen.target_ref.removeprefix("destination:")
    matches = tuple(
        d for d in scenario.destinations if d.destination_id == destination_id
    )
    if len(matches) != 1:
        raise MoveTargetRefusal("selected destination no longer in configured registry")
    destination = matches[0]
    if (
        not isinstance(destination, ControlledDestination)
        or destination.provenance.source == "mineflayer"
        or not any(
            t.ref == chosen.target_ref
            and t.kind == "DESTINATION"
            and t.provenance == destination.provenance
            and t.world_session_id == frame.scope.world_session_id
            and t.observed_sequence == current_probe.seq
            and t.live
            for t in percept.targets
        )
    ):
        raise MoveTargetRefusal("missing or laundered destination provenance")
    start = current_probe.snapshot.position
    end = destination.position
    distance = math.hypot(end.x - start.x, end.z - start.z)
    if distance <= 0 or not math.isfinite(distance):
        raise MoveTargetRefusal("MOVE target is not distinct horizontal position")
    yaw = mineflayer_yaw_to_target(start, end)
    # The yaw is only mathematical guidance, never proof of path safety.
    return ResolvedMoveTarget(
        scope=frame.scope,
        goal_id=chosen.goal_id,
        skill_id=chosen.skill_id,
        skill_version=chosen.skill_version,
        target_ref=chosen.target_ref,
        destination_position=end,
        native_position=start,
        yaw_rad=yaw,
        horizontal_distance=distance,
        vertical_delta=end.y - start.y,
        destination_provenance=destination.provenance,
        native_probe_provenance=current_probe.provenance,
        native_seq=current_probe.seq,
        native_request_id=current_probe.request_id,
    )
