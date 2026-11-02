"""Pinned, original M #676 and WB #669 types (offline synthetic sources).

CI checks out immutable independent owner revisions; this test never
reinterprets a fabricated M/S42/B0/L8 receipt or reads a real World.
"""
import importlib.util
import os
import sys
from dataclasses import replace
from pathlib import Path

import experiments
import relay_self
from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from adapters.mineflayer.s49_owner_cognition_join import (
    join_completed_s49_cognition,
)
from test_s49_completed_decision_bridge import _synthetic_original_shape


def _load_pinned(monkeypatch, module_name: str, env: str):
    filename = Path(os.environ[env])
    assert filename.is_file(), "pinned owner path not available"
    spec = importlib.util.spec_from_file_location(module_name, filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_original_m_wb_types_join_only_same_s49_source(monkeypatch):
    assert experiments is not None and relay_self is not None
    m = _load_pinned(
        monkeypatch, "experiments.metabolism_s49_owner_admission",
        "S0_PINNED_M_SOURCE",
    )
    wb = _load_pinned(
        monkeypatch, "relay_self.wb_l2_read_port", "S0_PINNED_WB_SOURCE",
    )
    steps, probes, receipts = _synthetic_original_shape()
    # The old S49 test deliberately uses test-* IDs. M correctly rejects
    # them. Construct an explicitly SYNTHETIC but source-format-valid S49
    # owner shape here; do not loosen M's production ID contract.
    sid = steps[0].choice.session_id
    original_move = steps[0]
    action_id = f"s49-native-move-{original_move.event_seq}"
    converted = []
    fixed_probes = {}
    for step in steps:
        request_id = f"s49-actual:{sid}:event-{step.event_seq}"
        new_choice = replace(step.choice, request_id=request_id)
        new_probe = replace(
            probes[step.choice.probe_seq], request_id=request_id,
        )
        fixed_probes[new_probe.seq] = new_probe
        if step.asks_for_action:
            converted.append(replace(
                step, choice=new_choice, action_request_id=action_id,
                grant=replace(step.grant, action_id=action_id),
            ))
        else:
            converted.append(replace(step, choice=new_choice))
    original_receipt = receipts[original_move.action_request_id]
    fixed_receipt = replace(
        original_receipt,
        terminal=replace(original_receipt.terminal, action_id=action_id),
        consequence=replace(original_receipt.consequence, action_id=action_id),
    )
    batch = read_original_s49_completions(
        tuple(converted), fixed_probes, {action_id: fixed_receipt},
    )
    accepted = m.S49MAdmissionLease(enabled=True).admit_batch(batch)
    assert accepted.status == "RECORDED"
    first, last = batch.steps[0].probe.seq, batch.steps[-1].probe.seq
    assert last > first
    past = wb.WBL2UncertaintyRead(
        state="PAST_EPOCH_REVIEW_ONLY",
        session_id=batch.session_id,
        source_world_seq=first,
        latest_world_seq=last,
        source_ref=f"present:{batch.session_id}:{first}:synthetic-fixture",
        current_uncertainty=None,
        past_review_candidate="Only a synthetic L2 question",
    )
    joined = join_completed_s49_cognition(
        enabled=True, batch=batch, m_admission=accepted, wb_read=past,
    )
    assert joined.status == "RECORDED"
    assert joined.m_status == "ORIGINAL_PYTHON_BATCH_RECORDED"
    assert joined.wb_status == "PAST_EPOCH_REVIEW_ONLY"
    assert joined.wb_source_probe_seq == first
    assert joined.model_usage == "UNKNOWN_NOT_METERED"
    assert joined.source_attested is False
    assert joined.new_action_issues == 0

    # Same module types, but WRONG source/session or falsely current: fail.
    for wrong in (
        replace(past, session_id="foreign"),
        replace(past, state="CURRENT_EPOCH_READ_ONLY",
                current_uncertainty="stale", past_review_candidate=None),
        replace(past, latest_world_seq=last + 100),
    ):
        rejected = join_completed_s49_cognition(
            enabled=True, batch=batch, m_admission=accepted, wb_read=wrong,
        )
        assert rejected.status == "DEFERRED"
        assert rejected.decisions == ()

    # Saved JSON is not equivalent to a same-process original batch.
    fake = replace(accepted, admission=replace(
        accepted.admission, kind="SAVED_REPORT_JSON",
    ))
    rejected = join_completed_s49_cognition(
        enabled=True, batch=batch, m_admission=fake, wb_read=past,
    )
    assert rejected.status == "DEFERRED"

    replay = m.S49MAdmissionLease(enabled=True)
    assert replay.admit_batch(batch).status == "RECORDED"
    assert replay.admit_batch(batch).status == "DEFERRED"
