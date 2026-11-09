"""R7: native receipt is diagnostic, never Action or physical STOP authority."""
from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from test_d14_local_oneworld import _fixture_paths, _validate
from test_d14_natural_motion_r6 import controller, observation
from tools.bug0_d14_natural_motion import NaturalMotionRejected
from tools.bug0_d14_r7_evidence_post import inspect_r7_source_only

R7 = "D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY"
D7 = "D7_PASSIVE_CONTROLS_WORLD_ONLY"


def unresolved_fence(tmp_path):
    fence = OriginalS49PhysicalFence.create(
        tmp_path / "original_s49_motion_fence.json",
        self_id="s49-original-self",
    )
    fence.prepare(
        session_id="native-session", intent_id="d14-test-intent",
        action_id="original-move-1", probe=observation(4),
    )
    return fence


def test_missing_original_w3_does_not_turn_prepared_into_outcome(tmp_path):
    original = unresolved_fence(tmp_path)
    result = inspect_r7_source_only(tmp_path)
    assert result["original_motion_fence_sha256"] == original.sha256
    assert result["original_motion_fence_unresolved"] is True
    assert result["w3_received_node_stdout_scope"] == "NOT_CAPTURED"
    assert result["s50_same_client_scope"] == "NOT_CAPTURED"
    assert result["actions"][0]["physical_result_of_unresolved_action"] == "UNKNOWN"
    assert result["actions"][0]["reissue_authorized"] is False
    assert result["paper_tick_aligned_stop_attested"] is False
    assert OriginalS49PhysicalFence.restore(
        original.path, self_id="s49-original-self",
    ).unresolved


def make_w3(tmp_path, *, forged=False):
    rows = [
        {"type": "adapter_started", "session_id": "native-session", "seq": 0},
        {"type": "effect_result", "session_id": "native-session", "seq": 1,
         "action_id": "original-move-1", "effect": "set_control", "result": "applied"},
        {"type": "effect_result", "session_id": "native-session", "seq": 2,
         "action_id": "original-move-1-s15-clear", "effect": "clear_controls",
         "result": "applied"},
    ]
    raw = ("".join(json.dumps(row) + "\n" for row in rows)).encode()
    (tmp_path / "w3-node-stdout.raw.jsonl").write_bytes(raw)
    receipt = {
        "scope": "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP",
        "stdout_sha256": "0" * 64 if forged else hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw), "frame_count": len(rows),
        "first_seq": 0, "last_seq": 2, "session_id": "native-session",
        "status": "INCOMPLETE_UNQUALIFIED",
    }
    (tmp_path / "w3-node-stdout-receipt.json").write_text(json.dumps(receipt))


