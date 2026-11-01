"""Freeze H9b DEV proxy parameters after four FIT Worlds, before EVAL Worlds.

The frozen artifact is source-byte and plan-digest bound, not a qualified
Memory/L1 model. Strict source chronology is additionally verified by the
readback CLI against the before-World markers.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass

from relay_self.l_bcg_h9b_dev_holdout import (
    CHEAP_CUTOFF_M,
    H9A_ARCHIVE_SESSION_IDS,
    H9A_ARCHIVE_WORLD_IDS,
    SLOTS,
    H9bRecord,
    _require,
    source_digest,
    validate_plan,
)


@dataclass(frozen=True, slots=True)
class H9bFrozenDevProxy:
    plan_sha256: str
    fit_source_report_shas: tuple[str, ...]
    fit_source_prereg_shas: tuple[str, ...]
    executor_head: str
    cheap_threshold_m: float
    x_a_mean_m: float
    x_b_mean_m: float
    y_a_mean_m: float
    y_b_mean_m: float
    y_global_mean_m: float
    candidate_slope: float
    classifier: str = "H9B_FROZEN_4_WORLD_DEV_PROXY_NOT_FORMAL_L1"
    formal_training_worlds: int = 0
    action_authority: bool = False
    goal_attested: bool = False
    effective_clear_attested: bool = False


def serialize_frozen(model: H9bFrozenDevProxy) -> bytes:
    return (json.dumps(
        asdict(model), sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":"),
    ) + "\n").encode()


def freeze_h9b_dev_proxy(
    *, plan: dict[str, object], plan_original: bytes,
    fit_records: tuple[H9bRecord, ...],
) -> H9bFrozenDevProxy:
    plan_sha = validate_plan(plan, raw=plan_original)
    _require(
        type(fit_records) is tuple and len(fit_records) == 4,
        "four exact fit World origins required",
    )
    sessions: set[str] = set()
    worlds: set[str] = set()
    preregs: set[str] = set()
    sources: set[str] = set()
    for (slot, arm, _role), row in zip(SLOTS[:4], fit_records):
        _require(
            type(row) is H9bRecord and row.slot_id == slot
            and row.arm.arm_id == arm
            and row.frozen_plan_sha256 == plan_sha
            and row.frozen_model_sha256 is None
            and row.arm.executor_head == plan["executor_head"]
            and row.arm.original_session_id not in sessions
            and row.arm.original_paper_world_id not in worlds
            and row.arm.original_session_id not in H9A_ARCHIVE_SESSION_IDS
            and row.arm.original_paper_world_id not in H9A_ARCHIVE_WORLD_IDS
            and row.arm.original_report_sha256 not in sources
            and row.prereg_sha256 not in preregs
            and type(row.prereg_sha256) is str and len(row.prereg_sha256) == 64
            and all(x in "0123456789abcdef" for x in row.prereg_sha256)
            and row.arm.l_bcg_advice == "DEFER_UNKNOWN"
            and row.arm.observed_arm_matched
            and not row.arm.physical_effective_clear_attested
            and row.arm.qualified_training_worlds == 0
            and row.arm.new_actions == row.arm.learning_updates == 0
            and type(row.arm.sampled_reported_input_off_motion_m) in (float, int)
            and math.isfinite(row.arm.sampled_reported_input_off_motion_m)
            and row.arm.sampled_reported_input_off_motion_m >= 0
            and type(row.arm.observed_s42_distance_m) in (float, int)
            and math.isfinite(row.arm.observed_s42_distance_m)
            and abs(row.arm.observed_s42_distance_m - (2.0 if arm == "A" else 3.5)) <= 0.15
            and row.arm.cheap_near_under_3m is (arm == "A"),
            "H9b invalid FIT provenance, arm, or admission",
        )
        sessions.add(row.arm.original_session_id)
        worlds.add(row.arm.original_paper_world_id)
        sources.add(row.arm.original_report_sha256)
        preregs.add(row.prereg_sha256)
    aa = [x.arm for x in fit_records if x.arm.arm_id == "A"]
    bb = [x.arm for x in fit_records if x.arm.arm_id == "B"]
    _require(len(aa) == len(bb) == 2, "two independent FIT Worlds per S42 arm")
    x_a = sum(x.observed_s42_distance_m for x in aa) / 2
    x_b = sum(x.observed_s42_distance_m for x in bb) / 2
    _require(x_b - x_a >= 1.0, "native S42 fit centroids insufficiently separated")
    y_a = sum(x.sampled_reported_input_off_motion_m for x in aa) / 2
    y_b = sum(x.sampled_reported_input_off_motion_m for x in bb) / 2
    y_global = (y_a + y_b) / 2
    return H9bFrozenDevProxy(
        plan_sha256=plan_sha,
        fit_source_report_shas=tuple(x.arm.original_report_sha256 for x in fit_records),
        fit_source_prereg_shas=tuple(x.prereg_sha256 for x in fit_records),
        executor_head=str(plan["executor_head"]),
        cheap_threshold_m=CHEAP_CUTOFF_M,
        x_a_mean_m=x_a, x_b_mean_m=x_b,
        y_a_mean_m=y_a, y_b_mean_m=y_b,
        y_global_mean_m=y_global,
        candidate_slope=(y_b - y_a) / (x_b - x_a),
    )


def validate_frozen_original(
    *, plan: dict[str, object], plan_original: bytes,
    fit_records: tuple[H9bRecord, ...],
    frozen_original: bytes,
) -> tuple[H9bFrozenDevProxy, str]:
    _require(
        type(frozen_original) is bytes and 0 < len(frozen_original) <= 4096,
        "bounded frozen model bytes required",
    )
    saved = json.loads(frozen_original)
    saved["fit_source_report_shas"] = tuple(saved["fit_source_report_shas"])
    saved["fit_source_prereg_shas"] = tuple(saved["fit_source_prereg_shas"])
    model = H9bFrozenDevProxy(**saved)
    plan_sha = validate_plan(plan, raw=plan_original)
    _require(
        len(fit_records) == 4
        and tuple(r.slot_id for r in fit_records) == tuple(s for s, _, _ in SLOTS[:4])
        and all(r.frozen_plan_sha256 == plan_sha and r.frozen_model_sha256 is None
                and r.arm.executor_head == plan["executor_head"] for r in fit_records)
        and model.plan_sha256 == plan_sha
        and model.executor_head == plan["executor_head"]
        and model.fit_source_report_shas == tuple(r.arm.original_report_sha256 for r in fit_records)
        and model.fit_source_prereg_shas == tuple(r.prereg_sha256 for r in fit_records)
        and model.cheap_threshold_m == CHEAP_CUTOFF_M
        and model.classifier == "H9B_FROZEN_4_WORLD_DEV_PROXY_NOT_FORMAL_L1"
        and model.formal_training_worlds == 0
        and model.action_authority is False and model.goal_attested is False
        and model.effective_clear_attested is False,
        "frozen DEV model provenance differs from fit-only source reconstruction",
    )
    # Integrity checks on saved coefficients, not a call to the fitting API.
    # No new model is fitted/serialized and EVAL targets never enter here.
    aa = tuple(r.arm for r in fit_records if r.arm.arm_id == "A")
    bb = tuple(r.arm for r in fit_records if r.arm.arm_id == "B")
    _require(len(aa) == len(bb) == 2, "two FIT sources per arm required")
    _require(
        model.x_a_mean_m == sum(a.observed_s42_distance_m for a in aa) / 2
        and model.x_b_mean_m == sum(a.observed_s42_distance_m for a in bb) / 2
        and model.y_a_mean_m == sum(a.sampled_reported_input_off_motion_m for a in aa) / 2
        and model.y_b_mean_m == sum(a.sampled_reported_input_off_motion_m for a in bb) / 2
        and model.y_global_mean_m == (model.y_a_mean_m + model.y_b_mean_m) / 2
        and model.x_b_mean_m - model.x_a_mean_m >= 1.0
        and model.candidate_slope == ((model.y_b_mean_m - model.y_a_mean_m)
                                      / (model.x_b_mean_m - model.x_a_mean_m))
        and frozen_original == serialize_frozen(model),
        "frozen DEV model bytes differ from fit-only source reconstruction",
    )
    return model, source_digest(frozen_original)
