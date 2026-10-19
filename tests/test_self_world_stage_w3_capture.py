"""W3 byte-exact stdout capture at the Node→Python boundary: synthetic only."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

import test_mineflayer_process_session as fixture
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    W3RawNodeStdoutCapture,
    audit_w3_sealed_stdout,
)


def _ack(seq=2):
    return (json.dumps({
        "type": "shutdown_ack", "session_id": "session-1", "seq": seq,
    }) + "\n").encode()


def _fixture_lines():
    return [fixture.started_line(), fixture.observation_line(), _ack()]


def _launch(monkeypatch, root, lines, *, shutdown=True):
    bridge = root / "bridge.mjs"
    bridge.write_text("// test bridge, no Minecraft", encoding="utf-8")
    process = fixture.FakeProcess(lines)

    async def make(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", make)

    async def scenario():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
            raw_capture_root=root,
        )
        if shutdown:
            rc = await session.shutdown()
            assert rc == 0
        return session

    return asyncio.run(scenario()), process


def test_w3_exact_raw_stdout_before_decode_and_shutdown_ack(monkeypatch, tmp_path):
    lines = _fixture_lines()
    session, process = _launch(monkeypatch, tmp_path, lines)
    raw = (tmp_path / "w3-node-stdout.raw.jsonl").read_bytes()
    receipt = session.raw_capture_receipt
    assert raw == b"".join(lines)
    assert receipt["stdout_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["frame_count"] == 3
    assert receipt["first_seq"] == 0 and receipt["last_seq"] == 2
    assert receipt["eof_observed"] is True
    assert receipt["shutdown_ack_count"] == 1
    assert receipt["status"] == "COMPLETE_NODE_STDOUT"
    assert not receipt["minecraft_tcp_packets_attested"]
    assert not receipt["external_source_independence_attested"]
    assert not receipt["s10_commit_permitted"]
    assert not receipt["physical_wait_permitted"]
    assert not receipt["science_qualified"]
    assert audit_w3_sealed_stdout(tmp_path) == receipt
    assert process.stdin.writes == [b'{"type":"shutdown"}\n']


def test_w3_default_uncaptured_lifecycle_unmodified(monkeypatch, tmp_path):
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// fixture")
    process = fixture.FakeProcess([fixture.started_line()])

    async def make(*_args, **_kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", make)

    async def scenario():
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(), bridge_path=bridge,
        )
        assert await session.shutdown() == 0
        assert session.raw_capture_receipt is None

    asyncio.run(scenario())
    assert not (tmp_path / "w3-node-stdout.raw.jsonl").exists()


@pytest.mark.parametrize("case", (
    "no_ack", "gap", "wrong_session", "duplicate_ack", "unknown_type",
    "invalid_utf8", "partial_line", "oversized_line",
))
def test_w3_bad_stream_fails_closed_and_retains_raw_evidence(
    monkeypatch, tmp_path, case,
):
    lines = _fixture_lines()
    if case == "no_ack":
        lines.pop()
    elif case == "gap":
        lines[-1] = _ack(seq=4)
    elif case == "wrong_session":
        lines[-1] = (json.dumps({
            "type": "shutdown_ack", "session_id": "intruder", "seq": 2,
        })+"\n").encode()
    elif case == "duplicate_ack":
        lines.append(_ack(seq=3))
    elif case == "unknown_type":
        lines[1] = (json.dumps({
            "type": "invented", "session_id": "session-1", "seq": 1,
        })+"\n").encode()
    elif case == "invalid_utf8":
        lines[1] = b"\xff\n"
    elif case == "partial_line":
        lines[1] = lines[1].removesuffix(b"\n")
    elif case == "oversized_line":
        lines[1] = b"x" * (1024 * 1024 + 1) + b"\n"

    if case in ("gap", "wrong_session", "unknown_type", "invalid_utf8",
                "partial_line", "oversized_line"):
        # Stream capture errors abort and then original owning session may
        # be terminated, never accepted as a complete sealed window.
        bridge = tmp_path / "bridge.mjs"
        bridge.write_text("// fixture")
        process = fixture.FakeProcess(lines)
        async def make(*_args, **_kwargs):
            return process
        monkeypatch.setattr(asyncio, "create_subprocess_exec", make)

        async def scenario():
            session = await MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), bridge_path=bridge,
                raw_capture_root=tmp_path,
            )
            with pytest.raises((ValueError, UnicodeError)):
                await session.shutdown()
            if session.raw_capture_receipt is None:
                await session.terminate()
            return session

        # Oversized raw may exceed asyncio default stream reader limits in
        # real Node; FakeStdout is a controlled source-boundary negative.
        session = asyncio.run(scenario())
    else:
        session, _ = _launch(monkeypatch, tmp_path, lines)
    assert session.raw_capture_receipt["status"] == "INCOMPLETE_UNQUALIFIED"
    with pytest.raises(W3CaptureRejected):
        audit_w3_sealed_stdout(tmp_path)


@pytest.mark.parametrize("case", (
    "replace_frame", "truncate_frame", "alter_receipt_sha",
    "remove_receipt", "falsify_qualification", "copy_stale_session",
))
def test_w3_auditor_rejects_changed_or_incomplete_original_archive(
    monkeypatch, tmp_path, case,
):
    session, _ = _launch(monkeypatch, tmp_path, _fixture_lines())
    assert session.raw_capture_receipt["status"] == "COMPLETE_NODE_STDOUT"
    raw_path = tmp_path / "w3-node-stdout.raw.jsonl"
    receipt_path = tmp_path / "w3-node-stdout-receipt.json"
    if case == "replace_frame":
        raw_path.write_bytes(raw_path.read_bytes().replace(b'"seq": 1', b'"seq": 7'))
    elif case == "truncate_frame":
        raw_path.write_bytes(raw_path.read_bytes()[:-1])
    elif case == "remove_receipt":
        receipt_path.unlink()
    else:
        receipt = json.loads(receipt_path.read_text())
        if case == "alter_receipt_sha":
            receipt["stdout_sha256"] = "0"*64
        elif case == "falsify_qualification":
            receipt["s10_commit_permitted"] = True
        elif case == "copy_stale_session":
            receipt["session_id"] = "foreign-session"
        receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(W3CaptureRejected):
        audit_w3_sealed_stdout(tmp_path)


def test_w3_rejects_reusing_an_existing_capture_root(monkeypatch, tmp_path):
    _launch(monkeypatch, tmp_path, _fixture_lines())
    with pytest.raises(W3CaptureRejected, match="already"):
        W3RawNodeStdoutCapture(tmp_path)
    assert audit_w3_sealed_stdout(tmp_path)["status"] == "COMPLETE_NODE_STDOUT"


def test_w3_raw_writer_never_overwrites_prior_or_allows_symlinks(tmp_path):
    raw = tmp_path/"w3-node-stdout.raw.jsonl"
    raw.write_bytes(b"ORIGINAL")
    with pytest.raises(FileExistsError):
        W3RawNodeStdoutCapture(tmp_path)
    assert raw.read_bytes() == b"ORIGINAL"
    raw.unlink()
    root = tmp_path / "symlink"
    root.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(W3CaptureRejected):
        W3RawNodeStdoutCapture(root)


def test_w3_stop_without_shutdown_ack_is_incomplete(tmp_path: Path):
    capture = W3RawNodeStdoutCapture(tmp_path)
    capture.append_before_decode(fixture.started_line())
    capture.after_decoder(session_id="session-1", seq=0, message_type="adapter_started")
    capture.mark_eof()
    receipt = capture.seal(exit_code=0, reason="clean_shutdown")
    assert receipt["status"] == "INCOMPLETE_UNQUALIFIED"
    with pytest.raises(W3CaptureRejected):
        audit_w3_sealed_stdout(tmp_path)
