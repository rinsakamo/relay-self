"""Read-only five-axis evaluation of qualified Stage27h sources (DEV)."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from relay_self.c_lane_evaluation_readout_dev import (
    EvaluationAxis,
    EvaluationCandidate,
    EvaluationReadout,
    EvaluationStep,
    interpret_evaluation_step,
)
from relay_self.c_lane_stage27g_original_owner_review_dev import C1OwnerReviewHold, _sha
from relay_self.c_lane_stage27hi_multi_action_review_dev import (
    frame_to_step,
    prepare_stage27hi_multi_review,
)
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitiveTask,
    CommonEnvelope,
    ScopeRef,
    TaskRequirement,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    ProviderDecision,
)


@dataclass(frozen=True, slots=True)
class EvaluationReceipt:
    task: CognitiveTask
    step: EvaluationStep
    request: BoundedChoiceRequest
    ticket: object
    result: ProviderDecision
    request_sha256: str
    response_sha256: str


@dataclass(frozen=True, slots=True)
class ExecutedEvaluation:
    readout: EvaluationReadout
    receipts: tuple[EvaluationReceipt, ...]


class EvaluationSourceStale(C1OwnerReviewHold):
    """Source evidence no longer qualifies for cognitive use."""


def build_evaluation_steps(frame):
    """Construct options from the already source-qualified review frame.

    These are observations and bounded interpretations, never automatic verdicts.
    """
    facts = json.loads(frame.request.context[0].value_json)
    wal = f"wal:sha256:{frame.wal_digest}"
    native = f"native:{frame.native_session_id}:{frame.last_probe_seq}"
    target = f"target:{frame.target_contract_ref}"
    terminal = f"l0-terminal:{frame.terminal_status}"
    before = facts.get("initial_target_gap_m")
    after = facts.get("target_gap_m")
    if frame.completion_review_offered:
        progress = "Target arrival condition observed; Goal completion is not established"
    elif (facts.get("initial_target_status") == "OUTSIDE"
          and facts.get("target_status") in ("OUTSIDE", "CONDITION_OBSERVED")
          and type(before) in (float, int) and type(after) in (float, int)
          and math.isfinite(before) and math.isfinite(after)):
        if math.isclose(before, after, abs_tol=1e-9):
            progress = "Target distance did not change; arrival not established"
        elif after < before:
            progress = "Target distance decreased; arrival not established"
        else:
            progress = "Target distance increased; arrival not established"
    else:
        progress = "Target distance comparison unavailable"
    descriptions = {
        EvaluationAxis.GOAL_PROGRESS: (
            progress,
            (native, target, terminal),
        ),
        EvaluationAxis.SKILL_EFFECTIVENESS: (
            "Settled Actions were observed; Skill success is not established", (wal, native),
        ),
        EvaluationAxis.INFORMATION_GAIN: (
            "The terminal observation records this attempt; novelty is unknown", (native, terminal),
        ),
        EvaluationAxis.APPLICABILITY_FAILURE: (
            f"This attempt stopped with {frame.terminal_status}; cause is not established",
            (terminal, wal),
        ),
        EvaluationAxis.EVIDENCE_UNCERTAINTY: (
            "Settled Action evidence exists; unexecuted work and causes remain unknown",
            (wal, native),
        ),
    }
    if facts["original_action_ids"] != list(frame.action_ids):
        raise C1OwnerReviewHold("source frame action IDs changed")
    steps = []
    for axis in EvaluationAxis:
        candidates = [EvaluationCandidate(
            BoundedChoice("1", descriptions[axis][0]), descriptions[axis][1],
        ), EvaluationCandidate(BoundedChoice("2", "UNKNOWN"), ())]
        if axis is EvaluationAxis.SKILL_EFFECTIVENESS:
            movement = any(row["displacement_m"] > 0 for row in facts["executed_actions"])
            candidates.append(EvaluationCandidate(BoundedChoice(
                "3", ("Movement was measured" if movement else "No movement was measured")
                + "; Skill effectiveness is not established",
            ), (wal, native)))
            if movement and facts.get("initial_target_status") == "OUTSIDE" \
                    and facts.get("target_status") in ("OUTSIDE", "CONDITION_OBSERVED") \
                    and type(before) in (float, int) and type(after) in (float, int) \
                    and math.isfinite(before) and math.isfinite(after) and after < before:
                candidates.append(EvaluationCandidate(BoundedChoice(
                    "4", "Movement coincided with Target progress; consistent with "
                    "effectiveness, but causation is unproven",
                ), (wal, native, target)))
        if axis is EvaluationAxis.EVIDENCE_UNCERTAINTY:
            candidates.append(EvaluationCandidate(BoundedChoice(
                "3", "Target observation is supported by native evidence, while Goal "
                "and Skill success remain unverified",
            ), (native, target)))
        steps.append(EvaluationStep(axis, tuple(candidates), "2"))
    return tuple(steps)


async def _execute_evaluation(frame, loop, *, physical, lane, bridge,
                             first_action_probe, last_settled_probe,
                             task_id, budget_s=60.0, _receipts, _axes,
                             _source_validator=None):
    """Run serial bounded L1 choices; source loss raises HOLD without adoption."""
    if not isinstance(task_id, str) or not task_id.strip() or not 0 < budget_s <= 120:
        raise ValueError("unique task ID and bounded budget required")
    common = dict(physical=physical, lane=lane, bridge=bridge,
                  first_action_probe=first_action_probe,
                  last_settled_probe=last_settled_probe, world_id=frame.world_id)
    if _source_validator is None:
        baseline_current = getattr(loop.owner, "current_worldbody_observation", None)
        if baseline_current != last_settled_probe:
            raise EvaluationSourceStale("settled native probe is not CURRENT")
        baseline_tick = loop.owner.last_observed_tick

        def validate():
            try:
                current = prepare_stage27hi_multi_review(
                    loop, frame_to_step(frame, loop), **common,
                )
            except C1OwnerReviewHold as exc:
                raise EvaluationSourceStale(
                    "evaluation source is no longer qualified"
                ) from exc
            if (
                current != frame
                or getattr(loop.owner, "current_worldbody_observation", None)
                != baseline_current
                or loop.owner.last_observed_tick != baseline_tick
            ):
                raise EvaluationSourceStale("evaluation source or CURRENT changed")
    else:
        # Internal I4a bridge only: every axis/HTTP receipt revalidates the
        # original Owner's certified old prefix AND the new S2 suffix.
        # A caller-supplied model frame alone must never grant source validity.
        validate = _source_validator

    validate()
    steps = build_evaluation_steps(frame)
    source_facts = json.loads(frame.request.context[0].value_json)
    started = time.monotonic_ns()
    deadline = started + int(budget_s * 1_000_000_000)
    receipts = _receipts
    axes = _axes
    for step in steps:
        validate()
        now = time.monotonic_ns()
        if now >= deadline:
            raise C1OwnerReviewHold("evaluation budget expired")
        ref = f"{task_id}:{step.axis.value}"
        provenance = Provenance("c-lane-evaluation", frame.wal_digest)
        stamp = ClockStamp(Clock.HOST_MONOTONIC_NS, now)
        task = CognitiveTask(
            CommonEnvelope(ref, "COGNITIVE_TASK", ScopeRef(frame.self_id, frame.world_id),
                           stamp, provenance, received_at=stamp),
            ref, TaskRequirement.SELECT_FINITE, (f"wal:sha256:{frame.wal_digest}",),
            deadline, 0, tuple(c.choice for c in step.candidates), intent_ref=frame.intent_id,
        )
        request = BoundedChoiceRequest(
            ref, "Select one numbered evaluation supported by the supplied evidence. "
                 "Do not infer Skill or Goal success or issue an Action.",
            frame.intent_id, step.axis.value, task.choices,
            (CognitionDatum.from_value("evaluation_evidence", {
                "self_id": frame.self_id, "world_id": frame.world_id,
                "world_epoch": frame.world_epoch, "skill_execution_id": frame.skill_execution_id,
                "action_ids": list(frame.action_ids),
                "target_status": source_facts["target_status"],
                "initial_target_status": source_facts["initial_target_status"],
                "target_gap_m": source_facts["target_gap_m"],
                "initial_target_gap_m": source_facts["initial_target_gap_m"],
                "terminal_status": frame.terminal_status,
                "action_count": len(frame.action_ids),
                "displacements_m": [row["displacement_m"]
                                    for row in source_facts["executed_actions"]],
                "candidates": [{"number": c.choice.choice_id,
                                "evidence_refs": list(c.evidence_refs)} for c in step.candidates],
            }, provenance),), soft_wall_time_budget_s=(deadline - now) / 1e9,
            think_allowed=False,
        )
        lane.require_world_idle()
        ticket = lane.submit(frame.self_id, work_ref=ref, request=request, mode=CognitionMode.BOUNDED)
        if (ticket.self_id != frame.self_id or ticket.request_id != ref
                or ticket.work_ref != ref or ticket.backend_ref != lane.backend_ref
                or ticket.mode is not CognitionMode.BOUNDED
                or ticket.native_session_id != frame.native_session_id
                or ticket.world_epoch != frame.world_epoch or ticket.action_issue_authorized):
            raise C1OwnerReviewHold("foreign evaluation ticket")
        result = await lane.await_result(ticket, timeout_s=min(120.0, (deadline - now) / 1e9))
        if not isinstance(result, ProviderDecision) or lane.result(ticket) != result:
            raise C1OwnerReviewHold("evaluation result unavailable")
        facts = result.call_facts
        if (facts.finish_reason != "stop" or facts.prompt_tokens is None
                or facts.completion_tokens is None
                or facts.total_tokens != facts.prompt_tokens + facts.completion_tokens):
            raise C1OwnerReviewHold("evaluation HTTP facts unavailable")
        raw = lane.provider.stage26_raw_receipt(ref)
        if (_sha(Path(raw.request_path)) != raw.request_sha256
                or _sha(Path(raw.response_path)) != raw.response_sha256):
            raise EvaluationSourceStale("evaluation HTTP bytes changed")
        receipts.append(EvaluationReceipt(task, step, request, ticket, result,
                                          raw.request_sha256, raw.response_sha256))
        lane.require_world_idle()
        validate()
        if time.monotonic_ns() >= deadline or lane.result(ticket) != result:
            raise C1OwnerReviewHold("evaluation result expired")
        axes.append(interpret_evaluation_step(step, status=result.status, choice_id=result.choice_id))
    validate()
    for receipt in receipts:
        raw = lane.provider.stage26_raw_receipt(receipt.request.request_id)
        if (raw.request_sha256 != receipt.request_sha256
                or raw.response_sha256 != receipt.response_sha256
                or _sha(Path(raw.request_path)) != receipt.request_sha256
                or _sha(Path(raw.response_path)) != receipt.response_sha256
                or lane.result(receipt.ticket) != receipt.result):
            raise EvaluationSourceStale("earlier evaluation result changed")
    return ExecutedEvaluation(EvaluationReadout(
        task_id, frame.self_id, frame.world_id, frame.world_epoch, frame.skill_execution_id,
        frame.action_ids, frame.wal_digest, tuple(axes)), tuple(receipts))


@dataclass(frozen=True, slots=True)
class InterruptedEvaluationAudit:
    """Historical evidence only, never an adoptable cognitive readout."""
    task_id: str
    status: str
    axes: tuple
    receipts: tuple[EvaluationReceipt, ...]


async def execute_evaluation(frame, loop, *, physical, lane, bridge,
                             first_action_probe, last_settled_probe,
                             task_id, budget_s=60.0):
    receipts = []
    axes = []
    try:
        return await _execute_evaluation(
            frame, loop, physical=physical, lane=lane, bridge=bridge,
            first_action_probe=first_action_probe, last_settled_probe=last_settled_probe,
            task_id=task_id, budget_s=budget_s, _receipts=receipts, _axes=axes,
        )
    except BaseException as exc:
        # Preserve the original exception, including coroutine cancellation.
        status = "SOURCE_STALE" if isinstance(exc, EvaluationSourceStale) else "INTERRUPTED"
        exc.evaluation_audit = InterruptedEvaluationAudit(
            task_id, status, tuple(axes), tuple(receipts),
        )
        raise
