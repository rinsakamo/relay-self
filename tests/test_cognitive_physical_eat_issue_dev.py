"""Offline physical EAT journal + single DEV issuer regressions.

Scripted Mineflayer bytes are not physical World evidence. No real
Minecraft, Gemma, physical grant principal or QUAL is claimed.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerInventoryItem,
    MineflayerLaunchConfig,
)
from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalEatRefusal,
    PhysicalGrantStage,
    issue_selected_eat_dev,
)
from relay_self.action import ActionState
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalError,
    PhysicalJournalReplay,
    PhysicalJournalUnresolved,
)
from relay_self.physical_action_port import (
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from test_cognitive_minimal_minecraft_dev import bread, observation, zombie
from test_physical_action_port import fixture


class OwnedFakeNative(MineflayerProcessSession):
    """Fake typed session, never starts a Node process or World."""

    def __init__(self, events):
        self._started = MineflayerAdapterStarted(
            "world-A", 0, "4.39.0", MineflayerLaunchConfig(),
        )
        self.events = list(events)
        self.sent = []
        self.failure = None

    @property
    def process_returncode(self):
        return None

    async def send_equip_item(self, action_id, *, item_name):
        self.sent.append(("equip_item", action_id, item_name))

    async def send_consume_held(self, action_id):
        self.sent.append(("consume_held", action_id))

    async def send_observe(self, request_id=None):
        self.sent.append(("observe", request_id))

    async def receive(self):
        if not self.events:
            raise RuntimeError("scripted native disconnect")
        return self.events.pop(0)


def setup(tmp_path):
    b, _, _, owner, skill, sup, prov = fixture()
    b = replace(b, capability_ref="EAT")
    cap = PhysicalCapability("EAT", 1, "hand", "FOOD", True)
    previous = observation(
        11, session_id="world-A", request_id="probe-prev",
        inventory=(bread(),),
    )
    current = observation(
        12, session_id="world-A", request_id="probe-A",
        inventory=(bread(),),
    )
    readback = PhysicalReadback(
        b.scope, current.provenance, 12, "probe-A", ("inventory:bread",), True,
    )
    proposal = propose_bound_physical_action(
        b, capability=cap, readback=readback, intent_owner=owner,
        skill_execution=skill, supervisor=sup, at_ns=4, provenance=prov,
    )
    journal = PhysicalActionJournal.create(
        tmp_path / "physical-eat.json", self_id="self-A",
    )
    grants = (
        PhysicalEatGrant(
            PhysicalGrantStage.PROPOSE, "external-proposer",
            Provenance("test-operator-propose", "1"), "intent-A",
            b.action_id, "world-A", 12, "probe-A", "inventory:bread", True,
        ),
        PhysicalEatGrant(
            PhysicalGrantStage.ISSUE, "external-issuer",
            Provenance("test-operator-issue", "1"), "intent-A",
            b.action_id, "world-A", 12, "probe-A", "inventory:bread", True,
        ),
    )
    equip = MineflayerEffectResult(
        "world-A", 13, b.action_id + "-equip", "equip_item", "applied", None,
    )
    consume = MineflayerEffectResult(
        "world-A", 14, b.action_id + "-consume", "consume_held", "applied", None,
    )
    after = observation(
        15, session_id="world-A",
        request_id=b.action_id + "-after-eat-00", food=13,
        inventory=(MineflayerInventoryItem("bread", 1, 9),),
    )
    session = OwnedFakeNative([equip, consume, after])
    kw = {
        "proposal": proposal, "previous_probe": previous,
        "current_probe": current, "propose_grant": grants[0],
        "issue_grant": grants[1], "intent_owner": owner,
        "skill_execution": skill, "supervisor": sup,
        "journal": journal, "at_ns": 5, "provenance": prov,
        "grant_real_world": True,
        "acknowledge_dev_unverified_principal": True,
    }
    return kw, session, grants, (equip, consume, after)


def run(kw, session):
    return asyncio.run(issue_selected_eat_dev(session, **kw))


def test_eat_native_parent_issues_once_only_after_fsynced_journal(tmp_path):
    kw, session, _, native = setup(tmp_path)
    receipt = run(kw, session)
    assert receipt.status == "NATIVE_EAT_OUTCOME_DEV_ONLY"
    assert receipt.terminal.state is ActionState.OUTCOME
    assert kw["supervisor"].get("action-eat-A") is receipt.terminal
    assert receipt.item == "bread"
    assert receipt.item_count_before == 2 and receipt.item_count_after == 1
    assert receipt.food_before == 7 and receipt.food_after == 13
    assert session.sent == [
        ("equip_item", "action-eat-A-equip", "bread"),
        ("consume_held", "action-eat-A-consume"),
        ("observe", "action-eat-A-after-eat-00"),
    ]
    assert kw["journal"].unresolved is False
    restored = PhysicalActionJournal.restore(
        kw["journal"].path, self_id="self-A",
    )
    restored.require_clear()
    assert len(restored.records) == 1
    assert restored.records[0]["status"] == "NATIVE_EAT_OUTCOME"
    assert restored.records[0]["effect_seqs"] == [13, 14]
    assert restored.records[0]["after_seq"] == 15
    with pytest.raises(PhysicalEatRefusal):
        run(kw, session)  # Never redispatch the same issued Action.
    assert len(session.sent) == 3


@pytest.mark.parametrize("changed", [
    "no_real_grant", "no_dev_ack", "same_authority", "foreign_intent",
    "foreign_source", "other_selected_food", "other_world",
    "moved", "missing_food", "near_entity", "busy_skill",
])
def test_reject_before_wal_and_native_io(tmp_path, changed):
    kw, session, grants, _ = setup(tmp_path)
    if changed == "no_real_grant":
        kw["grant_real_world"] = False
    elif changed == "no_dev_ack":
        kw["acknowledge_dev_unverified_principal"] = False
    elif changed == "same_authority":
        kw["issue_grant"] = replace(grants[1], authority_id="external-proposer")
    elif changed == "foreign_intent":
        kw["issue_grant"] = replace(grants[1], intent_id="other")
    elif changed == "foreign_source":
        kw["issue_grant"] = replace(grants[1], probe_request_id="other")
    elif changed == "other_selected_food":
        kw["issue_grant"] = replace(grants[1], selected_target_ref="inventory:apple")
    elif changed == "other_world":
        kw["current_probe"] = replace(kw["current_probe"], session_id="other-world")
    elif changed == "moved":
        p = kw["current_probe"].snapshot.position
        kw["current_probe"] = replace(
            kw["current_probe"], snapshot=replace(
                kw["current_probe"].snapshot, position=replace(p, x=p.x + 0.1),
            ),
        )
    elif changed == "missing_food":
        kw["current_probe"] = replace(
            kw["current_probe"], snapshot=replace(
                kw["current_probe"].snapshot, inventory=(),
            ),
        )
    elif changed == "near_entity":
        kw["current_probe"] = replace(
            kw["current_probe"], snapshot=replace(
                kw["current_probe"].snapshot,
                nearby_entities_coverage=replace(
                    kw["current_probe"].snapshot.nearby_entities_coverage,
                    candidate_count=1,
                ),
                nearby_entities=(zombie(),),
            ),
        )
    elif changed == "busy_skill":
        kw["skill_execution"] = kw["skill_execution"].succeed(
            reason="already done", at_ns=4, provenance=kw["provenance"],
        )
    with pytest.raises((PhysicalEatRefusal, ValueError)):
        run(kw, session)
    assert session.sent == []
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()


def test_durable_fsync_failure_is_hard_stop_before_supervisor_issue(tmp_path, monkeypatch):
    kw, session, _, _ = setup(tmp_path)
    def fail_commit(*args, **kwargs):
        raise OSError("TEST_DISK_FAILURE")
    monkeypatch.setattr(kw["journal"], "_commit", fail_commit)
    with pytest.raises(OSError, match="TEST_DISK_FAILURE"):
        run(kw, session)
    assert session.sent == []
    assert kw["supervisor"].recorded_actions == ()
    assert kw["journal"].records == ()


def test_interrupt_after_equip_ack_leaves_unknown_and_restart_stop(tmp_path):
    kw, session, _, native = setup(tmp_path)
    session.events = [native[0]]  # Model lost before consume ACK.
    with pytest.raises(RuntimeError, match="scripted native disconnect"):
        run(kw, session)
    assert session.sent == [
        ("equip_item", "action-eat-A-equip", "bread"),
        ("consume_held", "action-eat-A-consume"),
    ]
    assert kw["supervisor"].get("action-eat-A").state is ActionState.UNKNOWN
    assert kw["journal"].unresolved
    recovered = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    with pytest.raises(PhysicalJournalUnresolved, match="STOP/UNKNOWN"):
        recovered.require_clear()
    with pytest.raises(PhysicalJournalUnresolved):
        run(kw, session)  # Never retry after any potential native issue.
    assert len(session.sent) == 2


def test_after_ack_without_food_increase_remains_persistent_unknown(tmp_path):
    kw, session, _, native = setup(tmp_path)
    no_consequence = replace(native[2], snapshot=replace(
        native[2].snapshot, food=7, inventory=(bread(),),
    ))
    # 8 different correlated after-probe requests, no body change.
    session.events = [native[0], native[1]] + [
        replace(no_consequence, seq=15 + i,
                request_id=f"action-eat-A-after-eat-{i:02d}")
        for i in range(8)
    ]
    with pytest.raises(PhysicalEatRefusal, match="nutrition unverified"):
        run(kw, session)
    assert kw["supervisor"].get("action-eat-A").state is ActionState.UNKNOWN
    assert kw["journal"].unresolved
    assert len([x for x in session.sent if x[0] == "consume_held"]) == 1
    assert len([x for x in session.sent if x[0] == "observe"]) == 8


def test_persisted_cas_duplicate_action_and_foreign_self_fail_closed(tmp_path):
    kw, _, _, _ = setup(tmp_path)
    a = kw["journal"]
    stale = PhysicalActionJournal.restore(a.path, self_id="self-A")
    a.prepare_eat(kw["proposal"].binding, kw["current_probe"])
    with pytest.raises(PhysicalJournalReplay, match="CAS writer conflict"):
        stale.prepare_eat(kw["proposal"].binding, kw["current_probe"])
    recovered = PhysicalActionJournal.restore(a.path, self_id="self-A")
    with pytest.raises(PhysicalJournalUnresolved):
        recovered.prepare_eat(kw["proposal"].binding, kw["current_probe"])
    with pytest.raises(PhysicalJournalError, match="foreign Self"):
        PhysicalActionJournal.restore(a.path, self_id="self-B")
    with pytest.raises(PhysicalJournalReplay, match="restored"):
        PhysicalActionJournal.create(a.path, self_id="self-A")


def test_tampered_journal_and_symlink_are_not_resets(tmp_path):
    kw, _, _, _ = setup(tmp_path)
    path = kw["journal"].path
    raw = json.loads(path.read_text())
    raw["body"]["self_id"] = "evil-self"
    path.write_text(json.dumps(raw))
    with pytest.raises(PhysicalJournalError, match="checksum"):
        PhysicalActionJournal.restore(path, self_id="evil-self")
    path.unlink()
    target = tmp_path / "target.json"
    target.write_text("{}")
    path.symlink_to(target)
    with pytest.raises(PhysicalJournalError):
        PhysicalActionJournal.create(path, self_id="self-A")
    with pytest.raises(PhysicalJournalError):
        PhysicalActionJournal.restore(path, self_id="self-A")


def test_journal_close_rejects_replaced_native_after_probe(tmp_path):
    kw, session, _, events = setup(tmp_path)
    result = run(kw, session)
    restored = PhysicalActionJournal.restore(kw["journal"].path, self_id="self-A")
    assert not restored.unresolved
    # Existing terminal journal is sealed; it may not be rewritten.
    with pytest.raises(PhysicalJournalError, match="unresolved"):
        restored.close_eat(
            kw["proposal"].binding, kw["current_probe"],
            events[0], events[1], events[2],
            result.terminal, kw["supervisor"],
        )


def test_forged_action_binding_cannot_issue_different_proposal_lifecycle(tmp_path):
    kw, session, _, _ = setup(tmp_path)
    wrong = replace(
        kw["proposal"].binding, action_id="another-native-action",
    )
    kw["proposal"] = replace(kw["proposal"], binding=wrong)
    with pytest.raises(PhysicalEatRefusal, match="native correlated window"):
        run(kw, session)
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()
    assert session.sent == []


def test_close_fsync_failure_after_native_eat_keeps_wal_unresolved(tmp_path, monkeypatch):
    kw, session, _, _ = setup(tmp_path)
    journal = kw["journal"]
    original = journal._commit
    commit_count = 0

    def fail_after_native_eat(rows):
        nonlocal commit_count
        commit_count += 1
        if commit_count == 2:
            raise OSError("SIMULATED_CLOSE_FSYNC_FAILURE")
        return original(rows)

    monkeypatch.setattr(journal, "_commit", fail_after_native_eat)
    with pytest.raises(OSError, match="SIMULATED_CLOSE_FSYNC_FAILURE"):
        run(kw, session)
    assert commit_count == 2
    assert len(session.sent) == 3  # The one equip and consume already happened.
    assert kw["supervisor"].get("action-eat-A").state is ActionState.OUTCOME
    recovered = PhysicalActionJournal.restore(journal.path, self_id="self-A")
    with pytest.raises(PhysicalJournalUnresolved, match="STOP/UNKNOWN"):
        recovered.require_clear()
    assert recovered.records[0]["status"] == "PREPARED_UNRESOLVED"
    # A terminal in-memory Action does not retroactively prove durable close.


def test_native_eat_rejected_equip_keeps_unknown_without_consume(tmp_path):
    kw, session, _, events = setup(tmp_path)
    session.events = [
        replace(events[0], result="rejected", error="cannot_equip"),
    ]
    with pytest.raises(PhysicalEatRefusal, match="ACK not applied"):
        run(kw, session)
    assert session.sent == [("equip_item", "action-eat-A-equip", "bread")]
    assert kw["supervisor"].get("action-eat-A").state is ActionState.UNKNOWN
    assert kw["journal"].unresolved
