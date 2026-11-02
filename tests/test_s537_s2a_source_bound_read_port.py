"""S2-A host-order regression: all positive World evidence is SYNTHETIC.

Runs pinned M #676 and WB #669 implementation in the same Python process,
without launching Minecraft, a provider or the actual Action executor.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace

import pytest

from adapters.mineflayer.normal_action import (
    _READ_ONLY_CLOSURE,
    NormalActionClosedReadback,
)
from adapters.mineflayer.s49_completed_decision_bridge import (
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)
from adapters.mineflayer.s537_s2a_l2_read_port import S2ASourceBoundObserver
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.provenance import Provenance
from test_s49_owner_cognition_crosslane import _load_pinned
from test_s537_s1_live_wb_m_dev import _two_original_shape
from tools.s537_s2a_original_readonly_dev import main, run_s2a_original_dev


@pytest.fixture
def pinned_owners(monkeypatch):
    m = _load_pinned(
        monkeypatch, "experiments.metabolism_s49_owner_admission",
        "S0_PINNED_M_SOURCE",
    )
    wb = _load_pinned(
        monkeypatch, "relay_self.self_cognition_slice", "S1_PINNED_WB_SOURCE",
    )
    return m, wb


def _realistic_synthetic_batch():
    batch = _two_original_shape()
    first = batch.steps[0]
    receipt = first.action_receipt
    assert receipt is not None
    original = first.probe
    updated_consequence = replace(
        receipt.consequence,
        before_observation=replace(original, seq=original.seq + 1),
    )
    revised = replace(
        batch.steps[0], action_receipt=replace(
            receipt, consequence=updated_consequence,
        ),
    )
    return read_original_s49_completions(
        tuple([revised.step, *(entry.step for entry in batch.steps[1:])]),
        {item.probe.seq: item.probe for item in batch.steps},
        {revised.step.action_request_id: revised.action_receipt},
    )


def _closure(batch):
    src = batch.steps[0]
    receipt = src.action_receipt
    assert receipt is not None
    con = receipt.consequence
    return NormalActionClosedReadback(
        terminal=receipt.terminal,
        interpretation=ActionOutcomeInterpretation(
            action_id=receipt.terminal.action_id,
            binding_id=con.binding_id,
            action_ref=con.action_ref,
            skill_execution_id=receipt.terminal.skill_execution_id,
            intent_id=receipt.terminal.intent_id,
            session_id=batch.session_id,
            source_status=con.status.value,
            disposition=ActionOutcomeDisposition.OUTCOME,
            reason_code="observed_execution",
            world_provenance=con.provenance,
            provenance=Provenance("test", "typed-synthetic-S16"),
        ),
        consequence=con,
        original_probe=src.probe,
    )


def test_original_owner_action_closes_before_future_l2_input(pinned_owners):
    batch = _realistic_synthetic_batch()
    observer = S2ASourceBoundObserver(enabled=True)
    observer.observe(batch.steps[0].probe)
    assert observer._inputs[0].preceding_action_id is None
    observer.observe_closed(_closure(batch))
    observer.observe(batch.steps[1].probe)
    observer.completed(batch)
    row = observer.s2a_readout()
    assert row["status"] == "RECORDED"
    assert row["input_count"] == 2
    assert row["closed_s16_count"] == 1
    assert row["with_previous_s16"] == 1
    first, second = row["inputs"]
    assert first["preceding_action_id"] is None
    assert second["preceding_action_id"] == batch.steps[0].step.action_request_id
    assert second["preceding_s16_after_seq"] < second["probe_seq"]
    assert first["world_source_ref"].startswith("present:")
    assert second["observed_body"]
    assert row["s60_submissions"] == row["new_model_calls"] == 0
    assert row["source_attested"] is row["action_authority"] is False


@pytest.mark.parametrize("attack", [
    "wrong_session", "wrong_action", "future_after",
    "duplicate_closure", "stale_wrong_order",
])
def test_invalid_or_out_of_order_closure_never_becomes_l2_input(
    pinned_owners, attack,
):
    batch = _realistic_synthetic_batch()
    observer = S2ASourceBoundObserver(enabled=True)
    observer.observe(batch.steps[0].probe)
    closed = _closure(batch)
    if attack == "wrong_session":
        closed = replace(
            closed, interpretation=replace(closed.interpretation, session_id="foreign"),
        )
    elif attack == "wrong_action":
        closed = replace(
            closed, interpretation=replace(closed.interpretation, action_id="foreign"),
        )
    elif attack == "future_after":
        closed = replace(
            closed, consequence=replace(
                closed.consequence,
                after_observation=replace(
                    closed.consequence.after_observation,
                    seq=batch.steps[1].probe.seq + 3,
                ),
            ),
        )
    elif attack == "stale_wrong_order":
        observer.observe(batch.steps[1].probe)
    observer.observe_closed(closed)
    if attack == "duplicate_closure":
        observer.observe_closed(closed)
    if attack != "stale_wrong_order":
        if attack == "future_after":
            with pytest.raises(ValueError, match="future"):
                observer.observe(batch.steps[1].probe)
            observer.record_error(ValueError("future blocked"))
        else:
            observer.observe(batch.steps[1].probe)
    observer.completed(batch)
    assert observer.s2a_readout()["status"] == "DEFERRED"


def test_s2a_passive_runner_invokes_original_s49_once(
    pinned_owners, tmp_path,
):
    batch = _realistic_synthetic_batch()
    calls = []
    report = tmp_path / "s49.json"

    async def fake_original(
        path, log, *, live_probe, completed_l0, completed_l0_dev,
    ):
        calls.append("one")
        assert completed_l0_dev is True
        await live_probe(batch.steps[0].probe)
        callback = _READ_ONLY_CLOSURE.get()
        assert callback is not None
        callback(_closure(batch))
        await live_probe(batch.steps[1].probe)
        completed_l0(batch)
        row = bounded_original_s49_completion_row(batch)
        path.write_text(json.dumps({
            "status": "PASS",
            "session_id": batch.session_id,
            "original_completion_observer": "CALLBACK_RETURNED",
            "original_completion_readback": row,
            "source_pair_trace": [
                {"event_seq": d["event_seq"], "probe_seq": d["probe_seq"]}
                for d in row["decisions"]
            ],
        }))
        return 0

    observer = S2ASourceBoundObserver(enabled=True)
    code, result = asyncio.run(run_s2a_original_dev(
        original_qualify=fake_original,
        report_path=report,
        server_log=tmp_path / "server.log",
        observer=observer,
    ))
    assert calls == ["one"]
    assert code == 0 and result["status"] == "RECORDED"
    assert result["s2a"]["with_previous_s16"] == 1
    assert result["model_calls"] == 0
    assert result["s60_submissions"] == 0
    assert _READ_ONLY_CLOSURE.get() is None


def test_s2a_requires_explicit_world_gate(monkeypatch, capsys):
    monkeypatch.delenv("S537_S2A_LIVE_DEV_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "s537_s2a_original_readonly_dev",
        "--m-owner-dir", "/tmp/not-m",
        "--wb-owner-dir", "/tmp/not-wb",
        "--report", "/tmp/not-report",
        "--server-log", "/tmp/not-log",
        "--s2a-report", "/tmp/not-s2a",
    ])
    assert main() == 2
    assert '"BLOCKED"' in capsys.readouterr().out
