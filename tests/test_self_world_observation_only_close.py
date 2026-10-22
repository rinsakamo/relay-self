"""W4 observation-only local close owner, fake processes only (no Java/Node)."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.self_world_observation_only_close import (
    close_observation_only_dev,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevSession,
)
from test_mineflayer_process_session import FakeProcess, started_line


def _wire(type_name: str, seq: int) -> bytes:
    data = {"type": type_name, "session_id": "session-1", "seq": seq}
    if type_name == "connection_end":
        data["reason"] = "fixture clean close"
    return (json.dumps(data) + "\n").encode()


@pytest.mark.parametrize("fault", (
    "none", "no_ack", "duplicate_ack", "java_stop_error",
    "java_pre_exited", "collector_fault", "node_missing", "java_missing",
    "node_shutdown_timeout", "java_stop_timeout",
))
def test_observation_only_close_settles_every_resource_offline(tmp_path, fault):
    node = FakeProcess([
        started_line(), *(
            [_wire("connection_end", 1)] if fault == "no_ack"
            else [_wire("shutdown_ack", 1), _wire("shutdown_ack", 2)]
            if fault == "duplicate_ack"
            else [_wire("shutdown_ack", 1), _wire("connection_end", 2)]
        ),
    ])
    java = FakeProcess([])
    if fault == "java_pre_exited":
        java.returncode = 0
    if fault == "java_stop_error":
        def fail_write(_value):
            raise OSError("fixture Java stdin failed")
        java.stdin.write = fail_write
    if fault == "java_stop_timeout":
        original_java_wait = java.wait
        java_wait_calls = 0

        async def slow_java_wait():
            nonlocal java_wait_calls
            java_wait_calls += 1
            if java_wait_calls == 1:
                await asyncio.Event().wait()
            return await original_java_wait()

        java.wait = slow_java_wait

    async def run():
        session = ObservationOnlyDevSession(node, raw_capture_root=tmp_path)
        await session.receive()
        if fault == "node_shutdown_timeout":
            async def stalled_node_shutdown(*, timeout_s):
                await asyncio.Event().wait()
            session.shutdown_with_stdout_receipt = stalled_node_shutdown
        async def drain_collector():
            await asyncio.sleep(0)
            if fault == "collector_fault":
                raise OSError("fixture raw collector write fault")
        collector = asyncio.create_task(drain_collector())
        result = await close_observation_only_dev(
            server=None if fault == "java_missing" else java,
            collector=collector,
            session=None if fault == "node_missing" else session,
            timeout_s=0.05 if fault in {"node_shutdown_timeout", "java_stop_timeout"} else 0.3,
        )
        assert result["schema"] == "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1"
        assert result["action_count"] == result["outcome_count"] == 0
        assert result["s10_update_count"] == 0
        assert not result["physical_run_permitted"]
        assert not result["science_qualified"]
        assert not result["external_custody_qualified"]
        assert collector.done()
        if fault == "none":
            assert result["classification"] == "LOCAL_PRODUCER_CLOSE_ONLY"
            assert result["errors"] == []
            assert result["java_stop_requested"]
            assert result["node_exit"] == 0 and result["java_exit"] == 0
            assert result["java_collector_settled"]
            assert result["node_stdout_receipt"]["shutdown_ack_count"] == 1
            assert java.stdin.writes == [b"stop\n"]
            assert node.stdin.writes == [b'{"type":"shutdown"}\n']
        else:
            assert result["classification"] == "LOCAL_CLOSE_UNCONFIRMED"
            assert result["errors"]
            if fault in ("no_ack", "duplicate_ack", "collector_fault"):
                assert java.stdin.writes == [b"stop\n"]
            if fault in {"java_stop_error", "java_stop_timeout"}:
                assert java.returncode is not None
                assert any(e.startswith("java_stop_") for e in result["errors"])
            if fault == "node_shutdown_timeout":
                assert any(e.startswith("node_stop_") for e in result["errors"])
                assert java.stdin.writes == [b"stop\\n"]
    asyncio.run(run())


def test_observation_only_close_rejects_wrong_owner_and_timeout():
    async def run():
        with pytest.raises(ValueError):
            await close_observation_only_dev(
                server=None, collector=None, session=object(),
            )
        with pytest.raises(ValueError):
            await close_observation_only_dev(
                server=None, collector=None, session=None, timeout_s=0,
            )
    asyncio.run(run())


def test_observation_only_close_supervises_repeated_cancellation_offline():
    """Caller cancellation cannot abandon the single owned Java STOP."""
    async def run():
        node = FakeProcess([])
        java = FakeProcess([])
        session = ObservationOnlyDevSession(node)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def controlled_shutdown(*, timeout_s):
            assert timeout_s == 0.5
            entered.set()
            await release.wait()
            node.returncode = 0
            return {
                "status": "COMPLETE_NODE_STDOUT",
                "shutdown_ack_count": 1,
                "eof_observed": True,
                "process_exit_code": 0,
                "seal_reason": "clean_shutdown",
            }
        session.shutdown_with_stdout_receipt = controlled_shutdown

        async def collector():
            await asyncio.sleep(0)

        collect_task = asyncio.create_task(collector())
        task = asyncio.create_task(close_observation_only_dev(
            server=java, collector=collect_task, session=session, timeout_s=0.5,
        ))
        await entered.wait()
        task.cancel()
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert java.stdin.writes == [b"stop\n"]
        assert java.returncode == 0
        assert collect_task.done()
    asyncio.run(run())
