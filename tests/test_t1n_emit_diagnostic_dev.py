"""T1n original native + T1m Node sidecar + per-emit phase join negatives."""
from copy import deepcopy

from adapters.mineflayer.t1n_emit_diagnostic_dev import analyze_t1n_emit


def fixture():
    challenge = "a" * 32 + ":17"
    native = [{
        "type": "paper_snapshot", "session_id": "S", "seq": 8,
        "data": {
            "status": "ADMITTED",
            "snapshot": {"index": 17, "challenge": challenge}
        }
    }]
    emit = [{
        "kind": "t1n_emit_paper_snapshot", "diagnostic_version": 1,
        "session_id": "S", "seq": 8, "source_index": 17,
        "challenge": challenge, "source_status": "ADMITTED",
        "entry_ns": "100000000", "envelope_return_ns": "100100000",
        "trace_serialize_return_ns": "100200000",
        "trace_write_return_ns": "152200000",
        "stdout_serialize_return_ns": "152300000",
        "stdout_write_return_ns": "152500000",
        "stdout_write_return_is_delivery_ack": False,
        "node_clock_only": True, "process_cpu_user_us": 300,
        "process_cpu_system_us": 120,
    }]
    sidecar = [
        {"kind": "snapshot_callback", "index": 17,
         "challenge": challenge, "status": "ADMITTED",
         "node_complete_ns": "99900000"},
        {"kind": "challenge_write_return", "previous_index": 17,
         "previous_emit_return_ns": "152700000", "previous_complete_ns": "99900000",
         "previous_diagnostic_start_ns": "152710000",
         "previous_diagnostic_return_ns": "152800000", "node_sent_ns": "152900000"},
    ]
    return native, emit, sidecar


def test_original_paper_status_is_preserved_and_trace_stall_is_isolated():
    audit = analyze_t1n_emit(*fixture())
    assert audit["native_paper_count"] == 1
    assert audit["matched_paper_count"] == 1
    assert audit["original_statuses"] == {"ADMITTED": 1}
    assert audit["source_integrity_violations"] == []
    ms = audit["distributions_ms"]
    assert ms["trace_sync_write_ms"]["max"] == 52
    assert ms["stdout_call_ms"]["max"] == .2
    assert ms["post_stdout_to_emit_return_ms"]["max"] == .2
    assert ms["post_eval_to_emit_entry_ms"]["max"] == .1
    assert audit["stdout_write_returned_false_count"] == 0
    assert ms["emit_native_call_total_ms"]["max"] == 52.5
    assert not audit["native_stdout_write_acknowledged_by_python"]
    assert audit["scheduler_or_gc_root_cause"] == "UNKNOWN"


def test_stale_native_remains_stale():
    native, side, other = fixture()
    native[0]["data"]["status"] = "STALE"
    side[0]["source_status"] = "STALE"
    other[0]["status"] = "STALE"
    audit = analyze_t1n_emit(native, side, other)
    assert audit["original_statuses"] == {"STALE": 1}
    assert audit["matched_paper_count"] == 1
    assert not audit["source_qualification"]


def test_missing_emit_sidecar_is_explicit_diagnostic_gap():
    native, side, other = fixture()
    audit = analyze_t1n_emit(native, [], other)
    assert audit["matched_paper_count"] == 0
    assert "missing_or_extra_emit_sidecar" in audit["source_integrity_violations"]


def test_duplicate_seq_cannot_mint_extra_validated_source():
    native, side, other = fixture()
    audit = analyze_t1n_emit(native, side + [deepcopy(side[0])], other)
    assert audit["matched_paper_count"] == 1
    assert "emit_duplicate_or_invalid_seq" in audit["source_integrity_violations"]


def test_node_clock_order_violation_never_accepted():
    native, side, other = fixture()
    side[0]["trace_write_return_ns"] = "199999999"
    audit = analyze_t1n_emit(native, side, other)
    assert audit["matched_paper_count"] == 0
    assert "invalid_emit_clock_or_cpu" in audit["source_integrity_violations"]


def test_foreign_session_or_challenge_refused():
    native, side, other = fixture()
    side[0]["session_id"] = "OTHER"
    audit = analyze_t1n_emit(native, side, other)
    assert audit["matched_paper_count"] == 0
    assert "source_identity_or_status_mismatch" in audit["source_integrity_violations"]


def test_no_stdout_receipt_claim_from_write_return():
    native, side, other = fixture()
    side[0]["stdout_write_return_is_delivery_ack"] = True
    audit = analyze_t1n_emit(native, side, other)
    assert audit["matched_paper_count"] == 0
    assert "invalid_emit_clock_or_cpu" in audit["source_integrity_violations"]


def test_stdout_false_is_only_backpressure_signal_not_receive_confirmation():
    native, side, other = fixture()
    side[0]["stdout_write_accepted"] = False
    audit = analyze_t1n_emit(native, side, other)
    assert audit["matched_paper_count"] == 1
    assert audit["stdout_write_returned_false_count"] == 1
    assert audit["native_stdout_write_acknowledged_by_python"] is False


def test_seq_challenge_status_and_native_completion_mismatch():
    for field, value in (("seq", 9), ("challenge", "foreign"),
                         ("source_status", "STALE")):
        native, side, other = fixture()
        side[0][field] = value
        audit = analyze_t1n_emit(native, side, other)
        assert audit["matched_paper_count"] == 0
        assert audit["source_integrity_violations"]
    native, side, other = fixture()
    native[0]["data"]["evaluation_completed_ns"] = "1"
    assert analyze_t1n_emit(native, side, other)["matched_paper_count"] == 0


def test_post_emit_duplicate_or_forged_complete_refused():
    native, side, other = fixture()
    assert "duplicate_post_emit_record" in analyze_t1n_emit(
        native, side, other + [deepcopy(other[1])])["source_integrity_violations"]
    other[1]["previous_complete_ns"] = "1"
    assert analyze_t1n_emit(native, side, other)["matched_paper_count"] == 0


def test_missing_next_issue_is_unknown_not_zero():
    native, side, other = fixture()
    audit = analyze_t1n_emit(native, side, other[:1])
    assert audit["source_integrity_violations"] == []
    assert audit["matched_paper_count"] == 1
    assert audit["distributions_ms"]["post_stdout_to_emit_return_ms"]["n"] == 0
    assert audit["largest_emit_events"][0]["emit_total_ms"] is None


def test_reused_challenge_and_unapplied_issue_do_not_change_snapshot_join():
    native, side, other = fixture()
    n, s, callback = deepcopy(native[0]), deepcopy(side[0]), deepcopy(other[0])
    n["seq"] += 1
    n["data"]["snapshot"]["index"] += 1
    s.update(seq=n["seq"], source_index=18)
    callback["index"] = 18
    audit = analyze_t1n_emit(native + [n], side + [s], other + [callback,
        {"kind": "challenge_write_return", "challenge": "unused"}])
    assert audit["source_integrity_violations"] == []
    assert audit["matched_paper_count"] == 2
    assert audit["largest_emit_events"][0]["next_tick_reuses_challenge"] is True
