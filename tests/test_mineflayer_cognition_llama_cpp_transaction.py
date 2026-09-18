from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_llama_cpp_transaction as tx


def _valid_runtime(artifact: Path, *, model_ftype: str = "Q4_K - Medium"):
    revision = "a" * 40
    return {
        "health": {"status": "ok"},
        "models": {"data": [{"id": "model-x"}]},
        "props": {
            "build_info": f"llama.cpp {revision} build 10874",
            "model_alias": "model-x",
            "model_path": str(artifact),
            "model_ftype": model_ftype,
            "chat_template": "{{ messages }}",
            "total_slots": 1,
            "default_generation_settings": {"n_ctx": 8192},
        },
        "slots": [{"id": 0, "n_ctx": 8192}],
        "llama_identity": {
            "revision": revision,
            "version": "llama-server build 10874",
            "buildNumber": 10874,
        },
    }


def test_physical_requests_add_v1_controls_to_all_four_conditions():
    rendered = tx.physical_requests("model-x")
    assert tuple(rendered) == cognition.CONDITIONS
    for condition in cognition.CONDITIONS:
        request = rendered[condition]["request"]
        assert request["reasoning_effort"] == "none"
        assert request["cache_prompt"] is False
    assert len({rendered[c]["requestHash"] for c in cognition.CONDITIONS}) == 4


def test_planned_ledger_runs_exactly_four_conditions_per_repeat():
    ledger = tx.planned_request_ledger("model-x", repeats=2)
    assert len(ledger) == 8
    assert [row["condition"] for row in ledger[:4]] == list(cognition.CONDITIONS)
    assert [row["condition"] for row in ledger[4:]] == list(reversed(cognition.CONDITIONS))
    assert ledger == tx.planned_request_ledger("model-x", repeats=2)


def test_attestation_rejects_context_or_slot_mismatch(tmp_path):
    artifact = (tmp_path / "model.gguf").resolve()
    artifact.write_bytes(b"x")
    data = _valid_runtime(artifact)
    props = dict(data["props"])
    props["default_generation_settings"] = {"n_ctx": 4096}
    with pytest.raises(tx.PhysicalTransactionError, match="context"):
        tx.attest_runtime(
            health=data["health"],
            models=data["models"],
            props=props,
            slots=data["slots"],
            artifact_path=artifact,
            artifact_sha256="0" * 64,
            llama_identity=data["llama_identity"],
        )


def test_attestation_accepts_v1_equivalent_runtime_ftype(tmp_path):
    artifact = (tmp_path / "model.gguf").resolve()
    artifact.write_bytes(b"x")
    data = _valid_runtime(artifact)
    result = tx.attest_runtime(
        health=data["health"],
        models=data["models"],
        props=data["props"],
        slots=data["slots"],
        artifact_path=artifact,
        artifact_sha256="0" * 64,
        llama_identity=data["llama_identity"],
    )
    assert result["requestModel"] == "model-x"
    assert result["modelFtype"] == "Q4_K - Medium"
    assert result["targetQuantization"] == "Q4_K_M"
    assert result["context"] == 8192
    assert result["slots"] == 1
    assert result["contextShiftEnabled"] is False


def test_attestation_accepts_exact_target_quantization_label(tmp_path):
    artifact = (tmp_path / "model.gguf").resolve()
    artifact.write_bytes(b"x")
    data = _valid_runtime(artifact, model_ftype="Q4_K_M")
    result = tx.attest_runtime(
        health=data["health"],
        models=data["models"],
        props=data["props"],
        slots=data["slots"],
        artifact_path=artifact,
        artifact_sha256="0" * 64,
        llama_identity=data["llama_identity"],
    )
    assert result["modelFtype"] == "Q4_K_M"
    assert result["targetQuantization"] == "Q4_K_M"


def test_attestation_rejects_unrelated_ftype_label(tmp_path):
    artifact = (tmp_path / "model.gguf").resolve()
    artifact.write_bytes(b"x")
    data = _valid_runtime(artifact, model_ftype="Q5_K - Medium")
    with pytest.raises(tx.PhysicalTransactionError, match="target quantization"):
        tx.attest_runtime(
            health=data["health"],
            models=data["models"],
            props=data["props"],
            slots=data["slots"],
            artifact_path=artifact,
            artifact_sha256="0" * 64,
            llama_identity=data["llama_identity"],
        )


def test_execute_cognition_does_not_retry_transport_failure():
    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=urllib.error.URLError("boom"),
    ) as call:
        with pytest.raises(tx.PhysicalTransactionError, match="without retry"):
            tx.execute_cognition(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="model-x",
                repeats=2,
                timeout=1.0,
            )
    assert call.call_count == 1


