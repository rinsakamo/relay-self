"""D6-D offline original natural death → item-oriented S49 source negatives.

No World creation, physical Action, EAT, mutation of real Paper physics, or
replayed previous Action. Exact original runner remains the sole issuer.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.d6_loot_approach import (
    D6LootApproachRejected,
    source_qualified_loot_approach,
)
from adapters.mineflayer.normal_action import (
    NormalActionStage,
    NormalLootMoveAuthorization,
    NormalSessionActionExecutor,
)
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_d6_loot_approach import pair
from tools.bug0_d6_natural_move_post import D6DNaturalAuditRejected, audit
from tools.bug0_d6_natural_move_world import source_qualified_natural_move


def natural_with_orb():
    previous, current = pair()
    item = current.snapshot.nearby_entities[0]
    xp = replace(item, entity_id=60, name="experience_orb",
                 entity_type="other", distance=1.8)
    def new_snapshot(snap):
        return replace(
            snap,
            nearby_entities=(item, xp),
            nearby_entities_coverage=replace(
                snap.nearby_entities_coverage, candidate_count=2,
            ),
        )
    return (
        replace(previous, snapshot=new_snapshot(previous.snapshot)),
        replace(current, snapshot=new_snapshot(current.snapshot)),
    )


def test_natural_item_one_real_xp_orb_is_explicitly_source_admitted():
    previous, current = natural_with_orb()
    with pytest.raises(D6LootApproachRejected):
        source_qualified_loot_approach(
            previous, current, item_entity_id=42,
        )
    choice = source_qualified_loot_approach(
        previous, current, item_entity_id=42,
        allow_experience_orbs=True,
    )
    assert choice.item_entity_id == 42
    assert not choice.action_issued
    assert not choice.authority_granted
    assert not choice.pickup_verified
    assert not choice.item_identity_verified_as_rotten_flesh


@pytest.mark.parametrize("name", ["zombie", "creeper", "skeleton", "unknown", "item"])
def test_natural_item_does_not_ignore_any_other_unsafe_or_second_item(name):
    previous, current = natural_with_orb()
    def change(plain):
        a, b = plain.snapshot.nearby_entities
        new_entities = (a, replace(b, name=name))
        return replace(
            plain, snapshot=replace(plain.snapshot, nearby_entities=new_entities),
        )
    with pytest.raises(D6LootApproachRejected):
        source_qualified_loot_approach(
            change(previous), change(current),
            item_entity_id=42, allow_experience_orbs=True,
        )


def test_natural_item_refuses_more_than_two_xp_orbs():
    previous, current = natural_with_orb()
    def add(read):
        entities = read.snapshot.nearby_entities
        return replace(read, snapshot=replace(
            read.snapshot,
            nearby_entities=(*entities, replace(entities[1], entity_id=61),
                             replace(entities[1], entity_id=62)),
            nearby_entities_coverage=replace(
                read.snapshot.nearby_entities_coverage, candidate_count=4,
            ),
        ))
    with pytest.raises(D6LootApproachRejected):
        source_qualified_loot_approach(
            add(previous), add(current), item_entity_id=42,
            allow_experience_orbs=True,
        )


def test_natural_xp_allowance_refuses_nonboolean_flag():
    a, b = natural_with_orb()
    with pytest.raises(D6LootApproachRejected):
        source_qualified_loot_approach(
            a, b, item_entity_id=42, allow_experience_orbs="yes",
        )


def test_original_s49_new_scoped_authorizations_recompute_natural_source():
    a, b = natural_with_orb()
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="one original ATTACK then native loot MOVE",
        at_ns=1, provenance=Provenance("offline-d6", "intent"),
    )
    owner = NormalSessionActionExecutor(b.session_id, intent)
    choice = source_qualified_loot_approach(
        a, b, item_entity_id=42, allow_experience_orbs=True,
    )
    fields = dict(
        intent_id="escape-threat", session_id=b.session_id,
        action_id="d6-natural-move-1", probe_seq=b.seq,
        probe_request_id=b.request_id, item_entity_id=42,
        granted=True,
    )
    grant_a = NormalLootMoveAuthorization(
        stage=NormalActionStage.PROPOSE, authority_id="independent-propose",
        provenance=Provenance("offline-d6", "propose"), **fields,
    )
    grant_b = NormalLootMoveAuthorization(
        stage=NormalActionStage.ISSUE, authority_id="independent-issue",
        provenance=Provenance("offline-d6", "issue"), **fields,
    )
    owner.require_d6_loot_move_authorizations(
        a, b, choice, grant_a, grant_b, allow_experience_orbs=True,
    )
    with pytest.raises(D6LootApproachRejected):
        owner.require_d6_loot_move_authorizations(
            a, b, choice, grant_a, grant_b,
        )
    assert owner._count == 0
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()


def test_natural_real_world_scoped_entry_denies_without_grants(monkeypatch, tmp_path):
    from tools.bug0_d4_oneworld import run
    for key in ("S49_REAL_SERVER_CI", "BUG0_S49_D4_ONE_WORLD_ONLY",
                "D6_NATURAL_DROP_MOVE_WORLD_ONLY", "S49_D5_NONMOTION_FENCE_DEV_ONLY"):
        monkeypatch.delenv(key, raising=False)
    report = tmp_path / "report.json"
    result = asyncio.run(run(
        report, tmp_path / "paper.log",
        post_death_loot_move_dev=source_qualified_natural_move,
        nonmotion_fence_path=tmp_path / "nonmotion.json",
        motion_fence_path=tmp_path / "motion.json",
    ))
    assert result != 0
    assert not (tmp_path / "nonmotion.json").exists()
    assert not (tmp_path / "motion.json").exists()


def test_dual_fence_no_previous_world_reseed(tmp_path):
    from tools.bug0_d4_oneworld import preflight_original_nonmotion_fence
    from tools.bug0_d6_staged_move_world import preflight_move_fence
    non, restored = preflight_original_nonmotion_fence(tmp_path / "nonmotion.json")
    move = preflight_move_fence(tmp_path / "motion.json")
    assert not restored and non.actions == () and move.actions == ()
    assert OriginalS49PhysicalFence.restore(
        tmp_path / "motion.json", self_id="s49-original-self",
    ).actions == ()


def test_independent_natural_audit_never_accepts_empty_or_forged_evidence(tmp_path):
    with pytest.raises(D6DNaturalAuditRejected):
        audit("", {"status":"PASS_DEV"}, tmp_path / "n.json", tmp_path / "m.json")
    fake_log = "\n".join([
        "RSELF_RESPAWN_INITIAL world=00000000-0000-0000-0000-000000000001 entity=00000000-0000-0000-0000-000000000002 generation=1 tick=10",
        "RSELF_NATURAL_DROP_DEATH world=00000000-0000-0000-0000-000000000001 zombie=00000000-0000-0000-0000-000000000002 tick=12 rotten_count=1 killer=00000000-0000-0000-0000-000000000003 source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true",
    ])
    with pytest.raises(D6DNaturalAuditRejected):
        audit(fake_log, {"status":"PASS_DEV"}, tmp_path / "n.json", tmp_path / "m.json")
