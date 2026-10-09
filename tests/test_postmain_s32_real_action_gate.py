"""S32 offline negative controls for the real-Action3 hybrid CI gate.

Actual Minecraft and bridge are *only* run by the dedicated S32 job.
These tests reject false physical ancestry and stale post-Action evidence.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_source_native_world as s27
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.s32_real_action_lineage_ci import (
    MAX_TARGET_ATTEMPTS,
    REQUEST_ID,
)
from relay_self.source_native_world import (
    InvalidSourceNativeWorldEvidence,
    project_source_native_threat,
)

ROOT = Path(__file__).resolve().parents[1]


def test_s32_requires_explicit_distinct_new_correlated_id():
    assert REQUEST_ID == "s32-after-real-action3:000"
    assert MAX_TARGET_ATTEMPTS == 5
    source = (
        ROOT / "adapters/mineflayer/s32_real_action_lineage_ci.py"
    ).read_text()
    assert "execute_mineflayer_command(" in source
    assert "interpret_world_consequence(" in source
    assert "record_interpreted_action_outcome(" in source
    assert "project_source_native_threat(" in source
    assert "run_explicit_postfailure_epoch(" in source
    assert "s23._prepare_recovery()" in source


def test_offline_exact_S23_ancestry_projects_separate_source_evidence():
    data, failed, inputs, kwargs = s27._fixture(distance_m=2.0)
    receipt = project_source_native_threat(**kwargs)
    assert receipt.evidence.threat_clearance_cm == 200
    assert receipt.evidence.provenance == kwargs["observation"].provenance
    assert receipt.evidence.action_id == kwargs["action"].action_id
    assert receipt.evidence.session_id == kwargs["consequence"].session_id
    assert receipt.parent_after_seq < receipt.source.seq
    assert data["supervisor"].open_actions == ()
    assert failed.state.value == "failed"
    assert inputs["recovery_skill"].state.value == "started"


@pytest.mark.parametrize("field,change", [
    ("observation", "wrong_session"),
    ("observation", "old_seq"),
    ("action", "different_action"),
    ("consequence", "undetermined"),
    ("inspected_at_ns", "expired"),
])
def test_cross_session_stale_source_and_nonoutcome_rejected(field, change):
    data, _, _, kwargs = s27._fixture(distance_m=2.0)
    candidate = kwargs[field]
    if change == "wrong_session":
        candidate = replace(candidate, session_id="not-live-world-session")
    elif change == "old_seq":
        candidate = replace(
            candidate, seq=kwargs["consequence"].after_observation.seq,
        )
    elif change == "different_action":
        candidate = data["closed1"]
    elif change == "undetermined":
        candidate = replace(candidate, status=WorldConsequenceStatus.UNDETERMINED)
    elif change == "expired":
        candidate = 71
    with pytest.raises(InvalidSourceNativeWorldEvidence):
        project_source_native_threat(**{**kwargs, field: candidate})
    assert data["supervisor"].open_actions == ()


def test_qualification_cannot_claim_physical_earlier_epoch_or_action4():
    receipt = json.loads(
        (ROOT / "docs/postmain-s32-plan-receipt.json").read_text()
    )
    assert receipt["base_head"] == "2f3af780508a51b66513043b4cfedf80d20ff1a0"
    assert receipt["status"] == "PENDING_CI"
    assert receipt["qualification_requires"] == "S32_REPORT.status == PASS"
    assert receipt["synthetic_ancestry"] == "S19-S23 seeded only"
    assert receipt["real_action3_execution_required"] is True
    assert receipt["real_prior_actions_qualified"] is False
    assert receipt["automatic_action4_issued"] is False
    assert receipt["live_server_result"] == "NOT_YET_VERIFIED"
