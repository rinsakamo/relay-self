"""S2-B owner witness offline tests. All positive sources are SYNTHETIC.

Tests actual original S49 NormalWorldL0/IntentCommitment classes and pinned
WB/M original modules; it does NOT attest a real server World or Gemma.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.normal_action import NormalWorldL0
from adapters.mineflayer.s49_completed_decision_bridge import (
    bounded_original_s49_completion_row,
)
from adapters.mineflayer.s537_s2b_gated_l2_shadow import S2BSourceRejected
from adapters.mineflayer.s537_s2b_original_owner_epoch import (
    S2BOriginalOwnerEpochBinder,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_s49_owner_cognition_crosslane import _load_pinned
from test_s537_s2a_source_bound_read_port import (
    _closure,
    _realistic_synthetic_batch,
)
from tools.s537_s2b_original_owner_witness_dev import (
    S2BOwnerWitnessObserver,
    main,
    run_s2b_owner_witness_dev,
)



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


def _owners(batch):
    retained, *_ = s42._pair()
    host = NormalWorldL0(
        batch.session_id, "escape-threat", retained,
        max_events=3, max_action_requests=2,
    )
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape near zombie", at_ns=1,
        provenance=Provenance("synthetic", "original-owner-intent"),
    )
    return host, intent


def test_original_owner_and_next_epoch_s16_witness(pinned_owners):
    batch = _realistic_synthetic_batch()
    host, intent = _owners(batch)
    probe1, probe2 = (entry.probe for entry in batch.steps)
    observer = S2BOwnerWitnessObserver()
    observer.owner_epoch(probe1, host, intent)
    observer.observe(probe1)
    assert observer.bound[0].source_input.preceding_action_id is None
    observer.observe_closed(_closure(batch))
    observer.owner_epoch(probe2, host, intent)
    observer.observe(probe2)
    observer.completed(batch)
    report = observer.owner_epoch_readout()
    assert report["status"] == "RECORDED"
    assert [r["intent_generation"] for r in report["epoch_contexts"]] == [1, 1]
    assert [r["retained_revision"] for r in report["epoch_contexts"]] == [
        host.retained.revision, host.retained.revision,
    ]
    assert report["epoch_contexts"][1]["preceding_action_id"] == (
        batch.steps[0].step.action_request_id
    )
    assert report["model_calls"] == report["s60_submissions"] == 0
    assert report["original_owner"]["status"] == "RECORDED"


@pytest.mark.parametrize("fault", [
    "missing", "foreign", "stale_probe", "foreign_host",
    "foreign_intent", "retained_changed", "intent_changed",
    "future_probe_copy",
])
def test_original_owner_witness_fails_closed_on_source_mismatch(
    pinned_owners, fault,
):
    batch = _realistic_synthetic_batch()
    host, intent = _owners(batch)
    probe = batch.steps[0].probe
    binder = S2BOriginalOwnerEpochBinder()
    if fault == "missing":
        with pytest.raises(S2BSourceRejected):
            binder.bind(None, probe)
        return
    if fault == "foreign":
        binder.note_original_epoch(
            replace(probe, session_id="foreign"), host, intent,
        )
        assert binder.bounded_row()["status"] == "DEFERRED"
        return
    if fault == "stale_probe":
        binder.note_original_epoch(probe, host, intent)
        binder.note_original_epoch(probe, host, intent)
        assert binder.bounded_row()["status"] == "DEFERRED"
        return
    if fault == "foreign_host":
        other = NormalWorldL0(
            batch.session_id, "escape-threat", host.retained,
        )
        binder.note_original_epoch(probe, host, intent)
        binder.note_original_epoch(batch.steps[1].probe, other, intent)
        assert binder.bounded_row()["status"] == "DEFERRED"
        return
    if fault == "foreign_intent":
        _, other_intent = _owners(batch)
        binder.note_original_epoch(probe, host, intent)
        binder.note_original_epoch(
            batch.steps[1].probe, host, other_intent,
        )
        assert binder.bounded_row()["status"] == "DEFERRED"
        return
    binder.note_original_epoch(probe, host, intent)
    observer.owner_epoch(probe, host, intent)
    observer.observe(probe)
    source = observer._inputs[-1]
    if fault == "retained_changed":
        host.retained = replace(host.retained, revision=host.retained.revision + 1)
    elif fault == "intent_changed":
        intent.request_reconsideration(
            "escape-threat", reason="probe changed", at_ns=2,
            provenance=Provenance("synthetic", "reconsider"),
        )
    elif fault == "future_probe_copy":
        probe = replace(probe)
    with pytest.raises(S2BSourceRejected):
        binder.bind(source, probe)


def test_single_original_qualify_runner_makes_no_model_calls(
    pinned_owners, tmp_path,
):
    batch = _realistic_synthetic_batch()
    host, intent = _owners(batch)
    called = []
    report = tmp_path / "s49.json"

    async def fake_qualify(
        path, log, *, live_probe, owner_epoch_readonly,
        completed_l0, completed_l0_dev,
    ):
        called.append("original_s49_once")
        assert completed_l0_dev is True
        first, second = (step.probe for step in batch.steps)
        owner_epoch_readonly(first, host, intent)
        await live_probe(first)
        from adapters.mineflayer.normal_action import _READ_ONLY_CLOSURE
        callback = _READ_ONLY_CLOSURE.get()
        assert callback is not None
        callback(_closure(batch))
        owner_epoch_readonly(second, host, intent)
        await live_probe(second)
        completed_l0(batch)
        row = bounded_original_s49_completion_row(batch)
        path.write_text(json.dumps({
            "status": "PASS", "session_id": batch.session_id,
            "original_completion_observer": "CALLBACK_RETURNED",
            "original_completion_readback": row,
            "source_pair_trace": [
                {"event_seq": d["event_seq"], "probe_seq": d["probe_seq"]}
                for d in row["decisions"]
            ],
        }))
        return 0

    rc, result = asyncio.run(run_s2b_owner_witness_dev(
        original_qualify=fake_qualify,
        report_path=report, server_log=tmp_path / "server.log",
        observer=S2BOwnerWitnessObserver(),
    ))
    assert rc == 0
    assert result["status"] == "RECORDED"
    assert result["owner_epoch"]["status"] == "RECORDED"
    assert result["owner_epoch"]["model_calls"] == 0
    assert result["owner_epoch"]["s60_submissions"] == 0
    assert called == ["original_s49_once"]


def test_owner_witness_is_default_off(monkeypatch, capsys):
    monkeypatch.delenv("S537_S2B_OWNER_WITNESS_DEV_ONLY", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "s537_s2b_original_owner_witness_dev",
        "--m-owner-dir", "/tmp/no-owner",
        "--wb-owner-dir", "/tmp/no-wb",
        "--report", "/tmp/no-report",
        "--server-log", "/tmp/no-log",
        "--s2b-report", "/tmp/no-s2b",
    ])
    assert main() == 2
    assert '"BLOCKED"' in capsys.readouterr().out
