"""Small DEV checks: no second native receiver, no World in negatives."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_motor_clock_review_dev import review_native_motor_clock_dev
from adapters.mineflayer.s49_native_motor_clock_dev import (
    BRIDGE_SOURCE,
    instrument_native_bridge_dev,
    remove_native_bridge_dev,
)
from adapters.mineflayer.s49_paper_world_first_dev import CONFIRM, run


def test_generated_sibling_bridge_keeps_original_bytes_and_scope(tmp_path, monkeypatch):
    old = BRIDGE_SOURCE.read_bytes()
    monkeypatch.setattr(
        "adapters.mineflayer.s49_native_motor_clock_dev.BRIDGE_SOURCE",
        tmp_path / "bridge.mjs",
    )
    (tmp_path / "bridge.mjs").write_bytes(old)
    log = tmp_path / "native.jsonl"
    dev = instrument_native_bridge_dev(log)
    try:
        src = dev.read_text()
        assert "motionClockDevRow('back_on'" in src
        assert "motionClockDevRow('back_off'" in src
        assert "motionClockDevRow('physics_tick'" in src
        assert "process.stdout.write(JSON.stringify(message) + '\\n')" in src
        assert "bot.setControlState(command.control, command.state)" in src
        assert "bot.clearControlStates()" in src
        assert dev.parent == tmp_path
        assert not log.exists()
        assert (tmp_path / "bridge.mjs").read_bytes() == old
    finally:
        remove_native_bridge_dev(dev)
    assert not dev.exists()


def _trial_data(tmp_path: Path):
    sid = "test-session"
    actions = [{"action": f"s49-native-move-{n}", "terminal": "outcome",
                "movement_m": 0.626} for n in (3, 8, 12, 20)]
    lines = []
    count = 0
    for i, action in enumerate(actions):
        aid = action["action"]
        for kind, add_ms, ticks in (
            ("back_on", 0, 0),
            ("physics_tick", 50, 1),
            ("physics_tick", 100, 2),
            ("back_off", 200, 3),
        ):
            lines.append({
                "schema": "DEV_MOTOR_CLOCK_V0", "kind": kind,
                "action_id": aid, "index": count,
                "node_monotonic_ns": str(10**12 + i * 500_000_000 + add_ms * 1_000_000),
                "mineflayer_physics_tick_counter": i * 8 + ticks,
                "mineflayer_position_xz": {"x": 0.0, "z": 0.0},
                "paper_world_tick_attested": False,
                "new_action_issuer": False,
            })
            count += 1
    node = tmp_path / "node.jsonl"
    node.write_text("\n".join(json.dumps(r) for r in lines) + "\n")
    paper = tmp_path / "paper.log"
    paper.write_text("\n".join(
        f"[RelayS49WaitObserverDev] S49_DEV_BACK_WAIT_TICK "
        f"marker_id=irrelevant action_id={actions[1]['action']} "
        f"session_id={sid} world=world run_id=run tick={n+450} "
        f"index={n} input_idle=true"
        for n in range(1, 9)
    ))
    source = {
        "status": "PASS", "node_exit": 0, "server_exit": 0,
        "session_id": sid, "actual_native_actions": actions,
    }
    feedback = {"status": "DEV_REAL_S49_SELF_BODY_MOTION_CLOSED_LOOP"}
    return node, paper, source, feedback, lines


def test_three_clock_review_separates_node_client_ticks_and_paper_wait(tmp_path):
    node, paper, source, feedback, _ = _trial_data(tmp_path)
    result = review_native_motor_clock_dev(node, paper, source, feedback)
    assert result["status"] == "DEV_S49_THREE_CLOCKS_OBSERVED"
    assert result["source_action_count"] == 4
    assert all(row["node_control_active_monotonic_ms"] == 200
               for row in result["node_actions"])
    assert all(row["node_physics_tick_callbacks_while_back_active"] == 2
               for row in result["node_actions"])
    assert result["paper_wait_tick_samples"] == 8
    assert result["paper_after_second_action_wait_tick_first"] == 451
    assert result["cross_domain_clock_alignment_attested"] is False
    assert result["paper_effective_move_tick_count_attested"] is False
    assert result["qualification_go"] is False


@pytest.mark.parametrize("fault", [
    "foreign", "stale", "fake_server_tick", "extra_issuer", "wrong_count",
    "duplicate_off", "foreign_paper", "paper_gap", "missing_file",
])
def test_reject_tampered_motion_clock_readback(tmp_path, fault):
    node, paper, source, feedback, rows = _trial_data(tmp_path)
    if fault == "foreign":
        rows[0]["action_id"] = "foreign"
    elif fault == "stale":
        rows[2]["node_monotonic_ns"] = rows[1]["node_monotonic_ns"]
    elif fault == "fake_server_tick":
        rows[2]["paper_world_tick_attested"] = True
    elif fault == "extra_issuer":
        rows[2]["new_action_issuer"] = True
    elif fault == "wrong_count":
        del rows[2]
    elif fault == "duplicate_off":
        rows[2]["kind"] = "back_off"
    elif fault == "foreign_paper":
        paper.write_text(paper.read_text().replace("session_id=test-session", "session_id=other"))
    elif fault == "paper_gap":
        paper.write_text(paper.read_text().replace("tick=454", "tick=459"))
    elif fault == "missing_file":
        node.unlink()
    if fault in ("foreign", "stale", "fake_server_tick", "extra_issuer",
                 "wrong_count", "duplicate_off"):
        for i, row in enumerate(rows):
            row["index"] = i
        node.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    with pytest.raises((BoundaryRejected, KeyError, TypeError, ValueError)):
        review_native_motor_clock_dev(node, paper, source, feedback)


def test_timing_optin_requires_existing_original_selfbody(tmp_path):
    p, o = tmp_path / "paper.jar", tmp_path / "observer.jar"
    p.write_bytes(b"fixture")
    o.write_bytes(b"fixture")
    out = tmp_path / "not-created"
    rc = asyncio.run(run(
        out, p, hashlib.sha256(p.read_bytes()).hexdigest(),
        o, hashlib.sha256(o.read_bytes()).hexdigest(),
        confirmation=CONFIRM, motor_clock_dev=True,
    ))
    assert rc == 2
    assert not out.exists()
