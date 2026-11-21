"""#860: P0D main-thread Paper tick witness readback for the owned process.

The Bukkit plugin in experiments/p0b_paper_recorder writes this DEV evidence.
Matching the dedicated ACK and the log of the *same owned process* improves
provenance beyond an arbitrary callback, but is NOT cryptographic attestation,
complete Paper save proof, or authorization to control a Minecraft server.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import time
import uuid
from pathlib import Path
from typing import Callable

from relay_self.owned_paper_world_dev import PaperTickReceipt

_NAMES = frozenset({
    "boot_id", "nonce", "paper_tick", "server_session_id", "source", "world_uuid",
})
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class PaperTickWitnessError(ValueError):
    """The claimed Paper main-thread tick could not be independently joined."""


def _canonical_uuid(value: str) -> str:
    try:
        normalized = str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise PaperTickWitnessError("noncanonical UUID in Paper tick witness") from exc
    if normalized != value:
        raise PaperTickWitnessError("noncanonical UUID in Paper tick witness")
    return value


def _receipt(raw: bytes) -> dict[str, str]:
    if len(raw) > 4096:
        raise PaperTickWitnessError("oversize Paper tick witness ACK")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PaperTickWitnessError("non-UTF8 Paper tick witness ACK") from exc
    fields: dict[str, str] = {}
    for line in text.splitlines():
        name, sep, value = line.partition("=")
        if sep != "=" or name not in _NAMES or name in fields:
            raise PaperTickWitnessError("foreign, duplicate or invalid Paper witness field")
        if _TOKEN.fullmatch(value) is None:
            raise PaperTickWitnessError("invalid Paper tick witness field")
        fields[name] = value
    if set(fields) != _NAMES:
        raise PaperTickWitnessError("incomplete Paper witness ACK")
    _canonical_uuid(fields["nonce"])
    _canonical_uuid(fields["boot_id"])
    _canonical_uuid(fields["world_uuid"])
    if fields["source"] != "PAPER_MAIN_THREAD":
        raise PaperTickWitnessError("Paper main-thread source missing")
    if (
        not fields["paper_tick"].isdecimal()
        or str(int(fields["paper_tick"])) != fields["paper_tick"]
    ):
        raise PaperTickWitnessError("noncanonical Paper tick")
    return fields


def _write_request(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        out = memoryview(data)
        while out:
            n = os.write(fd, out)
            if n <= 0:
                raise PaperTickWitnessError("short tick witness request write")
            out = out[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


class PaperMainThreadTickReader:
    """Synchronous callback suitable for OwnedPaperWorld.tick_readback.

    read_owned_log(session_id) MUST be sourced from the *same owned* Popen
    process log, never a global server.log path or another running server.
    """

    def __init__(
        self, *, spool_dir: Path, expected_world_uuid: str,
        read_owned_log: Callable[[str], bytes],
        timeout_seconds: float = 4.0,
        monotonic: Callable[[], float] = time.monotonic,
        pause: Callable[[float], None] = time.sleep,
        allow_repeated_same_boot: bool = False,
    ) -> None:
        self.expected_world_uuid = _canonical_uuid(expected_world_uuid)
        self.spool_dir = Path(spool_dir)
        if self.spool_dir.is_symlink() or not self.spool_dir.is_dir():
            raise PaperTickWitnessError("owned Paper tick spool directory missing")
        self.requests = self.spool_dir / "requests"
        self.acks = self.spool_dir / "acks"
        if (
            any(p.is_symlink() or not p.is_dir() for p in (self.requests, self.acks))
            or not callable(read_owned_log)
            or not callable(monotonic) or not callable(pause)
            or type(allow_repeated_same_boot) is not bool
            or type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30
        ):
            raise PaperTickWitnessError("invalid owned Paper tick reader")
        self.read_owned_log = read_owned_log
        self.timeout_seconds = float(timeout_seconds)
        self.monotonic = monotonic
        self.pause = pause
        self._seen_sessions: dict[str, str] = {}
        self._seen_boots: set[str] = set()
        self._last_ticks: dict[str, int] = {}
        self.allow_repeated_same_boot = allow_repeated_same_boot

    def __call__(self, owned_server_session: str) -> PaperTickReceipt:
        # One source-qualified tick witness per server generation.
        if (
            type(owned_server_session) is not str
            or not owned_server_session.startswith("paper-owned-")
            or (owned_server_session in self._seen_sessions
                and not self.allow_repeated_same_boot)
            or _TOKEN.fullmatch(owned_server_session) is None
        ):
            raise PaperTickWitnessError("unknown or reused Paper process session")
        nonce = str(uuid.uuid4())
        fields = (
            "nonce=" + nonce + "\n"
            + "server_session_id=" + owned_server_session + "\n"
            + "world_uuid=" + self.expected_world_uuid + "\n"
        ).encode()
        request = self.requests / (nonce + ".request")
        staging = self.requests / (nonce + ".tmp")
        reply = self.acks / (nonce + ".ack")
        # Never expose half-written .request to Paper's main-thread poller.
        # Hard-link publication fails closed if a matching nonce already exists.
        _write_request(staging, fields)
        try:
            os.link(staging, request, follow_symlinks=False)
            staging.unlink()
            dir_fd = os.open(self.requests, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as exc:
            raise PaperTickWitnessError("atomic Paper witness request publication failed") from exc
        deadline = self.monotonic() + self.timeout_seconds
        while self.monotonic() < deadline:
            if reply.is_symlink():
                raise PaperTickWitnessError("symlink Paper main-thread ACK")
            if reply.is_file():
                try:
                    fd = os.open(reply, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        raw = os.read(fd, 4097)
                    finally:
                        os.close(fd)
                except OSError as exc:
                    raise PaperTickWitnessError("unreadable main-thread ACK") from exc
                claimed = _receipt(raw)
                if (
                    claimed["nonce"] != nonce
                    or claimed["server_session_id"] != owned_server_session
                    or claimed["world_uuid"] != self.expected_world_uuid
                    or (
                        claimed["boot_id"] in self._seen_boots
                        and claimed["boot_id"] != self._seen_sessions.get(owned_server_session)
                    )
                    or (
                        owned_server_session in self._seen_sessions
                        and claimed["boot_id"] != self._seen_sessions[owned_server_session]
                    )
                    or (
                        owned_server_session in self._last_ticks
                        and int(claimed["paper_tick"]) < self._last_ticks[owned_server_session]
                    )
                ):
                    raise PaperTickWitnessError("Paper tick ACK from stale/foreign boot or World")
                marker = (
                    "P0D_TICK_ACK nonce=" + nonce
                    + " boot=" + claimed["boot_id"]
                    + " session=" + owned_server_session
                    + " world=" + claimed["world_uuid"]
                    + " tick=" + claimed["paper_tick"]
                    + " source=PAPER_MAIN_THREAD"
                )
                try:
                    paper_log = self.read_owned_log(owned_server_session)
                except OSError as exc:
                    raise PaperTickWitnessError("owned Paper process log unavailable") from exc
                if not isinstance(paper_log, bytes):
                    raise PaperTickWitnessError("invalid owned Paper log source")
                lines = paper_log.decode("utf-8", errors="replace").splitlines()
                ready = (
                    "P0D_TICK_READY boot=" + claimed["boot_id"]
                    + " source=PAPER_MAIN_THREAD"
                )
                ready_indices = [n for n, line in enumerate(lines) if ready in line]
                ack_indices = [n for n, line in enumerate(lines) if marker in line]
                if ready_indices and ack_indices and min(ready_indices) < max(ack_indices):
                    self._seen_sessions[owned_server_session] = claimed["boot_id"]
                    self._seen_boots.add(claimed["boot_id"])
                    self._last_ticks[owned_server_session] = int(claimed["paper_tick"])
                    digest = hashlib.sha256(raw).hexdigest()
                    return PaperTickReceipt(
                        server_session_id=owned_server_session,
                        tick=int(claimed["paper_tick"]),
                        source_ref=(
                            "paper-main-thread:p0d:" + claimed["boot_id"]
                            + ":" + nonce + ":sha256:" + digest
                        ),
                    )
            self.pause(0.02)
        raise PaperTickWitnessError(
            "Paper main-thread ACK/log not correlated before bounded timeout"
        )
