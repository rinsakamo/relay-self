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
    assert report.missing_original_interfaces == ()
    assert report.original_s2_cpu_reservation_wired
    assert not report.independent_source_authenticated
    assert not report.real_world_authorized
    assert "quiescent_wal_history_window" not in (
        report.missing_original_interfaces
    )
