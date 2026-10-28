"""T1f DEV source snapshot schema; no R qualification or Action authority."""
from __future__ import annotations

import math
import re

STATUSES = {"ADMITTED", "STALE", "MISSING", "LATE", "UNDETERMINED"}
ASSESSMENTS = {"UNKNOWN", "LOW_HEALTH", "LOW_FOOD", "KNOWN_NEAR_HOSTILE", "NO_KNOWN_URGENT_SIGNAL"}
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SNAPSHOT_KEYS = set("version boot index tick world_tick paper_ns world player challenge x y z health food input threats_complete threats basal_ticks basal_exhaustion motion_blocks motion_exhaustion".split())
RESULT_KEYS = set("snapshot status reason assessment latest_confirmed_tick received_ns evaluation_start_ns evaluation_completed_ns age_upper_ns age_lower_ns paper_to_node_exact_ns cache_mismatch qualification tps_admission_granted challenge_sent_ns control".split())


def natural(v):
    return type(v) is int and 0 <= v < 2**53


def finite(v):
    return type(v) in (float, int) and math.isfinite(v)


def validate_result(d):
    if type(d) is not dict or set(d) not in (RESULT_KEYS, RESULT_KEYS | {"applied_controls_dev"}):
        raise ValueError("invalid T1f result fields")
    if "applied_controls_dev" in d:
        controls = d["applied_controls_dev"]
        if (type(controls) is not dict or set(controls) != {
                "forward", "back", "left", "right", "jump", "sneak", "sprint"}
                or any(type(v) is not bool for v in controls.values())):
            raise ValueError("invalid T1u applied control observation")
    s = d["snapshot"]
    if (type(s) is not dict or set(s) not in (SNAPSHOT_KEYS, SNAPSHOT_KEYS | {"gait_dev"})
            or s["version"] != 1
            or not all(type(s[k]) is str and UUID.fullmatch(s[k]) for k in ("boot", "world", "player"))
            or not all(natural(s[k]) for k in ("index", "tick", "world_tick", "paper_ns", "basal_ticks", "input", "food"))
            or not 1 <= s["index"] <= 2400 or s["input"] > 127 or s["food"] > 20
            or not all(finite(s[k]) for k in ("x", "y", "z", "health", "basal_exhaustion", "motion_blocks", "motion_exhaustion"))
            or not 0 <= s["health"] <= 2048
            or any(s[k] < 0 for k in ("basal_exhaustion", "motion_blocks", "motion_exhaustion"))
            or type(s["challenge"]) is not str
            or re.fullmatch(r"NONE|[0-9a-f]{32}:[1-9][0-9]{0,3}", s["challenge"]) is None
            or type(s["threats_complete"]) is not bool
            or type(s["threats"]) is not list or len(s["threats"]) > 128):
        raise ValueError("invalid T1f Paper body")
    if "gait_dev" in s:
        g = s["gait_dev"]
        if (type(g) is not dict or set(g) != {
                "sneaking", "sprinting", "speed_base", "speed_value", "speed_modifiers"}
                or any(type(g[k]) is not bool for k in ("sneaking", "sprinting"))
                or not all(finite(g[k]) and g[k] > 0 for k in ("speed_base", "speed_value"))
                or not natural(g["speed_modifiers"])):
            raise ValueError("invalid T1u passive gait facts")
    for t in s["threats"]:
        if (type(t) is not dict or set(t) != {"id", "kind", "x", "y", "z", "distance"}
                or not isinstance(t["id"], str) or UUID.fullmatch(t["id"]) is None
                or not isinstance(t["kind"], str) or not t["kind"]
                or not all(finite(t[k]) for k in ("x", "y", "z", "distance"))
                or not 0 <= t["distance"] <= 4
                or not math.isclose(math.dist([t[k] for k in ("x", "y", "z")],
                                              [s[k] for k in ("x", "y", "z")]),
                                    t["distance"], abs_tol=1e-6)):
            raise ValueError("invalid T1f threat")
    for k in ("received_ns", "evaluation_start_ns", "evaluation_completed_ns", "age_lower_ns"):
        if type(d[k]) is not str or re.fullmatch(r"0|[1-9][0-9]{0,19}", d[k]) is None:
            raise ValueError("invalid T1f Node clock")
    if (d["status"] not in STATUSES or d["assessment"] not in ASSESSMENTS
            or type(d["reason"]) is not str or not d["reason"]
            or d["qualification"] is not False or d["tps_admission_granted"] is not False
            or d["paper_to_node_exact_ns"] is not None
            or (d["cache_mismatch"] is not None and type(d["cache_mismatch"]) is not bool)
            or not natural(d["latest_confirmed_tick"])):
        raise ValueError("invalid T1f admission")
    c = d["control"]
    if (type(c) is not dict or set(c) != {"phase", "since_ns", "generation"}
            or c["phase"] not in {"INITIAL", "MOVING", "CLEARED"}
            or not natural(c["generation"]) or not isinstance(c["since_ns"], str)
            or re.fullmatch(r"0|[1-9][0-9]{0,19}", c["since_ns"]) is None):
        raise ValueError("invalid control phase")
    if d["status"] == "ADMITTED":
        sent = d["challenge_sent_ns"]
        if (type(sent) is not str or re.fullmatch(r"0|[1-9][0-9]{0,19}", sent) is None
                or int(sent) > int(d["received_ns"])):
            raise ValueError("invalid causal challenge timestamp")
        age = d["age_upper_ns"]
        if (type(age) is not str or re.fullmatch(r"0|[1-9][0-9]{0,19}", age) is None
                or not 0 <= int(d["age_lower_ns"]) <= int(age) < 150_000_000
                or not int(d["received_ns"]) <= int(d["evaluation_start_ns"]) <= int(d["evaluation_completed_ns"])
                or int(d["evaluation_completed_ns"]) - int(d["received_ns"]) >= 25_000_000
                or int(d["age_lower_ns"]) != int(d["evaluation_completed_ns"]) - int(d["received_ns"])
                or d["latest_confirmed_tick"] != s["tick"] or not s["threats_complete"]
                or s["challenge"] == "NONE"):
            raise ValueError("false fresh admission")
        expected = ("LOW_HEALTH" if s["health"] <= 6 else "LOW_FOOD" if s["food"] <= 6
                    else "KNOWN_NEAR_HOSTILE" if s["threats"] else "NO_KNOWN_URGENT_SIGNAL")
        if d["assessment"] != expected:
            raise ValueError("assessment disagrees with Paper")
    elif d["assessment"] != "UNKNOWN":
        raise ValueError("refusal cannot continue")
