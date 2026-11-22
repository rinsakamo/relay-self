"""U18: original Stage27 PLACE uses bounded shared STOP settling probes.

These are synthetic Native fixtures only; they never attest Paper/World.
"""
from __future__ import annotations

import asyncio

import pytest

from relay_self.physical_action_journal import (PhysicalActionJournal, PhysicalJournalError)
from experiments.cognitive_physical_move_issue_dev import (
    PhysicalMoveRefusal,
    _settled,
)
from test_p0d_resident_move_issuer_dev import ScriptedNative


def test_u18_stage27_call_signature_accepts_exact_three_settling_probes():
    native = ScriptedNative()
    initial, first, settled, probes = asyncio.run(_settled(
        native, native="native-A", stop_seq=2,
        timeout_s=3.0, max_probe_requests=3,
    ))
    assert len(probes) == 3
    assert initial.seq < first.seq < settled.seq
    assert first.snapshot.time.time_of_day - initial.snapshot.time.time_of_day >= 8
    assert settled.snapshot.time.time_of_day - first.snapshot.time.time_of_day >= 8


@pytest.mark.parametrize("cap", [0, 1, 2, -1, True, 3.5, 4097])
def test_u18_rejects_invalid_settlement_budget_before_native_probe(cap):
    native = ScriptedNative()
    with pytest.raises(PhysicalMoveRefusal, match="invalid bounded"):
        asyncio.run(_settled(
            native, native="native-A", stop_seq=2,
            timeout_s=3.0, max_probe_requests=cap,
        ))
    assert native.seq == 2


def test_u18_stalled_body_exhausts_fixed_reservation_without_retry():
    class DriftingNative(ScriptedNative):
        async def send_observe(self, request_id):
            self.x += 0.2
            await super().send_observe(request_id)
    native = DriftingNative()
    with pytest.raises(PhysicalMoveRefusal, match="reservation exhausted"):
        asyncio.run(_settled(
            native, native="native-A", stop_seq=2,
            timeout_s=3.0, max_probe_requests=3,
        ))
    assert native.seq == 5


def test_u18_original_empty_initial_wal_prefix_rechecks_across_v2_upgrade(
    tmp_path,
):
    """A zero Action prefix is not invented S1 history or a grant."""
    journal = PhysicalActionJournal.create(tmp_path / "original.json", self_id="B")
    exact_boot_digest = journal.digest
    assert journal.records == ()
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(0)
    # The first real PLACE would upgrade the SAME original WAL to schema v2.
    # An empty upgrade here only tests canonical origin hashes, no effect.
    journal._commit([], upgrade_to_v2=True)
    assert journal.schema_version == 2
    assert journal.certified_prefix_digest(
        0, source_schema=1,
    ) == exact_boot_digest
    with pytest.raises(PhysicalJournalError):
        journal.certified_prefix_digest(0)
