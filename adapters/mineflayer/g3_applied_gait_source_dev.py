"""DEV-only applied-gait candidate for T2's single P1/M0 WorldTick owner.

Map ONLY stable original Node controls + Paper T1u physical observations.
Unknown, blocked and transient body states return None; never guess WAIT.
This is not packet-accepted, R-qualified gait.
"""
from __future__ import annotations

import math

from adapters.mineflayer.s49_t2_applied_gait_observation_dev import G1AppliedGaitObserverDev
from experiments.p1_gait_dev import GaitTickDev

_KIND_TO_GAIT = {
    "STABLE_SNEAK_FORWARD_CANDIDATE": "WALK",
    "STABLE_ORDINARY_FORWARD_CANDIDATE": "JOG",
    "STABLE_SPRINT_FORWARD_CANDIDATE": "RUN",
    "STABLE_DASH_MODIFIER_FORWARD_CANDIDATE": "DASH",
}


def applied_gait_from_original_t1u_dev(
    frame, previous, wait, *, strict_modifier_identity_dev: bool = False,
):
    """Return a candidate frame or None; original T2 alone advances state.

    G3.2 strict opt-in requires both Paper snapshots' server modifier
    identities and effective +50% boost, never a heuristic 2-modifier total.
    """
    if type(strict_modifier_identity_dev) is not bool:
        raise ValueError("G3_IDENTITY_GATE_INVALID")
    if type(wait) is not bool or frame.session_id != previous.session_id:
        raise ValueError("G3_FOREIGN_OR_NONBOOLEAN_SOURCE")
    if frame.data["status"] != previous.data["status"] or frame.data["status"] != "ADMITTED":
        raise ValueError("G3_PAPER_SOURCE_NOT_ADMITTED")
    observer=G1AppliedGaitObserverDev(frame.session_id)
    observer.observe(previous,t2_activity=None)
    observer.observe(frame,t2_activity=None)
    kind=observer.rows[-1].kind
    world_tick=frame.data["snapshot"]["world_tick"]
    if wait:
        if kind != "STABLE_PHYSICAL_IDLE_CANDIDATE":
            # T2's causally established source may be idle before Node
            # controls are sampled as stable: conservative unknown MOVE.
            return None
        return GaitTickDev(frame.session_id,world_tick,"WAIT")
    gait=_KIND_TO_GAIT.get(kind)
    if gait is None:
        return None
    if gait == "DASH":
        physical=frame.data["snapshot"]["gait_dev"]
        if (physical["speed_modifiers"] != 2
                or not math.isclose(physical["speed_base"],0.1,abs_tol=1e-6)
                or not math.isclose(physical["speed_value"],0.195,abs_tol=1e-5)):
            return None
        if strict_modifier_identity_dev:
            mods = physical.get("speed_modifier_details")
            previous_mods = previous.data["snapshot"]["gait_dev"].get(
                "speed_modifier_details")
            if mods != previous_mods or type(mods) is not list or len(mods) != 2:
                return None
            by_key = {mod["key"]: mod for mod in mods}
            if set(by_key) != {
                "minecraft:sprinting",
                "relays49dashdev:forward_dash_only",
            }:
                return None
            if (by_key["minecraft:sprinting"]["operation"] != "MULTIPLY_SCALAR_1"
                    or by_key["relays49dashdev:forward_dash_only"]["operation"]
                    != "MULTIPLY_SCALAR_1"
                    or not math.isclose(
                        by_key["minecraft:sprinting"]["amount"], 0.3, abs_tol=1e-6)
                    or not math.isclose(
                        by_key["relays49dashdev:forward_dash_only"]["amount"],
                        0.5, abs_tol=1e-6)):
                return None
        # Only original G2 one-shot full-power DASH plugin is permitted;
        # actual output is still a source-bound DEV candidate, NOT R proof.
        return GaitTickDev(frame.session_id,world_tick,"DASH",
                           applied_dash_power=1.0)
    return GaitTickDev(frame.session_id,world_tick,gait)
