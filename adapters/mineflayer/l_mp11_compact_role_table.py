"""Compact, source-exact 1-based pair/role reference table for L2 OPEN.

This is an *input aid* to the existing strict numeric citation validator, not
a substitute for Paper original rows or a way to repair L2 output after fact.
"""
from __future__ import annotations

import math

from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger


class CompactRoleTableRejected(ValueError):
    """Paper source shape is insufficient to produce unambiguous metric roles."""


def compact_role_table(ledger: LivePriorLedger, *, feedback: dict | None) -> dict:
    if type(ledger) is not LivePriorLedger or not 1 <= len(ledger.history) <= 2:
        raise CompactRoleTableRejected("bounded one-World prior experience required")
    if (len(ledger.history) == 1) != (feedback is None):
        raise CompactRoleTableRejected("previous forecast only belongs to second call")
    trials = []
    for i, t in enumerate(ledger.history, 1):
        if (
            t.ordinal != i or len(t.paper_wait_ticks) != 8
            or len(t.paper_predicted_next_m) != 7
            or len(t.paper_next_abs_error_m) != 7
            or any(type(x) is not float or not math.isfinite(x) or x < 0
                   for x in (
                       t.paper_wait_total_m, t.paper_cheap_zero_next_mae_m,
                       *t.paper_predicted_next_m, *t.paper_next_abs_error_m,
                   ))
        ):
            raise CompactRoleTableRejected("bad original Paper role/pair shape")
        trials.append({
            "trial_ordinal": i,
            "pair_index_0": {
                "WAIT8_TOTAL_M": t.paper_wait_total_m,
                "PAPER_CHEAP_NEXT_TICK_MAE_M": t.paper_cheap_zero_next_mae_m,
            },
            "pair_index_1_to_7": [
                {
                    "pair_index": j,
                    "PAPER_NEXT_TICK_PREDICTION_M": pred,
                    "PAPER_NEXT_TICK_ABS_ERROR_M": err,
                }
                for j, (pred, err) in enumerate(
                    zip(t.paper_predicted_next_m, t.paper_next_abs_error_m), 1
                )
            ],
        })
    prior = None
    if feedback is not None:
        if (
            type(feedback) is not dict
            or feedback.get("target_trial_ordinal") != 2
            or feedback.get("target_kind") != "NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M"
        ):
            raise CompactRoleTableRejected("wrong prior hypothesis target")
        predicted = feedback.get("previous_prediction_m")
        error = feedback.get("prior_prediction_abs_error_m")
        if (predicted is None) != (error is None):
            raise CompactRoleTableRejected("incoherent prior hypothesis error")
        if predicted is not None and any(
            type(x) not in (int, float) or not math.isfinite(x) or x < 0
            for x in (predicted, error)
        ):
            raise CompactRoleTableRejected("nonfinite prior forecast")
        if predicted is not None:
            prior = {
                "trial_ordinal": 2,
                "pair_index": 0,
                "PRIOR_L2_NEXT_WAIT8_PREDICTION_M": predicted,
                "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M": error,
            }
    return {
        "unit": "m",
        "citation_rule": (
            "copy exact metric_role/trial_ordinal/pair_index/value_m; "
            "index 0=aggregate, 1..7=Paper frozen-next-tick pair, "
            "NOT original WAIT tick indexes. Predictions are NOT errors."
        ),
        "trials": trials,
        "prior_L2_target": prior,
        "all_surfaces": "GRASS_BLOCK",
        "causal_surface_comparison_proven": False,
    }
