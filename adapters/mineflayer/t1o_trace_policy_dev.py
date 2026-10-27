"""T1o DEV timing trace opt-in; native source remains authoritative.

T1m/T1n explicitly diagnostic sessions retain their previous detailed trace.
Every other T1e case defaults to no synchronous timing trace, and may
explicitly opt in for an isolated A/B comparison. No source/protocol changes.
"""

DIAGNOSTIC_CASES = frozenset({"t1m_source_soak", "t1n_source_soak"})


def trace_enabled(case: str, requested: str = "off") -> bool:
    if requested not in ("off", "on"):
        raise ValueError("node timing trace must be off/on")
    if requested == "off" and case in DIAGNOSTIC_CASES:
        # Explicit diagnostic case selection is itself a trace opt-in.
        return True
    return requested == "on"


def journal_name(*, enabled: bool) -> str:
    return "node_timing.jsonl" if enabled else "native.jsonl"


# Types for which the original bridge writes a synchronous Node trace.
TRACE_TYPES = frozenset({
    "paper_tick_sample", "paper_l0_shadow", "effect_result",
    "adapter_error", "paper_snapshot",
})


def audit_trace_pair(native_records, trace_records, *, enabled: bool, trace_exists: bool):
    """Audit original trace's exact subset, independent from T1f admission.

    Trace OFF intentionally has NO journal. Trace ON must have a valid original
    journal and identical canonical native envelopes (plus Node clock field).
    This is a DEV sidecar integrity check, not an authenticator or R gate.
    """
    expected = [r for r in native_records if r.get("type") in TRACE_TYPES]
    if not enabled:
        return {
            "mode": "OFF", "source_native_paper_count": sum(
                r.get("type") == "paper_snapshot" for r in native_records),
            "trace_count": 0, "valid": not trace_exists and not trace_records,
            "timing_metrics_available": False,
        }
    valid = trace_exists and bool(expected) and len(expected) == len(trace_records)
    previous = -1
    for original, traced in zip(expected, trace_records):
        if not isinstance(traced, dict):
            valid = False
            continue
        stamp = traced.get("node_monotonic_ns")
        if (not isinstance(stamp, str) or not stamp.isascii() or not stamp.isdecimal()
                or int(stamp) < previous
                or {k: v for k, v in traced.items() if k != "node_monotonic_ns"}
                   != original):
            valid = False
        if isinstance(stamp, str) and stamp.isascii() and stamp.isdecimal():
            previous = int(stamp)
    return {
        "mode": "ON", "source_native_paper_count": sum(
            r.get("type") == "paper_snapshot" for r in native_records),
        "trace_count": len(trace_records), "valid": bool(valid),
        "timing_metrics_available": bool(valid),
    }
