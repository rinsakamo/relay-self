"""DEV S49 pre-ISSUE physical fence: typed synthetic original receipts only.

Never invokes Minecraft, physical S49 Action IO or an LLM.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import replace

import pytest

import relay_self.c1_physical_action_fence as storage
from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.s49_normal_session_real_ci import qualify
from relay_self.c1_physical_action_fence import (
    OriginalS49PhysicalFence,
    PhysicalFenceError,
    PhysicalReplay,
    UnresolvedPhysicalAction,
)
from test_s49_c1_motion_owner_dev import (
    _joined_original_owner,
    _record_synthetic_original_terminal,
)


def _prepared(path):
    owner, executor, intent, step, selected, receipt, auth, p = _joined_original_owner()
    fence = OriginalS49PhysicalFence.create(path, self_id=owner.self_id)
    fence.prepare(
        session_id=selected.session_id, intent_id="escape-threat",
        action_id=step.action_request_id, probe=selected,
    )
    return fence, owner, executor, intent, step, selected, receipt, auth, p


def test_durable_preissue_unknown_blocks_after_crash_even_if_issue_not_proven(tmp_path):
    path = tmp_path / "physical.json"
    fence, owner, _, _, step, selected, _, _, _ = _prepared(path)
    assert fence.unresolved
    assert fence.actions[0]["status"] == "PREPARED_UNRESOLVED"
    restarted = OriginalS49PhysicalFence.restore(path, self_id=owner.self_id)
    with pytest.raises(UnresolvedPhysicalAction, match="STOP/UNKNOWN"):
        restarted.require_clear()
    with pytest.raises(UnresolvedPhysicalAction):
        restarted.prepare(
            session_id=selected.session_id, intent_id="escape-threat",
            action_id=step.action_request_id, probe=selected,
        )
    with pytest.raises(PhysicalReplay):
        OriginalS49PhysicalFence.create(path, self_id=owner.self_id)
    with pytest.raises(PhysicalFenceError):
        OriginalS49PhysicalFence.restore(path, self_id="other-self")


def test_only_original_S16_terminal_and_native_set_clear_seals_preissue(tmp_path):
    path = tmp_path / "physical.json"
    fence, owner, executor, _, step, selected, receipt, auth, p = _prepared(path)
    _, real_shape = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    fence.close(real_shape, selected, original_supervisor=executor.supervisor)
    assert not fence.unresolved
    assert fence.actions[0]["status"] == "S16_OUTCOME"
    assert fence.actions[0]["before_seq"] > selected.seq
    assert fence.actions[0]["after_seq"] > fence.actions[0]["cleanup_seq"]
    assert fence.actions[0]["movement_m"] == pytest.approx(0.31)
    recovered = OriginalS49PhysicalFence.restore(path, self_id=owner.self_id)
    recovered.require_clear()
    assert recovered.sha256 == fence.sha256
    assert recovered.actions == fence.actions
    with pytest.raises(PhysicalFenceError):
        recovered.close(real_shape, selected, original_supervisor=executor.supervisor)
    with pytest.raises(PhysicalReplay):
        recovered.prepare(
            session_id=selected.session_id, intent_id="escape-threat",
            action_id=step.action_request_id, probe=selected,
        )


@pytest.mark.parametrize("failure", [
    "wrong_selected", "wrong_terminal", "wrong_intent",
    "foreign_session", "wrong_control", "wrong_clear",
    "wrong_before_seq", "no_cleanup", "missing_after",
])
def test_forged_or_partial_S16_never_closes_physical_uncertainty(tmp_path, failure):
    fence, owner, executor, _, step, selected, receipt, auth, p = _prepared(
        tmp_path / "physical.json",
    )
    _, r = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    probe = selected
    if failure == "wrong_selected":
        probe = replace(selected, request_id="foreign-native-request")
    elif failure == "wrong_terminal":
        r = replace(r, terminal=receipt.terminal)
    elif failure == "wrong_intent":
        # Intent foreign source is blocked without fabricating an ActionLifecycle.
        fence._body["actions"][-1]["intent_id"] = "foreign-intent"
    elif failure == "foreign_session":
        probe = replace(probe, session_id="other-session")
    elif failure == "wrong_control":
        c = r.consequence
        r = replace(r, consequence=replace(
            c, dispatch_receipt=replace(c.dispatch_receipt, result="rejected",
                                        error="rejected fixture"),
            status=storage.WorldConsequenceStatus.FAILED,
            error="rejected command",
        ))
    elif failure == "wrong_clear":
        c = r.consequence
        r = replace(r, consequence=replace(
            c, cleanup_receipt=replace(c.cleanup_receipt, result="rejected",
                                       error="rejected fixture"),
            status=storage.WorldConsequenceStatus.FAILED,
            error="cleanup failed",
        ))
    elif failure == "wrong_before_seq":
        c = r.consequence
        r = replace(r, consequence=replace(
            c, before_observation=replace(c.before_observation, seq=probe.seq),
            status=storage.WorldConsequenceStatus.FAILED, error="bad provenance",
        ))
    elif failure == "no_cleanup":
        c = r.consequence
        r = replace(r, consequence=replace(
            c, cleanup_receipt=None, status=storage.WorldConsequenceStatus.FAILED,
            error="S15 cleanup missing",
        ))
    elif failure == "missing_after":
        c = r.consequence
        r = replace(r, consequence=replace(
            c, after_observation=None, status=storage.WorldConsequenceStatus.FAILED,
            error="S15 after absent",
        ))
    with pytest.raises(PhysicalFenceError):
        fence.close(r, probe, original_supervisor=executor.supervisor)
    assert OriginalS49PhysicalFence.restore(
        fence.path, self_id=owner.self_id,
    ).unresolved


def test_stale_separate_process_fence_snapshot_cannot_overwrite_owner(tmp_path):
    path = tmp_path / "physical.json"
    fence = OriginalS49PhysicalFence.create(path, self_id="self-a")
    stale = OriginalS49PhysicalFence.restore(path, self_id="self-a")
    owner, executor, _, step, selected, receipt, auth, p = _joined_original_owner()
    fence.prepare(
        session_id=selected.session_id, intent_id="escape-threat",
        action_id=step.action_request_id, probe=selected,
    )
    with pytest.raises(PhysicalReplay, match="CAS"):
        stale.prepare(
            session_id=selected.session_id, intent_id="escape-threat",
            action_id=step.action_request_id, probe=selected,
        )
    _, receipt = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    fence.close(receipt, selected, original_supervisor=executor.supervisor)
    assert len(OriginalS49PhysicalFence.restore(
        path, self_id="self-a",
    ).actions) == 1


@pytest.mark.parametrize("corruption", [
    "invalid_json", "bad_digest", "forged_resolved", "replayed_action",
    "premature_resolved", "wrong_order", "malformed_unresolved",
])
def test_corrupt_or_forged_fence_refuses_recovery(tmp_path, corruption):
    path = tmp_path / "physical.json"
    fence, owner, executor, _, step, selected, receipt, auth, p = _prepared(path)
    _, actual = _record_synthetic_original_terminal(
        owner, executor, step, selected, receipt, auth, p,
    )
    fence.close(actual, selected, original_supervisor=executor.supervisor)
    if corruption == "invalid_json":
        path.write_text('{"truncated":', encoding="utf-8")
    else:
        d = json.loads(path.read_text(encoding="utf-8"))
        body = d["body"]
        item = body["actions"][0]
        if corruption == "bad_digest":
            item["action_id"] = "different-action"
        elif corruption == "forged_resolved":
            item["status"] = "fake-qualified"
        elif corruption == "replayed_action":
            body["actions"].append(item)
        elif corruption == "premature_resolved":
            item["terminal_state"] = None
        elif corruption == "wrong_order":
            item["dispatch_seq"] = item["after_seq"] + 1
        elif corruption == "malformed_unresolved":
            item["status"] = "PREPARED_UNRESOLVED"
        if corruption != "bad_digest":
            d["sha256"] = hashlib.sha256(storage._canonical(body)).hexdigest()
        path.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(PhysicalFenceError):
        OriginalS49PhysicalFence.restore(path, self_id=owner.self_id)


def test_failed_pre_issue_write_refuses_physical_action_and_leave_owner_untouched(
    monkeypatch, tmp_path,
):
    path = tmp_path / "physical.json"
    fence = OriginalS49PhysicalFence.create(path, self_id="self-a")
    _, executor, _, step, selected, _, _, _ = _joined_original_owner()

    def write_failed(*_args, **_kwargs):
        raise OSError("simulated durable PREPARED fsync failure")

    monkeypatch.setattr(storage, "_write", write_failed)
    with pytest.raises(OSError, match="simulated"):
        fence.prepare(
            session_id=selected.session_id, intent_id="escape-threat",
            action_id=step.action_request_id, probe=selected,
        )
    assert executor._count == 0
    assert not executor._dispatched
    assert not executor.supervisor.open_actions
    assert OriginalS49PhysicalFence.restore(path, self_id="self-a").actions == ()


def test_original_executor_has_only_optin_pre_issue_reservation_before_supervisor_issue():
    source = inspect.getsource(NormalSessionActionExecutor.execute)
    assert "pre_issue_reservation: Callable[[], None] | None = None" in source
    assert source.index("pre_issue_reservation()") < source.index(
        "issued = self.supervisor.issue(",
    )
    assert source.index("issued = self.supervisor.issue(") < source.index(
        "await execute_mineflayer_command(",
    )


def test_ungranted_physical_fence_dev_denies_before_world(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_DEV_ONLY", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_TWO_INTENTS_DEV_ONLY", "1")
    monkeypatch.setenv("S49_C1_JOURNAL_DEV_ONLY", "1")
    monkeypatch.delenv("S49_C1_PHYSICAL_FENCE_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report = tmp_path / "blocked.json"
    rc = asyncio.run(qualify(
        report, tmp_path / "server.log", unified_c1_dev=True,
        unified_c1_two_intents_dev=True, unified_c1_journal_dev=True,
        unified_c1_physical_fence_dev=True,
    ))
    body = json.loads(report.read_text(encoding="utf-8"))
    assert rc == 2 and body["status"] == "BLOCKED"
    assert body["stage"] == "START"
    assert "pre-ISSUE physical fence" in body["error"]
    assert not (tmp_path / "c1_physical_action_fence.json").exists()
    assert body["actual_native_actions"] == []



def test_restart_with_pending_physical_action_blocks_before_world_provision(
    monkeypatch, tmp_path,
):
    import asyncio

    path = tmp_path / "c1_physical_action_fence.json"
    fence, owner, _, _, _, _, _, _, _ = _prepared(path)
    assert fence.unresolved and len(fence.actions) == 1
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_DEV_ONLY", "1")
    monkeypatch.setenv("S49_UNIFIED_C1_TWO_INTENTS_DEV_ONLY", "1")
    monkeypatch.setenv("S49_C1_JOURNAL_DEV_ONLY", "1")
    monkeypatch.setenv("S49_C1_PHYSICAL_FENCE_DEV_ONLY", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report_path = tmp_path / "pending-blocked.json"
    rc = asyncio.run(qualify(
        report_path, tmp_path / "nonexistent-minecraft.log",
        unified_c1_dev=True, unified_c1_two_intents_dev=True,
        unified_c1_journal_dev=True,
        unified_c1_physical_fence_dev=True,
    ))
    body = json.loads(report_path.read_text(encoding="utf-8"))
    assert rc == 2
    assert body["stage"] == "START"
    assert body["status"] == "BLOCKED"
    assert body["physical_fence_restored_before_world"] is True
    assert body["physical_fence_unresolved_before_world"] is True
    assert "STOP before World" in body["error"]
    assert body["actual_native_actions"] == []
    assert not (tmp_path / "c1_motion_journal.json").exists()
    assert OriginalS49PhysicalFence.restore(
        path, self_id=owner.self_id,
    ).unresolved
