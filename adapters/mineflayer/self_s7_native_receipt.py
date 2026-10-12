"""S7 optional exact Mineflayer bridge JSONL stream capture; NOT game TCP packets.

Owner-local, append-only originals at the Python-process I/O boundary. This
does not authenticate Minecraft protocol packets, server command ACKs, L0
authority, Action closure, or a future R1/R2/V claim.
"""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


class NativeStreamReceiptRejected(ValueError):
    """Source capture must never silently truncate or silently become optional."""


MAX_LINE = 1024 * 1024
MAX_RECEIVED_BYTES = 16 * 1024 * 1024
MAX_SENT_BYTES = 4 * 1024 * 1024
MAX_RECEIVED_LINES = 4096
MAX_SENT_LINES = 512


def _physical_new_path(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise NativeStreamReceiptRejected("receipt requires absolute fresh path")
    if path.exists() or path.is_symlink():
        raise NativeStreamReceiptRejected("native receipt must not overwrite existing file")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise NativeStreamReceiptRejected("parent must be an existing physical directory")
    if parent.resolve(strict=True) != parent or any(
        p.is_symlink() for p in parent.parents
    ):
        raise NativeStreamReceiptRejected("noncanonical/symlinked native receipt root")


class NativeStreamReceipt:
    """Capture the bytes actually read/written at one existing process boundary.

    Received bytes are recorded immediately after stdout.readline(), BEFORE
    Python decodes JSON; sent bytes are recorded BEFORE stdin.write/drain,
    therefore an outbound record proves *intent*, not delivery/ACK. Recording
    failures propagate and fail closed. Neither stream is ever replayed.
    """

    def __init__(self, received: Path, sent: Path) -> None:
        _physical_new_path(received)
        _physical_new_path(sent)
        if received == sent or received.parent != sent.parent:
            raise NativeStreamReceiptRejected("separate files in one root required")
        self.received = received
        self.sent = sent
        self._in = received.open("xb")
        try:
            self._out = sent.open("xb")
        except BaseException:
            self._in.close()
            raise
        self._received_hash = hashlib.sha256()
        self._sent_hash = hashlib.sha256()
        self.received_lines = 0
        self.sent_lines = 0
        self.received_bytes = 0
        self.sent_bytes = 0
        self._closed = False

    def _append(self, raw: bytes, *, incoming: bool) -> None:
        if self._closed:
            raise NativeStreamReceiptRejected("closed original source recorder")
        if not isinstance(raw, bytes) or not raw or not raw.endswith(b"\n"):
            raise NativeStreamReceiptRejected("original native JSONL line is incomplete")
        count = self.received_lines if incoming else self.sent_lines
        size = self.received_bytes if incoming else self.sent_bytes
        cap = MAX_RECEIVED_BYTES if incoming else MAX_SENT_BYTES
        lines = MAX_RECEIVED_LINES if incoming else MAX_SENT_LINES
        if len(raw) > MAX_LINE or count >= lines or size + len(raw) > cap:
            raise NativeStreamReceiptRejected("original native capture bound exhausted")
        target = self._in if incoming else self._out
        n = target.write(raw)
        if n != len(raw):
            raise NativeStreamReceiptRejected("partial original native write")
        target.flush()
        os.fsync(target.fileno())
        if incoming:
            self._received_hash.update(raw)
            self.received_lines += 1
            self.received_bytes += n
        else:
            self._sent_hash.update(raw)
            self.sent_lines += 1
            self.sent_bytes += n

    def record_received(self, raw: bytes) -> None:
        self._append(raw, incoming=True)

    def record_sent(self, raw: bytes) -> None:
        self._append(raw, incoming=False)

    def close(self) -> dict[str, object]:
        if self._closed:
            raise NativeStreamReceiptRejected("receipt already closed")
        self._closed = True
        try:
            self._in.flush()
            os.fsync(self._in.fileno())
            self._out.flush()
            os.fsync(self._out.fileno())
        finally:
            self._in.close()
            self._out.close()
        for path in (self.received, self.sent):
            if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
                raise NativeStreamReceiptRejected("original source replaced")
        return {
            "schema": "SELF_S7_RAW_MINEFLAYER_JSONL_RECEIPT_V1",
            "received_path": str(self.received),
            "sent_path": str(self.sent),
            "received_lines": self.received_lines,
            "sent_lines": self.sent_lines,
            "received_bytes": self.received_bytes,
            "sent_bytes": self.sent_bytes,
            "received_sha256": self._received_hash.hexdigest(),
            "sent_sha256": self._sent_hash.hexdigest(),
            "received_measured_before_decode": True,
            "sent_measured_before_write": True,
            "minecraft_tcp_packet_bytes": False,
            "native_execution_ack_attested": False,
            "v_science_qualified": False,
        }
