"""Scripted DEV ATTACK issuer regressions; not actual damage or Paper evidence."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerEntityHurt,
)
from experiments.cognitive_physical_attack_issue_dev import (
    PhysicalAttackRefusal,
    issue_selected_attack_dev,
)
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalGrantStage,
)
from relay_self.action import ActionState
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
    PhysicalJournalReplay,
    PhysicalJournalUnresolved,
)
from relay_self.physical_action_port import propose_bound_physical_action
from relay_self.provenance import Provenance
from test_cognitive_minimal_minecraft_dev import observation, zombie
from test_cognitive_physical_eat_issue_dev import OwnedFakeNative
from test_initial_skill_ir_v0 import fixture as initial_fixture


class AttackNative(OwnedFakeNative):
    async def send_attack_entity(self, action_id, *, entity_id):
        if self.journal is not None:
            import json

            self.wal_at_first_native_send = json.loads(
                self.journal.path.read_text()
            )["body"]["actions"][-1]["status"]
        self.sent.append(("attack_entity", action_id, entity_id))


def setup(tmp_path, *, event_kind="good"):
    selection, ir, owner, skill, binding, cap, readback, source = initial_fixture(
        "ATTACK"
    )
    prior = observation(
        11, session_id="world-A", request_id="probe-prev", food=20,
        entities=(zombie(entity_id=31),),
    )
    now = observation(
        12, session_id="world-A", request_id="probe-A", food=20,
        entities=(zombie(entity_id=31),),
    )
    proposal = propose_bound_physical_action(
        binding, capability=cap, readback=readback,
        intent_owner=owner, skill_execution=skill, supervisor=__import__(
            "relay_self.action_supervision", fromlist=["ActionSupervisor"]
        ).ActionSupervisor(),
        at_ns=4, provenance=source,
    )
    # Use the same original supervisor that received the proposal.
    supervisor = __import__(
        "relay_self.action_supervision", fromlist=["ActionSupervisor"]
    ).ActionSupervisor()
    # PROPOSED is not recorded; a fresh supervisor can legitimately admit it.
    journal = PhysicalActionJournal.create(
        tmp_path / "physical-shared.json", self_id="self-A",
    )
    ack = MineflayerEffectResult(
        "world-A", 13, "action-A-attack", "attack_entity", "applied", None,
    )
    hurt = MineflayerEntityHurt("world-A", 14, 31, 5, 5)
    after = observation(
        15, session_id="world-A", request_id="action-A-after-attack-00",
        food=20, entities=(zombie(entity_id=31),),
    )
    if event_kind == "missing_hurt":
        events = [ack]
    elif event_kind == "unknown_source":
        events = [ack, replace(hurt, source_entity_id=None), after]
    elif event_kind == "other_source":
        events = [ack, replace(hurt, source_entity_id=9), after]
    elif event_kind == "wrong_target":
        events = [ack, replace(hurt, entity_id=99), after]
    elif event_kind == "rejected_ack":
        events = [replace(ack, result="rejected", error="no_entity"), hurt, after]
    elif event_kind == "bad_after":
        events = [ack, hurt, replace(after, request_id="foreign")]
    elif event_kind == "hurt_first":
        events = [hurt, ack, after]
    else:
        events = [ack, hurt, after]
    session = AttackNative(events)
    session.journal = journal
    grants = (
        PhysicalEatGrant(
            PhysicalGrantStage.PROPOSE, "operator-propose",
            Provenance("test-propose", "1"), binding.intent_id, binding.action_id,
            "world-A", 12, "probe-A", "entity:31", True,
        ),
        PhysicalEatGrant(
            PhysicalGrantStage.ISSUE, "operator-issue",
            Provenance("test-issue", "1"), binding.intent_id, binding.action_id,
            "world-A", 12, "probe-A", "entity:31", True,
        ),
    )
    kwargs = dict(
        proposal=proposal, previous_probe=prior, current_probe=now,
        propose_grant=grants[0], issue_grant=grants[1],
        intent_owner=owner, skill_execution=skill, supervisor=supervisor,
        journal=journal, at_ns=5, provenance=source,
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        evidence_timeout_s=.1,
    )
    return kwargs, session


def run(kwargs, session):
    return asyncio.run(issue_selected_attack_dev(session, **kwargs))


@pytest.mark.parametrize("kind", ["good", "hurt_first"])
def test_attack_one_parent_wal_reservation_precedes_native_attack(tmp_path, kind):
    kw, session = setup(tmp_path, event_kind=kind)
    effect = run(kw, session)
    assert session.sent == [
        ("attack_entity", "action-A-attack", 31),
        ("observe", "action-A-after-attack-00"),
    ]
    assert session.wal_at_first_native_send == "PREPARED_UNRESOLVED"
    assert effect.status == "NATIVE_ATTACK_HURT_CORRELATED_DEV_ONLY"
    assert effect.damage_attested is False
    assert effect.terminal.state is ActionState.OUTCOME
    assert kw["supervisor"].get("action-A") is effect.terminal
    assert kw["skill_execution"].state.value == "started"
    reopened = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert not reopened.unresolved
    row = reopened.records[-1]
    assert row["status"] == "NATIVE_ATTACK_HURT_CORRELATED"
    assert row["capability"] == "attack_entity"
    assert row["effect_seqs"] == [13, 14]
    assert row["after_seq"] == 15
    assert row["food_before"] is None
    with pytest.raises((PhysicalAttackRefusal, PhysicalJournalReplay)):
        run(kw, session)
    assert len([x for x in session.sent if x[0] == "attack_entity"]) == 1


@pytest.mark.parametrize("kind", [
    "missing_hurt", "unknown_source", "other_source",
    "wrong_target", "rejected_ack", "bad_after",
])
def test_unattributed_hurt_and_missing_ack_are_unknown_not_success(tmp_path, kind):
    kw, session = setup(tmp_path, event_kind=kind)
    with pytest.raises((PhysicalAttackRefusal, RuntimeError)):
        run(kw, session)
    assert kw["supervisor"].get("action-A").state is ActionState.UNKNOWN
    restored = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert restored.unresolved
    assert restored.records[0]["status"] == "PREPARED_UNRESOLVED"
    with pytest.raises(PhysicalJournalUnresolved):
        run(kw, session)
    assert len([x for x in session.sent if x[0] == "attack_entity"]) == 1


@pytest.mark.parametrize("change", [
    "no_grant", "unauth_ack", "grant_target", "foreign_world", "other_target",
    "missing_zombie", "busy_owner", "future_source",
])
def test_reject_before_journal_and_native_send(tmp_path, change):
    kw, session = setup(tmp_path)
    if change == "no_grant":
        kw["grant_real_world"] = False
    elif change == "unauth_ack":
        kw["acknowledge_dev_unverified_principal"] = False
    elif change == "grant_target":
        kw["issue_grant"] = replace(
            kw["issue_grant"], selected_target_ref="entity:7",
        )
    elif change == "foreign_world":
        kw["current_probe"] = replace(kw["current_probe"], session_id="other")
    elif change == "other_target":
        kw["previous_probe"] = replace(
            kw["previous_probe"],
            snapshot=replace(
                kw["previous_probe"].snapshot,
                nearby_entities=(zombie(entity_id=8),),
            ),
        )
    elif change == "missing_zombie":
        kw["current_probe"] = replace(
            kw["current_probe"],
            snapshot=replace(
                kw["current_probe"].snapshot,
                nearby_entities=(),
                nearby_entities_coverage=replace(
                    kw["current_probe"].snapshot.nearby_entities_coverage,
                    candidate_count=0,
                ),
            ),
        )
    elif change == "busy_owner":
        kw["intent_owner"].invalidate(
            "intent-A", reason="withdrawn", at_ns=5,
            provenance=Provenance("test", "withdrawal"),
        )
    elif change == "future_source":
        kw["current_probe"] = replace(
            kw["current_probe"], seq=15,
        )
    with pytest.raises((PhysicalAttackRefusal, ValueError)):
        run(kw, session)
    assert session.sent == []
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()


def test_same_self_eat_history_and_attack_share_wal_and_restart_ledger(tmp_path):
    kw, session = setup(tmp_path)
    receipt = run(kw, session)
    restored = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert len(restored.records) == 1
    assert restored.records[0]["capability"] == "attack_entity"
    assert restored.digest == kw["journal"].digest
    with pytest.raises(PhysicalJournalError):
        PhysicalActionJournal.restore(kw["journal"].path, self_id="other")
