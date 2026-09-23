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


def test_no_bytecode_launcher_preserves_clean_checkout_before_preflight(
    tmp_path,
):
    launcher = Path(
        "experiments/"
        "run_mineflayer_cognition_opaque_id_calibration_transaction.sh"
    )
    launcher_text = launcher.read_text(encoding="utf-8")
    assert (
        "exec python3 -B -m "
        "experiments.mineflayer_cognition_opaque_id_calibration_transaction "
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
        "mineflayer_cognition_opaque_id_calibration_transaction.py",
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
