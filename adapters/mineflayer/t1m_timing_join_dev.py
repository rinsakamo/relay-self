"""T1m read-only sidecar join. Never subtract JVM and Node clock values.

The JVM durations are measured inside ONE JVM nanoTime domain. The Node
challenge→receive bound is measured inside ONE Node hrtime domain.
The cross-domain offsets, Paper-to-Node one-way delay and root cause remain
UNKNOWN. This reducer cannot admit a previously refused source frame.
"""
from __future__ import annotations

from collections import Counter
from statistics import median
from math import ceil


def _line_fields(line, marker):
    if marker not in line:
        return None
    fields = {}
    for item in line.split(marker, 1)[1].strip().split():
        if "=" in item:
            k, v = item.split("=", 1)
            fields[k] = v
    return fields


def _int(value):
    if type(value) is int and not isinstance(value, bool):
        return value
    if type(value) is str and value.isascii() and value.isdecimal():
        return int(value)
    raise ValueError("missing/invalid T1m numeric field")


def _stats(values):
    if not values:
        return {"n": 0, "median": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)
    return {
        "n": len(values), "median": round(median(ordered), 6),
        "p95": round(ordered[ceil(.95 * len(values)) - 1], 6),
        "p99": round(ordered[ceil(.99 * len(values)) - 1], 6),
        "max": round(ordered[-1], 6),
    }


def analyze_t1m_timing(paper_lines, node_sidecar, native_records):
    """Correlate exactly: native snapshot(index, challenge) ↔ JVM ↔ Node."""
    java_rx = {}
    java_cb = {}
    issues = []
    for line in paper_lines:
        if (d := _line_fields(line, "T1M_DEV_JVM_CHALLENGE_RX ")) is not None:
            key = d.get("challenge")
            if not key or key in java_rx:
                issues.append("duplicate_or_missing_java_challenge_rx")
            else:
                java_rx[key] = d
        if (d := _line_fields(line, "T1M_DEV_JVM_CALLBACK ")) is not None:
            try:
                key = (_int(d["index"]), d["challenge"])
            except (KeyError, ValueError):
                issues.append("malformed_java_callback")
                continue
            if key in java_cb:
                issues.append("duplicate_java_callback")
            else:
                java_cb[key] = d
    node_issues = {}
    node_cb = {}
    for e in node_sidecar:
        if not isinstance(e, dict):
            issues.append("invalid_node_sidecar_object")
            continue
        if e.get("kind") == "challenge_write_return":
            key = e.get("challenge")
            if not key or key in node_issues:
                issues.append("duplicate_node_challenge_issue")
            else:
                node_issues[key] = e
        elif e.get("kind") == "snapshot_callback":
            try:
                key = (_int(e["index"]), e["challenge"])
            except (KeyError, ValueError):
                issues.append("invalid_node_callback")
                continue
            if key in node_cb:
                issues.append("duplicate_node_callback")
            else:
                node_cb[key] = e
        else:
            issues.append("unknown_node_sidecar_kind")
    native = []
    seen_native = set()
    for record in native_records:
        if not isinstance(record, dict):
            issues.append("invalid_native_record")
            continue
        if record.get("type") != "paper_snapshot":
            continue
        try:
            d = record["data"]
            s = d["snapshot"]
            key = (_int(s["index"]), s["challenge"])
        except (KeyError, ValueError, TypeError):
            issues.append("invalid_native_snapshot")
            continue
        if key in seen_native:
            issues.append("duplicate_native_snapshot")
        seen_native.add(key)
        native.append((key, d))
    metrics = {"node_a_ms": [], "jvm_rx_to_callback_ms": [],
               "jvm_callback_to_send_return_ms": [],
               "event_loop_delay_window_max_ms": []}
    matched = 0
    status_counts = Counter()
    for (index, challenge), raw in native:
        status_counts[str(raw.get("status"))] += 1
        jvm = java_cb.get((index, challenge))
        node = node_cb.get((index, challenge))
        sent = node_issues.get(challenge)
        rx = java_rx.get(challenge)
        if not all([jvm, node, sent, rx]):
            issues.append("missing_challenge_index_join")
            continue
        try:
            node_a = _int(node["node_received_ns"]) - _int(sent["node_sent_ns"])
            upper = _int(raw["age_upper_ns"])
            received = _int(raw["received_ns"])
            completed = _int(raw["evaluation_completed_ns"])
            jvm_rx_delta = _int(jvm["rx_to_callback_ns"])
            jvm_callback_delta = _int(jvm["callback_to_send_return_ns"])
            loop_max = _int(node["event_loop_delay_window_max_ns"])
            if (node_a < 0 or jvm_rx_delta < 0 or jvm_callback_delta < 0
                    or loop_max < 0 or received != _int(node["node_received_ns"])
                    or completed != _int(node["node_complete_ns"])
                    or upper != completed - _int(sent["node_sent_ns"])
                    or node["status"] != raw["status"]
                    or node["reason"] != raw["reason"]
                    or _int(jvm["world_tick"]) != _int(raw["snapshot"]["world_tick"])):
                issues.append("cross_source_join_inconsistent")
                continue
        except (KeyError, ValueError, TypeError):
            issues.append("malformed_join_timing")
            continue
        metrics["node_a_ms"].append(node_a / 1e6)
        metrics["jvm_rx_to_callback_ms"].append(jvm_rx_delta / 1e6)
        metrics["jvm_callback_to_send_return_ms"].append(jvm_callback_delta / 1e6)
        metrics["event_loop_delay_window_max_ms"].append(loop_max / 1e6)
        matched += 1
    return {
        "classification": "T1M_PASSIVE_JVM_NODE_DIAGNOSTIC_ONLY",
        "qualification": False,
        "protocol_snapshot_schema_unchanged": True,
        "source_statuses_original": dict(status_counts),
        "original_native_paper_count": len(native),
        "matched_positive_jvm_samples": matched,
        "source_integrity_violations": sorted(set(issues)),
        "distributions_ms": {k: _stats(v) for k, v in metrics.items()},
        "node_clock_comparable_to_jvm_clock": False,
        "jvm_to_node_one_way_latency_known": False,
        "event_loop_delay_correlated_to_exact_packet": False,
        "root_cause": "UNKNOWN",
    }
