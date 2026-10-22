"""W4 observation-only DEV interface (source-local, no physical run grant).

This module does not launch a Minecraft World or carry any runnable CLI.
The original ProcessSession owns the sole Node stdout reader. A real run
must have a separately authenticated, HEAD-specific, spend-once DEV grant
and must use the original one Java stdout collector. Frame review cannot
make local Java console text independently authenticated World/tick truth.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerObservation,
    encode_observe,
    encode_shutdown,
)


class ObservationOnlyDevBlocked(ValueError):
    """An observation-only source/command boundary was not met."""


class ObservationOnlyDevSession(MineflayerProcessSession):
    """Original decoder and one reader; never send a physical Action.

    Public inherited Action methods reach this exact _send boundary and are
    rejected before writing to the bridge. Only canonical, explicitly
    correlated observe and shutdown commands are admitted. This contract
    is not a run grant or a second action/reader owner.
    """

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
        await super()._send(line)

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
        rc = await self.shutdown(timeout_s=timeout_s)
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
