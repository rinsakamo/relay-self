"""Original second S49 native readback versus two *hypothetical* next-epoch P1 limits.

All native frames were already received by the ORIGINAL S49 owner. Review only:
no new native reader/Action, no inference that second vanilla sprint measures
Paper DASH power or the internal P1 fatigue, no L0 physical power admission.
"""
from __future__ import annotations

import math

from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)


class P1NextNativeL0Rejected(ValueError):
    """Native S16, hypothetical P1, or owner epoch sources do not align."""


def _native_action(action: dict, sid: str, expected_id: str) -> dict:
    if (
        type(action) is not dict
        or action.get("action") != expected_id
        or action.get("terminal") != "outcome"
        or action.get("source") != sid
        or type(action.get("movement_m")) not in (float, int)
        or not math.isfinite(action["movement_m"])
        or action["movement_m"] <= 0.05
        or type(action.get("event_seq")) is not int
        or type(action.get("probe_seq")) is not int
    ):
        raise P1NextNativeL0Rejected("original S49 native action not closed")
    evidence = action.get("execution_evidence")
    try:
        verify_native_action_evidence(
            evidence, action_id=expected_id, session_id=sid,
            movement_m=action["movement_m"],
            allow_dev_forward=True, allow_dev_sprint=True,
        )
    except (NativeEvidenceRejected, KeyError, TypeError, ValueError) as exc:
        raise P1NextNativeL0Rejected("original S16 decoded native proof invalid") from exc
    if evidence["action_ref"] != "MOVE_FORWARD_SPRINT_DEV":
        raise P1NextNativeL0Rejected("original forward sprint evidence absent")
    return evidence


