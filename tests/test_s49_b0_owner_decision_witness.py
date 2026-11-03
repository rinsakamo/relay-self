"""Source-owned B0 decision-only witness against original S49 typed fixtures.

Probes and S16 outcomes are SYNTHETIC. Never report native Energy debit.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_s49_completed_decision_bridge as s49_test
from adapters.mineflayer.s49_b0_owner_decision_witness import (
    S49B0DecisionWitness,
    S49B0WitnessRejected,
    bounded_original_b0_decision_row,
    validate_original_b0_decisions,
)
from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from adapters.mineflayer.s49_normal_session_real_ci import qualify
from experiments.metabolism_viability import initial_body


def _owner():
    steps, probes, receipts = s49_test._synthetic_original_shape()
    original = read_original_s49_completions(steps, probes, receipts)
    witness = S49B0DecisionWitness(original.session_id)
    for item in original.steps:
        witness.observe(item.probe)
    return original, witness, witness.complete(original)


def test_original_b0_owner_decides_on_exact_native_source_without_debit():
    original, witness, batch = _owner()
    assert batch.original_l0 is original
    assert batch.owner_ledger is witness.ledger
    assert len(batch.original_decisions) == len(original.steps)
    assert all(
        a.original_probe is b.probe
        for a, b in zip(batch.original_decisions, original.steps)
    )
    assert all(row.original_decision.kind == "WAIT" for row in batch.original_decisions)
    assert batch.owner_ledger.body == initial_body(batch.owner_ledger.config)
    assert batch.owner_ledger.credit_count == 0
    assert batch.energy_transitions == batch.energy_debits == batch.food_credits == 0
    row = bounded_original_b0_decision_row(batch)
    assert row["status"] == "RECORDED"
    assert row["decision_count"] == len(original.steps)
    assert row["energy_debits"] == 0
    assert row["true_world_energy"] == "UNKNOWN_NO_PHYSICAL_ENERGY_TICK"
    assert row["b0_owner_model_energy"].startswith("UNADVANCED")
    assert row["source_attested"] is False
    assert "snapshot" not in repr(row)


@pytest.mark.parametrize("attack", (
    "session", "copy_probe", "copy_decision", "missing", "duplicate",
    "fake_tick", "energy_debit", "food_credit", "wrong_decision_seq",
    "wrong_sensor", "move_model_energy", "replay_probe",
))
def test_b0_forgery_or_owner_energy_mutation_rejected(attack):
    original, witness, batch = _owner()
    first = batch.original_decisions[0]
    if attack == "session":
        batch = replace(batch, session_id="foreign")
    elif attack == "copy_probe":
        batch = replace(batch, original_decisions=(
            replace(first, original_probe=replace(first.original_probe)),
            *batch.original_decisions[1:],
        ))
    elif attack == "copy_decision":
        batch = replace(batch, original_decisions=(
            replace(first, original_decision=replace(
                first.original_decision, probe_seq=first.original_decision.probe_seq + 1,
            )),
            *batch.original_decisions[1:],
        ))
    elif attack == "missing":
        batch = replace(batch, original_decisions=batch.original_decisions[:-1])
    elif attack == "duplicate":
        batch = replace(batch, original_decisions=batch.original_decisions * 2)
    elif attack == "fake_tick":
        witness.ledger.step("WAIT")
    elif attack == "energy_debit":
        batch = replace(batch, energy_debits=1)
    elif attack == "food_credit":
        batch = replace(batch, food_credits=1)
    elif attack == "wrong_decision_seq":
        batch = replace(batch, original_decisions=(
            replace(first, original_decision=replace(
                first.original_decision, probe_seq=999,
            )),
            *batch.original_decisions[1:],
        ))
    elif attack == "wrong_sensor":
        batch = replace(batch, original_decisions=(
            replace(first, original_decision=replace(
                first.original_decision,
                sensor_reading=first.original_decision.sensor_reading + 1.0,
            )),
            *batch.original_decisions[1:],
        ))
    elif attack == "move_model_energy":
        witness.ledger.body = replace(witness.ledger.body, energy=10.0)
    elif attack == "replay_probe":
        witness.observe(original.steps[0].probe)
        with pytest.raises(S49B0WitnessRejected):
            witness.complete(original)
        return
    with pytest.raises(S49B0WitnessRejected):
        validate_original_b0_decisions(batch)


def test_b0_dev_seam_is_default_off_and_blocked_before_world(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.delenv("S49_B0_DECISION_WITNESS_DEV_ONLY", raising=False)
    report = tmp_path / "blocked.json"
    rc = asyncio.run(qualify(
        report, tmp_path / "server.log", completed_b0_decisions_dev=True,
    ))
    assert rc == 2
    assert not (tmp_path / "server.log").exists()
