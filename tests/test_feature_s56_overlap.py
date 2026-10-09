"""S56 negative controls for physical L0 vs live-L2 timing witness."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.s56_overlap_gate import (
    L0ModelOverlap,
    OverlapDenied,
    OverlapStage,
)
from adapters.mineflayer.s56_real_model_world_ci import qualify


def test_physical_l0_receipt_only_with_model_still_inflight():
    gate = L0ModelOverlap()
    gate.model_enter()
    gate.l0_enter(action_id="real-issued-action")
    witnessed = gate.l0_closed(
        action_id="real-issued-action", movement_m=0.63,
    )
    assert witnessed.proven_overlap
    assert gate.stage is OverlapStage.L0_CLOSED
    assert gate.provider_attempt_count == 1
    gate.model_exit()
    assert gate.finished.is_set()
    assert gate.receipt().proven_overlap


def test_no_model_call_cannot_qualify_l0():
    gate = L0ModelOverlap()
    with pytest.raises(OverlapDenied):
        gate.l0_enter(action_id="action")
    with pytest.raises(OverlapDenied):
        gate.l0_closed(action_id="action", movement_m=1)


def test_premature_model_completion_denies_physical_overlap():
    gate = L0ModelOverlap()
    gate.model_enter()
    gate.model_exit()
    with pytest.raises(OverlapDenied):
        gate.l0_enter(action_id="action")


def test_model_finish_during_native_action_denies_qualified_overlap():
    gate = L0ModelOverlap()
    gate.model_enter()
    gate.l0_enter(action_id="issued-action")
    gate.model_exit()
    with pytest.raises(OverlapDenied):
        gate.l0_closed(action_id="issued-action", movement_m=1)


@pytest.mark.parametrize("invalid_distance", (0.0, -2.0, 0.049, 21.0, True))
def test_no_success_without_real_movement(invalid_distance):
    gate = L0ModelOverlap()
    gate.model_enter()
    gate.l0_enter(action_id="issued-action")
    with pytest.raises(OverlapDenied):
        gate.l0_closed(
            action_id="issued-action", movement_m=invalid_distance,
        )


def test_wrong_action_identity_denied():
    gate = L0ModelOverlap()
    gate.model_enter()
    gate.l0_enter(action_id="issued-a")
    with pytest.raises(OverlapDenied):
        gate.l0_closed(action_id="unrelated-b", movement_m=1)


def test_second_provider_call_is_not_admitted():
    gate = L0ModelOverlap()
    gate.model_enter()
    with pytest.raises(OverlapDenied):
        gate.model_enter()
    assert gate.provider_attempt_count == 1


def test_physical_real_model_gate_blocks_before_world_without_operator_opt_in(
    tmp_path, monkeypatch,
):
    monkeypatch.delenv("S56_LOCAL_REAL_MODEL", raising=False)
    report = tmp_path / "out.json"
    rc = asyncio.run(qualify(
        report, tmp_path / "server.log",
        model="missing-model", endpoint="http://127.0.0.1:1234/v1/chat/completions",
        gguf=tmp_path / "missing.gguf",
        expected_sha256="0" * 64,
        timeout_s=1, max_tokens=16,
    ))
    payload = json.loads(report.read_text())
    assert rc == 2 and payload["status"] == "BLOCKED"
    assert payload["backend_process_and_model_identity_attested"] is False
    assert payload["fake_responder_installed"] is False
    assert payload["actual_native_actions"] == []
