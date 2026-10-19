from __future__ import annotations

import asyncio
from pathlib import Path

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
from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture


class MineflayerProcessError(RuntimeError):
    """Base error for the target-local Mineflayer child process."""


class MineflayerProcessStartError(MineflayerProcessError):
    """Raised when the Mineflayer bridge cannot establish a valid session."""


class MineflayerProcessEnded(MineflayerProcessError):
    """Raised when the child process stream ends before a requested message."""


class MineflayerProcessIOError(MineflayerProcessError):
    """Raised when JSONL input cannot be delivered to the child process."""


class MineflayerProcessSession:
    """Own one Node/Mineflayer bridge process without adding Self semantics."""

    def __init__(
        self, process: asyncio.subprocess.Process, *,
        raw_capture_root: Path | None = None,
    ) -> None:
        if process.stdin is None or process.stdout is None:
            raise MineflayerProcessStartError(
                "Mineflayer child process requires stdin and stdout pipes"
            )
        self._process = process
        self._decoder = MineflayerStreamDecoder()
        self._started: MineflayerAdapterStarted | None = None
        self._raw_capture = (
            W3RawNodeStdoutCapture(raw_capture_root)
            if raw_capture_root is not None else None
        )
        self._raw_receipt: dict[str, object] | None = None

    @classmethod
    async def launch(
        cls,
        config: MineflayerLaunchConfig,
        *,
        bridge_path: str | Path | None = None,
        node_executable: str = "node",
        startup_timeout_s: float = 10.0,
        raw_capture_root: Path | None = None,
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
            session = cls(process, raw_capture_root=raw_capture_root)
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

    @property
    def process_returncode(self) -> int | None:
        return self._process.returncode

    @property
    def raw_capture_receipt(self) -> dict[str, object] | None:
        return self._raw_receipt

    async def receive(self) -> MineflayerDecodedMessage:
        """Read and validate exactly one target-local JSONL message."""

        assert self._process.stdout is not None
        line = await self._process.stdout.readline()
        if not line:
            if self._raw_capture is not None:
                self._raw_capture.mark_eof()
            raise MineflayerProcessEnded(
                "Mineflayer bridge stdout ended; "
                f"returncode={self._process.returncode}"
            )
        if self._raw_capture is not None:
            self._raw_capture.append_before_decode(line)
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            if self._raw_capture is not None:
                self._raw_capture.mark_decode_failure()
            raise MineflayerProcessIOError(
                "Mineflayer bridge emitted non-UTF-8 stdout"
            ) from exc
        try:
            message = self._decoder.decode(text)
        except ValueError:
            if self._raw_capture is not None:
                self._raw_capture.mark_decode_failure()
            raise
        if self._raw_capture is not None:
            self._raw_capture.after_decoder(
                session_id=message.session_id, seq=message.seq,
                message_type=(
                    "adapter_started" if isinstance(message, MineflayerAdapterStarted)
                    else "shutdown_ack" if type(message).__name__ == "MineflayerShutdownAck"
                    else type(message).__name__
                ),
            )
        return message

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
        """Legacy probe when absent; correlated observe on explicit request ID."""
        await self._send(encode_observe(request_id))

    async def shutdown(self, *, timeout_s: float = 5.0) -> int:
        """Request one clean bridge shutdown, with bounded termination fallback."""

        _require_positive_timeout("timeout_s", timeout_s)
        if self._raw_capture is None:
            if self._process.returncode is not None:
                return self._process.returncode
            await self._send(encode_shutdown())
            try:
                return await asyncio.wait_for(
                    self._process.wait(), timeout=timeout_s,
                )
            except TimeoutError as exc:
                await self.terminate()
                raise MineflayerProcessEnded(
                    "Mineflayer bridge did not exit after shutdown request"
                ) from exc

        # Capture-only path: drain all Node stdout through the same decoder
        # until EOF so the shutdown_ack and trailing messages are not lost.
        # No second event consumer is introduced during S49 active control.
        try:
            if self._process.returncode is None:
                await self._send(encode_shutdown())
            async def until_eof() -> None:
                while True:
                    try:
                        await self.receive()
                    except MineflayerProcessEnded:
                        return
            await asyncio.wait_for(until_eof(), timeout=timeout_s)
            rc = await asyncio.wait_for(self._process.wait(), timeout=timeout_s)
            self._seal_raw_capture(exit_code=rc, reason="clean_shutdown")
            return rc
        except Exception:
            await _terminate_child(self._process)
            self._seal_raw_capture(
                exit_code=self._process.returncode, reason="aborted_shutdown",
            )
            raise

    def _seal_raw_capture(self, *, exit_code: int | None, reason: str) -> None:
        if self._raw_capture is not None and self._raw_receipt is None:
            self._raw_receipt = self._raw_capture.seal(
                exit_code=exit_code, reason=reason,
            )

    async def terminate(self) -> int:
        """Terminate the owned child without retrying or launching a replacement."""
        rc = await _terminate_child(self._process)
        self._seal_raw_capture(exit_code=rc, reason="terminated")
        return rc

    async def _send(self, line: str) -> None:
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
