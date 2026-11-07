"""D6-C no-World restart/refusal tests and strict staged-item audit negatives."""
from __future__ import annotations

import asyncio
import json

import pytest

import test_d6_original_s49_loot_move as d6b
from relay_self.c1_physical_action_fence import (
    OriginalS49PhysicalFence,
    PhysicalReplay,
    UnresolvedPhysicalAction,
)
from tools.bug0_d6_staged_move_post import (
    D6StagedSourceAuditRejected,
    audit,
)
from tools.bug0_d6_staged_move_world import preflight_move_fence, run


def test_first_preflight_only_allows_empty_original_c1_fence(tmp_path):
    path = tmp_path / "original_s49_move.json"
    fence = preflight_move_fence(path)
    assert fence.actions == () and not fence.unresolved
    again = preflight_move_fence(path)
    assert again.actions == () and again.sha256 == fence.sha256


def test_existing_unresolved_move_aborts_before_new_world(tmp_path):
    path = tmp_path / "original_s49_move.json"
    fence = preflight_move_fence(path)
    before, current = d6b.pair()
    fence.prepare(
        session_id=current.session_id,
        intent_id="collect-loot",
        action_id="prior-native-io-unknown",
        probe=current,
    )
    with pytest.raises(UnresolvedPhysicalAction):
        preflight_move_fence(path)
    assert OriginalS49PhysicalFence.restore(
        path, self_id="s49-original-self",
    ).unresolved


def test_sealed_old_world_must_not_be_reseeded(tmp_path, monkeypatch):
    before, current, candidate, owner, propose, issue, fence, native = (
        d6b.fixture(monkeypatch, tmp_path)
    )
    asyncio.run(owner.execute_d6_loot_move(
        native, before, current, candidate, propose, issue,
        physical_fence=fence,
    ))
    fence.require_clear()
    with pytest.raises(PhysicalReplay):
        preflight_move_fence(fence.path)


@pytest.mark.parametrize("mode", ["symlink", "missing-parent", "corrupted"])
def test_nonregular_or_missing_preflight_store_is_rejected(tmp_path, mode):
    path = tmp_path / "original.json"
    if mode == "symlink":
        other = tmp_path / "other"
        other.write_text("{}", encoding="utf8")
        path.symlink_to(other)
    elif mode == "missing-parent":
        path = tmp_path / "absent" / "original.json"
    else:
        path.write_text('{"bad":"checksum"}', encoding="utf8")
    with pytest.raises(ValueError):
        preflight_move_fence(path)


def test_real_world_entry_requires_exclusive_gate_before_paper(tmp_path, monkeypatch):
    monkeypatch.delenv("D6_STAGED_LOOT_MOVE_WORLD_ONLY", raising=False)
    report = tmp_path / "report.json"
    fence = tmp_path / "fence.json"
    result = asyncio.run(run(report, tmp_path / "paper.log", fence))
    assert result == 2 and not fence.exists()
    body = json.loads(report.read_text(encoding="utf8"))
    assert body["status"] == "BLOCKED"
    assert body["real_world_started"] is False
    assert body["original_s49_actions"] == 0
    assert body["physical_action_issued"] is False


def test_world_entry_refuses_unresolved_without_server_start(tmp_path, monkeypatch):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_PICKUP_D1_DEV_ONLY", "1")
    monkeypatch.setenv("D6_STAGED_LOOT_MOVE_WORLD_ONLY", "1")
    path = tmp_path / "fence.json"
    before, current = d6b.pair()
    fence = preflight_move_fence(path)
    fence.prepare(
        session_id=current.session_id, intent_id="collect-loot",
        action_id="unresolved-original-move", probe=current,
    )
    report = tmp_path / "report.json"
    rc = asyncio.run(run(report, tmp_path / "paper.log", path))
    body = json.loads(report.read_text(encoding="utf8"))
    assert rc == 2
    assert body["classification"] == "D6_PREWORLD_REFUSED"
    assert body["real_world_started"] is False


def test_independent_post_audit_never_accepts_fake_success(tmp_path):
    with pytest.raises(D6StagedSourceAuditRejected):
        audit("", {"status": "PASS_DEV"}, tmp_path / "absent.json")
    log = (
        "RSELF_LOOT_STAGED world=00000000-0000-0000-0000-000000000001 "
        "owner=00000000-0000-0000-0000-000000000002 "
        "entity=00000000-0000-0000-0000-000000000003 "
        "item=rotten_flesh count=1 tick=10 "
        "source=OPERATOR_FIXTURE_NOT_ZOMBIE_DROP mode=BACK_2_2M\n"
        "RSELF_LOOT_PICKED world=00000000-0000-0000-0000-000000000001 "
        "owner=00000000-0000-0000-0000-000000000002 "
        "entity=00000000-0000-0000-0000-000000000003 "
        "item=rotten_flesh count=1 tick=15 "
        "source=ACTUAL_PAPER_PICKUP_EVENT\n"
    )
    with pytest.raises(D6StagedSourceAuditRejected):
        audit(log, {"status": "PASS_DEV"}, tmp_path / "absent.json")
