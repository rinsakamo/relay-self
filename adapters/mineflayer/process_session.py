from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerDecodedMessage,
    MineflayerLaunchConfig,
    MineflayerStreamDecoder,
    encode_attack_entity,
    encode_clear_controls,
    encode_consume_held,
    encode_equip_item,
    encode_look,
    encode_observe,
    encode_set_control,
    encode_shutdown,
)


class MineflayerProcessError(RuntimeError):
    """Base error for the target-local Mineflayer child process."""


class MineflayerProcessStartError(MineflayerProcessError):
    """Raised when the Mineflayer bridge cannot establish a valid session."""


class MineflayerProcessEnded(MineflayerProcessError):
    """Raised when the child process stream ends before a requested message."""


class MineflayerProcessIOError(MineflayerProcessError):
    """Raised when JSONL input cannot be delivered to the child process."""


class MineflayerEffectAdmissionError(MineflayerProcessIOError):
    """A physical effect was refused before sending to the native bridge."""


class MineflayerProcessSession:
    """Own one Node/Mineflayer bridge process without adding Self semantics."""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        if process.stdin is None or process.stdout is None:
            raise MineflayerProcessStartError(
                "Mineflayer child process requires stdin and stdout pipes"
            )
        self._process = process
        self._decoder = MineflayerStreamDecoder()
        self._started: MineflayerAdapterStarted | None = None
        self._effect_admission: Callable[[str, str, str], None] | None = None
        self._atomic_effect_sender: (
            Callable[[str, str, str, Callable[[], None]], None] | None
        ) = None
        # No two coroutine writes can interleave Native frames or drains.
        self._send_lock = asyncio.Lock()
        self._bounded_place_dev_mode = False
        self._raw_source_audit_fd: int | None = None
        self._raw_source_audit_finished = False

    @classmethod
    async def launch(
        cls,
        config: MineflayerLaunchConfig,
        *,
        bridge_path: str | Path | None = None,
        node_executable: str = "node",
        startup_timeout_s: float = 10.0,
        enable_q4_bounded_place_dev: bool = False,
    ) -> "MineflayerProcessSession":
        """Launch exactly one bridge process and consume its startup attestation."""

        _require_positive_timeout("startup_timeout_s", startup_timeout_s)
        if type(enable_q4_bounded_place_dev) is not bool:
            raise MineflayerProcessStartError("Q4 DEV mode must be an explicit boolean")
        # Never accept ambient Q4 authorization inherited from a shell.
        # Only this one native process launch can receive an explicit guard.
        child_env = dict(os.environ)
        child_env.pop("RELAY_Q4_BOUNDED_PLACE_DEV", None)
        if enable_q4_bounded_place_dev:
            child_env["RELAY_Q4_BOUNDED_PLACE_DEV"] = "1"
        bridge = (
            Path(__file__).with_name("bridge.mjs")
            if bridge_path is None
            else Path(bridge_path)
        )
        if not bridge.is_file():
            raise MineflayerProcessStartError(
                f"Mineflayer bridge does not exist: {bridge}"
            )

        try:
            process = await asyncio.create_subprocess_exec(
                *config.argv(bridge, node_executable=node_executable),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=None,
                env=child_env,
            )
        except OSError as exc:
            raise MineflayerProcessStartError(
                f"could not launch Mineflayer bridge: {exc}"
            ) from exc

        try:
            session = cls(process)
        except Exception:
            await _terminate_child(process)
            raise

        try:
            started = await asyncio.wait_for(
                session.receive(),
                timeout=startup_timeout_s,
            )
        except Exception:
            await session.terminate()
            raise

        if not isinstance(started, MineflayerAdapterStarted):
            await session.terminate()
            raise MineflayerProcessStartError(
                "Mineflayer bridge did not produce adapter_started"
            )

        session._started = started
        session._bounded_place_dev_mode = enable_q4_bounded_place_dev
        return session

    @property
    def started(self) -> MineflayerAdapterStarted:
        if self._started is None:
            raise MineflayerProcessStartError(
                "Mineflayer session startup has not completed"
            )
        return self._started

    @property
    def bounded_place_dev_mode(self) -> bool:
        """Local launch option only, never a Native/Paper producer receipt."""
        return self._bounded_place_dev_mode

    def install_effect_admission(
        self, check_effect: Callable[[str, str], None],
    ) -> None:
        """One-way opt-in gate for ALL native effect commands on this session.

        check_effect(session_id, effect, action_id) must be owned by the shared checkpoint
        issuer. Observation and shutdown remain allowed. No gate removal API.
        """
        if (
            not callable(check_effect)
            or self._started is None
            or getattr(self, "_effect_admission", None) is not None
        ):
            raise MineflayerEffectAdmissionError(
                "native effect admission can only be installed once after startup"
            )
        self._effect_admission = check_effect

    def install_atomic_effect_sender(
        self,
        submit_effect: Callable[[str, str, str, Callable[[], None]], None],
    ) -> None:
        """One-way issuer-bound synchronous effect check + stdin.write callback.

        The callback is owned by the original physical gate and invokes the
        supplied writer under its source/lease locks without awaiting.
        """
        if (
            not callable(submit_effect)
            or self._started is None
            or self._effect_admission is None
            or self._atomic_effect_sender is not None
        ):
            raise MineflayerEffectAdmissionError(
                "atomic native effect sender requires one existing admission"
            )
        self._atomic_effect_sender = submit_effect

    def start_raw_source_audit(self, path: str | Path) -> None:
        """Capture exact native stdout JSONL bytes from THIS owned Node process.

        This is a source transcript, not independent Minecraft/Paper evidence.
        Exclusive creation and per-line fsync ensure an ACK or settle sample
        cannot disappear behind a success-only post-hoc JSON report.
        """
        if (
            self._started is None
            or self._raw_source_audit_fd is not None
            or self._raw_source_audit_finished
        ):
            raise MineflayerProcessIOError("native source audit already used/not started")
        location = Path(path)
        fd = os.open(location, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.fsync(fd)
            dir_fd = os.open(location.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except BaseException:
            os.close(fd)
            raise
        self._raw_source_audit_fd = fd

    def finish_raw_source_audit(self) -> None:
        """Freeze a completed source transcript before checksum readback."""
        fd = self._raw_source_audit_fd
        if fd is None or self._raw_source_audit_finished:
            raise MineflayerProcessIOError("native source audit not active")
        os.fsync(fd)
        os.close(fd)
        self._raw_source_audit_fd = None
        self._raw_source_audit_finished = True

    @property
    def owned_child_pid(self) -> int | None:
        """OS PID of THIS adapter-owned native process (not source authentication)."""
        pid = getattr(self._process, "pid", None)
        return pid if type(pid) is int and pid > 0 else None

    @property
    def process_returncode(self) -> int | None:
        return self._process.returncode

    async def receive(self) -> MineflayerDecodedMessage:
        """Read and validate exactly one target-local JSONL message."""

        assert self._process.stdout is not None
        line = await self._process.stdout.readline()
        if not line:
            raise MineflayerProcessEnded(
                "Mineflayer bridge stdout ended; "
                f"returncode={self._process.returncode}"
            )
        fd = self._raw_source_audit_fd
        if fd is not None:
            # Persist ORIGINAL bytes, including malformed/foreign stream
            # messages. A failed write is fatal, never silently drops proof.
            try:
                written = os.write(fd, line)
                if written != len(line):
                    raise OSError("partial native source audit write")
                os.fsync(fd)
            except OSError as exc:
                raise MineflayerProcessIOError(
                    "native stdout evidence write failed; source held"
                ) from exc
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MineflayerProcessIOError(
                "Mineflayer bridge emitted non-UTF-8 stdout"
            ) from exc
        return self._decoder.decode(text)

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        await self._send(
            encode_set_control(
                action_id,
                control=control,
                state=state,
            )
        )

    async def send_clear_controls(self, action_id: str) -> None:
        await self._send(encode_clear_controls(action_id))

    async def send_equip_item(
        self,
        action_id: str,
        *,
        item_name: str,
    ) -> None:
        await self._send(
            encode_equip_item(
                action_id,
                item_name=item_name,
            )
        )

    async def send_consume_held(self, action_id: str) -> None:
        await self._send(encode_consume_held(action_id))

    async def send_look(
        self,
        action_id: str,
        *,
        yaw: float,
        pitch: float,
    ) -> None:
        await self._send(
            encode_look(
                action_id,
                yaw=yaw,
                pitch=pitch,
            )
        )

    async def send_attack_entity(
        self,
        action_id: str,
        *,
        entity_id: int,
    ) -> None:
        await self._send(
            encode_attack_entity(
                action_id,
                entity_id=entity_id,
            )
        )

    async def send_observe(self, request_id: str | None = None) -> None:
        """Backwards-compatible native probe, optionally correlated by ID."""
        await self._send(encode_observe(request_id))

    async def shutdown(self, *, timeout_s: float = 5.0) -> int:
        """Request one clean bridge shutdown, with bounded termination fallback."""

        _require_positive_timeout("timeout_s", timeout_s)
        if self._process.returncode is not None:
            return self._process.returncode

        await self._send(encode_shutdown())
        try:
            return await asyncio.wait_for(
                self._process.wait(),
                timeout=timeout_s,
            )
        except TimeoutError as exc:
            await self.terminate()
            raise MineflayerProcessEnded(
                "Mineflayer bridge did not exit after shutdown request"
            ) from exc

    async def terminate(self) -> int:
        """Terminate the owned child without retrying or launching a replacement."""

        return await _terminate_child(self._process)

    async def force_terminate_owned(self, *, timeout_s: float = 0.5) -> int:
        """Q4 host kill switch: bounded TERM→KILL of this owned Node process.

        No new session and no claim of STOP ACK, World settling or WAL
        resolution. A timeout or unconfirmed exit is an explicit HOLD.
        """
        if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 1.0:
            raise MineflayerProcessIOError("Q4 termination timeout is invalid")
        if self._process.returncode is not None:
            return self._process.returncode
        self._process.terminate()
        try:
            result = await asyncio.wait_for(
                self._process.wait(), timeout=timeout_s,
            )
        except TimeoutError:
            self._process.kill()
            try:
                result = await asyncio.wait_for(
                    self._process.wait(), timeout=timeout_s,
                )
            except TimeoutError as exc:
                raise MineflayerProcessIOError(
                    "owned Q4 Native termination not confirmed after KILL"
                ) from exc
        if self._process.returncode is None:
            raise MineflayerProcessIOError(
                "owned Q4 Native process has no exit readback"
            )
        return result

    async def _send(self, line: str) -> None:
        # The original Native adapter serializes full frames including drains.
        # The opt-in atomic callback is the existing B issuer, never a second
        # selector; it holds owner/physical/WAL locks through stdin.write().
        async with self._send_lock:
            gate = getattr(self, "_effect_admission", None)
            command = None
            if gate is not None:
                try:
                    command = json.loads(line)
                except (TypeError, ValueError) as exc:
                    raise MineflayerEffectAdmissionError(
                        "invalid command under native checkpoint admission"
                    ) from exc
                if type(command) is not dict:
                    raise MineflayerEffectAdmissionError("invalid native command body")
                command_type = command.get("type")
                if command_type == "effect":
                    effect = command.get("effect")
                    if type(effect) is not str or not effect:
                        raise MineflayerEffectAdmissionError("untyped physical effect")
                    action_id = command.get("action_id")
                    if type(action_id) is not str or not action_id:
                        raise MineflayerEffectAdmissionError("missing physical action ID")
                elif command_type not in {"observe", "shutdown"}:
                    raise MineflayerEffectAdmissionError(
                        "unknown native command during coordinated checkpoint mode"
                    )
            if self._process.returncode is not None:
                raise MineflayerProcessEnded(
                    "cannot send to ended Mineflayer bridge; "
                    f"returncode={self._process.returncode}"
                )

            assert self._process.stdin is not None
            data = line.encode("utf-8")
            try:
                if gate is not None and command["type"] == "effect":
                    sender = self._atomic_effect_sender
                    if sender is None:
                        # Legacy non-PLACE sessions use their prior guard.
                        # The owned physical bridge installs atomic submission
                        # for genuine process-backed resident sessions.
                        gate(self.started.session_id, effect, action_id)
                        self._process.stdin.write(data)
                    else:
                        # No await between original lock-bound final admission
                        # and the synchronous final Native stdin buffer write.
                        sender(
                            self.started.session_id, effect, action_id,
                            lambda: self._process.stdin.write(data),
                        )
                else:
                    self._process.stdin.write(data)
                # Drain, ACK and Paper readback remain separate qualifications.
                # A write/drain error cannot be retried with this one-shot ID.
                await self._process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise MineflayerProcessIOError(
                    "could not write to Mineflayer bridge stdin"
                ) from exc

async def _terminate_child(process: asyncio.subprocess.Process) -> int:
    if process.returncode is None:
        process.terminate()
    return await process.wait()


def _require_positive_timeout(name: str, value: object) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value <= 0
    ):
        raise MineflayerProcessStartError(
            f"{name} must be a positive number"
        )
