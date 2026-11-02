"""L2 B1 candidate contract V2: forecast, abstention, units and prior evaluation.

Only typed interpretation of a prior-only Paper hypothesis. Source IDs and
the numeric measurements still come from the original L MP11 source, not this
contract. It cannot establish that a natural-language explanation is correct.
V1 historical responses are NEVER translated or auto-upgraded to V2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

V2_EXTRA_FIELDS = frozenset({
    "measurement_target",
    "forecast_status",
    "prior_evaluation_basis",
    "prior_evaluation_reason",
})
TARGET = "NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M"
FORECAST_STATUSES = (
    "NUMERIC_ESTIMATE",
    "ABSTAIN_INSUFFICIENT_EVIDENCE",
    "ABSTAIN_OUTSIDE_APPLICABILITY",
    "ABSTAIN_MODEL_UNRESOLVED",
)
EVALUATION_BASES = (
    "FIRST_UNTESTED",
    "SCORED_ERROR",
    "QUALITATIVE_ONLY",
    "NO_SCORABLE_FORECAST",
)
V2_INSTRUCTION = (
    "B1 read-only prediction contract V2. Original S49/Paper WAIT8_TOTAL_M "
    "means TOTAL DISPLACEMENT over 8 world ticks, measured in METERS (m), "
    "NOT wait duration, time elapsed, or a single-next-tick prediction. "
    "Prediction means the NEXT trial's WAIT8 TOTAL DISPLACEMENT in meters. "
    "Output exact 14 JSON keys: the normal ten keys plus measurement_target, "
    "forecast_status, prior_evaluation_basis, prior_evaluation_reason. "
    f"measurement_target MUST be {TARGET}. "
    "forecast_status NUMERIC_ESTIMATE means predicted_wait_total_m is a finite "
    "0..3 meter point prediction; otherwise use exactly one of "
    "ABSTAIN_INSUFFICIENT_EVIDENCE|ABSTAIN_OUTSIDE_APPLICABILITY|"
    "ABSTAIN_MODEL_UNRESOLVED and predicted_wait_total_m MUST be null. "
    "ABSTAIN is valid uncertainty, never secretly replace with zero or a cheap "
    "reference forecast. "
    "prior_evaluation_basis FIRST_UNTESTED for H1; for H2 select SCORED_ERROR "
    "only when H1 has numeric prediction and host supplies its matching "
    "following-trial error; QUALITATIVE_ONLY for a purely observation-based "
    "comparison of the two measured WAIT8 TOTAL meters (not forecast error); "
    "NO_SCORABLE_FORECAST for explicit inability to score H1. "
    "When there is no H1 numeric prediction, do NOT say predicted-versus-actual "
    "discrepancy and do NOT claim you scored an error. If no score/defensible "
    "qualitative comparison, use ABSTAIN_ON_PRIOR, not KEEP_PRIOR. "
    "prior_evaluation_reason is a 16..120 character reason stating the "
    "specific type of evidence/limitation; explain what was or was not tested. "
    "KEEP_PRIOR with no H1 forecast requires QUALITATIVE_ONLY and source IDs "
    "T1_W8 and T2_W8, but is NEVER proof of numerical forecast evaluation. "
    "With SCORED_ERROR, select both T2_H1ERR and T2_W8 source IDs. "
    "All experiment proposals remain UNAPPROVED; no Action/learning authority. "
    "Use no future Action3 data and keep complete JSON under 512 tokens."
)


class B1ContractRejected(ValueError):
    """Malformed or semantically unsupported typed V2 self-evaluation."""


@dataclass(frozen=True, slots=True)
class B1TypedResult:
    measurement_target: str
    forecast_status: str
    prior_evaluation_basis: str
    prior_evaluation_reason: str
    numeric_prior_forecast_scored: bool
    qualitative_only: bool
    cannot_score_forecast: bool


def schema_v2_additions() -> dict[str, dict]:
    def enum(values: tuple[str, ...]) -> dict:
        return {"type": "string", "enum": list(values)}
    return {
        "measurement_target": enum((TARGET,)),
        "forecast_status": enum(FORECAST_STATUSES),
        "prior_evaluation_basis": enum(EVALUATION_BASES),
        "prior_evaluation_reason": {
            "type": "string",
            "minLength": 16,
            "maxLength": 120,
        },
    }


def validate_b1_v2(
    raw: dict, *, trial_count: int, previous_prediction_m: float | None,
    selected_ids: tuple[str, ...],
) -> B1TypedResult:
    """Validate typed claims BEFORE accepting the new hypothesis.

    Does not pretend to verify narrative physics or causal claims: that
    requires independent semantic review and physical holdouts.
    """
    if (
        type(raw) is not dict
        or trial_count not in (1, 2)
        or not V2_EXTRA_FIELDS.issubset(raw)
        or raw["measurement_target"] != TARGET
        or type(raw["forecast_status"]) is not str
        or raw["forecast_status"] not in FORECAST_STATUSES
        or type(raw["prior_evaluation_basis"]) is not str
        or raw["prior_evaluation_basis"] not in EVALUATION_BASES
        or type(raw["prior_evaluation_reason"]) is not str
        or not 16 <= len(raw["prior_evaluation_reason"]) <= 120
    ):
        raise B1ContractRejected("missing or invalid B1 V2 typed fields")

    # Targeted lexical contradiction checks, NOT general natural-language
    # verification. Duration hypotheses and time-varying input *tests* remain
    # allowed; measured WAIT8 displacement must never be renamed wait time.
    explanation = raw.get("explanation", "")
    if type(explanation) is str and re.search(
        r"\b(?:wait\s+times?|elapsed\s+time|time\s+elapsed)\b",
        explanation, flags=re.IGNORECASE,
    ):
        raise B1ContractRejected("WAIT8 displacement in meters mislabeled as waiting time")
    if trial_count == 2 and previous_prediction_m is None:
        combined = f"{explanation} {raw['prior_evaluation_reason']}"
        if re.search(
            r"\b(?:prediction\s+error|forecast\s+error|predicted\s+(?:versus|vs\.?|and)\s+actual)\b",
            combined, flags=re.IGNORECASE,
        ):
            raise B1ContractRejected("cannot claim a forecast discrepancy without H1 forecast")
    predicted = raw.get("predicted_wait_total_m")
    if (raw["forecast_status"] == "NUMERIC_ESTIMATE") != (
        type(predicted) in (int, float)
    ):
        raise B1ContractRejected("numeric forecast and explicit abstention inconsistent")
    basis = raw["prior_evaluation_basis"]
    relation = raw.get("prior_hypothesis_relation")
    if trial_count == 1:
        if basis != "FIRST_UNTESTED" or relation != "FIRST_HYPOTHESIS":
            raise B1ContractRejected("H1 cannot evaluate its own future outcome")
    else:
        if basis == "FIRST_UNTESTED" or relation == "FIRST_HYPOTHESIS":
            raise B1ContractRejected("H2 must identify its previous H1")
        if basis == "SCORED_ERROR":
            if (previous_prediction_m is None
                    or not {"T2_H1ERR", "T2_W8"}.issubset(selected_ids)):
                raise B1ContractRejected("H2 scored-error claim lacks prior numeric forecast and error witness")
        elif basis == "QUALITATIVE_ONLY":
            if not {"T1_W8", "T2_W8"}.issubset(selected_ids):
                raise B1ContractRejected("qualitative comparison lacks both observed WAIT8 displacement sources")
        elif basis == "NO_SCORABLE_FORECAST":
            if previous_prediction_m is not None:
                raise B1ContractRejected("H1 did forecast, so no-scorable claim is false")
            if relation != "ABSTAIN_ON_PRIOR":
                raise B1ContractRejected("cannot KEEP/REVISE/REJECT unscored H1 numerically")
        if relation in {"KEEP_PRIOR", "REVISE_PRIOR", "REJECT_PRIOR"} and basis not in (
            "SCORED_ERROR", "QUALITATIVE_ONLY",
        ):
            raise B1ContractRejected("prior hypothesis judgment lacks independent basis")
        if relation == "KEEP_PRIOR" and previous_prediction_m is None and basis != "QUALITATIVE_ONLY":
            raise B1ContractRejected("unscored KEEP requires explicit qualitative-only comparison")

    return B1TypedResult(
        measurement_target=TARGET,
        forecast_status=raw["forecast_status"],
        prior_evaluation_basis=basis,
        prior_evaluation_reason=raw["prior_evaluation_reason"],
        numeric_prior_forecast_scored=trial_count == 2 and basis == "SCORED_ERROR",
        qualitative_only=trial_count == 2 and basis == "QUALITATIVE_ONLY",
        cannot_score_forecast=trial_count == 2 and previous_prediction_m is None,
    )


def historical_v1_b1_readback(h1: dict, h2: dict) -> dict[str, Any]:
    """Read ONLY old frozen proposal fields; never invent missing forecasts."""
    if any(type(x) is not dict for x in (h1, h2)):
        raise B1ContractRejected("original frozen hypotheses must be objects")
    if (
        h1.get("source_prior_count") != 1
        or h2.get("source_prior_count") != 2
        or h2.get("prior_proposal_sha256") != h1.get("proposal_sha256")
    ):
        raise B1ContractRejected("original H1/H2 chronological source SHA mismatch")
    h1_prediction = h1.get("predicted_wait_total_m")
    h2_ids = tuple(h2.get("selected_evidence_ids", []))
    if h1_prediction is None:
        return {
            "classification": "HISTORICAL_V1_UNSCORABLE_NOT_B1",
            "h1_numeric_prediction": None,
            "h1_forecast_status_v2": "NOT_RECORDED_IN_V1",
            "h2_basis_v2": "NOT_RECORDED_IN_V1",
            "h2_relation_v1": h2.get("prior_hypothesis_relation"),
            "h2_selected_ids_v1": h2_ids,
            "h1_to_h2_sha_verified": True,
            "numeric_forecast_error": None,
            "can_establish_B1_numeric_self_evaluation": False,
            "world_result_changed": False,
        }
    return {
        "classification": "HISTORICAL_V1_HAS_NUMERIC_FORECAST_NOT_V2",
        "h1_numeric_prediction": h1_prediction,
        "h1_forecast_status_v2": "NOT_RECORDED_IN_V1",
        "h2_basis_v2": "NOT_RECORDED_IN_V1",
        "h2_relation_v1": h2.get("prior_hypothesis_relation"),
        "h2_selected_ids_v1": h2_ids,
        "h1_to_h2_sha_verified": True,
        "numeric_forecast_error": "REQUIRES_TYPED_ORIGINAL_NEXT_TRIAL_NOT_HERE",
        "can_establish_B1_numeric_self_evaluation": False,
        "world_result_changed": False,
    }
