"""DEV-only next-cognition-epoch SelfBody hypotheses from P1 static Paper replay.

The next Action is historical in the original S49 run: this is a retrospective,
read-only preflight COMPARISON, NOT an online gate or production state update.
Unclassified ticks prevent any actual P1 fatigue interval from being inferred.
"""
from __future__ import annotations

import math

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.p1_gait_dev import p1_motor_power_limit_dev
from relay_self.prediction import PredictionState, StateVariable
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyHypothesis,
    BodyOrigin,
    compose_self_body_view,
)


class P1BodyEpochDevRejected(ValueError):
    """Source, epoch, or hypothetical capability boundary was violated."""


CARRY = "p1-carry-without-recovery-dev"
STATIC = "p1-assume-static-wait-dev"
SCOPE = "DEV_RETROSPECTIVE_P1_HYPOTHESES_NOT_NATIVE_PRESENT"


def project_p1_static_next_body_epoch_dev(
    model: dict, fence: dict, *, profile: FatigueProfile,
    session_id: str, first_action_id: str, second_action_id: str,
    self_id: str = "RelaySelf",
) -> dict:
    """Build two explicit scenarios at the end of the static candidate.

    Scenario A carries the first DASH final F unchanged. Scenario B assumes
    every *observed static* tick was WAIT and replays the existing single P1.
    Neither is a physical uncertainty bound: unclassified gaps could contain
    other loads. M0 is modeled as plentiful ONLY to isolate the P1 motor fade.
    """
    if (
        type(model) is not dict or type(fence) is not dict
        or not isinstance(profile, FatigueProfile) or not profile.enabled
        or any(type(v) is not str or not v or v != v.strip()
               or any(ch.isspace() for ch in v)
               for v in (session_id, first_action_id, second_action_id, self_id))
        or first_action_id == second_action_id
        or model.get("classification") != (
            "P1_OBSERVED_STATIC_TICK_DEV_MODEL_REPLAY_NOT_APPLIED"
        )
        or model.get("evidence_grade") != "DEV_WORLD_OBSERVED"
        or model.get("session_id") != session_id
        or model.get("action_ids") != [first_action_id, second_action_id]
        or model.get("p1_profile_sha256") != profile.sha256
        or model.get("p1_dev_state_is_counterfactual_copy") is not True
        or model.get("actual_fatigue_at_interval_start_attested") is not False
        or model.get("actual_physical_recovery_attested") is not False
        or model.get("r_qualified_wait_ticks") != 0
        or model.get("r_qualified_p1_recovery") != 0.0
        or model.get("live_p1_owner_state_modified") is not False
        or model.get("m0_posted") is not False
        or model.get("s49_action_issuer_added") is not False
        or model.get("source_bound_tick_created") is not False
        or model.get("qualification_go") is not False
        or model.get("science_go") is not False
        or fence.get("classification") != (
            "S49_CAUSAL_OWNER_PAPER_STATIC_SUBWINDOW_DEV_ONLY"
        )
        or fence.get("session_id") != session_id
        or fence.get("action_ids") != [first_action_id, second_action_id]
        or fence.get("physical_WAIT_admitted") is not False
        or fence.get("P1_recovery_posted") is not False
        or fence.get("M0_posted") is not False
        or fence.get("qualification_go") is not False
        or fence.get("science_go") is not False
    ):
        raise P1BodyEpochDevRejected("cannot promote an unreviewed P1 model into SelfBody")
    first = model.get("first_tick")
    last = model.get("last_tick")
    n = model.get("dev_wait_model_ticks_replayed")
    second_fence = fence.get("paper_second_owner_fence_delivery_tick")
    gap = model.get("p1_start_assumption_gap_ticks")
    digest = model.get("paper_candidate_source_sha256")
    if (
        any(type(v) is not int for v in (first, last, n, second_fence, gap))
        or first <= 0 or last < first or n != last-first+1 or n < 8
        or last >= second_fence or gap < 1
        or first != fence.get("paper_causal_subwindow_first_tick")
        or last != fence.get("paper_causal_subwindow_last_tick")
        or n != fence.get("paper_causal_subwindow_contiguous_still_ticks")
        or model.get("p1_dev_model_world_tick") != last
        or type(digest) is not str or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise P1BodyEpochDevRejected("stale, out-of-fence, or unbound Paper candidate")
    values = [model.get(k) for k in (
        "p1_dev_model_before", "p1_dev_model_after", "p1_dev_model_recovered",
    )]
    if (
        any(type(x) not in (int, float) or not math.isfinite(x) for x in values)
        or not (0 <= values[1] <= values[0] <= profile.capacity)
        or not math.isclose(values[0] - values[1], values[2], abs_tol=1e-11)
        or values[2] <= 0
    ):
        raise P1BodyEpochDevRejected("invalid one-dimensional P1 model transition")

    hypotheses = []
    outputs = {}
    for hypothesis_id, fatigue, assumption in (
        (CARRY, values[0], "CARRY_FIRST_DASH_F_NO_RECOVERY"),
        (STATIC, values[1], "ASSUME_STATIC_TICKS_ARE_WAIT"),
    ):
        state = FatigueState(session_id, profile.sha256, last, fatigue)
        # Explicitly plentiful hypothetical extra M0 so this tests only P1 fade.
        power = p1_motor_power_limit_dev(
            profile, state, 1.0, available_extra_m0_energy=1.0,
        )
        if not math.isfinite(power) or not 0 <= power <= 1:
            raise P1BodyEpochDevRejected("invalid hypothetical motor ceiling")
        fatigue_bp = int(round(10_000 * fatigue / profile.capacity))
        power_bp = int(round(10_000 * power))
        origin = Provenance(
            "p1-dev-next-epoch-hypothesis-not-present",
            f"{session_id}:{first_action_id}:{last}:{digest}:{hypothesis_id}",
        )
        hypothesis = BodyHypothesis(
            hypothesis_id=hypothesis_id,
            state=PredictionState(
                state_id=f"p1-dev-epoch-{last}-{hypothesis_id}",
                variables=(
                    StateVariable("fatigue_model_basis_points", fatigue_bp),
                    StateVariable("forward_dash_power_ceiling_bp", power_bp),
                    StateVariable("scenario", assumption),
                    StateVariable("source_scope", SCOPE),
                    StateVariable("unclassified_prior_gap_ticks", gap),
                    StateVariable("paper_static_candidate_ticks", n),
                ),
                provenance=origin,
                source_refs=(
                    f"paper-source-sha256:{digest}",
                    f"first-closed-action:{session_id}:{first_action_id}",
                    f"next-original-action:{session_id}:{second_action_id}",
                    f"candidate-ticks:{first}:{last}",
                ),
                source_provenance=(origin,),
            ),
        )
        hypotheses.append(hypothesis)
        outputs[hypothesis_id] = (fatigue_bp, power_bp)
    body = compose_self_body_view(
        session_id=session_id,
        epoch_id=f"p1-dev-retrospective-before-second-{last}",
        self_id=self_id,
        hypotheses=tuple(hypotheses),
    )
    if (
        body.observation is not None
        or body.interoceptions
        or body.observed("p1_fatigue").origin is not BodyOrigin.UNKNOWN
        or body.sensed("p1_fatigue_sensor").origin is not BodyOrigin.UNKNOWN
        or any(
            body.hypothetical(case, "forward_dash_power_ceiling_bp").origin
            is not BodyOrigin.HYPOTHESIS
            for case in (CARRY, STATIC)
        )
        or outputs[STATIC][1] < outputs[CARRY][1]
    ):
        raise P1BodyEpochDevRejected("physical SelfBody source leaked or inverted P1")
    return {
        "classification": "P1_RETROSPECTIVE_NEXT_SELFBODY_HYPOTHESES_DEV_ONLY",
        "source_scope": SCOPE,
        "session_id": session_id,
        "action_ids": [first_action_id, second_action_id],
        "self_id": self_id,
        "epoch_id": body.epoch_id,
        "epoch_hypotheses_count": len(body.hypotheses),
        "body_origin": "hypothesis",
        "paper_candidate_source_sha256": digest,
        "p1_profile_sha256": profile.sha256,
        "model_last_candidate_world_tick": last,
        "next_original_action_is_historical": True,
        "candidate_before_second_owner_delivery": True,
        "unclassified_gap_ticks_before_candidate": gap,
        "no_recovery_carry_fatigue_bp": outputs[CARRY][0],
        "wait_assumed_fatigue_bp": outputs[STATIC][0],
        "no_recovery_forward_dash_ceiling_bp": outputs[CARRY][1],
        "wait_assumed_forward_dash_ceiling_bp": outputs[STATIC][1],
        "model_ceiling_gain_bp": outputs[STATIC][1] - outputs[CARRY][1],
        "only_p1_power_fade_compared": True,
        "hypothetical_extra_m0_energy": 1.0,
        "model_not_actual_fatigue_bounds": True,
        "unknown_gap_and_non_wait_activity_unexcluded": True,
        "native_present_or_postcandidate_p1_sensor": None,
        "physically_admitted_next_action_power": None,
        "original_s49_action_policy_modified": False,
        "new_action_issuers": 0,
        "additional_native_reads": 0,
        "live_p1_state_modified": False,
        "m0_posted": False,
        "qualified_wait_ticks": 0,
        "qualification_go": False,
        "science_go": False,
    }
