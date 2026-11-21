"""Minimal pure D exploration Need contract; no Goal or execution owner."""
import math
from dataclasses import dataclass
from enum import Enum

from relay_self.common_io import CommonEnvelope
from relay_self.innate_schema import (
    CognitiveSignal,
    SchemaMode,
    SchemaSnapshot,
    check_schema_eligibility,
)
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
    disposition: ExplorationDisposition | None

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
    disposition: ExplorationDisposition | None,
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
    ) or (disposition is not None and not isinstance(disposition, ExplorationDisposition)):
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
    # A caller-provided interpretation may not upgrade an UNKNOWN or
    # hypothetical Present reference into OBSERVED World evidence.
    claim_status = {}
    for view in (
        present.three_self.my_self, present.three_self.self_body,
        present.three_self.self_world,
    ):
        for claim in view.claims:
            claim_status[claim.claim_key] = claim.status
            if claim.value_ref is not None:
                claim_status[claim.value_ref] = claim.status
    for item in evidence:
        if (item.present_ref in claim_status
                and item.status is not claim_status[item.present_ref]):
            raise ExplorationContractError("exploration evidence status differs from Present")
        if (item.status is EpistemicStatus.OBSERVED
                and claim_status.get(item.present_ref) is not EpistemicStatus.OBSERVED):
            raise ExplorationContractError("only observed Present lens claims can be OBSERVED")
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
    if disposition is not None:
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


