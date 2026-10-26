"""Original S49 single existing B0 owner: exact-once DASH extra debit DEV."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.b0_energy_bridge import (
    B0EnergyLedger,
    B0EnergyRejected,
    DashM0InvoiceDev,
)
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from relay_self.provenance import Provenance


def source():
    chain = s17.executed_closed_chain()
    original_consequence = chain[-3]
    consequence = replace(
        original_consequence,
        action_ref="MOVE_FORWARD_SPRINT_DEV",
        dispatch_receipt=replace(
            original_consequence.dispatch_receipt, effect="set_forward_sprint_dev",
        ),
    )
    receipt = NormalActionReceipt(
        chain[-1], consequence, Provenance("dev-synthetic-test", "closed"),
    )
    native_evidence = capture_native_action_evidence(
        consequence, allow_dev_forward=True, allow_dev_sprint=True,
    )
    invoice = DashM0InvoiceDev(
        session_id=consequence.session_id,
        action_id=receipt.terminal.action_id,
        first_world_tick=244, last_world_tick=256,
        observed_world_ticks=13, boost_ticks=10, charge=0.0786981057,
    )
    return receipt, invoice, native_evidence


def test_existing_b0_owner_debits_single_real_issued_action_only_once():
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(receipt.consequence.session_id, dev_dash_extra_debit=True)
    posted = ledger.post_dash_extra_dev(receipt, invoice, native_evidence=evidence)
    assert posted.posted_extra == pytest.approx(0.0786981057)
    assert posted.energy_before == pytest.approx(12.0)
    assert posted.energy_after == pytest.approx(11.9213018943)
    assert posted.m0_tick_before == 0 and posted.m0_tick_after == 1
    assert ledger.body.energy == posted.energy_after
    assert ledger.body.meals == ledger.credit_count == 0
    with pytest.raises(B0EnergyRejected):
        ledger.post_dash_extra_dev(receipt, invoice, native_evidence=evidence)
    assert ledger.body.tick == 1
    assert ledger.body.energy == posted.energy_after


@pytest.mark.parametrize("alter", [
    {"session_id": "foreign"},
    {"action_id": "other"},
    {"first_world_tick": -1},
    {"last_world_tick": 257},
    {"observed_world_ticks": 0},
    {"observed_world_ticks": 80},
    {"boost_ticks": 14},
    {"boost_ticks": 0},
    {"charge": 0.0},
    {"charge": -0.2},
    {"charge": 0.2},
    {"charge": float("nan")},
    {"charge": float("inf")},
    {"charge": True},
    {"source_scope": "INDEPENDENT_ATTESTED_FAKE"},
])
def test_invalid_invoice_never_mutates_existing_m0_balance(alter):
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    with pytest.raises(B0EnergyRejected):
        ledger.post_dash_extra_dev(
            receipt, replace(invoice, **alter), native_evidence=evidence,
        )
    assert ledger.body.energy == 12
    assert ledger.body.tick == ledger.credit_count == ledger.body.meals == 0


def test_default_b0_owner_denies_dash_and_legacy_step_unchanged():
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id)
    with pytest.raises(B0EnergyRejected):
        ledger.post_dash_extra_dev(receipt, invoice, native_evidence=evidence)
    assert ledger.step("MOVE").expenditure == 0.75
    assert ledger.body.energy == 11.25


def test_undetermined_native_or_changed_s16_receipt_rejected():
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    invalid = dict(evidence)
    invalid["action_ref"] = "MOVE_BACKWARD"
    with pytest.raises(Exception):
        ledger.post_dash_extra_dev(receipt, invoice, native_evidence=invalid)
    assert ledger.body.energy == 12 and ledger.body.tick == 0


def test_original_s49_dash_debit_gate_denies_before_world(monkeypatch, tmp_path):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_FORWARD_MOTOR_DEV_ONLY", "1")
    monkeypatch.setenv("S49_SPRINT_MOTOR_DEV_ONLY", "1")
    monkeypatch.delenv("S49_M0_DASH_DEBIT_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(original, "_fetch_official_server", lambda *a, **kw: (
        pytest.fail("unadmitted M0 debit opened Minecraft World")
    ))
    rc = asyncio.run(original.qualify(
        tmp_path / "blocked.json", tmp_path / "paper.log",
        dev_forward_motor=True, dev_sprint_motor=True,
        dev_m0_dash_invoice=lambda receipt: None,
    ))
    assert rc == 2