def make_s50(tmp_path):
    controls = {x: False for x in (
        "forward", "back", "left", "right", "jump", "sprint", "sneak",
    )}
    rows = [
        {"kind": "SESSION_START", "native_seq": 0, "client_physics_tick": 0},
        {"kind": "EFFECT_ACK", "native_seq": 2, "client_physics_tick": 0,
         "native_action_id": "original-move-1-s15-clear", "controls": controls},
    ]
    rows += [
        {"kind": "PHYSICS_TICK", "client_physics_tick": tick, "controls": controls}
        for tick in range(1, 9)
    ]
    for i, row in enumerate(rows, 1):
        row.update({
            "source": "S50_DEV_NATIVE_READBACK_V1", "ordinal": i,
            "session_id": "native-session",
        })
    (tmp_path / "r7-s50-client-readback.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )


def test_w3_and_s50_join_still_never_certifies_paper_stop(tmp_path):
    original = unresolved_fence(tmp_path)
    make_w3(tmp_path)
    make_s50(tmp_path)
    result = inspect_r7_source_only(tmp_path)
    assert result["w3_received_node_stdout_scope"] == (
        "INCOMPLETE_SAME_PROCESS_NODE_STDOUT_ONLY"
    )
    assert result["s50_same_client_scope"] == "SAME_CLIENT_READBACK_ONLY"
    row = result["actions"][0]
    assert [x["seq"] for x in row["node_stdout_effect_results"]] == [1, 2]
    assert row["s50_same_client_clear_ack_seen"] is True
    assert row["s50_postclear_quiet_client_ticks"] == 8
    assert row["physical_dispatch_attested"] is False
    assert row["paper_effective_stop_attested"] is False
    assert row["physical_result_of_unresolved_action"] == "UNKNOWN"
    assert original.unresolved


def test_tampered_w3_receipt_cannot_claim_native_ack(tmp_path):
    unresolved_fence(tmp_path)
    make_w3(tmp_path, forged=True)
    make_s50(tmp_path)
    result = inspect_r7_source_only(tmp_path)
    assert result["w3_received_node_stdout_scope"] == "RECEIPT_OR_SEQUENCE_MISMATCH"
    assert result["actions"][0]["node_stdout_effect_results"] == []
    assert result["actions"][0]["physical_dispatch_attested"] is False


def test_unqualified_s50_client_controls_cannot_be_stop(tmp_path):
    unresolved_fence(tmp_path)
    make_s50(tmp_path)
    file = tmp_path / "r7-s50-client-readback.jsonl"
    text = file.read_text().replace('"ordinal": 10', '"ordinal": 1')
    file.write_text(text)
    result = inspect_r7_source_only(tmp_path)
    assert result["s50_same_client_scope"] == "UNQUALIFIED_CLIENT_SOURCE"
    assert result["actions"][0]["s50_same_client_clear_ack_seen"] is False


def test_r7_requires_an_explicit_r6_and_s50_grant(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4][R7] = "1"
    with pytest.raises(Exception, match="R7_SOURCE_CAPTURE"):
        _validate(paths)
    paths[4]["D14_R6_NATURAL_MOTION_ONEWORLD_ONLY"] = "1"
    with pytest.raises(Exception, match="R7_SOURCE_CAPTURE"):
        _validate(paths)
    paths[4][D7] = "1"
    accepted = _validate(paths)
    assert accepted["r7_source_capture_opt_in"] is True
    assert accepted["r6_original_s49_motion_opt_in"] is True
    assert not paths[1].exists()


def test_r7_unknown_move_persists_read_only_exception_diagnostic(tmp_path, monkeypatch):
    loop, report = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    native_event = observation(4, kind="entities")
    loop.capture_native_event(native_event)
    loop._read = AsyncMock(side_effect=[observation(5), observation(6)])
    loop.policy = SimpleNamespace(
        decide=lambda *_args, **_kwargs: SimpleNamespace(
            selected="DEFER", preferred="MOVE_AWAY", fallback="ATTACK",
            reason="ZOMBIE_NEAR",
        ),
    )
    loop.motion.issue_original_move = AsyncMock(
        side_effect=NaturalMotionRejected("ORIGINAL_S49_MOVE_S16_NOT_OUTCOME")
    )
    captured = []
    with pytest.raises(NaturalMotionRejected, match="S16_NOT_OUTCOME"):
        asyncio.run(loop.step(
            lambda kind, line, native=None: captured.append((kind, native))
        ))
    failure = report["life_unresolved_actions"][0]
    assert failure["original_s16_receipt"] is None
    assert failure["original_s49_supervisor_state"] is None
    assert failure["original_move_fence_unresolved"] is False
    assert failure["interpretation"] == "UNRESOLVED_NOT_DISPATCH_OR_STOP_PROOF"
    assert captured[-1][0] == "LIFE_ACTION_UNRESOLVED"
    assert report["life_action_outcomes"] == []
    assert report["c1_intent_experiences"] == 0


def test_read_only_historical_fence_does_not_create_missing_lock(tmp_path):
    fence = unresolved_fence(tmp_path)
    lock = fence.path.with_name(fence.path.name + ".lock")
    lock.unlink()  # simulate an old immutable archive missing the lock
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = inspect_r7_source_only(tmp_path)
    after = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert result["original_motion_fence_unresolved"] is True
    assert before == after
    assert not lock.exists()


def test_foreign_s50_client_cannot_claim_native_clear(tmp_path):
    unresolved_fence(tmp_path)
    make_s50(tmp_path)
    file = tmp_path / "r7-s50-client-readback.jsonl"
    file.write_text(file.read_text().replace("native-session", "foreign-session"))
    result = inspect_r7_source_only(tmp_path)
    assert result["s50_same_client_scope"] == "FOREIGN_ORIGINAL_S49_SESSION"
    assert result["actions"][0]["s50_same_client_clear_ack_seen"] is False


def test_cross_source_clear_seq_must_match(tmp_path):
    unresolved_fence(tmp_path)
    make_w3(tmp_path)
    make_s50(tmp_path)
    file = tmp_path / "r7-s50-client-readback.jsonl"
    file.write_text(file.read_text().replace('"native_seq": 2', '"native_seq": 99'))
    result = inspect_r7_source_only(tmp_path)
    assert result["actions"][0]["stdout_s50_clear_seq_match"] is False
    assert result["paper_tick_aligned_stop_attested"] is False
