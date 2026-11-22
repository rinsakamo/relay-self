"""Q4 original real wiring diagnostic; never launches Native or World."""
from __future__ import annotations

from relay_self.q4_original_real_wiring_dev import (
    Q4OriginalRealWiringAudit,
    audit_q4_original_live_wiring_cpu,
)


def test_stage27_original_executor_is_importable_from_unified_i():
    report = audit_q4_original_live_wiring_cpu()
    assert isinstance(report, Q4OriginalRealWiringAudit)
    assert report.implemented_receipt
    assert report.implemented_shared_executor
    assert not report.real_world_authorized
    assert report.synthetic_only_s2_api


def test_q4_live_wiring_advertises_remaining_exact_issuer_blockers():
    report = audit_q4_original_live_wiring_cpu()
    assert set(report.missing_original_interfaces) == {
        "original_i4a_s2_first_wal_window",
        "require_original_i4a_s2_wal_window",
        "consume_original_i4a_s2_action_once",
        "original_place_s2_wal_reservation",
        "original_place_prior_terminal_reservation",
    }
    assert "quiescent_wal_history_window" not in (
        report.missing_original_interfaces
    )
