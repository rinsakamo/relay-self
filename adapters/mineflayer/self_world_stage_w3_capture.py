"""W3: byte-exact received Node→Python JSONL transcript, OFFLINE DEV.

Captures stdout.readline bytes BEFORE UTF-8/JSON decode and before
S49 filters. This is NOT Minecraft TCP, server raw packets, or an
externally independent archivist. Only a new disposable opt-in session.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class W3CaptureRejected(ValueError):
    """Missing, incomplete, corrupt or noncanonical Node stdout receipt."""


class W3RawNodeStdoutCapture:
    """Exclusive-create, synchronous append, bounded, sealed single stream."""

    def __init__(self, root: Path, *, max_bytes: int = 32 * 1024 * 1024) -> None:
        if (
            not isinstance(root, Path) or not root.is_absolute()
            or not root.is_dir() or root.is_symlink()
            or any(p.is_symlink() for p in root.parents)
            or type(max_bytes) is not int or not 1024 <= max_bytes <= 512 * 1024 * 1024
        ):
            raise W3CaptureRejected("fresh absolute non-symlink evidence root required")
        self.raw_path = root / "w3-node-stdout.raw.jsonl"
        self.receipt_path = root / "w3-node-stdout-receipt.json"
        if self.receipt_path.exists() or self.receipt_path.is_symlink():
            raise W3CaptureRejected("W3 original receipt already exists")
        fd = os.open(str(self.raw_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self._file = os.fdopen(fd, "wb")
        self._digest = hashlib.sha256()
        self._bytes = 0
        self._count = 0
        self._max = max_bytes
        self._first: int | None = None
        self._last: int | None = None
        self._sid: str | None = None
        self._ack_count = 0
        self._eof = False
        self._fault: str | None = None
        self._sealed = False

    def append_before_decode(self, raw: bytes) -> None:
        if self._sealed or self._eof or self._fault:
            raise W3CaptureRejected("W3 transcript not appendable")
        if (
            not isinstance(raw, bytes) or not raw or not raw.endswith(b"\n")
            or len(raw) > 1024 * 1024
            or self._bytes + len(raw) > self._max
        ):
            self._fault = "invalid_or_unbounded_node_frame"
            raise W3CaptureRejected(self._fault)
        try:
            self._file.write(raw)
            self._file.flush()
            os.fsync(self._file.fileno())
        except OSError as exc:
            self._fault = "raw_write_failure"
            raise W3CaptureRejected(self._fault) from exc
        self._digest.update(raw)
        self._bytes += len(raw)
        self._count += 1

    def after_decoder(self, *, session_id: str, seq: int, message_type: str) -> None:
        if self._sealed or self._fault:
            raise W3CaptureRejected("cannot attest failed W3 decoder")
        if (
            not isinstance(session_id, str) or not session_id
            or type(seq) is not int or seq != self._count - 1
            or not isinstance(message_type, str)
        ):
            self._fault = "decoder_sequence_mismatch"
            raise W3CaptureRejected(self._fault)
        if self._sid is None:
            if seq != 0 or message_type != "adapter_started":
                self._fault = "missing_adapter_started"
                raise W3CaptureRejected(self._fault)
            self._sid = session_id
            self._first = seq
        elif session_id != self._sid:
            self._fault = "decoder_session_mismatch"
            raise W3CaptureRejected(self._fault)
        self._last = seq
        if message_type == "shutdown_ack":
            self._ack_count += 1

    def mark_decode_failure(self) -> None:
        self._fault = "node_protocol_decode_failed"

    def mark_eof(self) -> None:
        self._eof = True

    def seal(self, *, exit_code: int | None, reason: str) -> dict[str, object]:
        if self._sealed:
            raise W3CaptureRejected("W3 receipt already sealed")
        self._sealed = True
        try:
            self._file.flush()
            os.fsync(self._file.fileno())
        finally:
            self._file.close()
        complete = (
            self._fault is None and self._eof and exit_code == 0
            and self._first == 0 and self._last == self._count - 1
            and self._count >= 2 and self._ack_count == 1
            and reason == "clean_shutdown"
        )
        receipt: dict[str, object] = {
            "schema": "relay-self-w3-node-stdout-v0",
            "scope": "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP",
            "session_id": self._sid,
            "first_seq": self._first, "last_seq": self._last,
            "frame_count": self._count, "byte_count": self._bytes,
            "stdout_sha256": self._digest.hexdigest(),
            "eof_observed": self._eof,
            "shutdown_ack_count": self._ack_count,
            "process_exit_code": exit_code, "seal_reason": reason,
            "capture_fault": self._fault,
            "status": "COMPLETE_NODE_STDOUT" if complete else "INCOMPLETE_UNQUALIFIED",
            "minecraft_tcp_packets_attested": False,
            "external_source_independence_attested": False,
            "s10_commit_permitted": False,
            "physical_wait_permitted": False,
            "science_qualified": False,
        }
        payload = (json.dumps(receipt, sort_keys=True, separators=(",", ":"))+"\n").encode()
        fd = os.open(
            str(self.receipt_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
        )
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        return receipt


def audit_w3_sealed_stdout(root: Path) -> dict[str, object]:
    """Independent read-only replay of saved raw JSONL against claimed receipt.

    No trust in the given receipt as an external timestamp or original producer.
    """
    if not isinstance(root, Path) or not root.is_dir() or root.is_symlink():
        raise W3CaptureRejected("valid W3 original directory required")
    raw_path = root / "w3-node-stdout.raw.jsonl"
    receipt_path = root / "w3-node-stdout-receipt.json"
    if (
        not raw_path.is_file() or raw_path.is_symlink()
        or not receipt_path.is_file() or receipt_path.is_symlink()
    ):
        raise W3CaptureRejected("both sealed W3 files required")
    data = raw_path.read_bytes()
    if len(data) > 32 * 1024 * 1024 or not data:
        raise W3CaptureRejected("W3 raw bounds exceeded")
    try:
        receipt = json.loads(receipt_path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise W3CaptureRejected("invalid W3 receipt") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != "relay-self-w3-node-stdout-v0"
        or receipt.get("scope") != "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
        or receipt.get("stdout_sha256") != hashlib.sha256(data).hexdigest()
        or receipt.get("byte_count") != len(data)
        or receipt.get("status") != "COMPLETE_NODE_STDOUT"
        or receipt.get("eof_observed") is not True
        or receipt.get("shutdown_ack_count") != 1
        or receipt.get("process_exit_code") != 0
        or receipt.get("seal_reason") != "clean_shutdown"
        or receipt.get("capture_fault") is not None
        or any(receipt.get(k) is not False for k in (
            "minecraft_tcp_packets_attested", "external_source_independence_attested",
            "s10_commit_permitted", "physical_wait_permitted", "science_qualified",
        ))
    ):
        raise W3CaptureRejected("W3 incomplete or forged receipt")
    from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
    decoder = MineflayerStreamDecoder()
    count = 0
    ack_count = 0
    for raw in data.splitlines(keepends=True):
        if not raw.endswith(b"\n") or len(raw) > 1024 * 1024:
            raise W3CaptureRejected("partial or oversized W3 frame")
        try:
            text = raw.decode("utf-8")
            message = decoder.decode(text)
        except (UnicodeError, ValueError) as exc:
            raise W3CaptureRejected("W3 decoded native frame mismatch") from exc
        if message.seq != count:
            raise W3CaptureRejected("W3 sequence gap")
        count += 1
        if type(message).__name__ == "MineflayerShutdownAck":
            ack_count += 1
    if (
        count != receipt.get("frame_count")
        or count < 2 or receipt.get("first_seq") != 0
        or receipt.get("last_seq") != count - 1
        or receipt.get("session_id") != decoder.session_id
        or ack_count != 1 or decoder.next_seq != count
    ):
        raise W3CaptureRejected("W3 source stream not consistent with signed-out receipt")
    return receipt
