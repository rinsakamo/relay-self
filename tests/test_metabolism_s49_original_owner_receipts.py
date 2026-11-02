"""M #616: exact typed original S49 S16 receipt source read-only tests.

Original S49 validators and M admission from the pinned S49 product checkout.
All fixtures are synthetic. No native World, model, body update or S42 owner.
"""
from __future__ import annotations

from dataclasses import replace

import pytest
from adapters.mineflayer.s49_completed_decision_bridge import (
    S49OriginalCompletedBatch,
)

import test_metabolism_s49_owner_admission as source
from experiments.metabolism_s49_original_owner_receipts import (
    S49MOwnerReceiptReadout,
    bounded_original_s49_owner_receipt_row,
    observe_original_s49_s16_receipts,
)
from experiments.metabolism_s49_owner_admission import S49MAdmissionLease
from tools.m616_s49_live_owner_dev import M616OriginalS49CompletedTap


def _accepted_batch():
    batch = source._owner_batch()
    admission = S49MAdmissionLease(enabled=True).admit_batch(batch)
    assert admission.status == "RECORDED"
    return batch, admission


def test_original_s16_receipts_preserve_is_identity_and_separate_native_before():
    batch, admission = _accepted_batch()
    receipt = observe_original_s49_s16_receipts(
        enabled=True, batch=batch, original_admission=admission,
    )
    assert receipt.status == "RECORDED"
    assert receipt.reason == "original_s49_s16_source_bound"
    assert receipt.session_id == batch.session_id
    assert receipt.wait_count == receipt.outcome_count == 1
    assert len(receipt.original_actions) == 1
    action = receipt.original_actions[0]
    src = batch.steps[0]
    assert action.original_step is src.step
    assert action.original_probe is src.probe
    assert action.original_s16 is src.action_receipt
    assert action.probe_seq < action.before_seq
    assert action.before_seq < action.dispatch_seq < action.clear_seq < action.after_seq
    assert action.movement_m == src.action_receipt.consequence.movement_distance
    row = bounded_original_s49_owner_receipt_row(receipt)
    assert row["actions"][0]["s15_clear_seq"] == action.clear_seq
    assert row["s42_owner_receipt"] == row["b0_owner_receipt"] == row["l8_owner_receipt"] == (
        "NOT_SUPPLIED_BY_ORIGINAL_S49_COMPLETION_CALLBACK"
    )
    assert row["provider_calls"] is None and row["metabolic_energy"] == "UNKNOWN_NO_B0_OWNER"
    assert row["source_attested"] is False and row["action_authority"] is False
    assert "snapshot" not in repr(row) and "inventory" not in repr(row)
    assert row["native_reads"] == row["model_calls"] == row["action_issues"] == 0


