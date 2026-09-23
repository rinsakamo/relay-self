from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_choice_calibration as calibration
import experiments.mineflayer_cognition_choice_calibration_transaction as tx
import experiments.mineflayer_cognition_llama_cpp_transaction as physical


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def test_physical_requests_add_controls_to_all_calibration_conditions():
    rendered = tx.physical_requests("model-x")
    assert tuple(rendered) == calibration.CALIBRATION_CONDITIONS
    for condition in calibration.CALIBRATION_CONDITIONS:
        request = rendered[condition]["request"]
        assert request["reasoning_effort"] == "none"
        assert request["cache_prompt"] is False
        history_text = json.dumps(
            _user_payload(request)["history"],
            sort_keys=True,
        )
        assert "valueGradient" not in history_text

    hashes = {
        rendered[condition]["requestHash"]
        for condition in calibration.CALIBRATION_CONDITIONS
    }
    assert len(hashes) == len(calibration.CALIBRATION_CONDITIONS)


def test_planned_ledger_is_exactly_twenty_calls_with_alternating_order():
    ledger = tx.planned_request_ledger("model-x")
    assert len(ledger) == 20
    conditions = list(calibration.CALIBRATION_CONDITIONS)
    for trial in range(tx.CALIBRATION_REPEATS):
        start = trial * len(conditions)
        block = [row["condition"] for row in ledger[start : start + 4]]
        expected = conditions if trial % 2 == 0 else list(reversed(conditions))
        assert block == expected

    assert ledger == tx.planned_request_ledger("model-x")


def test_planned_ledger_records_predeclared_geometry_bindings():
    ledger = tx.planned_request_ledger("model-x")
    first_by_condition = {}
    for row in ledger:
        first_by_condition.setdefault(row["condition"], row)

    assert first_by_condition[calibration.K0_CANONICAL][
        "shortestGeometryPlanId"
    ] == "direct"
    assert first_by_condition[calibration.K1_SWAP_DIRECT_DETOUR][
        "shortestGeometryPlanId"
    ] == "detour"
    assert first_by_condition[calibration.K2_CYCLIC_GEOMETRY][
        "shortestGeometryPlanId"
    ] == "detour"
    assert first_by_condition[calibration.K3_REVERSED_ORDER][
        "planOrder"
    ] == ["observe", "detour", "direct"]


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


def test_no_bytecode_launcher_preserves_clean_checkout_before_preflight(
    tmp_path,
):
    launcher = Path(
        "experiments/"
        "run_mineflayer_cognition_choice_calibration_transaction.sh"
    )
    launcher_text = launcher.read_text(encoding="utf-8")
    assert (
        "exec python3 -B -m "
        "experiments.mineflayer_cognition_choice_calibration_transaction "
        '"$@"'
        in launcher_text
    )

    repo = tmp_path / "repo"
    experiments = repo / "experiments"
    experiments.mkdir(parents=True)

    for name in (
        "__init__.py",
        "mineflayer_viability_relay.py",
        "mineflayer_cognition_ab.py",
        "mineflayer_cognition_choice_calibration.py",
        "mineflayer_cognition_llama_cpp_transaction.py",
        "mineflayer_cognition_choice_calibration_transaction.py",
        launcher.name,
    ):
        shutil.copy2(Path("experiments") / name, experiments / name)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "relay-self-test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "RelaySelf Test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "fixture"],
        cwd=repo,
        check=True,
    )

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
    summary = json.loads(
        (evidence / "transaction-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert "requires port 1234" in summary["error"]

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
