"""DEV physical rest witness, distinct from S49 Action WAIT qualification.

WorldBody may be physically motionless before an Action has ever closed.
This is NOT a control-plane WAIT/clear ACK, and is not R full-tick proof.
Only the existing T1u Paper/Node observations are read; no extra receiver.
"""
from __future__ import annotations

import math

from adapters.mineflayer.t1u_gait_source_dev import applied_gait_source_dev
from experiments.p1_gait_dev import GaitTickDev

_CONTROLS = ("forward", "back", "left", "right", "jump", "sneak", "sprint")


def physical_idle_witness_dev(current, previous) -> bool:
    """Conservative *sampled* stationary-body evidence, no Action authority.

    Both source endpoints must have unchanged pose/motion counter, zero input,
    all Node applied controls off, vanilla unmodified physical speed, no
    threats, and one stable INITIAL or CLEARED owner generation. This only
    supports a DEV body rest model; the full intervening tick is not R-attested.
    """
    if current.session_id != previous.session_id:
        return False
    d, pd = current.data, previous.data
    s, p = d["snapshot"], pd["snapshot"]
    if (d["status"] != "ADMITTED" or pd["status"] != "ADMITTED"
            or current.seq <= previous.seq
            or s["world_tick"] != p["world_tick"] + 1
            or s["tick"] != p["tick"] + 1
            or s["index"] != p["index"] + 1
            or any(s[k] != p[k] for k in ("boot", "world", "player"))
            or s["input"] != 0 or p["input"] != 0
            or s["threats"] or p["threats"]
            or not s["threats_complete"] or not p["threats_complete"]):
        return False
    if (not all(s[k] == p[k] for k in ("x", "y", "z", "motion_blocks"))
            or not math.isfinite(s["motion_blocks"])):
        return False
    for source in (d, pd):
        applied = source.get("applied_controls_dev")
        if (type(applied) is not dict or set(applied) != set(_CONTROLS)
                or any(applied[k] is not False for k in _CONTROLS)):
            return False
        gait = source["snapshot"].get("gait_dev")
        if (type(gait) is not dict or gait.get("sneaking") is not False
                or gait.get("sprinting") is not False
                or gait.get("speed_modifiers") != 0
                or not math.isclose(gait.get("speed_base", -1), .1, abs_tol=1e-7)
                or not math.isclose(gait.get("speed_value", -1), .1, abs_tol=1e-7)):
            return False
    phase, prior = d["control"], pd["control"]
    return (phase["phase"] == prior["phase"]
            and phase["phase"] in ("INITIAL", "CLEARED")
            and phase["generation"] == prior["generation"]
            and int(d["challenge_sent_ns"]) > int(phase["since_ns"])
            and int(pd["challenge_sent_ns"]) > int(prior["since_ns"]))


def applied_gait_or_physical_idle_dev(current, previous, causal_wait):
    """Strict original JOG/WAIT provider, plus explicit pre-Action body rest.

    No guess at the onset, residual, coasting or obstructed motor gait.
    """
    if not causal_wait and physical_idle_witness_dev(current, previous):
        return GaitTickDev(
            current.session_id, current.data["snapshot"]["world_tick"], "WAIT")
    return applied_gait_source_dev(current, previous, causal_wait)
