"""Bounded subprocess startup custody for the S31A/S49 Java and Node helpers.

This module is a small helper, not another process/observation owner. A spawn
task retains custody until a Process is returned or conclusively fails. No
second stdout receiver or background cleanup task survives a successful return.
"""

from __future__ import annotations

import asyncio


class StartupCleanupUnconfirmed(RuntimeError):
    """Spawned child exit/reap could not be confirmed."""


def _mark_unconfirmed(cancel: asyncio.CancelledError, error: BaseException) -> None:
    setattr(cancel, "startup_cleanup_unconfirmed", f"{type(error).__name__}: {error}")
    cancel.add_note(f"startup cleanup/custody unconfirmed: {error!r}")


async def _supervise(awaitable):
    """Keep one cleanup task under supervision through repeated caller cancels."""
    task = asyncio.create_task(awaitable)
    cancelled: asyncio.CancelledError | None = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            if cancelled is None:
                cancelled = exc
    value = task.result()
    if cancelled is not None:
        raise cancelled
    return value


async def terminate_and_reap(process: asyncio.subprocess.Process, *, timeout_s: float = 5.0) -> int:
    """Terminate, escalate to kill when necessary, and require a confirmed reap.

    Works during startup cancellation as well as startup exceptions. A second
    caller cancellation does not orphan the one teardown task.
    """
    async def close() -> int:
        signal_error: BaseException | None = None
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass  # May have exited before the signal; still must wait.
            except Exception as exc:
                signal_error = exc
        try:
            result = await asyncio.wait_for(process.wait(), timeout=timeout_s)
        except (Exception, asyncio.CancelledError) as first_wait_error:
            # The first wait can time out, fail, or be fault-injected. Never
            # declare that an attempted signal is a confirmed process exit.
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                except Exception as exc:
                    signal_error = exc
            try:
                result = await asyncio.wait_for(process.wait(), timeout=timeout_s)
            except (Exception, asyncio.CancelledError) as second_wait_error:
                raise StartupCleanupUnconfirmed(
                    "kill/reap did not confirm process exit; "
                    f"first_wait={first_wait_error!r}, "
                    f"signal={signal_error!r}, second_wait={second_wait_error!r}"
                ) from second_wait_error
        if type(result) is not int or type(process.returncode) is not int:
            raise StartupCleanupUnconfirmed("process wait did not confirm an integer exit code")
        return result

    return await _supervise(close())


async def spawn_with_custody(*argv, **kwargs) -> asyncio.subprocess.Process:
    """Do not deliver cancellation between OS spawn and Process handoff.

    The shielded spawn task owns a newly created child until this function can
    return its handle to the caller. If the caller cancels, the same task is
    awaited to completion and any produced child is terminated and reaped.
    """
    spawn = asyncio.create_task(asyncio.create_subprocess_exec(*argv, **kwargs))
    cancelled: asyncio.CancelledError | None = None
    while not spawn.done():
        try:
            await asyncio.shield(spawn)
        except asyncio.CancelledError as exc:
            if cancelled is None:
                cancelled = exc
    try:
        process = spawn.result()
    except BaseException as exc:
        if cancelled is not None:
            _mark_unconfirmed(cancelled, exc)
            raise cancelled from exc
        raise
    if cancelled is not None:
        try:
            await terminate_and_reap(process)
        except BaseException as exc:
            if type(process.returncode) is not int:
                _mark_unconfirmed(cancelled, exc)
            raise cancelled from exc
        raise cancelled
    return process
