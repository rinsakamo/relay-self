"""Synthetic DEV-only tests for Java/Node launch custody (no real World)."""

import asyncio
from pathlib import Path

import pytest

from adapters.mineflayer import s31a_real_server_ci as s31a
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.startup_process_ownership import (
    StartupCleanupUnconfirmed,
    spawn_with_custody,
    terminate_and_reap,
)


class FakeStdin:
    def write(self, data):
        del data

    async def drain(self):
        pass


class FakeStdout:
    def __init__(self, *, ready=False):
        self.ready = ready
        self.read_started = asyncio.Event()

    async def readline(self):
        self.read_started.set()
        if self.ready:
            self.ready = False
            return b"[Server thread/INFO]: Done (1.5s)! For help, type \"help\"\\n"
        await asyncio.Event().wait()


class FakeProcess:
    def __init__(self, *, ready=False, blocked_reap=False):
        self.pid = 49123
        self.returncode = None
        self.stdin = FakeStdin()
        self.stdout = FakeStdout(ready=ready)
        self.terminated = 0
        self.killed = 0
        self.reaped = 0
        self.wait_started = asyncio.Event()
        self.release_reap = asyncio.Event()
        self.blocked_reap = blocked_reap
        self.fail_first_wait = False

    def terminate(self):
        self.terminated += 1
        self.returncode = -15

    def kill(self):
        self.killed += 1
        self.returncode = -9

    async def wait(self):
        self.wait_started.set()
        if self.fail_first_wait:
            self.fail_first_wait = False
            self.returncode = None
            raise RuntimeError("injected wait failure")
        if self.blocked_reap:
            await self.release_reap.wait()
        self.reaped += 1
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def _node_args(tmp_path: Path):
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("// synthetic fixture", encoding="utf-8")
    return {"bridge_path": bridge, "startup_timeout_s": 1.0}


def test_spawn_preflight_error_has_no_child(monkeypatch):
    launches = []

    async def broken(*args, **kwargs):
        launches.append((args, kwargs))
        raise OSError("no process")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", broken)

    async def run():
        with pytest.raises(OSError, match="no process"):
            await spawn_with_custody("never")
        assert len(launches) == 1

    asyncio.run(run())


@pytest.mark.parametrize("target", ["node", "java"])
def test_cancel_during_spawn_reaps_child_once(monkeypatch, tmp_path, target):
    async def run():
        process = FakeProcess()
        entering = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def spawn(*args, **kwargs):
            calls.append((args, kwargs))
            entering.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        if target == "node":
            operation = MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), **_node_args(tmp_path),
            )
        else:
            operation = s31a._ready_server(
                tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log",
            )
        owner = asyncio.create_task(operation)
        await entering.wait()
        owner.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert len(calls) == 1
        assert process.terminated == 1
        assert process.reaped == 1
        assert process.returncode == -15

    asyncio.run(run())


def test_node_cancel_while_receiving_started_reaps_child(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess()

        async def spawn(*a, **kw):
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        owner = asyncio.create_task(
            MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), **_node_args(tmp_path),
            )
        )
        await process.stdout.read_started.wait()
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert process.terminated == 1
        assert process.reaped == 1

    asyncio.run(run())


def test_node_constructor_failure_reaps_without_session(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess()

        async def spawn(*a, **kw):
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        def broken_init(self, *a, **kw):
            raise ValueError("injected constructor failure")
        monkeypatch.setattr(MineflayerProcessSession, "__init__", broken_init)
        with pytest.raises(ValueError, match="constructor"):
            await MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), **_node_args(tmp_path),
            )
        assert process.terminated == 1
        assert process.reaped == 1

    asyncio.run(run())


