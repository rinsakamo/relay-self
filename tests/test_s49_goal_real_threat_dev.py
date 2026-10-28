"""L0 threat preemption and original S49 real World source refusal."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition
from adapters.mineflayer.s49_goal_real_threat_review_dev import (
    GoalThreatReviewRejected,
    review_world_reports,
)
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalDecisionKind,
    GoalPurpose,
    L2GoalProposal,
    ObservedGoalL0,
    compile_l1_goal_dev,
)
from relay_self.provenance import Provenance


def l0():
    proposal=L2GoalProposal(
        goal_id="hazard-goal",intent_id="goal-navigate",session_id="native-session",
        target_x=0.0,target_z=2.6,purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.3,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,provenance=Provenance("dev-l2","original-goal"),
    )
    directive=compile_l1_goal_dev(
        proposal,current_x=0.0,current_z=0.0,
        provenance=Provenance("dev-l1","purpose-and-distance"),
    )
    return ObservedGoalL0(directive,start_x=0.0,start_z=0.0)


def probe(seq, *,z=0.0, distance=None, session="native-session"):
    p=Mock(spec=MineflayerObservation)
    p.kind="probe"
    p.request_id=f"real-probe-{seq}"
    p.seq=seq
    p.session_id=session
    p.provenance=Provenance("mineflayer",f"real-{seq}")
    p.snapshot=SimpleNamespace(
        position=MineflayerPosition(x=0.0,y=-60.0,z=z),
        nearby_entities=(
            () if distance is None
            else (SimpleNamespace(name="zombie",entity_id=42,distance=distance),)
        ),
        nearby_entities_coverage=SimpleNamespace(truncated=False),
    )
    return p


def test_threat_interruption_after_a_real_previous_action_decision():
    controller=l0()
    before=controller.decide(probe(2))
    assert before.kind is GoalDecisionKind.MOVE
    controller.admitted(before)
    interrupted=controller.decide(probe(19,z=0.94,distance=0.75))
    assert interrupted.kind is GoalDecisionKind.INTERRUPT
    assert interrupted.reason=="OBSERVED_NEAR_THREAT"
    assert controller.actions==1
    assert controller.closed is True
    assert controller.directive.proposal.goal_id=="hazard-goal"
    with pytest.raises(GoalControlRejected):
        controller.decide(probe(20,z=0.96))


def test_threat_preempts_arrival_even_in_deadband():
    controller=l0()
    interrupted=controller.decide(probe(11,z=2.55,distance=0.85))
    assert interrupted.kind is GoalDecisionKind.INTERRUPT
    assert controller.actions==0


def test_distant_real_entity_does_not_trigger_interrupt():
    controller=l0()
    first=controller.decide(probe(2,distance=3.0))
    assert first.kind is GoalDecisionKind.MOVE
    assert controller.closed is False


@pytest.mark.parametrize("distance", [0.2,0.75,1.49])
def test_bounded_genuine_zombie_proximity(distance):
    controller=l0()
    assert controller.decide(probe(2,distance=distance)).kind is GoalDecisionKind.INTERRUPT


def test_threat_handoff_not_accepted_without_two_world_source(tmp_path):
    with pytest.raises(GoalThreatReviewRejected):
        review_world_reports(tmp_path)


def test_world_change_uses_only_original_minecraft_command_not_forged_probe():
    runner=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    assert "summon minecraft:zombie" in runner
    assert "if inject_threat_after_first_dev and executor._count==1:" in runner
    assert "probe.snapshot.nearby_entities" in runner
    assert '"additional_action_issued_after_interrupt":False' in runner
    assert '"upper_layer_replan_executed":False' in runner
    assert "executor.supervisor.open_actions" in runner
