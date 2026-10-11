"""RSEE R1 shared runtime: deterministic source-only and synthetic controls."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.standard_env import shared_runtime as r1


@pytest.fixture
def host(monkeypatch, tmp_path):
    repo = tmp_path / "checkout"
    repo.mkdir()
    base = tmp_path / "rsee"
    base.mkdir()
    (base / "evidence").mkdir()
    (base / "venv/bin").mkdir(parents=True)
    node = base / "npm-mineflayer-4.39.0"
    node.mkdir()
    head = "a" * 40
    observations = {
        "head": head, "dirty": False, "ports": set(), "preflight_fail": False,
        "world_fail": False, "node_fail": False,
    }
    profile = {
        "qualification": "CANDIDATE_NOT_PHYSICALLY_QUALIFIED",
        "host": {},
        "llm": {"model_sha256": "b" * 64},
        "minecraft": {"version": "1.21.8"},
        "resource_key": "llama-cpp:local-gpu",
    }
    monkeypatch.setattr(r1, "read_profile", lambda _: (profile, "c" * 64))
    monkeypatch.setattr(r1, "_git_head", lambda _: observations["head"])
    monkeypatch.setattr(r1, "_git_dirty", lambda _: observations["dirty"])
    monkeypatch.setattr(r1, "_port_listeners", lambda: observations["ports"])
    monkeypatch.setattr(r1.sys, "executable", str(base / "venv/bin/python"))
    monkeypatch.setattr(r1.sys, "prefix", str(base / "venv"))
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.delenv("NODE_PATH", raising=False)

    def node_probe(root, _adapter):
        if observations["node_fail"]:
            raise ValueError("node mismatch")
        return {"node_runtime_root": str(root), "source_lock_sha256": "d" * 64}

    def local_probe(*_args, **_kwargs):
        bad = observations["preflight_fail"]
        return {
            "classification": (
                "RSEE_LOCAL_PREFLIGHT_BLOCKED"
                if bad else "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED"
            ),
            "errors": ["GGUF: SHA256 mismatch"] if bad else [],
        }

    def world_probe(*_args, **_kwargs):
        if observations["world_fail"]:
            raise ValueError("world mismatch")
        return SimpleNamespace(
            jar_sha256="e" * 64, manifest_sha256="f" * 64,
            initial_evidence_sha256="1" * 64, files=[None] * 26,
        )

    monkeypatch.setattr(r1, "verify_node_runtime", node_probe)
    monkeypatch.setattr(r1, "verify_local", local_probe)
    monkeypatch.setattr(r1, "verify_qualified_world", world_probe)
    kwargs = {
        "lane": "S", "expected_head": head,
        "evidence_dir": base / "evidence/new-run",
        "repo": repo, "base": base,
        "profile_path": tmp_path / "profile.v1.json",
    }
    return kwargs, observations


@pytest.mark.parametrize("lane", ["S", "L", "V"])
def test_shared_preflight_uses_existing_verifiers_never_grants(host, lane):
    args, _ = host
    report = r1.preflight(**{**args, "lane": lane})
    assert report["classification"] == "RSEE_R1_FILES_READY_NOT_AUTHORIZED"
    assert report["source_head"] == "a" * 40
    assert report["node_identity"]["source_lock_sha256"] == "d" * 64
    assert report["world_observation"]["snapshot_files"] == 26
    assert report["gpu_cuda_observation"] == "UNKNOWN"
    assert report["lease_observation"] == "UNKNOWN"
    assert report["resource_ownership"]["r_lane_owned_processes"] == 0
    assert report["physical_execution_authorized"] is False
    assert report["science_qualified"] is False
    assert report["evidence_output_created"] is False
    assert not args["evidence_dir"].exists()


def test_plan_performs_no_git_or_node_or_world_probe(host, monkeypatch):
    args, _ = host

    def forbid(*_args, **_kwargs):
        pytest.fail("plan must not probe worktree or model or World")

    for name in ("_git_head", "verify_local", "verify_qualified_world",
                 "verify_node_runtime", "_port_listeners"):
        monkeypatch.setattr(r1, name, forbid)
    result = r1.plan("L", repo=args["repo"], base=args["base"],
                     profile_path=args["profile_path"])
    assert result["classification"] == "RSEE_R1_PLAN_ONLY"
    assert result["source_head"] == "UNKNOWN_NOT_READ_IN_PLAN"
    assert result["execution_permission"] == "NOT_CONVEYED_BY_R1"


@pytest.mark.parametrize(("field", "value", "error"), [
    ("head", "b" * 40, "EXACT_HEAD_MISMATCH"),
    ("dirty", True, "WORKTREE_TRACKED_DIRTY"),
    ("ports", {1234}, "MODEL_OR_WORLD_PORT_IN_USE_NO_R_OWNERSHIP"),
    ("ports", {25565}, "MODEL_OR_WORLD_PORT_IN_USE_NO_R_OWNERSHIP"),
    ("preflight_fail", True, "EXISTING_PREFLIGHT_BLOCKED"),
    ("world_fail", True, "WORLD_BYTES_UNVERIFIED:ValueError"),
    ("node_fail", True, "NODE_IDENTITY_UNVERIFIED:ValueError"),
])
def test_negative_host_cases_fail_closed(host, field, value, error):
    args, observations = host
    observations[field] = value
    report = r1.preflight(**args)
    assert report["classification"] == "RSEE_R1_PREFLIGHT_BLOCKED"
    assert error in report["errors"]
    assert report["physical_execution_authorized"] is False


def test_existing_output_and_repo_output_rejected(host):
    args, _ = host
    args["evidence_dir"].mkdir()
    result = r1.preflight(**args)
    assert "EVIDENCE_OUTPUT_UNSAFE_OR_ALREADY_EXISTS" in result["errors"]
    args["evidence_dir"].rmdir()
    args["evidence_dir"] = args["repo"] / "run"
    result = r1.preflight(**args)
    assert "EVIDENCE_OUTPUT_UNSAFE_OR_ALREADY_EXISTS" in result["errors"]


def test_symlink_parent_and_asset_output_rejected(host, tmp_path):
    args, _ = host
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink = tmp_path / "sym"
    symlink.symlink_to(outside, target_is_directory=True)
    assert not r1._safe_output(symlink / "new", args["repo"], args["base"])
    assert not r1._safe_output(args["base"] / "venv/new", args["repo"], args["base"])


def test_python_node_override_and_expected_head_block(host, monkeypatch):
    args, _ = host
    monkeypatch.setenv("NODE_PATH", "/tmp/other-modules")
    report = r1.preflight(**args)
    assert "NODE_RUNTIME_OVERRIDE_PRESENT" in report["errors"]
    monkeypatch.delenv("NODE_PATH")
    args["node_runtime_root"] = args["base"] / "another-npm"
    report = r1.preflight(**args)
    assert "NONCANONICAL_NODE_ROOT" in report["errors"]
    monkeypatch.setattr(r1.sys, "prefix", "/tmp/not-rsee")
    report = r1.preflight(**args)
    assert "NONCANONICAL_PYTHON_PREFIX" in report["errors"]


def test_invalid_sha_must_fail_before_host_probes(host, monkeypatch):
    args, _ = host

    def forbid(*_args):
        pytest.fail("no host probe with invalid exact head")

    monkeypatch.setattr(r1, "_git_head", forbid)
    with pytest.raises(r1.SharedRuntimeRejected, match="exact expected HEAD"):
        r1.preflight(**{**args, "expected_head": "invalid"})


def test_original_receipts_index_without_mutating_source(tmp_path):
    a = tmp_path / "original.jsonl"
    a.write_bytes(b'{"native":1}\n')
    old = a.read_bytes()
    index = r1.read_only_receipt_index({"source": a})
    assert list(index) == [str(a)]
    assert a.read_bytes() == old
    assert len(index[str(a)]) == 64
    with pytest.raises(r1.SharedRuntimeRejected):
        r1.read_only_receipt_index({"missing": tmp_path / "missing"})


def evidence_record(path: Path, index: dict[str, str]) -> dict:
    return {
        "schema": r1.SCHEMA, "lane": "V",
        "source_head": "a" * 40, "environment_profile_sha256": "b" * 64,
        "source_session": "native-session", "world_identity": {"receipt": "original"},
        "model_identity": None, "original_receipt_refs": [
            {"path": str(path), "sha256": index[str(path)]},
        ], "action_outcome_refs": [],
        "cleanup_observations": {
            "host_cancellation": "UNKNOWN", "backend_stop_ack": "UNKNOWN",
            "slot_release": "UNKNOWN", "process_exit": "OBSERVED",
            "gpu_quiescence": "UNKNOWN", "vram_release": "UNKNOWN",
        },
        "terminal_classification": "UNDETERMINED",
        "evidence_sha256_index": index,
        "physical_execution_authorized": False,
        "science_qualified": False, "timeline_is_physical_proof": False,
    }


def test_evidence_provenance_refs_readonly_and_tamper_fails(tmp_path):
    original = tmp_path / "native-frames.jsonl"
    original.write_bytes(b'{"kind":"probe"}\n')
    index = r1.read_only_receipt_index({"frame": original})
    record = evidence_record(original, index)
    r1.validate_evidence(record, verify_receipts=True)
    original.write_bytes(b"drift")
    with pytest.raises(r1.SharedRuntimeRejected, match="source receipt bytes differ"):
        r1.validate_evidence(record, verify_receipts=True)


def test_missing_ref_unqualified_and_timeline_promotion_rejected(tmp_path):
    original = tmp_path / "native.jsonl"
    original.write_bytes(b"frame")
    index = r1.read_only_receipt_index({"raw": original})
    record = evidence_record(original, index)
    record["action_outcome_refs"] = [{"path": "/tmp/missing", "sha256": "1" * 64}]
    with pytest.raises(r1.SharedRuntimeRejected, match="reference missing"):
        r1.validate_evidence(record)
    record["action_outcome_refs"] = []
    record["timeline_is_physical_proof"] = True
    with pytest.raises(r1.SharedRuntimeRejected, match="timeline proof"):
        r1.validate_evidence(record)


def test_cli_plan_does_not_trigger_runtime(host, monkeypatch, capsys):
    args, _ = host
    monkeypatch.setattr(r1, "plan", lambda lane: {
        "classification": "RSEE_R1_PLAN_ONLY", "lane": lane,
        "physical_execution_authorized": False,
    })
    monkeypatch.setattr(r1, "preflight", lambda **_args: pytest.fail("no host preflight"))
    assert r1.main(["--lane", "S"]) == 0
    assert json.loads(capsys.readouterr().out)["lane"] == "S"
    assert r1.main(["--lane", "S", "--new-evidence-dir", str(args["evidence_dir"])]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "RSEE_R1_PREFLIGHT_BLOCKED"
