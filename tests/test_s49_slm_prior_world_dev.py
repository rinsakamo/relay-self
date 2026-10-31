"""DEV prior original S49 source admission is always withheld from L8 training.

Offline source-shaped fixtures; real saved W3 bytes are independently
read back later by a separate exact-source GitHub Actions DEV step.
"""
from __future__ import annotations

import json
import pytest

from adapters.mineflayer import slm_prior_world_dev
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from adapters.mineflayer.slm_prior_world_dev import PriorWorldRejected, read_previous_s49_world
from test_s49_slm_passive_dev import setup

SID = "older-native-dev-session"
HASH = "a" * 64


def old_world(tmp_path, monkeypatch):
    root = tmp_path / "past"
    root.mkdir()
    (root / "native").mkdir()
    rows = []
    for seq, num in ((21, 20), (48, 47)):
        aid = f"s49-native-move-{num}"
        before, after = seq + 1, seq + 8
        rows.append({
            "action": aid, "probe_seq": seq, "terminal": "outcome",
            "source": SID, "execution_evidence": {
                "status": "executed", "action_id": aid, "session_id": SID,
                "goal_success_attested": False,
                "learning_feedback_qualified": False,
                "dispatch_receipt": {
                    "action_id": aid, "seq": before + 1,
                    "result": "applied", "effect": "set_control",
                },
                "cleanup_receipt": {
                    "action_id": aid + "-s15-clear", "seq": after - 1,
                    "result": "applied", "effect": "clear_controls",
                },
                "before_observation": {"session_id": SID, "seq": before},
                "after_observation": {"session_id": SID, "seq": after},
            },
        })
    w3 = {
        "session_id": SID, "stdout_sha256": HASH, "last_seq": 58,
        "frame_count": 59, "status": "COMPLETE_NODE_STDOUT",
    }
    report = {
        "status": "PASS", "session_id": SID, "node_exit": 0,
        "server_exit": 0, "real_model_calls": 0,
        "learning_in_world": False,
        "actual_native_actions": rows, "w3_node_stdout_capture": w3,
    }
    monkeypatch.setattr(slm_prior_world_dev, "audit_w3_sealed_stdout", lambda root: w3)
    (root / "report.json").write_text(json.dumps(report))
    return root, report


def test_previous_original_action_can_only_be_withheld(tmp_path, monkeypatch):
    root, _ = old_world(tmp_path, monkeypatch)
    read = read_previous_s49_world(root, expected_stdout_sha256=HASH)
    assert read.session_id == SID
    assert read.original_action_ids == (
        "s49-native-move-20", "s49-native-move-47",
    )
    assert read.original_goal_labels == read.l8_admissible_episodes == 0
    assert not read.s10_commit_permitted
    _, host, supervisor, _, _ = setup()
    # Isolated same S49 original host, no new Action issuer or learned candidate.
    inherited = S49SLMDevOwner(retention_enabled=True, prior_world=read)
    inherited.bind(type(host)(
        host.session_id, host.intent_id, host.retained,
    ), supervisor)
    assert inherited.prior_world.session_id != host.session_id
    assert inherited.cognition is not None
    assert inherited.ledger.credit_count == 0
    summary = inherited.finish([])
    assert summary["previous_world"]["status"] == "WITHHELD_NO_INDEPENDENT_EXTERNAL_GOAL"
    assert summary["previous_world"]["original_goal_labels"] == 0
    assert summary["previous_world"]["l8_admissible_episodes"] == 0
    assert summary["l8_training_admissions"] == 0
    assert summary["one_l8_memory_owner"] is True


@pytest.mark.parametrize("attack", (
    "wrong_sha", "unclosed", "forged_goal", "missing_clear", "foreign_session",
    "duplicate_action", "future_seq", "fake_learning", "missing_native",
))
def test_previous_world_abstains_on_tampered_or_incomplete_source(tmp_path, monkeypatch, attack):
    root, r = old_world(tmp_path, monkeypatch)
    if attack == "wrong_sha":
        with pytest.raises(PriorWorldRejected):
            read_previous_s49_world(root, expected_stdout_sha256="b" * 64)
        return
    if attack == "unclosed":
        r["actual_native_actions"][0]["terminal"] = "unknown"
    elif attack == "forged_goal":
        r["actual_native_actions"][0]["execution_evidence"]["goal_success_attested"] = True
    elif attack == "missing_clear":
        r["actual_native_actions"][0]["execution_evidence"]["cleanup_receipt"] = None
    elif attack == "foreign_session":
        r["actual_native_actions"][0]["source"] = "other"
    elif attack == "duplicate_action":
        r["actual_native_actions"][1] = r["actual_native_actions"][0]
    elif attack == "future_seq":
        r["actual_native_actions"][1]["execution_evidence"]["after_observation"]["seq"] = 100
    elif attack == "fake_learning":
        r["learning_in_world"] = True
    else:
        (root / "report.json").unlink()
        with pytest.raises(PriorWorldRejected):
            read_previous_s49_world(root, expected_stdout_sha256=HASH)
        return
    (root / "report.json").write_text(json.dumps(r))
    with pytest.raises(PriorWorldRejected):
        read_previous_s49_world(root, expected_stdout_sha256=HASH)


def test_current_and_previous_world_cannot_share_session(tmp_path, monkeypatch):
    root, _ = old_world(tmp_path, monkeypatch)
    history = read_previous_s49_world(root, expected_stdout_sha256=HASH)
    _, host, supervisor, _, _ = setup()
    from adapters.mineflayer.normal_action import NormalWorldL0

    current = NormalWorldL0(
        history.session_id, host.intent_id, host.retained,
    )
    with pytest.raises(ValueError, match="its own prior"):
        S49SLMDevOwner(prior_world=history).bind(current, supervisor)


def test_persistent_cognition_owner_shared_across_three_original_probes():
    owner, host, _, native, event = setup()
    assert owner.cognition is not None
    initial = owner.cognition
    from test_s49_slm_passive_dev import decide

    decide(owner, host, native, event)
    read = owner.finish([])
    assert read["one_l8_memory_owner"] is True
    assert read["l8_training_admissions"] == 0
    assert owner.cognition is initial
    assert read["rows"][0]["status"] == "RECORDED"
