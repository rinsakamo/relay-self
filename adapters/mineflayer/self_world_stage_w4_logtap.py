"""W4-WIN read-only tail of the *existing* server stdout collector's log.

Not another reader of Java stdout, not an Action issuer, not a physical-run
entrypoint. The existing S31A/S49 collector remains the sole stdout consumer.
All file bytes and timestamps are LOCAL PRODUCER CONTENT, never external
independent custody or attestations of World execution/tick.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_window import (
    W4PlacementCommands,
    W4WindowEvent,
)

_MARKER_RE = re.compile(r"W4NH1_READY_[A-Z0-9]{24,48}_S[12]\Z")
_MAX_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class W4CollectorCursor:
    """Before-dispatch original-file byte offset; no independent witness."""

    path: Path
    device: int
    inode: int
    start_byte: int


@dataclass(frozen=True, slots=True)
class W4CollectorMarker:
    """Verified content window in an unchanged regular log file."""

    cursor: W4CollectorCursor
    log_line: str
    start_byte: int
    end_byte: int
    raw_line_sha256: str
    read_monotonic_ns: int
    producer_content_only: bool = True
    external_source_qualified: bool = False
    physical_run_permitted: bool = False


def _open_original_log(path: Path) -> tuple[int, os.stat_result]:
    if type(path) is not Path or not path.is_absolute():
        raise W4PreworldBlocked("W4 collector log must be explicit absolute Path")
    # Avoid path alias/inode replacement. POSIX O_NOFOLLOW applies to final link;
    # ancestor aliases are also denied rather than assuming directory custody.
    for ancestor in (path, *path.parents):
        try:
            st = ancestor.lstat()
        except OSError as exc:
            raise W4PreworldBlocked("collector log path does not exist") from exc
        if stat.S_ISLNK(st.st_mode):
            raise W4PreworldBlocked("collector log path uses symlink ancestor")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
    except OSError as exc:
        raise W4PreworldBlocked("cannot open original collector log") from exc
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        os.close(fd)
        raise W4PreworldBlocked("collector log must be sole-link regular file")
    return fd, st


def capture_w4_collector_cursor(log_path: Path) -> W4CollectorCursor:
    """Capture end-of-file before original experimenter sends World commands."""
    fd, st = _open_original_log(log_path)
    os.close(fd)
    return W4CollectorCursor(
        path=log_path, device=st.st_dev, inode=st.st_ino,
        start_byte=st.st_size,
    )


def _tail_bytes(cursor: W4CollectorCursor, start: int) -> bytes:
    fd, st = _open_original_log(cursor.path)
    try:
        if (
            st.st_dev != cursor.device or st.st_ino != cursor.inode
            or st.st_size < cursor.start_byte or st.st_size < start
            or st.st_size - cursor.start_byte > _MAX_BYTES
        ):
            raise W4PreworldBlocked("collector log replaced/truncated/over limit")
        # This is a read of the already collected log, never server stdout.
        return os.pread(fd, st.st_size - start, start)
    finally:
        os.close(fd)


async def wait_for_w4_collector_marker(
    cursor: W4CollectorCursor, commands: W4PlacementCommands, *,
    timeout_s: float = 1.0, poll_s: float = 0.01,
) -> W4CollectorMarker:
    """Bounded wait for one COMPLETE log line appended after captured cursor.

    Polling is used for IO progress only. The presence/order/content of a
    line are not an authenticated Java tick, independently attested stdout,
    native packet, or S10 source. The caller must fail closed on timeout.
    """
    if (
        type(cursor) is not W4CollectorCursor
        or type(commands) is not W4PlacementCommands
        or not _MARKER_RE.fullmatch(commands.confirmation_marker)
        or type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30
        or type(poll_s) not in (int, float) or not 0 < poll_s <= 0.5
    ):
        raise W4PreworldBlocked("invalid W4 collector cursor/marker/bounds")
    deadline = time.monotonic() + timeout_s
    start = cursor.start_byte
    pending = b""
    raw_marker = None
    marker_start = None
    marker_end = None
    marker_time = None
    while True:
        buf = _tail_bytes(cursor, start)
        start += len(buf)
        pending += buf
        if len(pending) > _MAX_BYTES:
            raise W4PreworldBlocked("collector emitted unbounded partial log line")
        while b"\n" in pending:
            raw, pending = pending.split(b"\n", 1)
            raw += b"\n"
            line_start = start - len(pending) - len(raw)
            try:
                line = raw.decode("utf-8").rstrip("\n")
            except UnicodeDecodeError as exc:
                raise W4PreworldBlocked("collector log contains invalid UTF-8") from exc
            if commands.confirmation_marker in line:
                if (
                    marker_start is not None
                    or "\r" in line
                    or not line.endswith(commands.expected_log_suffix)
                    or "]: " not in line
                ):
                    raise W4PreworldBlocked("duplicate/forged/ambiguous W4 marker")
                raw_marker = raw
                marker_start = line_start
                marker_end = start - len(pending)
                marker_time = time.monotonic_ns()
        if marker_start is not None and not pending:
            # Require complete newline-delimited marker before acceptance.
            assert raw_marker is not None and marker_end is not None
            assert marker_time is not None
            return W4CollectorMarker(
                cursor, raw_marker.decode("utf-8").rstrip("\n"),
                marker_start, marker_end,
                hashlib.sha256(raw_marker).hexdigest(), marker_time,
            )
        if time.monotonic() >= deadline:
            raise W4PreworldBlocked("no unambiguous complete W4 log marker")
        await asyncio.sleep(poll_s)


def marker_as_w4_window_event(
    marker: W4CollectorMarker, *, order: int, server_pid: int,
) -> W4WindowEvent:
    """Convert read-only content marker into the old W4-WIN event vocabulary."""
    if (
        type(marker) is not W4CollectorMarker
        or type(order) is not int or order < 0
        or type(server_pid) is not int or server_pid <= 0
    ):
        raise W4PreworldBlocked("invalid W4 marker record")
    return W4WindowEvent(
        name="server_stdout_marker", order=order,
        monotonic_ns=marker.read_monotonic_ns,
        source="existing_server_console_collector",
        content=marker.log_line,
        server_pid=server_pid,
    )
