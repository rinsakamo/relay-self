"""D Lane v0: source-bound exploration motivation -> existing Schema/L1/L2 seams.

CPU-only, opt-in and pure. Neither a second Goal/Intent owner nor an Action
issuer, learning owner, GPU scheduler, checkpoint writer, or target discoverer.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping

from relay_self.cognitive_minimal_dev import (
    Goal, L1Round, Option, PatternRegistry, SchemaFrame, Selection, Target, WorldPercept,
    assemble_l1_select, cpu_schema_epoch,
)
from relay_self.common_io import CommonEnvelope, ScopeRef
from relay_self.innate_schema import (
    CognitiveSignal, SchemaMode, SchemaSnapshot, check_schema_eligibility,
    signal_is_current,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, OpenCognitionRequest
from relay_self.skill_invocation import SkillDefinition
from relay_self.three_self_present import EpistemicStatus, PresentFrame


class ExplorationContractError(ValueError):
    """Reject stale, foreign, fabricated or unbounded exploration inputs."""


class ExplorationBasis(str, Enum):
    NOVELTY = "NOVELTY"
    OPEN_QUESTION = "OPEN_QUESTION"
    SKILL_UNCERTAINTY = "SKILL_UNCERTAINTY"
    PREDICTION_MISMATCH = "PREDICTION_MISMATCH"
    COMPLETED_GOAL = "COMPLETED_GOAL"
    EXPERIENCE_GAP = "EXPERIENCE_GAP"


@dataclass(frozen=True, slots=True)
class ExplorationEvidence:
    """Reference to an existing Present item; not a fresh World observation."""

    kind: ExplorationBasis
    present_ref: str
    status: EpistemicStatus

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExplorationBasis) or not isinstance(
            self.status, EpistemicStatus
        ) or not isinstance(self.present_ref, str) or not self.present_ref.strip():
            raise ExplorationContractError("typed Present evidence required")


@dataclass(frozen=True, slots=True)
class NeedReadout:
    """An independent caller-owned Need, never an exploration permission gate."""

    need_ref: str
    intensity: float
    horizon: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.need_ref, str) or not self.need_ref.strip():
            raise ExplorationContractError("Need reference missing")
        _fraction("Need intensity", self.intensity)
        if type(self.horizon) is not int or self.horizon < 0:
            raise ExplorationContractError("Need horizon must be nonnegative")


@dataclass(frozen=True, slots=True)
class ExplorationDisposition:
    """MySelf temperament / Present appraisal supplied by the existing owner."""

    curiosity: float = 1.0
    cognitive_capacity: float = 1.0
    competing_need_sensitivity: float = 0.25

    def __post_init__(self) -> None:
        _fraction("curiosity", self.curiosity)
        _fraction("cognitive capacity", self.cognitive_capacity)
        _fraction("competing Need sensitivity", self.competing_need_sensitivity)


@dataclass(frozen=True, slots=True)
class ExplorationNeed:
    signal: CognitiveSignal
    intensity: float
    basis: tuple[ExplorationEvidence, ...]
    other_needs: tuple[NeedReadout, ...]
    disposition: ExplorationDisposition

    def __post_init__(self) -> None:
        if (not isinstance(self.signal, CognitiveSignal)
                or self.signal.signal_kind != "EXPLORATION_NEED"):
            raise ExplorationContractError("need must carry an exploration Schema signal")
        _fraction("exploration intensity", self.intensity)
        if not self.basis:
            raise ExplorationContractError("exploration needs at least one reason")


def _fraction(label: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplorationContractError(f"{label} must be finite 0..1")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ExplorationContractError(f"{label} must be finite 0..1")


def _present_refs(present: PresentFrame) -> set[str]:
    refs = (set(present.attention_refs) | set(present.active_question_refs)
            | set(present.active_goal_refs)
            | {s.envelope.event_id for s in present.signals})
    for view in (
        present.three_self.my_self, present.three_self.self_body,
        present.three_self.self_world,
    ):
        for claim in view.claims:
            refs.add(claim.claim_key)
            if claim.value_ref is not None:
                refs.add(claim.value_ref)
    return refs


def propose_exploration_need(
    *,
    present: PresentFrame,
    snapshot: SchemaSnapshot,
    schema_id: str,
    evidence: tuple[ExplorationEvidence, ...],
    other_needs: tuple[NeedReadout, ...],
    disposition: ExplorationDisposition,
    signal_envelope: CommonEnvelope,
    current_registry_revision: int,
    current_source_revision_refs: tuple[str, ...],
) -> ExplorationNeed | None:
    """Produce a continuous motivation, even while busy or physically hungry.

    The evidence must already be represented in this Self's Present projection.
    Only motivation changes; no Goal/Intent/Question/Memory is committed.
    UNKNOWN is an epistemic value, neither known absent nor known present.
    """
    if not isinstance(present, PresentFrame) or not isinstance(
        snapshot, SchemaSnapshot
    ) or not isinstance(disposition, ExplorationDisposition):
        raise ExplorationContractError("Present, Schema and disposition required")
    if (present.three_self.scope.self_id != snapshot.self_id
            or present.registry_revision != snapshot.revision
            or current_registry_revision != snapshot.revision
            or present.three_self.source_revision_refs != current_source_revision_refs):
        raise ExplorationContractError("stale/foreign Present or registry")
    if (not isinstance(evidence, tuple) or len(evidence) > 16
            or any(not isinstance(e, ExplorationEvidence) for e in evidence)
            or len({(e.kind, e.present_ref) for e in evidence}) != len(evidence)
            or not isinstance(other_needs, tuple)
            or len(other_needs) > 16
            or any(not isinstance(n, NeedReadout) for n in other_needs)
            or len({n.need_ref for n in other_needs}) != len(other_needs)):
        raise ExplorationContractError("bounded unique typed evidence/Need required")
    if (not isinstance(signal_envelope, CommonEnvelope)
            or signal_envelope.kind != "COGNITIVE_SIGNAL"
            or signal_envelope.scope != present.three_self.scope
            or not signal_envelope.source_refs
            or signal_envelope.event_id in _present_refs(present)):
        raise ExplorationContractError("new current source-bound signal required")
    refs = _present_refs(present)
    if any(e.present_ref not in refs for e in evidence):
        raise ExplorationContractError("evidence is not in this Self's Present")
    eligible = check_schema_eligibility(
        snapshot, scope=present.three_self.scope, schema_id=schema_id,
        requested_mode=SchemaMode.FULL,
        current_registry_revision=current_registry_revision,
    )
    module = snapshot.get(schema_id)
    if (not eligible.allowed or module is None
            or "EXPLORATION_NEED" not in module.spec.signal_kinds or not evidence):
        return None

    # Uniform evidence contribution is NOT a fixed action/Goal priority table.
    # Owner-supplied SOUL/resource/appraisal values modulate a signal only.
    pressure = max((n.intensity for n in other_needs), default=0.0)
    intensity = min(1.0, len(evidence) / 3.0)
    intensity *= disposition.curiosity
    intensity *= (0.5 + 0.5 * disposition.cognitive_capacity)
    intensity *= (1.0 - pressure * disposition.competing_need_sensitivity)
    signal = CognitiveSignal(
        envelope=signal_envelope, schema_id=schema_id,
        module_version=module.spec.version,
        registry_revision=snapshot.revision,
        source_revision_refs=current_source_revision_refs,
        signal_kind="EXPLORATION_NEED", execution_mode=SchemaMode.FULL,
        epistemic_status="INFERRED",
    )
    return ExplorationNeed(
        signal=signal, intensity=intensity, basis=evidence,
        other_needs=other_needs, disposition=disposition,
    )


@dataclass(frozen=True, slots=True)
class ExplorationGoalCandidate:
    """Not an adopted Goal; wraps the existing finite Schema Goal contract."""

    goal: Goal
    need_signal_ref: str
    question_refs: tuple[str, ...]
    intensity: float
    route: str
    target_refs: tuple[str, ...]
    active_intent_ref: str | None
    continuity_hint: str


@dataclass(frozen=True, slots=True)
class ExplorationRound:
    present: PresentFrame
    need: ExplorationNeed
    frame: SchemaFrame
    l1: L1Round
    proposals: tuple[ExplorationGoalCandidate, ...]
    owner_revision: int

    @property
    def all_goal_candidates(self) -> tuple[Goal, ...]:
        return self.frame.goals


def form_exploration_round(
    *,
    present: PresentFrame,
    need: ExplorationNeed,
    snapshot: SchemaSnapshot,
    percept: WorldPercept,
    registry: PatternRegistry,
    intent_owner: IntentCommitment,
    owner_revision: int,
    allowed_skills: frozenset[tuple[str, int]],
    definitions: Mapping[tuple[str, int], SkillDefinition],
    epoch: int,
    goal_threshold: float = 0.20,
    recent_3self: tuple[str, ...] = (),
) -> ExplorationRound:
    """Adapt motivated Present to the ORIGINAL CPU Schema and L1 shortlist.

    Never installs a preset, synthesizes Target, selects Goal, starts Intent,
    changes L1 parameters, issues Action or modifies retained memory.
    """
    _fraction("Goal consideration threshold", goal_threshold)
    if type(owner_revision) is not int or owner_revision < 0:
        raise ExplorationContractError("owner revision required")
    if (not isinstance(percept, WorldPercept)
            or not isinstance(intent_owner, IntentCommitment)
            or present.three_self.scope != percept.scope
            or present.three_self.scope.self_id != snapshot.self_id
            or percept.source not in need.signal.envelope.source_refs
            or need.signal not in present.signals
            or present.registry_revision != snapshot.revision
            or not signal_is_current(
                need.signal, snapshot=snapshot, scope=percept.scope,
                source_revision_refs=present.three_self.source_revision_refs,
                current_registry_revision=snapshot.revision,
                requested_mode=SchemaMode.FULL,
            )):
        raise ExplorationContractError("foreign/stale/unprojected exploration Need")
    motivated = need.intensity >= goal_threshold and need.intensity > 0
    # The existing CPU evaluator is the only source of Goal/Skill/Target matches.
    frame = cpu_schema_epoch(
        replace(percept, exploration_need=motivated), registry,
        allowed_skills=allowed_skills, epoch=epoch,
        skill_definitions=definitions, use_registered_presets=True,
    )
    active = intent_owner.current_intent
    proposals = []
    for goal in frame.goals:
        if goal.schema_id != "exploration":
            continue
        options = tuple(o for o in frame.options
                        if o.goal_id == goal.goal_id and o.schema_id == "exploration"
                        and o.invocation is not None)
        route = "KNOWN_PRESET_BOUND" if options else "NEEDS_L2"
        proposals.append(ExplorationGoalCandidate(
            goal=goal, need_signal_ref=need.signal.envelope.event_id,
            question_refs=present.active_question_refs or tuple(
                e.present_ref for e in need.basis
                if e.kind is ExplorationBasis.OPEN_QUESTION
            ),
            intensity=need.intensity, route=route,
            target_refs=tuple(o.target_ref for o in options),
            active_intent_ref=None if active is None else active.intent_id,
            continuity_hint="KEEP_CURRENT_INTENT" if active is not None
                            else "NO_CURRENT_INTENT",
        ))
    return ExplorationRound(
        present=present, need=need, frame=frame,
        l1=assemble_l1_select(frame, intent_owner=intent_owner,
                              recent_3self=recent_3self),
        proposals=tuple(proposals), owner_revision=owner_revision,
    )


@dataclass(frozen=True, slots=True)
class ExplorationL2Task:
    """Proposed L2 work; no model invocation or automatic retry."""

    request: OpenCognitionRequest
    question_ref: str
    attempt_key: str
    scope: ScopeRef
    source_revision_refs: tuple[str, ...]


def prepare_exploration_l2(
    round_: ExplorationRound,
    *,
    selection: Selection,
    current_owner_revision: int,
    attempted_keys: frozenset[str],
) -> ExplorationL2Task | None:
    """Only an explicit L1 ESCALATE_L2 + current owner may propose new L2 work.

    Owner keeps attempted keys and Question refs; CANCEL/UNRESOLVED does not
    retry in the same owner/question revision, and cannot mutate any ledger.
    """
    if current_owner_revision != round_.owner_revision:
        raise ExplorationContractError("stale Intent/Goal owner revision")
    if (not isinstance(selection, Selection)
            or selection.status != "ESCALATE_L2"
            or selection.reason != "L1 requested cognitive escalation"):
        return None
    unresolved = tuple(p for p in round_.proposals if p.route == "NEEDS_L2")
    if not unresolved:
        return None
    proposal = unresolved[0]
    question = (proposal.question_refs[0] if proposal.question_refs
                else proposal.need_signal_ref)
    key = (f"explore-l2:{round_.present.three_self.scope.self_id}:"
           f"{question}:owner-{current_owner_revision}")
    if key in attempted_keys:
        return None
    if len(attempted_keys) > 256:
        raise ExplorationContractError("unbounded owner attempt view")
    context = CognitionDatum.from_value(
        "exploration_unresolved",
        {
            "question_ref": question,
            "goal_id": proposal.goal.goal_id,
            "need_signal_ref": proposal.need_signal_ref,
            "evidence_refs": [e.present_ref for e in round_.need.basis],
            "known_targets": list(proposal.target_refs),
            "source_revisions": list(round_.present.three_self.source_revision_refs),
        },
        round_.need.signal.envelope.provenance,
    )
    request = OpenCognitionRequest(
        request_id=key,
        instruction=(
            "Investigate this unresolved Question. Suggest a typed Goal/Target/"
            "existing Skill pattern or a hypothesis only. Never assert an "
            "unobserved target exists, invent coordinates, write executable "
            "code, change parameter budgets, or issue an Action. A proposed "
            "target reference must be independently validated and Self-accepted. "
            "UNRESOLVED is allowed."
        ),
        intent_id=None,
        focus="EXPLORATION_TARGET_DISCOVERY",
        context=(context,),
    )
    return ExplorationL2Task(
        request, question, key, round_.present.three_self.scope,
        round_.present.three_self.source_revision_refs,
    )


@dataclass(frozen=True, slots=True)
class L2TargetReview:
    """Read-only validation of an L2 reference against actual observed targets."""

    question_ref: str
    status: str
    target: Target | None
    provenance: Provenance


def review_l2_target_reference(
    *,
    task: ExplorationL2Task,
    result_status: str,
    result_text: str | None,
    result_provenance: Provenance,
    percept: WorldPercept,
    current_source_revision_refs: tuple[str, ...],
) -> L2TargetReview:
    """A language model cannot mint WorldBody Target evidence.

    L2 may only point to an already current source-qualified Target. A newly
    imagined destination remains a hypothesis until the Gateway observes it.
    """
    if (not isinstance(task, ExplorationL2Task)
            or percept.scope != task.scope
            or task.source_revision_refs != current_source_revision_refs
            or not isinstance(result_provenance, Provenance)):
        raise ExplorationContractError("foreign or stale L2 target review")
    if result_status in ("CANCELLED", "TIMEOUT", "UNRESOLVED"):
        return L2TargetReview(task.question_ref, result_status, None,
                              result_provenance)
    if result_status != "RESOLVED" or not isinstance(result_text, str) or (
        len(result_text) > 2048
    ):
        raise ExplorationContractError("unexpected or unbounded L2 result")
    try:
        obj = json.loads(result_text)
    except (ValueError, TypeError) as exc:
        raise ExplorationContractError("invalid L2 target JSON") from exc
    if (not isinstance(obj, dict)
            or set(obj) != {"kind", "question_ref", "target_ref", "target_kind"}
            or obj["kind"] != "TARGET_REFERENCE"
            or obj["question_ref"] != task.question_ref
            or not isinstance(obj["target_ref"], str)
            or not isinstance(obj["target_kind"], str)):
        raise ExplorationContractError("untyped, invented or foreign L2 proposal")
    target = next((t for t in percept.targets
                   if t.ref == obj["target_ref"] and t.kind == obj["target_kind"]
                   and t.live and t.observed_sequence <= percept.sequence), None)
    if target is None:
        raise ExplorationContractError("L2 Target is not in the current World Percept")
    return L2TargetReview(task.question_ref, "REFERENCED_OBSERVED_TARGET",
                          target, result_provenance)


@dataclass(frozen=True, slots=True)
class ExplorationExperienceRef:
    """Read-only C Lane handoff: Outcome is not automatically success or truth."""

    scope: ScopeRef
    goal_ref: str
    question_ref: str
    intent_ref: str | None
    action_outcome_ref: str | None
    epistemic_status: EpistemicStatus
    source_revision_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not isinstance(
            self.epistemic_status, EpistemicStatus
        ) or not self.goal_ref or not self.question_ref:
            raise ExplorationContractError("invalid bounded C Lane reference")
