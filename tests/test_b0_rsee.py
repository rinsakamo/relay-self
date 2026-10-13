"""B0 RSEE fail-closed gates; never start Minecraft/Node/Java/GPU."""
import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer.b0_rsee import (
    B0_CONFIRM,
    RSEE_HEAD,
    SOURCE_BLOBS,
    B0RSEEInputs,
    B0RSEERejected,
    verify_b0_rsee,
)
from adapters.mineflayer.s51_eat_real_ci import qualify


def test_b0_uses_a_pinned_external_source_without_rsee_reimplementation():
    assert len(RSEE_HEAD) == 40
    assert len(SOURCE_BLOBS) >= 8
    assert "experiments/standard_env/golden_admission.py" in SOURCE_BLOBS
    assert "adapters/mineflayer/bridge.mjs" in SOURCE_BLOBS


@pytest.mark.parametrize("confirmation", [None, "", "older-one-shot", B0_CONFIRM])
def test_b0_never_starts_world_without_rsee_even_with_env_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, confirmation: str | None,
) -> None:
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report, log = tmp_path / "report.json", tmp_path / "minecraft.log"
    result = asyncio.run(qualify(
        report, log, food_item="rotten_flesh", confirmation=confirmation,
    ))
    assert result == 2
    body = json.loads(report.read_text())
    assert body["status"] == "BLOCKED"
    assert body["stage"] == "START"
    assert "RSEE" in body["error"]
    assert not log.exists() and not body.get("session_id")


def test_nonexistent_rsee_source_cannot_launch_or_claim_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    inp = B0RSEEInputs(
        *(tmp_path / key for key in (
            "missing-rsee", "jar", "world", "manifest", "observation", "npm",
        )),
        eula_accepted=True,
    )
    with pytest.raises(B0RSEERejected):
        verify_b0_rsee(inp)
    report, log = tmp_path / "report.json", tmp_path / "server.log"
    rc = asyncio.run(qualify(
        report, log, food_item="rotten_flesh",
        rsee=inp, confirmation=B0_CONFIRM,
    ))
    assert rc == 2
    body = json.loads(report.read_text())
    assert body["status"] == "BLOCKED"
    assert body["stage"] == "RSEE_ORIGINAL_READONLY_PRELAUNCH_GATE"
    assert "session_id" not in body and not log.exists()


def test_eula_consent_is_independent_of_operator_confirmation(tmp_path: Path) -> None:
    inp = B0RSEEInputs(*(tmp_path / str(i) for i in range(6)))
    with pytest.raises(B0RSEERejected, match="EULA"):
        verify_b0_rsee(inp)


@pytest.mark.parametrize("mode", ["ground", "none"])
def test_all_b0_physical_variants_refuse_missing_rsee_before_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str,
) -> None:
    monkeypatch.setenv("S51_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    output = tmp_path / "report.json"
    log = tmp_path / "server.log"
    rc = asyncio.run(qualify(
        output, log, food_item="rotten_flesh",
        food_source=mode, confirmation=B0_CONFIRM,
    ))
    assert rc == 2
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["status"] == "BLOCKED"
    assert value["m_energy_credited"] is False
    assert not log.exists()


def test_readonly_preflight_never_requires_physical_permission_or_starts_java(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Synthetic verifier return proves the *branch routing* only, not RSEE
    # qualification. The original source verifier is exercised on a host.
    from adapters.mineflayer import s51_eat_real_ci as host

    monkeypatch.delenv("S51_REAL_SERVER_CI", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    fake = B0RSEEInputs(
        *(tmp_path / str(i) for i in range(6)), eula_accepted=True,
    )
    calls = []

    def verify_once(inputs):
        calls.append(inputs)
        return {
            "classification": "SYNTHETIC_TEST_READONLY_ONLY",
            "physical_execution_authorized": False,
        }

    monkeypatch.setattr(host, "verify_b0_rsee", verify_once)
    report_path, log = tmp_path / "result.json", tmp_path / "no-java.log"
    rc = asyncio.run(host.qualify(
        report_path, log,
        food_item="rotten_flesh",
        rsee=fake,
        preflight_only=True,
    ))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert rc == 0 and report["status"] == "PASS"
    assert report["classification"] == "B0_RSEE_READONLY_PREFLIGHT_ONLY"
    assert report["physical_execution_authorized"] is False
    assert report["rsee_preflight"]["classification"] == "SYNTHETIC_TEST_READONLY_ONLY"
    assert calls == [fake]
    assert not log.exists() and not report.get("session_id")


def test_readonly_preflight_requires_full_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    path = tmp_path / "blocked.json"
    rc = asyncio.run(qualify(
        path, tmp_path / "no-java.log",
        food_item="rotten_flesh",
        preflight_only=True,
    ))
    result = json.loads(path.read_text(encoding="utf-8"))
    assert rc == 2 and result["status"] == "BLOCKED"
    assert "RSEE" in result["error"]
    assert result.get("physical_execution_authorized") is None
    assert not (tmp_path / "no-java.log").exists()
