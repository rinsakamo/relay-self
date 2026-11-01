"""MP4: bounded read-only S50 host forecast -> existing Paper console pipe.

No Minecraft launch, no extra reader, no extra Action/issuer, no retry.
A queued or console-written prediction is NOT Paper ACCEPTED. The Paper
main-thread ACCEPT/MATCH owner is the sole source for that narrower event.
"""
from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REQUIRED = (
    "dev-enabled", "s50-tick-meter-dev",
    "s50-forecast-gate-dev", "s50-input-witness-dev",
)


class ForecastDispatchRejected(ValueError):
    """Malformed, foreign, over-budget or unpinned diagnostics-only command."""


class _Pipe(Protocol):
    async def drain(self) -> None: ...


class _Server(Protocol):
    returncode: int | None
    stdin: _Pipe | None


@dataclass(frozen=True, slots=True)
class ForecastCommand:
    marker: str
    world: str
    subject_uuid: str
    prior_tick: int
    target_tick: int
    predicted_m: float
    ticket_sha256: str

    def wire(self) -> str:
        if (
            any(type(s) is not str or _TOKEN.fullmatch(s) is None
                for s in (self.marker, self.world, self.subject_uuid))
            or type(self.ticket_sha256) is not str
            or _SHA.fullmatch(self.ticket_sha256) is None
            or type(self.prior_tick) is not int
            or type(self.target_tick) is not int
            or not 0 <= self.prior_tick < 2**63 - 1
            or self.target_tick != self.prior_tick + 1
            or type(self.predicted_m) is not float
            or not math.isfinite(self.predicted_m)
            or not 0 <= self.predicted_m <= 64
        ):
            raise ForecastDispatchRejected("unbounded/foreign command or tick")
        return (
            f"relaydevforecast {self.marker} {self.prior_tick} {self.target_tick} "
            f"{self.predicted_m!r} {self.ticket_sha256}"
        )


def require_paper_gate_config(config_path: Path, expected_sha: str) -> None:
    """Read verified pin, reject disabled/duplicate flags BEFORE any Java World."""
    import hashlib

    if (
        not isinstance(config_path, Path)
        or not config_path.is_absolute()
        or config_path.is_symlink() or not config_path.is_file()
        or not isinstance(expected_sha, str)
        or _SHA.fullmatch(expected_sha) is None
    ):
        raise ForecastDispatchRejected("missing pinned absolute Paper config")
    data = config_path.read_bytes()
    if len(data) > 1_000_000 or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ForecastDispatchRejected("Paper config source hash changed")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ForecastDispatchRejected("invalid Paper UTF-8 config") from exc
    for key in _REQUIRED:
        entries = re.findall(rf"^{re.escape(key)}:\s*([^#\r\n]+)", text, re.M)
        if len(entries) != 1 or entries[0].strip() != "true":
            raise ForecastDispatchRejected(f"Paper {key} true not uniquely pinned")


class PaperForecastDispatch:
    """Single bounded best-effort console writer, not server stdin owner."""

    def __init__(self, *, marker: str, world: str, subject_uuid: str) -> None:
        if any(type(v) is not str or _TOKEN.fullmatch(v) is None
               for v in (marker, world, subject_uuid)):
            raise ForecastDispatchRejected("unbound Paper console target")
        self.marker = marker
        self.world = world
        self.subject_uuid = subject_uuid
        self._queue: asyncio.Queue[ForecastCommand] = asyncio.Queue(maxsize=7)
        self.queued = 0
        self.sent = 0
        self.closed = False

    def offer(self, prediction: ForecastCommand) -> None:
        if not isinstance(prediction, ForecastCommand):
            raise ForecastDispatchRejected("typed forecast required")
        prediction.wire()
        if (
            self.closed
            or (prediction.marker, prediction.world, prediction.subject_uuid)
            != (self.marker, self.world, self.subject_uuid)
            or self.queued >= 7
        ):
            raise ForecastDispatchRejected("foreign, closed or full Paper queue")
        try:
            self._queue.put_nowait(prediction)
        except asyncio.QueueFull as exc:
            raise ForecastDispatchRejected("bounded Paper queue exhausted") from exc
        self.queued += 1

    async def pump(self, server: _Server, *, on_sent=None) -> None:
        """Send each offered item exactly once with S49's existing _command.

        The owner's separate Paper ACCEPT/REJECT line, not this pump, decides
        whether a command was processed before the future callback.
        """
        from adapters.mineflayer.s31a_real_server_ci import _command

        while not self.closed or not self._queue.empty():
            try:
                prediction = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                continue
            try:
                if server.returncode is not None or server.stdin is None:
                    raise ForecastDispatchRejected("Paper server ended before write")
                _command(server, prediction.wire())
                await server.stdin.drain()
                self.sent += 1
                if on_sent is not None:
                    on_sent(prediction)
            finally:
                self._queue.task_done()

    def close(self) -> None:
        self.closed = True
