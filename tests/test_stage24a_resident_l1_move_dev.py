"""Stage24a CPU/L1 relative MOVE, offline only; no native motor/GPU/Paper."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine
from relay_self.resident_l1_move_options_dev import (
    MOVE_PULSE_SECONDS,
    ResidentL1MoveRefusal,
    build_resident_l1_move_turn,
    propose_resident_l1_move,
    resolve_resident_l1_move,
)
from relay_self.skill import SkillExecution

CAP = PhysicalCapability("MOVE", 1, "locomotion", "RELATIVE", True)


def probe(
    seq: int, *,
    native: str = "world-B",
    food: float = 20.0,
    health: float = 20.0,
    oxygen: float | None = 300.0,
    has_time: bool = True,
    entity: bool = False,
    truncated: bool = False,
    request_id: str | None = None,
) -> MineflayerObservation:
    entities = (
        (MineflayerEntityFact(4, "zombie", "mob", 2.0, MineflayerPosition(2, 64, 0)),)
        if entity else ()
    )
    if truncated:
        entities = tuple(
            MineflayerEntityFact(i, "unknown", "mob", 2, MineflayerPosition(2, 64, 0))
            for i in range(16)
        )
    count = 17 if truncated else len(entities)
    snapshot = MineflayerSnapshot(
        health=health,
        food=food,
        food_saturation=5.0,
        oxygen_level=oxygen,
        position=MineflayerPosition(0, 64, 0),
        time=MineflayerTime(6000, 0, True) if has_time else None,
        inventory=(),
        nearby_entities=entities,
        nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
            MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
            16.0, 16, count, truncated,
        ),
    )
    return MineflayerObservation(
        native, seq, "probe", snapshot, request_id or f"stage24-probe-{seq}",
    )


def choose(turn, *, choice_id: str):
    calls = []

    def provider(request, *, mode):
        assert mode is CognitionMode.BOUNDED
        assert request is turn.round.request
        calls.append(request)
        return ProviderDecision.resolved(choice_id)

    result = RelayEngine(provider)(turn.round.request)
    assert len(calls) == 1
    return result


def make_turn(owner=None):
    owner = owner or IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10), self_id="B", intent_owner=owner, capability=CAP, epoch=1,
    )
    return turn, owner


def test_cpu_schema_exploration_emits_four_complete_options_without_operator_choice():
    turn, _ = make_turn()
    assert turn.exploration_need_active
    assert len(turn.prebound_moves) == 4
    assert {c.option.target_ref for c in turn.prebound_moves} == {
        "relative:forward", "relative:back",
        "relative:left", "relative:right",
    }
    assert {c.option.goal_id for c in turn.prebound_moves} == {"EXPLORE_WORLD"}
    assert all(c.pulse_seconds == MOVE_PULSE_SECONDS for c in turn.prebound_moves)
    assert all("pulse=0.35s" in c.description
               for c in turn.round.request.choices[:4])
    assert [c.description for c in turn.round.request.choices[-2:]] == [
        "ESCALATE_L2", "DEFER",
    ]
    assert not turn.round.request.think_allowed
    assert len(turn.candidate_set_sha256) == 64


def test_l1_number_selects_exact_right_preset_and_proposes_only():
    turn, owner = make_turn()
    right = next(c for c in turn.prebound_moves
                 if c.option.target_ref == "relative:right")
    decision = resolve_resident_l1_move(
        turn, choose(turn, choice_id=right.choice_id),
        current_probe=probe(11), intent_owner=owner, capability=CAP, epoch=2,
    )
    assert decision.status == "READY"
    assert decision.candidate == right
    assert owner.current_intent is None
    source = Provenance("stage24a-test", "model-selected-right")
    owner.commit("selected-i", objective=right.option.goal_id,
                 at_ns=10, provenance=source)
    skill = SkillExecution.start(
        "selected-run", skill_id="MOVE", intent_commitment=owner,
        at_ns=11, provenance=source,
    )
    proposal = propose_resident_l1_move(
        decision, intent_owner=owner, skill_execution=skill,
        supervisor=ActionSupervisor(), intent_id="selected-i",
        action_id="selected-action", at_ns=12, provenance=source,
    )
    assert proposal.binding.target_ref == "relative:right"
    assert proposal.binding.goal_id == "EXPLORE_WORLD"
    assert proposal.binding.native_seq == 11
    assert proposal.binding.native_request_id == "stage24-probe-11"
    assert proposal.state == "PROPOSED_NOT_AUTHORIZED"
    assert not proposal.physical_issued and not proposal.physical_authorized
    assert not proposal.preissue_persisted


@pytest.mark.parametrize(
    "changes",
    [
        {"food": 10.0},
        {"oxygen": None},
        {"oxygen": 0},
        {"health": 0},
        {"health": 5},
        {"has_time": False},
        {"entity": True},
        {"truncated": True},
    ],
)
def test_body_pressure_or_unknown_coverage_never_vetoes_selected_move(changes):
    turn, owner = make_turn()
    chosen = turn.prebound_moves[0].choice_id
    decision = resolve_resident_l1_move(
        turn, choose(turn, choice_id=chosen),
        current_probe=probe(11, **changes),
        intent_owner=owner, capability=CAP, epoch=2,
    )
    assert decision.status == "READY"
    assert decision.candidate.option.goal_id == "EXPLORE_WORLD"
    assert owner.events == ()


def test_native_session_change_refuses_no_retarget():
    turn, owner = make_turn()
    with pytest.raises(ResidentL1MoveRefusal, match="foreign"):
        resolve_resident_l1_move(
            turn, choose(turn, choice_id=turn.prebound_moves[0].choice_id),
            current_probe=probe(11, native="world-other"),
            intent_owner=owner, capability=CAP, epoch=2,
        )
    assert owner.events == ()


def test_irrelevant_new_epoch_keeps_selected_preset_when_body_valid():
    turn, owner = make_turn()
    decision = resolve_resident_l1_move(
        turn, choose(turn, choice_id=turn.prebound_moves[-1].choice_id),
        current_probe=probe(19), intent_owner=owner, capability=CAP, epoch=99,
    )
    assert decision.status == "READY"
    assert decision.candidate.option.target_ref == "relative:right"


def test_unknown_model_number_fails_without_issuing():
    turn, owner = make_turn()
    decision = resolve_resident_l1_move(
        turn, choose(turn, choice_id="999"),
        current_probe=probe(11), intent_owner=owner, capability=CAP, epoch=2,
    )
    # RelayEngine already rejects out-of-set provider numbers as unresolved.
    assert decision.status == "RECONSIDER"
    with pytest.raises(ResidentL1MoveRefusal, match="only current"):
        propose_resident_l1_move(
            decision, intent_owner=owner,
            skill_execution=None, supervisor=ActionSupervisor(),
            intent_id="i", action_id="a", at_ns=10,
            provenance=Provenance("test", "none"),
        )
    assert owner.events == ()


@pytest.mark.parametrize("special", ["DEFER", "ESCALATE_L2"])
def test_explicit_nonphysical_choice_preserved(special):
    turn, owner = make_turn()
    option_number = next(n for n, v in turn.round.numbered if v == special)
    decision = resolve_resident_l1_move(
        turn, choose(turn, choice_id=option_number),
        current_probe=probe(11), intent_owner=owner, capability=CAP, epoch=2,
    )
    assert decision.status == special
    assert decision.candidate is None
    assert owner.events == ()


def test_missing_capability_yields_unresolved_goal_not_fake_move():
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10), self_id="B", intent_owner=owner,
        capability=replace(CAP, available=False), epoch=1,
    )
    assert turn.exploration_need_active
    assert turn.round.frame.goals[-1].goal_id == "EXPLORE_WORLD"
    assert turn.round.frame.goals[-1].unresolved
    assert not turn.prebound_moves


def test_frozen_candidate_tamper_and_repeated_probe_fail_closed():
    turn, owner = make_turn()
    selected = choose(turn, choice_id=turn.prebound_moves[0].choice_id)
    with pytest.raises(ResidentL1MoveRefusal):
        replace(turn.prebound_moves[0], pulse_seconds=0.36)
    with pytest.raises(ResidentL1MoveRefusal, match="replayed"):
        resolve_resident_l1_move(
            turn, selected, current_probe=probe(10),
            intent_owner=owner, capability=CAP, epoch=2,
        )
    with pytest.raises(ResidentL1MoveRefusal, match="candidate set"):
        resolve_resident_l1_move(
            replace(turn, candidate_set_sha256="0" * 64), selected,
            current_probe=probe(11), intent_owner=owner,
            capability=CAP, epoch=2,
        )

@pytest.mark.parametrize(
    "changes",
    [
        {"food": 0.0, "oxygen": None, "has_time": False},
        {"food": 5.0, "oxygen": 0, "entity": True},
        {"health": 0, "oxygen": 0, "truncated": True},
    ],
)
def test_exploration_goal_exists_in_unfavorable_initial_body_states(changes):
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10, **changes), self_id="B", intent_owner=owner,
        capability=CAP, epoch=1,
    )
    assert turn.exploration_need_active  # Need active, never a motor admission gate
    assert len(turn.prebound_moves) == 4
    assert any(g.goal_id == "EXPLORE_WORLD" for g in turn.round.frame.goals)
    assert not owner.events
    assert all(v.option.skill_id == "MOVE" for v in turn.prebound_moves)


def test_low_oxygen_produces_independent_unresolved_goal_not_fake_move_skill():
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10, oxygen=0), self_id="B", intent_owner=owner,
        capability=CAP, epoch=1,
    )
    oxygen = next(g for g in turn.round.frame.goals
                  if g.goal_id == "RESTORE_OXYGEN")
    assert oxygen.schema_id == "homeostatic"
    assert oxygen.strength == "URGENT"
    assert oxygen.skill_id == ""
    assert oxygen.unresolved
    assert {c.option.goal_id for c in turn.prebound_moves} == {"EXPLORE_WORLD"}
    assert "OXYGEN_LOW" in turn.round.frame.fast_cues


def test_unknown_oxygen_is_not_low_oxygen_or_move_veto():
    owner = IntentCommitment()
    turn = build_resident_l1_move_turn(
        probe(10, oxygen=None), self_id="B", intent_owner=owner,
        capability=CAP, epoch=1,
    )
    assert not any(g.goal_id == "RESTORE_OXYGEN" for g in turn.round.frame.goals)
    assert len(turn.prebound_moves) == 4
