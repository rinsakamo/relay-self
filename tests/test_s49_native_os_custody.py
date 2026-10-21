"""DEV-only real Java/Node custody probes: no Minecraft, bridge or World.

These execute inert, single-process fixtures on Linux (including WSL2).
They prove only subprocess ownership, cancellation and OS-level reap on the
current machine. They do not waive protected-source or W4 live-lease gates.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from adapters.mineflayer import s31a_real_server_ci as s31a
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.startup_process_ownership import spawn_with_custody


def _linux_pid_identity(pid: int) -> tuple[int, str]:
    assert sys.platform.startswith("linux"), "Linux/WSL2 is required for PID custody"
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    # Linux field 22 is starttime, after 'comm' (parenthesized field 2).
    fields = stat.rsplit(")", maxsplit=1)[1].split()
    return pid, fields[19]


def _assert_gone(identity: tuple[int, str]) -> None:
    pid, _ = identity
    assert not Path(f"/proc/{pid}").exists(), f"PID {pid} has not been reaped"


def _native_command(tmp_path: Path, target: str) -> tuple[str, ...]:
    if target == "node":
        node = shutil.which("node")
        assert node is not None, "Node executable is required, not a SKIP"
        script = tmp_path / "inert.js"
        script.write_text("setInterval(() => {}, 1000);\n", encoding="utf-8")
        return node, str(script)
    if target == "java":
        java = shutil.which("java")
        javac = shutil.which("javac")
        assert java is not None and javac is not None, "JDK is required, not a SKIP"
        src = tmp_path / "S49Inert.java"
        src.write_text(
            'public final class S49Inert {'
            ' public static void main(String[] args) throws Exception {'
            ' System.out.println("BOOT"); System.out.flush();'
            ' Thread.sleep(60000);'
            ' }}\n',
            encoding="utf-8",
        )
        subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", str(tmp_path), str(src)],
            check=True,
            timeout=30,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return java, "-cp", str(tmp_path), "S49Inert"
    raise AssertionError(target)


@pytest.mark.parametrize("target", ["node", "java"])
def test_real_native_spawn_cancel_before_handoff_reaps_exact_pid(
    monkeypatch, tmp_path, target,
):
    """OS-created child is owned even before create_subprocess_exec hands it off."""
    argv = _native_command(tmp_path, target)

    async def run():
        real_spawn = asyncio.create_subprocess_exec
        created = asyncio.Event()
        release = asyncio.Event()
        children = []

        async def delayed_handoff(*args, **kwargs):
            child = await real_spawn(*args, **kwargs)
            children.append(child)
            created.set()
            await release.wait()
            return child

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_handoff)
        owner = asyncio.create_task(
            spawn_with_custody(*argv, stdout=asyncio.subprocess.PIPE)
        )
        try:
            await asyncio.wait_for(created.wait(), timeout=10)
            assert len(children) == 1
            identity = _linux_pid_identity(children[0].pid)
            assert identity[0] != os.getpid()
            owner.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            child = children[0]
            assert type(child.returncode) is int
            assert await asyncio.wait_for(child.wait(), timeout=2) == child.returncode
            _assert_gone(identity)
        finally:
            release.set()
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await asyncio.wait_for(child.wait(), timeout=5)

    asyncio.run(run())


def test_real_node_cancel_during_original_adapter_startup_reaps_and_seals(
    monkeypatch, tmp_path,
):
    """Exercise actual Node launch() and its *same* W3 startup capture."""
    script = Path(_native_command(tmp_path, "node")[1])
    real_spawn = asyncio.create_subprocess_exec
    real_receive = MineflayerProcessSession.receive

    async def run():
        children = []
        receiving = asyncio.Event()

        async def track_spawn(*args, **kwargs):
            child = await real_spawn(*args, **kwargs)
            children.append(child)
            return child

        async def track_receive(self):
            receiving.set()
            return await real_receive(self)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", track_spawn)
        monkeypatch.setattr(MineflayerProcessSession, "receive", track_receive)
        root = tmp_path / "w3"
        root.mkdir()  # W3 requires an existing fresh absolute evidence directory.
        owner = asyncio.create_task(
            MineflayerProcessSession.launch(
                MineflayerLaunchConfig(),
                bridge_path=script,
                node_executable=shutil.which("node") or "node",
                startup_timeout_s=10,
                raw_capture_root=root,
            )
        )
        try:
            async def wait_for_receive():
                while not receiving.is_set():
                    if owner.done():
                        owner.result()  # Surface startup faults rather than a false timeout.
                        raise AssertionError("Node startup exited without receiving")
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_for_receive(), timeout=10)
            assert len(children) == 1
            identity = _linux_pid_identity(children[0].pid)
            owner.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            assert type(children[0].returncode) is int
            _assert_gone(identity)
            receipt_path = root / "w3-node-stdout-receipt.json"
            assert receipt_path.is_file()
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            assert receipt["status"] == "INCOMPLETE_UNQUALIFIED"
            assert receipt["eof_observed"] is False
        finally:
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await asyncio.wait_for(child.wait(), timeout=5)

    asyncio.run(run())


def test_real_java_original_readiness_cancel_settles_only_collector(
    monkeypatch, tmp_path,
):
    """Exercise original _ready_server() on an inert JVM, no Minecraft JAR."""
    java_argv = _native_command(tmp_path, "java")

    async def run():
        real_spawn = asyncio.create_subprocess_exec
        children = []
        original_task = asyncio.create_task
        collectors = []
        log = tmp_path / "java-start.log"

        async def redirect_java(*args, **kwargs):
            assert args[0] == "java"
            child = await real_spawn(*java_argv, **kwargs)
            children.append(child)
            return child

        def track_collector(coro, *args, **kwargs):
            task = original_task(coro, *args, **kwargs)
            if getattr(coro, "__qualname__", "").endswith(".collect"):
                collectors.append(task)
            return task

        monkeypatch.setattr(asyncio, "create_subprocess_exec", redirect_java)
        monkeypatch.setattr(asyncio, "create_task", track_collector)
        owner = original_task(s31a._ready_server(tmp_path, tmp_path / "not-used.jar", log))

        async def await_log():
            while not log.is_file() or "BOOT" not in log.read_text(encoding="utf-8"):
                await asyncio.sleep(0.025)

        try:
            await asyncio.wait_for(await_log(), timeout=10)
            assert len(children) == 1
            identity = _linux_pid_identity(children[0].pid)
            owner.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            assert type(children[0].returncode) is int
            assert len(collectors) == 1
            assert collectors[0].done()
            _assert_gone(identity)
        finally:
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await asyncio.wait_for(child.wait(), timeout=5)
            for task in collectors:
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=2)
                    except asyncio.CancelledError:
                        pass

    asyncio.run(run())
