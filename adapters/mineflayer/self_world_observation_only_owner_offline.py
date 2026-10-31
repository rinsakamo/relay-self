"""W4 observation-only SINGLE OWNER rehearsal with in-memory transports only.

Not an actual native Java/Mineflayer launcher. All Node/Java processes below
are closed classes allocating NO OS subprocesses, sockets, Minecraft Worlds,
Action/S10 owner, or grant verifier. Producer-local receipts remain DEV_ONLY.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    encode_observe,
    encode_shutdown,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _correlated_observe,
)
from adapters.mineflayer.self_world_observation_only_close import (
    close_observation_only_dev,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevBlocked,
    ObservationOnlyDevSession,
    review_observation_only_dev_offline,
    wait_for_observation_raw_world_marker,
)
from adapters.mineflayer.self_world_observation_only_entry import (
    ObservationOnlyEntryInventory,
)
from adapters.mineflayer.self_world_observation_only_lifetime import (
    join_observation_only_local_lifetime,
)
from adapters.mineflayer.self_world_stage_w4_logtap import (
    capture_w4_collector_cursor,
)


class _InMemoryNode:
    """Not an OS process. The only stdout source is an in-memory deque."""

    def __init__(self, raw_frames: tuple[bytes, ...]) -> None:
        sid = json.loads(raw_frames[0])["session_id"]
        last = len(raw_frames)
        ack = (json.dumps({
            "type": "shutdown_ack", "session_id": sid, "seq": last,
        }) + "\n").encode()
        end = (json.dumps({
            "type": "connection_end", "session_id": sid, "seq": last + 1,
            "reason": "synthetic normal shutdown",
        }) + "\n").encode()
        self._frames = deque([*raw_frames, ack, end])
        self.stdout = self
        self.stdin = self
        self.returncode: int | None = None
        self.writes: list[bytes] = []
        self.frame_reads = 0

    async def readline(self) -> bytes:
        await asyncio.sleep(0)
        self.frame_reads += 1
        return self._frames.popleft() if self._frames else b""

    def write(self, raw: bytes) -> None:
        self.writes.append(raw)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    async def wait(self) -> int:
        if not self.writes or self.writes[-1] != encode_shutdown().encode():
            raise ObservationOnlyDevBlocked("in-memory Node STOP absent")
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


class _InMemoryJava:
    """No server process, no stdout pipe, and no executable World commands."""

    def __init__(self) -> None:
        self.stdin = self
        self.returncode: int | None = None
        self.writes: list[bytes] = []

    def write(self, raw: bytes) -> None:
        if raw != b"stop\n":
            raise ObservationOnlyDevBlocked("Java console accepts synthetic STOP only")
        self.writes.append(raw)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    async def wait(self) -> int:
        if self.writes != [b"stop\n"]:
            raise ObservationOnlyDevBlocked("in-memory Java STOP absent")
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


async def rehearse_observation_only_owner_offline(
    *, inventory: ObservationOnlyEntryInventory,
    raw_frames: tuple[bytes, ...],
    before_request: str, after_request: str,
    marker_line: bytes, evidence_root: Path,
) -> dict[str, object]:
    """Exercise the original reader/capture/STOP/close under one fake owner.

    All inputs are TEST data; this function has no executable grant/launcher
    port and cannot be promoted into a physical-run entry by passing flags.
    Java collector bytes are simulated on disk, NOT a server stdout tap.
    """
    if (
        type(inventory) is not ObservationOnlyEntryInventory
        or inventory.disposition != "PREWORLD_BLOCKED"
        or type(raw_frames) is not tuple or len(raw_frames) != 6
        or any(type(x) is not bytes or not x.endswith(b"\n") for x in raw_frames)
        or type(before_request) is not str or not before_request
        or type(after_request) is not str or not after_request
        or before_request == after_request
        or type(marker_line) is not bytes or not marker_line.endswith(b"\n")
        or not isinstance(evidence_root, Path) or not evidence_root.is_absolute()
        or not evidence_root.is_dir() or evidence_root.is_symlink()
        or any(evidence_root.iterdir())
    ):
        raise ObservationOnlyDevBlocked("one empty evidence root and six fake frames required")

    node = _InMemoryNode(raw_frames)
    java = _InMemoryJava()
    # The simulated Java log is never the real Java stdout pipe.
    java_log = evidence_root / "sole-java-collector.raw"
    with java_log.open("xb") as sink:
        sink.write(b"[10:00:00] [Server thread/INFO]: fake collector ready\n")
    collector = asyncio.create_task(asyncio.sleep(0))
    session = ObservationOnlyDevSession(node, raw_capture_root=evidence_root)
    readback = None
    raw_marker = None
    closed = None
    try:
        started = await session.receive()
        if type(started) is not MineflayerAdapterStarted:
            raise ObservationOnlyDevBlocked("missing fake adapter_started")
        session._started = started
        spawn = await _await_spawn(session)
        before = await _correlated_observe(session, before_request)
        cursor = capture_w4_collector_cursor(java_log)
        # This writes only fake console data, never a World command.
        with java_log.open("ab") as sink:
            sink.write(marker_line)
        raw_marker = await wait_for_observation_raw_world_marker(
            cursor, timeout_s=0.3,
        )
        after = await _correlated_observe(session, after_request)
        readback = review_observation_only_dev_offline(
            started=started, spawn=spawn, before=before, after=after,
            before_request=before_request, after_request=after_request,
            raw_marker_line=marker_line,
            marker_sha256=hashlib.sha256(marker_line).hexdigest(),
            marker_after_before=True, after_marker=True,
        )
        expected = [
            encode_observe(before_request).encode(),
            encode_observe(after_request).encode(),
        ]
        if node.writes != expected:
            raise ObservationOnlyDevBlocked("probe command sequence mismatch")
    finally:
        # Owner owns this teardown exactly once, including any probe failure.
        closed = await close_observation_only_dev(
            server=java, collector=collector, session=session, timeout_s=0.5,
        )
    if readback is None or raw_marker is None:
        raise ObservationOnlyDevBlocked("missing complete observation window")
    joined = join_observation_only_local_lifetime(
        inventory=inventory, readback=readback, marker=raw_marker,
        close=closed, node_raw_root=evidence_root,
    )
    if (
        node.writes != [
            encode_observe(before_request).encode(),
            encode_observe(after_request).encode(), encode_shutdown().encode(),
        ]
        or java.writes != [b"stop\n"]
        or node.frame_reads != len(raw_frames) + 3
    ):
        raise ObservationOnlyDevBlocked("fake process owner not exclusive and closed")
    return {
        "schema": "W4_OBSERVATION_ONLY_OWNER_REHEARSAL_OFFLINE_V1",
        "scope": "FAKE_PROCESSES_LOCAL_CONTENT_ONLY",
        "local_lifetime": asdict(joined),
        "node_raw_audit": closed["node_stdout_receipt"],
        "node_commands": ["observe", "observe", "shutdown"],
        "java_commands": ["stop"],
        "node_frame_reads_including_eof": node.frame_reads,
        "raw_java_marker": asdict(raw_marker),
        "physical_run_permitted": False,
        "external_grant_verified": False,
        "external_owner_attested": False,
        "actual_pid_port_disposal_attested": False,
        "science_qualified": False,
        "action_count": 0,
        "outcome_count": 0,
        "s10_update_count": 0,
    }
