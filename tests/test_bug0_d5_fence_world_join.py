"""Offline pre-World D5 nonmotion fence integration and refusal tests.

No Paper, Minecraft, Node, physical effects or learned state.
"""
from __future__ import annotations

import asyncio
import json

import pytest

import test_bug0_s49_attack_owner as attack
import test_s49_nonmotion_physical_fence as original
from relay_self.s49_nonmotion_physical_fence import (
    NonMotionFenceError,
    NonMotionReplay,
    NonMotionUnresolved,
    OriginalS49NonMotionFence,
)
from tools.bug0_d4_oneworld import preflight_original_nonmotion_fence, run
from tools.bug0_d5_fence_post import D5NonMotionAuditRejected, audit


def _pending(path):
    fence = OriginalS49NonMotionFence.create(path, self_id="s49-original-self")
    _, current = attack._pair()
    fence.prepare_attack(
        probe=current, intent_id="escape-threat", action_id="unresolved-original",
        target_entity_id=current.snapshot.nearby_entities[0].entity_id,
    )
    return fence


def test_preflight_creates_only_one_original_empty_fence(tmp_path):
    path = tmp_path / "original.json"
    first, restored = preflight_original_nonmotion_fence(path)
    assert restored is False and first.actions == ()
    later, restored = preflight_original_nonmotion_fence(path)
    assert restored is True and later.actions == ()
    assert later.sha256 == first.sha256


def test_preflight_rejects_unresolved_original_physical_effect(tmp_path):
    path = tmp_path / "original.json"
    _pending(path)
    with pytest.raises(NonMotionUnresolved):
        preflight_original_nonmotion_fence(path)
    assert OriginalS49NonMotionFence.restore(
        path, self_id="s49-original-self",
    ).unresolved


def test_preflight_refuses_already_sealed_old_world_even_if_outcome(
    tmp_path, monkeypatch,
):
    path = tmp_path / "original.json"
    owner, _, receipt, fence, native, grant = original._attack(monkeypatch, path)
    assert receipt.terminal is owner.supervisor.get(grant.action_id)
    assert not fence.unresolved and native.sent
    with pytest.raises(NonMotionReplay):
        preflight_original_nonmotion_fence(path)


@pytest.mark.parametrize("mode", ["corrupt", "symlink", "missing-parent"])
def test_preflight_fails_closed_on_invalid_persistent_store(tmp_path, mode):
    path = tmp_path / "original.json"
    if mode == "corrupt":
        path.write_text('{"body": "injected"}', encoding="utf8")
    elif mode == "symlink":
        other = tmp_path / "other.json"
        other.write_text("{}", encoding="utf8")
        path.symlink_to(other)
    else:
        path = tmp_path / "absent" / "original.json"
    with pytest.raises((NonMotionFenceError, ValueError)):
        preflight_original_nonmotion_fence(path)


def test_world_entry_refuses_unresolved_before_provisioning_paper(
    tmp_path, monkeypatch,
):
    report_path = tmp_path / "original_report.json"
    fence_path = tmp_path / "original_fence.json"
    _pending(fence_path)
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_S49_D4_ONE_WORLD_ONLY", "1")
    monkeypatch.setenv("S49_D5_NONMOTION_FENCE_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    rc = asyncio.run(run(
        report_path, tmp_path / "paper_original.log",
        nonmotion_fence_path=fence_path,
    ))
    report = json.loads(report_path.read_text(encoding="utf8"))
    assert rc == 2 and report["status"] == "FAIL"
    assert report["stage"] == "NOT_STARTED"
    assert report.get("real_world_started") is not True
    assert report["s49_actions"] == []
    assert report["nonmotion_fence"]["unresolved"] is True
    assert len(report["nonmotion_fence"]["action_ids"]) == 1


def test_world_entry_requires_explicit_optin_before_start(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("BUG0_S49_D4_ONE_WORLD_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.delenv("S49_D5_NONMOTION_FENCE_DEV_ONLY", raising=False)
    report_path = tmp_path / "report.json"
    fence_path = tmp_path / "fence.json"
    rc = asyncio.run(run(
        report_path, tmp_path / "paper.log",
        nonmotion_fence_path=fence_path,
    ))
    assert rc == 2 and not fence_path.exists()
    report = json.loads(report_path.read_text(encoding="utf8"))
    assert report.get("real_world_started") is not True
    assert report["status"] == "FAIL"


def test_independent_post_audit_refuses_missing_or_fake_d5_world(
    tmp_path, monkeypatch,
):
    path = tmp_path / "original.json"
    original._attack(monkeypatch, path)
    with pytest.raises(D5NonMotionAuditRejected):
        audit({"status": "PASS_DEV"}, path)
    with pytest.raises(D5NonMotionAuditRejected):
        audit({"status": "PASS_DEV",
               "classification": "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS",
               "nonmotion_fence_preflight": {"checked_before_world": True,
                                             "prior_actions": 0,
                                             "filename": path.name},
               "nonmotion_fence": {"sha256": "forged"},
               "s49_actions": [{"action_id": "fake"}],
               "d5_second_action": {"action_id": "fake2"},
               "d4_natural_food_pickup_eat_proven": False,
               "session_id": "fake"}, path)
