"""DEV L1 grid revision tests: fresh native packet, same L2, no stale cells."""
from dataclasses import replace

import pytest

from relay_self.goal_grid_refresh_dev import refresh_grid_route_dev
from relay_self.goal_grid_search_dev import choose_grid_route_dev
from relay_self.goal_navigation import GoalControlRejected
from relay_self.provenance import Provenance
from test_s49_l1_grid_search_dev import _goal
from test_s49_l1_local_voxel_dev import grid


def _refresh(*, block_middle=True):
    raw = grid(left_block=True)
    initial = choose_grid_route_dev(
        raw, _goal(), blocked_after_seq=33,
        blocked_action_id="original-unknown",
        provenance=Provenance("test-L1", "first-native-grid"),
    ).plan
    assert initial is not None
    cells = tuple(
        replace(c, feet="BLOCKED")
        if block_middle and c.dx == 2 and c.dz == 2 else c
        for c in raw.cells
    )
    live = replace(
        raw, native_seq=60, request_id="refresh-after-settled-55",
        player_x=2.5, player_z=11.5, cells=cells,
        provenance=Provenance("mineflayer", f"{raw.session_id}:60"),
    )
    return initial, live


def _decide(original, live, **overrides):
    return refresh_grid_route_dev(
        live, original,
        last_s16_after_seq=overrides.get("last_s16_after_seq", 55),
        last_closed_action_id=overrides.get(
            "last_closed_action_id", "stage-zero-outcome"
        ),
        provenance=Provenance("test-L1", "waypoint-reobserve"),
    )


def test_new_obstacle_changes_remaining_path_and_preserves_l2():
    original, live = _refresh()
    assert (2, 2) in original.cell_path
    revised = _decide(original, live)
    assert revised.status == "SELECTED"
    assert revised.plan.revision == 2
    assert revised.plan.source_s16_seq == 55
    assert revised.plan.source_voxel_seq == 60
    assert revised.plan.source_action_id == "stage-zero-outcome"
    assert revised.plan.parent == original.parent
    assert revised.plan.cell_path[0] == (2, 1)
    assert revised.plan.cell_path[-1] == (0, 4)
    assert (2, 2) not in revised.plan.cell_path
    assert (3, 2) in revised.plan.cell_path
    assert revised.plan.subgoal(0).goal_id != original.subgoal(0).goal_id
    assert revised.plan.stages[-1].target_z == original.parent.target_z


def test_unchanged_map_still_uses_fresh_pose_not_stale_full_route():
    original, live = _refresh(block_middle=False)
    revised = _decide(original, live)
    assert revised.status == "SELECTED"
    assert revised.plan.cell_path[0] == (2, 1)
    assert len(revised.plan.cell_path) < len(original.cell_path)


def test_no_path_after_observed_dynamic_closure_defers_without_plan():
    original, live = _refresh()
    cells = tuple(
        replace(c, feet="BLOCKED") if c.dz == 2 and c.dx >= 2 else c
        for c in live.cells
    )
    choice = _decide(original, replace(live, cells=cells))
    assert choice.status == "DEFER"
    assert choice.plan is None


@pytest.mark.parametrize("updates,options", [
    ({"native_seq": 54, "provenance": Provenance("mineflayer", "real-new-world:54")}, {}),
    ({}, {"last_s16_after_seq": 33}),
    ({"player_x": 8.0}, {}),
    ({"session_id": "other"}, {}),
    ({"origin_z": 11.5}, {}),
    ({}, {"last_closed_action_id": "original-unknown"}),
])
def test_stale_foreign_unchanged_closed_id_or_outside_are_rejected(updates, options):
    original, live = _refresh()
    if "session_id" in updates:
        updates["provenance"] = Provenance("mineflayer", "other:60")
    with pytest.raises(GoalControlRejected):
        _decide(original, replace(live, **updates), **options)


def test_exhausted_revision_budget_is_not_silently_reused():
    original, live = _refresh()
    with pytest.raises(GoalControlRejected):
        _decide(replace(original, revision=12), live)
