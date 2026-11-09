"""F2: one exact zombie among benign native bystanders; offline only."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from adapters.mineflayer.normal_action import NormalActionRejected
from adapters.mineflayer.python_protocol import MineflayerEntityFact, MineflayerPosition
from adapters.mineflayer.s49_reactive_defense import (
    F2_SOURCE,
    evaluate_native_damage_defense,
    require_native_damage_defense,
)
from relay_self.action import ActionState
from test_d14_defense_f1_reactive import _grants, native
from test_d14_local_oneworld import _fixture_paths, _validate
from test_d14_natural_motion_r6 import controller
from test_d14_r9_combat_first import _decision
from tools import bug0_d14_local_oneworld as local
from tools.bug0_d14_natural_life import F2_DEFENSE_GRANT


def with_bystander(probe, *, name="sheep", entity_type="mob", eid=19):
    sheep = MineflayerEntityFact(
        entity_id=eid, name=name, entity_type=entity_type,
        distance=2.0, position=MineflayerPosition(2.0, 64.0, 0.0),
    )
    original = probe.snapshot
    return replace(probe, snapshot=replace(
        original,
        nearby_entities=original.nearby_entities + (sheep,),
        nearby_entities_coverage=replace(
            original.nearby_entities_coverage, candidate_count=2,
        ),
    ))


def pair():
    witness = with_bystander(native(3, health=20, distance=3.8))
    before = with_bystander(native(5, health=18, distance=3.3))
    current = with_bystander(native(6, health=17, distance=2.2))
    return witness, before, current


def test_f2_one_zombie_and_sheep_admits_only_with_explicit_candidate_type():
    witness, before, current = pair()
    old, _ = evaluate_native_damage_defense(before, current, witness)
    assert old is None  # F1 strictly unchanged.
    candidate, reason = evaluate_native_damage_defense(
        before, current, witness, allow_known_bystanders=True,
    )
    assert reason == "F2_SINGLE_ZOMBIE_KNOWN_BYSTANDERS_REACTIVE_CANDIDATE"
    assert candidate is not None
    assert candidate.source == F2_SOURCE
    assert candidate.target_entity_id == 7
    assert candidate.health_loss == 3
    require_native_damage_defense(before, current, 7, candidate)


@pytest.mark.parametrize("name,entity_type", [
    ("skeleton", "mob"), ("zombie", "mob"), (None, "mob"),
    ("unknown", "mob"), ("sheep", "object"), ("creeper", "mob"),
])
def test_f2_never_ignores_unknown_hostile_or_second_zombie(name, entity_type):
    _, before, current = pair()
    wrong = with_bystander(
        native(5, health=18, distance=3.3),
        name=name, entity_type=entity_type,
    )
    candidate, reason = evaluate_native_damage_defense(
        wrong, current, native(3, health=20),
        allow_known_bystanders=True,
    )
    assert candidate is None
    assert reason in (
        "UNKNOWN_OR_HOSTILE_BYSTANDER_UNSAFE",
        "NOT_EXACTLY_ONE_VISIBLE_ZOMBIE",
    )


def test_f2_rejects_ambiguous_or_truncated_native_coverage():
    witness, before, current = pair()
    # An inconsistent "not truncated" snapshot is already rejected
    # by the common protocol; do not invent a frame the decoder can't emit.
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError

    with pytest.raises(MineflayerAdapterProtocolError):
        replace(current.snapshot, nearby_entities_coverage=replace(
            current.snapshot.nearby_entities_coverage,
            candidate_count=3,
        ))
    # A genuine truncated native frame contains max_entities entries
    # but reports more candidates than can be represented.
    more_sheep = tuple(
        MineflayerEntityFact(
            entity_id=20 + i, name="sheep", entity_type="mob",
            distance=2.0, position=MineflayerPosition(2.0, 64.0, 0.0),
        ) for i in range(14)
    )
    truncated = replace(current, snapshot=replace(
        current.snapshot,
        nearby_entities=current.snapshot.nearby_entities + more_sheep,
        nearby_entities_coverage=replace(
            current.snapshot.nearby_entities_coverage,
            candidate_count=17, truncated=True,
        ),
    ))
    assert evaluate_native_damage_defense(
        before, truncated, witness, allow_known_bystanders=True,
    )[0] is None


def test_f2_oxygen_unknown_and_loss_absent_are_not_bypassed():
    witness, before, current = pair()
    unknown = replace(current, snapshot=replace(
        current.snapshot, oxygen_level=None,
    ))
    assert evaluate_native_damage_defense(
        before, unknown, witness, allow_known_bystanders=True,
    )[0] is None
    no_loss = replace(witness, snapshot=replace(witness.snapshot, health=17))
    assert evaluate_native_damage_defense(
        before, current, no_loss, allow_known_bystanders=True,
    )[0] is None


def test_f2_only_explicit_original_s49_owner_accepts_scope(tmp_path, monkeypatch):
    _grants(monkeypatch)
    witness, before, current = pair()
    candidate, _ = evaluate_native_damage_defense(
        before, current, witness, allow_known_bystanders=True,
    )
    assert candidate is not None
    (tmp_path / "default").mkdir()
    (tmp_path / "allowed").mkdir()
    default, _ = controller(tmp_path / "default", monkeypatch)
    grants = default._grant("ATTACK", current, "f2-gate", target=7)
    with pytest.raises(NormalActionRejected, match="separate original S49 grant"):
        default.owner.require_attack_authorizations(
            before, current, 7, *grants, reactive_damage_source=candidate,
        )
    assert default.owner._count == 0
    assert default.nonmotion.actions == ()
    monkeypatch.setenv(F2_DEFENSE_GRANT, "1")
    allowed, _ = controller(tmp_path / "allowed", monkeypatch)
    assert allowed.defense_f2
    grants = allowed._grant("ATTACK", current, "f2-admit", target=7)
    allowed.owner.require_attack_authorizations(
        before, current, 7, *grants, reactive_damage_source=candidate,
    )
    allowed.owner._post_move_settling_unqualified = True
    with pytest.raises(NormalActionRejected):
        allowed.owner.require_attack_authorizations(
            before, current, 7, *grants, reactive_damage_source=candidate,
        )


def test_f2_l0_candidate_then_original_s49_without_forged_move(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    monkeypatch.setenv(F2_DEFENSE_GRANT, "1")
    loop, report = controller(tmp_path, monkeypatch)
    loop.policy = SimpleNamespace(decide=lambda *_a, **_kw: _decision())
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("F2 must not inject second MOVE issuer"),
    )
    loop.owner.execute_attack = AsyncMock(return_value=SimpleNamespace(
        terminal=SimpleNamespace(state=ActionState.OUTCOME),
    ))
    loop._read = AsyncMock(side_effect=[
        with_bystander(native(5, health=20, distance=3.7)),
        with_bystander(native(6, health=20, distance=3.5)),
        with_bystander(native(7, health=17, distance=2.5)),
        with_bystander(native(8, health=17, distance=1.8)),
    ])
    asyncio.run(loop.step(lambda *_a, **_k: None))
    asyncio.run(loop.step(lambda *_a, **_k: None))
    assert loop.owner.execute_attack.await_count == 1
    assert loop.owner.execute_attack.await_args.kwargs[
        "reactive_damage_source"
    ].source == F2_SOURCE
    assert report["f2_reactive_defense_actions"] == 1
    assert report["life_action_outcomes"][0]["f2_reactive_damage_source"] == F2_SOURCE
    loop.motion.issue_original_move.assert_not_awaited()


def test_f2_preflight_requires_f1_and_all_prior_grants(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4][F2_DEFENSE_GRANT] = "1"
    with pytest.raises(local.D14LocalRejected, match="F2_DEFENSE_REQUIRES"):
        _validate(paths)
    _grants(monkeypatch)
    for key in (
        local.R6_GRANT, local.R7_EVIDENCE_GRANT,
        local.R9_COMBAT_GRANT, local.R10_SWORD_GRANT,
        local.R11_DAY_GRANT, local.F1_DEFENSE_GRANT,
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        paths[4][key] = "1"
    valid = _validate(paths)
    assert valid["f2_single_zombie_bystanders_opt_in"] is True
    assert valid["requested_paper_horizon_ticks"] == 24000
    assert not paths[1].exists()