def test_wrong_gguf_blocks_before_server_launch(tmp_path):
    evidence = tmp_path / "evidence"
    artifact = tmp_path / "wrong.gguf"
    artifact.write_bytes(b"wrong")
    with (
        patch.object(tx, "_require_clean_repo", return_value=("a" * 40, "b" * 40)),
        patch.object(tx, "_port_is_free", return_value=True),
        patch.object(tx, "_require_llama_cpp_paths"),
        patch.object(tx, "_collect_llama_revision", return_value="c" * 40),
        patch.object(
            tx,
            "_collect_server_version",
            return_value={"version": "build 1", "buildNumber": 1},
        ),
        patch.object(tx, "_collect_gpu_identity", return_value="GPU") as gpu,
        patch.object(tx, "_start_server") as start,
    ):
        code = tx.main(
            [
                "--repo-root",
                str(tmp_path),
                "--llama-cpp-root",
                str(tmp_path),
                "--artifact-path",
                str(artifact),
                "--evidence-root",
                str(evidence),
            ]
        )
    assert code == 3
    start.assert_not_called()
    gpu.assert_not_called()


def test_occupied_port_blocks_before_identity_or_launch(tmp_path):
    evidence = tmp_path / "evidence"
    with (
        patch.object(tx, "_require_clean_repo", return_value=("a" * 40, "b" * 40)),
        patch.object(tx, "_port_is_free", return_value=False),
        patch.object(tx, "_collect_llama_revision") as identity,
        patch.object(tx, "_start_server") as start,
    ):
        code = tx.main(["--repo-root", str(tmp_path), "--evidence-root", str(evidence)])
    assert code == 3
    identity.assert_not_called()
    start.assert_not_called()


def test_cleanup_targets_only_supplied_owned_process():
    process = Mock()
    process.poll.side_effect = [None, 0]
    process.wait.return_value = 0
    process.returncode = 0
    assert tx._terminate_owned_process(process) == 0
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=15.0)
    process.kill.assert_not_called()


def test_no_bytecode_launcher_preserves_clean_checkout_before_preflight(tmp_path):
    launcher = Path("experiments/run_mineflayer_cognition_llama_cpp_transaction.sh")
    launcher_text = launcher.read_text(encoding="utf-8")
    assert (
        'exec python3 -B -m experiments.mineflayer_cognition_llama_cpp_transaction "$@"'
        in launcher_text
    )

    repo = tmp_path / "repo"
    experiments = repo / "experiments"
    experiments.mkdir(parents=True)
    for name in (
        "__init__.py",
        "mineflayer_viability_relay.py",
        "mineflayer_cognition_ab.py",
        "mineflayer_cognition_llama_cpp_transaction.py",
        launcher.name,
    ):
        shutil.copy2(Path("experiments") / name, experiments / name)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "relay-self-test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "RelaySelf Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)

    evidence = tmp_path / "evidence"
    completed = subprocess.run(
        [
            "bash",
            str(experiments / launcher.name),
            "--repo-root",
            str(repo),
            "--port",
            "9999",
            "--evidence-root",
            str(evidence),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 3
    summary = json.loads((evidence / "transaction-summary.json").read_text(encoding="utf-8"))
    assert "current physical condition requires port 1234" in summary["error"]
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert status == ""
    assert not list(repo.rglob("__pycache__"))
    assert not list(repo.rglob("*.pyc"))



def test_run_text_wraps_spawn_oserror_with_exact_command():
    error = PermissionError(1, "Operation not permitted")
    with patch.object(subprocess, "run", side_effect=error):
        with pytest.raises(
            tx.PhysicalTransactionError,
            match=r"command could not start: git rev-parse HEAD: PermissionError: .*Operation not permitted",
        ):
            tx._run_text(["git", "rev-parse", "HEAD"])


def test_preflight_trace_records_exact_failing_stage(tmp_path):
    evidence = tmp_path / "evidence"
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"x")

    with (
        patch.object(tx, "_require_clean_repo", return_value=("a" * 40, "b" * 40)),
        patch.object(tx, "_port_is_free", return_value=True),
        patch.object(tx, "_require_llama_cpp_paths"),
        patch.object(tx, "_collect_llama_revision", return_value="c" * 40),
        patch.object(
            tx,
            "_collect_server_version",
            return_value={"version": "llama-server build 10874", "buildNumber": 10874},
        ),
        patch.object(
            tx,
            "_verify_artifact",
            side_effect=PermissionError(1, "Operation not permitted"),
        ),
        patch.object(tx, "_collect_gpu_identity") as gpu,
        patch.object(tx, "_start_server") as start,
    ):
        code = tx.main(
            [
                "--repo-root",
                str(tmp_path),
                "--llama-cpp-root",
                str(tmp_path),
                "--artifact-path",
                str(artifact),
                "--evidence-root",
                str(evidence),
            ]
        )

    assert code == 2
    summary = json.loads((evidence / "transaction-summary.json").read_text(encoding="utf-8"))
    assert summary["disposition"] == "HARNESS_INVALID"
    assert summary["currentStage"] == "gguf_verify"
    assert summary["completedStages"][:4] == [
        "clean_repo",
        "port_free",
        "llama_cpp_revision",
        "llama_server_version",
    ]
    assert summary["completedStages"][-1] == "cleanup"
    assert "PermissionError" in summary["error"]
    gpu.assert_not_called()
    start.assert_not_called()
