"""U18: original Stage27 PLACE uses bounded shared STOP settling probes.

These are synthetic Native fixtures only; they never attest Paper/World.
"""
from __future__ import annotations

import asyncio

import pytest

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
