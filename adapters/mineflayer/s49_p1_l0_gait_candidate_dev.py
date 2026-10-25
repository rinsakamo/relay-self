"""DEV-only cognition candidate from one fresh native event/probe and P1 Body model.

This is an optional evaluated movement-envelope candidate, never S42/L0
selection authority, Action permission, real fatigue telemetry or S10 update.
"""
from __future__ import annotations

import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_l0_fresh_pair_dev import review_postwait_fresh_l0_input_dev
from adapters.mineflayer.s49_p1_l0_sensitivity_dev import BASELINE, CHALLENGE
from adapters.mineflayer.s49_p1_self_body_dev import (
    compose_s49_p1_dev_self_body,
    compose_s49_p1_postwait_native_dev,
)
from experiments.fatigue_p1 import FatigueState, capability
from relay_self.learning import LearningPreferenceState


def evaluate_fatigue_aware_fresh_candidate_dev(
    original_s49: dict,
    paper_window: str,
    prior_native_probe: MineflayerObservation,
    fresh_event: MineflayerObservation,
    fresh_probe: MineflayerObservation,
    *,
    expected_player_uuid: str,
    retained: LearningPreferenceState,
) -> dict[str, object]:
    """Two model-only P1 profiles against exactly the same fresh World inputs.

    Exact native matching is checked independently through original
    NormalWorldL0._check in each case. No L0.decide or issuance occurs.
    The P1 model constrains a *candidate gait*, never the S42 intent.
    """
    if (not isinstance(original_s49, dict)
            or not isinstance(paper_window, str)
            or not isinstance(prior_native_probe, MineflayerObservation)
            or not isinstance(fresh_event, MineflayerObservation)
            or not isinstance(fresh_probe, MineflayerObservation)
            or not isinstance(retained, LearningPreferenceState)):
        raise BoundaryRejected("typed original S49/Paper/native sources required")
    actions = original_s49.get("actual_native_actions")
    if not isinstance(actions, list) or len(actions) != 2:
        raise BoundaryRejected("exact original S49 action pair required")
    snapshots: list[tuple[str, dict, dict, float]] = []
    for name, profile in (("BASELINE", BASELINE), ("STRESS", CHALLENGE)):
        handoff, reviewed = compose_s49_p1_dev_self_body(
            original_s49, paper_window,
            expected_player_uuid=expected_player_uuid,
            profile=profile,
        )
        body, _ = compose_s49_p1_postwait_native_dev(
            handoff, reviewed, actions[-1], prior_native_probe,
            expected_request_id=(
                f"s49-postwait:{handoff.session_id}:{handoff.action_id}"
            ),
        )
        fresh = review_postwait_fresh_l0_input_dev(
            fresh_event, fresh_probe,
            prior_postwait_probe=prior_native_probe,
            body=body, handoff=handoff, p1_reviewed=reviewed,
            profile=profile, retained=retained,
        )
        last_tick = reviewed["dev_wait_ticks"][-1]["tick"]
        fatigue = reviewed["dev_fatigue_after"]
        limit = capability(
            profile, FatigueState(
                handoff.session_id, profile.sha256, last_tick, fatigue,
            ),
        ).max_move_blocks_per_world_tick
        if (not math.isfinite(limit) or limit <= 0
                or fresh["fresh_s42_selection"] not in ("MOVE_AWAY", "WAIT")
                or fresh["new_action_grant_issued"] is not False
                or fresh["new_action_issued"] is not False
                or fresh["original_l0_decide_called"] is not False):
            raise BoundaryRejected("unqualified P1 gait candidate")
        snapshots.append((name, fresh, reviewed, limit))

    _, base, base_review, base_limit = snapshots[0]
    _, stress, stress_review, stress_limit = snapshots[1]
    if (base["session_id"] != stress["session_id"]
            or base["action_id"] != stress["action_id"]
            or base["world"] != stress["world"]
            or base["observer_run_id"] != stress["observer_run_id"]
            or base["paper_window_sha256"] != stress["paper_window_sha256"]
            or base["fresh_event_seq"] != stress["fresh_event_seq"]
            or base["fresh_probe_seq"] != stress["fresh_probe_seq"]
            or base["fresh_probe_request_id"] != stress["fresh_probe_request_id"]
            or base["fresh_zombie_entity_id"] != stress["fresh_zombie_entity_id"]
            or base["fresh_s42_selection"] != stress["fresh_s42_selection"]
            or base["fresh_s42_distance_m"] != stress["fresh_s42_distance_m"]
            or base["fresh_native_body_source_ref"]
            != stress["fresh_native_body_source_ref"]
            or base["fresh_body_p1_model_origin"] != "hypothesis"
            or stress["fresh_body_p1_model_origin"] != "hypothesis"
            or base_review["dev_move"]["movement_m"]
            != stress_review["dev_move"]["movement_m"]
            or base_review["dev_wait_count"] != stress_review["dev_wait_count"]
            or base_limit <= stress_limit
            or base_review["dev_fatigue_after"] >= stress_review["dev_fatigue_after"]
            or base["qualification_go"] is not False
            or stress["qualification_go"] is not False):
        raise BoundaryRejected("same fresh World and distinct P1 scenarios required")

    demand = BASELINE.nominal_move_limit_blocks
    if demand != CHALLENGE.nominal_move_limit_blocks:
        raise BoundaryRejected("candidate comparison must use identical nominal gait")

    def choice(limit: float) -> str:
        if base["fresh_s42_selection"] == "WAIT":
            return "WAIT_NO_ACTION_CANDIDATE"
        if limit + 1e-9 < demand:
            return "MOVE_AWAY_LIMIT_TO_MODEL_CAPACITY_CANDIDATE"
        return "MOVE_AWAY_NOMINAL_MODEL_CANDIDATE"

    baseline_candidate = choice(base_limit)
    stress_candidate = choice(stress_limit)
    if base["fresh_s42_selection"] == "MOVE_AWAY" and (
        baseline_candidate != "MOVE_AWAY_NOMINAL_MODEL_CANDIDATE"
        or stress_candidate != "MOVE_AWAY_LIMIT_TO_MODEL_CAPACITY_CANDIDATE"
    ):
        raise BoundaryRejected("P1 candidate comparison did not change gait envelope")

    return {
        "status": "DEV_FRESH_WORLD_P1_CAPABILITY_CONDITIONED_L0_CANDIDATE",
        "source_scope": "DEV_ONLY_S42_INTENT_PLUS_UNATTESTED_P1_MODEL",
        "session_id": base["session_id"],
        "action_id": base["action_id"],
        "world": base["world"],
        "observer_run_id": base["observer_run_id"],
        "paper_window_sha256": base["paper_window_sha256"],
        "fresh_event_seq": base["fresh_event_seq"],
        "fresh_probe_seq": base["fresh_probe_seq"],
        "fresh_probe_request_id": base["fresh_probe_request_id"],
        "fresh_body_epoch_id": base["fresh_body_epoch_id"],
        "fresh_native_source_ref": base["fresh_native_body_source_ref"],
        "fresh_zombie_entity_id": base["fresh_zombie_entity_id"],
        "fresh_s42_selection_unchanged": base["fresh_s42_selection"],
        "nominal_one_tick_demand_blocks": demand,
        "baseline_after_wait_model_fatigue": base_review["dev_fatigue_after"],
        "stress_after_wait_model_fatigue": stress_review["dev_fatigue_after"],
        "baseline_one_tick_capacity_blocks": base_limit,
        "stress_one_tick_capacity_blocks": stress_limit,
        "baseline_cognition_candidate": baseline_candidate,
        "stress_cognition_candidate": stress_candidate,
        "gait_candidate_changed_by_p1_scenario": (
            baseline_candidate != stress_candidate
        ),
        "s42_intent_modified": False,
        "actual_l0_decide_called": False,
        "new_action_grant_issued": False,
        "new_action_issued": False,
        "additional_native_receivers": 0,
        "additional_native_probes": 0,
        "p1_physically_attested": False,
        "production_p1_mutated": False,
        "qualification_go": False,
        "science_go": False,
    }
