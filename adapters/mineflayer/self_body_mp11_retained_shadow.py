"""MP11: offline read-only cross-epoch retention and heldout forecast boundary.

A cheap condition mean is a provisional comparator, NOT L2 structural learning.
The MP11 WorldTrialReceipt is an unverified fixture, NOT original S49/Paper
source authentication or an L1 Habit/L0 reflex qualification.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.self_body_s50_l2_mp11_experiment import (
    EXPERIMENTS,
    L2ExperimentLoop,
    WorldTrialReceipt,
)


class MP11RetentionRejected(ValueError):
    """Reject invalid chronology, source status, identity, or future leakage."""


def _sha(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _token(value: str) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 128 and not any(
        ch.isspace() for ch in value
    )


def _digest(fields: dict) -> str:
    return hashlib.sha256(json.dumps(
        fields, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _valid_source(r: WorldTrialReceipt) -> bool:
    return (
        type(r) is WorldTrialReceipt
        and r.action_outcome == "S16_OUTCOME"
        and r.experiment_id in EXPERIMENTS
        and (r.actual_floor_material, r.actual_input_regime)
        == EXPERIMENTS[r.experiment_id]
        and r.source_status == "UNVERIFIED_OWNER_SUPPLIED_FIXTURE"
        and all(_token(x) for x in (
            r.world_uuid, r.subject_uuid, r.session_id, r.action_id,
        ))
        and all(_sha(x) for x in (
            r.proposal_sha256, r.paper_original_sha256, r.native_original_sha256,
        ))
        and len(r.wait_ticks) == len(r.wait_motion_m) == 8
        and all(type(t) is int and t > 0 for t in r.wait_ticks)
        and all(b == a + 1 for a, b in zip(r.wait_ticks, r.wait_ticks[1:]))
        and all(type(v) is float and math.isfinite(v) and v >= 0
                for v in r.wait_motion_m)
    )


@dataclass(frozen=True, slots=True)
class RetainedTrial:
    condition: str
    proposal_sha256: str
    action_id: str
    first_tick: int
    last_tick: int
    observed_wait_total_m: float
    l2_family_label: str
    paper_sha256: str
    native_sha256: str


@dataclass(frozen=True, slots=True)
class ProvisionalModel:
    world_uuid: str
    subject_uuid: str
    session_id: str
    training: tuple[RetainedTrial, ...]
    model_sha256: str
    source_status: str = "UNVERIFIED_MP11_OWNER_FIXTURES"
    algorithm: str = "CHEAP_CONDITION_MEAN_NOT_L2_STRUCTURE_LEARNING"
    authorized_actions: int = 0
    learning_admissions: int = 0
    l0_promotions: int = 0


@dataclass(frozen=True, slots=True)
class FrozenForecast:
    model_sha256: str
    world_uuid: str
    subject_uuid: str
    session_id: str
    action_id: str
    proposal_sha256: str
    experiment_id: str
    candidate_m: float | None
    cheap_zero_m: float
    cheap_global_m: float
    decision: str
    forecast_sha256: str
    executable_action: bool = False
    learning_admission: int = 0


@dataclass(frozen=True, slots=True)
class HeldoutScore:
    forecast_sha256: str
    world_uuid: str
    observed_total_m: float
    candidate_absolute_error_m: float | None
    cheap_zero_absolute_error_m: float
    cheap_global_absolute_error_m: float
    classification: str
    source_status: str = "UNVERIFIED_FIXTURE_NOT_REAL_WORLD_QUALIFICATION"
    learning_admissions: int = 0
    scientific_advantage: str = "NOT_ESTABLISHED"


def _model_fields(world: str, subject: str, session: str,
                  training: tuple[RetainedTrial, ...]) -> dict:
    return {
        "world": world, "subject": subject, "session": session,
        "training": [asdict(t) for t in training],
        "algorithm": "CHEAP_CONDITION_MEAN_NOT_L2_STRUCTURE_LEARNING",
        "source_status": "UNVERIFIED_MP11_OWNER_FIXTURES",
    }


def freeze_epoch(loop: L2ExperimentLoop) -> ProvisionalModel:
    """Seal past, completed, unverified Stage0 trials. No live World/LLM calls."""
    if (type(loop) is not L2ExperimentLoop or loop.pending is not None
            or not loop.receipts or not (
                len(loop.proposals) == len(loop.receipts) == len(loop.evaluations)
            )):
        raise MP11RetentionRejected("no completed consistent prior epoch")
    training = []
    used_actions: set[str] = set()
    used_conditions: set[str] = set()
    last_tick = -1
    for i, (p, r, e) in enumerate(zip(
        loop.proposals, loop.receipts, loop.evaluations,
    ), 1):
        if (
            not _valid_source(r)
            or (r.world_uuid, r.subject_uuid, r.session_id)
            != (loop.world_uuid, loop.subject_uuid, loop.session_id)
            or (p.world_uuid, p.subject_uuid, p.round)
            != (loop.world_uuid, loop.subject_uuid, i)
            or r.proposal_sha256 != p.proposal_sha256
            or r.experiment_id != p.experiment_id
            or p.executable_action or p.learning_admission != 0
            or r.action_id in used_actions
            or r.experiment_id in used_conditions
            or r.wait_ticks[0] <= last_tick
            or (e.round, e.proposal_sha256, e.experiment_id)
            != (i, p.proposal_sha256, r.experiment_id)
            or e.original_trial_world_uuid != loop.world_uuid
            or e.source_status != "UNVERIFIED_OWNER_SUPPLIED_FIXTURE"
            or e.learning_admissions != 0
            or not math.isclose(e.actual_wait_total_m,
                                sum(r.wait_motion_m), abs_tol=1e-10)
        ):
            raise MP11RetentionRejected("mixed, forged, replayed or stale source")
        used_actions.add(r.action_id)
        used_conditions.add(r.experiment_id)
        last_tick = r.wait_ticks[-1]
        training.append(RetainedTrial(
            r.experiment_id, p.proposal_sha256, r.action_id,
            r.wait_ticks[0], last_tick, sum(r.wait_motion_m),
            p.model_family, r.paper_original_sha256, r.native_original_sha256,
        ))
    records = tuple(training)
    seal = _digest(_model_fields(
        loop.world_uuid, loop.subject_uuid, loop.session_id, records,
    ))
    return ProvisionalModel(
        loop.world_uuid, loop.subject_uuid, loop.session_id, records, seal,
    )


def forecast_next_epoch(
    model: ProvisionalModel, *, world_uuid: str, subject_uuid: str,
    session_id: str, action_id: str, proposal_sha256: str, experiment_id: str,
) -> FrozenForecast:
    """Freeze before the heldout outcome. Unknown conditions abstain."""
    if (
        type(model) is not ProvisionalModel
        or model.source_status != "UNVERIFIED_MP11_OWNER_FIXTURES"
        or model.algorithm != "CHEAP_CONDITION_MEAN_NOT_L2_STRUCTURE_LEARNING"
        or model.authorized_actions or model.learning_admissions
        or model.l0_promotions or not model.training
        or model.model_sha256 != _digest(_model_fields(
            model.world_uuid, model.subject_uuid, model.session_id,
            model.training,
        ))
        or not all(_token(x) for x in (
            world_uuid, subject_uuid, session_id, action_id,
        ))
        or subject_uuid != model.subject_uuid
        or world_uuid == model.world_uuid
        or session_id == model.session_id
        or not _sha(proposal_sha256)
        or experiment_id not in EXPERIMENTS
    ):
        raise MP11RetentionRejected("untrusted or non-independent next epoch")
    matched = [t.observed_wait_total_m for t in model.training
               if t.condition == experiment_id]
    global_mean = sum(t.observed_wait_total_m for t in model.training) / len(
        model.training
    )
    fields = dict(
        model_sha256=model.model_sha256, world_uuid=world_uuid,
        subject_uuid=subject_uuid, session_id=session_id,
        action_id=action_id, proposal_sha256=proposal_sha256,
        experiment_id=experiment_id,
        candidate_m=sum(matched) / len(matched) if matched else None,
        cheap_zero_m=0.0, cheap_global_m=global_mean,
        decision="SHADOW_PREDICT_UNVERIFIED" if matched
        else "ABSTAIN_ESCALATE_L2",
    )
    return FrozenForecast(**fields, forecast_sha256=_digest(fields))


def score_later(
    model: ProvisionalModel, forecast: FrozenForecast,
    receipt: WorldTrialReceipt,
) -> HeldoutScore:
    """Heldout scoring never re-fits or converts a fixture into ground truth."""
    if type(forecast) is not FrozenForecast or not _valid_source(receipt):
        raise MP11RetentionRejected("missing original typed fixture")
    expected = forecast_next_epoch(
        model, world_uuid=forecast.world_uuid,
        subject_uuid=forecast.subject_uuid, session_id=forecast.session_id,
        action_id=forecast.action_id,
        proposal_sha256=forecast.proposal_sha256,
        experiment_id=forecast.experiment_id,
    )
    if (
        forecast != expected or forecast.executable_action
        or forecast.learning_admission
        or (receipt.world_uuid, receipt.subject_uuid, receipt.session_id,
            receipt.action_id, receipt.proposal_sha256, receipt.experiment_id)
        != (forecast.world_uuid, forecast.subject_uuid, forecast.session_id,
            forecast.action_id, forecast.proposal_sha256, forecast.experiment_id)
    ):
        raise MP11RetentionRejected("future leaked or cross-owner heldout source")
    actual = sum(receipt.wait_motion_m)
    error = (abs(actual - forecast.candidate_m)
             if forecast.candidate_m is not None else None)
    zero = abs(actual)
    global_error = abs(actual - forecast.cheap_global_m)
    if error is None:
        status = "ABSTAIN_UNSEEN_CONDITION"
    elif error < min(zero, global_error) - 1e-12:
        status = "SHADOW_LOWER_ERROR_UNVERIFIED_SINGLE_HELDOUT"
    else:
        status = "CHEAP_TIE_OR_BETTER_UNVERIFIED_SINGLE_HELDOUT"
    return HeldoutScore(
        forecast.forecast_sha256, receipt.world_uuid, actual,
        error, zero, global_error, status,
    )
