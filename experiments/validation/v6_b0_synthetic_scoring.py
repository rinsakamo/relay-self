"""V6 prospective outcome-scoring rehearsal; *never* an authenticated World score.

Only the 48 exact frozen *simulated* slots are accepted. A missing/invalid
outcome is not zero, and an assumed EAT is not an S51 receipt.
"""
from __future__ import annotations

import json
import math
from typing import Any

from experiments.validation.v6_b0_paired_world_plan import (
    ARMS,
    REGIMES,
    STARTS,
    offline_session_slots,
)

SIMULATED = "SYNTHETIC_UNATTESTED_NO_WORLD"
HORIZON = 16
BASAL = 0.5
MOVE_EXTRA = 0.25
EAT_CREDIT = 4
CAPACITY = 20
BLIND = ("ALWAYS_SEEK", "ALWAYS_WAIT")
NON_OUTCOME = ("INVALID", "CENSORED")


class V6SyntheticRejected(ValueError):
    """Pretend original receipt, altered pairing, or synthetic accounting drift."""


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise V6SyntheticRejected(why)


def mock_cohort() -> list[dict[str, Any]]:
    """All-zero cost-effect witness: NOT_RUN does not become real S51/World."""
    out = []
    for slot in offline_session_slots():
        out.append({
            "world_start_slot": slot["world_start_slot"],
            "planned_order": slot["planned_order"],
            "regime": slot["regime"],
            "arm": slot["arm"],
            "initial_m0_energy": slot["initial_m0_energy"],
            "source": SIMULATED,
            "status": "COMPLETE",
            "observed_m0_ticks": HORIZON,
            "assumed_issued_moves": 0,
            "assumed_eat_events": 0,
            "assumed_final_m0_energy": float(slot["initial_m0_energy"] - HORIZON * BASAL),
            "invalid_or_censor_reason": None,
            "real_world_source_verified": False,
            "native_world_elapsed_tick_verified": False,
            "genuine_s51_receipt_verified": False,
            "user_world_grant": False,
        })
    return out


def _validated_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], float | None]:
    template = offline_session_slots()
    _need(type(rows) is list and len(rows) == len(template),
          "missing or extra frozen session slot")
    values: dict[tuple[str, str, str], float | None] = {}
    names = {
        "world_start_slot", "planned_order", "regime", "arm",
        "initial_m0_energy", "source", "status", "observed_m0_ticks",
        "assumed_issued_moves", "assumed_eat_events",
        "assumed_final_m0_energy", "invalid_or_censor_reason",
        "real_world_source_verified", "native_world_elapsed_tick_verified",
        "genuine_s51_receipt_verified", "user_world_grant",
    }
    for i, (row, slot) in enumerate(zip(rows, template)):
        _need(type(row) is dict and set(row) == names,
              "outcome schema or original provenance changed")
        for field in ("world_start_slot", "planned_order", "regime", "arm", "initial_m0_energy"):
            _need(type(row[field]) is type(slot[field]) and row[field] == slot[field],
                  f"altered paired session identity at slot {i}")
        _need(row["source"] == SIMULATED, "real-source claim in rehearsal")
        _need(all(row[k] is False for k in (
            "real_world_source_verified", "native_world_elapsed_tick_verified",
            "genuine_s51_receipt_verified", "user_world_grant",
        )), "synthetic data promoted to real evidence")
        _need(
            type(row["observed_m0_ticks"]) is int
            and 0 <= row["observed_m0_ticks"] <= HORIZON
            and type(row["assumed_issued_moves"]) is int
            and 0 <= row["assumed_issued_moves"] <= 8
            and row["assumed_issued_moves"] <= row["observed_m0_ticks"]
            and type(row["assumed_eat_events"]) is int
            and 0 <= row["assumed_eat_events"] <= 1,
            "M0 budget or synthetic one-food opportunity violated",
        )
        label = row["status"]
        _need(label in ("COMPLETE", *NON_OUTCOME), "unregistered outcome status")
        value: float | None = None
        if label == "COMPLETE":
            _need(
                row["observed_m0_ticks"] == HORIZON
                and row["invalid_or_censor_reason"] is None
                and type(row["assumed_final_m0_energy"]) in (int, float)
                and math.isfinite(row["assumed_final_m0_energy"]),
                "incomplete/invalid result masquerades as full horizon",
            )
            expected = (
                row["initial_m0_energy"]
                - HORIZON * BASAL
                - row["assumed_issued_moves"] * MOVE_EXTRA
                + row["assumed_eat_events"] * EAT_CREDIT
            )
            # The only predeclared item enters after eleven basal WAITs;
            # before any possible eat E<=14.5, so +4 cannot hit E cap20.
            _need(0 < expected <= CAPACITY
                  and abs(row["assumed_final_m0_energy"] - expected) < 1e-9,
                  "unearned meal credit or energy accounting drift")
            value = float(expected)
        else:
            _need(
                row["assumed_final_m0_energy"] is None
                and type(row["invalid_or_censor_reason"]) is str
                and bool(row["invalid_or_censor_reason"].strip()),
                "invalid/censored source may not contribute a numeric primary",
            )
        key = (row["world_start_slot"], row["regime"], row["arm"])
        _need(key not in values, "duplicated trial identity")
        values[key] = value
    _need(set(values) == {
        (start, regime, arm)
        for start in STARTS for regime, _ in REGIMES for arm in ARMS
    }, "incomplete preregistered World grid")
    return values


def rehearse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate only eligible WITHIN-START contrasts, preserve all gaps."""
    values = _validated_map(rows)
    pairs: list[dict[str, Any]] = []
    n_computed = 0
    n_invalid = sum(row["status"] == "INVALID" for row in rows)
    n_censored = sum(row["status"] == "CENSORED" for row in rows)
    for start in STARTS:
        for regime, _ in REGIMES:
            on = values[(start, regime, "SENSOR_ON")]
            for blind in BLIND:
                control = values[(start, regime, blind)]
                eligible = on is not None and control is not None
                contrast = round(on - control, 10) if eligible else None
                n_computed += int(eligible)
                pairs.append({
                    "world_start_slot": start,
                    "regime": regime, "contrast": "ON_MINUS_" + blind,
                    "synthetic_difference": contrast,
                    "source_complete_pair": eligible,
                    "not_world_effect": True,
                })
    _need(len(pairs) == len(STARTS) * len(REGIMES) * len(BLIND),
          "preregistered primary contrast omitted")
    return {
        "classification": "V6_SYNTHETIC_PREOUTCOME_SCORING_REHEARSAL_ONLY",
        "planned_world_slots": len(rows),
        "simulated_invalid": n_invalid,
        "simulated_censored": n_censored,
        "computed_complete_primary_pairs": n_computed,
        "missing_primary_pairs": len(pairs) - n_computed,
        "predeclared_primary_contrasts": pairs,
        "real_world_trials": 0,
        "genuine_s51_outcomes": 0,
        "r_world_clock_admitted": False,
        "science_g3": "NO_GO",
        "production_go": False,
    }


def main() -> int:
    r = rehearse(mock_cohort())
    print(json.dumps({
        k: v for k, v in r.items() if k != "predeclared_primary_contrasts"
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
