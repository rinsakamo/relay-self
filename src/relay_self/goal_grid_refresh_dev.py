"""One closed-S16, source-bound L1 local-grid refresh; no Action authority.

A revision is created from a NEW native cache packet only after a settled
waypoint and its genuine S16 OUTCOME. Stale paths are discarded, not appended.
Safety is bounded to the same loaded 42-column flat grid as revision one.
"""
from __future__ import annotations

import math

from relay_self.goal_detour_dev import L1DetourStageDev
from relay_self.goal_grid_search_dev import (
    L1GridRoutePlanDev,
    L1GridSearchDecisionDev,
    _find_path,
    _turns,
    swept_body_safe_dev,
)
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev
from relay_self.goal_navigation import GoalControlRejected
from relay_self.provenance import Provenance


def refresh_grid_route_dev(
    present: NativeVoxelPresentDev,
    previous: L1GridRoutePlanDev,
    *,
    last_s16_after_seq: int,
    last_closed_action_id: str,
    provenance: Provenance,
) -> L1GridSearchDecisionDev:
    """Replan from observed body position to the SAME parent L2 destination.

    Call-site must establish that there are no open Actions, that the last
    source Action is an OUTCOME, and that the preceding waypoint settled.
    This pure function separately checks the native source and pose lineage.
    """
    if (
        not isinstance(present, NativeVoxelPresentDev)
        or not isinstance(previous, L1GridRoutePlanDev)
        or present.session_id != previous.parent.session_id
        or type(last_s16_after_seq) is not int
        or last_s16_after_seq <= previous.source_voxel_seq
        or present.native_seq <= last_s16_after_seq
        or not isinstance(last_closed_action_id, str)
        or not last_closed_action_id
        or last_closed_action_id == previous.source_action_id
        or not isinstance(provenance, Provenance)
        or provenance.source == "mineflayer"
        or not math.isclose(
            present.origin_x, previous.parent.target_x, abs_tol=1e-8
        )
        or not math.isclose(
            present.origin_z + 4.0, previous.parent.target_z, abs_tol=1e-8
        )
        or previous.revision >= 12
        or abs(present.origin_x - (math.floor(present.origin_x) + 0.5)) > 0.03
        or abs(present.origin_z - (math.floor(present.origin_z) + 0.5)) > 0.03
    ):
        raise GoalControlRejected("grid refresh needs fresh settled native source")
    start = (
        round(present.player_x - present.origin_x),
        round(present.player_z - present.origin_z),
    )
    if (
        not -3 <= start[0] <= 3
        or not 0 <= start[1] <= 5
        or math.hypot(
            present.player_x - present.origin_x - start[0],
            present.player_z - present.origin_z - start[1],
        ) > 0.45
    ):
        raise GoalControlRejected("grid refresh body outside centered native map")
    path, visited = _find_path(present, start, (0, 4))
    if (len(path) < 2 or not swept_body_safe_dev(
        present, (present.player_x-present.origin_x,
                  present.player_z-present.origin_z), start
    )):
        return L1GridSearchDecisionDev(
            "DEFER", "NO_OBSERVED_BODY_SAFE_GRID_ROUTE",
            present.native_seq, 42, visited, (), None,
        )
    corners = _turns(path)
    if not 1 <= len(corners) <= 12:
        return L1GridSearchDecisionDev(
            "DEFER", "GRID_ROUTE_EXCEEDS_WAYPOINT_BUDGET",
            present.native_seq, 42, visited, path, None,
        )
    stages = tuple(
        L1DetourStageDev(
            stage_id=f"grid-turn-{i}",
            target_x=float(present.origin_x + x),
            target_z=float(present.origin_z + z),
        )
        for i, (x, z) in enumerate(corners)
    )
    plan = L1GridRoutePlanDev(
        parent=previous.parent,
        route_id=previous.route_id,
        revision=previous.revision + 1,
        source_action_id=last_closed_action_id,
        source_s16_seq=last_s16_after_seq,
        reason="NATIVE_GRID_REFRESH_AFTER_SETTLED_WAYPOINT",
        stages=stages,
        provenance=provenance,
        source_voxel_seq=present.native_seq,
        source_voxel_request_id=present.request_id,
        cell_path=path,
        no_diagonal_edges=True,
        body_radius_m=0.30,source_grid=present,
    )
    return L1GridSearchDecisionDev(
        "SELECTED", "BFS_CARDINAL_NATIVE_REFRESH_GRID",
        present.native_seq, 42, visited, path, plan,
    )
