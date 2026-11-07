"""D6-B original S49, genuine S15 MOVE and C1 durable MOVE fence offline.

Synthetic native frames for protocol correctness. No real World/physical effect.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer import normal_action
from adapters.mineflayer.d6_loot_approach import source_qualified_loot_approach
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalLootMoveAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from relay_self.action import ActionState
from relay_self.c1_physical_action_fence import (
    OriginalS49PhysicalFence, UnresolvedPhysicalAction,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_d6_loot_approach import pair
from test_mineflayer_execution_qualification import FakeSession


class LootNativeSession(FakeSession):
    @property
    def process_returncode(self):
        return None


def fixture(monkeypatch, tmp_path):
    previous, current = pair()
    # The reused S15 scripted session has this exact original native ID.
    previous = replace(previous, session_id="s15-session")
    current = replace(current, session_id="s15-session")
    candidate = source_qualified_loot_approach(
        previous, current, item_entity_id=42,
    )
    intent = IntentCommitment()
    intent.commit(
        "collect-loot", objective="bounded original S49 item approach", at_ns=1,
        provenance=Provenance("d6-scripted", "intent"),
    )
    owner = NormalSessionActionExecutor(current.session_id, intent)
    action = "d6-native-back-to-item"
    common = dict(
        intent_id="collect-loot", session_id=current.session_id,
        action_id=action, probe_seq=current.seq,
        probe_request_id=current.request_id, item_entity_id=42,
        granted=True,
    )
    propose = NormalLootMoveAuthorization(
        stage=NormalActionStage.PROPOSE,
        authority_id="d6-dev-propose",
        provenance=Provenance("d6-independent-dev-operator", "propose"),
        **common,
    )
    issue = NormalLootMoveAuthorization(
        stage=NormalActionStage.ISSUE,
        authority_id="d6-dev-issue",
        provenance=Provenance("d6-independent-dev-operator", "issue"),
        **common,
    )
    fence = OriginalS49PhysicalFence.create(
        tmp_path / "d6_move_physical.json", self_id="s49-original-self",
    )
    monkeypatch.setattr(normal_action, "MineflayerProcessSession", LootNativeSession)
    after_position = replace(
        current.snapshot.position, x=current.snapshot.position.x + 0.4,
    )
    after = replace(
        current, seq=305, request_id=None,
        snapshot=replace(current.snapshot, position=after_position),
    )
    frames = (
        replace(current, seq=302, request_id=None),
        MineflayerEffectResult(
            current.session_id, 303, action, "set_control", "applied", None,
        ),
        MineflayerEffectResult(
            current.session_id, 304, action + "-s15-clear",
            "clear_controls", "applied", None,
        ),
        after,
    )
    session = LootNativeSession(frames)
    return previous, current, candidate, owner, propose, issue, fence, session


def test_d6_original_s49_owner_fence_and_real_s15_protocol(monkeypatch, tmp_path):
    previous, current, candidate, owner, propose, issue, fence, native = (
        fixture(monkeypatch, tmp_path)
    )
    receipt = asyncio.run(owner.execute_d6_loot_move(
        native, previous, current, candidate, propose, issue,
        physical_fence=fence,
    ))
    assert receipt.terminal.state is ActionState.OUTCOME
    assert owner.supervisor.get(propose.action_id) is receipt.terminal
    assert owner._dispatched == {propose.action_id}
    assert owner._count == 1
    assert owner._post_move_settling_unqualified is True
    assert receipt.consequence.movement_distance == pytest.approx(0.4)
    assert native.sent == [
        ("observe",),
        ("set_control", propose.action_id, "back", True),
        ("clear_controls", propose.action_id + "-s15-clear"),
        ("observe",),
    ]
    assert not fence.unresolved
    loaded = OriginalS49PhysicalFence.restore(
        fence.path, self_id="s49-original-self",
    )
    loaded.require_clear()
    assert len(loaded.actions) == 1
    row = loaded.actions[0]
    assert row["status"] == "S16_OUTCOME"
    assert row["decision_seq"] == current.seq
    assert row["action_id"] == propose.action_id
    assert row["intent_id"] == "collect-loot"
    assert row["dispatch_seq"] == 303 and row["cleanup_seq"] == 304
    assert row["movement_m"] == pytest.approx(0.4)
    read = owner.read_only_post_move_eat_boundary(receipt)
    assert read.s15_clear_ack_applied is True
    assert read.eat_issuance_authorized is False
    assert read.physically_stopped_proven is False
    assert read.settling_status == "WORLD_TICK_IDLE_NOT_ATTESTED"
    with pytest.raises(NormalActionRejected):
        owner.require_d6_loot_move_authorizations(
            previous, current, candidate, propose, issue,
        )


def test_d6_preissue_failure_does_not_issue_any_native_move(
    monkeypatch, tmp_path,
):
    previous, current, candidate, owner, propose, issue, fence, native = (
        fixture(monkeypatch, tmp_path)
    )
    def fail(*args, **kwargs):
        raise OSError("durable write unavailable")
    monkeypatch.setattr(fence, "prepare", fail)
    with pytest.raises(OSError):
        asyncio.run(owner.execute_d6_loot_move(
            native, previous, current, candidate, propose, issue,
            physical_fence=fence,
        ))
    assert not native.sent
    assert owner._dispatched == set()
    assert owner._count == 0
    assert owner.supervisor.open_actions == ()
    assert fence.actions == ()


@pytest.mark.parametrize("mutation", [
    "same_authority", "foreign_session", "foreign_intent", "stale_probe",
    "wrong_item", "bad_grant", "forged_candidate", "existing_unknown",
])
def test_d6_inadmissible_source_authority_cannot_touch_native_or_fence(
    monkeypatch, tmp_path, mutation,
):
    previous, current, candidate, owner, propose, issue, fence, native = (
        fixture(monkeypatch, tmp_path)
    )
    if mutation == "same_authority":
        issue = replace(issue, authority_id=propose.authority_id)
    elif mutation == "foreign_session":
        issue = replace(issue, session_id="foreign")
    elif mutation == "foreign_intent":
        propose = replace(propose, intent_id="foreign")
    elif mutation == "stale_probe":
        issue = replace(issue, probe_seq=current.seq - 1)
    elif mutation == "wrong_item":
        issue = replace(issue, item_entity_id=43)
    elif mutation == "bad_grant":
        issue = replace(issue, granted=False)
    elif mutation == "forged_candidate":
        candidate = replace(candidate, item_distance_m=0.05)
    else:
        owner._last_issued_probe_seq = current.seq
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_d6_loot_move(
            native, previous, current, candidate, propose, issue,
            physical_fence=fence,
        ))
    assert native.sent == []
    assert fence.actions == ()


def test_d6_native_dispatch_rejection_retains_unresolved_ledger(
    monkeypatch, tmp_path,
):
    previous, current, candidate, owner, propose, issue, fence, native = (
        fixture(monkeypatch, tmp_path)
    )
    native.fail_set_control = True
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_d6_loot_move(
            native, previous, current, candidate, propose, issue,
            physical_fence=fence,
        ))
    assert len([s for s in native.sent if s[0] == "set_control"]) == 1
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert fence.unresolved is True
    with pytest.raises(UnresolvedPhysicalAction):
        OriginalS49PhysicalFence.restore(
            fence.path, self_id="s49-original-self",
        ).require_clear()
