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
