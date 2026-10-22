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


async def _bounded_wait(awaitable, *, timeout_s: float, name: str):
    """Bound even a wait coroutine which ignores its cancellation request.

    wait_for() can wait *past* its timeout for an uncooperative coroutine.
    Do not let a synthetic or buggy child waiter hold cleanup indefinitely.
    """
    waiter = asyncio.create_task(awaitable)
    done, _ = await asyncio.wait({waiter}, timeout=timeout_s)
    if not done:
        waiter.cancel()
        settled, _ = await asyncio.wait({waiter}, timeout=0.25)
        if not settled:
            # The pending waiter remains unconfirmed: do not call it reaped.
            waiter.add_done_callback(lambda task: task.exception() if not task.cancelled() else None)
            raise StartupCleanupUnconfirmed(f"{name} ignored cancellation after timeout")
        try:
            waiter.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        raise TimeoutError(f"{name} timed out")
    return waiter.result()


async def terminate_and_reap(process: asyncio.subprocess.Process, *, timeout_s: float = 5.0) -> int:
    """Terminate, escalate to kill, then require a confirmed reap.

    The stop/kill path is supervised across repeated caller cancellation.
    A stuck wait task never turns a known signal into a claimed reap.
    """
    if type(timeout_s) not in (int, float) or timeout_s <= 0:
        raise ValueError("positive bounded process timeout required")

    async def close() -> int:
        signal_error: BaseException | None = None
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            except Exception as exc:
                signal_error = exc
        first_wait_error: BaseException | None = None
        try:
            result = await _bounded_wait(process.wait(), timeout_s=timeout_s, name="terminate wait")
        except (Exception, asyncio.CancelledError) as exc:
            first_wait_error = exc
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                except Exception as signal_exc:
                    signal_error = signal_exc
            try:
                result = await _bounded_wait(process.wait(), timeout_s=timeout_s, name="kill wait")
            except (Exception, asyncio.CancelledError) as second_wait_error:
                raise StartupCleanupUnconfirmed(
                    "kill/reap did not confirm process exit; "
                    f"first_wait={first_wait_error!r}, "
                    f"signal={signal_error!r}, second_wait={second_wait_error!r}"
                ) from second_wait_error
        if type(result) is not int or type(process.returncode) is not int:
            raise StartupCleanupUnconfirmed("process wait did not confirm an integer exit code")
        if result != process.returncode:
            raise StartupCleanupUnconfirmed(
                "process wait result disagrees with process returncode: "
                f"wait={result}, returncode={process.returncode}"
            )
        if isinstance(first_wait_error, StartupCleanupUnconfirmed):
            # Another wait task still exists; even a later integer rc cannot
            # attest full waiter settlement/cleanup.
            raise StartupCleanupUnconfirmed(
                f"process exited but prior wait remains unconfirmed: {first_wait_error}"
            )
        return result

    return await _supervise(close())


async def spawn_with_custody(*argv, **kwargs) -> asyncio.subprocess.Process:
    """Do not deliver cancellation between OS spawn and Process handoff.

    The shielded spawn task owns a newly created child until this function can
    return its handle to the caller. If the caller cancels, the same task is
    awaited to completion and any produced child is terminated and reaped.
    """
    caller = asyncio.current_task()
    if caller is not None and caller.cancelling():
        # No child should be spawned if cancellation was already requested.
        raise asyncio.CancelledError
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
            # A recorded returncode alone is not custody proof: wait/reap may
            # have failed or an earlier waiter/collector may remain pending.
            _mark_unconfirmed(cancelled, exc)
            raise cancelled from exc
        raise cancelled
    return process
