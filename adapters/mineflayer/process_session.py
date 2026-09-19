from __future__ import annotations

import asyncio
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerDecodedMessage,
    MineflayerLaunchConfig,
    MineflayerStreamDecoder,
    encode_clear_controls,
    encode_consume_held,
    encode_equip_item,
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
