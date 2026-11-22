from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerDecodedMessage,
    MineflayerLaunchConfig,
    MineflayerObservation,
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


@dataclass(frozen=True, slots=True)
class PassiveAggregation:
    """Cumulative omission bounds; timestamps are local receipt, not native time.

    The sequence interval may contain delivered messages; only the count is
    exact. Neither this summary nor the latest snapshot reconstructs history.
    """
    source: str
    first_replaced_seq: int
    last_replaced_seq: int
    latest_seq: int
    replaced_count: int
    first_received_monotonic: float
    latest_received_monotonic: float


@dataclass(frozen=True, slots=True)
class NativeReceiveContinuityHold:
    """Original stream's first unbounded receive-queue pressure witness.

    This receipt records a local receive boundary, not any Native/Paper
    acquisition timestamp. Requalification requires an original new session,
    not a consumer clearing this record.
    """

    source: str
    first_seq: int
    reason: str
    received_monotonic: float


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
        self._raw_source_audit_fd: int | None = None
        self._raw_source_audit_finished = False
        self._raw_command_audit_fd: int | None = None
        self._raw_command_audit_finished = False
        self._receive_active = False
        self._dispatch_task: asyncio.Task[None] | None = None
        self._dispatch_queue: asyncio.Queue[object] | None = None
        self._dispatch_observer: Callable[[MineflayerDecodedMessage], None] | None = None
        self._dispatch_error: Exception | None = None
        self.observer_error: Exception | None = None
        self._compact_safe: Callable[[], bool] | None = None
        self._preserve_all = False
        self.backpressure_hold = False
        self.passive_aggregation: PassiveAggregation | None = None
        self.native_continuity_hold: NativeReceiveContinuityHold | None = None
        self._tail_received_monotonic = 0.0

    @classmethod
    async def launch(
        cls,
        config: MineflayerLaunchConfig,
        *,
        bridge_path: str | Path | None = None,
        node_executable: str = "node",
        startup_timeout_s: float = 10.0,
    ) -> "MineflayerProcessSession":
        """Launch exactly one bridge process and consume its startup attestation."""

        _require_positive_timeout("startup_timeout_s", startup_timeout_s)
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
        return session

    @property
    def started(self) -> MineflayerAdapterStarted:
        if self._started is None:
            raise MineflayerProcessStartError(
                "Mineflayer session startup has not completed"
            )
        return self._started

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

    def start_raw_command_audit(self, path: str | Path) -> None:
        """Opt-in exact native stdin journal (predefined DEV observer only).

        This records the bytes actually passed through the original session
        after stdin.drain(), without adding a second native writer or issuer.
        Source evidence is independent from stdout: neither log alone proves
        the underlying game World.
        """
        if (self._started is None or self._raw_command_audit_fd is not None
                or self._raw_command_audit_finished):
            raise MineflayerProcessIOError("native command source audit already used")
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
        self._raw_command_audit_fd = fd

    def finish_raw_command_audit(self) -> None:
        """Freeze opt-in original stdin commands before SHA256 calculation."""
        fd = self._raw_command_audit_fd
        if fd is None or self._raw_command_audit_finished:
            raise MineflayerProcessIOError("native command source audit not active")
        os.fsync(fd)
        os.close(fd)
        self._raw_command_audit_fd = None
        self._raw_command_audit_finished = True

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

        if self._receive_active:
            raise MineflayerProcessIOError("concurrent native receive is forbidden")
        self._receive_active = True
        try:
            if self._dispatch_queue is None:
                return await self._read_native()
            while True:
                if not self._dispatch_queue.empty():
                    return self._dispatch_queue.get_nowait()  # type: ignore[return-value]
                if self._dispatch_error is not None:
                    raise self._dispatch_error
                if self._dispatch_task is not None and self._dispatch_task.done():
                    raise MineflayerProcessEnded("native dispatcher stopped")
                getter = asyncio.create_task(self._dispatch_queue.get())
                assert self._dispatch_task is not None
                try:
                    done, _ = await asyncio.wait(
                        (getter, self._dispatch_task), return_when=asyncio.FIRST_COMPLETED,
                    )
                    if getter in done:
                        return getter.result()  # type: ignore[return-value]
                finally:
                    if not getter.done():
                        getter.cancel()
        finally:
            self._receive_active = False

    def start_dispatcher(
        self, observer: Callable[[MineflayerDecodedMessage], None], *, capacity: int = 256,
        compact_safe: Callable[[], bool] | None = None,
    ) -> None:
        """Start one reader; backpressure preserves every owner message in order.

        The observer is a best-effort read-only notification, not World authority.
        A full owner queue pauses reading; no audit event is discarded.
        """
        if (self._started is None or self._dispatch_task is not None
                or self._receive_active or not callable(observer)
                or type(capacity) is not int or capacity < 1
                or (compact_safe is not None and not callable(compact_safe))):
            raise MineflayerProcessIOError("invalid or already active native dispatcher")
        self._dispatch_queue = asyncio.Queue(maxsize=capacity)
        self._dispatch_observer = observer
        self._compact_safe = compact_safe
        self._dispatch_task = asyncio.create_task(self._dispatch())

    async def _dispatch(self) -> None:
        assert self._dispatch_queue is not None
        assert self._dispatch_observer is not None
        batch = 0
        try:
            while True:
                message = await self._read_native()
                received_at = time.monotonic()
                self._observer_received_monotonic = received_at
                batch += 1
                if batch == 64:
                    batch = 0
                    await asyncio.sleep(0)
                try:
                    self._dispatch_observer(message)
                except Exception as exc:
                    self.observer_error = exc
                if self._dispatch_queue.full():
                    # A full queue means residence in the original native pipe
                    # cannot be bounded by Python receipt time. Even if a
                    # concurrent consumer immediately relieves pressure,
                    # current perception must HOLD until original reJOIN.
                    if self.native_continuity_hold is None:
                        self.native_continuity_hold = NativeReceiveContinuityHold(
                            source=message.session_id,
                            first_seq=message.seq,
                            reason="OWNER_QUEUE_FULL_UNKNOWN_PIPE_DELAY",
                            received_monotonic=received_at,
                        )
                if self._dispatch_queue.full() and self._can_compact(message):
                    tail = self._dispatch_queue._queue[-1]
                    if self._passive(tail):
                        prior = self.passive_aggregation
                        self.passive_aggregation = PassiveAggregation(
                            source=message.session_id,
                            first_replaced_seq=prior.first_replaced_seq if prior else tail.seq,
                            last_replaced_seq=tail.seq, latest_seq=message.seq,
                            replaced_count=(prior.replaced_count if prior else 0) + 1,
                            first_received_monotonic=(prior.first_received_monotonic if prior
                                                      else self._tail_received_monotonic),
                            latest_received_monotonic=received_at,
                        )
                        self._dispatch_queue._queue[-1] = message
                        self._tail_received_monotonic = received_at
                        continue
                self.backpressure_hold = self._dispatch_queue.full()
                try:
                    await self._dispatch_queue.put(message)
                    self._tail_received_monotonic = received_at
                finally:
                    self.backpressure_hold = False
        except Exception as exc:
            self._dispatch_error = exc

    @staticmethod
    def _passive(message: object) -> bool:
        return (isinstance(message, MineflayerObservation)
                and message.kind in {"move", "entities"} and message.request_id is None)

    def _can_compact(self, message: object) -> bool:
        if self._preserve_all or self._compact_safe is None or not self._passive(message):
            return False
        if not self._compact_safe():
            self._preserve_all = True
            return False
        return True

    async def _read_native(self) -> MineflayerDecodedMessage:
        """The only JSONL decoder and raw-source-audit path."""

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
        try:
            return await _terminate_child(self._process)
        finally:
            if self._dispatch_task is not None and not self._dispatch_task.done():
                self._dispatch_task.cancel()
                try:
                    await self._dispatch_task
                except asyncio.CancelledError:
                    pass

    async def _send(self, line: str) -> None:
        # Even without the optional admission gate, a native effect ends the
        # passive-only period permanently for this session.
        try:
            if json.loads(line).get("type") == "effect":
                self._preserve_all = True
        except (ValueError, AttributeError):
            pass
        gate = getattr(self, "_effect_admission", None)
        if gate is not None:
            # Check at final native stdin, not only at send_* wrappers.
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
                gate(self.started.session_id, effect, action_id)
                # Keep every subsequent observation, including delayed settling.
                self._preserve_all = True
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
        try:
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise MineflayerProcessIOError(
                "could not write to Mineflayer bridge stdin"
            ) from exc
        fd = self._raw_command_audit_fd
        if fd is not None:
            # Loss of command evidence AFTER delivery is an unresolved
            # observation, not permission to claim a clean successful trial.
            try:
                raw = line.encode("utf-8")
                if os.write(fd, raw) != len(raw):
                    raise OSError("partial Native command evidence write")
                os.fsync(fd)
            except OSError as exc:
                raise MineflayerProcessIOError(
                    "original Native stdin command evidence unavailable"
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
