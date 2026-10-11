"""E12: original-byte captured Mineflayer process owner and Action3 terminal.

Operator library only. Does not launch Java, select a World, grant Action
authority, or authenticate physical origin. Never invoked by offline CI with
a genuine Node process. E5 physical science is NOT_RUN.
"""
from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequence,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerConnectionEnd,
    MineflayerLaunchConfig,
    MineflayerShutdownAck,
    encode_shutdown,
)
from experiments.epistemic_e11_avatar_handoff import SourceShutdown
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.provenance import Provenance

MAX_LINE_BYTES = 262_144
MAX_SOURCE_BYTES = 4_194_304
MAX_CLOSE_FRAMES = 32


class E12Rejected(ValueError):
    """An untrusted child or Action3 owner failed its exact source contract."""


@dataclass(frozen=True, slots=True)
class Action3TerminalReceipt:
    consequence: WorldConsequence
    interpretation: ActionOutcomeInterpretation
    action: ActionLifecycle | None
    parent_qualified: bool
    physically_authenticated: bool = False


def _loopback(config: MineflayerLaunchConfig) -> None:
    if not isinstance(config, MineflayerLaunchConfig):
        raise E12Rejected("exact typed native launch config required")
    try:
        host = ipaddress.ip_address(config.host)
    except ValueError as exc:
        raise E12Rejected("numeric loopback host only") from exc
    if not host.is_loopback or host.is_unspecified:
        raise E12Rejected("external or wildcard Minecraft host forbidden")


class OriginalWireSession(MineflayerProcessSession):
    """One owned Node process, exact raw wire copied BEFORE typed decoding.

    A bad wire line stays in the raw evidence. SHA alone does not authenticate
    this process, its Minecraft endpoint or a World. Only the caller can retain
    Java-server and /proc identity evidence independently.
    """

    def __init__(self, process, raw_file):
        super().__init__(process)
        self._raw_file = raw_file
        self.source_bytes = 0
        self.shutdown_sent = False
        self.closed = False
        self.wire_frames = 0

    @classmethod
    async def launch_original(
        cls,
        config: MineflayerLaunchConfig,
        *,
        raw_path: str | Path,
        node_executable: str = "node",
        bridge_path: str | Path | None = None,
        startup_timeout_s: float = 10.0,
        spawn: Callable | None = None,
    ) -> "OriginalWireSession":
        _loopback(config)
        path = Path(raw_path)
        if not path.parent.is_dir():
            raise E12Rejected("pre-existing evidence directory required")
        if not 0 < startup_timeout_s <= 120:
            raise E12Rejected("positive bounded startup deadline required")
        bridge = (
            Path(__file__).resolve().parents[1] / "adapters" / "mineflayer" / "bridge.mjs"
            if bridge_path is None else Path(bridge_path)
        )
        if not bridge.is_file():
            raise E12Rejected("original bridge not found")
        if not node_executable or node_executable != node_executable.strip():
            raise E12Rejected("invalid Node executable")
        # Atomic exclusive output reservation, before any child or physical I/O.
        try:
            file = path.open("xb")
        except OSError as exc:
            raise E12Rejected("source evidence output exists or cannot be created") from exc
        process = None
        session = None
        try:
            spawn_fn = asyncio.create_subprocess_exec if spawn is None else spawn
            process = await spawn_fn(
                *config.argv(bridge, node_executable=node_executable),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=None,
            )
            session = cls(process, file)
            msg = await asyncio.wait_for(session.receive(), startup_timeout_s)
            if (not isinstance(msg, MineflayerAdapterStarted)
                    or msg.seq != 0 or msg.config != config):
                raise E12Rejected("original adapter_started / exact config missing")
            session._started = msg
            return session
        except BaseException:
            if session is not None:
                await session.terminate()
            elif process is not None and process.returncode is None:
                process.terminate()
                await process.wait()
            file.close()
            raise

    async def receive(self):
        if self.closed:
            raise MineflayerProcessEnded("raw owner already closed")
        raw = await self._process.stdout.readline()
        if not raw:
            raise MineflayerProcessEnded("original bridge stdout ended")
        self.source_bytes += len(raw)
        # Fail closed before decode but keep original overlimit bytes on disk.
        self._raw_file.write(raw)
        self._raw_file.flush()
        if (len(raw) > MAX_LINE_BYTES or self.source_bytes > MAX_SOURCE_BYTES
                or not raw.endswith(b"\n")):
            raise MineflayerProcessIOError("bounded complete JSONL framing required")
        try:
            frame = self._decoder.decode(raw.decode("utf-8"))
        except UnicodeError as exc:
            raise MineflayerProcessIOError("original stdout non-UTF8") from exc
        self.wire_frames += 1
        return frame

    async def close_original(self, *, timeout_s: float = 10.0) -> SourceShutdown:
        """Once-only native shutdown ACK / optional close / EOF / owned exit0.

        This is suitable as the E11 close_source callback. No second Node
        process may be launched until this returns a successful receipt.
        """
        if self.shutdown_sent or self.closed or not 0 < timeout_s <= 120:
            raise E12Rejected("shutdown already attempted or timeout invalid")
        self.shutdown_sent = True
        session_id = self.started.session_id
        ack = None
        end = None

        async def _consume():
            nonlocal ack, end
            await self._send(encode_shutdown())
            for _ in range(MAX_CLOSE_FRAMES):
                try:
                    msg = await self.receive()
                except MineflayerProcessEnded:
                    break
                if ack is None:
                    if isinstance(msg, MineflayerShutdownAck):
                        if msg.session_id != session_id:
                            raise E12Rejected("foreign native shutdown acknowledgement")
                        ack = msg
                    elif isinstance(msg, MineflayerConnectionEnd):
                        raise E12Rejected("native connection ended before shutdown ACK")
                elif isinstance(msg, MineflayerConnectionEnd) and end is None:
                    if msg.seq != ack.seq + 1:
                        raise E12Rejected("connection close not immediately after ACK")
                    end = msg
                else:
                    raise E12Rejected("extra or duplicate source after native shutdown ACK")
            else:
                raise E12Rejected("native shutdown exceeded close frame bound")
            if ack is None:
                raise E12Rejected("native shutdown ACK missing")
            exit_code = await self._process.wait()
            if type(exit_code) is not int or exit_code != 0:
                raise E12Rejected("owned bridge nonzero terminal exit")
            return SourceShutdown(session_id, ack, end, exit_code)

        try:
            return await asyncio.wait_for(_consume(), timeout_s)
        finally:
            self.closed = True
            self._raw_file.close()
            if self._process.returncode is None:
                await self.terminate()

    async def terminate(self) -> int:
        self.closed = True
        try:
            return await super().terminate()
        finally:
            self._raw_file.close()


