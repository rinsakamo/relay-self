"""Original S49 cancellation/secondary-fault tests; no physical processes."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest


@pytest.fixture
def owner_ports(monkeypatch, tmp_path):
    from types import SimpleNamespace as NS

    import adapters.mineflayer.s49_normal_session_real_ci as s49
    from adapters.mineflayer.execution import WorldConsequenceStatus
    from relay_self.action import ActionState
    from relay_self.world_conditioned_choice import WorldChoiceKind

    sid = "fake-only-s49-native-session"
    events = []
    faults = set()
    def inject(name):
        events.append(name)
        if name + "_cancel" in faults:
            raise asyncio.CancelledError(name)
        if name + "_error" in faults:
            raise RuntimeError(name)
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(s49, "_fetch_official_server", lambda path: {})
    monkeypatch.setattr(s49, "_write_config", lambda root: None)
    monkeypatch.setattr(s49, "_command", lambda *args: None)
    monkeypatch.setattr(s49, "capture_native_action_evidence", lambda c: {})
    monkeypatch.setattr(s49, "ExecutionBinding", lambda **kwargs: kwargs)
    monkeypatch.setattr(s49, "resolve_execution_binding", lambda *a, **kw: object())
    monkeypatch.setattr(s49, "_native_threat", lambda *a, **kw: NS(distance_m=2))
    monkeypatch.setattr(
        s49, "_native_epoch_two",
        lambda *a, **kw: (
            {"plan": NS(selected=NS(candidate_id="MOVE_AWAY")),
             "admission": NS(status=NS(value="admitted")),
             "control": object(), "route": object(),
             "policies": [object(), object()]},
            NS(cognition_requested=False),
        ),
    )
    monkeypatch.setattr(
        s49.s19, "_epoch_one",
        lambda: (None, NS(new_state=NS(
            target_id="risk_weight", revision=1, value=4,
        )), None, None, None, None),
    )

    class FakeStdin:
        async def drain(self):
            return None

    class Process:
        stdin = FakeStdin()
        returncode = None
        def terminate(self):
            inject(self.name + "_terminate")
        def kill(self):
            inject(self.name + "_kill")
            self.returncode = -9
        async def wait(self):
            inject(self.name + "_reap")
            if self.returncode is None:
                self.returncode = -15
            return self.returncode
    server = Process()
    server.name = "java"
    node = Process()
    node.name = "node"
    collector = None
    original_temp = s49.tempfile.TemporaryDirectory
    class Temp:
        def __init__(self, **kwargs):
            self.inner = original_temp(**kwargs)
            self.name = self.inner.name
        def cleanup(self):
            inject("temp")
            self.inner.cleanup()
    monkeypatch.setattr(s49.tempfile, "TemporaryDirectory", Temp)

    async def ready(*args):
        nonlocal collector
        async def collect():
            try:
                await asyncio.Event().wait()
            finally:
                inject("collector")
        collector = asyncio.create_task(collect())
        return server, collector, None

    async def stop(*args):
        inject("java_shutdown")
        server.returncode = 8 if "java_nonzero" in faults else 0
        collector.cancel()
        try:
            await collector
        except asyncio.CancelledError:
            if "collector_cancel" in faults:
                raise

    monkeypatch.setattr(s49, "_ready_server", ready)
    monkeypatch.setattr(s49, "_shutdown_server", stop)

    class FakeNodeSession:
        started = NS(session_id=sid)
        _process = node

        @property
        def raw_capture_receipt(self):
            inject("receipt")
            return {
                "status": "INCOMPLETE_UNQUALIFIED" if "w3_incomplete" in faults else "COMPLETE_NODE_STDOUT",
                "session_id": sid,
                "eof_observed": True,
                "shutdown_ack_count": (
                    0 if "missing_ack" in faults else 1
                ),
                "process_exit_code": 0,
                "capture_fault": None,
            }

        async def shutdown(self, *, timeout_s):
            inject("node_shutdown")
            if "node_hang" in faults:
                await asyncio.Event().wait()
            node.returncode = 7 if "node_nonzero" in faults else 0
            return node.returncode

        async def terminate(self):
            inject("node_terminate")
            return await node.wait()

    async def new_session(**kwargs):
        return FakeNodeSession()

    monkeypatch.setattr(s49, "_new_session", new_session)

    async def read_probe(session, request_id):
        if "body_cancel" in faults:
            raise asyncio.CancelledError("original-body")
        seq = int(request_id.rsplit("-", 1)[1])
        return NS(
            seq=seq + 1, request_id=request_id,
            snapshot=NS(nearby_entities=(NS(
                name="zombie", entity_id=seq, distance=2.0,
            ),)),
        )

    monkeypatch.setattr(s49, "_correlated_observe", read_probe)

    class FakeExecutor:
        def __init__(self, session, intent):
            self.supervisor = NS(
                open_actions=(),
                get=lambda aid: NS(state=ActionState.OUTCOME),
            )

        async def execute(self, session, step, bound, probe, *auth):
            return NS(
                terminal=NS(state=ActionState.OUTCOME, action_id=step.action_request_id),
                consequence=NS(
                    status=WorldConsequenceStatus.EXECUTED,
                    movement_distance=0.2, session_id=sid,
                ),
            )

    monkeypatch.setattr(s49, "NormalSessionActionExecutor", FakeExecutor)

    class FakeL0:
        events = 3
        action_requests = 2

        def __init__(self, *a, **kw):
            pass

        async def run_session(
            self, source, *, probe, grant, on_action_request, max_frames,
        ):
            assert max_frames == 320
            # Let the real original staging coroutine enter its first sleep.
            await asyncio.sleep(0)
            result = []
            for i, event_seq in enumerate((1, 3, 5)):
                entity = NS(name="zombie", entity_id=event_seq, distance=2.0)
                frame = NS(
                    seq=event_seq, kind="entities",
                    snapshot=NS(nearby_entities=(entity,)),
                )
                reading = await probe(frame)
                choice = NS(
                    selection=WorldChoiceKind.WAIT if i == 0
                    else WorldChoiceKind.MOVE_AWAY,
                    probe_seq=reading.seq, entity_id=event_seq,
                    distance_m=10 if i == 0 else 2,
                )
                aid = f"s49-native-move-{event_seq}" if i else None
                step = NS(
                    event_seq=event_seq, choice=choice,
                    asks_for_action=i != 0, action_request_id=aid,
                )
                if i:
                    assert grant(choice, event_seq).action_id == aid
                    await on_action_request(step)
                result.append(step)
            return tuple(result)

    monkeypatch.setattr(s49, "NormalWorldL0", FakeL0)
    # Exercise original staging finally by making its drain raise on cancel.
    async def drain():
        try:
            await asyncio.Event().wait()
        finally:
            inject("staging")
    server.stdin.drain = drain
    if hasattr(s49, "_CLEANUP_STEP_TIMEOUT_S"):
        monkeypatch.setattr(s49, "_CLEANUP_STEP_TIMEOUT_S", 0.03)
        monkeypatch.setattr(s49, "_CLEANUP_CANCEL_GRACE_S", 0.03)
    return s49, faults, events, node, server


# Each case covers a distinct cleanup boundary, not a Cartesian product.
CASES = [
    ((), False),
    (("node_nonzero",), False),
    (("node_shutdown_error",), False),
    (("node_shutdown_cancel",), True),
    (("node_shutdown_error", "node_terminate_error"), False),
    (("node_shutdown_error", "node_terminate_cancel"), True),
    (("java_nonzero",), False),
    (("java_shutdown_error",), False),
    (("java_shutdown_cancel",), True),
    (("staging_error",), False),
    (("collector_error",), False),
    (("collector_cancel",), True),
    (("receipt_error",), False),
    (("temp_error",), False),
    (("missing_ack",), False),
    (("w3_incomplete",), False),
    (("body_cancel", "staging_error", "node_shutdown_error",
      "node_terminate_cancel", "java_shutdown_error", "temp_error"), True),
    (("node_hang",), False),
]


@pytest.mark.parametrize("injections,cancelled", CASES,
                         ids=["+".join(x[0]) or "clean" for x in CASES])
def test_original_owner_cleanup(owner_ports, tmp_path, injections, cancelled, capsys):
    s49, faults, events, node, server = owner_ports
    faults.update(injections)
    out = tmp_path / "report.json"

    async def run():
        if cancelled:
            with pytest.raises(asyncio.CancelledError):
                await s49.qualify(out, tmp_path / "java.log", raw_capture_root=tmp_path / "raw")
        else:
            rc = await s49.qualify(out, tmp_path / "java.log", raw_capture_root=tmp_path / "raw")
            assert rc == (1 if injections else 0)
        assert not [t for t in asyncio.all_tasks()
                    if t is not asyncio.current_task() and not t.done()]

    asyncio.run(run())
    report = json.loads(out.read_text())
    assert report["status"] == ("FAIL" if injections else "PASS")
    if injections:
        assert report["classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert "java_shutdown" in events
    assert "temp" in events
    assert "collector" in events
    assert node.returncode is not None and server.returncode is not None
    if any(x.startswith("node_terminate_") for x in injections):
        assert "node_kill" in events and "node_reap" in events
    if not injections:
        assert [x["selected"] for x in report["decisions"]] == ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]
        assert len(report["actual_native_actions"]) == 2
    assert "S49_REPORT=" in capsys.readouterr().out
    print("S49_FAULT_RECORD=" + json.dumps({
        "injections": injections, "calls": events,
        "node_exit": node.returncode, "java_exit": server.returncode,
        "report_exists": out.exists(), "report": report,
        "rc": None if cancelled else (1 if injections else 0),
        "propagated": "CancelledError" if cancelled else None,
    }, sort_keys=True))


@pytest.mark.parametrize("boundary", ("_ready_server", "_new_session"))
@pytest.mark.parametrize("kind", ("cancel", "blocked", "error"))
def test_startup_cleanup_diagnosis_survives_to_s49_report(
    owner_ports, tmp_path, monkeypatch, boundary, kind,
):
    """An unreturned helper handle cannot erase its cleanup fault."""
    s49, _, _, _, _ = owner_ports
    errors = {"cancel": asyncio.CancelledError, "blocked": s49.S31ABlocked,
              "error": RuntimeError}
    error = errors[kind]("injected startup custody fault")
    error.startup_cleanup_unconfirmed = "injected: waiter or collector still unconfirmed"

    async def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(s49, boundary, fail)
    out = tmp_path / "startup-fault-report.json"

    async def run():
        if kind == "cancel":
            with pytest.raises(asyncio.CancelledError) as raised:
                await s49.qualify(out, tmp_path / "java.log")
            assert raised.value is error
        else:
            assert await s49.qualify(out, tmp_path / "java.log") != 0
        assert not [t for t in asyncio.all_tasks()
                    if t is not asyncio.current_task() and not t.done()]

    asyncio.run(run())
    report = json.loads(out.read_text())
    assert report["status"] in ("FAIL", "BLOCKED")
    assert report["classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert report["startup_cleanup_unconfirmed"] == error.startup_cleanup_unconfirmed


def test_report_failure_is_explicit(owner_ports, tmp_path, monkeypatch, capsys):
    s49, _, events, _, _ = owner_ports
    original = Path.replace
    def fail(self, target):
        if target == tmp_path / "report.json":
            raise OSError("injected atomic replacement failure")
        return original(self, target)
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="atomic replacement"):
        asyncio.run(s49.qualify(tmp_path / "report.json", tmp_path / "java.log"))
    assert "temp" in events and "java_shutdown" in events
    output = capsys.readouterr()
    assert '"status": "PASS"' not in output.out
    assert "report_write_error" in output.err
    assert not (tmp_path / "report.json").exists()


def test_repeated_caller_cancellation_is_supervised(owner_ports, tmp_path, monkeypatch):
    s49, _, events, node, _ = owner_ports
    entered_body = asyncio.Event()
    entered_shutdown = asyncio.Event()
    release_shutdown = asyncio.Event()
    async def body(*args):
        entered_body.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(s49, "_correlated_observe", body)
    async def shutdown(self, **kwargs):
        events.append("node_shutdown")
        entered_shutdown.set()
        await release_shutdown.wait()
        node.returncode = 0
        return 0
    # Use the fake port returned by the original session factory.
    original_new = s49._new_session
    async def new(**kwargs):
        session = await original_new(**kwargs)
        session.shutdown = shutdown.__get__(session)
        return session
    monkeypatch.setattr(s49, "_new_session", new)
    out = tmp_path / "repeat.json"
    async def run():
        task = asyncio.create_task(s49.qualify(out, tmp_path / "java.log"))
        await entered_body.wait()
        task.cancel("first-caller-cancel")
        await entered_shutdown.wait()
        for message in ("second-cancel", "third-cancel"):
            task.cancel(message)
            await asyncio.sleep(0)
        assert not task.done()
        release_shutdown.set()
        with pytest.raises(asyncio.CancelledError, match="first-caller-cancel"):
            await task
        assert task.cancelling() == 3  # no uncancel() erasing caller state
        assert not [t for t in asyncio.all_tasks()
                    if t is not asyncio.current_task() and not t.done()]
    asyncio.run(run())
    report = json.loads(out.read_text())
    assert report["status"] == "FAIL" and report["cancellation_count"] == 3
    assert report["first_cancellation"] == "first-caller-cancel"
    assert "java_shutdown" in events and "temp" in events


@pytest.mark.parametrize("boundary", ("terminate_timeout", "kill_error", "reap_error",
                                      "unknown_exit", "receipt_cancel", "temp_cancel"))
def test_fallback_and_sync_boundary_faults(owner_ports, tmp_path, monkeypatch, boundary):
    s49, faults, events, node, _ = owner_ports
    if boundary in {"terminate_timeout", "kill_error", "reap_error", "unknown_exit"}:
        faults.add("node_shutdown_error")
    if boundary in {"kill_error", "reap_error"}:
        faults.update({"node_terminate_error", "node_" + boundary})
    if boundary == "unknown_exit":
        faults.add("node_terminate_error")
        async def unknown():
            return None
        monkeypatch.setattr(node, "wait", unknown)
        monkeypatch.setattr(node, "kill", lambda: None)
    original_new = s49._new_session
    async def new(**kwargs):
        session = await original_new(**kwargs)
        if boundary == "terminate_timeout":
            async def hang():
                events.append("node_terminate")
                await asyncio.Event().wait()
            session.terminate = hang
        return session
    monkeypatch.setattr(s49, "_new_session", new)
    faults.add(boundary)
    out = tmp_path / "fallback.json"
    async def run():
        if boundary.endswith("_cancel"):
            with pytest.raises(asyncio.CancelledError):
                await s49.qualify(out, tmp_path / "java.log", raw_capture_root=tmp_path / "raw")
        else:
            assert await s49.qualify(out, tmp_path / "java.log") == 1
    asyncio.run(run())
    report = json.loads(out.read_text())
    assert report["status"] == "FAIL"
    assert "java_shutdown" in events and "temp" in events
    if boundary == "unknown_exit":
        assert "node_exit" not in report and report["node_reap_unconfirmed"]
    if boundary == "terminate_timeout":
        assert report["node_kill_attempted"] and report["node_exit"] == -9
    if boundary == "kill_error":
        assert "node_kill_error" in report and "node_reap" in events


def test_atomic_report_failure_preserves_prior_bytes(owner_ports, tmp_path, monkeypatch, capsys):
    s49, faults, _, _, _ = owner_ports
    faults.add("body_cancel")
    out = tmp_path / "report.json"
    out.write_bytes(b"prior-snapshot\n")
    def fail(self, target):
        raise OSError("replace denied")
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(asyncio.CancelledError, match="original-body") as caught:
        asyncio.run(s49.qualify(out, tmp_path / "java.log"))
    assert isinstance(caught.value.__cause__, OSError)
    assert out.read_bytes() == b"prior-snapshot\n"
    assert not list(tmp_path.glob(".report.json.*"))
    assert "report_write_error" in capsys.readouterr().err


def test_real_stage_r_summary_remains_readonly_during_cleanup():
    import adapters.mineflayer.s49_normal_session_real_ci as s49
    from test_self_world_stage_r_owner import _sealed
    operator, host, executor, _, _, _, following = _sealed()
    operator.observe_original_probe(following)  # actual existing S10 HOLD producer
    before = operator.summary()
    report = {}
    asyncio.run(s49._cleanup_session(report, None, None, None, None, None,
                                     operator, None, []))
    assert report["stage_r_owner"] == before == operator.summary()
    assert host.retained.revision == 2 and host.retained.value == 4
    assert executor.supervisor.open_actions == ()


def test_cancellation_resistant_step_has_bounded_failure(owner_ports, tmp_path, monkeypatch):
    s49, faults, events, node, _ = owner_ports
    faults.add("node_terminate_error")
    release = asyncio.Event()
    original_new = s49._new_session
    async def new(**kwargs):
        session = await original_new(**kwargs)
        async def resistant(**kwargs):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await release.wait()
        session.shutdown = resistant
        return session
    kill = node.kill
    def kill_and_release():
        kill()
        release.set()
    monkeypatch.setattr(s49, "_new_session", new)
    monkeypatch.setattr(node, "kill", kill_and_release)
    out = tmp_path / "bounded.json"
    async def run():
        assert await s49.qualify(out, tmp_path / "java.log") == 1
        await asyncio.sleep(0)
        assert not [t for t in asyncio.all_tasks()
                    if t is not asyncio.current_task() and not t.done()]
    asyncio.run(run())
    report = json.loads(out.read_text())
    assert report["node_cleanup_error_unconfirmed"]
    assert report["status"] == "FAIL"
    assert report["node_exit"] == -9
    assert "java_shutdown" in events and "temp" in events


def test_preexisting_staging_cancellation_is_not_success(owner_ports, tmp_path, monkeypatch):
    s49, _, events, _, _ = owner_ports
    create = asyncio.create_task
    def create_and_cancel(coro, **kwargs):
        task = create(coro, **kwargs)
        if coro.cr_code.co_name == "stage_world":
            task.cancel("foreign-stage-cancel")
        return task
    monkeypatch.setattr(asyncio, "create_task", create_and_cancel)
    out = tmp_path / "staging.json"
    with pytest.raises(asyncio.CancelledError, match="foreign-stage-cancel"):
        asyncio.run(s49.qualify(out, tmp_path / "java.log"))
    assert json.loads(out.read_text())["status"] == "FAIL"
    assert "java_shutdown" in events and "temp" in events


def test_forced_reap_seals_existing_raw_file_as_incomplete(owner_ports, tmp_path, monkeypatch):
    from adapters.mineflayer.process_session import MineflayerProcessSession
    from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture
    s49, faults, _, _, _ = owner_ports
    faults.update({"node_shutdown_cancel", "node_terminate_error"})
    root = tmp_path / "raw"
    root.mkdir()
    capture = W3RawNodeStdoutCapture(root)
    original_new = s49._new_session
    holder = []
    async def new(**kwargs):
        session = await original_new(**kwargs)
        session._raw_capture = capture
        session._raw_receipt = None
        session._seal_raw_capture = MineflayerProcessSession._seal_raw_capture.__get__(session)
        holder.append(session)
        return session
    monkeypatch.setattr(s49, "_new_session", new)
    with pytest.raises(asyncio.CancelledError, match="node_shutdown"):
        asyncio.run(s49.qualify(tmp_path / "report.json", tmp_path / "java.log",
                                raw_capture_root=root))
    assert capture._file.closed
    receipt = json.loads((root / "w3-node-stdout-receipt.json").read_text())
    assert holder[0]._raw_receipt == receipt
    assert receipt["status"] == "INCOMPLETE_UNQUALIFIED"
    assert receipt["process_exit_code"] == -9
    assert receipt["shutdown_ack_count"] == 0 and not receipt["eof_observed"]
    assert receipt["seal_reason"] == "s49_cleanup_incomplete"


def test_supervisor_fault_still_writes_non_success(owner_ports, tmp_path, monkeypatch):
    s49, _, _, _, _ = owner_ports
    original = s49._cleanup_session
    async def broken(*args):
        await original(*args)
        raise RuntimeError("supervisor fault after resource cleanup")
    monkeypatch.setattr(s49, "_cleanup_session", broken)
    out = tmp_path / "supervisor.json"
    assert asyncio.run(s49.qualify(out, tmp_path / "java.log")) == 1
    report = json.loads(out.read_text())
    assert report["status"] == "FAIL"
    assert "supervisor fault" in report["cleanup_supervisor_error"]
