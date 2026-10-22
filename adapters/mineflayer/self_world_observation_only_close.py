"""W4 observation-only DEV teardown owner, with no World launcher or grant.

Reuses the one Node owner + original Java process and collector. All process
evidence is LOCAL OS/producer content; not a qualification, scientific run
or independent PID/reap witness. The function never issues an Action.
"""
from __future__ import annotations

import asyncio
from typing import Any

from adapters.mineflayer.s31a_real_server_ci import _command
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevSession,
)
from adapters.mineflayer.startup_process_ownership import (
    StartupCleanupUnconfirmed,
    _supervise,
    terminate_and_reap,
)


async def close_observation_only_dev(
    *, server: Any, collector: asyncio.Task[None] | None,
    session: ObservationOnlyDevSession | None,
    timeout_s: float = 5.0,
) -> dict[str, object]:
    """Settle Node, Java and Java collector once, including on teardown fault.

    A physical caller must supervise this single call in finally and persist
    the returned failure report separately; this helper alone is not an
    independently owned World admission or custody receipt.
    """
    if (
        type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30
        or (session is not None and type(session) is not ObservationOnlyDevSession)
    ):
        raise ValueError("owned observation-only handles and timeout required")
    result: dict[str, object] = {
        "schema": "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1",
        "classification": "LOCAL_CLOSE_UNCONFIRMED",
        "node_exit": None,
        "java_exit": None,
        "node_stdout_receipt": None,
        "java_collector_settled": False,
        "java_stop_requested": False,
        "errors": [],
        "action_count": 0,
        "outcome_count": 0,
        "s10_update_count": 0,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "science_qualified": False,
    }
    errors: list[str] = result["errors"]  # type: ignore[assignment]

    async def close_once() -> None:
        # Node first: no host has any authority to issue further commands.
        if session is None:
            errors.append("node_missing")
        else:
            try:
                receipt = await asyncio.wait_for(
                    session.shutdown_with_stdout_receipt(timeout_s=timeout_s),
                    timeout=timeout_s + 1,
                )
                result["node_exit"] = session.process_returncode
                result["node_stdout_receipt"] = receipt
            except BaseException as exc:
                errors.append(f"node_stop_{type(exc).__name__}")
                try:
                    result["node_exit"] = await terminate_and_reap(
                        session._process, timeout_s=timeout_s,
                    )
                except BaseException as secondary:
                    errors.append(f"node_reap_{type(secondary).__name__}")
        # Always continue to Java even if Node cleanup or evidence failed.
        if server is None:
            errors.append("java_missing")
        else:
            if server.returncode is None:
                try:
                    _command(server, "stop")  # Original Java experimenter stdin.
                    assert server.stdin is not None
                    await server.stdin.drain()
                    result["java_stop_requested"] = True
                    result["java_exit"] = await asyncio.wait_for(
                        server.wait(), timeout=timeout_s,
                    )
                except BaseException as exc:
                    errors.append(f"java_stop_{type(exc).__name__}")
            else:
                errors.append("java_exited_before_stop")
            # Even on stop failure require a termination/reap, never infer it.
            if result["java_exit"] is None:
                try:
                    result["java_exit"] = await terminate_and_reap(
                        server, timeout_s=timeout_s,
                    )
                except BaseException as exc:
                    errors.append(f"java_reap_{type(exc).__name__}")
        if collector is None:
            errors.append("java_collector_missing")
        else:
            done, _ = await asyncio.wait({collector}, timeout=timeout_s)
            if not done:
                collector.cancel()
                done, _ = await asyncio.wait({collector}, timeout=0.25)
                errors.append("java_collector_timeout")
            if done:
                try:
                    collector.result()
                    result["java_collector_settled"] = True
                except BaseException as exc:
                    errors.append(f"java_collector_{type(exc).__name__}")
            else:
                # Never convert an uncooperative pending task to settled.
                collector.add_done_callback(
                    lambda task: None if task.cancelled() else task.exception()
                )
                errors.append("java_collector_unconfirmed")
        if (
            not errors and result["node_exit"] == 0 and result["java_exit"] == 0
            and result["java_stop_requested"] is True
            and result["java_collector_settled"] is True
        ):
            result["classification"] = "LOCAL_PRODUCER_CLOSE_ONLY"
        else:
            result["classification"] = "LOCAL_CLOSE_UNCONFIRMED"

    # The pre-existing startup supervisor continues the exact cleanup task
    # through repeated caller cancellations, then re-raises cancellation.
    await _supervise(close_once())
    return result
