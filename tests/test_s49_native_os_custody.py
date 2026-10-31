"""DEV-only real Java/Node custody probes: no Minecraft, bridge or World.

These execute inert, single-process fixtures on Linux (including WSL2).
They prove only subprocess ownership, cancellation and OS-level reap on the
current machine. They do not waive protected-source or W4 live-lease gates.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from adapters.mineflayer import s31a_real_server_ci as s31a
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.startup_process_ownership import spawn_with_custody


@pytest.fixture(autouse=True)
def native_evidence(monkeypatch, tmp_path, request):
    """Record real Process operations without another stdout reader or owner."""
    events = tmp_path / "native-os-events.jsonl"
    evidence_root = os.environ.get("S49_NATIVE_EVIDENCE_ROOT")
    if evidence_root:
        events = Path(evidence_root) / (hashlib.sha256(request.node.nodeid.encode()).hexdigest() + '.jsonl')
        # A new run must never overwrite previous custody observations.
        events.touch(exist_ok=False)
    children = []
    collectors = []
    real_spawn = asyncio.create_subprocess_exec
    real_task = asyncio.create_task

    def emit(event, **fields):
        row = {"event": event, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "test": request.node.nodeid, "python": sys.version, **fields}
        with events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()

    async def track_spawn(*args, **kwargs):
        child = await real_spawn(*args, **kwargs)
        identity = _linux_pid_identity(child.pid)
        children.append((child, identity))
        emit("spawn", pid=child.pid, starttime=identity[1], argv=list(map(str, args)),
             parent_pid=os.getpid(), proc_stat=Path(f"/proc/{child.pid}/stat").read_text())
        for name in ("terminate", "kill"):
            original = getattr(child, name)

            def signal(original=original, name=name):
                emit(name, pid=child.pid, starttime=identity[1], returncode=child.returncode)
                return original()

            monkeypatch.setattr(child, name, signal)
        real_wait = child.wait

        async def wait():
            emit("wait_enter", pid=child.pid, starttime=identity[1])
            try:
                result = await real_wait()
            except BaseException as exc:
                emit("wait_error", pid=child.pid, error=type(exc).__name__)
                raise
            emit("wait_return", pid=child.pid, starttime=identity[1], result=result,
                 returncode=child.returncode, proc_absent=not Path(f"/proc/{child.pid}").exists())
            return result

        monkeypatch.setattr(child, "wait", wait)
        observer_root = os.environ.get("S49_OBSERVER_ROOT")
        if observer_root:
            ack = Path(observer_root) / f"{child.pid}-{identity[1]}.ack"
            deadline = asyncio.get_running_loop().time() + 5
            while not ack.is_file():
                if asyncio.get_running_loop().time() > deadline:
                    emit("observer_ack_missing", pid=child.pid)
                    child.kill()
                    await child.wait()
                    raise AssertionError("Independent observer did not identify child")
                await asyncio.sleep(0.002)
            emit("independent_observer_ack", pid=child.pid, starttime=identity[1])
        return child

    def track_task(coro, *args, **kwargs):
        task = real_task(coro, *args, **kwargs)
        if getattr(coro, "__qualname__", "").endswith(".collect"):
            collectors.append(task)
            emit("collector_created", task_name=task.get_name())
            task.add_done_callback(lambda done: emit(
                "collector_settled", task_name=done.get_name(), done=done.done(),
                cancelled=done.cancelled()))
        return task

    def cancel(owner, boundary):
        emit("cancel_requested", boundary=boundary, task_name=owner.get_name())
        owner.cancel()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", track_spawn)
    monkeypatch.setattr(asyncio, "create_task", track_task)
    def settled():
        pending = [t.get_name() for t in asyncio.all_tasks()
                   if t is not asyncio.current_task() and not t.done()]
        emit("owner_cleanup_settled", pending_tasks=pending)
        assert not pending

    yield {"cancel": cancel, "settled": settled, "emit": emit}
    for child, identity in children:
        emit("final_process", pid=child.pid, starttime=identity[1], returncode=child.returncode,
             proc_absent=not Path(f"/proc/{child.pid}").exists())
        assert type(child.returncode) is int
        _assert_gone(identity)
    for task in collectors:
        emit("final_collector", task_name=task.get_name(), done=task.done(),
             cancelled=task.cancelled())
        assert task.done()
    for receipt in tmp_path.rglob("w3-node-stdout-receipt.json"):
        emit("w3_receipt", path=str(receipt), sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
             content=json.loads(receipt.read_text()))


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
    monkeypatch, tmp_path, target, native_evidence,
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
            native_evidence["cancel"](owner, "os_spawn_before_process_handoff")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            child = children[0]
            assert type(child.returncode) is int
            assert await asyncio.wait_for(child.wait(), timeout=2) == child.returncode
            await asyncio.sleep(0)
            native_evidence["settled"]()
            _assert_gone(identity)
        finally:
            release.set()
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await asyncio.wait_for(child.wait(), timeout=5)

    asyncio.run(run())


def test_real_node_cancel_during_original_adapter_startup_reaps_and_seals(
    monkeypatch, tmp_path, native_evidence,
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
            native_evidence["cancel"](owner, "original_launch_wait_adapter_started")
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            assert type(children[0].returncode) is int
            await asyncio.sleep(0)
            native_evidence["settled"]()
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
    monkeypatch, tmp_path, native_evidence,
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
            native_evidence["cancel"](owner, "original_ready_server_wait_readiness")
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(owner, timeout=10)
            assert type(children[0].returncode) is int
            assert len(collectors) == 1
            assert collectors[0].done()
            await asyncio.sleep(0)
            native_evidence["settled"]()
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


def test_real_node_w4_successful_startup_owner_preworld_and_bounded_host_handoff(
    tmp_path, native_evidence,
):
    """Inert Node stdout traverses ORIGINAL decoder and W4 owner; no Minecraft.

    A fabricated collector marker is used ONLY to exercise the offline HOST
    lease transition. It is not a Java/World attestation or Action grant.
    """
    from adapters.mineflayer.s31a_real_server_ci import _await_spawn
    from adapters.mineflayer.self_world_stage_w4_lease import W4DevLeasedSession
    from test_self_world_stage_w4_lease import marker_for, preworld
    from test_self_world_stage_w4_prehost import _offline_lines

    node = shutil.which("node")
    assert node is not None, "real Node executable required; no silent skip"
    pre, _, lines = _offline_lines()
    script = tmp_path / "inert-w4-startup.js"
    script.write_text(
        "const frames = " + json.dumps([row.decode("utf-8") for row in lines]) + ";\n"
        "for (const frame of frames) process.stdout.write(frame);\n"
        "process.stdin.on('data', (data) => {\n"
        "  if (data.toString('utf8').includes('\\\"shutdown\\\"')) process.exit(0);\n"
        "});\n"
        "setInterval(() => {}, 1000);\n",
        encoding="utf-8",
    )

    async def run():
        session = None
        identity = None
        try:
            session = await W4DevLeasedSession.launch(
                MineflayerLaunchConfig(version="1.21.8"),
                bridge_path=script,
                node_executable=node,
                startup_timeout_s=10,
            )
            identity = _linux_pid_identity(session._process.pid)
            owner = session.owner_token()
            native_evidence["emit"](
                "node_startup_handoff", pid=session._process.pid,
                session_object=id(session), process_object=id(session._process),
                original_decoder_module=type(session._decoder.original).__module__,
                original_receive_module=MineflayerProcessSession.receive.__module__,
                started_session_id=session.started.session_id,
                action_supervisor_absent=session._supervisor is None,
            )
            assert session.process_returncode is None
            # The original S34 startup reader consumes the sole native spawn.
            observed_spawn = await _await_spawn(session)
            assert observed_spawn.kind == "spawn"
            receipt, ledger = await preworld(session, owner, pre)
            assert not receipt.physical_run_permitted
            native_evidence["emit"](
                "preworld_handoff", receipt=asdict(receipt), ledger=asdict(ledger),
                session_object=id(session), physical_run_permitted=False,
            )
            assert ledger.delivery_scope == "PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS"
            session.advance(owner=owner, phase="WORLD_WINDOW", binding="offline-only")
            # Deliberately synthetic: exercises the lease handoff, not a
            # genuine Minecraft World marker or server collector witness.
            session.world_marker(owner=owner, marker=marker_for(receipt))
            op = session.advance(owner=owner, phase="HOST", binding="offline-host")
            frame = await asyncio.wait_for(
                session.delegate(
                    owner=owner, operation=op, invoke=lambda: session.receive(),
                ),
                timeout=10,
            )
            assert frame.seq == 4 and frame.session_id == pre.session_id
            native_evidence["emit"](
                "host_handoff", frame=asdict(frame), operation_epoch=op.epoch,
                phase=session.phase, actor_is_controller=session._actor is asyncio.current_task(),
                delegated=session._delegated, action_supervisor_absent=session._supervisor is None,
            )
            assert [row.seq for row in session.audit if row.event == "DELIVER"] == [
                0, 1, 2, 3, 4,
            ]
            assert not any(row.event == "DENY" for row in session.audit)
            assert session._actor is asyncio.current_task()
            assert session._delegated == 0
            session.advance(owner=owner, phase="QUIESCE", binding="offline-quiet")
            session.advance(owner=owner, phase="SHUTDOWN", binding="offline-shutdown")
            assert await session.shutdown(timeout_s=5) == 0
            assert session.phase == "CLOSED"
            assert session.process_returncode == 0
            native_evidence["emit"](
                "node_closed", pid=session._process.pid, phase=session.phase,
                action_supervisor_absent=session._supervisor is None,
                audit=[asdict(row) for row in session.audit],
            )
            _assert_gone(identity)
            await asyncio.sleep(0)
            native_evidence["settled"]()
        finally:
            if session is not None and session.process_returncode is None:
                from adapters.mineflayer.startup_process_ownership import terminate_and_reap

                await terminate_and_reap(session._process)

    asyncio.run(run())


def test_real_java_original_readiness_success_transfers_single_collector(
    monkeypatch, tmp_path, native_evidence,
):
    """Original _ready_server success hands over one real JVM and one reader.

    Only an inert Java program imitates the readiness string; this does not
    establish actual Minecraft readiness or source attestation.
    """
    java_argv = _native_command(tmp_path, "java")
    src = tmp_path / "S49Inert.java"
    src.write_text(
        'public final class S49Inert {'
        ' public static void main(String[] args) throws Exception {'
        ' System.out.println("BOOT");'
        ' System.out.println("Done (0.5s)! For help, type help");'
        ' System.out.flush();'
        ' Thread.sleep(60000);'
        ' }}\n',
        encoding="utf-8",
    )
    javac = shutil.which("javac")
    assert javac is not None
    subprocess.run(
        [javac, "-encoding", "UTF-8", "-d", str(tmp_path), str(src)],
        check=True, timeout=30, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    prior_spawn = asyncio.create_subprocess_exec
    launched = []

    async def redirect_inert_java(*args, **kwargs):
        assert args[0] == "java" and "-jar" in args
        assert "-jar" not in java_argv
        child = await prior_spawn(*java_argv, **kwargs)
        launched.append(child)
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", redirect_inert_java)

    async def run():
        server = None
        collector = None
        try:
            server, collector, ready = await asyncio.wait_for(
                s31a._ready_server(tmp_path, tmp_path / "unused.jar",
                                  tmp_path / "original-collector.log"),
                timeout=12,
            )
            identity = _linux_pid_identity(server.pid)
            assert ready.is_set() and server.returncode is None
            assert len(launched) == 1 and launched[0] is server
            native_evidence["emit"](
                "java_ready_handoff", pid=server.pid, starttime=identity[1],
                server_object=id(server), launched_object=id(launched[0]),
                collector_object=id(collector), collector_name=collector.get_name(),
                collector_done=collector.done(), ready_object=id(ready), ready_is_set=ready.is_set(),
                collector_coro=collector.get_coro().__qualname__,
                collector_locals={key: id(value) for key, value in
                                  collector.get_coro().cr_frame.f_locals.items()
                                  if key in {"process", "ready", "log_path"}},
            )
            log = (tmp_path / "original-collector.log").read_text(encoding="utf-8")
            assert log.count("BOOT") == 1
            assert log.count("Done (") == 1
            # Ownership is now with the caller; the same collector remains
            # the *only* reader until the exact child exits.
            from adapters.mineflayer.startup_process_ownership import terminate_and_reap

            result = await asyncio.wait_for(terminate_and_reap(server), timeout=10)
            assert result == server.returncode and type(result) is int
            await asyncio.wait_for(collector, timeout=5)
            assert collector.done()
            native_evidence["emit"](
                "java_collector_handoff_closed", pid=server.pid,
                collector_object=id(collector), collector_done=collector.done(),
                collector_cancelled=collector.cancelled(), collector_exception=collector.exception(),
                wait_result=result, returncode=server.returncode,
            )
            _assert_gone(identity)
            await asyncio.sleep(0)
            native_evidence["settled"]()
        finally:
            if server is not None and server.returncode is None:
                from adapters.mineflayer.startup_process_ownership import terminate_and_reap

                await terminate_and_reap(server)
            if collector is not None and not collector.done():
                collector.cancel()
                try:
                    await asyncio.wait_for(collector, timeout=3)
                except asyncio.CancelledError:
                    pass

    asyncio.run(run())


def test_real_node_sigterm_resistance_requires_kill_and_reap(tmp_path, native_evidence):
    from adapters.mineflayer.startup_process_ownership import terminate_and_reap
    script = tmp_path / 'resistant.js'
    script.write_text("process.on('SIGTERM', () => {}); console.log('BOOT'); setInterval(()=>{},1000);\n")
    async def run():
        child = await spawn_with_custody(shutil.which('node'), str(script),
                                        stdout=asyncio.subprocess.PIPE)
        try:
            assert await asyncio.wait_for(child.stdout.readline(), 3) == b'BOOT\n'
            result = await terminate_and_reap(child, timeout_s=.1)
            assert result == child.returncode == -9
            assert not Path(f'/proc/{child.pid}').exists()
            await asyncio.sleep(0)
            native_evidence['settled']()
        finally:
            if child.returncode is None:
                child.kill()
                await child.wait()
    asyncio.run(run())


@pytest.mark.parametrize('fault', ['normal', 'cancel', 'exception'])
def test_real_node_original_s34_native_spawn_ownership(monkeypatch, tmp_path, native_evidence, fault):
    from adapters.mineflayer import s34_native_world_cognition_ci as s34
    from test_self_world_stage_w4_prehost import _offline_lines
    _, _, frames = _offline_lines()
    script = tmp_path / 'original-startup.js'
    selected = frames[:2] if fault == 'normal' else frames[:1]
    script.write_text('for (const f of '+json.dumps([x.decode() for x in selected])+') process.stdout.write(f);\nsetInterval(()=>{},1000);\n')
    original_launch = MineflayerProcessSession.launch.__func__
    original_await = s34._await_spawn
    sessions = []
    async def launch(cls, config, **kwargs):
        session = await original_launch(cls, config, bridge_path=script,
                                       node_executable=shutil.which('node'), **kwargs)
        sessions.append(session)
        return session
    monkeypatch.setattr(MineflayerProcessSession, 'launch', classmethod(launch))
    async def run():
        entered = asyncio.Event()
        async def wait_spawn(session):
            entered.set()
            if fault == 'exception':
                raise RuntimeError('native S34 spawn fixture exception')
            return await original_await(session)
        monkeypatch.setattr(s34, '_await_spawn', wait_spawn)
        raw = tmp_path / 'raw'
        raw.mkdir()
        owner = asyncio.create_task(s34._new_session(raw_capture_root=raw))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            if fault == 'normal':
                session = await asyncio.wait_for(owner, 5)
                assert session is sessions[0] and session.process_returncode is None
                native_evidence['emit']('original_s34_handoff', pid=session._process.pid,
                                        session_object=id(session), owner_returned=True)
                await session.abort_startup()  # Caller now owns cleanup.
            elif fault == 'cancel':
                native_evidence['cancel'](owner, 'original_s34_await_native_spawn')
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(owner, 5)
            else:
                with pytest.raises(RuntimeError, match='S34 spawn fixture'):
                    await asyncio.wait_for(owner, 5)
            assert len(sessions) == 1
            child = sessions[0]._process
            assert child.returncode == await child.wait() == -15
            assert not Path(f'/proc/{child.pid}').exists()
            receipt = json.loads((raw/'w3-node-stdout-receipt.json').read_text())
            assert receipt['status'] == 'INCOMPLETE_UNQUALIFIED'
            await asyncio.sleep(0)
            native_evidence['settled']()
        finally:
            if not owner.done():
                owner.cancel()
                try:
                    await owner
                except asyncio.CancelledError:
                    pass
            for session in sessions:
                if session.process_returncode is None:
                    await session.abort_startup()
    asyncio.run(run())


@pytest.mark.parametrize('fault', ['cancel', 'secondary_exception'])
def test_real_s49_owner_node_fault_reaps_java_and_original_collector(monkeypatch, tmp_path, native_evidence, fault):
    from adapters.mineflayer import s49_normal_session_real_ci as s49
    from test_self_world_stage_w4_prehost import _offline_lines
    _, _, frames = _offline_lines()
    script = tmp_path / 's49-inert.js'
    script.write_text('for (const f of '+json.dumps([x.decode() for x in frames[:2]])+') process.stdout.write(f);\nsetInterval(()=>{},1000);\n')
    java_argv = _native_command(tmp_path, 'java')
    source = tmp_path / 'S49Inert.java'
    source.write_text('public final class S49Inert { public static void main(String[] args) throws Exception { System.out.println("Done (0.1s)! For help"); System.out.flush(); Thread.sleep(60000); }}\n')
    subprocess.run([shutil.which('javac'), '-d', str(tmp_path), str(source)], check=True, timeout=30)
    original_spawn = asyncio.create_subprocess_exec
    async def spawn(*argv, **kwargs):
        return await original_spawn(*(java_argv if argv[0] == 'java' else argv), **kwargs)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    original_launch = MineflayerProcessSession.launch.__func__
    async def launch(cls, config, **kwargs):
        return await original_launch(cls, config, bridge_path=script,
                                     node_executable=shutil.which('node'), **kwargs)
    monkeypatch.setattr(MineflayerProcessSession, 'launch', classmethod(launch))
    async def bad_shutdown(self, **kwargs):
        if fault == 'cancel':
            raise asyncio.CancelledError('native S49 cleanup cancellation')
        raise RuntimeError('native S49 shutdown failure')
    async def bad_terminate(self):
        raise OSError('native S49 secondary terminate failure')
    monkeypatch.setattr(MineflayerProcessSession, 'shutdown', bad_shutdown)
    monkeypatch.setattr(MineflayerProcessSession, 'terminate', bad_terminate)
    monkeypatch.setattr(s49, '_CLEANUP_STEP_TIMEOUT_S', .2)
    monkeypatch.setattr(s49, '_fetch_official_server', lambda path: {})
    monkeypatch.setattr(s49, '_write_config', lambda root: None)
    def stop_before_action():
        raise RuntimeError('native fixture stops before cognition/Action')
    monkeypatch.setattr(s49.s19, '_epoch_one', stop_before_action)
    monkeypatch.setenv('S49_REAL_SERVER_CI', '1')
    monkeypatch.delenv('NODE_OPTIONS', raising=False)
    async def run():
        raw = tmp_path / 'raw'
        raw.mkdir()
        report_path = tmp_path / 'report.json'
        operation = s49.qualify(report_path, tmp_path / 'java.log', raw_capture_root=raw)
        if fault == 'cancel':
            with pytest.raises(asyncio.CancelledError, match='native S49 cleanup cancellation'):
                await operation
        else:
            assert await operation == 1
        report = json.loads(report_path.read_text())
        assert report['status'] == 'FAIL'
        assert report['actual_native_actions'] == []
        assert report['node_exit'] == report['server_exit'] == -9
        assert report['w3_node_stdout_capture']['status'] == 'INCOMPLETE_UNQUALIFIED'
        assert not any(k.endswith('_unconfirmed') for k in report)
        native_evidence['emit']('original_s49_native_report', report=report)
        await asyncio.sleep(0)
        native_evidence['settled']()
    asyncio.run(run())
