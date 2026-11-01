"""H9b prospective DEV-only World-heldout proxy prediction.

No formal Memory, MotorOutcome, learned L1 Action policy, Goal, effective-clear
attestation, or qualification. H9a Worlds are explicitly excluded.
The cheap threshold comparator and the candidate use identical S42 native data.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from relay_self.l_bcg_h9a_pair import H9aArmResult

PROTOCOL = "L_BCG_H9B_DEV_S42_WORLD_HOLDOUT_V1"
CONFIG_RULE = "ORIGINAL_SHA_PER_WORLD_AND_TIMESTAMP_LINE_ONLY_CROSS_WORLD"
CHEAP_CUTOFF_M = 3.0
SLOTS = (
    ("A-F1", "A", "dev_fit"), ("B-F1", "B", "dev_fit"),
    ("B-F2", "B", "dev_fit"), ("A-F2", "A", "dev_fit"),
    ("B-E1", "B", "dev_eval"), ("A-E1", "A", "dev_eval"),
    ("A-E2", "A", "dev_eval"), ("B-E2", "B", "dev_eval"),
)
H9A_ARCHIVE_SESSION_IDS = frozenset((
    "1ba73115-4038-40ef-8435-90ad7c7e8f92",
    "b7a49586-27bf-4ce2-b012-49f477451a45",
))
H9A_ARCHIVE_WORLD_IDS = frozenset((
    "48e59ab1-dba7-440c-8a6e-e63b064a9f27",
    "cb941137-9e11-4a8d-a08a-6b81a1d91cb6",
))


class H9bRejected(ValueError):
    """Provenance, prospective prereg, split or DEV authority violation."""


@dataclass(frozen=True, slots=True)
class H9bRecord:
    slot_id: str
    arm: H9aArmResult
    frozen_plan_sha256: str
    prereg_sha256: str


@dataclass(frozen=True, slots=True)
class H9bScore:
    arm_id: str
    slot_id: str
    observed_s42_m: float
    outcome_proxy_m: float
    cheap_global_pred_m: float
    cheap_threshold_bin_pred_m: float
    candidate_linear_pred_m: float
    cheap_global_abs_error_m: float
    cheap_threshold_bin_abs_error_m: float
    candidate_linear_abs_error_m: float


@dataclass(frozen=True, slots=True)
class H9bComparison:
    classification: str
    plan_sha256: str
    fit_world_count: int
    eval_world_count: int
    model_frozen_before_eval: bool
    cheap_global_mae_m: float
    cheap_threshold_bin_mae_m: float
    candidate_linear_mae_m: float
    candidate_vs_cheap_threshold: str
    candidate_condition_responsive: bool
    scores: tuple[H9bScore, ...]
    outcome_kind: str = "DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M"
    causal_learning_improvement_attested: bool = False
    cross_world_generalization_attested: bool = False
    physical_training_worlds: int = 0
    formal_heldout_worlds: int = 0
    new_l0_action_issues: int = 0
    l1_action_authority: bool = False
    learned_l1_attention: str = "DEFER_UNKNOWN"
    goal: str = "UNDETERMINED"
    effective_clear: str = "NOT_ATTESTED"
    qualification: str = "NO_GO"
    science: str = "NOT_RUN"


def _require(value: bool, reason: str) -> None:
    if not value:
        raise H9bRejected(reason)


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def source_digest(raw: bytes) -> str:
    _require(type(raw) is bytes, "bytes source required")
    return hashlib.sha256(raw).hexdigest()


def validate_plan(plan: dict[str, object], *, raw: bytes) -> str:
    """Exact fixed 8-slot prior protocol; no adaptive splits or cutoffs."""
    _require(type(plan) is dict, "H9b plan JSON object required")
    _require(
        plan.get("schema") == PROTOCOL
        and plan.get("config_rule") == CONFIG_RULE
        and plan.get("slots") == [
            {"slot_id": slot, "arm_id": arm, "role": role}
            for slot, arm, role in SLOTS
        ]
        and plan.get("cheap_threshold_m") == CHEAP_CUTOFF_M
        and plan.get("worlds") == 8
        and plan.get("max_original_actions_per_world") == 1
        and plan.get("retries_per_world") == 0
        and plan.get("additional_native_probes") == 0
        and plan.get("additional_l_bcg_actions") == 0
        and plan.get("model_calls") == 0
        and plan.get("learning_updates") == 0
        and plan.get("qualified_training_worlds") == 0
        and plan.get("fit_before_eval") is True
        and plan.get("freeze_model_before_eval") is True
        and plan.get("old_h9a_sources_excluded") is True
        and plan.get("outcome_kind") == "DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M"
        and plan.get("qualification") == "NO_GO"
        and plan.get("science") == "NOT_RUN",
        "H9b fixed prospective plan changed",
    )
    head = plan.get("executor_head")
    _require(
        type(head) is str and len(head) == 40
        and all(c in "0123456789abcdef" for c in head),
        "H9b exact executor HEAD not frozen",
    )
    return source_digest(raw)


def validate_records(
    plan: dict[str, object], plan_original: bytes,
    records: tuple[H9bRecord, ...],
) -> str:
    digest = validate_plan(plan, raw=plan_original)
    _require(
        type(records) is tuple and len(records) == 8,
        "eight exact independent DEV Worlds required; no partial PASS",
    )
    sessions: set[str] = set()
    worlds: set[str] = set()
    reports: set[str] = set()
    preregs: set[str] = set()
    for (slot, arm_id, _role), row in zip(SLOTS, records):
        _require(type(row) is H9bRecord and type(row.arm) is H9aArmResult,
                 "typed H9b independently audited source required")
        a = row.arm
        _require(
            row.slot_id == slot and a.arm_id == arm_id
            and row.frozen_plan_sha256 == digest
            and type(row.prereg_sha256) is str and len(row.prereg_sha256) == 64
            and all(c in "0123456789abcdef" for c in row.prereg_sha256)
            and row.prereg_sha256 not in preregs
            and a.executor_head == plan["executor_head"]
            and type(a.original_session_id) is str and bool(a.original_session_id)
            and type(a.original_paper_world_id) is str and bool(a.original_paper_world_id)
            and type(a.original_report_sha256) is str
            and len(a.original_report_sha256) == 64
            and a.original_session_id not in sessions
            and a.original_paper_world_id not in worlds
            and a.original_report_sha256 not in reports
            and a.original_session_id not in H9A_ARCHIVE_SESSION_IDS
            and a.original_paper_world_id not in H9A_ARCHIVE_WORLD_IDS
            and a.original_l0_selection == "MOVE_AWAY"
            and a.l_bcg_advice == "DEFER_UNKNOWN"
            and a.observed_arm_matched
            and not a.physical_effective_clear_attested
            and a.qualified_training_worlds == 0
            and a.new_actions == a.learning_updates == 0
            and _number(a.sampled_reported_input_off_motion_m)
            and a.sampled_reported_input_off_motion_m >= 0
            and _number(a.observed_s42_distance_m)
            and abs(a.observed_s42_distance_m - (2.0 if arm_id == "A" else 3.5)) <= 0.15
            and a.cheap_near_under_3m is (arm_id == "A"),
            "H9b provenance, duplicate or authority ceiling mismatch",
        )
        sessions.add(a.original_session_id)
        worlds.add(a.original_paper_world_id)
        reports.add(a.original_report_sha256)
        preregs.add(row.prereg_sha256)
    return digest


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values)


def compare_h9b_dev_holdout(
    *, plan: dict[str, object], plan_original: bytes,
    records: tuple[H9bRecord, ...],
) -> H9bComparison:
    """Models trained on four DEV proxy fit Worlds and scored on four unseen Worlds.

    Baselines:
    - global mean from fit only (no condition),
    - CHEAP 3m threshold bin means from fit only (same native S42 data).
    Candidate:
    - 1D affine fit to TRAINING arm *means* (two native x centroids).
    With exactly two discrete S42 settings it often matches CHEAP; this is
    intended and forbids claiming intelligence from merely splitting bins.
    """
    plan_sha = validate_records(plan, plan_original, records)
    fit = records[:4]
    evaluation = records[4:]
    _require(
        all(row.slot_id.endswith(("F1", "F2")) for row in fit)
        and all(row.slot_id.endswith(("E1", "E2")) for row in evaluation),
        "H9b World chronological fit/eval partition changed",
    )
    y_fit = tuple(row.arm.sampled_reported_input_off_motion_m for row in fit)
    global_pred = _mean(y_fit)
    groups = {
        "A": tuple(row.arm for row in fit if row.arm.arm_id == "A"),
        "B": tuple(row.arm for row in fit if row.arm.arm_id == "B"),
    }
    _require(len(groups["A"]) == len(groups["B"]) == 2, "H9b two fit Worlds each")
    x_a = _mean(tuple(x.observed_s42_distance_m for x in groups["A"]))
    x_b = _mean(tuple(x.observed_s42_distance_m for x in groups["B"]))
    _require(x_b - x_a >= 1.0, "H9b distance centroids collapsed")
    y_a = _mean(tuple(x.sampled_reported_input_off_motion_m for x in groups["A"]))
    y_b = _mean(tuple(x.sampled_reported_input_off_motion_m for x in groups["B"]))
    slope = (y_b - y_a) / (x_b - x_a)
    # Frozen fit-only parameters; no parameter tuning, interpolation selection,
    # or thresholds based on heldout target observations.
    out: list[H9bScore] = []
    for row in evaluation:
        a = row.arm
        predicted_cheap = y_a if a.observed_s42_distance_m < CHEAP_CUTOFF_M else y_b
        predicted_linear = y_a + slope * (a.observed_s42_distance_m - x_a)
        y = a.sampled_reported_input_off_motion_m
        _require(math.isfinite(predicted_linear), "non-finite H9b prediction")
        out.append(H9bScore(
            arm_id=a.arm_id, slot_id=row.slot_id,
            observed_s42_m=a.observed_s42_distance_m,
            outcome_proxy_m=y,
            cheap_global_pred_m=global_pred,
            cheap_threshold_bin_pred_m=predicted_cheap,
            candidate_linear_pred_m=predicted_linear,
            cheap_global_abs_error_m=abs(global_pred - y),
            cheap_threshold_bin_abs_error_m=abs(predicted_cheap - y),
            candidate_linear_abs_error_m=abs(predicted_linear - y),
        ))
    scores = tuple(out)
    global_mae = _mean(tuple(x.cheap_global_abs_error_m for x in scores))
    cheap_mae = _mean(tuple(x.cheap_threshold_bin_abs_error_m for x in scores))
    candidate_mae = _mean(tuple(x.candidate_linear_abs_error_m for x in scores))
    tol = 1e-9
    relation = (
        "EQUIVALENT_WITHIN_1E-9_M"
        if abs(candidate_mae - cheap_mae) <= tol else
        "DEV_CANDIDATE_LOWER_MAE_NO_CAUSAL_CLAIM"
        if candidate_mae < cheap_mae else
        "CHEAP_THRESHOLD_LOWER_MAE"
    )
    return H9bComparison(
        classification="H9B_8_WORLD_DEV_PROXY_FIT_EVAL_ONLY",
        plan_sha256=plan_sha, fit_world_count=4, eval_world_count=4,
        model_frozen_before_eval=True,
        cheap_global_mae_m=global_mae,
        cheap_threshold_bin_mae_m=cheap_mae,
        candidate_linear_mae_m=candidate_mae,
        candidate_vs_cheap_threshold=relation,
        candidate_condition_responsive=(abs(y_b - y_a) > tol),
        scores=scores,
    )


def build_h9b_plan(*, executor_head: str) -> dict[str, object]:
    """Generate prospectively; owner must save and SHA before FIRST World."""
    plan = {
        "schema": PROTOCOL, "executor_head": executor_head,
        "config_rule": CONFIG_RULE,
        "slots": [
            {"slot_id": slot, "arm_id": arm, "role": role}
            for slot, arm, role in SLOTS
        ],
        "cheap_threshold_m": CHEAP_CUTOFF_M,
        "worlds": 8, "max_original_actions_per_world": 1,
        "retries_per_world": 0,
        "additional_native_probes": 0, "additional_l_bcg_actions": 0,
        "model_calls": 0, "learning_updates": 0,
        "qualified_training_worlds": 0,
        "fit_before_eval": True, "freeze_model_before_eval": True,
        "old_h9a_sources_excluded": True,
        "outcome_kind": "DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M",
        "qualification": "NO_GO", "science": "NOT_RUN",
    }
    validate_plan(plan, raw=json.dumps(plan).encode())
    return plan