def review_next_native_p1_l0_comparison_dev(
    original: dict, body: dict, model: dict, fence: dict, timeline: dict,
) -> dict:
    """Retrospective L0 feasibility *comparison*, never an Action power gate.

    Original L0 MOVE_AWAY, native before/after XZ displacement and S15 ACK
    are independent evidence that a SECOND MOVEMENT occurred. They do not
    discriminate between model P1 fade scenarios for an unboosted Action.
    """
    if any(type(x) is not dict for x in (original, body, model, fence, timeline)):
        raise P1NextNativeL0Rejected("typed immutable-source dictionaries required")
    sid = original.get("session_id")
    actions = original.get("actual_native_actions")
    if (
        original.get("status") != "PASS"
        or type(sid) is not str or not sid
        or type(actions) is not list or len(actions) != 2
        or original.get("dev_sprint_motor") is not True
        or original.get("dev_m0_action_move_step") is not True
        or original.get("dev_m0_dash_unboosted_actions") != [actions[1].get("action")]
        or original.get("real_model_calls") != 0
        or body.get("classification")
           != "P1_RETROSPECTIVE_NEXT_SELFBODY_HYPOTHESES_DEV_ONLY"
        or body.get("source_scope")
           != "DEV_RETROSPECTIVE_P1_HYPOTHESES_NOT_NATIVE_PRESENT"
        or body.get("body_origin") != "hypothesis"
        or body.get("epoch_hypotheses_count") != 2
        or body.get("model_not_actual_fatigue_bounds") is not True
        or body.get("next_original_action_is_historical") is not True
        or body.get("original_s49_action_policy_modified") is not False
        or body.get("new_action_issuers") != 0
        or body.get("additional_native_reads") != 0
        or body.get("live_p1_state_modified") is not False
        or body.get("m0_posted") is not False
        or body.get("qualified_wait_ticks") != 0
        or body.get("qualification_go") is not False
        or body.get("science_go") is not False
        or model.get("classification")
           != "P1_OBSERVED_STATIC_TICK_DEV_MODEL_REPLAY_NOT_APPLIED"
        or model.get("actual_physical_recovery_attested") is not False
        or model.get("live_p1_owner_state_modified") is not False
        or model.get("source_bound_tick_created") is not False
        or model.get("r_qualified_wait_ticks") != 0
        or fence.get("classification")
           != "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY"
        or fence.get("physical_WAIT_admitted") is not False
        or timeline.get("classification")
           != "M0_TWO_NATIVE_ACTIONS_CONTIGUOUS_WORLD_TIMELINE_SHADOW_DEV_ONLY"
        or timeline.get("bridge_motion_classification")
           != "UNKNOWN_NOT_CERTIFIED_WAIT_OR_MOVE"
        or timeline.get("tick_gaps_or_replay") is not False
        or timeline.get("world_tick_m0_debits_posted") is not False
    ):
        raise P1NextNativeL0Rejected("P1 or S49 owner source accidentally promoted")
    first, second = actions
    ids = [a.get("action") for a in actions]
    digest = body.get("paper_candidate_source_sha256")
    if (
        any(type(i) is not str or not i for i in ids) or ids[0] == ids[1]
        or any(x.get("session_id") != sid
               or x.get("action_ids") != ids
               for x in (body, model, fence, timeline))
        or body.get("p1_profile_sha256") != model.get("p1_profile_sha256")
        or digest != model.get("paper_candidate_source_sha256")
        or type(digest) is not str or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
        or body.get("model_last_candidate_world_tick")
           != fence.get("paper_causal_subwindow_last_tick")
        or body.get("model_last_candidate_world_tick")
           != model.get("last_tick")
        or type(model.get("p1_start_assumption_gap_ticks")) is not int
        or body.get("unclassified_gap_ticks_before_candidate")
           != model.get("p1_start_assumption_gap_ticks")
        or body.get("unclassified_gap_ticks_before_candidate") < 1
    ):
        raise P1NextNativeL0Rejected("foreign P1/Paper window or original owner")
    first_evidence = _native_action(first, sid, ids[0])
    second_evidence = _native_action(second, sid, ids[1])
    if (
        first_evidence["after_observation"]["seq"]
        >= second_evidence["before_observation"]["seq"]
        or second["probe_seq"] >= second_evidence["before_observation"]["seq"]
        or first["event_seq"] >= second["event_seq"]
        or first["probe_seq"] >= second["probe_seq"]
    ):
        raise P1NextNativeL0Rejected("native second Action did not follow original first")
    decisions = original.get("decisions")
    if (
        type(decisions) is not list or len(decisions) != 3
        or sum(d.get("issued") is True for d in decisions) != 2
        or decisions[-1].get("selected") != "MOVE_AWAY"
        or decisions[-1].get("issued") is not True
        or decisions[-1].get("event_seq") != second["event_seq"]
        or decisions[-1].get("probe_seq") != second["probe_seq"]
        or type(decisions[-1].get("distance_m")) not in (int, float)
        or not math.isfinite(decisions[-1]["distance_m"])
        or not 0 < decisions[-1]["distance_m"] < 4
    ):
        raise P1NextNativeL0Rejected("second original L0 choice not source-matched")
    last_tick = fence.get("paper_causal_subwindow_last_tick")
    second_delivery = fence.get("paper_second_owner_fence_delivery_tick")
    if (
        type(last_tick) is not int or type(second_delivery) is not int
        or not last_tick < second_delivery
        or not second_delivery < timeline.get("second_ack_delivery_applied_tick", 0)
        or timeline.get("second_ack_delivery_window_ticks", 0) < 3
        or timeline.get("second_window_not_exact_native_effect_timing") is not True
    ):
        raise P1NextNativeL0Rejected("Paper causal ordering or timing ambiguity lost")
    carry = body.get("no_recovery_forward_dash_ceiling_bp")
    assumed = body.get("wait_assumed_forward_dash_ceiling_bp")
    if (
        any(type(x) is not int for x in (carry, assumed))
        or not 0 <= carry <= assumed <= 10000
        or body.get("model_ceiling_gain_bp") != assumed - carry
        or body.get("model_ceiling_gain_bp") <= 0
        or body.get("physically_admitted_next_action_power") is not None
        or body.get("native_present_or_postcandidate_p1_sensor") is not None
    ):
        raise P1NextNativeL0Rejected("model power promoted to physical capacity")
    pre = second_evidence["before_observation"]
    after = second_evidence["after_observation"]
    return {
        "classification": "P1_NEXT_NATIVE_L0_SHADOW_CAPACITY_SOURCE_JOIN_DEV_ONLY",
        "session_id": sid,
        "action_ids": ids,
        "paper_candidate_source_sha256": digest,
        "p1_profile_sha256": body["p1_profile_sha256"],
        "body_epoch_id": body["epoch_id"],
        "second_original_l0_choice": "MOVE_AWAY",
        "second_original_l0_event_seq": second["event_seq"],
        "second_original_l0_probe_seq": second["probe_seq"],
        "second_native_before_seq": pre["seq"],
        "second_native_after_seq": after["seq"],
        "second_native_before_ref": f"mineflayer:{sid}:{pre['seq']}",
        "second_native_after_ref": f"mineflayer:{sid}:{after['seq']}",
        "second_native_observed_displacement_m": second["movement_m"],
        "second_original_native_outcome": True,
        "second_original_paper_dash_boost": False,
        "native_movement_is_not_p1_fatigue_measurement": True,
        "native_movement_is_not_dash_power_measurement": True,
        "native_to_paper_exact_world_tick_joined": False,
        "first_dash_to_static_gap_unclassified": True,
        "hypothetical_no_recovery_dash_ceiling_bp": carry,
        "hypothetical_static_wait_dash_ceiling_bp": assumed,
        "hypothetical_l0_dash_power_options_disagree": carry != assumed,
        "p1_fatigue_independently_observed": False,
        "physical_l0_dash_power_admission": None,
        "l0_shadow_next_dash_constraint": (
            "UNDETERMINED_SOURCE_NEEDED_BEFORE_ACTUATION"
        ),
        "native_source_can_constrain_geometry_only": True,
        "original_s42_l0_decision_reexecuted": False,
        "original_s49_l0_selection_modified": False,
        "original_native_reader_added": False,
        "original_action_issuer_added": False,
        "live_p1_state_modified": False,
        "m0_posted": False,
        "r_qualified_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }
