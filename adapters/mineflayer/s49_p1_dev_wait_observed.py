"""DEV-only P1 WAIT-model replay from Paper source ticks inside original S49 fence.

The paper observer certifies static displacement locally, not exclusive control
of the entire physical World. This adds no Action issuer, P1 production state,
R SourceBoundTick, or M0 ledger entry. The candidate is admitted for *DEV model
replay*, never for physically qualified WAIT or real fatigue attribution.
"""
from __future__ import annotations

import hashlib
import math

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.p1_gait_dev import GaitRatesDev, GaitTickDev, advance_gait_dev


class P1ObservedWaitDevRejected(ValueError):
    """A DEV candidate lost its source, tick continuity, or model boundary."""


def _fields(line: str, mark: str) -> dict[str, str]:
    fields = {}
    for token in line.split(mark, 1)[1].split():
        if token.count("=") != 1:
            raise P1ObservedWaitDevRejected("malformed Paper row")
        key, value = token.split("=", 1)
        if not key or not value or key in fields:
            raise P1ObservedWaitDevRejected("duplicate/empty Paper field")
        fields[key] = value
    return fields


def _valid_number(raw: str | None) -> float:
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise P1ObservedWaitDevRejected("bad Paper position") from exc
    if not math.isfinite(number):
        raise P1ObservedWaitDevRejected("nonfinite Paper position")
    return number


def replay_p1_observed_static_wait_dev(
    raw: str, *, fence: dict, shadow: dict, stillness: dict, timeline: dict,
    profile: FatigueProfile, first_action_id: str, second_action_id: str,
    session_id: str, rates: GaitRatesDev = GaitRatesDev(),
) -> dict:
    """Revalidate *each* static Paper tick then project a DEV-only P1 state.

    The starting F is NOT observed on the candidate's first tick: it is the
    first DASH end carried without mutation across an unclassified gap. The
    result is an observation-grounded MODEL replay, not measured P1 recovery.
    A prior caller must independently run original S49 / Node / Paper reviewers.
    """
    if (
        type(raw) is not str or not 0 < len(raw) <= 10_000_000
        or any(type(v) is not dict for v in (fence, shadow, stillness, timeline))
        or type(session_id) is not str or not session_id
        or type(first_action_id) is not str or not first_action_id
        or type(second_action_id) is not str or not second_action_id
        or first_action_id == second_action_id
        or not isinstance(profile, FatigueProfile) or not profile.enabled
        or not isinstance(rates, GaitRatesDev)
    ):
        raise P1ObservedWaitDevRejected("untyped or unbounded DEV replay inputs")
    if (
        fence.get("classification") != "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY"
        or fence.get("session_id") != session_id
        or fence.get("action_ids") != [first_action_id, second_action_id]
        or fence.get("physical_WAIT_admitted") is not False
        or fence.get("P1_recovery_posted") is not False
        or fence.get("M0_posted") is not False
        or fence.get("global_world_quiescence_attested") is not False
        or fence.get("global_action_absence_attested") is not False
        or fence.get("original_issuer_no_second_issue_during_causal_subwindow")
           is not True
        or fence.get("node_local_controls_off_sampled_between_first_clear_second_set")
           is not True
        or fence.get("paper_body_static_measured_inside_causal_subwindow")
           is not True
        or fence.get("qualification_go") is not False
        or fence.get("science_go") is not False
        or shadow.get("classification") != (
            "P1_CAUSALLY_FENCED_STATIC_WAIT_COUNTERFACTUAL_UNAPPLIED_DEV_ONLY"
        )
        or shadow.get("session_id") != session_id
        or shadow.get("action_ids") != [first_action_id, second_action_id]
        or shadow.get("single_existing_p1_profile_sha256") != profile.sha256
        or shadow.get("starting_fatigue_not_observed_at_candidate") is not True
        or shadow.get("starting_fatigue_assumption")
           != "HOLD_FIRST_DASH_FINAL_OVER_UNKNOWN_GAP"
        or shadow.get("counterfactual_activity") != "WAIT_FOR_ALL_CANDIDATE_TICKS_ONLY"
        or shadow.get("physical_wait_admitted") is not False
        or shadow.get("actual_p1_state_updated") is not False
        or shadow.get("p1_recovery_applied") != 0.0
        or shadow.get("m0_posted") is not False
        or shadow.get("source_bound_tick_created") is not False
        or shadow.get("qualification_go") is not False
        or shadow.get("science_go") is not False
        or stillness.get("classification") != "S49_INTER_ACTION_STILLNESS_CANDIDATE_DEV_ONLY"
        or stillness.get("session_id") != session_id
        or stillness.get("action_ids") != [first_action_id, second_action_id]
        or stillness.get("node_all_controls_off_until_second_set") is not True
        or stillness.get("physical_WAIT_admitted") is not False
        or stillness.get("P1_recovery_posted") is not False
        or stillness.get("M0_posted") is not False
        or timeline.get("classification")
           != "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY"
        or timeline.get("action_ids") != [first_action_id, second_action_id]
        or timeline.get("session_id") != session_id
        or timeline.get("tick_gaps_or_replay") is not False
        or timeline.get("double_counted_world_ticks") is not False
        or timeline.get("world_tick_m0_debits_posted") is not False
        or timeline.get("WAIT_sourcebound_admitted") is not False
        or timeline.get("P1_recovery_posted") is not False
    ):
        raise P1ObservedWaitDevRejected("original S49/Paper/P1 DEV receipts inconsistent")
    low = fence.get("paper_causal_subwindow_first_tick")
    high = fence.get("paper_causal_subwindow_last_tick")
    n = fence.get("paper_causal_subwindow_contiguous_still_ticks")
    first = timeline.get("first_sample_tick")
    last = timeline.get("last_sample_tick")
    total = timeline.get("observed_contiguous_paper_ticks")
    if (
        any(type(v) is not int for v in (low, high, n, first, last, total))
        or not (0 < first < low <= high < last)
        or not (8 <= n <= 1200) or n != high-low+1
        or total != last-first+1 or not 16 <= total <= 1200
        or shadow.get("paper_stillness_tick_interval") != [low, high]
        or shadow.get("candidate_ticks") != n
        or shadow.get("unclassified_world_ticks_after_first_dash_before_candidate", 0) < 1
        or not isinstance(shadow.get("counterfactual_start_fatigue"), (float, int))
        or type(shadow.get("counterfactual_start_fatigue")) is bool
    ):
        raise P1ObservedWaitDevRejected("invalid World interval or missing unknown gap")
    initial = float(shadow["counterfactual_start_fatigue"])
    if not math.isfinite(initial) or not 0 <= initial <= profile.capacity:
        raise P1ObservedWaitDevRejected("unphysical initial P1 model fatigue")
    world = timeline.get("world_uuid")
    player = timeline.get("player_uuid")
    if (world != fence.get("world_uuid") or player != fence.get("player_uuid")
            or not isinstance(world, str) or not world
            or not isinstance(player, str) or not player):
        raise P1ObservedWaitDevRejected("Paper actor/world did not match causal fence")
    mark = "S49_DASH_DEV_TRAIL_TICK "
    rows = [line for line in raw.splitlines() if mark in line]
    if len(rows) != total:
        raise P1ObservedWaitDevRejected("missing/duplicated Paper World tick rows")
    witness = []
    state = FatigueState(session_id, profile.sha256, low - 1, initial)
    prior_pos = None
    maximum = 0.0
    for index, line in enumerate(rows, 1):
        row = _fields(line, mark)
        tick = first + index - 1
        try:
            observed_tick = int(row["tick"])
            observed_index = int(row["index"])
        except (KeyError, ValueError) as exc:
            raise P1ObservedWaitDevRejected("bad Paper World tick/index") from exc
        if (
            observed_tick != tick or observed_index != index
            or row.get("action_id") != first_action_id
            or row.get("session_id") != session_id
            or row.get("world") != world
            or row.get("player_uuid") != player
            or any(row.get(field) != "false" for field in (
                "motor_write", "M0_POSTED", "P1_APPLIED", "WAIT_ATTESTED"
            ))
        ):
            raise P1ObservedWaitDevRejected("Paper source gap, replay, or foreign actor")
        pos = (_valid_number(row.get("x")), _valid_number(row.get("z")))
        if low <= tick <= high:
            if (
                prior_pos is None or row.get("first_dash_modifier_present") != "false"
                or row.get("second_applied_marker_seen") != "false"
                or row.get("second_cleared_marker_seen") != "false"
            ):
                raise P1ObservedWaitDevRejected("native activity in DEV stillness candidate")
            delta = math.hypot(pos[0]-prior_pos[0], pos[1]-prior_pos[1])
            if not math.isfinite(delta) or delta > 0.002000000001:
                raise P1ObservedWaitDevRejected("Paper movement exceeds static threshold")
            maximum = max(maximum, delta)
            witness.append(line)
            transition = advance_gait_dev(
                profile, state, GaitTickDev(session_id, tick, "WAIT"), rates=rates,
            )
            if (
                transition.added_m0_charge != 0
                or transition.m0_ledger_posted
                or transition.source_authenticated
                or transition.new_action_issuer
            ):
                raise P1ObservedWaitDevRejected("DEV model minted authority or M0")
            state = transition.after
        prior_pos = pos
    recovered = initial - state.fatigue
    if (
        len(witness) != n
        or not math.isfinite(recovered) or recovered < 0
        or not isinstance(shadow.get("counterfactual_end_fatigue"), (float, int))
        or type(shadow.get("counterfactual_end_fatigue")) is bool
        or not isinstance(shadow.get("counterfactual_p1_recovered_if_all_wait"), (float, int))
        or type(shadow.get("counterfactual_p1_recovered_if_all_wait")) is bool
        or not math.isclose(state.fatigue, shadow["counterfactual_end_fatigue"],
                            rel_tol=0, abs_tol=1e-11)
        or not math.isclose(recovered, shadow["counterfactual_p1_recovered_if_all_wait"],
                            rel_tol=0, abs_tol=1e-11)
    ):
        raise P1ObservedWaitDevRejected("single-P1 WAIT replay does not match shadow")
    digest = hashlib.sha256(("\n".join(witness)+"\n").encode("utf-8")).hexdigest()
    return {
        "classification": "P1_OBSERVED_STATIC_TICK_DEV_MODEL_REPLAY_NOT_APPLIED",
        "evidence_grade": "DEV_WORLD_OBSERVED",
        "model_activity_assumption": "CONSERVATIVE_PAPER_STATIC_WITH_NODE_SAMPLED_OFF",
        "session_id": session_id,
        "action_ids": [first_action_id, second_action_id],
        "world_uuid": world,
        "player_uuid": player,
        "first_tick": low,
        "last_tick": high,
        "dev_wait_model_ticks_replayed": n,
        "paper_max_horizontal_delta_m": maximum,
        "paper_candidate_source_sha256": digest,
        "node_physics_samples_off": stillness["node_physics_samples"],
        "p1_profile_sha256": profile.sha256,
        "p1_start_assumption_gap_ticks":
            shadow["unclassified_world_ticks_after_first_dash_before_candidate"],
        "p1_dev_model_before": initial,
        "p1_dev_model_after": state.fatigue,
        "p1_dev_model_recovered": recovered,
        "p1_dev_model_world_tick": high,
        "p1_dev_state_is_counterfactual_copy": True,
        "actual_fatigue_at_interval_start_attested": False,
        "actual_physical_recovery_attested": False,
        "r_qualified_wait_ticks": 0,
        "r_qualified_p1_recovery": 0.0,
        "live_p1_owner_state_modified": False,
        "s49_action_issuer_added": False,
        "m0_posted": False,
        "source_bound_tick_created": False,
        "qualification_go": False,
        "science_go": False,
    }
