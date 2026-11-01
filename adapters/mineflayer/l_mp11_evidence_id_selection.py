"""Read-only typed evidence IDs chosen by L2; exact values owned by Paper source.

Opaque IDs replace model transcription of decimal measurements. Selecting an ID
does NOT certify that a model interpreted the associated physical role correctly.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from adapters.mineflayer.l_mp11_typed_feedback import (
    NumericCitation,
    NumericRoleRejected,
    numeric_value,
    previous_feedback,
)

MAX_SELECTED = 2


class EvidenceIDRejected(ValueError):
    """Missing, duplicate, future or untyped original Paper evidence ID."""


@dataclass(frozen=True, slots=True)
class EvidenceID:
    evidence_id: str
    metric_role: str
    trial_ordinal: int
    pair_index: int
    value_m: float


def _record(ledger: LivePriorLedger, role: str, trial: int, pair: int, *,
            feedback: dict | None) -> EvidenceID:
    value = numeric_value(tuple(ledger.history), role, trial, pair,
                          feedback=feedback)
    if not math.isfinite(value):
        raise EvidenceIDRejected("nonfinite original Paper evidence")
    prefix = f"T{trial}"
    suffix = {
        "WAIT8_TOTAL_M": "W8",
        "PAPER_CHEAP_NEXT_TICK_MAE_M": "CMAE",
        "PAPER_NEXT_TICK_PREDICTION_M": f"P{pair}PRED",
        "PAPER_NEXT_TICK_ABS_ERROR_M": f"P{pair}ERR",
        "PRIOR_L2_NEXT_WAIT8_PREDICTION_M": "H1PRED",
        "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M": "H1ERR",
    }[role]
    return EvidenceID(f"{prefix}_{suffix}", role, trial, pair, value)


def evidence_catalog(
    ledger: LivePriorLedger, *, previous: object = None,
) -> tuple[EvidenceID, ...]:
    if type(ledger) is not LivePriorLedger or not 1 <= len(ledger.history) <= 2:
        raise EvidenceIDRejected("only closed previous original Paper trials")
    if (len(ledger.history) == 1) != (previous is None):
        raise EvidenceIDRejected("previous hypothesis required only for trial 2")
    feedback = None
    if previous is not None:
        try:
            feedback = previous_feedback(previous, ledger.history[-1])
        except NumericRoleRejected as exc:
            raise EvidenceIDRejected("previous hypothesis has wrong source") from exc
    items: list[EvidenceID] = []
    for trial in range(1, len(ledger.history) + 1):
        for role in ("WAIT8_TOTAL_M", "PAPER_CHEAP_NEXT_TICK_MAE_M"):
            items.append(_record(ledger, role, trial, 0, feedback=feedback))
        for pair in range(1, 8):
            for role in ("PAPER_NEXT_TICK_PREDICTION_M",
                         "PAPER_NEXT_TICK_ABS_ERROR_M"):
                items.append(_record(ledger, role, trial, pair, feedback=feedback))
    if feedback is not None and feedback.get("previous_prediction_m") is not None:
        for role in ("PRIOR_L2_NEXT_WAIT8_PREDICTION_M",
                     "PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M"):
            items.append(_record(ledger, role, 2, 0, feedback=feedback))
    if len({x.evidence_id for x in items}) != len(items) or len(items) > 34:
        raise EvidenceIDRejected("nonunique or unbounded typed evidence catalog")
    return tuple(items)


def model_evidence_catalog(
    ledger: LivePriorLedger, *, previous: object = None,
) -> dict:
    items = evidence_catalog(ledger, previous=previous)
    return {
        "source_kind": "CLOSED_ORIGINAL_PAPER_AND_PRIOR_L2_FEEDBACK",
        "unit": "m",
        "indexed": [asdict(x) for x in items],
        "selection_note": (
            "Return evidence_ids only, not numeric values. "
            "Host binds selected IDs to original Paper role/index/value; "
            "this does not validate causal meaning or learning."
        ),
    }


def resolve_evidence_ids(
    ledger: LivePriorLedger, selected: object, *, previous: object = None,
) -> tuple[tuple[str, ...], tuple[NumericCitation, ...]]:
    if (type(selected) is not list or not 1 <= len(selected) <= MAX_SELECTED
            or any(type(x) is not str for x in selected)
            or len(set(selected)) != len(selected)
            or selected != sorted(selected)):
        raise EvidenceIDRejected("1-2 distinct sorted evidence IDs required")
    catalog = {x.evidence_id: x for x in evidence_catalog(
        ledger, previous=previous,
    )}
    if not all(x in catalog for x in selected):
        raise EvidenceIDRejected("unknown or future original-source evidence ID")
    citations = tuple(
        NumericCitation(catalog[x].metric_role, catalog[x].trial_ordinal,
                        catalog[x].pair_index, catalog[x].value_m)
        for x in selected
    )
    return tuple(selected), citations
