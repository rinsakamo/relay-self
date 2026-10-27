"""T1n read-only Node emitter phase diagnostics; no source promotion.

Compare original native Paper messages, opt-in emit sidecar, and T1m
snapshot/next-challenge sidecar in the same NODE monotonic clock only.
Node CPU usage is per process and is not proof of GC or OS scheduling cause.
"""
from __future__ import annotations

from collections import Counter
from math import ceil
from statistics import median


def _ns(raw):
    if raw is None:
        return None
    if type(raw) is str and raw.isascii() and raw.isdecimal():
        return int(raw)
    raise ValueError("invalid Node monotonic timestamp")


def _stats(values):
    if not values:
        return {"n": 0, "min": None, "median": None, "p95": None,
                "p99": None, "max": None}
    s = sorted(values)
    return {"n": len(s), "min": round(s[0], 6),
            "median": round(median(s), 6),
            "p95": round(s[ceil(.95 * len(s)) - 1], 6),
            "p99": round(s[ceil(.99 * len(s)) - 1], 6),
            "max": round(s[-1], 6)}


def analyze_t1n_emit(native, emit_sidecar, t1m_sidecar):
    issues = []
    native_by_seq = {}
    emitted_by_seq = {}
    stats = Counter()
    for row in native:
        if row.get("type") != "paper_snapshot":
            continue
        seq = row.get("seq")
        if type(seq) is not int or seq in native_by_seq:
            issues.append("native_duplicate_or_invalid_seq")
        else:
            native_by_seq[seq] = row
            stats[str(row["data"]["status"])] += 1
    for row in emit_sidecar:
        if (row.get("kind") != "t1n_emit_paper_snapshot"
                or row.get("diagnostic_version") != 1):
            issues.append("unknown_t1n_sidecar_record")
            continue
        seq = row.get("seq")
        if type(seq) is not int or seq in emitted_by_seq:
            issues.append("emit_duplicate_or_invalid_seq")
        else:
            emitted_by_seq[seq] = row
    t1m_by_key = {}
    for row in t1m_sidecar:
        if row.get("kind") != "snapshot_callback":
            continue
        key = (row.get("index"), row.get("challenge"))
        if key in t1m_by_key:
            issues.append("t1m_duplicate_snapshot_callback")
        else:
            t1m_by_key[key] = row
    if native_by_seq.keys() != emitted_by_seq.keys():
        issues.append("missing_or_extra_emit_sidecar")
    fields = {
        "envelope_ms": [], "trace_serialize_ms": [], "trace_sync_write_ms": [],
        "stdout_serialize_ms": [], "stdout_call_ms": [],
        "emit_native_call_total_ms": [], "post_stdout_to_emit_return_ms": [],
        "cpu_user_ms": [], "cpu_system_ms": [],
    }
    matched = 0
    events = []
    for seq, raw in native_by_seq.items():
        side = emitted_by_seq.get(seq)
        if side is None:
            continue
        source = raw["data"]["snapshot"]
        key = (source.get("index"), source.get("challenge"))
        snap = t1m_by_key.get(key)
        if snap is None:
            issues.append("missing_t1m_snapshot_join")
            continue
        if (raw.get("session_id") != side.get("session_id")
                or source.get("index") != side.get("source_index")
                or source.get("challenge") != side.get("challenge")
                or side.get("source_status") != raw["data"]["status"]
                or snap.get("status") != raw["data"]["status"]
                or snap.get("index") != source.get("index")):
            issues.append("source_identity_or_status_mismatch")
            continue
        try:
            entry = _ns(side["entry_ns"])
            envelope = _ns(side["envelope_return_ns"])
            trace_json = _ns(side["trace_serialize_return_ns"])
            trace_end = _ns(side["trace_write_return_ns"])
            stdout_json = _ns(side["stdout_serialize_return_ns"])
            stdout_end = _ns(side["stdout_write_return_ns"])
            complete = _ns(snap["node_complete_ns"])
            event_emitted = next((row for row in t1m_sidecar
                                  if row.get("kind") == "challenge_write_return"
                                  and row.get("previous_index") == source["index"]), None)
            emit_return = (_ns(event_emitted["previous_emit_return_ns"])
                           if event_emitted else None)
            if (None in (entry, envelope, trace_json, trace_end, stdout_json, stdout_end)
                    or not complete <= entry <= envelope <= trace_json <= trace_end
                    <= stdout_json <= stdout_end
                    or (emit_return is not None and emit_return < stdout_end)
                    or (side.get("stdout_write_return_is_delivery_ack") is not False)
                    or side.get("node_clock_only") is not True):
                raise ValueError("invalid T1n clock order/provenance")
            cpu_user = side["process_cpu_user_us"]
            cpu_sys = side["process_cpu_system_us"]
            if (type(cpu_user) is not int or type(cpu_sys) is not int
                    or cpu_user < 0 or cpu_sys < 0):
                raise ValueError("invalid CPU delta")
        except (KeyError, TypeError, ValueError):
            issues.append("invalid_emit_clock_or_cpu")
            continue
        sample = {
            "seq": seq, "source_index": source["index"],
            "source_status": raw["data"]["status"],
            "envelope_ms": (envelope-entry)/1e6,
            "trace_serialize_ms": (trace_json-envelope)/1e6,
            "trace_sync_write_ms": (trace_end-trace_json)/1e6,
            "stdout_serialize_ms": (stdout_json-trace_end)/1e6,
            "stdout_call_ms": (stdout_end-stdout_json)/1e6,
            "emit_native_call_total_ms": (stdout_end-entry)/1e6,
            "cpu_user_ms": cpu_user/1000,
            "cpu_system_ms": cpu_sys/1000,
        }
        if emit_return is not None:
            sample["post_stdout_to_emit_return_ms"] = (emit_return-stdout_end)/1e6
        for k,v in sample.items():
            if k in fields:
                fields[k].append(v)
        events.append(sample)
        matched += 1
    large = sorted(events, key=lambda x: x["emit_native_call_total_ms"], reverse=True)[:20]
    return {
        "classification": "T1N_NODE_EMIT_SUBPHASE_DIAGNOSTIC_ONLY",
        "source_qualification": False,
        "original_statuses": dict(stats),
        "native_paper_count": len(native_by_seq),
        "matched_paper_count": matched,
        "source_integrity_violations": sorted(set(issues)),
        "distributions_ms": {key: _stats(values) for key, values in fields.items()},
        "largest_emit_events": large,
        "native_stdout_write_acknowledged_by_python": False,
        "scheduler_or_gc_root_cause": "UNKNOWN",
    }
