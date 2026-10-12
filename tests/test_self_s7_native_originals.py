"""S7 offline-only raw bridge boundary capture and original-index readback."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_s7_evidence_audit as audit
from adapters.mineflayer import self_s7_native_trial as trial
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerLaunchConfig,
)
from adapters.mineflayer.self_s7_native_receipt import (
    NativeStreamReceipt,
    NativeStreamReceiptRejected,
)
from test_mineflayer_process_session import (
    FakeProcess,
    observation_line,
    started_line,
)

USER_HASH = "baa0e633a10f2cfd64107d1aee77250e56b4fa56405c826ff27e2f3f3652fd47"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fixture_index(root: Path):
    (root / "physical").mkdir()
    (root / "physical" / "session_events.jsonl").write_bytes(b'{"derived":true}\n')
    (root / "physical" / "owned_cleanup.json").write_bytes(b'{"stop_ack":false}\n')
    entries = [
        p for p in (root / "physical").iterdir() if p.is_file()
    ]
    entries.sort()
    raw = "".join(
        f"{_sha(p.read_bytes())}  {p.relative_to(root)}\n"
        for p in entries
    ).encode()
    (root / "SHA256SUMS").write_bytes(raw)
    return _sha(raw)


def test_full_original_bridge_received_and_sent_bytes(monkeypatch, tmp_path):
    process = FakeProcess([started_line(), observation_line()])
    async def launch(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("fixture")
    receipt = NativeStreamReceipt(
        tmp_path / "original_received.jsonl",
        tmp_path / "original_sent.jsonl",
    )

    async def exercise():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            native_receipt=receipt,
        )
        await session.receive()
        await session.send_observe("s7-correlated-probe")

    asyncio.run(exercise())
    meta = receipt.close()
    received = (tmp_path / "original_received.jsonl").read_bytes()
    sent = (tmp_path / "original_sent.jsonl").read_bytes()
    assert received == started_line() + observation_line()
    assert b'"request_id":"s7-correlated-probe"' in sent
    assert meta["received_sha256"] == _sha(received)
    assert meta["sent_sha256"] == _sha(sent)
    assert meta["received_lines"] == 2 and meta["sent_lines"] == 1
    assert meta["minecraft_tcp_packet_bytes"] is False
    assert meta["native_execution_ack_attested"] is False


def test_malformed_original_line_is_saved_before_decode(monkeypatch, tmp_path):
    process = FakeProcess([started_line(), b"{malformed-json}\n"])

    async def launch(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("fixture")
    receipt = NativeStreamReceipt(
        tmp_path / "rx.jsonl", tmp_path / "tx.jsonl",
    )

    async def exercise():
        s = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            native_receipt=receipt,
        )
        with pytest.raises((MineflayerAdapterProtocolError, ValueError)):
            await s.receive()

    asyncio.run(exercise())
    receipt.close()
    assert (tmp_path / "rx.jsonl").read_bytes().endswith(b"{malformed-json}\n")


def test_outbound_capture_precedes_send_no_execution_ack(monkeypatch, tmp_path):
    process = FakeProcess([started_line()])
    receipt = NativeStreamReceipt(tmp_path / "rx.jsonl", tmp_path / "tx.jsonl")

    async def failing_drain():
        raise BrokenPipeError("uncertain delivery")

    process.stdin.drain = failing_drain

    async def launch(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("fixture")

    async def exercise():
        s = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            native_receipt=receipt,
        )
        with pytest.raises(Exception):
            await s.send_observe("attempted-but-not-confirmed")

    asyncio.run(exercise())
    details = receipt.close()
    assert b"attempted-but-not-confirmed" in (tmp_path / "tx.jsonl").read_bytes()
    assert details["native_execution_ack_attested"] is False


def test_optional_none_stays_legacy_without_capture(monkeypatch, tmp_path):
    process = FakeProcess([started_line()])
    async def launch(*_args, **_kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("fixture")

    async def exercise():
        s = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        await s.send_observe("normal")
    asyncio.run(exercise())
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bridge.mjs"]


@pytest.mark.parametrize("received,sent", [
    ("same", "same"), ("../foreign", "good"), ("x", "x"),
])
def test_receipt_paths_reject_alias_or_escape(tmp_path, received, sent):
    with pytest.raises(NativeStreamReceiptRejected):
        NativeStreamReceipt(tmp_path / received, tmp_path / sent)


def test_receipt_fails_closed_for_incomplete_lines_and_overwrite(tmp_path):
    rx = tmp_path / "rx.jsonl"
    tx = tmp_path / "tx.jsonl"
    rec = NativeStreamReceipt(rx, tx)
    with pytest.raises(NativeStreamReceiptRejected):
        rec.record_received(b"missing-terminator")
    with pytest.raises(NativeStreamReceiptRejected):
        rec.record_sent(b"\n" * (1024 * 1024 + 1))
    rec.close()
    with pytest.raises(NativeStreamReceiptRejected):
        NativeStreamReceipt(rx, tx)


def test_user_sha_mismatch_is_diagnostic_not_original_content_mutation(tmp_path):
    claimed = _fixture_index(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = audit.audit(
        tmp_path,
        reported_index_sha256=claimed,
        user_supplied_sha256=USER_HASH,
    )
    assert result["classification"] == "S7_REPORTED_INDEX_MATCH_USER_HASH_DIFFERENT"
    assert result["index_actual_sha256"] == claimed
    assert result["indexed_files_all_sha256_match"] is True
    assert result["user_hash_other_original_matches"] == []
    assert result["raw_mineflayer_jsonl_available_in_s6"] is False
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_tampered_sha_index_fails_closed(tmp_path):
    claimed = _fixture_index(tmp_path)
    (tmp_path / "physical" / "owned_cleanup.json").write_text("tampered")
    result = audit.audit(
        tmp_path,
        reported_index_sha256=claimed,
        user_supplied_sha256=USER_HASH,
    )
    assert result["classification"] == "S7_ORIGINAL_INDEX_CONTENT_MISMATCH_BLOCKED"
    assert result["indexed_files_all_sha256_match"] is False


@pytest.mark.parametrize("line", [
    f"{'0'*64}  ../forbidden",
    f"{'0'*64}  /tmp/forbidden",
    f"{'0'*64}  SHA256SUMS",
    "wrong sha",
])
def test_sha_audit_does_not_leave_evidence_root(tmp_path, line):
    (tmp_path / "SHA256SUMS").write_text(line + "\n")
    with pytest.raises(audit.S7EvidenceRejected):
        audit.audit(
            tmp_path,
            reported_index_sha256="0" * 64,
            user_supplied_sha256=USER_HASH,
        )


def test_audit_default_no_host_read(capsys, monkeypatch):
    monkeypatch.setattr(audit, "audit", lambda *_a, **_k:
                        pytest.fail("dry audit plan must not inspect host"))
    assert audit.main([]) == 0
    assert json.loads(capsys.readouterr().out)["original_host_evidence_read"] is False


def test_s7_future_trial_default_has_no_effect(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_a, **_k:
                        pytest.fail("default must not touch RSEE"))
    assert trial.main([]) == 0
    assert json.loads(capsys.readouterr().out)["world_started"] is False


def test_consumed_s6_grant_cannot_start_new_s7(monkeypatch, capsys):
    monkeypatch.setattr(trial.s1, "preflight", lambda *_a, **_k:
                        pytest.fail("consumed grant must be rejected first"))
    assert trial.main([
        "--run-disposable", "--confirm", trial.CONFIRM,
        "--standing-eula-confirmed",
        "--authorization-reference", trial.CONSUMED_S6_GRANT,
        "--output-dir", "/tmp/s7-absent",
    ]) == 2
    assert "S7_NEW_PHYSICAL_AUTHORITY_REQUIRED" in capsys.readouterr().out
