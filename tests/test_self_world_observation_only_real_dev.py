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


@pytest.mark.parametrize("fault", ("none", "probe_error", "cleanup_unconfirmed"))
def test_real_dev_owned_flow_is_dev_only_and_stops_on_failure(
    tmp_path, monkeypatch, fault,
):
    """Only synthetic fixture handles: test original calls are wired correctly."""
    from types import SimpleNamespace as NS

    from adapters.mineflayer.self_world_observation_only_dev import (
        ObservationOnlyDevReadback, ObservationOnlyRawWorldMarker,
    )
    from adapters.mineflayer.self_world_observation_only_entry import (
        ObservationOnlyEntryInventory,
    )
    from adapters.mineflayer.self_world_observation_only_lifetime import (
        ObservationOnlyLocalLifetime,
    )
    from adapters.mineflayer.self_world_observation_only_native_boundary import (
        NativeLocalDisposalReadback, NativePidFingerprint,
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
            self.started = NS(session_id="session-1")
        @classmethod
        async def launch(cls, *args, **kwargs):
            assert kwargs["raw_capture_root"].parent == evidence
            assert kwargs["bridge_path"].name == "bridge.mjs"
            seen.append("node_launch")
            return cls()
        @property
        def process_returncode(self):
            return self._process.returncode

    java = Java()
    async def ready(root, server_jar, log, *, raw_stdout_path):
        assert root.name == "w4-observe-" + run_id
        assert log.parent == raw_stdout_path.parent
        seen.append("java_launch")
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
        return NS()
    monkeypatch.setattr(runner, "_await_spawn", spawn)
    async def observe(session, request_id):
        seen.append(request_id)
        if fault == "probe_error" and request_id.startswith("w4-after"):
            raise ValueError("fixture missing postprobe")
        return NS()
    monkeypatch.setattr(runner, "_correlated_observe", observe)
    monkeypatch.setattr(
        runner, "capture_w4_collector_cursor", lambda raw: NS(start_byte=0),
    )
    async def marker(*args, **kwargs):
        seen.append("marker")
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
    result = asyncio.run(runner.run_observation_only_real_dev(**args))
    assert result["action_count"] == result["outcome_count"] == 0
    assert result["s10_update_count"] == 0
    assert result["classification"] in (
        "DEV_LOCAL_OBSERVATION_ONLY", "DEV_ONLY_NOT_QUALIFIED",
    )
    assert not result["qualification_approved"] and not result["science_qualified"]
    assert "java_launch" in seen and "node_launch" in seen and "close" in seen
    if fault != "cleanup_unconfirmed":
        assert not list(worlds.iterdir())
    assert (evidence / ("w4-observe-" + run_id) / "report.json").exists()
    if fault == "none":
        assert result["status"] == "PASS"
        assert seen.index("spawn") < seen.index("w4-before-" + run_id)
        assert seen.index("marker") < seen.index("w4-after-" + run_id)
        assert seen.index("w4-after-" + run_id) < seen.index("close")
        assert "disposal_audit" in seen
    else:
        assert result["status"] == "BLOCKED"
        assert "disposal_audit" not in seen
        assert "join" not in seen
        if fault == "cleanup_unconfirmed":
            assert result["world_root_removed"] is False
            assert list(worlds.iterdir())
