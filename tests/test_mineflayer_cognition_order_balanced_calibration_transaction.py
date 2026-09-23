from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

import experiments.mineflayer_cognition_ab as cognition
import experiments.mineflayer_cognition_llama_cpp_transaction as physical
import experiments.mineflayer_cognition_order_balanced_calibration as balanced
import experiments.mineflayer_cognition_order_balanced_calibration_transaction as tx


def _user_payload(request):
    return json.loads(request["messages"][1]["content"])


def test_physical_requests_are_exactly_thirty_six_and_add_runtime_controls():
    rendered = tx.physical_requests("model-x")
    assert len(rendered) == 36

    for item in rendered:
        request = item["request"]
        assert request["temperature"] == 0
        assert request["max_tokens"] == 32
        assert request["reasoning_effort"] == "none"
        assert request["cache_prompt"] is False
        assert "valueGradient" not in json.dumps(
            _user_payload(request)["history"],
            sort_keys=True,
        )


def test_physical_ledger_preserves_predeclared_execution_order():
    ledger = tx.planned_request_ledger("model-x")
    cells = balanced.planned_cells()
    assert len(ledger) == len(cells) == 36

    observed = [
        (
            row["repeat"],
            row["geometryMapping"],
            row["permutation"],
            row["planOrder"],
        )
        for row in ledger
    ]
    expected = [
        (
            row["repeat"],
            row["geometryMapping"],
            row["permutation"],
            row["planOrder"],
        )
        for row in cells
    ]
    assert observed == expected


def test_physical_ledger_has_eighteen_request_hashes_each_repeated_twice():
    ledger = tx.planned_request_ledger("model-x")
    counts = {}
    for row in ledger:
        key = (row["geometryMapping"], row["permutation"])
        counts.setdefault(key, set()).add(row["requestHash"])

    assert len(counts) == 18
    assert all(len(hashes) == 1 for hashes in counts.values())


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
        "run_mineflayer_cognition_order_balanced_calibration_transaction.sh"
    )
    launcher_text = launcher.read_text(encoding="utf-8")
    assert (
        "exec python3 -B -m "
        "experiments.mineflayer_cognition_order_balanced_calibration_transaction "
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
        "mineflayer_cognition_llama_cpp_transaction.py",
        "mineflayer_cognition_opaque_id_calibration.py",
        "mineflayer_cognition_order_balanced_calibration.py",
        "mineflayer_cognition_order_balanced_calibration_transaction.py",
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
