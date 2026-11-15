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
from relay_self.approach_controller import (
    ApproachRecommendation,
    BodyApproachCapabilities,
    GaitMode,
    recommend_approach,
)
from relay_self.cognitive_minimal_dev import (
    SchemaFrame,
    Selection,
    WorldPercept,
)
from relay_self.common_io import ScopeRef
from relay_self.move_destination_ref import move_destination_ref
from relay_self.provenance import Provenance
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetBodyObservation,
    TargetContract,
    TargetContractRefusal,
    TargetKind,
)


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
    arrival_contract: TargetContract | None = None
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
            r"destination:[A-Za-z0-9][A-Za-z0-9._:-]{0,89}@[a-f0-9]{64}",
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
    destination_id = chosen.target_ref.removeprefix("destination:").split("@", 1)[0]
    matches = tuple(
        d for d in scenario.destinations if d.destination_id == destination_id
    )
    if len(matches) != 1:
        raise MoveTargetRefusal("selected destination no longer in configured registry")
    destination = matches[0]
    if (
        not isinstance(destination, ControlledDestination)
        or move_destination_ref(
            destination.destination_id, destination.position,
            destination.provenance,
        ) != chosen.target_ref
        or (
            chosen.arrival_contract is None
            and destination.arrival_condition is not None
        )
        or (
            chosen.arrival_contract is not None
            and (
                chosen.arrival_contract.condition != destination.arrival_condition
                or chosen.arrival_contract.scope != frame.scope
                or chosen.arrival_contract.provenance != destination.provenance
                or chosen.arrival_contract.goal_id != chosen.goal_id
                or chosen.arrival_contract.anchor != destination.position
            )
        )
        or not any(
            t.ref == chosen.target_ref
            and t.kind == "DESTINATION"
            and t.provenance == destination.provenance
            and t.world_session_id == frame.scope.world_session_id
            and t.observed_sequence == current_probe.seq
            and t.arrival_contract == chosen.arrival_contract
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
        arrival_contract=chosen.arrival_contract,
    )


def propose_arrival_contract_for_selected_move(
    target: ResolvedMoveTarget, condition: ArrivalCondition,
) -> TargetContract:
    """Propose a target-specific PLACE envelope without physical authority.

    The *existing* L1 Option selected the destination ref, not this new
    precision envelope. This function creates a separately SHA256-bound
    contract candidate for later L1/schema approval; it cannot silently
    install/authorize a new tolerance or alter an issued MOVE/WAL.
    """
    if (
        not isinstance(target, ResolvedMoveTarget)
        or target.arrival_contract is not None
        or target.status != "TARGET_BOUND_NO_PHYSICAL_MOVE_CAPABILITY"
        or target.physical_issued or target.reached or target.stop_settled_attested
        or target.skill_id != "MOVE" or target.skill_version != 1
        or not isinstance(condition, ArrivalCondition)
        or move_destination_ref(
            target.target_ref.removeprefix("destination:").split("@", 1)[0],
            target.destination_position, target.destination_provenance,
        ) != target.target_ref
    ):
        raise TargetContractRefusal("not an unchanged selected native MOVE target")
    return TargetContract(
        scope=target.scope,
        goal_id=target.goal_id,
        target_ref=target.target_ref,
        kind=TargetKind.PLACE,
        reference_frame=ReferenceFrame.WORLD,
        provenance=target.destination_provenance,
        condition=condition,
        bound_seq=target.native_seq,
        anchor=target.destination_position,
    )


def assess_l1_selected_move_approach(
    selection: Selection,
    bound: ResolvedMoveTarget,
    observed: TargetBodyObservation,
    capability: BodyApproachCapabilities,
    *,
    current_gait: GaitMode | None = None,
    route_clear: bool | None = None,
) -> ApproachRecommendation:
    """CPU-only bridge from actual numbered L1 choice to Target controller.

    No motor invocation or implicit revision of the selected arrival contract.
    A legacy unconditioned MOVE cannot acquire a policy after the selection;
    the caller must obtain a fresh L1 choice with declared semantics.
    """
    if (
        not isinstance(selection, Selection)
        or selection.status != "READY"
        or selection.option is None
        or not isinstance(bound, ResolvedMoveTarget)
        or bound.arrival_contract is None
        or selection.option.arrival_contract != bound.arrival_contract
        or selection.option.target_ref != bound.target_ref
        or selection.option.goal_id != bound.goal_id
        or bound.arrival_contract.target_ref != bound.target_ref
        or bound.arrival_contract.scope != bound.scope
        or bound.arrival_contract.goal_id != bound.goal_id
        or not isinstance(observed, TargetBodyObservation)
        or observed.scope != bound.scope
        or observed.seq < bound.native_seq
    ):
        raise TargetContractRefusal("no exact L1-selected current target precision contract")
    return recommend_approach(
        bound.arrival_contract, observed, capability,
        current_gait=current_gait, route_clear=route_clear,
    )
