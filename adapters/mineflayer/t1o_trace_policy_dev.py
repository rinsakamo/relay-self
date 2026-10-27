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
