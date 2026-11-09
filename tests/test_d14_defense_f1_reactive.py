"""D14 Defense-F1: source-backed reactive attack admission, OFFLINE only."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from adapters.mineflayer.normal_action import NormalActionRejected
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerPosition,
)
from adapters.mineflayer.s49_reactive_defense import (
    MAX_DAMAGE_WITNESS_SEQ_LAG,
    evaluate_native_damage_defense,
    require_native_damage_defense,
)
from relay_self.action import ActionState
from test_d14_local_oneworld import _fixture_paths, _validate
from test_d14_natural_motion_r6 import controller, observation
from test_d14_r9_combat_first import _decision
from tools import bug0_d14_local_oneworld as local
from tools.bug0_d14_natural_life import (
    F1_DEFENSE_GRANT,
    NaturalLifeRejected,
    admissible_natural_attack,
)


def native(
    seq, *, health=20, distance=1.5, oxygen=20,
    body_x=0.0, entity_id=7, session_id="native-session",
):
    base = observation(seq, distance=distance, entity_id=entity_id,
                       session_id=session_id)
    return replace(base, snapshot=replace(
        base.snapshot, health=health, oxygen_level=oxygen,
        position=MineflayerPosition(body_x, 64.0, 0.0),
        nearby_entities=(
            MineflayerEntityFact(
                entity_id=entity_id, name="zombie", entity_type="mob",
                distance=distance,
                position=MineflayerPosition(distance + body_x, 64.0, 0.0),
            ),
        ),
    ))


def test_f1_native_health_loss_admits_mobile_target_not_r9_stationary_pair():
    prior = native(3, health=20, distance=3.9)
    before = native(5, health=18, distance=3.5)
    current = native(6, health=17, distance=2.3)
    assert admissible_natural_attack(before, current) is None
    candidate, reason = evaluate_native_damage_defense(
        before, current, prior,
    )
    assert reason == "REACTIVE_NATIVE_HEALTH_LOSS_CANDIDATE"
    assert candidate.target_entity_id == 7
    assert candidate.health_loss == 3
    assert candidate.witness is prior
    assert candidate.source.endswith("CAUSE_UNATTESTED")
    require_native_damage_defense(before, current, 7, candidate)
    with pytest.raises(NormalActionRejected):
        require_native_damage_defense(before, current, 8, candidate)


@pytest.mark.parametrize("change", [
    "no_damage", "oxygen_unknown", "oxygen_zero", "dead", "wrong_target",
    "foreign", "stale", "out_of_reach", "teleported_zombie",
    "teleported_self", "truncated", "other_entity",
])
def test_f1_refuses_unsafe_or_unbound_native_source(change):
    prior = native(3, health=20)
    before = native(5, health=18, distance=2.4)
    current = native(6, health=17, distance=1.5)
    if change == "no_damage":
        prior = native(3, health=17)
        before = native(5, health=17)
    if change == "oxygen_unknown":
        current = native(6, health=17, oxygen=None)
    if change == "oxygen_zero":
        current = native(6, health=17, oxygen=0)
    if change == "dead":
        current = native(6, health=0)
    if change == "wrong_target":
        current = native(6, health=17, entity_id=8)
    if change == "foreign":
        prior = native(3, health=20, session_id="foreign")
    if change == "stale":
        prior = native(1, health=20)
        before = native(
            MAX_DAMAGE_WITNESS_SEQ_LAG + 3, health=18, distance=2.4,
        )
        current = native(
            MAX_DAMAGE_WITNESS_SEQ_LAG + 4, health=17, distance=1.5,
        )
    if change == "out_of_reach":
        current = native(6, health=17, distance=3.0)
    if change == "teleported_zombie":
        before = native(5, health=18, distance=3.9)
        current = native(6, health=17, distance=1.5)
    if change == "teleported_self":
        current = native(6, health=17, distance=1.5, body_x=1.5)
    if change == "truncated":
        extras = tuple(
            MineflayerEntityFact(
                entity_id=40 + i, name="zombie", entity_type="mob",
                distance=2, position=MineflayerPosition(2, 64, 0),
            ) for i in range(15)
        )
        before = replace(before, snapshot=replace(
            before.snapshot,
            nearby_entities=before.snapshot.nearby_entities + extras,
            nearby_entities_coverage=replace(
                before.snapshot.nearby_entities_coverage,
                candidate_count=17, truncated=True,
            ),
        ))
    if change == "other_entity":
        other = MineflayerEntityFact(
            entity_id=8, name="cow", entity_type="mob", distance=1,
            position=MineflayerPosition(1, 64, 0),
        )
        before = replace(before, snapshot=replace(
            before.snapshot, nearby_entities=before.snapshot.nearby_entities+(other,),
            nearby_entities_coverage=replace(
                before.snapshot.nearby_entities_coverage, candidate_count=2,
            ),
        ))
    candidate, _ = evaluate_native_damage_defense(before, current, prior)
    assert candidate is None


def test_f1_source_is_revalidated_by_original_s49_not_only_l0(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, _ = controller(tmp_path, monkeypatch)
    before = native(5, health=18, distance=3.3)
    current = native(6, health=17, distance=2.3)
    witness = native(3, health=20, distance=3.8)
    candidate, _ = evaluate_native_damage_defense(before, current, witness)
    assert candidate is not None
    grants = loop._grant("ATTACK", current, "f1-original-s49-one", target=7)
    with pytest.raises(NormalActionRejected):
        loop.owner.require_attack_authorizations(
            before, current, 7, *grants,
        )
    loop.owner.require_attack_authorizations(
        before, current, 7, *grants, reactive_damage_source=candidate,
    )
    # Reusing the same candidate on a different current seq is not allowed.
    future = native(7, health=16, distance=2.1)
    with pytest.raises(NormalActionRejected):
        loop.owner.require_attack_authorizations(
            before, future, 7, *grants, reactive_damage_source=candidate,
        )
    loop.owner._post_move_settling_unqualified = True
    with pytest.raises(NormalActionRejected, match="source/owner"):
        loop.owner.require_attack_authorizations(
            before, current, 7, *grants, reactive_damage_source=candidate,
        )


def test_f1_source_cannot_bypass_default_original_s49_owner(tmp_path, monkeypatch):
    monkeypatch.setenv("D14_R4_NATURAL_S49_ONEWORLD_ONLY", "1")
    loop, _ = controller(tmp_path, monkeypatch)
    previous = native(5, health=18, distance=3.3)
    current = native(6, health=17, distance=2.3)
    source, _ = evaluate_native_damage_defense(
        previous, current, native(3, health=20, distance=3.8),
    )
    assert source is not None
    grants = loop._grant("ATTACK", current, "default-owner", target=7)
    with pytest.raises(NormalActionRejected, match="requires original S49 DEV grant"):
        loop.owner.require_attack_authorizations(
            previous, current, 7, *grants, reactive_damage_source=source,
        )
    assert loop.nonmotion.actions == ()
    assert loop.owner._count == 0


def _grants(monkeypatch):
    for key in (
        "D14_R4_NATURAL_S49_ONEWORLD_ONLY",
        "D14_R5_LOCAL_ONEWORLD_ONLY",
        "D14_R6_NATURAL_MOTION_ONEWORLD_ONLY",
        "D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY",
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
        "D14_R9_COMBAT_FIRST_ONEWORLD_ONLY",
        "D14_R10_INITIAL_STONE_SWORD_ONEWORLD_ONLY",
        "D14_R11_NATURAL_DAY_ONEWORLD_ONLY",
        F1_DEFENSE_GRANT,
    ):
        monkeypatch.setenv(key, "1")


def test_f1_requires_separate_explicit_grant_before_s49_fence(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("D14_R4_NATURAL_S49_ONEWORLD_ONLY", "1")
    monkeypatch.setenv(F1_DEFENSE_GRANT, "1")
    session = SimpleNamespace(
        started=SimpleNamespace(session_id="native-session"),
    )
    from tools.bug0_d14_natural_life import NaturalLifeLoop
    with pytest.raises(NaturalLifeRejected, match="F1_DEFENSE_REQUIRES"):
        NaturalLifeLoop(session, tmp_path, {})
    assert list(tmp_path.iterdir()) == []


def test_f1_reactive_decision_and_original_issuer_without_new_move(
    tmp_path, monkeypatch,
):
    _grants(monkeypatch)
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.defense_f1
    loop.policy = SimpleNamespace(decide=lambda *_a, **_kw: _decision())
    loop.motion.issue_original_move = AsyncMock(
        side_effect=AssertionError("reactive defense must not fake MOVE"),
    )
    loop.owner.execute_attack = AsyncMock(return_value=SimpleNamespace(
        terminal=SimpleNamespace(state=ActionState.OUTCOME),
    ))
    loop._read = AsyncMock(side_effect=[
        native(5, health=20, distance=3.7),
        native(6, health=20, distance=3.5),
        native(7, health=17, distance=2.5),
        native(8, health=17, distance=1.8),
    ])
    asyncio.run(loop.step(lambda *_a, **_k: None))
    assert loop.owner.execute_attack.await_count == 0
    asyncio.run(loop.step(lambda *_a, **_k: None))
    assert loop.owner.execute_attack.await_count == 1
    assert loop.owner.execute_attack.await_args.kwargs[
        "reactive_damage_source"
    ].witness.seq == 6
    assert report["life_decisions"][1]["f1_admission"] == (
        "REACTIVE_HEALTH_LOSS_NATIVE_PAIR_ORIGINAL_S49"
    )
    assert report["f1_reactive_defense_actions"] == 1
    assert report["life_action_outcomes"][0]["f1_native_health_loss"] == 3
    assert report["life_action_outcomes"][0]["f1_reactive_damage_source"] == (
        "NATIVE_HEALTH_DROP_NEAR_ZOMBIE_NOT_CAUSAL_PROOF"
    )
    assert loop.motion.fence.actions == ()


def test_f1_local_oneworld_preflight_requires_full_prior_grants(
    tmp_path, monkeypatch,
):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4][F1_DEFENSE_GRANT] = "1"
    with pytest.raises(local.D14LocalRejected, match="F1_DEFENSE_REQUIRES"):
        _validate(paths)
    assert not paths[1].exists()
    for key in (
        local.R11_DAY_GRANT, local.R10_SWORD_GRANT,
        local.R9_COMBAT_GRANT, local.R7_EVIDENCE_GRANT, local.R6_GRANT,
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        paths[4][key] = "1"
    accepted = _validate(paths)
    assert accepted["f1_reactive_defense_opt_in"] is True
    assert accepted["requested_paper_horizon_ticks"] == 24000
