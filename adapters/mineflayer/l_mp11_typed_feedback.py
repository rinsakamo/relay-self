"""Typed numeric roles and prior-hypothesis feedback for L2, not learning.

A citation binds a specific measurement *role* to original past observations.
It cannot prove free-text causal reasoning or grant Action/Model authority.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.l_mp11_live_previous_action import LivePriorObservation

ROLES = frozenset({
    "WAIT8_TOTAL_M",
    "PAPER_NEXT_TICK_PREDICTION_M",
    "PAPER_NEXT_TICK_ABS_ERROR_M",
    "PAPER_CHEAP_NEXT_TICK_MAE_M",
    "PRIOR_L2_NEXT_WAIT8_PREDICTION_M",
    "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M",
})
RELATIONS = frozenset({
    "FIRST_HYPOTHESIS", "KEEP_PRIOR", "REVISE_PRIOR", "REJECT_PRIOR",
    "ABSTAIN_ON_PRIOR",
})


class NumericRoleRejected(ValueError):
    """Metric role, index, prior target, source or numeric value is mismatched."""


@dataclass(frozen=True, slots=True)
class NumericCitation:
    metric_role: str
    trial_ordinal: int
    pair_index: int
    value_m: float


def previous_feedback(previous: object, new_trial: LivePriorObservation) -> dict:
    """Previous L2 prediction TARGETS the following trial's WAIT8 TOTAL."""
    if (
        not isinstance(new_trial, LivePriorObservation)
        or new_trial.ordinal != 2
        or previous is None
        or getattr(previous, "source_prior_count", None) != 1
        or getattr(previous, "source_last_action_id", None) == new_trial.action_id
        or not isinstance(getattr(previous, "proposal_sha256", None), str)
        or len(previous.proposal_sha256) != 64
    ):
        raise NumericRoleRejected("previous L2 model not bound to original next trial")
    prediction = getattr(previous, "predicted_wait_total_m", None)
    if prediction is not None and (
        type(prediction) not in (float, int)
        or not math.isfinite(prediction) or prediction < 0
    ):
        raise NumericRoleRejected("nonfinite prior L2 forecast")
    return {
        "status": (
            "PREVIOUS_FORECAST_SCORED" if prediction is not None
            else "PREVIOUS_HYPOTHESIS_NO_NUMERIC_FORECAST"
        ),
        "previous_proposal_sha256": previous.proposal_sha256,
        "previous_model_family": previous.model_family,
        "previous_explanation": previous.explanation,
        "previous_falsification_test": previous.falsification_test,
        "previous_source_action_id": previous.source_last_action_id,
        "previous_source_trial_ordinal": previous.source_prior_count,
        "previous_source_prefix_sha256": previous.source_last_prefix_sha256,
        "target_action_id": new_trial.action_id,
        "target_prefix_sha256": new_trial.paper_prefix_sha256,
        "source_world_uuid": new_trial.world_uuid,
        "source_session_id": new_trial.session_id,
        "previous_reconsideration": previous.reconsideration,
        "previous_next_test_unapproved": previous.next_test,
        "target_kind": "NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M",
        "target_trial_ordinal": 2,
        "previous_prediction_m": prediction,
        "target_observed_m": new_trial.paper_wait_total_m,
        "prior_prediction_abs_error_m": (
            abs(prediction - new_trial.paper_wait_total_m)
            if prediction is not None else None
        ),
        "comparator_scope": (
            "PAPER_CHEAP_NEXT_TICK_MAE_M_IS_DIFFERENT_TARGET; "
            "NOT_COMPARABLE_TO_WAIT8_TOTAL_ERROR"
        ),
        "model_revised_and_admitted": False,
        "source_is_original_Paper_but_postrun_unqualified": True,
    }


def numeric_value(
    history: tuple[LivePriorObservation, ...],
    metric: str, ordinal: int, pair: int, *, feedback: dict | None,
) -> float:
    """Resolve a cited numeric role against *only visible prior* observations."""
    if (
        metric not in ROLES or type(ordinal) is not int
        or not 1 <= ordinal <= len(history) or type(pair) is not int
    ):
        raise NumericRoleRejected("unavailable ordinal/metric role")
    t = history[ordinal-1]
    if metric == "WAIT8_TOTAL_M" and pair == 0:
        return t.paper_wait_total_m
    if metric == "PAPER_CHEAP_NEXT_TICK_MAE_M" and pair == 0:
        return t.paper_cheap_zero_next_mae_m
    if metric in {"PAPER_NEXT_TICK_PREDICTION_M", "PAPER_NEXT_TICK_ABS_ERROR_M"}:
        if 1 <= pair <= 7:
            series = (t.paper_predicted_next_m if metric.endswith("PREDICTION_M")
                      else t.paper_next_abs_error_m)
            return series[pair-1]
    if (
        metric in {
            "PRIOR_L2_NEXT_WAIT8_PREDICTION_M",
            "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M",
        }
        and feedback is not None and ordinal == 2 and pair == 0
    ):
        value = (feedback["previous_prediction_m"]
                 if metric.endswith("PREDICTION_M")
                 else feedback["prior_prediction_abs_error_m"])
        if value is not None:
            return value
    raise NumericRoleRejected("pair index or target family cannot be compared")


def validate_numeric_citations(
    history: tuple[LivePriorObservation, ...], refs: object,
    *, feedback: dict | None,
) -> tuple[NumericCitation, ...]:
    if type(refs) is not list or not 1 <= len(refs) <= 4:
        raise NumericRoleRejected("one to four role-bound citations required")
    found = []
    keys = set()
    for item in refs:
        if type(item) is not dict or set(item) != {
            "metric_role", "trial_ordinal", "pair_index", "value_m",
        }:
            raise NumericRoleRejected("numeric citations must have exact role schema")
        role = item["metric_role"]
        trial = item["trial_ordinal"]
        pair = item["pair_index"]
        claimed = item["value_m"]
        if (
            type(role) is not str
            or type(claimed) not in (int, float) or not math.isfinite(claimed)
            or (role, trial, pair) in keys
        ):
            raise NumericRoleRejected("nonfinite or duplicate metric claim")
        expected = numeric_value(history, role, trial, pair, feedback=feedback)
        if not math.isclose(float(claimed), expected, rel_tol=0, abs_tol=1e-8):
            raise NumericRoleRejected("claim does not match original typed source value")
        keys.add((role, trial, pair))
        found.append(NumericCitation(role, trial, pair, float(claimed)))
    return tuple(found)
