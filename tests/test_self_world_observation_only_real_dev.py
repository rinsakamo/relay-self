"""No-world tests for explicitly opt-in W4 DEV real-runner admission."""
from __future__ import annotations

import asyncio

import pytest

import adapters.mineflayer.self_world_observation_only_real_dev as runner


@pytest.mark.parametrize("fault", (
    "no_confirmation", "wrong_confirmation", "short_id", "bad_head",
    "bad_jar_hash", "relative_repo", "same_parent", "nested_parent",
))
def test_real_dev_rejects_bad_opt_in_before_any_files_or_spawn(
    tmp_path, monkeypatch, fault,
):
    repo = tmp_path / "repository"
    repo.mkdir()
    jar = tmp_path / "pinned-server.jar"
    jar.write_bytes(b"just-a-test-jar")
    worlds = tmp_path / "worlds"
    worlds.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    inputs = {
        "confirm": "DEV_OBSERVATION_ONLY",
        "expected_head": "a" * 40,
        "expected_jar_sha256": "b" * 64,
        "repository": repo, "jar": jar,
        "world_parent": worlds, "evidence_parent": evidence,
        "run_id": "0123456789abcdef",
    }
    if fault == "no_confirmation":
        inputs["confirm"] = ""
    elif fault == "wrong_confirmation":
        inputs["confirm"] = "SCIENCE"
    elif fault == "short_id":
        inputs["run_id"] = "reuse"
    elif fault == "bad_head":
        inputs["expected_head"] = "floating"
    elif fault == "bad_jar_hash":
        inputs["expected_jar_sha256"] = "unpinned"
    elif fault == "relative_repo":
        inputs["repository"] = repo.relative_to(tmp_path)
    elif fault == "same_parent":
        inputs["evidence_parent"] = worlds
    elif fault == "nested_parent":
        nested = worlds / "nested"
        nested.mkdir()
        inputs["evidence_parent"] = nested

    async def forbid(*args, **kwargs):
        raise AssertionError("invalid DEV admission started native process")
    monkeypatch.setattr(runner, "_ready_server", forbid)
    with pytest.raises(runner.ObservationDevRunBlocked):
        asyncio.run(runner.run_observation_only_real_dev(**inputs))
    assert list(evidence.iterdir()) == []


def test_real_dev_cli_requires_explicit_confirm(capsys):
    with pytest.raises(SystemExit) as exit_info:
        runner.main(["--head", "a" * 40])
    assert exit_info.value.code == 2
    assert "required" in capsys.readouterr().err


def test_real_dev_source_has_no_action_owner_or_implicit_launch():
    # Names are intentionally restricted to the observe/stop/inspect path.
    assert runner._CONFIRM == "DEV_OBSERVATION_ONLY"
    assert runner.__name__ != "__main__"


