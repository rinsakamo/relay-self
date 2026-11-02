"""S1 uses original typed owners, but all positive data is SYNTHETIC.

The pinned M and WB modules are real code at immutable source commits.
No actual Java, Node, Minecraft, provider or S49 Action is invoked in CI.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace

import pytest

from adapters.mineflayer.s49_completed_decision_bridge import (
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)
from adapters.mineflayer.s537_s1_original_wb_m import S1WBMMatchedObserver
from test_s49_completed_decision_bridge import _synthetic_original_shape
from test_s49_owner_cognition_crosslane import _load_pinned
from tools.s537_s1_live_wb_m_dev import main, run_s1_owner_dev


@pytest.fixture
def pinned_owners(monkeypatch):
    m = _load_pinned(
        monkeypatch, "experiments.metabolism_s49_owner_admission",
        "S0_PINNED_M_SOURCE",
    )
    wb = _load_pinned(
        monkeypatch, "relay_self.self_cognition_slice", "S0_PINNED_WB_SOURCE",
    )
    return m, wb


def _two_original_shape():
    steps, probes, receipts = _synthetic_original_shape()
    sid = steps[0].choice.session_id
    original_move = steps[0]
    action_id = f"s49-native-move-{original_move.event_seq}"
    converted = []
    fixed_probes = {}
    for step in steps:
        request_id = f"s49-actual:{sid}:event-{step.event_seq}"
        updated_choice = replace(step.choice, request_id=request_id)
        updated_probe = replace(
            probes[step.choice.probe_seq], request_id=request_id,
        )
        fixed_probes[updated_probe.seq] = updated_probe
        if step.asks_for_action:
            converted.append(replace(
                step, choice=updated_choice, action_request_id=action_id,
                grant=replace(step.grant, action_id=action_id),
            ))
        else:
            converted.append(replace(step, choice=updated_choice))
    original_receipt = receipts[original_move.action_request_id]
    receipt = replace(
        original_receipt,
        terminal=replace(original_receipt.terminal, action_id=action_id),
        consequence=replace(original_receipt.consequence, action_id=action_id),
    )
    return read_original_s49_completions(
        tuple(converted), fixed_probes, {action_id: receipt},
    )


def test_live_probe_plus_postowner_callback_same_original_source(pinned_owners):
    batch = _two_original_shape()
    tap = S1WBMMatchedObserver(enabled=True)
    for source in batch.steps:
        tap.observe(source.probe)
    tap.completed(batch)
    assert tap.errors == []
    assert tap.completed_callbacks == 1
    assert tap.readout is not None
    row = tap.readout
    assert row["status"] == "RECORDED"
    assert row["m_status"] == "RECORDED"
    assert row["wb_status"] == "L1_SOURCE_BOUND_PRESENT_READ_ONLY"
    assert row["s49"]["m_status"] == "ORIGINAL_PYTHON_BATCH_RECORDED"
    assert row["s49"]["wb_status"] == "NOT_SUPPLIED"
    assert len(row["wb_rows"]) == len(batch.steps)
    assert row["wb_rows"][0]["world_source_ref"].startswith("present:")
    assert row["wb_rows"][0]["body_source_ref"].startswith("native-probe:")
    assert row["s16_to_next_epoch"][0]["action_id"] == (
        batch.steps[0].action_receipt.terminal.action_id
    )
    assert row["new_native_reads"] == row["new_action_issues"] == 0
    assert row["energy_debits"] == row["learning_updates"] == 0
    assert "MineflayerObservation" not in repr(row)


@pytest.mark.parametrize("fault", [
    "foreign_probe", "missing_probe", "wrong_s16", "duplicate_callback",
    "callback_error",
])
def test_original_owner_mismatch_fails_without_new_actions(pinned_owners, fault):
    batch = _two_original_shape()
    tap = S1WBMMatchedObserver(enabled=True)
    if fault == "missing_probe":
        tap.observe(batch.steps[0].probe)
    elif fault == "foreign_probe":
        for source in batch.steps:
            tap.observe(source.probe)
        batch = replace(batch, session_id="foreign")
    elif fault == "wrong_s16":
        for source in batch.steps:
            tap.observe(source.probe)
        batch = replace(batch, steps=(
            replace(batch.steps[0], action_receipt=None), batch.steps[1],
        ))
    else:
        for source in batch.steps:
            tap.observe(source.probe)
        if fault == "callback_error":
            tap.record_error(ValueError("synthetic observer failure"))
    tap.completed(batch)
    if fault == "duplicate_callback":
        tap.completed(batch)
        assert tap.completed_callbacks == 2
    assert tap.readout is not None
    assert tap.readout["status"] == "DEFERRED"


def test_original_one_call_run_report_is_source_joined(pinned_owners, tmp_path):
    batch = _two_original_shape()
    root = tmp_path
    report = root / "original-s49.json"
    server_log = root / "unstarted-server.log"
    calls = []

    async def fake_qualify(path, log, *, live_probe, completed_l0, completed_l0_dev):
        calls.append((path, log))
        assert completed_l0_dev is True
        for source in batch.steps:
            await live_probe(source.probe)
        completed_l0(batch)
        original_row = bounded_original_s49_completion_row(batch)
        path.write_text(json.dumps({
            "status": "PASS",
            "session_id": batch.session_id,
            "original_completion_observer": "CALLBACK_RETURNED",
            "original_completion_readback": original_row,
            "source_pair_trace": [
                {"event_seq": d["event_seq"], "probe_seq": d["probe_seq"]}
                for d in original_row["decisions"]
            ],
        }))
        return 0

    obs = S1WBMMatchedObserver(enabled=True)
    code, result = asyncio.run(run_s1_owner_dev(
        original_qualify=fake_qualify,
        report_path=report,
        server_log=server_log,
        observer=obs,
    ))
    assert len(calls) == 1
    assert code == 0 and result["status"] == "RECORDED"
    assert result["typed_join"]["m_status"] == "RECORDED"
    assert result["new_action_issues"] == result["new_native_reads"] == 0
    assert result["qualification"] == "NO_GO"
    assert result["science"] == "NOT_RUN"


def test_no_dev_flag_blocks_before_world(monkeypatch, capsys):
    monkeypatch.delenv("S537_S1_LIVE_DEV_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "s537_s1_live_wb_m_dev", "--m-owner-dir", "/nonexistent/m",
        "--wb-owner-dir", "/nonexistent/wb", "--report", "/tmp/no-s49-report",
        "--server-log", "/tmp/no-s49-server",
        "--s1-report", "/tmp/no-s1-report",
    ])
    assert main() == 2
    assert '"BLOCKED"' in capsys.readouterr().out
