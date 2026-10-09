from __future__ import annotations

import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from contextlib import ExitStack
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


# #406 splits static shell identity, interpreter -B behavior, and preflight.
# Shell exec/argv integration coverage is deferred to a separately authorized
# test owner: neither the canonical launcher nor a copy is executed here.
LAUNCHER = Path("experiments/run_mineflayer_cognition_llama_cpp_transaction.sh")
LAUNCHER_TEXT = (
    "#!/usr/bin/env bash\n"
    "set -euo pipefail\n\n"
    'exec python3 -B -m experiments.mineflayer_cognition_llama_cpp_transaction "$@"\n'
)


def _assert_launcher_identity(text):
    # Exact bytes reject extra commands, preload/environment changes and flags.
    assert text == LAUNCHER_TEXT


def test_launcher_static_identity_without_execution():
    _assert_launcher_identity(LAUNCHER.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mutation", [
    lambda text: text.replace(" -B ", " "),
    lambda text: text.replace(" -B ", " -b "),
    lambda text: text + "echo unexpected\n",
    lambda text: text.replace("exec python3", "PYTHONPATH=/tmp exec python3"),
    lambda text: text.replace("python3", "python"),
    lambda text: text.replace('"$@"', "$*"),
])
def test_launcher_identity_rejects_drift(mutation):
    with pytest.raises(AssertionError):
        _assert_launcher_identity(mutation(LAUNCHER_TEXT))


def test_direct_B_import_preserves_clean_non_scientific_fixture(tmp_path):
    repo = tmp_path / "import-fixture"
    experiments = repo / "experiments"
    experiments.mkdir(parents=True)
    for name in (
        "__init__.py",
        "mineflayer_viability_relay.py",
        "mineflayer_cognition_ab.py",
        "mineflayer_cognition_llama_cpp_transaction.py",
    ):
        shutil.copy2(Path("experiments") / name, experiments / name)
    # No shell scripts or experiment CLI invocations in this fixture.
    assert not list(repo.rglob("*.sh"))
    for args in (
        ["init", "-q"],
        ["config", "user.email", "relay-self-test@example.invalid"],
        ["config", "user.name", "RelaySelf Test"],
        ["add", "."],
        ["commit", "-qm", "fixture"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True)
    script = (
        "import sys; assert sys.dont_write_bytecode; "
        "import socket, subprocess, urllib.request; "
        "from unittest.mock import patch; "
        "from contextlib import ExitStack; "
        f"sys.path.insert(0, {str(repo)!r}); "
        "stack = ExitStack(); "
        "[stack.enter_context(patch.object(obj, name, "
        "side_effect=AssertionError('import attempted external operation'))) "
        "for obj, name in [(socket, 'socket'), (subprocess, 'Popen'), "
        "(urllib.request, 'urlopen')]]; "
        "import experiments.mineflayer_cognition_llama_cpp_transaction; stack.close()"
    )
    # -I ignores inherited PYTHONPATH and PYTHONDONTWRITEBYTECODE. This proves
    # the interpreter's -B effect, independently of the static launcher flag.
    interpreter = shutil.which("python3")
    assert interpreter is not None
    result = subprocess.run(
        [interpreter, "-I", "-B", "-c", script],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    missing_B = subprocess.run(
        [interpreter, "-I", "-c", script],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    # Fails before importing the fixture, even if the parent has bytecode off.
    assert missing_B.returncode != 0
    assert "AssertionError" in missing_B.stderr
    assert not list(repo.rglob("__pycache__"))
    assert not list(repo.rglob("*.pyc"))
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo,
        text=True, capture_output=True, check=True,
    ).stdout
    assert status == ""


def _guarded_port_preflight(tmp_path, *, drift=None):
    # These are temporary synthetic unit artifacts, never scientific evidence.
    artifacts = tmp_path / "synthetic-preflight"
    forbidden = [
        (tx, name) for name in (
            "_port_is_free", "_require_llama_cpp_paths", "_collect_llama_revision",
            "_collect_server_version", "_verify_artifact", "_collect_gpu_identity",
            "_server_command", "_start_server", "_get_json", "_wait_until_ready",
            "_probe_and_attest", "_terminate_owned_process",
        )
    ] + [
        (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"),
        (urllib.request, "urlopen"), (cognition, "call_openai_compatible"),
        (tx, "execute_cognition"),
    ]
    with ExitStack() as stack:
        guards = {
            name: stack.enter_context(patch.object(
                obj, name, side_effect=AssertionError(f"forbidden operation: {name}"),
            )) for obj, name in forbidden
        }
        clean = stack.enter_context(patch.object(
            tx, "_require_clean_repo", return_value=("a" * 40, "b" * 40),
        ))
        if drift == "port":
            stack.enter_context(patch.object(tx, "DEFAULT_PORT", 9999))
        elif drift is not None:
            clean.side_effect = lambda *_: guards[drift]()
        code = tx.main([
            "--repo-root", str(tmp_path), "--port", "9999",
            "--evidence-root", str(artifacts),
        ])
        assert code == 3
        summary = json.loads((artifacts / "transaction-summary.json").read_text())
        assert summary["disposition"] == "BLOCKED_OR_INVALID"
        assert summary["currentStage"] == "port_free"
        assert summary["completedStages"] == ["clean_repo", "cleanup"]
        assert summary["error"] == (
            "PhysicalTransactionError: current physical condition requires port 1234"
        )
        assert summary["transactionExitCode"] == 3
        for key in ("serverLaunchCount", "modelCallCount", "retryCount",
                    "replayCount", "fallbackCount", "repositoryMutationCount"):
            assert summary[key] == 0
        assert summary["cleanup"] == {
            "ownedProcess": False, "terminated": False, "exitCode": None,
        }
        assert sorted(p.name for p in artifacts.iterdir()) == [
            "cleanup.json", "transaction-summary.json",
        ]
        clean.assert_called_once_with(tmp_path.resolve())
        for guard in guards.values():
            guard.assert_not_called()


def test_in_process_port_9999_preflight_rejects_before_external_operations(tmp_path):
    _guarded_port_preflight(tmp_path)


@pytest.mark.parametrize("drift", [
    "port", "_start_server", "_get_json", "call_openai_compatible",
    "run", "Popen", "socket", "_verify_artifact", "execute_cognition",
])
def test_preflight_guard_rejects_port_or_execution_drift(tmp_path, drift):
    # main catches the injected exception; exact stage/code plus guard accounting
    # must still reject it, rather than accepting any generic failure as safe.
    with pytest.raises(AssertionError):
        _guarded_port_preflight(tmp_path, drift=drift)



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
