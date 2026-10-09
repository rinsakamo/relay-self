from __future__ import annotations

import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_f46_successor as probe
import experiments.mineflayer_cognition_f46_successor_transaction as tx


def test_physical_ledger_is_exactly_frozen_36_rows():
    ledger = tx.planned_request_ledger("model-x")

    assert len(ledger) == 36
    assert [row["executionIndex"] for row in ledger] == list(range(36))
    assert [row["blockId"] for row in ledger[:6]] == ["B0"] * 6
    assert [row["blockId"] for row in ledger[-6:]] == ["B5"] * 6

    for row in ledger:
        request = row["request"]
        assert request["temperature"] == 0
        assert request["max_tokens"] == 32
        assert request["reasoning_effort"] == "none"
        assert request["cache_prompt"] is False


def test_transport_failure_is_recorded_and_stops_after_one_call():
    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=urllib.error.URLError("boom"),
    ) as call:
        result = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )

    assert call.call_count == 1
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["planId"] is None
    assert record["transportError"].startswith("URLError:")
    assert result["summary"]["classification"] == probe.INVALID


def test_parser_failure_is_recorded_and_stops_after_one_call():
    with patch.object(
        cognition,
        "call_openai_compatible",
        return_value="not-json",
    ) as call:
        result = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )

    assert call.call_count == 1
    assert len(result["records"]) == 1
    assert result["records"][0]["parseError"].startswith("invalid_json:")
    assert result["summary"]["classification"] == probe.INVALID


def test_complete_valid_execution_uses_exactly_36_calls():
    def choose_first(*, request_body, **_kwargs):
        payload = json.loads(request_body["messages"][1]["content"])
        plan_id = payload["candidate_plans"][0]["plan_id"]
        return json.dumps({"plan_id": plan_id})

    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=choose_first,
    ) as call:
        result = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )

    assert call.call_count == 36
    assert len(result["records"]) == 36
    assert all(row["parseError"] is None for row in result["records"])
    assert all(row["transportError"] is None for row in result["records"])
    assert result["summary"]["classification"] in {
        probe.EFFECT,
        probe.NO_EFFECT,
        probe.NON_DISCRIMINATING,
        probe.MIXED,
    }


# #406 splits static shell identity, interpreter -B behavior, and preflight.
# Shell exec/argv integration coverage is deferred to a separately authorized
# test owner: neither the canonical launcher nor a copy is executed here.
LAUNCHER = Path("experiments/run_mineflayer_cognition_f46_successor_transaction.sh")
LAUNCHER_TEXT = (
    "#!/usr/bin/env bash\n"
    "set -euo pipefail\n\n"
    'exec python3 -B -m experiments.mineflayer_cognition_f46_successor_transaction "$@"\n'
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
        "mineflayer_cognition_f46_successor.py",
        "mineflayer_cognition_f46_successor_transaction.py",
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
        "import experiments.mineflayer_cognition_f46_successor_transaction; stack.close()"
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
        (tx.physical, name) for name in (
            "_port_is_free", "_require_llama_cpp_paths", "_collect_llama_revision",
            "_collect_server_version", "_verify_artifact", "_collect_gpu_identity",
            "_server_command", "_start_server", "_get_json", "_wait_until_ready",
            "_probe_and_attest", "_terminate_owned_process",
        )
    ] + [
        (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"),
        (urllib.request, "urlopen"), (cognition, "call_openai_compatible"),
        (tx, "execute_successor"),
    ]
    with ExitStack() as stack:
        guards = {
            name: stack.enter_context(patch.object(
                obj, name, side_effect=AssertionError(f"forbidden operation: {name}"),
            )) for obj, name in forbidden
        }
        clean = stack.enter_context(patch.object(
            tx.physical, "_require_clean_repo", return_value=("a" * 40, "b" * 40),
        ))
        if drift == "port":
            stack.enter_context(patch.object(tx.physical, "DEFAULT_PORT", 9999))
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
            "PhysicalTransactionError: current successor condition requires port 1234"
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
    "run", "Popen", "socket", "_verify_artifact", "execute_successor",
])
def test_preflight_guard_rejects_port_or_execution_drift(tmp_path, drift):
    # main catches the injected exception; exact stage/code plus guard accounting
    # must still reject it, rather than accepting any generic failure as safe.
    with pytest.raises(AssertionError):
        _guarded_port_preflight(tmp_path, drift=drift)



def test_pre_send_hash_mismatch_has_zero_generation_attempts():
    planned = tx.planned_request_ledger("model-x")
    planned[0]["requestHash"] = "0" * 64

    with (
        patch.object(tx, "planned_request_ledger", return_value=planned),
        patch.object(cognition, "call_openai_compatible") as call,
    ):
        result = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )

    assert call.call_count == 0
    assert result["attemptedModelCallCount"] == 0
    assert len(result["records"]) == 1
    assert result["records"][0]["parseError"] == "request_hash_mismatch"
    assert result["summary"]["classification"] == probe.INVALID


def test_unexpected_exception_after_three_calls_preserves_partial_rows(tmp_path):
    attempts = 0
    journal = tmp_path / "partial.json"

    def unexpectedly_fail(*, request_body, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 4:
            raise RuntimeError("unexpected failure")
        payload = json.loads(request_body["messages"][1]["content"])
        return json.dumps(
            {"plan_id": payload["candidate_plans"][0]["plan_id"]}
        )

    def preserve(records, count):
        journal.write_text(
            json.dumps({"attempts": count, "records": records}),
            encoding="utf-8",
        )

    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=unexpectedly_fail,
    ) as call:
        result = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
            on_progress=preserve,
        )

    assert call.call_count == 4
    assert result["attemptedModelCallCount"] == 4
    assert len(result["records"]) == 4
    assert all(
        row["parseError"] is None
        for row in result["records"][:3]
    )
    assert result["records"][3]["transportError"].startswith("RuntimeError:")
    assert result["summary"]["classification"] == probe.INVALID

    preserved = json.loads(journal.read_text(encoding="utf-8"))
    assert preserved["attempts"] == 4
    assert len(preserved["records"]) == 4


def test_ordinary_transport_and_parser_failures_count_one_attempt():
    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=urllib.error.URLError("boom"),
    ):
        transport = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )
    assert transport["attemptedModelCallCount"] == 1

    with patch.object(
        cognition,
        "call_openai_compatible",
        return_value="not-json",
    ):
        parser = tx.execute_successor(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-x",
            timeout=1.0,
        )
    assert parser["attemptedModelCallCount"] == 1
