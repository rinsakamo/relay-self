from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import patch

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


def test_no_bytecode_launcher_preserves_clean_checkout_before_preflight(
    tmp_path,
):
    launcher = Path(
        "experiments/"
        "run_mineflayer_cognition_f46_successor_transaction.sh"
    )
    launcher_text = launcher.read_text(encoding="utf-8")
    assert (
        "exec python3 -B -m "
        "experiments.mineflayer_cognition_f46_successor_transaction "
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
        "mineflayer_cognition_f46_successor.py",
        "mineflayer_cognition_f46_successor_transaction.py",
        launcher.name,
    ):
        shutil.copy2(Path("experiments") / name, experiments / name)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "relay-self-test@example.invalid",
        ],
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
    assert summary["serverLaunchCount"] == 0
    assert summary["modelCallCount"] == 0
    assert summary["retryCount"] == 0
    assert summary["replayCount"] == 0
    assert summary["fallbackCount"] == 0

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
