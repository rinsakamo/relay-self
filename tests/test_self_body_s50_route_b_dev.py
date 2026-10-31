"""Route B host source/lifecycle negatives; no synthetic World PASS claim."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_live_next_epoch import (
    LiveNextEpochLease,
    LiveNextEpochReadout,
    LiveNextEpochRejected,
)
from adapters.mineflayer.self_body_s50_world_dev import (
    S49PhysicalFailure,
    wait_live_paper_window,
)
from adapters.mineflayer.self_s7_native_receipt import (
    NativeStreamReceipt,
    NativeStreamReceiptRejected,
)
from test_s50_live_paper_window import MARKER, capture, captured
from test_self_body_s50_live_next_epoch import next_source, prior_body


@pytest.mark.parametrize("missing", ["wait", "input", "both", "partial", "foreign"])
def test_live_host_wait_requires_both_complete_newline_sources(tmp_path, missing):
    raw = captured()
    if missing in ("wait", "both"):
        raw = b"\n".join(x for x in raw.split(b"\n") if b"S50_DEV_WAIT_TICK" not in x)
    if missing in ("input", "both"):
        raw = b"\n".join(x for x in raw.split(b"\n") if b"S50_DEV_INPUT_TICK" not in x)
    if missing == "partial":
        raw = raw.rstrip(b"\n")
    if missing == "foreign":
        raw = raw.replace(MARKER.encode(), b"foreign")
    path = tmp_path / "paper.log"
    path.write_bytes(raw)
    with pytest.raises(S49PhysicalFailure, match="missing complete"):
        asyncio.run(wait_live_paper_window(path, marker=MARKER, timeout_s=.001))


def test_wait_and_recorded_read_are_once(tmp_path, monkeypatch):
    path = tmp_path / "paper.log"
    path.write_bytes(captured())
    asyncio.run(wait_live_paper_window(path, marker=MARKER, timeout_s=.1))
    original = LiveNextEpochReadout.read_previous_motion
    count = []
    def counted(self):
        count.append(1)
        return original(self)
    monkeypatch.setattr(LiveNextEpochReadout, "read_previous_motion", counted)
    lease = LiveNextEpochLease(prior_body(), capture())
    asyncio.run(lease.observe_original_l0_probe(next_source()))
    taken = lease.take_once()
    assert taken.current_body.observation.native_seq == next_source().seq
    first = lease.decision_readback()
    first["previous_action_id"] = "mutated diagnostic copy"
    assert lease.decision_readback()["previous_action_id"] != first["previous_action_id"]
    assert count == [1]
    with pytest.raises(LiveNextEpochRejected):
        lease.take_once()


def test_s7_owner_snapshot_keeps_measured_full_original_open(tmp_path):
    root = tmp_path / "prefix"
    root.mkdir()
    recorder = NativeStreamReceipt(tmp_path / "received.jsonl", tmp_path / "sent.jsonl")
    recorder.record_received(b'{"seq":0}\n')
    recorder.record_sent(b'{"type":"observe"}\n')
    prefix = recorder.snapshot_prefix(root)
    recorder.record_received(b'{"seq":1}\n')
    final = recorder.close()
    assert prefix["received_lines"] == 1 and final["received_lines"] == 2
    assert recorder.received.read_bytes().startswith((root / "received.jsonl").read_bytes())
    assert prefix["received_sha256"] != final["received_sha256"]
    with pytest.raises(NativeStreamReceiptRejected):
        recorder.snapshot_prefix(root)


def test_s7_snapshot_rejects_changed_original(tmp_path):
    root = tmp_path / "prefix"
    root.mkdir()
    recorder = NativeStreamReceipt(tmp_path / "received.jsonl", tmp_path / "sent.jsonl")
    recorder.record_received(b'{"seq":0}\n')
    recorder.received.write_bytes(b'forged\n')
    try:
        with pytest.raises(NativeStreamReceiptRejected, match="changed"):
            recorder.snapshot_prefix(root)
    finally:
        recorder.close()


def test_unknown_s16_cannot_enter_live_host():
    body = prior_body()
    with pytest.raises(LiveNextEpochRejected):
        LiveNextEpochLease(replace(body, outcome=replace(body.outcome, source_status="unknown")), capture())
