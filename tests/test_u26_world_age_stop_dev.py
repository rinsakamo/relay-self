"""U26 CPU-only contract: server world age vs frozen Minecraft daylight clock.

Synthetic snapshots, not real World, Node/Paper or a native-action authorization.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerTime
from experiments.cognitive_physical_move_issue_dev import _settled, _tick
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalError
from test_i_unified_i4a_place_lease_dev import _acks, _probes, _terminal, _typed_place
from test_p0d_resident_move_issuer_dev import _probe


def _with_age(probe, age, *, daylight=100):
    return replace(
        probe, snapshot=replace(
            probe.snapshot,
            time=MineflayerTime(daylight, 0, True, age),
        ),
    )


def test_server_age_tick_advances_while_daylight_is_frozen():
    old = _probe("native-A", 1, "p1", 100, 1.0)
    first = _with_age(old, 110)
    later = _with_age(_probe("native-A", 2, "p2", 100, 1.0), 130)
    assert first.snapshot.time.time_of_day == later.snapshot.time.time_of_day == 100
    assert _tick(first) == 110
    assert _tick(later) == 130
    assert _tick(old) == 100


def test_original_place_wal_commits_only_same_server_age_basis(tmp_path):
    binding, before, invocation, motion = _typed_place()
    journal = PhysicalActionJournal.create(tmp_path / "physical.json", self_id="A")
    journal.prepare_place_move(binding, before, invocation, motion)
    look, start, stop = _acks("native-A", binding.action_id)
    initial, first, settled = (
        _with_age(probe, age) for probe, age
        in zip(_probes("native-A"), (110, 120, 130), strict=True)
    )
    terminal, supervisor = _terminal(binding)
    assert journal.close_place_move(
        binding, invocation, before, look, start, stop,
        initial, first, settled, terminal, supervisor,
    ) == "NATIVE_PLACE_MOVE_SETTLED"
    record = journal.records[-1]
    assert [record["initial_stop_tick"], record["first_stable_tick"],
            record["settled_tick"]] == [110, 120, 130]
    assert not journal.unresolved


def test_original_place_wal_refuses_mixed_server_age_and_daylight(tmp_path):
    binding, before, invocation, motion = _typed_place()
    journal = PhysicalActionJournal.create(tmp_path / "physical.json", self_id="A")
    journal.prepare_place_move(binding, before, invocation, motion)
    look, start, stop = _acks("native-A", binding.action_id)
    old = _probes("native-A")
    initial = _with_age(old[0], 110)
    first = _with_age(old[1], 120)
    terminal, supervisor = _terminal(binding)
    with pytest.raises(PhysicalJournalError, match="clock source changed"):
        journal.close_place_move(
            binding, invocation, before, look, start, stop,
            initial, first, old[2], terminal, supervisor,
        )
    assert journal.unresolved

@pytest.mark.parametrize(
    ("cap", "interval"),
    [(None, 0.05), (24, 0.15), (60, 0.15)],
)
def test_bounded_stop_probes_are_paced_without_raising_quota(monkeypatch, cap, interval):
    """CPU-only Native response script; STOP/settlement thresholds unchanged."""
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    class Native:
        def __init__(self):
            self.seq = 5
            self.tick = 101
            self.events = []

        async def send_observe(self, request_id):
            self.seq += 1
            self.tick += 9
            self.events.append(
                _probe("native-A", self.seq, request_id, self.tick, 1.0),
            )

        async def receive(self):
            return self.events.pop(0)

    _, _, _, probes = asyncio.run(_settled(
        Native(), native="native-A", stop_seq=5,
        timeout_s=1, max_probe_requests=cap,
    ))
    assert len(probes) == 3
    assert delays == [interval, interval]
