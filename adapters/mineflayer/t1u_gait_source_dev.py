"""Passive original-Paper callback gait evidence; no issuer or reader.

Only stable ordinary back movement is certified in this bounded DEV slice.
Edge/residual/initial-idle intervals remain UNDETERMINED. A typed gait or
requested Action is never used as evidence of a mode. Not R full-tick proof.
"""
from __future__ import annotations

import math

from experiments.p1_gait_dev import GaitTickDev


def applied_gait_source_dev(current, previous, wait):
    """Use the admitted two-endpoint source plus the original T2 WAIT decision."""
    s, p = current.data["snapshot"], previous.data["snapshot"]
    if (current.session_id != previous.session_id
            or any(s[k] != p[k] for k in ("world", "player", "boot"))
            or current.data["status"] != "ADMITTED"
            or previous.data["status"] != "ADMITTED"
            or s["world_tick"] != p["world_tick"] + 1
            or s["tick"] != p["tick"] + 1 or s["index"] != p["index"] + 1
            or current.seq <= previous.seq):
        raise ValueError("NATIVE_GAIT_NOT_ATTESTED: source identity/continuity")
    facts = [v.get("gait_dev") for v in (p, s)]
    ordinary = all(
        isinstance(g, dict) and g.get("sneaking") is False
        and g.get("sprinting") is False and g.get("speed_modifiers") == 0
        and math.isclose(g.get("speed_base", -1), .1, abs_tol=1e-7)
        and math.isclose(g.get("speed_value", -1), .1, abs_tol=1e-7)
        for g in facts)
    if wait:
        observed_idle = all(
            f.data.get("applied_controls_dev") == dict.fromkeys((
                "forward", "back", "left", "right", "jump", "sneak", "sprint"), False)
            for f in (previous, current))
        if not ordinary or not observed_idle or s["input"] != 0 or p["input"] != 0:
            raise ValueError("NATIVE_GAIT_NOT_ATTESTED: WAIT mode contradiction")
        return GaitTickDev(current.session_id, s["world_tick"], "WAIT")
    phases = [f.data["control"] for f in (previous, current)]
    back_only = {k: k == "back" for k in (
        "forward", "back", "left", "right", "jump", "sneak", "sprint")}
    observed_back = all(f.data.get("applied_controls_dev") == back_only
                        for f in (previous, current))
    if (ordinary and observed_back and p["input"] in (0, 2) and s["input"] in (0, 2)
            and all(c["phase"] == "MOVING" for c in phases)
            and phases[0]["generation"] == phases[1]["generation"]
            and int(previous.data["challenge_sent_ns"]) > int(phases[0]["since_ns"])
            and s["motion_blocks"] > p["motion_blocks"]
            and math.dist([s[k] for k in ("x", "z")], [p[k] for k in ("x", "z")]) > 0):
        return GaitTickDev(current.session_id, s["world_tick"], "JOG", direction="back")
    raise ValueError("NATIVE_GAIT_NOT_ATTESTED: initial/edge/residual or unsupported mode")