@pytest.mark.parametrize("fault", (
    "none", "probe_error", "cleanup_unconfirmed", "node_start_error",
    "java_start_error", "spawn_missing", "marker_missing", "pid_remains",
    "disposal_error", "node_start_cancel", "port_busy", "reused_world",
))
def test_real_dev_owned_flow_is_dev_only_and_stops_on_failure(
    tmp_path, monkeypatch, fault,
):
    """Only synthetic fixture handles: test original calls are wired correctly."""
    from dataclasses import dataclass
    from types import SimpleNamespace as NS

    from adapters.mineflayer.self_world_observation_only_dev import (
        ObservationOnlyDevReadback,
        ObservationOnlyRawWorldMarker,
    )
    from adapters.mineflayer.self_world_observation_only_entry import (
        ObservationOnlyEntryInventory,
    )
    from adapters.mineflayer.self_world_observation_only_lifetime import (
        ObservationOnlyLocalLifetime,
    )
    from adapters.mineflayer.self_world_observation_only_native_boundary import (
        NativeLocalDisposalReadback,
        NativePidFingerprint,
    )

    repository = tmp_path / "repository"
    worlds = tmp_path / "worlds"
    evidence = tmp_path / "evidence"
    repository.mkdir()
    worlds.mkdir()
    evidence.mkdir()
    jar = tmp_path / "server.jar"
    jar.write_bytes(b"not executed")
    run_id = "0123456789abcdef"
    seen = []
    marker_line = b"[21:00:00] [Server thread/INFO]: The time is 1234\n"
    import hashlib
    marker_hash = hashlib.sha256(marker_line).hexdigest()

    @dataclass
    class Message:
        session_id: str = "session-1"

    monkeypatch.setattr(runner, "_read_proc_starttime", lambda pid: 1 if fault == "pid_remains" else None)
    monkeypatch.setattr(runner, "_loopback_port_can_bind", lambda port: fault != "port_busy")
    if fault == "disposal_error":
        def deny_delete(*args, **kwargs):
            raise OSError("fixture disposal failed")
        monkeypatch.setattr(runner, "_delete_disposable_root", deny_delete)
    if fault == "reused_world":
        old = worlds / ("w4-observe-" + run_id)
        old.mkdir()
        (old / "original").write_text("do not remove")

    class Java:
        def __init__(self):
            self.pid = 12001
            self.returncode = None
            self.stdin = self
        async def drain(self):
            seen.append("java_drain")

    class Node:
        def __init__(self):
            self._process = NS(pid=12002, returncode=None)
            self.started = Message()
        @classmethod
        async def launch(cls, *args, **kwargs):
            assert kwargs["raw_capture_root"].parent == evidence
            assert kwargs["bridge_path"].name == "bridge.mjs"
            seen.append("node_launch")
            if fault == "node_start_error":
                raise OSError("fixture Node startup failed")
            if fault == "node_start_cancel":
                raise asyncio.CancelledError
            return cls()
        @property
        def process_returncode(self):
            return self._process.returncode

    java = Java()
    async def ready(root, server_jar, log, *, raw_stdout_path):
        assert root.name == "w4-observe-" + run_id
        assert log.parent == raw_stdout_path.parent
        seen.append("java_launch")
        if fault == "java_start_error":
            raise OSError("fixture Java startup failed")
        return java, asyncio.create_task(asyncio.sleep(0)), asyncio.Event()

    monkeypatch.setattr(runner, "_ready_server", ready)
    monkeypatch.setattr(runner, "_write_config", lambda root: seen.append("config"))
    monkeypatch.setattr(runner, "ObservationOnlyDevSession", Node)
    monkeypatch.setattr(
        runner, "inventory_observation_only_entry",
        lambda **kw: ObservationOnlyEntryInventory(
            schema="W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1",
            exact_head="a" * 40, jar_sha256="b" * 64, bridge_sha256="c" * 64,
        ),
    )
    monkeypatch.setattr(
        runner, "capture_original_native_pid",
        lambda process: NativePidFingerprint(process.pid, 10, "fake-boot"),
    )
    async def spawn(session):
        seen.append("spawn")
        if fault == "spawn_missing":
            raise TimeoutError("fixture spawn absent")
        return Message()
    monkeypatch.setattr(runner, "_await_spawn", spawn)
    async def observe(session, request_id):
        seen.append(request_id)
        if fault == "probe_error" and request_id.startswith("w4-after"):
            raise ValueError("fixture missing postprobe")
        return Message()
    monkeypatch.setattr(runner, "_correlated_observe", observe)
    monkeypatch.setattr(
        runner, "capture_w4_collector_cursor", lambda raw: NS(start_byte=0),
    )
    async def marker(*args, **kwargs):
        seen.append("marker")
        if fault == "marker_missing":
            raise TimeoutError("fixture marker absent")
        return ObservationOnlyRawWorldMarker(
            raw_start_byte=0, raw_end_byte=len(marker_line),
            raw_sha256=marker_hash, local_game_time=1234,
        )
    monkeypatch.setattr(runner, "wait_for_observation_raw_world_marker", marker)
    monkeypatch.setattr(runner, "_tail_bytes", lambda *args: marker_line)
    def command(server, value):
        assert server is java and value == "time query gametime"
        seen.append("time_command")
    monkeypatch.setattr(runner, "_command", command)
    monkeypatch.setattr(
        runner, "review_observation_only_dev_offline",
        lambda **kw: ObservationOnlyDevReadback(
            session_id="session-1", spawn_seq=1, before_seq=3, after_seq=5,
            before_source="session-1:3", after_source="session-1:5",
            marker_raw_sha256=marker_hash, marker_local_game_time=1234,
        ),
    )
    async def close(*, server, collector, session, timeout_s):
        seen.append("close")
        if fault == "cleanup_unconfirmed":
            raise RuntimeError("fixture cleanup not confirmed")
        server.returncode = 0
        if session is not None:
            session._process.returncode = 0
        await collector
        return {
            "schema": "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1",
            "classification": "LOCAL_PRODUCER_CLOSE_ONLY",
            "java_exit": 0, "node_exit": 0,
        }
    monkeypatch.setattr(runner, "close_observation_only_dev", close)
    def join(**kw):
        assert kw["node_raw_root"].parent == evidence
        seen.append("join")
        return ObservationOnlyLocalLifetime(
            schema="W4_OBSERVATION_ONLY_LOCAL_LIFETIME_JOIN_V1",
            exact_head="a" * 40, session_id="session-1",
            before_seq=3, after_seq=5,
            local_world_marker_sha256=marker_hash, local_game_time=1234,
        )
    monkeypatch.setattr(runner, "join_observation_only_local_lifetime", join)
    def disposal(**kw):
        assert not kw["disposable_world_root"].exists()
        seen.append("disposal_audit")
        return NativeLocalDisposalReadback(
            schema="W4_OBSERVATION_ONLY_NATIVE_LOCAL_DISPOSAL_V1",
            java_pid=12001, node_pid=12002, boot_id="fake-boot",
            port=25565, world_dir_name="w4-observe-" + run_id,
        )
    monkeypatch.setattr(runner, "audit_observation_only_local_disposal", disposal)

    args = dict(
        confirm="DEV_OBSERVATION_ONLY", expected_head="a" * 40,
        expected_jar_sha256="b" * 64, repository=repository, jar=jar,
        world_parent=worlds, evidence_parent=evidence, run_id=run_id,
    )
    if fault == "node_start_cancel":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(runner.run_observation_only_real_dev(**args))
        import json
        result = json.loads((evidence / ("w4-observe-" + run_id) / "report.json").read_text())
    else:
        result = asyncio.run(runner.run_observation_only_real_dev(**args))
    if fault in {"java_start_error", "port_busy", "reused_world"}:
        assert result["status"] == "BLOCKED"
        assert "node_launch" not in seen
        assert (evidence / ("w4-observe-" + run_id) / "report.json").exists()
        if fault == "reused_world":
            assert (old / "original").read_text() == "do not remove"
        return
    assert result["action_count"] == result["outcome_count"] == 0
    assert result["s10_update_count"] == 0
    assert result["classification"] in (
        "DEV_LOCAL_OBSERVATION_ONLY_PASS", "DEV_OBSERVATION_ONLY_BLOCKED",
        "CLEANUP_UNCONFIRMED",
    )
    assert not result["qualification_approved"] and not result["science_qualified"]
    assert "java_launch" in seen and "node_launch" in seen and "close" in seen
    if fault not in {"cleanup_unconfirmed", "pid_remains", "disposal_error"}:
        assert not list(worlds.iterdir())
    assert (evidence / ("w4-observe-" + run_id) / "report.json").exists()
    if fault == "none":
        assert result["status"] == "PASS"
        assert seen.index("spawn") < seen.index("w4-before-" + run_id)
        assert seen.index("marker") < seen.index("w4-after-" + run_id)
        assert seen.index("w4-after-" + run_id) < seen.index("close")
        assert "disposal_audit" in seen
        report_path = evidence / ("w4-observe-" + run_id) / "report.json"
        original = report_path.read_bytes()
        with pytest.raises(FileExistsError):
            asyncio.run(runner.run_observation_only_real_dev(**args))
        assert report_path.read_bytes() == original
    else:
        assert result["status"] == "BLOCKED"
        assert result["verdict"] in {"DEV_OBSERVATION_ONLY_BLOCKED", "CLEANUP_UNCONFIRMED"}
        assert "disposal_audit" not in seen
        assert "join" not in seen
        if fault == "cleanup_unconfirmed":
            assert result["world_root_removed"] is False
            assert list(worlds.iterdir())


