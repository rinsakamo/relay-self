"""#860 DEV: own and cycle one explicitly launched Paper process for autosave.

No discovery, attachment to an already-running server, World/LLM control, or
Action grant. Paper stop/save receipts are process/log evidence, NOT proof that
World + all Self owners share an atomic or semantically complete checkpoint.
"""
from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from relay_self.coordinated_autosave_runtime_dev import (
    RestartedWorldReceipt,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)


class OwnedPaperError(RuntimeError):
    """Refuse to control an unowned or uncertain Minecraft server process."""


@dataclass(frozen=True, slots=True)
class PaperTickReceipt:
    """Server-source tick witness; caller must supply a real authenticated probe."""

    server_session_id: str
    tick: int
    source_ref: str


class OwnedPaperWorld:
    """Bounded synchronous Paper lifecycle for a disposable dedicated server.

    This class only sends console commands to its own Popen stdin. It never
    discovers ports/PIDs or sends signals to another Minecraft server.
    """

    def __init__(
        self, *, server_dir: Path, world_dir: Path, evidence_dir: Path,
        command: tuple[str, ...], world_id: str, branch_id: str,
        tick_readback: Callable[[str], PaperTickReceipt],
        ready_marker: str = "Done (",
        save_marker: str = "Saved the game",
        shutdown_marker: str = "Stopping server",
        timeout_seconds: float = 30.0,
    ) -> None:
        for value in (world_id, branch_id, ready_marker, save_marker, shutdown_marker):
            if type(value) is not str or not value:
                raise OwnedPaperError("explicit World identity and log markers required")
        if (type(command) is not tuple or not command
                or any(type(x) is not str or not x for x in command)):
            raise OwnedPaperError("explicit executable and arguments required")
        if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 180:
            raise OwnedPaperError("bounded start/stop timeout required")
        self.server_dir = Path(server_dir).resolve(strict=True)
        self.world_dir = Path(world_dir).resolve(strict=True)
        self.evidence_dir = Path(evidence_dir).resolve(strict=True)
        if (
            not self.server_dir.is_dir() or not self.world_dir.is_dir()
            or not self.evidence_dir.is_dir()
            or not self.world_dir.is_relative_to(self.server_dir)
            or not (self.world_dir / "level.dat").is_file()
        ):
            raise OwnedPaperError("existing controlled server and World directories required")
        self.command = command
        self.world_id = world_id
        self.branch_id = branch_id
        self.tick_readback = tick_readback
        self.ready_marker = ready_marker.encode("utf-8")
        self.save_marker = save_marker.encode("utf-8")
        self.shutdown_marker = shutdown_marker.encode("utf-8")
        self.timeout_seconds = float(timeout_seconds)
        self._process: subprocess.Popen[bytes] | None = None
        self._session_id: str | None = None
        self._log_path: Path | None = None
        self._uncertain = False

    def _assert_owned(self) -> subprocess.Popen[bytes]:
        if self._uncertain or self._process is None or self._session_id is None:
            raise OwnedPaperError("no unambiguously owned active server")
        if self._process.poll() is not None:
            self._uncertain = True
            raise OwnedPaperError("owned server exited unexpectedly")
        return self._process

    def _read_log(self) -> bytes:
        if self._log_path is None or self._log_path.is_symlink():
            raise OwnedPaperError("owned process log unavailable")
        return self._log_path.read_bytes()

    def read_owned_log(self, session_id: str) -> bytes:
        """Read only the log attached to THIS explicitly running Paper Popen.

        This supports matching the Paper main-thread tick ACK to the owning
        process, rather than accepting a foreign/global server.log claim.
        """
        self._assert_owned()
        if session_id != self._session_id:
            raise OwnedPaperError("foreign Paper process session log")
        return self._read_log()

    def start_owned(self) -> str:
        """Launch only the explicitly configured executable in a NEW process."""
        if self._uncertain or self._process is not None:
            raise OwnedPaperError("refusing to attach to or duplicate existing server")
        session = "paper-owned-" + str(uuid.uuid4())
        log_path = self.evidence_dir / (session + ".log")
        with log_path.open("xb") as log_stream:
            try:
                proc = subprocess.Popen(
                    self.command, cwd=self.server_dir, stdin=subprocess.PIPE,
                    stdout=log_stream, stderr=subprocess.STDOUT, shell=False,
                )
            except OSError as exc:
                raise OwnedPaperError("configured Paper process failed to launch") from exc
        self._process = proc
        self._session_id = session
        self._log_path = log_path
        (self.evidence_dir / (session + ".pid")).write_text(str(proc.pid) + "\n")
        deadline = time.monotonic() + self.timeout_seconds
        try:
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise OwnedPaperError("Paper process exited before readiness")
                if self.ready_marker in self._read_log():
                    return session
                time.sleep(0.02)
            raise OwnedPaperError("Paper readiness marker not observed before deadline")
        except Exception:
            # Process might still run. No blind kill or implicit restart.
            self._uncertain = True
            raise

    def stop_and_save(self) -> StoppedWorldReceipt:
        proc = self._assert_owned()
        session = self._session_id
        assert session is not None
        try:
            tick = self.tick_readback(session)
        except Exception as exc:
            # The server is still running, but this attempted save has lost
            # independent source timing. Never continue with a second cut.
            self._uncertain = True
            raise OwnedPaperError("owned Paper source tick readback failed; HOLD") from exc
        if (
            not isinstance(tick, PaperTickReceipt)
            or tick.server_session_id != session
            or type(tick.tick) is not int or tick.tick < 0
            or type(tick.source_ref) is not str or not tick.source_ref.strip()
        ):
            self._uncertain = True
            raise OwnedPaperError("fresh server-qualified tick readback required")
        if proc.stdin is None:
            raise OwnedPaperError("owned Paper console stdin missing")
        try:
            offset = len(self._read_log())
            proc.stdin.write(b"save-all flush\n")
            proc.stdin.flush()
            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise OwnedPaperError("Paper exited before flush completion")
                if self.save_marker in self._read_log()[offset:]:
                    break
                time.sleep(0.02)
            else:
                raise OwnedPaperError("Paper flush completion not observed; HOLD")
            proc.stdin.write(b"stop\n")
            proc.stdin.flush()
            returncode = proc.wait(timeout=self.timeout_seconds)
        except OwnedPaperError:
            self._uncertain = True
            raise
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._uncertain = True
            raise OwnedPaperError("Paper save/stop did not complete cleanly") from exc
        finally:
            if proc.poll() is not None and proc.stdin is not None:
                proc.stdin.close()
        log = self._read_log()
        self._process = None
        self._session_id = None
        if (
            returncode != 0 or self.save_marker not in log
            or self.shutdown_marker not in log
        ):
            self._uncertain = True
            raise OwnedPaperError("Paper exit/log lacks clean save evidence")
        if not (self.world_dir / "level.dat").is_file():
            self._uncertain = True
            raise OwnedPaperError("World was not present after Paper stop")
        return StoppedWorldReceipt(
            world_id=self.world_id,
            branch_id=self.branch_id,
            old_server_session_id=session,
            logical_tick=tick.tick,
            tick_source_ref=tick.source_ref,
            stopped_server_ref="owned-process-log:" + str(self._log_path),
            process_exit_code=returncode,
            all_dimensions_saved=True,  # DEV log/exit corroboration, not atomicity.
        )

    def restart_same_source_world(self) -> RestartedWorldReceipt:
        if self._process is not None or self._uncertain:
            raise OwnedPaperError("Paper cannot restart from uncertain state")
        session = self.start_owned()
        return RestartedWorldReceipt(
            world_id=self.world_id, branch_id=self.branch_id,
            new_server_session_id=session, server_started=True,
        )

    def runtime_hooks(self) -> WorldRuntimeHooks:
        return WorldRuntimeHooks(
            stop_and_save=self.stop_and_save,
            restart_same_source_world=self.restart_same_source_world,
        )

    @property
    def owned_session_id(self) -> str | None:
        return self._session_id

    @property
    def held_uncertain(self) -> bool:
        return self._uncertain
