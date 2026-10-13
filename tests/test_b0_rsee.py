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