def test_disposal_refuses_symlink_or_replaced_world(tmp_path):
    run_id = "0123456789abcdef"
    root = tmp_path / ("w4-observe-" + run_id)
    root.mkdir()
    identity = (root.stat().st_dev, root.stat().st_ino)
    old = tmp_path / "original"
    root.rename(old)
    root.mkdir()
    (root / "foreign").write_text("preserve")
    with pytest.raises(runner.ObservationDevRunBlocked):
        runner._delete_disposable_root(root, tmp_path, run_id=run_id, identity=identity)
    assert (root / "foreign").read_text() == "preserve"
    root.rename(tmp_path / "foreign-root")
    root.symlink_to(old, target_is_directory=True)
    with pytest.raises(runner.ObservationDevRunBlocked):
        runner._delete_disposable_root(root, tmp_path, run_id=run_id, identity=identity)
    assert old.is_dir()


def test_bounded_dev_io_cancellation_settles_exact_task():
    from adapters.mineflayer.self_world_observation_only_dev import (
        _bounded_observation_wait,
    )

    async def run():
        entered = asyncio.Event()
        settled = asyncio.Event()
        async def io():
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                settled.set()
        task = asyncio.create_task(_bounded_observation_wait(io(), timeout_s=1, name="test"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert settled.is_set()
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    asyncio.run(run())
