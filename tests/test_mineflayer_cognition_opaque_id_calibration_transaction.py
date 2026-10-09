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
import experiments.mineflayer_cognition_llama_cpp_transaction as physical
import experiments.mineflayer_cognition_opaque_id_calibration as opaque
import experiments.mineflayer_cognition_opaque_id_calibration_transaction as tx


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def test_physical_requests_add_runtime_controls_without_gradient():
    rendered = tx.physical_requests("model-x")
    assert tuple(rendered) == opaque.OPAQUE_CONDITIONS

    for condition in opaque.OPAQUE_CONDITIONS:
        request = rendered[condition]["request"]
        assert request["reasoning_effort"] == "none"
        assert request["cache_prompt"] is False
        assert request["temperature"] == 0
        assert request["max_tokens"] == 32

        payload = _user_payload(request)
        assert "valueGradient" not in json.dumps(
            payload["history"],
            sort_keys=True,
        )
        assert {
            plan["plan_id"]
            for plan in payload["candidate_plans"]
        } == opaque.OPAQUE_PLAN_IDS


def test_planned_ledger_is_exactly_twenty_calls_and_alternates():
    ledger = tx.planned_request_ledger("model-x")
    assert len(ledger) == 20

    conditions = list(opaque.OPAQUE_CONDITIONS)
    for trial in range(tx.CALIBRATION_REPEATS):
        start = trial * 4
        block = [
            row["condition"]
            for row in ledger[start : start + 4]
        ]
        expected = (
            conditions
            if trial % 2 == 0
            else list(reversed(conditions))
        )
        assert block == expected

    assert ledger == tx.planned_request_ledger("model-x")


def test_planned_ledger_records_expected_shortest_geometry_ids():
    ledger = tx.planned_request_ledger("model-x")
    first = {}
    for row in ledger:
        first.setdefault(row["condition"], row)

    assert first[opaque.N0_CANONICAL]["shortestGeometryPlanId"] == (
        opaque.OPAQUE_DIRECT_SLOT
    )
    assert first[opaque.N1_SWAP_FIRST_TWO]["shortestGeometryPlanId"] == (
        opaque.OPAQUE_DETOUR_SLOT
    )
    assert first[opaque.N2_CYCLIC_GEOMETRY]["shortestGeometryPlanId"] == (
        opaque.OPAQUE_DETOUR_SLOT
    )
    assert first[opaque.N3_REVERSED_ORDER]["planOrder"] == [
        opaque.OPAQUE_OBSERVE_SLOT,
        opaque.OPAQUE_DETOUR_SLOT,
        opaque.OPAQUE_DIRECT_SLOT,
    ]


def test_execute_calibration_does_not_retry_transport_failure():
    with patch.object(
        cognition,
        "call_openai_compatible",
        side_effect=urllib.error.URLError("boom"),
    ) as call:
        with pytest.raises(
            physical.PhysicalTransactionError,
            match="without retry",
        ):
            tx.execute_calibration(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="model-x",
                timeout=1.0,
            )
    assert call.call_count == 1


# #409 splits static shell identity, interpreter -B behavior, and preflight.
# Shell exec/argv integration coverage is deferred to a separately authorized
# test owner: neither the canonical launcher nor a copy is executed here.
LAUNCHER = Path("experiments/run_mineflayer_cognition_opaque_id_calibration_transaction.sh")
LAUNCHER_TEXT = (
    "#!/usr/bin/env bash\n"
    "set -euo pipefail\n\n"
    'exec python3 -B -m experiments.mineflayer_cognition_opaque_id_calibration_transaction "$@"\n'
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
        "mineflayer_cognition_opaque_id_calibration.py",
        "mineflayer_cognition_opaque_id_calibration_transaction.py",
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
        "import experiments.mineflayer_cognition_opaque_id_calibration_transaction; stack.close()"
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
        (tx, "execute_calibration"),
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
            "PhysicalTransactionError: current calibration condition requires port 1234"
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
    "run", "Popen", "socket", "_verify_artifact", "execute_calibration",
])
def test_preflight_guard_rejects_port_or_execution_drift(tmp_path, drift):
    # main catches the injected exception; exact stage/code plus guard accounting
    # must still reject it, rather than accepting any generic failure as safe.
    with pytest.raises(AssertionError):
        _guarded_port_preflight(tmp_path, drift=drift)
