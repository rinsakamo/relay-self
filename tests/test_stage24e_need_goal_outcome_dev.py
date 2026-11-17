"""Stage24e: Need/Goal always selectable; WorldBody outcomes remain authoritative."""
from __future__ import annotations

import json

import pytest

from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    WorldPercept,
    cpu_schema_epoch,
    initial_patterns_with_relative_move,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.resident_l1_move_options_dev import (
    build_resident_l1_move_turn,
    resolve_resident_l1_move,
)
from test_stage24a_resident_l1_move_dev import CAP, choose, probe


@pytest.mark.parametrize(
    ("oxygen", "strength"),
    [(0, "URGENT"), (3, "URGENT"), (4, "ACTIVE"), (10, "ACTIVE")],
)
def test_low_oxygen_emits_unresolved_homeostatic_goal_not_a_move_veto(
    oxygen, strength,
):
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(1, oxygen=oxygen, food=2, entity=True),
        self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    oxygen_goals = [g for g in turn.round.frame.goals
                    if g.goal_id == "RESTORE_OXYGEN"]
    assert len(oxygen_goals) == 1
    assert oxygen_goals[0].strength == strength
    assert oxygen_goals[0].skill_id == ""
    assert oxygen_goals[0].unresolved
    assert len(turn.prebound_moves) == 4
    assert all(c.option.goal_id == "EXPLORE_WORLD" for c in turn.prebound_moves)
    assert any(g.goal_id == "HUNGER_RELIEF" for g in turn.round.frame.goals)
    assert any(g.goal_id == "DEFEND_SELF" for g in turn.round.frame.goals)
    assert not owner.events
    context = json.loads(turn.round.request.context[0].value_json)
    oxygen_presented = next(g for g in context["goals"]
                            if g["id"] == "RESTORE_OXYGEN")
    assert oxygen_presented["skill"] is None
    assert oxygen_presented["unresolved"] is True


@pytest.mark.parametrize("oxygen", [None, 10.01, 20, 300])
def test_no_oxygen_restore_goal_above_need_threshold_or_unknown(oxygen):
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(1, oxygen=oxygen),
        self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    assert not any(g.goal_id == "RESTORE_OXYGEN" for g in turn.round.frame.goals)
    assert len(turn.prebound_moves) == 4


def test_selected_move_keeps_bound_skill_target_despite_new_oxygen_need():
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10, oxygen=None, food=20),
        self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    selected = choose(turn, choice_id="1")
    decision = resolve_resident_l1_move(
        turn, selected, current_probe=probe(11, oxygen=0, food=1, entity=True),
        intent_owner=owner, capability=CAP, epoch=2,
    )
    assert decision.status == "READY"
    assert decision.candidate.option.goal_id == "EXPLORE_WORLD"
    # Body/World actually moving, failing, or blocking is not claimed here.
    assert owner.current_intent is None


def test_oxygen_unknown_does_not_fabricate_need():
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(1, oxygen=None, food=20),
        self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    assert "OXYGEN_LOW" not in turn.round.frame.fast_cues
    assert all(g.goal_id != "RESTORE_OXYGEN" for g in turn.round.frame.goals)


@pytest.mark.parametrize("oxygen", [-1, float("nan"), float("inf")])
def test_oxygen_schema_input_refuses_invalid_body_measurement(oxygen):
    source = Provenance("fixture", "stage24e")
    with pytest.raises(MinimalCognitionError, match="invalid observed oxygen"):
        WorldPercept(
            scope=ScopeRef("B", "native-B"), source=source, sequence=1,
            hunger=20, fatigue_high=None, targets=(),
            exploration_need=True, oxygen_reserve=oxygen,
        )


def test_oxygen_pattern_does_not_install_unobserved_skill():
    patterns = initial_patterns_with_relative_move()
    oxygen = next(p for p in patterns.patterns if p.goal_id == "RESTORE_OXYGEN")
    assert oxygen.skill_id is None
    assert oxygen.target_kind is None
    assert oxygen.skill_version is None


def test_oxygen_thresholds_adjust_need_not_permission():
    owner = IntentCommitment()
    base = probe(1, oxygen=7)
    turn = build_resident_l1_move_turn(
        base, self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    assert any(g.goal_id == "RESTORE_OXYGEN" for g in turn.round.frame.goals)
    source = turn.round.frame.source
    percept = WorldPercept(
        scope=ScopeRef("B", base.session_id),
        source=source,
        sequence=base.seq,
        hunger=20, fatigue_high=None,
        targets=(), exploration_need=True, oxygen_reserve=7,
    )
    frame = cpu_schema_epoch(
        percept, initial_patterns_with_relative_move(),
        allowed_skills=frozenset({("MOVE", 1)}),
        epoch=1, oxygen_need_threshold=4,
    )
    assert not any(g.goal_id == "RESTORE_OXYGEN" for g in frame.goals)
    assert any(g.goal_id == "EXPLORE_WORLD" for g in frame.goals)


def test_head_medium_is_not_oxygen_need_input():
    from relay_self.head_breathing_context_dev import (
        HeadBreathingContext,
        HeadVolumeCell,
        assess_head_breathing_context,
    )

    air = HeadVolumeCell(True, "AIRLIKE", "NONE")
    head = HeadBreathingContext(
        session_id="synthetic", source_seq=1, source_request_id="q1",
        source=Provenance("fixture", "head"), measured_head_position=True,
        fresh=True, eye_cell=air, upper_head_cell=air,
    )
    assert assess_head_breathing_context(head).classification == "HEAD_AIRLIKE_OBSERVED"
    turn = build_resident_l1_move_turn(
        probe(1, oxygen=None), self_id="B",
        intent_owner=IntentCommitment(), capability=CAP, epoch=1,
    )
    assert all(g.goal_id != "RESTORE_OXYGEN" for g in turn.round.frame.goals)
    assert len(turn.prebound_moves) == 4
