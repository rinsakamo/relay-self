"""#860 DEV: bounded N-Self fan-out, full-roster ordered barrier, and fail-closed joins.

No individual worker is permitted to COMMIT, release admission, or issue an
Action. The caller owns one global physical/cognitive gate, kept closed until
ALL the indexed results are checked and the canonical generation is verified.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")
_MISSING = object()


class CohortParallelBarrierError(ValueError):
    """A worker cohort, limit or internal result is not fully qualified."""


def require_bounded_workers(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 64:
        raise CohortParallelBarrierError("parallel worker bound must be 1..64")
    return value


async def run_async_cohort_barrier(
    items: tuple[T, ...], fn: Callable[[T], Awaitable[R]], *,
    workers: int, total_timeout_s: float,
) -> tuple[R, ...]:
    """Fan out at most workers coroutines and join every result in roster order.

    If any worker fails, cancel the entire outstanding cohort and await all
    cancellations before returning failure. Physical STOP/issuer fencing
    happens outside and must remain HELD after cancellation. A cancellation
    may already have sent native STOP; the durable preissue WAL is retained.
    """
    import math

    require_bounded_workers(workers)
    if (
        type(items) is not tuple or not items or not callable(fn)
        or type(total_timeout_s) not in (int, float)
        or not math.isfinite(total_timeout_s)
        or not 0 < total_timeout_s <= 300
    ):
        raise CohortParallelBarrierError("invalid bounded cohort operation")
    values: list[object] = [_MISSING] * len(items)
    cursor = 0

    async def consume() -> None:
        nonlocal cursor
        while cursor < len(items):
            index = cursor
            cursor += 1
            values[index] = await fn(items[index])

    tasks = [
        asyncio.create_task(consume())
        for _ in range(min(workers, len(items)))
    ]
    try:
        async with asyncio.timeout(total_timeout_s):
            await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    if any(value is _MISSING for value in values):
        raise CohortParallelBarrierError("full cohort result missing")
    return tuple(values)  # type: ignore[return-value]


def run_sync_freeze_barrier(
    items: tuple[T, ...], fn: Callable[[T], R], *,
    workers: int,
) -> tuple[R, ...]:
    """Blocking bounded threads: all outstanding owner freezes JOIN on failure.

    Thread workers cannot be force-killed. On an exception, the pool waits
    for every started freeze to finish before returning to the checkpoint
    caller, which MUST HOLD the gate and MUST NOT save/restart Paper.
    No World callback or COMMIT happens inside this parallel section.
    """
    require_bounded_workers(workers)
    if type(items) is not tuple or not items or not callable(fn):
        raise CohortParallelBarrierError("invalid synchronous freeze cohort")
    if workers == 1:
        return tuple(fn(item) for item in items)
    with ThreadPoolExecutor(
        max_workers=min(workers, len(items)),
        thread_name_prefix="p0d-cognitive-freeze",
    ) as pool:
        futures = [pool.submit(fn, item) for item in items]
        results: list[R] = []
        try:
            for future in futures:
                results.append(future.result())
        except BaseException:
            for future in futures:
                future.cancel()
            # The executor context manager waits for in-flight callbacks.
            raise
    return tuple(results)
