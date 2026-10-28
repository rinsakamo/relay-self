"""Different *real* route experience cannot be silently reduced to one guess."""
from __future__ import annotations

from pathlib import Path

import pytest

from relay_self.goal_detour_dev import explicit_l1_detour_dev
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.provenance import Provenance


def _goal():
    return L2GoalProposal(
        goal_id="approach-demo",intent_id="goal-navigate",
        session_id="fresh-session",target_x=0.5,target_z=14.5,
        purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.3,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,
        provenance=Provenance("dev-operator","fixed-goal"),
    )


def test_both_operator_routes_have_same_parent_but_different_stages():
    g=_goal()
    kwargs={
        "start_x":0.5,"start_z":10.5,
        "blocked_action_id":"original-step-2","blocked_s16_seq":31,
        "provenance":Provenance("dev-l1","explicit-route"),
    }
    right=explicit_l1_detour_dev(g,**kwargs,lateral_offset_dev=2.5)
    left=explicit_l1_detour_dev(g,**kwargs,lateral_offset_dev=-2.5)
    assert right.parent==left.parent
    assert right.stages[0].target_x==3.0
    assert left.stages[0].target_x==-2.0
    assert right.stages[1].target_x==3.0
    assert left.stages[1].target_x==-2.0
    assert right.subgoal(2).target_x==g.target_x
    assert left.subgoal(2).target_z==g.target_z


@pytest.mark.parametrize("side",[-3.0,0.0,2.4,3,2.5e300,float("nan")])
def test_unadmitted_lateral_geometry_denied(side):
    with pytest.raises(GoalControlRejected):
        explicit_l1_detour_dev(
            _goal(),start_x=0.5,start_z=10.5,
            blocked_action_id="source-action",blocked_s16_seq=31,
            provenance=Provenance("dev-l1","source"),
            lateral_offset_dev=side,
        )


def test_source_and_owner_handoff_is_explicit():
    runner=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    memory=Path("adapters/mineflayer/s49_l1_selfworld_memory_dev.py").read_text()
    controller=Path("src/relay_self/goal_memory_choice_dev.py").read_text()
    assert "detour_left_dev" in runner
    assert "lateral_offset_dev=-2.5 if detour_left_dev else 2.5" in runner
    assert "require_conflicting_success_dev" in memory
    assert "CONFLICTING_RECALLED_ROUTES" in controller
    assert '"stage"]="L1_MEMORY_DEFER"' in runner
    assert '"status"]="PASS"' in runner
    assert "self.supervisor.open_actions" in Path(
        "adapters/mineflayer/s49_goal_executor_dev.py"
    ).read_text()


def test_no_physical_evidence_cannot_pass_conflict_audit(tmp_path):
    from adapters.mineflayer.s49_l1_conflicting_routes_review_dev import (
        ConflictingRealRoutesRejected,
        audit_conflicting_real_routes_dev,
    )
    with pytest.raises((ConflictingRealRoutesRejected,FileNotFoundError)):
        audit_conflicting_real_routes_dev(tmp_path)
