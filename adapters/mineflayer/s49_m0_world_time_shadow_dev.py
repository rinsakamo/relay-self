"""Read-only, explicitly unit-calibrated Paper World-tick M0 basal projection.

DEV only. One normalized World-second is exactly 20 *observed Paper*
World ticks by convention, NOT 1s wall clock or an inherited M0 step.
No B0EnergyLedger access, billing or Action authority occurs in this file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


class WorldTimeM0ShadowRejected(ValueError):
    """Cannot extrapolate from a missing, foreign or aliased World tick."""


@dataclass(frozen=True, slots=True)
class M0WorldRateDev:
    basal_energy_per_world_second: float
    world_ticks_per_world_second: int = 20
    calibration: str = "DEV_EXPLICIT_ASSUMPTION_NOT_CANONICAL"

    def __post_init__(self) -> None:
        if (type(self.basal_energy_per_world_second) not in (int, float)
                or not math.isfinite(self.basal_energy_per_world_second)
                or not 0 < self.basal_energy_per_world_second <= 4
                or type(self.world_ticks_per_world_second) is not int
                or self.world_ticks_per_world_second != 20
                or self.calibration != "DEV_EXPLICIT_ASSUMPTION_NOT_CANONICAL"):
            raise WorldTimeM0ShadowRejected(
                "explicit bounded World-time calibration required"
            )


def project_s49_world_time_m0_shadow_dev(
    *,
    action_id: str,
    session_id: str,
    paper_action_bracket: dict,
    passive_post_release: dict,
    native_edges: dict,
    node_paper_moving_footprint: dict,
    original_m0_postings: list,
    original_energy_remaining: float,
    rate: M0WorldRateDev,
) -> dict:
    """Count only contiguous Paper producer-captured intervals.

    First interval: all 13 (or >=5) actual native-Action Paper callback
    World ticks. Second: precisely 5 post-owner-RELEASE Paper callback
    ticks. The intervening release tick is NOT observed as a tick callback
    and therefore MUST NOT earn any basal charge. A scope fingerprint
    guards the controls-clear readback, not clock synchronization.
    """
    if (not isinstance(action_id, str) or not action_id
            or not isinstance(session_id, str) or not session_id
            or not isinstance(rate, M0WorldRateDev)
            or any(type(x) is not dict for x in (
                paper_action_bracket, passive_post_release,
                native_edges, node_paper_moving_footprint,
            ))
            or type(original_m0_postings) is not list
            or len(original_m0_postings) != 2
            or type(original_energy_remaining) not in (int, float)
            or not math.isfinite(original_energy_remaining)
            or original_energy_remaining <= 0):
        raise WorldTimeM0ShadowRejected("source-scoped World rate inputs required")
    b, p, e, f = (
        paper_action_bracket, passive_post_release,
        native_edges, node_paper_moving_footprint,
    )
    if (any(item.get("action_id") != action_id
            or item.get("session_id") != session_id for item in (b, p, e, f))
            or b.get("classification")
               != "PAPER_LOCAL_ARM_TICK_RELEASE_BRACKET_DEV_ONLY"
            or p.get("classification")
               != "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY"
            or e.get("classification")
               != "S49_NATIVE_ACK_TO_PAPER_MARKER_DELIVERY_DEV_ONLY"
            or f.get("classification")
               != "S49_NODE_PAPER_CONSECUTIVE_TRANSLATION_FOOTPRINT_DEV_ONLY"
            or b.get("original_owner_release") is not True
            or b.get("independent_source_attested") is not False
            or e.get("marker_after_native_ack") is not True
            or e.get("native_single_reader") is not True
            or e.get("client_effect_world_tick_attested") is not False
            or e.get("paper_release_tick") != b.get("release_tick")
            or p.get("WAIT_sourcebound_admitted") is not False
            or p.get("action_authority") is not False
            or p.get("speed_modifier_present") is not False
            or p.get("P1_posted") is not False
            or p.get("M0_posted") is not False
            or f.get("two_producer_local_motion_views_consistent") is not True
            or f.get("native_Paper_tick_correspondence_attested") is not False
            or f.get("physical_WAIT_qualified") is not False
            or f.get("M0_posted") is not False
            or f.get("P1_posted") is not False):
        raise WorldTimeM0ShadowRejected("foreign or overclaimed Paper/Node interval")
    # All tick counts must be real integers (not booleans), and both
    # producer-local auditors have already verified the individual callbacks.
    fields = (
        b.get("first_tick"), b.get("last_tick"), b.get("release_tick"),
        b.get("elapsed_callbacks"), p.get("first_sample_tick"),
        p.get("last_sample_tick"), p.get("paper_callbacks"),
    )
    if any(type(n) is not int or n < 0 for n in fields):
        raise WorldTimeM0ShadowRejected("malformed or aliased World time")
    start, end, release, count, post_start, post_end, post_count = fields
    gap = release - end
    if (start < b.get("arm_tick", -1)
            or not 5 <= count <= 80
            or end - start + 1 != count
            or not 0 <= gap <= 20
            or post_count != 5
            or post_start != release + 1
            or post_end != post_start + 4
            or p.get("paper_callbacks") != post_count
            or b.get("mineflayer_paper_tick_synchronized") is not False):
        raise WorldTimeM0ShadowRejected("Paper World tick gap/replay/clock claim")
    # Check the immutable original owner state. Do not mint a new ledger or
    # retroactively change its charge for either Action.
    first, second = original_m0_postings
    if (type(first) is not dict or type(second) is not dict
            or first.get("session_id") != session_id
            or first.get("action_id") != action_id
            or second.get("session_id") != session_id
            or second.get("action_id") in (None, action_id)
            or first.get("source_scope")
               != "S49_NATIVE_ACTION_M0_STEP_DEV_NOT_WORLD_TICK"
            or second.get("source_scope")
               != "S49_NATIVE_ACTION_M0_STEP_DEV_NOT_WORLD_TICK"
            or first.get("m0_tick_before") != 0
            or first.get("m0_tick_after") != 1
            or second.get("m0_tick_before") != 1
            or second.get("m0_tick_after") != 2
            or first.get("basal_debit") != .5
            or second.get("basal_debit") != .5
            or first.get("move_debit") != .25
            or second.get("move_debit") != .25
            or type(first.get("dash_extra_debit")) not in (int, float)
            or first["dash_extra_debit"] <= 0
            or second.get("dash_extra_debit") != 0
            or not math.isclose(
                second.get("energy_after", float("nan")),
                original_energy_remaining, abs_tol=1e-10,
            )
            or not math.isclose(
                first.get("energy_after", float("nan")),
                second.get("energy_before", float("nan")), abs_tol=1e-10,
            )):
        raise WorldTimeM0ShadowRejected("original B0 owner ledger mismatch")
    # Intervals are disjoint. Any unsampled [end+1, release] remains
    # **UNBILLED**; never treat a release marker as a Paper tick sample.
    per_tick = rate.basal_energy_per_world_second / rate.world_ticks_per_world_second
    active = per_tick * count
    passive = per_tick * post_count
    unobserved = gap
    return {
        "classification": "M0_PAPER_WORLD_TICK_BASAL_SHADOW_NOT_POSTED_DEV_ONLY",
        "action_id": action_id, "session_id": session_id,
        "world_uuid": b.get("world_uuid"),
        "calibration": rate.calibration,
        "world_ticks_per_world_second": rate.world_ticks_per_world_second,
        "explicit_basal_energy_per_world_second":
            rate.basal_energy_per_world_second,
        "basal_energy_per_observed_world_tick": per_tick,
        "original_action_observed_interval": [start, end],
        "original_action_observed_ticks": count,
        "passive_post_release_observed_interval": [post_start, post_end],
        "passive_post_release_observed_ticks": post_count,
        "unsampled_between_intervals_ticks": unobserved,
        "unsampled_between_intervals_billed": False,
        "observed_distinct_world_ticks": count + post_count,
        "observed_normalized_world_seconds":
            (count + post_count) / rate.world_ticks_per_world_second,
        "active_window_basal_projection": active,
        "passive_window_basal_projection": passive,
        "combined_basal_projection_not_posted": active + passive,
        "original_action_basal_posted": first["basal_debit"] + second["basal_debit"],
        "original_energy_remaining_unchanged": original_energy_remaining,
        "legacy_action_m0_replaced": False,
        "double_charged": False,
        "world_tick_basal_posted": False,
        "source_world_clock_authoritative_across_processes": False,
        "wall_clock_seconds_attested": False,
        "WAIT_admitted": False,
        "P1_recovery_posted": False,
        "M0_posted": False,
        "qualification_go": False, "science_go": False,
    }