def test_java_readiness_cancel_settles_original_collector(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess()
        async def spawn(*a, **kw):
            return process
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        owner = asyncio.create_task(
            s31a._ready_server(tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log")
        )
        await process.stdout.read_started.wait()
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert process.terminated == 1
        assert process.reaped == 1
        assert process.returncode == -15

    asyncio.run(run())


@pytest.mark.parametrize("target", ["node", "java"])
def test_secondary_cancel_during_reap_does_not_orphan(monkeypatch, tmp_path, target):
    async def run():
        process = FakeProcess(blocked_reap=True)
        entering = asyncio.Event()
        release = asyncio.Event()

        async def spawn(*a, **kw):
            entering.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        if target == "node":
            operation = MineflayerProcessSession.launch(
                MineflayerLaunchConfig(), **_node_args(tmp_path),
            )
        else:
            operation = s31a._ready_server(
                tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log",
            )
        owner = asyncio.create_task(operation)
        await entering.wait()
        owner.cancel()
        release.set()
        await process.wait_started.wait()
        owner.cancel()
        process.release_reap.set()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert process.reaped == 1
        assert process.returncode == -15

    asyncio.run(run())


def test_java_task_creation_failure_reaps_before_handoff(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess()
        original = asyncio.create_task

        async def spawn(*a, **kw):
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

        def create(coro, *args, **kwargs):
            if getattr(coro, "__qualname__", "").endswith(".collect"):
                coro.close()
                raise RuntimeError("injected collector constructor failure")
            return original(coro, *args, **kwargs)

        monkeypatch.setattr(asyncio, "create_task", create)
        with pytest.raises(RuntimeError, match="collector constructor"):
            await s31a._ready_server(tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log")
        assert process.terminated == 1
        assert process.reaped == 1

    asyncio.run(run())


def test_java_normal_ready_handoff_preserves_single_collector(monkeypatch, tmp_path):
    async def run():
        process = FakeProcess(ready=True)
        async def spawn(*a, **kw):
            return process
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        server, collector, ready = await s31a._ready_server(
            tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log",
        )
        assert server is process
        assert ready.is_set()
        assert process.terminated == 0
        assert process.reaped == 0
        # Test is now the sole caller/owner of a successfully handed-off
        # session; settle it explicitly without a second stdout consumer.
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            pass
        await terminate_and_reap(process)
        assert process.reaped == 1

    asyncio.run(run())


def test_wait_fault_escalates_to_kill_and_reaps():
    async def run():
        process = FakeProcess()
        process.fail_first_wait = True
        rc = await terminate_and_reap(process)
        assert rc == -9
        assert process.killed == 1
        assert process.reaped == 1

    asyncio.run(run())


def test_no_exit_confirmation_fails_closed():
    async def run():
        process = FakeProcess()
        async def bad_wait():
            process.returncode = None
            raise RuntimeError("never reaped")
        process.wait = bad_wait
        with pytest.raises(StartupCleanupUnconfirmed, match="kill/reap"):
            await terminate_and_reap(process)
        assert process.killed == 1
        assert process.returncode is None  # signal is NOT a successful reap

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["cancel", "exception", "secondary_cancel"])
def test_native_spawn_after_adapter_started_stays_owned(monkeypatch, tmp_path, fault):
    from adapters.mineflayer import s34_native_world_cognition_ci as s34

    async def run():
        process = FakeProcess(blocked_reap=fault == "secondary_cancel")
        session = MineflayerProcessSession(process, raw_capture_root=tmp_path)
        entered = asyncio.Event()

        async def fake_launch(cls, *args, **kwargs):
            return session

        async def fake_native_spawn(existing):
            assert existing is session
            entered.set()
            if fault == "exception":
                raise RuntimeError("native spawn fault")
            await asyncio.Event().wait()

        monkeypatch.setattr(
            s34.MineflayerProcessSession, "launch", classmethod(fake_launch),
        )
        monkeypatch.setattr(s34, "_await_spawn", fake_native_spawn)
        owner = asyncio.create_task(s34._new_session(raw_capture_root=tmp_path))
        await entered.wait()
        if fault == "exception":
            with pytest.raises(RuntimeError, match="native spawn fault"):
                await owner
        else:
            owner.cancel()
            if fault == "secondary_cancel":
                await process.wait_started.wait()
                owner.cancel()
                process.release_reap.set()
            with pytest.raises(asyncio.CancelledError):
                await owner
        assert process.terminated == 1
        assert process.reaped == 1
        assert process.returncode == -15
        receipt_path = tmp_path / "w3-node-stdout-receipt.json"
        assert receipt_path.is_file()
        import json
        receipt = json.loads(receipt_path.read_text())
        assert receipt["status"] == "INCOMPLETE_UNQUALIFIED"
        assert receipt["eof_observed"] is False

    asyncio.run(run())


def test_native_spawn_success_transfers_without_early_reap(monkeypatch):
    from adapters.mineflayer import s34_native_world_cognition_ci as s34

    async def run():
        process = FakeProcess()
        session = MineflayerProcessSession(process)

        async def fake_launch(cls, *args, **kwargs):
            return session

        async def fake_native_spawn(existing):
            assert existing is session

        monkeypatch.setattr(
            s34.MineflayerProcessSession, "launch", classmethod(fake_launch),
        )
        monkeypatch.setattr(s34, "_await_spawn", fake_native_spawn)
        actual = await s34._new_session()
        assert actual is session
        assert process.terminated == 0
        assert process.reaped == 0
        await actual.abort_startup()
        assert process.reaped == 1

    asyncio.run(run())


def test_uncooperative_java_collector_fails_closed_without_waiting_forever(
    monkeypatch, tmp_path,
):
    """A reader suppressing cancellation cannot certify successful cleanup."""
    async def run():
        process = FakeProcess()
        entered = asyncio.Event()
        release = asyncio.Event()
        original_create = asyncio.create_task
        collectors = []

        class ResistantStdout:
            async def readline(self):
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    await release.wait()
                return b""

        process.stdout = ResistantStdout()

        async def fake_spawn(*args, **kwargs):
            return process

        def track_create(coro, *args, **kwargs):
            task = original_create(coro, *args, **kwargs)
            if getattr(coro, "__qualname__", "").endswith(".collect"):
                collectors.append(task)
            return task

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
        monkeypatch.setattr(asyncio, "create_task", track_create)
        monkeypatch.setattr(s31a, "_STARTUP_COLLECTOR_SETTLE_S", 0.02)
        owner = original_create(
            s31a._ready_server(tmp_path, tmp_path / "dummy.jar", tmp_path / "java.log"),
        )
        await entered.wait()
        owner.cancel()
        try:
            with pytest.raises(asyncio.CancelledError) as exc:
                await asyncio.wait_for(owner, 1)
            assert "collector did not settle" in getattr(
                exc.value, "startup_cleanup_unconfirmed", "",
            )
            assert process.terminated == 1
            assert process.reaped == 1
            assert len(collectors) == 1
            assert not collectors[0].done()  # Not misreported as settled.
        finally:
            release.set()
            for collector in collectors:
                await asyncio.wait_for(collector, 1)

    asyncio.run(run())


def test_process_wait_ignoring_cancel_never_becomes_confirmed_cleanup():
    """wait_for() alone would overrun the deadline and lose the fault."""
    async def run():
        process = FakeProcess()
        released = asyncio.Event()
        wait_started = asyncio.Event()
        call_count = 0

        async def noncooperative_wait():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                wait_started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    await released.wait()
                return process.returncode
            process.reaped += 1
            return process.returncode

        process.wait = noncooperative_wait
        try:
            with pytest.raises(StartupCleanupUnconfirmed, match="prior wait remains"):
                await asyncio.wait_for(terminate_and_reap(process, timeout_s=0.01), 1)
            assert wait_started.is_set()
            assert call_count == 2
            # The second process.wait() may have returned an exit integer.
            # The first noncooperative task still prevents complete settlement.
            assert process.reaped == 1
        finally:
            released.set()
            await asyncio.sleep(0)

    asyncio.run(run())


def test_preexisting_cancel_before_spawn_never_creates_process(monkeypatch):
    calls = []

    async def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

    async def requested_cancel():
        asyncio.current_task().cancel()
        with pytest.raises(asyncio.CancelledError):
            await spawn_with_custody("java", "unused")
        assert calls == []

    async def run():
        child = asyncio.create_task(requested_cancel())
        with pytest.raises(asyncio.CancelledError):
            await child
        assert calls == []

    asyncio.run(run())


def test_cancel_during_spawn_preserves_unconfirmed_even_with_returncode(monkeypatch):
    """An integer returncode must not mask a failed reap receipt."""
    async def run():
        process = FakeProcess()
        entering = asyncio.Event()
        release = asyncio.Event()

        async def spawn(*args, **kwargs):
            entering.set()
            await release.wait()
            return process

        async def broken_wait():
            raise RuntimeError("injected unreaped waiter")

        process.wait = broken_wait
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        owner = asyncio.create_task(spawn_with_custody("node", "dummy"))
        await entering.wait()
        owner.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError) as caught:
            await owner
        assert process.terminated == 1
        assert process.returncode == -15  # A signal is not a reap receipt.
        assert "StartupCleanupUnconfirmed" in getattr(
            caught.value, "startup_cleanup_unconfirmed", "",
        )

    asyncio.run(run())


def test_reap_result_must_match_observed_process_exit():
    """A fake wait returning a different status cannot attest custody."""
    async def run():
        process = FakeProcess()

        async def inconsistent_wait():
            process.reaped += 1
            return 0  # terminate() sets process.returncode=-15

        process.wait = inconsistent_wait
        with pytest.raises(StartupCleanupUnconfirmed, match="disagrees"):
            await terminate_and_reap(process)
        assert process.returncode == -15
        assert process.reaped == 1

    asyncio.run(run())


def test_local_python_child_postspawn_cancel_real_reap(monkeypatch):
    """DEV Linux/CI OS smoke: one inert Python child, never Minecraft/Node."""
    import sys

    async def run():
        actual_spawn = asyncio.create_subprocess_exec
        ready = asyncio.Event()
        release = asyncio.Event()
        spawned = []

        async def delayed_handoff(*args, **kwargs):
            process = await actual_spawn(*args, **kwargs)
            spawned.append(process)
            ready.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_handoff)
        owner = asyncio.create_task(
            spawn_with_custody(
                sys.executable, "-c", "import time; time.sleep(30)",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
        )
        try:
            await asyncio.wait_for(ready.wait(), timeout=5)
            owner.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            assert len(spawned) == 1
            process = spawned[0]
            assert type(process.returncode) is int
            assert await asyncio.wait_for(process.wait(), timeout=2) == process.returncode
        finally:
            release.set()
            for process in spawned:
                if process.returncode is None:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5)

    asyncio.run(run())


def test_local_python_child_resisting_term_real_kill_reap():
    """DEV POSIX OS smoke: confirmed escalation, not a scientific World."""
    import os
    import sys

    if os.name != "posix":
        pytest.skip("POSIX SIGTERM-ignore subprocess fixture")
    async def run():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", "-c",
            "import signal,time,sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "sys.stdout.write('READY\\n'); sys.stdout.flush(); time.sleep(30)",
            stdout=asyncio.subprocess.PIPE,
        )
        try:
            assert process.stdout is not None
            assert await asyncio.wait_for(process.stdout.readline(), timeout=5) == b"READY\\n"
            rc = await asyncio.wait_for(
                terminate_and_reap(process, timeout_s=0.1),
                timeout=5,
            )
            assert rc == process.returncode
            assert type(rc) is int
            assert rc != 0
        finally:
            if process.returncode is None:
                process.kill()
                await asyncio.wait_for(process.wait(), timeout=5)

    asyncio.run(run())
