"""B0 two-epoch control and source gates; no Java/Node/World startup."""
import asyncio
from dataclasses import replace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.b0_two_epoch import (
    B0TwoEpochRejected,
    _admit_hunger_wait,
    run_two_ground_epochs,
)
from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from experiments.metabolism_viability import MetabolismConfig


def test_two_epoch_hunger_wait_requires_real_item_free_source():
    probe = s46.case()
    no_item = replace(probe, snapshot=replace(
        probe.snapshot, inventory=(),
    ))
    ledger = B0EnergyLedger(no_item.session_id)
    trace = _admit_hunger_wait(ledger, no_item)
    assert trace["l0_kind"] == "WAIT"
    assert trace["issued_action"] is False
    assert trace["probe_seq"] == no_item.seq
    assert ledger.body.tick == 0
    with pytest.raises(B0TwoEpochRejected, match="no item fixture"):
        _admit_hunger_wait(ledger, replace(
            no_item, seq=no_item.seq + 1,
            snapshot=replace(no_item.snapshot, inventory=(
                MineflayerInventoryItem("rotten_flesh", 1, 5),
            )),
        ))


def test_two_epoch_runner_refuses_stale_or_used_body_before_world():
    probe = s46.case()
    ledger = B0EnergyLedger(probe.session_id)
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(None, None, ledger, [{"already": "used"}]))
    terminal = B0EnergyLedger(
        probe.session_id,
        config=MetabolismConfig(initial_energy=0.5),
    )
    terminal.step("WAIT")
    assert terminal.body.terminal
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(None, None, terminal, []))


def test_nonforcing_two_epoch_prelaunch_rejects_used_trace():
    probe = s46.case()
    ledger = B0EnergyLedger(probe.session_id, forage_policy="sensor_gate")
    with pytest.raises(B0TwoEpochRejected, match="fresh live"):
        asyncio.run(run_two_ground_epochs(
            None, None, ledger, [{"used": True}], nonforcing=True,
        ))


def test_nonforcing_terminal_is_measured_outcome_not_forced_seek(monkeypatch):
    import adapters.mineflayer.b0_two_epoch as two

    probe = s46.case()
    ledger = B0EnergyLedger(
        probe.session_id, forage_policy="sensor_gate",
        config=MetabolismConfig(initial_energy=1),
    )

    async def fake_stage(*args):
        return None

    async def fake_opportunity(*args, **kwargs):
        assert kwargs["nonforcing"] is True
        assert kwargs["epoch"] == 0
        ledger.step("WAIT")
        ledger.step("WAIT")
        return {
            "status": "M0_TERMINAL_NO_PICKUP",
            "pickup_inventory_delta": 0,
            "epoch": 0,
        }

    monkeypatch.setattr(two, "_stage_hunger", fake_stage)
    monkeypatch.setattr(two, "acquire_staged_ground_flesh", fake_opportunity)
    traces = []
    result = asyncio.run(run_two_ground_epochs(
        None, None, ledger, traces, nonforcing=True,
    ))
    assert result["outcome"] == "M0_TERMINAL_NO_PICKUP"
    assert result["m0_terminal"] is True
    assert result["credits"] == result["meals"] == 0
    assert result["epochs_started"] == 1
    assert len(traces) == 1 and traces[0]["stage"] == "OBSERVED_NONFORCING_NO_PICKUP"
