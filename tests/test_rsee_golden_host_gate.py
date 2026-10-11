"""No-process host Golden Run gate: strict offline report and negative controls."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.standard_env import golden_host_gate as gate


@pytest.fixture
def fake_host(monkeypatch, tmp_path):
    repo = tmp_path / "worktree"
    repo.mkdir()
    new_output = tmp_path / "brand-new-run"
    head = "22c5e188c63c3f7d5fb89690e0fa8f6eb783d07d"
    checks: dict[str, object] = {"head": head, "dirty": False, "ports": set(), "nfiles": 26}

    monkeypatch.setattr(gate, "_git_head", lambda _: checks["head"])
    monkeypatch.setattr(gate, "_git_dirty", lambda _: checks["dirty"])
    monkeypatch.setattr(gate, "_port_listeners", lambda: checks["ports"])
    monkeypatch.setattr(gate, "verify_local", lambda *a, **k: {
        "classification": "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED",
        "errors": [], "product_profile_audit": {"classification": "STATIC_PASS", "gaps": []},
        "golden_run_blockers": [
            "HISTORICAL #580 world unbound -- intentionally ignored",
        ],
    })
    monkeypatch.setattr(gate, "verify_qualified_world", lambda *_args: SimpleNamespace(
        files=[None] * int(checks["nfiles"]),
        manifest_sha256="a" * 64,
        initial_evidence_sha256="b" * 64,
    ))
    monkeypatch.setattr(gate, "_observed_native_initial", lambda _: {
        "native_complete_saved_state_checked": True
    })
    return {
        "expected_head": head, "output_dir": new_output,
        "repo": repo, "gguf": tmp_path / "model.gguf",
        "llama_server": tmp_path / "llama-server",
        "jar": tmp_path / "jar",
        "snapshot": tmp_path / "snapshot",
        "manifest": tmp_path / "manifest",
        "initial_evidence": tmp_path / "initial",
    }, checks


def test_one_offline_command_claims_no_runtime_or_new_authorization(fake_host):
    args, checks = fake_host
    result = gate.audit(**args)
    assert result["classification"] == "RSEE_GOLDEN_HOST_FILES_READY_NOT_AUTHORIZED"
    assert result["errors"] == []
    assert result["world"]["world_file_count"] == 26
    assert result["physical_execution_authorized"] is False
    assert result["golden_run"] == "NOT_RUN"
    assert result["llm_post"] == result["new_world_launch"] == 0
    assert result["runtime_props_slots_qualified"] is False
    assert result["thinking_off_execution_qualified"] is False
    assert result["gpu_execution_qualified"] is False
    assert result["structured_generation_qualified"] is False
    assert result["port_listener_snapshot"]["exclusive_port_ownership_qualified"] is False
    assert checks["nfiles"] == 26
    assert not args["output_dir"].exists()


@pytest.mark.parametrize(("key", "value", "expected"), [
    ("head", "0" * 40, "EXACT_WORKTREE_HEAD_MISMATCH"),
    ("dirty", True, "WORKTREE_TRACKED_DIFF_UNCOMMITTED"),
    ("ports", {1234}, "EXPECTED_MODEL_OR_WORLD_PORT_HAS_LISTENER"),
    ("ports", {25565}, "EXPECTED_MODEL_OR_WORLD_PORT_HAS_LISTENER"),
    ("nfiles", 25, "EXACT_583_NATIVE_WORLD_IDENTITY_UNCONFIRMED"),
])
def test_changed_head_dirty_worktree_busy_port_or_unqualified_world_blocks(
    fake_host, key, value, expected,
):
    args, checks = fake_host
    checks[key] = value
    result = gate.audit(**args)
    assert result["classification"] == "RSEE_GOLDEN_HOST_OFFLINE_BLOCKED"
    assert expected in result["errors"]
    assert result["physical_execution_authorized"] is False


def test_preexisting_or_symlinked_destination_never_admitted(fake_host):
    args, _ = fake_host
    args["output_dir"].mkdir()
    result = gate.audit(**args)
    assert "EVIDENCE_DESTINATION_NOT_FRESH" in result["errors"]
    args["output_dir"].rmdir()
    target = args["repo"]
    args["output_dir"].symlink_to(target, target_is_directory=True)
    result = gate.audit(**args)
    assert "EVIDENCE_DESTINATION_NOT_FRESH" in result["errors"]


def test_unexpected_node_options_blocks(fake_host, monkeypatch):
    args, _ = fake_host
    monkeypatch.setenv("NODE_OPTIONS", "--require=/tmp/untrusted-shim")
    report = gate.audit(**args)
    assert report["classification"] == "RSEE_GOLDEN_HOST_OFFLINE_BLOCKED"
    assert "NODE_OPTIONS_OVERRIDE_PRESENT" in report["errors"]


def test_real_local_preflight_mismatch_not_promoted_by_world_pass(fake_host, monkeypatch):
    args, _ = fake_host
    monkeypatch.setattr(gate, "verify_local", lambda *a, **k: {
        "classification": "RSEE_LOCAL_PREFLIGHT_BLOCKED",
        "errors": ["GGUF: SHA256 mismatch"],
        "product_profile_audit": {"gaps": ["L2_REQUEST_REASONING_OFF_NOT_EXPLICIT"]},
    })
    report = gate.audit(**args)
    assert "HOST_ARTIFACT_OR_DEPENDENCY_MISMATCH" in report["errors"]
    assert "GGUF: SHA256 mismatch" in report["errors"]
    assert "PRODUCT_STATIC_PROFILE_GAPS" in report["errors"]


def test_invalid_head_rejected_before_any_subprocess_or_local_read(fake_host, monkeypatch):
    args, _ = fake_host

    def must_not_call(*_args, **_kwargs):
        pytest.fail("no git/process/artifact I/O on invalid HEAD")

    monkeypatch.setattr(gate, "_git_head", must_not_call)
    with pytest.raises(gate.HostGateRejected, match="exact 40-digit"):
        gate.audit(**{**args, "expected_head": "not-a-sha"})


def test_native_readback_keeps_spawn_and_stopped_player_separate(tmp_path):
    path = tmp_path / "initial.json"
    frame = {
        "schema": "RSEE_BOOTSTRAP_NATIVE_INITIAL_V1",
        "initial_spawn": {"kind": "spawn", "seq": 1, "session_id": "s"},
        "initial_probe": {
            "kind": "probe", "seq": 2, "session_id": "s",
            "request_id": "rsee-bootstrap:initial:001",
            "snapshot": {
                "position": {"x": -6.5, "y": -60.0, "z": 10.5},
                "health": 20, "food": 20, "inventory": [],
            },
        },
        "native_stopped_state": {
            "stored_player": {
                "position": [-6.5, -60.0, 10.5],
                "rotation_yaw_pitch": [0, 0],
                "health": 20, "food": 20, "inventory": [],
            },
            "stored_world": {
                "day_time": 18000, "raining": 0, "thundering": 0,
                "full_gamerules": {
                    "doDaylightCycle": "false", "doWeatherCycle": "false",
                    "doMobSpawning": "false",
                },
            },
        },
        "java_clean_exit_observed": True,
        "bridge_clean_exit_observed": True,
    }
    path.write_text(json.dumps(frame), encoding="utf-8")
    report = gate._observed_native_initial(path)
    assert report["player_position"] == [-6.5, -60.0, 10.5]
    assert report["stopped_yaw_pitch"] == [0, 0]
    for alteration in (
        ("initial_probe", "seq", 3),
        ("initial_probe", "session_id", "foreign"),
        ("native_stopped_state", "stored_player", {}),
    ):
        forged = json.loads(json.dumps(frame))
        forged[alteration[0]][alteration[1]] = alteration[2]
        path.write_text(json.dumps(forged))
        with pytest.raises(gate.HostGateRejected):
            gate._observed_native_initial(path)


def test_main_never_starts_physical_runtime_on_invalid_head(tmp_path, capsys, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("no runtime or Git subprocess on invalid SHA")

    monkeypatch.setattr(gate, "_git_head", forbidden)
    path = tmp_path / "unused"
    flags = [
        "--expected-head", "INVALID",
        "--new-output-dir", str(path),
        "--jar", str(path), "--snapshot", str(path),
        "--manifest", str(path), "--initial-evidence", str(path),
        "--gguf", str(path), "--llama-server", str(path),
    ]
    assert gate.main(flags) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["classification"] == "RSEE_GOLDEN_HOST_OFFLINE_BLOCKED"
    assert output["physical_execution_authorized"] is False
    assert not path.exists()
