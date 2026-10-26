"""Original S49 Action-level existing B0 M0 transaction and replay boundary."""
from dataclasses import replace

import pytest

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger, B0EnergyRejected
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.self_action_evidence import capture_native_action_evidence
from test_s49_m0_dash_extra_owner_dev import source


def second_action(original):
    receipt, _, _ = original
    previous = receipt.consequence
    new_id = receipt.terminal.action_id + "-second"
    consequence = replace(
        previous, action_id=new_id,
        dispatch_receipt=replace(previous.dispatch_receipt, action_id=new_id),
        cleanup_receipt=replace(
            previous.cleanup_receipt, action_id=new_id + "-s15-clear",
        ),
    )
    terminal = replace(receipt.terminal, action_id=new_id)
    new_receipt = NormalActionReceipt(terminal, consequence, receipt.source)
    proof = capture_native_action_evidence(
        consequence, allow_dev_forward=True, allow_dev_sprint=True,
    )
    return new_receipt, proof


def test_original_m0_two_native_actions_bill_base_move_once_each():
    original = source()
    receipt, invoice, proof = original
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    first = ledger.post_s49_move_step_dev(receipt, invoice, native_evidence=proof)
    assert first.m0_tick_before == 0 and first.m0_tick_after == 1
    assert first.basal_debit == .5 and first.move_debit == .25
    assert first.paper_world_ticks_for_dash == 13
    assert first.dash_extra_debit == pytest.approx(invoice.charge)
    assert first.energy_after == pytest.approx(12 - .75 - invoice.charge)
    with pytest.raises(B0EnergyRejected):
        ledger.post_s49_move_step_dev(receipt, invoice, native_evidence=proof)
    next_receipt, next_proof = second_action(original)
    later = ledger.post_s49_move_step_dev(
        next_receipt, None, native_evidence=next_proof,
    )
    assert later.paper_world_ticks_for_dash == 0
    assert later.dash_extra_debit == 0
    assert later.energy_after == pytest.approx(12 - 1.5 - invoice.charge)
    assert later.m0_tick_before == 1 and later.m0_tick_after == 2
    assert ledger.body.meals == ledger.credit_count == 0
    with pytest.raises(B0EnergyRejected):
        ledger.post_s49_move_step_dev(
            next_receipt, None, native_evidence=next_proof,
        )
    assert ledger.body.tick == 2


@pytest.mark.parametrize("changed", [
    {"session_id": "foreign"}, {"action_id": "forged"}, {"charge": 0},
    {"charge": float("nan")}, {"charge": 1.0},
    {"observed_world_ticks": 0}, {"boost_ticks": 14},
    {"last_world_tick": 257}, {"source_scope": "R_QUALIFIED_FAKE"},
])
def test_unverified_first_paper_invoice_never_charges(changed):
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    with pytest.raises(B0EnergyRejected):
        ledger.post_s49_move_step_dev(
            receipt, replace(invoice, **changed), native_evidence=evidence,
        )
    assert ledger.body.energy == 12 and ledger.body.tick == 0


def test_no_explicit_gate_or_unboosted_first_action_fails():
    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id)
    with pytest.raises(B0EnergyRejected):
        ledger.post_s49_move_step_dev(receipt, invoice, native_evidence=evidence)
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    with pytest.raises(B0EnergyRejected):
        ledger.post_s49_move_step_dev(receipt, None, native_evidence=evidence)
    assert ledger.body.tick == 0


def test_bad_native_cleanup_and_insufficient_balance_are_atomic():
    from experiments.metabolism_viability import MetabolismConfig

    receipt, invoice, evidence = source()
    ledger = B0EnergyLedger(invoice.session_id, dev_dash_extra_debit=True)
    bad = dict(evidence)
    bad["action_ref"] = "MOVE_BACKWARD"
    with pytest.raises(Exception):
        ledger.post_s49_move_step_dev(receipt, invoice, native_evidence=bad)
    assert ledger.body.energy == 12 and ledger.body.tick == 0
    poor = B0EnergyLedger(
        invoice.session_id, dev_dash_extra_debit=True,
        config=MetabolismConfig(initial_energy=0.76),
    )
    with pytest.raises(B0EnergyRejected):
        poor.post_s49_move_step_dev(receipt, invoice, native_evidence=evidence)
    assert poor.body.energy == .76 and poor.body.tick == 0
