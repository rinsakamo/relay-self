"""S0 DEV only: fixture source readback, no real World/WB/M attestation."""
from dataclasses import replace

import pytest

from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from adapters.mineflayer.s49_owner_cognition_join import (
    NOT_SUPPLIED,
    bounded_s49_cognition_join_row,
    join_completed_s49_cognition,
)
from test_s49_completed_decision_bridge import _synthetic_original_shape


def _source():
    steps, probes, receipts = _synthetic_original_shape()
    return read_original_s49_completions(steps, probes, receipts)


def test_disabled_default_does_not_validate_or_observe():
    result = join_completed_s49_cognition(batch=object())
    assert result.status == "DISABLED"
    assert result.decisions == ()
    assert result.new_action_issues == result.new_native_reads == 0


def test_original_typed_s49_source_readout_without_invented_wb_m():
    batch = _source()
    result = join_completed_s49_cognition(enabled=True, batch=batch)
    assert result.status == "RECORDED"
    assert result.session_id == batch.session_id
    assert result.m_status == result.wb_status == NOT_SUPPLIED
    assert result.model_usage == "UNKNOWN_NOT_METERED"
    row = bounded_s49_cognition_join_row(result)
    assert row["decision_count"] == 2
    assert row["decision_source_ids"][0]["action_id"] is not None
    assert row["decision_source_ids"][1]["action_id"] is None
    assert row["s42_owner"] == row["b0_owner"] == row["l8_owner"] == NOT_SUPPLIED
    assert row["source_attested"] is row["action_authority"] is False
    for name in (
        "new_native_reads", "new_model_calls", "new_action_issues",
        "learning_updates", "energy_debits",
    ):
        assert row[name] == 0
    assert "MineflayerObservation" not in repr(row)
    assert "NormalActionReceipt" not in repr(row)


@pytest.mark.parametrize("attack", [
    "session", "authority", "s42", "replay", "missing_s16",
    "foreign_probe", "bad_terminal", "not_a_batch",
])
def test_invalid_original_rejected_atomically(attack):
    batch = _source()
    if attack == "session":
        batch = replace(batch, session_id="foreign")
    elif attack == "authority":
        batch = replace(batch, action_authority=True)
    elif attack == "s42":
        batch = replace(batch, real_s42_epoch_supplied=True)
    elif attack == "replay":
        batch = replace(batch, steps=(batch.steps[0], batch.steps[0]))
    elif attack == "missing_s16":
        batch = replace(batch, steps=(
            replace(batch.steps[0], action_receipt=None), batch.steps[1],
        ))
    elif attack == "foreign_probe":
        batch = replace(batch, steps=(
            replace(batch.steps[0], probe=batch.steps[1].probe), batch.steps[1],
        ))
    elif attack == "bad_terminal":
        owner = batch.steps[0].action_receipt
        assert owner is not None
        batch = replace(batch, steps=(
            replace(batch.steps[0], action_receipt=replace(
                owner, terminal=replace(owner.terminal, action_id="foreign"),
            )), batch.steps[1],
        ))
    else:
        batch = object()
    result = join_completed_s49_cognition(enabled=True, batch=batch)
    assert result.status == "DEFERRED"
    assert result.session_id is None
    assert result.decisions == ()
    assert result.new_action_issues == result.new_native_reads == 0


def test_foreign_optional_companions_do_not_claim_integration():
    batch = _source()
    for supplied in ({"m_admission": object()}, {"wb_read": object()}):
        readout = join_completed_s49_cognition(
            enabled=True, batch=batch, **supplied,
        )
        assert readout.status == "DEFERRED"
        assert readout.decisions == ()


def test_allowlist_serializer_requires_typed_readout():
    with pytest.raises(ValueError, match="typed"):
        bounded_s49_cognition_join_row(object())