class OneAvatarOriginalOwner:
    """No overlapping original parent and Action4 clients, no retries."""

    def __init__(
        self,
        config: MineflayerLaunchConfig,
        *,
        parent_raw: str | Path,
        action_raw: str | Path,
        bridge_path: str | Path | None = None,
        node_executable: str = "node",
        spawn: Callable | None = None,
    ) -> None:
        _loopback(config)
        self.config = config
        self.parent_raw = Path(parent_raw)
        self.action_raw = Path(action_raw)
        if self.parent_raw == self.action_raw:
            raise E12Rejected("distinct exclusive original output files required")
        if self.parent_raw.exists() or self.action_raw.exists():
            raise E12Rejected("cannot replace existing native source evidence")
        self.bridge_path = bridge_path
        self.node_executable = node_executable
        self.spawn = spawn
        self.parent = None
        self.action4 = None
        self.phase = "NEW"
        self.parent_close = None

    async def start_parent(self):
        if self.phase != "NEW":
            raise E12Rejected("no second parent connection")
        self.phase = "PARENT_ATTEMPTED"
        self.parent = await OriginalWireSession.launch_original(
            self.config, raw_path=self.parent_raw,
            bridge_path=self.bridge_path,
            node_executable=self.node_executable,
            spawn=self.spawn,
        )
        self.phase = "PARENT"
        return self.parent

    async def close_parent(self, adapter) -> SourceShutdown:
        if self.phase != "PARENT" or adapter is not self.parent:
            raise E12Rejected("foreign or already closed parent session")
        self.phase = "PARENT_CLOSE_ATTEMPTED"
        result = await self.parent.close_original()
        self.parent_close = result
        self.phase = "PARENT_CLOSED"
        return result

    async def launch_action4(self):
        if self.phase != "PARENT_CLOSED" or self.parent_close is None:
            raise E12Rejected("new client cannot overlap live parent")
        self.phase = "ACTION4_ATTEMPTED"
        self.action4 = await OriginalWireSession.launch_original(
            self.config, raw_path=self.action_raw,
            bridge_path=self.bridge_path,
            node_executable=self.node_executable,
            spawn=self.spawn,
        )
        if self.action4.started.session_id == self.parent.started.session_id:
            await self.action4.terminate()
            raise E12Rejected("new source cannot reuse the old session identity")
        self.phase = "ACTION4"
        return self.action4


async def run_issued_parent_action3(
    session,
    supervisor: ActionSupervisor,
    issued: ActionLifecycle,
    binding: ExecutionBindingResult,
    *,
    at_ns: Callable[[], int],
    timeout_s: float = 5.0,
    provenance: Provenance,
) -> Action3TerminalReceipt:
    """Existing S15/S16 closure ONLY; original S23 caller owns admission.

    A complete native EXECUTED Action3 is mandatory for E10/E11 continuation.
    A rejected, UNKNOWN or UNAVAILABLE parent is reported faithfully and not
    presented as a qualified source for post-Action correlated observations.
    """
    if (not isinstance(supervisor, ActionSupervisor)
            or not isinstance(issued, ActionLifecycle)
            or issued.state is not ActionState.ISSUED
            or supervisor.get(issued.action_id) is not issued
            or not isinstance(provenance, Provenance)
            or issued.events[-1].provenance != provenance):
        raise E12Rejected("current supervised issued parent Action3 required")
    command = build_mineflayer_command(issued, binding)
    if not isinstance(getattr(session, "started", None), MineflayerAdapterStarted):
        raise E12Rejected("original native parent source not started")
    consequence = await execute_mineflayer_command(
        session, command, timeout_s=timeout_s, provenance=provenance,
    )
    if consequence.session_id != session.started.session_id:
        raise E12Rejected("cross-source parent World consequence")
    interpretation = interpret_world_consequence(
        issued, binding, consequence, provenance=provenance,
    )
    if interpretation.disposition is ActionOutcomeDisposition.UNAVAILABLE:
        return Action3TerminalReceipt(consequence, interpretation, None, False)
    ended_at = at_ns()
    if (type(ended_at) is not int
            or ended_at <= (supervisor.last_at_ns or 0)
            or ended_at >= issued.events[-1].deadline_ns):
        raise E12Rejected("late or invalid parent terminal time")
    terminal = record_interpreted_action_outcome(
        supervisor, interpretation, at_ns=ended_at,
    )
    return Action3TerminalReceipt(
        consequence, interpretation, terminal,
        consequence.status is WorldConsequenceStatus.EXECUTED
        and terminal.state is ActionState.OUTCOME,
    )
