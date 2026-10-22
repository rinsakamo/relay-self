"""W4 observation-only DEV interface (source-local, no physical run grant).

This module does not launch a Minecraft World or carry any runnable CLI.
The original ProcessSession owns the sole Node stdout reader. The dedicated
real DEV runner requires explicit confirmation and pins, and uses the original
one Java stdout collector. Qualification still needs external trust. Frame review cannot
make local Java console text independently authenticated World/tick truth.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessEnded, MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerObservation,
    encode_observe,
    encode_shutdown,
)
from adapters.mineflayer.startup_process_ownership import (
    StartupCleanupUnconfirmed,
    _supervise,
    terminate_and_reap,
)


async def _bounded_observation_wait(awaitable, *, timeout_s: float, name: str):
    """Settle the exact I/O task on timeout *or* outer cancellation."""
    task = asyncio.create_task(awaitable)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout_s)
        if not done:
            raise TimeoutError(f"{name} timed out")
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            done, _ = await asyncio.wait({task}, timeout=0.25)
            if not done:
                task.add_done_callback(lambda t: None if t.cancelled() else t.exception())
                raise StartupCleanupUnconfirmed(f"{name} cancellation did not settle")
            if not task.cancelled():
                task.exception()


class ObservationOnlyDevBlocked(ValueError):
    """An observation-only source/command boundary was not met."""


class ObservationOnlyDevSession(MineflayerProcessSession):
    """Original decoder and one reader; never send a physical Action.

    Public inherited Action methods reach this exact _send boundary and are
    rejected before writing to the bridge. Only canonical, explicitly
    correlated observe and shutdown commands are admitted. This contract
    is not a run grant or a second action/reader owner.
    """

    def __init__(self, process, *, raw_capture_root=None) -> None:
        super().__init__(process, raw_capture_root=raw_capture_root)
        self._native_read_active = False

    async def receive(self):
        # One outstanding receive() on the inherited byte/decoder stream.
        # wait_for() may delegate that exact read into a child Task; no
        # ambient task/ContextVar or second stdout pipe is granted custody.
        if self._native_read_active:
            raise ObservationOnlyDevBlocked("concurrent native stdout reader denied")
        self._native_read_active = True
        try:
            return await super().receive()
        finally:
            self._native_read_active = False

    async def _send(self, line: str) -> None:
        if type(line) is not str:
            raise ObservationOnlyDevBlocked("command must be canonical text")
        try:
            payload = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise ObservationOnlyDevBlocked("invalid observation-only command") from exc
        if type(payload) is not dict:
            raise ObservationOnlyDevBlocked("command must be JSON object")
        if payload.get("type") == "observe":
            request_id = payload.get("request_id")
            if type(request_id) is not str or not request_id:
                raise ObservationOnlyDevBlocked("explicit correlated request is mandatory")
            try:
                allowed = encode_observe(request_id)
            except ValueError as exc:
                raise ObservationOnlyDevBlocked("invalid request_id") from exc
        elif payload == {"type": "shutdown"}:
            allowed = encode_shutdown()
        else:
            raise ObservationOnlyDevBlocked("Action/World effect command forbidden")
        if line != allowed:
            raise ObservationOnlyDevBlocked("noncanonical command forbidden")
        await _bounded_observation_wait(
            super()._send(line), timeout_s=5, name="observation-only command drain",
        )

    async def shutdown_with_stdout_receipt(
        self, *, timeout_s: float = 10.0,
    ) -> dict[str, object]:
        """Require the inherited W3 same-reader shutdown ACK, EOF and reap.

        This checks Node→Python received bytes, not Minecraft network bytes,
        physical Java PID custody, or an independently signed STOP witness.
        A normal no-capture shutdown cannot qualify this DEV observation gate.
        """
        if self._raw_capture is None:
            raise ObservationOnlyDevBlocked(
                "read-only STOP requires original W3 raw stdout capture"
            )
        async def graceful():
            if self._process.returncode is None:
                await self._send(encode_shutdown())
            while True:
                try:
                    await self.receive()
                except MineflayerProcessEnded:
                    break
            rc = await self._process.wait()
            if type(rc) is not int or rc != self.process_returncode:
                raise ObservationOnlyDevBlocked("Node wait/returncode mismatch")
            self._seal_raw_capture(exit_code=rc, reason="clean_shutdown")
            return rc

        # No inherited shutdown fallback with an unbounded process.wait().
        # This same session reaps and seals failures after the bounded operation.
        try:
            rc = await _bounded_observation_wait(
                graceful(), timeout_s=timeout_s, name="observation-only Node STOP/EOF/wait",
            )
        except BaseException:
            async def abort():
                try:
                    await terminate_and_reap(self._process, timeout_s=timeout_s)
                finally:
                    self._seal_raw_capture(
                        exit_code=self.process_returncode, reason="aborted_shutdown",
                    )
            await _supervise(abort())
            raise
        receipt = self.raw_capture_receipt
        if (
            type(rc) is not int or rc != 0
            or type(receipt) is not dict
            or receipt.get("status") != "COMPLETE_NODE_STDOUT"
            or receipt.get("eof_observed") is not True
            or receipt.get("shutdown_ack_count") != 1
            or receipt.get("process_exit_code") != 0
            or receipt.get("seal_reason") != "clean_shutdown"
        ):
            raise ObservationOnlyDevBlocked(
                "STOP ACK/EOF/Node exit not jointly confirmed"
            )
        return dict(receipt)


@dataclass(frozen=True, slots=True)
class ObservationOnlyDevReadback:
    session_id: str
    spawn_seq: int
    before_seq: int
    after_seq: int
    before_source: str
    after_source: str
    marker_raw_sha256: str
    marker_local_game_time: int
    scope: str = "SYNTHETIC_OR_LOCAL_CONSOLE_NOT_EXTERNAL_CUSTODY"
    action_count: int = 0
    outcome_count: int = 0
    s10_update_count: int = 0
    physical_run_permitted: bool = False
    qualification_approved: bool = False
    science_qualified: bool = False


# The console grammar is a conservative DEV-only example of the response to
# time query gametime. A real server yielding another representation is a
# reason to stop/review, never to silently accept arbitrary text as a marker.
_GAME_TIME = re.compile(
    rb"\[[^\r\n\]]+\] \[Server thread/INFO\]: The time is ([0-9]{1,15})\r?\n\Z"
)


def review_observation_only_dev_offline(
    *, started: MineflayerAdapterStarted, spawn: MineflayerObservation,
    before: MineflayerObservation, after: MineflayerObservation,
    before_request: str, after_request: str, raw_marker_line: bytes,
    marker_sha256: str, marker_after_before: bool, after_marker: bool,
) -> ObservationOnlyDevReadback:
    """Check one typed source lineage; no server/Process/issuer may be passed.

    The two ordering flags are input *claims* from a future original-owner
    capture record; tests below only prove fail-closed shape and identity.
    They do not independently attest Minecraft TCP or server tick order.
    """
    if (
        type(started) is not MineflayerAdapterStarted
        or type(spawn) is not MineflayerObservation
        or type(before) is not MineflayerObservation
        or type(after) is not MineflayerObservation
        or not started.session_id
        or any(x.session_id != started.session_id for x in (spawn, before, after))
        or spawn.kind != "spawn"
        or before.kind != "probe" or after.kind != "probe"
        or type(before_request) is not str or not before_request
        or type(after_request) is not str or not after_request
        or before_request == after_request
        or before.request_id != before_request
        or after.request_id != after_request
        or not (started.seq < spawn.seq < before.seq < after.seq)
        or before.provenance == after.provenance
        or before.provenance.source != "mineflayer"
        or after.provenance.source != "mineflayer"
        or marker_after_before is not True
        or after_marker is not True
    ):
        raise ObservationOnlyDevBlocked("unbound observation phase/session/source")
    if (
        type(raw_marker_line) is not bytes
        or type(marker_sha256) is not str
        or hashlib.sha256(raw_marker_line).hexdigest() != marker_sha256
    ):
        raise ObservationOnlyDevBlocked("raw collector marker bytes/hash mismatch")
    match = _GAME_TIME.fullmatch(raw_marker_line)
    if match is None:
        raise ObservationOnlyDevBlocked("invalid or ambiguous console marker")
    return ObservationOnlyDevReadback(
        session_id=started.session_id,
        spawn_seq=spawn.seq,
        before_seq=before.seq,
        after_seq=after.seq,
        before_source=before.provenance.reference,
        after_source=after.provenance.reference,
        marker_raw_sha256=marker_sha256,
        marker_local_game_time=int(match.group(1)),
    )


async def run_observation_only_synthetic_dev(
    *, raw_frames: tuple[bytes, ...], before_request: str,
    after_request: str, marker_line: bytes,
) -> dict[str, object]:
    """Exercise the original one-session decoder in an IN-MEMORY DEV only.

    Not a Java/Node/Minecraft launcher and deliberately accepts no Process,
    server, socket, callback, external file or grant. This cannot authorize
    any real physical execution. No consumer Action/host/S16/S10 is imported.
    """
    import asyncio
    from collections import deque
    from dataclasses import asdict

    from adapters.mineflayer.s31a_real_server_ci import (
        _await_spawn,
        _correlated_observe,
    )

    if (
        type(raw_frames) is not tuple or len(raw_frames) != 6
        or any(type(frame) is not bytes or not frame.endswith(b"\n") for frame in raw_frames)
        or type(before_request) is not str or not before_request
        or type(after_request) is not str or not after_request
        or before_request == after_request
        or type(marker_line) is not bytes
    ):
        raise ObservationOnlyDevBlocked("exact in-memory DEV fixture required")

    class _FakeProcess:
        returncode = None

        def __init__(self):
            self.remaining = deque(raw_frames)
            self.commands: list[bytes] = []
            self.stdout = self
            self.stdin = self
            self.read_count = 0

        async def readline(self) -> bytes:
            await asyncio.sleep(0)
            self.read_count += 1
            return self.remaining.popleft() if self.remaining else b""

        def write(self, raw: bytes) -> None:
            self.commands.append(raw)

        async def drain(self) -> None:
            await asyncio.sleep(0)

        async def wait(self) -> int:
            if self.commands[-1:] != [encode_shutdown().encode()]:
                raise ObservationOnlyDevBlocked("synthetic shutdown missing")
            self.returncode = 0
            return 0

        def terminate(self) -> None:
            self.returncode = -15

    process = _FakeProcess()
    session = ObservationOnlyDevSession(process)
    try:
        started = await session.receive()
        if type(started) is not MineflayerAdapterStarted:
            raise ObservationOnlyDevBlocked("native adapter_started missing")
        session._started = started
        spawn = await _await_spawn(session)
        before = await _correlated_observe(session, before_request)
        # This marker is caller-supplied test data, never native Java evidence.
        marker_sha = hashlib.sha256(marker_line).hexdigest()
        after = await _correlated_observe(session, after_request)
        result = review_observation_only_dev_offline(
            started=started, spawn=spawn, before=before, after=after,
            before_request=before_request, after_request=after_request,
            raw_marker_line=marker_line, marker_sha256=marker_sha,
            marker_after_before=True, after_marker=True,
        )
        if (
            process.remaining or process.read_count != 6
            or process.commands != [
                encode_observe(before_request).encode(),
                encode_observe(after_request).encode(),
            ]
        ):
            raise ObservationOnlyDevBlocked("unconsumed frame or foreign command")
        rc = await session.shutdown(timeout_s=5)
        if rc != 0 or process.commands[-1] != encode_shutdown().encode():
            raise ObservationOnlyDevBlocked("synthetic shutdown incomplete")
        return {
            "schema": "W4_OBSERVATION_ONLY_SYNTHETIC_DEV_V1",
            "readback": asdict(result),
            "source_frames": process.read_count,
            "commands": ["observe", "observe", "shutdown"],
            "local_shutdown_completed": True,
            "node_exit_code": rc,
            "world_marker_synthetic": True,
            "action_issued": False,
            "physical_run_permitted": False,
            "science_qualified": False,
        }
    except BaseException:
        process.terminate()  # No PID exists: synthetic process only.
        raise


@dataclass(frozen=True, slots=True)
class ObservationOnlyRawWorldMarker:
    """Content in the original sole Java collector RAW file, not a tick proof."""

    raw_start_byte: int
    raw_end_byte: int
    raw_sha256: str
    local_game_time: int
    local_collector_only: bool = True
    external_world_attested: bool = False


async def wait_for_observation_raw_world_marker(
    cursor, *, timeout_s: float = 5.0,
) -> ObservationOnlyRawWorldMarker:
    """Tail only the raw file already written by the original Java collector.

    The calling owner should capture its cursor before sending exactly one
    read-only `time query gametime` command through original Java stdin.
    This function never reads server.stdout or sends World/Action commands.
    The expected output grammar is prospective and version-dependent.
    """
    import asyncio
    import time

    from adapters.mineflayer.self_world_stage_w4_logtap import (
        W4CollectorCursor,
        _tail_bytes,
    )

    if (
        type(cursor) is not W4CollectorCursor
        or type(timeout_s) not in (int, float)
        or not 0 < timeout_s <= 30
    ):
        raise ObservationOnlyDevBlocked("valid raw collector cursor/timeout required")
    deadline = time.monotonic() + timeout_s
    start = cursor.start_byte
    pending = b""
    found = None
    while True:
        batch = _tail_bytes(cursor, start)
        start += len(batch)
        pending += batch
        if len(pending) > 65_536:
            raise ObservationOnlyDevBlocked("unbounded raw World marker tail")
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            raw = line + b"\n"
            offset = start - len(pending) - len(raw)
            # Reject any mutated/fake candidate rather than ignoring it.
            if b"The time is " in raw:
                match = _GAME_TIME.fullmatch(raw)
                if match is None or found is not None:
                    raise ObservationOnlyDevBlocked("ambiguous raw Java console marker")
                found = ObservationOnlyRawWorldMarker(
                    raw_start_byte=offset, raw_end_byte=offset + len(raw),
                    raw_sha256=hashlib.sha256(raw).hexdigest(),
                    local_game_time=int(match.group(1)),
                )
        if found is not None and not pending:
            return found
        if time.monotonic() >= deadline:
            raise ObservationOnlyDevBlocked("missing complete raw World marker")
        await asyncio.sleep(0.01)
