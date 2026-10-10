"""P0: deterministic local HTTP and fake process/proc only; no model launch."""
import asyncio
import hashlib
import json
import os
import threading
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import s60b2_owned_backend_probe as probe
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from test_feature_s60b1_adapter import envelope, response


def config(tmp_path, arm="A"):
    return probe.Config(tmp_path / "binary", tmp_path / "model.gguf", tmp_path / "source",
                        probe.BINARY, probe.MODEL, probe.SOURCE, "offline-model", 12345,
                        4352, 50, arm, "private prompt /secret/path")


def encoded(cfg):
    obj = asdict(cfg)
    for key in ("binary", "gguf", "source"):
        obj[key] = str(obj[key])
    return json.dumps(obj).encode()


def approval(data, root):
    return dict(runner_head="a" * 40, manifest_sha256=probe.MANIFEST,
                config_sha256=hashlib.sha256(data).hexdigest(), arm="A", operator_token="b" * 64,
                allow_model_gpu_launch=True, source_binary_mapping_reviewed=True,
                prior_cleanup_confirmed=True, evidence_root=str(root.resolve()))


@pytest.fixture
def admission(monkeypatch):
    for key in ("CI", "GITHUB_ACTIONS", "GITLAB_CI"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(probe, "git", lambda root, *args: "a" * 40 if args[0] == "rev-parse" else "")
    monkeypatch.setattr(probe, "digest", lambda _: probe.MANIFEST)


@pytest.mark.parametrize("argv", [[], ["--plan"], ["--plan", "--config", "/abs/private"]])
def test_default_plan_has_no_files_sockets_processes(monkeypatch, capsys, argv):
    def forbidden(*args, **kw):
        pytest.fail("plan performed external work")
    monkeypatch.setattr(probe, "digest", forbidden)
    monkeypatch.setattr(probe, "git", forbidden)
    monkeypatch.setattr(probe.socket, "socket", forbidden)
    monkeypatch.setattr(probe.asyncio, "create_subprocess_exec", forbidden)
    assert probe.main(argv) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "P0_ONLY" and result["launch_count"] == 0
    assert probe.CEILING == result["ceilings"]


def test_run_without_additional_authority_is_blocked(capsys):
    assert probe.main(["--run"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


@pytest.mark.parametrize("field,value", [
    ("binary_sha256", "0" * 64), ("model_sha256", "0" * 64), ("source_commit", "a" * 40),
    ("alias", "bad\r\nInjected: yes"), ("alias", "https://remote"),
    ("port", 80), ("port", True), ("port", 65536), ("ctx_size", 511),
    ("ctx_size", True), ("gpu_layers", 121), ("gpu_layers", -1),
    ("arm", "D"), ("prompt", ""), ("prompt", "x" * 4097), ("binary", Path("relative")),
])
def test_strict_config_rejects_mismatch(tmp_path, field, value):
    with pytest.raises(probe.ProbeRejected):
        replace(config(tmp_path), **{field: value})


@pytest.mark.parametrize("body", [b"{}", b"[]", b'{"arm":"A","arm":"B"}',
                                  b'{"x":NaN}', b"\xff", b"[" * 2000])
def test_strict_json_inputs_fail_closed(body):
    with pytest.raises(probe.ProbeRejected):
        probe.Config.read(body)


def test_config_no_arbitrary_fields_or_relative_paths(tmp_path):
    obj = json.loads(encoded(config(tmp_path)))
    obj["flags"] = ["--host", "0.0.0.0"]
    with pytest.raises(probe.ProbeRejected):
        probe.Config.read(json.dumps(obj).encode())
    del obj["flags"]
    obj["binary"] = "relative"
    with pytest.raises(probe.ProbeRejected):
        probe.Config.read(json.dumps(obj).encode())


@pytest.mark.parametrize("field,value", [
    ("runner_head", "c" * 40), ("manifest_sha256", "0" * 64),
    ("config_sha256", "0" * 64), ("arm", "B"), ("operator_token", "allow"),
    ("allow_model_gpu_launch", 1), ("source_binary_mapping_reviewed", False),
    ("prior_cleanup_confirmed", False), ("evidence_root", "/another/root"),
])
def test_grant_exact_bindings(tmp_path, admission, field, value):
    data = encoded(config(tmp_path))
    grant = approval(data, tmp_path / "receipt")
    grant[field] = value
    with pytest.raises(probe.ProbeRejected):
        probe.authorize(data, json.dumps(grant).encode(), tmp_path / "receipt")


def test_grant_complete_and_exact_clean_head(tmp_path, admission, monkeypatch):
    data = encoded(config(tmp_path))
    root = tmp_path / "receipt"
    grant = json.dumps(approval(data, root)).encode()
    assert probe.authorize(data, grant, root) == config(tmp_path)
    monkeypatch.setattr(probe, "git", lambda root, *args: "a" * 40 if args[0] == "rev-parse" else " M file")
    with pytest.raises(probe.ProbeRejected):
        probe.authorize(data, grant, root)


@pytest.mark.parametrize("key", ["CI", "GITHUB_ACTIONS", "GITLAB_CI"])
def test_ci_never_run(tmp_path, admission, monkeypatch, key):
    monkeypatch.setenv(key, "true")
    def forbidden(*args, **kw):
        pytest.fail("CI reached physical path")
    monkeypatch.setattr(probe, "git", forbidden)
    with pytest.raises(probe.ProbeRejected, match="CI"):
        probe.authorize(encoded(config(tmp_path)), b"{}", tmp_path / "receipt")


def test_shell_safe_exact_argv(tmp_path):
    cfg = replace(config(tmp_path), binary=tmp_path / "binary $(touch injected); `false`")
    argv = cfg.argv()
    assert argv[0] == str(cfg.binary) and argv.count("--model") == 1
    assert argv[argv.index("--host") + 1] == "127.0.0.1"
    assert argv[argv.index("--parallel") + 1] == "1" and argv[-1] == "--slots"


def test_occupied_port_and_invalid_loopback_input(tmp_path):
    with probe.socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        with pytest.raises(OSError):
            probe.available_port(listener.getsockname()[1])


def test_bounded_files_and_duplicate_reservation(tmp_path):
    path = tmp_path / "private"
    path.write_bytes(b"x" * 8193)
    with pytest.raises(probe.ProbeRejected):
        probe.bounded_read(path)
    root = tmp_path / "receipt"
    journal = probe.Journal(root)
    journal.emit("UNDETERMINED")
    journal.close()
    with pytest.raises(FileExistsError):
        probe.Journal(root)
    assert len((root / "events.jsonl").read_text().splitlines()) == 2
    assert (root.stat().st_mode & 0o777) == 0o700


def test_journal_sanitized_bounded_no_private_content(tmp_path):
    journal = probe.Journal(tmp_path / "receipt")
    with pytest.raises(probe.ProbeRejected):
        journal.emit("UNDETERMINED", prompt="private")
    with pytest.raises(probe.ProbeRejected):
        journal.emit("UNDETERMINED", runner_head="/secret/path")
    with pytest.raises(probe.ProbeRejected):
        journal.emit("UNDETERMINED", elapsed_s=float("nan"))
    for _ in range(255):
        journal.emit("BACKEND_BUSY_OBSERVED", busy=True, decoded=1)
    with pytest.raises(probe.ProbeRejected):
        journal.emit("UNDETERMINED")
    journal.close()
    assert (journal.root / "events.jsonl").stat().st_size < 256 * 2048


def stock_slot(cfg, busy=True, task=1):
    return dict(id=0, n_ctx=cfg.ctx_size, is_processing=busy, id_task=task,
                n_prompt_tokens_processed=8,
                next_token=[dict(n_decoded=2)], params={"prompt": "private"},
                prompt="private prompt /secret/path", generated="transient-output")


def test_slot_sanitization_and_no_hardware_implication(tmp_path):
    cfg = config(tmp_path)
    slot = probe.slot_snapshot(json.dumps([stock_slot(cfg)]).encode(), cfg)
    assert slot.busy and slot.decoded == 2 and slot.task == 1
    assert "private" not in repr(slot) and "transient-output" not in repr(slot)
    idle = probe.slot_snapshot(json.dumps([stock_slot(cfg, False)]).encode(), cfg)
    assert idle == probe.Slot(False, None, 0, 0)
    assert not hasattr(slot, "gpu_quiesced")


@pytest.mark.parametrize("field,value", [
    ("id", True), ("id", 1), ("n_ctx", 512), ("is_processing", 1),
    ("id_task", True), ("id_task", -1), ("n_prompt_tokens_processed", -1),
    ("next_token", []), ("next_token", [{"n_decoded": True}]),
    ("next_token", [{"n_decoded": -1}]),
])
def test_version_specific_slot_parser_negatives(tmp_path, field, value):
    cfg = config(tmp_path)
    obj = stock_slot(cfg)
    obj[field] = value
    with pytest.raises(probe.ProbeRejected):
        probe.slot_snapshot(json.dumps([obj]).encode(), cfg)


@pytest.mark.parametrize("data", [b"{}", b"[]", b"[{},{}]", b'[null]', b'x' * 131073,
                                  b'[{"id":0,"id":0}]'])
def test_absent_or_unknown_slot_evidence_fails_closed(tmp_path, data):
    with pytest.raises(probe.ProbeRejected):
        probe.slot_snapshot(data, config(tmp_path))


def test_preflight_hash_mismatch_never_launch(tmp_path):
    cfg = config(tmp_path)
    cfg.binary.write_bytes(b"not stock")
    cfg.binary.chmod(0o700)
    cfg.gguf.write_bytes(b"GGUFfake")
    with pytest.raises(probe.ProbeRejected, match="pinned file"):
        probe.preflight(cfg)


def test_source_and_model_magic_and_toctou_negatives(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    cfg.binary.write_bytes(b"not stock")
    cfg.binary.chmod(0o700)
    cfg.gguf.write_bytes(b"GGUFfake")
    monkeypatch.setattr(probe, "digest", lambda p: probe.BINARY if p == cfg.binary else
                        probe.MODEL if p == cfg.gguf else probe.SOURCE_FILES[str(p.relative_to(cfg.source))])
    monkeypatch.setattr(probe, "git", lambda root, *a: probe.SOURCE if a[0] == "rev-parse" else "")
    monkeypatch.setattr(probe, "available_port", lambda _: None)
    pins = probe.preflight(cfg)
    assert pins[0] == probe.fingerprint(cfg.binary)
    cfg.gguf.write_bytes(b"xxxxfake")
    with pytest.raises(probe.ProbeRejected, match="model source"):
        probe.preflight(cfg)
    cfg.gguf.write_bytes(b"GGUFfake")
    monkeypatch.setattr(probe, "git", lambda *a: "unknown")
    with pytest.raises(probe.ProbeRejected, match="SLOT_IDLE"):
        probe.preflight(cfg)
    monkeypatch.setattr(probe, "git", lambda root, *a: probe.SOURCE if a[0] == "rev-parse" else "")
    monkeypatch.setattr(probe, "available_port", lambda _: cfg.gguf.write_bytes(b"GGUFchanged"))
    with pytest.raises(probe.ProbeRejected, match="changed"):
        probe.preflight(cfg)


def proc_fixture(tmp_path):
    cfg = config(tmp_path)
    cfg.binary.write_bytes(b"fake binary")
    cfg.gguf.write_bytes(b"GGUFfake")
    base = tmp_path / "proc" / "345"
    (base / "fd").mkdir(parents=True)
    (base / "net").mkdir()
    (base / "exe").symlink_to(cfg.binary)
    (base / "stat").write_text("345 (comm (with spaces)) S " + "0 " * 18 + "1234 0")
    (base / "cmdline").write_bytes(b"\0".join(x.encode() for x in cfg.argv()) + b"\0")
    (base / "fd" / "7").symlink_to("socket:[987]")
    (base / "net/tcp").write_text("header\n0: 0100007F:3039 00000000:0000 0A 0 0 0 0 0 987\n")
    stat = cfg.gguf.stat()
    device = f"{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}"
    (base / "maps").write_text(f"1000-2000 r--p 0000 {device} {stat.st_ino} /private/model\n")
    witness = probe.ProcessWitness(cfg, 345, (probe.fingerprint(cfg.binary), probe.fingerprint(cfg.gguf)),
                                   proc=tmp_path / "proc")
    return cfg, base, witness


def test_process_pid_starttime_exe_cmdline_listener_model_match(tmp_path):
    cfg, base, witness = proc_fixture(tmp_path)
    witness.verify()
    (base / "maps").write_text("")
    witness.verify(model=False)
    with pytest.raises(probe.ProbeRejected, match="model"):
        witness.verify()


@pytest.mark.parametrize("mutation", ["start", "argv", "exe", "model", "foreign", "public", "duplicate"])
def test_proc_identity_rejects_foreign_or_changed_sources(tmp_path, mutation):
    cfg, base, witness = proc_fixture(tmp_path)
    if mutation == "start":
        (base / "stat").write_text("345 (x) S " + "0 " * 18 + "5678 0")
    elif mutation == "argv":
        (base / "cmdline").write_bytes(b"foreign\0")
    elif mutation == "exe":
        cfg.binary.write_bytes(b"changed executable")
    elif mutation == "model":
        cfg.gguf.write_bytes(b"changed model")
    elif mutation == "foreign":
        (base / "fd/7").unlink()
    elif mutation == "public":
        (base / "net/tcp").write_text("header\n0: 00000000:3039 00000000:0000 0A 0 0 0 0 0 987\n")
    else:
        data = (base / "net/tcp").read_text()
        (base / "net/tcp").write_text(data + data.splitlines()[1] + "\n")
    with pytest.raises(probe.ProbeRejected):
        witness.verify()


class FakeStock:
    """Barrier controlled stock-shape HTTP. EOF deliberately does not stop backend."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.posts = []
        self.busy = False
        self.release = []
        self.tasks = set()
        self.writers = set()
        self.disconnected = asyncio.Event()
        self.slot_body = None

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.cfg = replace(self.cfg, port=self.server.sockets[0].getsockname()[1])
        return self

    async def handle(self, reader, writer):
        self.tasks.add(asyncio.current_task())
        self.writers.add(writer)
        children = []
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            if head.startswith(b"POST "):
                length = next(int(x.split(b":")[1]) for x in head.split(b"\r\n")
                              if x.startswith(b"Content-Length:"))
                await reader.readexactly(length)
                self.posts.append(head)
                self.busy = True
                release = asyncio.Event()
                self.release.append(release)
                children = [asyncio.create_task(reader.read()), asyncio.create_task(release.wait())]
                done, _ = await asyncio.wait(children, return_when=asyncio.FIRST_COMPLETED)
                if children[0] in done:
                    self.disconnected.set()
                    await release.wait()  # continues after EOF, independent busy retained
                self.busy = False
                obj = envelope()
                obj["system_fingerprint"] = probe.FINGERPRINT
                writer.write(response(json.dumps(obj).encode()))
            else:
                if head.startswith(b"GET /health "):
                    body = b'{"status":"ok"}'
                else:
                    assert head.startswith(b"GET /slots ")
                    body = self.slot_body or json.dumps([stock_slot(self.cfg, self.busy,
                                                                  len(self.posts))]).encode()
                writer.write(response(body))
            await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            for task in children:
                task.cancel()
            await asyncio.gather(*children, return_exceptions=True)
            writer.close()
            self.writers.discard(writer)
            self.tasks.discard(asyncio.current_task())

    async def __aexit__(self, *args):
        self.server.close()
        for release in self.release:
            release.set()
        for writer in tuple(self.writers):
            writer.close()
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.server.wait_closed()


def accelerated(monkeypatch):
    real_sleep = asyncio.sleep
    real_time = probe.time.monotonic
    now = [real_time()]
    async def sleep(seconds):
        now[0] += seconds
        # Drain real loopback events, no wall-clock acceptance criterion.
        for _ in range(15):
            await real_sleep(0)
    monkeypatch.setattr(probe, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(probe, "asyncio", SimpleNamespace(**{
        name: getattr(asyncio, name) for name in dir(asyncio) if not name.startswith("__")
    }))
    monkeypatch.setattr(probe.asyncio, "sleep", sleep)
    return now


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_actual_runner_measurement_arms_fake_http_and_independent_l0(tmp_path, monkeypatch, arm):
    async def scenario():
        accelerated(monkeypatch)
        async with FakeStock(config(tmp_path, arm)) as server:
            journal = probe.Journal(tmp_path / "receipt")
            original = journal.emit
            loop = asyncio.get_running_loop()
            foreground_thread = threading.get_ident()
            def emit(phase, **facts):
                assert threading.get_ident() != foreground_thread
                original(phase, **facts)
                if arm != "C" and phase == "L0_CALLBACK_RETURN":
                    loop.call_soon_threadsafe(server.release[0].set)
                if arm != "C" and phase == "NEW_INFERENCE_STARTED" and facts["generation"] > 1:
                    loop.call_soon_threadsafe(server.release[-1].set)
            monkeypatch.setattr(journal, "emit", emit)
            checks = []
            witness = SimpleNamespace(verify=lambda **kw: checks.append(server.busy))
            result = await asyncio.wait_for(probe.measure(server.cfg, witness, journal), 5)
            journal.close()
            rows = [json.loads(x) for x in (journal.root / "events.jsonl").read_text().splitlines()]
            phases = [x["phase"] for x in rows]
            assert phases.index("L0_CALLBACK_ENTER") < phases.index("L0_CALLBACK_RETURN")
            assert checks and result["hardware_evidence"] is False and result["world_actions"] == 0
            assert "private" not in json.dumps(rows) and "transient-output" not in json.dumps(rows)
            if arm == "C":
                await asyncio.wait_for(server.disconnected.wait(), 1)
                assert len(server.posts) == result["transport_starts"] == 1
                assert server.busy and result["complete_responses"] == 0
                assert "CANCEL_UNCONFIRMED_BACKEND_BUSY" in phases
                assert "PROVIDER_TERMINAL_OBSERVED" not in phases
                assert "BACKEND_BUSY_OBSERVED" in phases[phases.index("TRANSPORT_DISCONNECTED") + 1:]
            else:
                assert len(server.posts) == result["transport_starts"] == 2
                assert result["independently_observed_starts"] == result["complete_responses"] == 2
                assert ("STALE_REJECTED" in phases) == (arm == "B")
            assert not set(phases) & {"STOP_ACK", "GPU_COMPUTE_QUIESCED", "VRAM_RELEASED"}
            assert not server.tasks or all(not t.done() for t in server.tasks)
    asyncio.run(scenario())


def test_unsupported_slots_and_fixed_endpoints(tmp_path):
    async def scenario():
        async with FakeStock(config(tmp_path)) as server:
            assert probe.parse_json(await probe.get_json(server.cfg, "/health")) == {"status": "ok"}
            server.slot_body = b'{"error":"unsupported"}'
            with pytest.raises(probe.ProbeRejected):
                probe.slot_snapshot(await probe.get_json(server.cfg, "/slots"), server.cfg)
            with pytest.raises(probe.ProbeRejected):
                await probe.get_json(server.cfg, "https://remote")
            assert not server.posts
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value", [
    ("model", "foreign-model"), ("choices", []),
    ("choices", [dict(message=dict(role="assistant", content="x"), finish_reason="tool_calls")]),
    ("timings", {"predicted_ms": float("nan")}), ("__verbose", {"prompt": "private"}),
])
def test_stock_response_compatibility_negatives(tmp_path, field, value):
    async def scenario():
        adapter = LoopbackDisplacementAdapter(LoopbackTransportConfig("offline-model", 12345), lambda _: {})
        obj = envelope()
        obj[field] = value
        with pytest.raises(TransportUnconfirmed):
            adapter._validate_response(json.dumps(obj).encode(), 256)
        await adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("forced", [False, True])
def test_owned_cleanup_uses_only_owned_group_and_never_stop_ack(tmp_path, monkeypatch, forced):
    async def scenario():
        journal = probe.Journal(tmp_path / "receipt")
        process = SimpleNamespace(pid=123, returncode=None)
        calls = []
        async def wait():
            if forced and not calls.count((123, probe.signal.SIGKILL)):
                raise TimeoutError
            process.returncode = -9 if forced else 0
            return process.returncode
        process.wait = wait
        monkeypatch.setattr(probe.os, "killpg", lambda pid, sig: calls.append((pid, sig)))
        await probe.cleanup(process, journal)
        journal.close()
        phases = [json.loads(s)["phase"] for s in (journal.root / "events.jsonl").read_text().splitlines()]
        assert calls[0] == (123, probe.signal.SIGTERM)
        assert ("OWNED_PROCESS_FORCED_KILL" in phases) == forced
        assert "OWNED_PROCESS_EXIT" in phases and "STOP_ACK" not in phases
    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["preflight", "spawn", "measure", "cleanup"])
def test_one_shot_failure_inclusive_reserved_no_duplicate_start(tmp_path, monkeypatch, failure):
    async def scenario():
        cfg = config(tmp_path)
        monkeypatch.setattr(probe, "authorize", lambda *args: cfg)
        monkeypatch.setattr(probe, "git", lambda *args: "a" * 40)
        calls = []
        def preflight(_):
            if failure == "preflight":
                raise probe.ProbeRejected("private diagnostic")
            return ()
        monkeypatch.setattr(probe, "preflight", preflight)
        process = SimpleNamespace(pid=777, returncode=0)
        async def spawn(*args, **kw):
            calls.append((args, kw))
            if failure == "spawn":
                raise OSError("private diagnostic")
            return process
        monkeypatch.setattr(probe.asyncio, "create_subprocess_exec", spawn)
        monkeypatch.setattr(probe, "ProcessWitness", lambda *args: None)
        async def ready(*args):
            pass
        monkeypatch.setattr(probe, "ready", ready)
        async def measure(*args):
            if failure == "measure":
                raise TimeoutError
            return dict(status="P1_RECEIPTS_REVIEW_REQUIRED")
        monkeypatch.setattr(probe, "measure", measure)
        async def cleanup(*args):
            if failure == "cleanup":
                raise TimeoutError
        monkeypatch.setattr(probe, "cleanup", cleanup)
        root = tmp_path / "receipt"
        result = await probe.run(b"config", b"approval", root)
        assert result["status"] == ("CLEANUP_UNCONFIRMED" if failure == "cleanup" else "UNDETERMINED")
        assert len(calls) == (0 if failure == "preflight" else 1)
        if calls:
            args, kw = calls[0]
            assert args == cfg.argv() and kw["start_new_session"] is True
            assert kw["env"] == {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
            assert "shell" not in kw and kw["stdout"] == asyncio.subprocess.DEVNULL
        with pytest.raises(FileExistsError):
            await probe.run(b"config", b"approval", root)
        assert len(calls) <= 1
        assert "private" not in (root / "events.jsonl").read_text()
        summary = (root / "summary.json").read_text()
        assert cfg.prompt not in summary and str(cfg.binary) not in summary
        assert "private diagnostic" not in summary
    asyncio.run(scenario())


def test_absolute_arm_deadline_and_adapter_cleanup(tmp_path, monkeypatch):
    async def scenario():
        closed = []
        original_close = LoopbackDisplacementAdapter.aclose
        async def close(self):
            closed.append(self)
            await original_close(self)
        monkeypatch.setattr(LoopbackDisplacementAdapter, "aclose", close)
        class Deadline:
            async def __aenter__(self):
                raise TimeoutError
            async def __aexit__(self, *args):
                pass
        observed = []
        monkeypatch.setattr(probe.asyncio, "timeout_at", lambda deadline:
                            (observed.append(deadline) or Deadline()))
        journal = probe.Journal(tmp_path / "receipt")
        with pytest.raises(TimeoutError):
            await probe.measure(config(tmp_path), SimpleNamespace(verify=lambda: None), journal)
        journal.close()
        assert len(closed) == 1 and closed[0]._closed
        assert observed[0] >= journal.start + 60
    asyncio.run(scenario())


def test_startup_timeout_and_dead_process_zero_inference(tmp_path, monkeypatch):
    async def scenario():
        accelerated(monkeypatch)
        called = []
        async def no_health(cfg, endpoint):
            called.append(endpoint)
            raise TransportUnconfirmed("health unavailable")
        monkeypatch.setattr(probe, "get_json", no_health)
        witness = SimpleNamespace(verify=lambda **kwargs: None)
        process = SimpleNamespace(returncode=None)
        with pytest.raises(probe.ProbeRejected, match="startup"):
            await probe.ready(config(tmp_path), process, witness)
        assert len(called) == 180 and set(called) == {"/health"}
        called.clear()
        process.returncode = 1
        with pytest.raises(probe.ProbeRejected):
            await probe.ready(config(tmp_path), process, witness)
        assert not called
    asyncio.run(scenario())


def test_busy_on_arrival_blocks_before_post(tmp_path, monkeypatch):
    async def scenario():
        accelerated(monkeypatch)
        async with FakeStock(config(tmp_path)) as server:
            server.busy = True
            journal = probe.Journal(tmp_path / "receipt")
            with pytest.raises(probe.ProbeRejected, match="initial backend busy"):
                await probe.measure(server.cfg, SimpleNamespace(verify=lambda: None), journal)
            journal.close()
            assert not server.posts
    asyncio.run(scenario())


def test_no_observed_progress_exhausts_budget_without_inventing_start(tmp_path, monkeypatch):
    async def scenario():
        accelerated(monkeypatch)
        async with FakeStock(config(tmp_path)) as server:
            server.slot_body = json.dumps([stock_slot(server.cfg, False)]).encode()
            journal = probe.Journal(tmp_path / "receipt")
            with pytest.raises(probe.ProbeRejected, match="budget exhausted"):
                await probe.measure(server.cfg, SimpleNamespace(verify=lambda: None), journal)
            journal.close()
            rows = [json.loads(x) for x in (journal.root / "events.jsonl").read_text().splitlines()]
            assert len(server.posts) == 1
            assert sum(r["phase"] == "SAME_PROCESS_SLOT_IDLE_OBSERVED" for r in rows) == 120
            assert not any(r["phase"] == "NEW_INFERENCE_STARTED" for r in rows)
    asyncio.run(scenario())


def test_slot_identity_failure_stops_arm_without_successor(tmp_path, monkeypatch):
    async def scenario():
        accelerated(monkeypatch)
        async with FakeStock(config(tmp_path)) as server:
            calls = []
            def verify():
                calls.append(None)
                if len(calls) == 4:
                    raise probe.ProbeRejected("foreign process")
            journal = probe.Journal(tmp_path / "receipt")
            with pytest.raises(probe.ProbeRejected, match="foreign"):
                await probe.measure(server.cfg, SimpleNamespace(verify=verify), journal)
            journal.close()
            assert len(server.posts) == 1
            assert "NEW_INFERENCE_STARTED" not in (journal.root / "events.jsonl").read_text()
    asyncio.run(scenario())


def test_b_ignored_cancel_complete_after_pending_deadline_skips_no_retry(tmp_path, monkeypatch):
    async def scenario():
        clock = accelerated(monkeypatch)
        async with FakeStock(config(tmp_path, "B")) as server:
            journal = probe.Journal(tmp_path / "receipt")
            original = journal.emit
            loop = asyncio.get_running_loop()
            foreground_thread = threading.get_ident()
            def emit(phase, **facts):
                assert threading.get_ident() != foreground_thread
                original(phase, **facts)
                if phase == "L0_CALLBACK_RETURN":
                    clock[0] += 6
                    loop.call_soon_threadsafe(server.release[0].set)
            monkeypatch.setattr(journal, "emit", emit)
            result = await probe.measure(server.cfg, SimpleNamespace(verify=lambda: None), journal)
            journal.close()
            assert result["transport_starts"] == len(server.posts) == 1
            assert result["complete_responses"] == 1
            data = (journal.root / "events.jsonl").read_text()
            assert "STALE_REJECTED" in data and "CANCEL_UNCONFIRMED_BACKEND_BUSY" in data
    asyncio.run(scenario())


def test_cancel_during_process_creation_retains_child_for_cleanup(tmp_path, monkeypatch):
    async def scenario():
        cfg = config(tmp_path)
        monkeypatch.setattr(probe, "authorize", lambda *args: cfg)
        monkeypatch.setattr(probe, "git", lambda *args: "a" * 40)
        monkeypatch.setattr(probe, "preflight", lambda cfg: ())
        creation = asyncio.Event()
        release = asyncio.Event()
        child = SimpleNamespace(pid=777, returncode=0)
        calls = []
        async def spawn(*args, **kw):
            creation.set()
            await release.wait()
            return child
        monkeypatch.setattr(probe.asyncio, "create_subprocess_exec", spawn)
        async def cleanup(process, journal):
            calls.append(process)
            journal.emit("OWNED_PROCESS_EXIT", returncode=0)
        monkeypatch.setattr(probe, "cleanup", cleanup)
        root = tmp_path / "receipt"
        task = asyncio.create_task(probe.run(b"config", b"approval", root))
        await creation.wait()
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert calls == [child]
        data = (root / "events.jsonl").read_text()
        assert "HOST_ABORTED" in data and "OWNED_PROCESS_EXIT" in data
        assert json.loads((root / "summary.json").read_text())["status"] == "UNDETERMINED"
    asyncio.run(scenario())


@pytest.mark.parametrize("mutation", ["model_missing", "model_wrong", "source_missing", "source_wrong",
                                      "usage_missing"])
def test_b2_stock_response_requires_actual_alias_and_source(tmp_path, mutation):
    async def scenario():
        journal = probe.Journal(tmp_path / "receipt")
        adapter = probe.MeasuredTransport(LoopbackTransportConfig("offline-model", 12345),
                                           lambda _: {}, journal)
        obj = envelope()
        obj["system_fingerprint"] = probe.FINGERPRINT
        assert adapter._validate_response(json.dumps(obj).encode(), 256) == "transient-output"
        field = "model" if mutation.startswith("model") else (
            "system_fingerprint" if mutation.startswith("source") else "usage")
        if mutation.endswith("missing"):
            obj.pop(field)
        else:
            obj[field] = "foreign"
        with pytest.raises(TransportUnconfirmed):
            adapter._validate_response(json.dumps(obj).encode(), 256)
        await adapter.aclose()
        journal.close()
    asyncio.run(scenario())
