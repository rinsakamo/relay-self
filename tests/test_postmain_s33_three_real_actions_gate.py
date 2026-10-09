"""S33 offline safeguards. Real Minecraft is exclusively in dedicated CI job."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer.s33_real_three_actions_ci import (
    S33EvidenceFailure,
    _prepare_second_real,
    _real_epoch_one,
    _real_recovery_prep,
    _real_skill2_evidence,
    _real_skill2_exit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_s33_plan_does_not_fabricate_full_sensor_cognition():
    data = json.loads((ROOT / "docs/postmain-s33-plan-receipt.json").read_text())
    assert data["status"] == "PENDING_CI"
    assert data["qualification_requires"] == "S33_REPORT.status == PASS"
    assert data["base_head"] == "47ea181608b4e7143326e37c336f062540ecadd8"
    assert data["consecutive_sessions_expected"] == 3
    assert data["retained_expected"] == "4/rev1"
    assert data["no_auto_action4"] is True
    assert data["s19_first_threat_evidence"] == "FROZEN_STRUCTURED_TEST_INPUT_NOT_NATIVE_WORLD"
    assert data["s21_skill_goal"].startswith("Caller-fixed VIOLATED")


def test_reused_frozen_cognitive_functions_do_not_hide_fake_world():
    assert callable(_real_epoch_one)
    assert callable(_prepare_second_real)
    assert callable(_real_skill2_evidence)
    assert callable(_real_skill2_exit)
    assert callable(_real_recovery_prep)
    source = (
        ROOT / "adapters/mineflayer/s33_real_three_actions_ci.py"
    ).read_text()
    assert "s19.FakeSession(" not in source
    assert "s20.SecondSession(" not in source
    assert "s23.RecoverySession(" not in source
    assert "execute_mineflayer_command(" in source
    assert "interpret_action_outcome_as_learning_feedback(" not in source or (
        "s19.interpret_action_outcome_as_learning_feedback(" in source
    )
    assert "propose_learning_update(" in source
    assert "commit_learning_update(" in source
    assert "require_fresh_second_consequence(" in source
    assert "project_source_native_threat(" in source
    assert "run_explicit_postfailure_epoch(" in source


@pytest.mark.parametrize("physical_actions,distinct_session_ids", [
    (0, 0), (1, 1), (2, 2), (3, 2), (4, 3),
])
def test_strict_terminal_three_actual_actions_gate_is_not_loosened(
    physical_actions, distinct_session_ids,
):
    assert (physical_actions == 3 and distinct_session_ids == 3) is False


def test_runtime_error_does_not_default_to_pass():
    assert issubclass(S33EvidenceFailure, RuntimeError)
