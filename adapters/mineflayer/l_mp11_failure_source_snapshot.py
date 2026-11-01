"""Non-qualifying post-shutdown observation summary for a FAILED L2 World.

S49 native Action closure and Paper raw source must be recorded whether or not
a later OPEN succeeds. No status is rewritten; this cannot satisfy G3/R/V.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict

from adapters.mineflayer.l_mp11_paper_eof_envelope import (
    PaperEOFRejected,
    seal_after_shutdown,
)

SCOPE = "PARTIAL_NATIVE_AND_EOF_EVIDENCE_NOT_WORLD_QUALIFICATION"


def summarize_closed_partial(
    report: dict, paper_original: bytes | None, *, predeclared: bool,
) -> dict:
    if type(report) is not dict or type(predeclared) is not bool:
        raise ValueError("typed original owner report required")
    native = report.get("actual_native_actions", [])
    g2 = report.get("mp11_g2", {})
    live = report.get("l_mp11_live_prefix", {})
    l2 = report.get("l_mp11_live_l2", {})
    if not isinstance(native, list) or not isinstance(g2, dict):
        raise ValueError("original S49 native owner evidence malformed")
    typed = g2.get("typed_s16_actions", [])
    if not isinstance(typed, list):
        raise ValueError("typed original S16 source missing")
    result = {
        "classification": SCOPE,
        "world_report_status_at_capture": report.get("status"),
        "native_closed_action_count": len(native),
        "typed_s16_count": len(typed),
        "native_action_ids": [a.get("action") for a in native],
        "typed_s16_action_ids": [a.get("action_id") for a in typed],
        "live_completed_paper_prefix_count": (
            len(live.get("observations", [])) if isinstance(live, dict) else 0
        ),
        "l2_attempt_count": (
            l2.get("attempts", 0) if isinstance(l2, dict) else 0
        ),
        "valid_l2_open_count": (
            l2.get("validated_open_calls", 0) if isinstance(l2, dict) else 0
        ),
        "next_action_issued_on_L2_failure": False
        if report.get("status") == "FAIL" else None,
        "original_paper_available": type(paper_original) is bytes,
        "paper_eof_shape_only": None,
        "world_qualified_by_this_report": False,
        "mandatory_g3_and_live_prefix_qualified": False,
        "learning_admissions": 0,
        "l0_promotions": 0,
    }
    if type(paper_original) is bytes:
        result["paper_full_original_sha256"] = hashlib.sha256(paper_original).hexdigest()
        result["paper_full_original_length"] = len(paper_original)
        try:
            result["paper_eof_shape_only"] = asdict(
                seal_after_shutdown(paper_original, predeclared=predeclared)
            )
        except PaperEOFRejected as exc:
            result["paper_eof_shape_error"] = str(exc)
    return result