@pytest.mark.parametrize("attack", [
    "missing_original", "foreign_session", "wrong_action", "unknown_terminal",
    "source_before_probe", "wrong_clear_seq", "false_B0", "false_source",
])
def test_corrupted_s16_batch_or_admission_cannot_be_passively_bound(attack):
    batch, admission = _accepted_batch()
    if attack == "missing_original":
        batch = replace(batch, steps=(
            replace(batch.steps[0], action_receipt=None), batch.steps[1],
        ))
    elif attack == "foreign_session":
        batch = replace(batch, session_id="foreign-original")
    elif attack == "wrong_action":
        s = batch.steps[0]
        action = replace(
            s.action_receipt, terminal=replace(s.action_receipt.terminal,
                                              action_id="foreign-action"),
        )
        batch = replace(batch, steps=(replace(s, action_receipt=action), batch.steps[1]))
    elif attack == "unknown_terminal":
        s = batch.steps[0]
        from relay_self.action import ActionEvent, ActionState
        from relay_self.provenance import Provenance

        state = replace(
            s.action_receipt.terminal,
            _events=s.action_receipt.terminal.events[:-1] + (
                ActionEvent(ActionState.UNKNOWN, 4, Provenance("test", "unknown")),
            ),
        )
        batch = replace(batch, steps=(
            replace(s, action_receipt=replace(s.action_receipt, terminal=state)),
            batch.steps[1],
        ))
    elif attack == "source_before_probe":
        s = batch.steps[0]
        receipt = s.action_receipt
        evidence = replace(
            receipt.consequence,
            before_observation=replace(
                receipt.consequence.before_observation,
                seq=s.probe.seq,
            ),
        )
        batch = replace(batch, steps=(replace(
            s, action_receipt=replace(receipt, consequence=evidence),
        ), batch.steps[1]))
    elif attack == "wrong_clear_seq":
        s = batch.steps[0]
        receipt = s.action_receipt
        evidence = replace(
            receipt.consequence,
            cleanup_receipt=replace(
                receipt.consequence.cleanup_receipt,
                seq=receipt.consequence.dispatch_receipt.seq,
            ),
        )
        batch = replace(batch, steps=(replace(
            s, action_receipt=replace(receipt, consequence=evidence),
        ), batch.steps[1]))
    elif attack == "false_B0":
        admission = replace(admission, admission=replace(
            admission.admission, real_b0_decision_supplied=True,
        ))
    elif attack == "false_source":
        admission = replace(admission, source_attested=True)
    readout = observe_original_s49_s16_receipts(
        enabled=True, batch=batch, original_admission=admission,
    )
    assert readout.status == "DEFERRED"
    assert readout.original_actions == ()
    row = bounded_original_s49_owner_receipt_row(readout)
    assert row["actions"] == [] and row["session_id"] is None


def test_no_touch_default_off_and_typed_false_flag():
    class NoSource:
        def __getattribute__(self, key):
            raise AssertionError("disabled tap touched source")

    for enabled in (False, 1):
        readout = observe_original_s49_s16_receipts(
            enabled=enabled, batch=NoSource(), original_admission=NoSource(),
        )
        assert readout.status == "DISABLED"


def test_live_callback_carries_bounded_s16_receipts_not_source_snapshots():
    batch, _ = _accepted_batch()
    tap = M616OriginalS49CompletedTap(enabled=True)
    tap(batch)
    assert tap.readout["status"] == "RECORDED"
    s16 = tap.original_s16_receipts
    assert s16["status"] == "RECORDED"
    assert s16["outcome_count"] == 1
    assert s16["actions"][0]["action_id"] == batch.steps[0].step.action_request_id
    assert s16["actions"][0]["s16_before_seq"] > batch.steps[0].probe.seq
    assert "snapshot" not in repr(s16)
    tap(batch)
    assert tap.readout["status"] == "DEFERRED"
    assert tap.original_s16_receipts["status"] == "DEFERRED"


@pytest.mark.parametrize("change", (
    {"s42_owner_receipt": "PRESENT"},
    {"b0_owner_receipt": "PRESENT"},
    {"l8_owner_receipt": "PRESENT"},
    {"action_authority": True},
    {"native_reads": 1},
    {"model_calls": 1},
    {"energy_debits": 1},
))
def test_bounded_receipts_reject_fabricated_owner_or_resource(change):
    original, _ = _accepted_batch()
    tap = M616OriginalS49CompletedTap(enabled=True)
    tap(original)
    row = S49MOwnerReceiptReadout(
        "DISABLED", "not_enabled",
    )
    with pytest.raises(ValueError):
        bounded_original_s49_owner_receipt_row(replace(row, **change))


def test_failure_is_atomic_after_successful_original_M_admission():
    batch, admission = _accepted_batch()
    foreign = S49OriginalCompletedBatch("foreign", batch.steps)
    out = observe_original_s49_s16_receipts(
        enabled=True, batch=foreign, original_admission=admission,
    )
    assert out.status == "DEFERRED"
    assert not out.original_actions
