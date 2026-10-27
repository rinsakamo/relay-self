"""T1m read-only sidecar join. Never subtract JVM and Node clock values.

The JVM durations are measured inside ONE JVM nanoTime domain. The Node
challenge→receive bound is measured inside ONE Node hrtime domain.
The cross-domain offsets, Paper-to-Node one-way delay and root cause remain
UNKNOWN. This reducer cannot admit a previously refused source frame.
"""
from __future__ import annotations

from collections import Counter
from math import ceil
from statistics import median


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
        return {"n": 0, "min": None, "median": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)
    return {
        "n": len(values), "min": round(ordered[0], 6), "median": round(median(ordered), 6),
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
    native_indices = set()
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
        if key[0] in native_indices:
            issues.append("duplicate_native_index")
        native_indices.add(key[0])
        if key in seen_native:
            issues.append("duplicate_native_snapshot")
        seen_native.add(key)
        native.append((key, d))
    metrics = {"node_a_ms": [], "node_write_ms": [], "jvm_rx_to_callback_ms": [],
               "jvm_callback_to_send_return_ms": [],
               "event_loop_delay_window_max_ms": [],
               "post_eval_to_next_issue_ms": [], "post_eval_emit_ms": [],
               "diagnostic_hook_ms": [], "post_hook_to_issue_ms": []}
    post_by_key = {}
    preceding = None
    for event in node_sidecar:
        if not isinstance(event, dict):
            continue
        if event.get("kind") == "snapshot_callback":
            preceding = event
        elif event.get("kind") == "challenge_write_return":
            try:
                sent_ns = _int(event["node_sent_ns"])
                write_ns = _int(event["node_write_return_ns"]) - sent_ns
                if write_ns < 0:
                    raise ValueError("negative write duration")
                metrics["node_write_ms"].append(write_ns / 1e6)
                if preceding is not None:
                    complete = _int(preceding["node_complete_ns"])
                    post = sent_ns - complete
                    if post < 0:
                        raise ValueError("post-evaluation order")
                    key = (_int(preceding["index"]), preceding["challenge"])
                    detail = {"post_eval_to_next_issue_ms": post / 1e6}
                    if event.get("timing_revision") == 2:
                        emitted = _int(event["previous_emit_return_ns"])
                        hook_start = _int(event["previous_diagnostic_start_ns"])
                        hook_end = _int(event["previous_diagnostic_return_ns"])
                        if (event["previous_index"] != preceding["index"]
                                or _int(event["previous_complete_ns"]) != complete
                                or not complete <= emitted <= hook_start <= hook_end <= sent_ns):
                            raise ValueError("post-evaluation boundaries")
                        detail.update(post_eval_emit_ms=(emitted - complete) / 1e6,
                                      diagnostic_hook_ms=(hook_end - hook_start) / 1e6,
                                      post_hook_to_issue_ms=(sent_ns - hook_end) / 1e6)
                    post_by_key[key] = detail
                    for metric, value in detail.items():
                        metrics[metric].append(value)
                    preceding = None
            except (KeyError, ValueError, TypeError):
                issues.append("invalid_post_evaluation_timing")
    timeline = []
    matched = 0
    used_challenges = set()
    startup_none = 0
    sessions = {r.get("session_id") for r in native_records
                if isinstance(r, dict) and r.get("type") == "paper_snapshot"}
    if len(sessions) > 1:
        issues.append("native_session_changed")
    status_counts = Counter()
    for (index, challenge), raw in native:
        status_counts[str(raw.get("status"))] += 1
        jvm = java_cb.get((index, challenge))
        node = node_cb.get((index, challenge))
        if (index == 1 and challenge == "NONE"
                and raw.get("status") == "UNDETERMINED"
                and raw.get("reason") == "NO_MATCHING_CAUSAL_CHALLENGE"):
            startup_none += 1
            if not jvm or not node:
                issues.append("missing_startup_callback")
            else:
                try:
                    snap = raw["snapshot"]
                    if (node["status"] != raw["status"] or node["reason"] != raw["reason"]
                            or node["age_upper_ns"] is not None or raw["age_upper_ns"] is not None
                            or _int(node["world_tick"]) != _int(snap["world_tick"])
                            or _int(jvm["world_tick"]) != _int(snap["world_tick"])
                            or _int(node["node_received_ns"]) != _int(raw["received_ns"])
                            or any(node.get("source_" + k) != snap.get(k)
                                   or jvm.get(k) != snap.get(k) for k in ("boot", "world", "player"))):
                        issues.append("startup_callback_inconsistent")
                except (KeyError, ValueError, TypeError):
                    issues.append("malformed_startup_callback")
            continue
        used_challenges.add(challenge)
        sent = node_issues.get(challenge)
        rx = java_rx.get(challenge)
        if not all([jvm, node, sent, rx]):
            issues.append("missing_challenge_index_join")
            continue
        try:
            suffix = challenge.rsplit(":", 1)
            if (len(suffix) != 2 or len(suffix[0]) != 32
                    or any(c not in "0123456789abcdef" for c in suffix[0])
                    or not 1 <= _int(suffix[1]) <= 2400
                    or _int(sent["challenge_index"]) != _int(suffix[1])):
                raise ValueError("invalid challenge identity/index")
            node_write = _int(sent["node_write_return_ns"]) - _int(sent["node_sent_ns"])
            node_a = _int(node["node_received_ns"]) - _int(sent["node_sent_ns"])
            upper = _int(raw["age_upper_ns"])
            received = _int(raw["received_ns"])
            completed = _int(raw["evaluation_completed_ns"])
            jvm_rx_delta = _int(jvm["rx_to_callback_ns"])
            jvm_callback_delta = _int(jvm["callback_to_send_return_ns"])
            loop_max = _int(node["event_loop_delay_window_max_ns"])
            snap = raw["snapshot"]
            if (node_write < 0 or node_write > node_a
                    or completed < received
                    or _int(raw["challenge_sent_ns"]) != _int(sent["node_sent_ns"])
                    or node.get("age_upper_ns") != raw.get("age_upper_ns")
                    or any(node.get("source_" + k) != snap.get(k)
                           or jvm.get(k) != snap.get(k) for k in ("boot", "world", "player"))
                    or _int(node["world_tick"]) != _int(snap["world_tick"])
                    or _int(node["server_tick"]) != _int(snap["tick"])
                    or _int(jvm["server_tick"]) != _int(snap["tick"])
                    or _int(jvm["jvm_rel_ns"]) - _int(rx["jvm_rel_ns"])
                       != jvm_rx_delta + jvm_callback_delta
                    or node_a < 0 or jvm_rx_delta < 0 or jvm_callback_delta < 0
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
        timeline.append({"index": index, "challenge": challenge,
                         "world_tick": raw["snapshot"]["world_tick"],
                         "status": raw["status"], "node_a_ms": node_a / 1e6,
                         "node_write_ms": node_write / 1e6,
                         "jvm_d_ms": jvm_rx_delta / 1e6,
                         "jvm_e_ms": jvm_callback_delta / 1e6,
                         "event_loop_window_max_ms": loop_max / 1e6,
                         **post_by_key.get((index, challenge), {})})
        matched += 1
    unmatched_java = set(java_cb) - seen_native
    unmatched_node = set(node_cb) - seen_native
    shutdown_java = set()
    last_native = max((key[0] for key in seen_native), default=0)
    identity = native[-1][1]["snapshot"] if native else {}
    for key in unmatched_java:
        sample = java_cb[key]
        if (key[0] > last_native and all(sample.get(k) == identity.get(k)
                                        for k in ("boot", "world", "player"))):
            shutdown_java.add(key)
    if unmatched_java - shutdown_java:
        issues.append("unmatched_java_callback")
    if sorted(k[0] for k in shutdown_java) != list(
            range(last_native + 1, last_native + 1 + len(shutdown_java))):
        issues.append("shutdown_java_tail_gap")
    if unmatched_node:
        issues.append("unmatched_node_callback")
    # The last next-challenge may be written/received without another callback
    # before shutdown. Preserve and classify it; never invent a matching tick.
    unused_issues = set(node_issues) - used_challenges
    unused_rx = set(java_rx) - used_challenges
    tail = max(node_issues, key=lambda k: _int(node_issues[k]["node_sent_ns"]), default=None)
    superseded = []
    for challenge in unused_issues - {tail}:
        try:
            arrival = _int(java_rx[challenge]["jvm_rel_ns"])
            later = any(_int(java_rx[k]["jvm_rel_ns"]) >= arrival
                        and _int(k.rsplit(":", 1)[1]) > _int(challenge.rsplit(":", 1)[1])
                        for k in java_rx)
            if not later:
                raise ValueError("unexplained unused challenge")
            superseded.append(challenge)
        except (KeyError, ValueError, TypeError):
            issues.append("unmatched_nonterminal_challenge")
    indices = []
    tokens = set()
    for challenge, event in node_issues.items():
        try:
            token, suffix = challenge.rsplit(":", 1)
            idx = _int(suffix)
            if (len(token) != 32 or any(c not in "0123456789abcdef" for c in token)
                    or not 1 <= idx <= 2400 or _int(event["challenge_index"]) != idx
                    or _int(event["node_write_return_ns"]) < _int(event["node_sent_ns"])):
                raise ValueError("invalid issued challenge")
            indices.append(idx)
            tokens.add(token)
        except (KeyError, ValueError, TypeError):
            issues.append("invalid_issued_challenge")
    if indices != list(range(1, len(indices) + 1)) or len(tokens) > 1:
        issues.append("challenge_issue_history_gap_or_identity_change")
    if set(java_rx) - set(node_issues):
        issues.append("java_rx_without_node_issue")
    return {
        "matched_timeline": timeline,
        "startup_none_callbacks": startup_none,
        "unmatched_java_callbacks": len(unmatched_java),
        "shutdown_java_without_node_receipt": sorted(shutdown_java),
        "unmatched_node_callbacks": len(unmatched_node),
        "superseded_unapplied_challenges": sorted(superseded),
        "terminal_unapplied_node_challenges": sorted(unused_issues & {tail}),
        "terminal_unapplied_java_challenges": sorted(unused_rx & {tail}),
        "java_challenge_rx_count": len(java_rx),
        "node_challenge_issue_count": len(node_issues),
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
