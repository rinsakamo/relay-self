"""T1o: trace defaults OFF, native source metrics remain available."""
import json
import pytest

from adapters.mineflayer.t1o_trace_policy_dev import (
    trace_enabled, journal_name, audit_trace_pair,
)
from adapters.mineflayer.t1e_native_dev import measure


@pytest.mark.parametrize(("case", "requested", "expected"), [
    ("normal", "off", False),
    ("t1l_source_soak", "off", False),
    ("t1l_source_soak", "on", True),
    ("t1m_source_soak", "off", True),
    ("t1m_source_soak", "on", True),
    ("t1n_source_soak", "off", True),
    ("t1n_source_soak", "on", True),
])
def test_trace_is_explicitly_opted_in(case, requested, expected):
    assert trace_enabled(case, requested) is expected


def test_bad_trace_mode_fails_closed():
    with pytest.raises(ValueError, match="off/on"):
        trace_enabled("t1l_source_soak", "auto")


def test_journal_selector_keeps_independent_native_source():
    assert journal_name(enabled=False) == "native.jsonl"
    assert journal_name(enabled=True) == "node_timing.jsonl"


def test_trace_off_reads_original_native_source_without_creating_trace(tmp_path):
    rows = [
        {"type": "adapter_started", "seq": 0},
        {"type": "paper_snapshot", "seq": 1,
         "data": {"snapshot": {"tick": 11}, "status": "ADMITTED"}},
        {"type": "paper_snapshot", "seq": 2,
         "data": {"snapshot": {"tick": 12}, "status": "ADMITTED"}},
    ]
    (tmp_path / "native.jsonl").write_text(
        "\n".join(map(json.dumps, rows)) + "\n")
    (tmp_path / "commands.jsonl").write_text("")
    (tmp_path / "paper.log").write_text(
        "PAPER_DEV_TIME_SAMPLE server_tick=11 wall_nanos=0\n"
        "PAPER_DEV_TIME_SAMPLE server_tick=12 wall_nanos=50000000\n")
    metrics = measure(tmp_path, {"node_trace_enabled": False})
    assert metrics["journal_source"] == "native.jsonl"
    assert metrics["node_clock_trace_available"] is False
    assert metrics["node_received_ticks"] == 2
    assert metrics["node_admitted_ticks"] == 2
    assert metrics["paper_ticks_without_node_snapshot"] == []
    assert metrics["set_control_sends"] == 0
    assert not (tmp_path / "node_timing.jsonl").exists()


def test_explicit_trace_on_missing_journal_is_unavailable_not_zero_observations(tmp_path):
    (tmp_path / "paper.log").write_text("")
    (tmp_path / "commands.jsonl").write_text("")
    metrics = measure(tmp_path, {"node_trace_enabled": True})
    assert metrics["node_clock_trace_available"] is False
    assert metrics["journal_source"] == "native.jsonl"
    assert not audit_trace_pair([], [], enabled=True, trace_exists=False)["valid"]


def test_trace_on_preserves_historical_t1e_metrics(tmp_path):
    rows = [
        {"type": "paper_snapshot", "seq": 2,
         "data": {"snapshot": {"tick": 12}, "status": "ADMITTED"}},
    ]
    (tmp_path / "node_timing.jsonl").write_text(
        "\n".join(map(json.dumps, rows)) + "\n")
    (tmp_path / "paper.log").write_text(
        "PAPER_DEV_TIME_SAMPLE server_tick=12 wall_nanos=1\n")
    metrics = measure(tmp_path, {"node_trace_enabled": True})
    assert metrics["journal_source"] == "node_timing.jsonl"
    assert metrics["node_clock_trace_available"] is True
    assert metrics["node_admitted_ticks"] == 1


def test_trace_off_never_claims_legacy_node_clock_latency(tmp_path):
    frames = [
        {"type": "paper_l0_shadow", "seq": 4, "paper_server_tick": "11",
         "assessment": "LOW_HEALTH"},
        {"type": "effect_result", "effect": "set_control", "seq": 3,
         "result": "applied"},
        {"type": "effect_result", "effect": "clear_controls", "seq": 5,
         "result": "applied"},
    ]
    (tmp_path / "native.jsonl").write_text(
        "\n".join(map(json.dumps, frames)) + "\n")
    (tmp_path / "paper.log").write_text(
        "PAPER_DEV_TIME_SAMPLE server_tick=11 wall_nanos=0\n")
    metrics = measure(tmp_path, {"node_trace_enabled": False})
    assert metrics["node_shadow_emit_to_clear_applied_ms"] is None
    assert metrics["active_danger_assessment"] == "LOW_HEALTH"
    assert metrics["set_control_sends"] == 0


def test_trace_off_although_expected_native_rows_do_not_write_sync_trace():
    native = [{"type": "paper_snapshot", "seq": 7, "session_id": "S",
               "data": {"status": "ADMITTED"}}]
    audit = audit_trace_pair(native, [], enabled=False, trace_exists=False)
    assert audit["valid"] and audit["trace_count"] == 0
    assert audit["source_native_paper_count"] == 1
    assert not audit["timing_metrics_available"]


def test_off_mode_refuses_unexpected_timing_trace_file():
    assert not audit_trace_pair([], [], enabled=False, trace_exists=True)["valid"]


def test_on_mode_requires_exact_canonical_native_rows_and_node_clock_field():
    native = [{"type": "adapter_started", "seq": 0},
              {"type": "paper_snapshot", "seq": 1, "session_id": "S",
               "data": {"status": "ADMITTED"}}]
    recorded = [{"node_monotonic_ns": "1000000", **native[1]}]
    audit = audit_trace_pair(native, recorded, enabled=True, trace_exists=True)
    assert audit["valid"]
    assert audit["trace_count"] == 1
    assert audit["timing_metrics_available"]


def test_on_mode_refuses_missing_or_mutated_trace_without_source_promotion():
    native = [{"type": "paper_snapshot", "seq": 1, "session_id": "S",
               "data": {"status": "STALE"}}]
    assert not audit_trace_pair(native, [], enabled=True, trace_exists=True)["valid"]
    mismatch = [{"node_monotonic_ns": "1", **native[0], "seq": 2}]
    audit = audit_trace_pair(native, mismatch, enabled=True, trace_exists=True)
    assert not audit["valid"]
