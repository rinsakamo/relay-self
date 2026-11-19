"""C Lane: read-only C1 assembly on ORIGINAL Intent/Skill/Action owners.

Stacked on #840. No new owner, issuer, Memory store, WAL reader or GPU work.
#828 §22 overrides the older terminal-Intent C1 unit: a bounded executed
child SkillRun is an experience even when its parent Intent is still active.

All WAL / observation descriptors here are caller-provided readouts. They
cannot authenticate a Paper or native file: live admission must come from the
existing issuer / independent source verifier before this adapter is used.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle, ActionState
from relay_self.cognitive_learning_contract import (
    BeforePrediction,
    ConditionalReuseCandidate,
    CurrentCue,
    EvidenceOrigin,
    OutcomeAssessment,
    RetainedRevisionRead,
    ReuseStage,
    assess_conditional_reuse,
)
from relay_self.common_io import Clock, ClockStamp, ScopeRef
from relay_self.intent import IntentCommitment, IntentEventKind
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, CognitionDatum
from relay_self.skill import SkillExecution
from relay_self.three_self_present import EpistemicStatus, Lens


class C1AdmissionError(ValueError):
    """Cross-owner, stale or falsely qualified C1 input."""


class WalDisposition(str, Enum):
    PREPARED_UNRESOLVED = "PREPARED_UNRESOLVED"
    TERMINAL_OUTCOME = "TERMINAL_OUTCOME"
    TERMINAL_UNKNOWN = "TERMINAL_UNKNOWN"


@dataclass(frozen=True, slots=True)
class WorldBodyRead:
    """A referenced observation, NOT self-authenticating World evidence."""

    scope: ScopeRef
    world_id: str
    epoch: int
    source_seq: int
    clock: ClockStamp
    source_refs: tuple[Provenance, ...]
    origin: EvidenceOrigin

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise C1AdmissionError("native World session is mandatory")
        _text(self.world_id)
        _uint(self.epoch)
        _uint(self.source_seq)
        if not isinstance(self.clock, ClockStamp) or self.clock.domain is Clock.UNKNOWN:
            raise C1AdmissionError("observation needs known clock domain")
        if not self.source_refs or not all(isinstance(v, Provenance) for v in self.source_refs):
            raise C1AdmissionError("source-qualified observation refs required")
        if self.origin is not EvidenceOrigin.WORLD_BODY_OBSERVED:
            raise C1AdmissionError("LLM/remembered evidence is not a physical readout")


@dataclass(frozen=True, slots=True)
class WalActionRead:
    action_id: str
    scope: ScopeRef
    world_id: str
    disposition: WalDisposition
    wal_ref: Provenance
    digest_sha256: str

    def __post_init__(self) -> None:
        _text(self.action_id)
        _text(self.world_id)
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise C1AdmissionError("WAL session required")
        if not isinstance(self.disposition, WalDisposition):
            raise C1AdmissionError("unrecognized WAL disposition")
        if not isinstance(self.wal_ref, Provenance):
            raise C1AdmissionError("WAL source ref required")
        if len(self.digest_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.digest_sha256):
            raise C1AdmissionError("original WAL SHA256 required")


@dataclass(frozen=True, slots=True)
class TargetRead:
    """Independent objective assessment, never inferred from Action OUTCOME."""

    disposition: OutcomeAssessment
    check_ref: Provenance | None = None
    observed_after_ref: Provenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, OutcomeAssessment):
            raise C1AdmissionError("bad target assessment")
        if self.disposition is OutcomeAssessment.UNKNOWN:
            if self.check_ref is not None or self.observed_after_ref is not None:
                raise C1AdmissionError("unknown target cannot claim an objective check")
        elif not isinstance(self.check_ref, Provenance) or not isinstance(
            self.observed_after_ref, Provenance
        ):
            raise C1AdmissionError("known target result needs an independent observation/check")


@dataclass(frozen=True, slots=True)
class BoundedSkillRead:
    """Existing owner snapshots plus immutable *selected* Goal/Target/Preset refs."""

    cognition: PersistentCognition
    intent: IntentCommitment
    skill: SkillExecution
    actions: tuple[ActionLifecycle, ...]
    wal: tuple[WalActionRead, ...]
    scope: ScopeRef
    world_id: str
    goal_ref: str
    target_ref: str
    preset_ref: str
    bound_selection_ref: Provenance
    before: WorldBodyRead
    after: WorldBodyRead | None
    target: TargetRead | None
    before_prediction: BeforePrediction | None = None


@dataclass(frozen=True, slots=True)
class BoundedSkillExperience:
    """C1 candidate. NOT retained and NOT an authority grant."""

    scope: ScopeRef
    world_id: str
    epoch_start: int
    epoch_end: int | None
    goal_ref: str
    intent_id: str
    skill_execution_id: str
    skill_id: str
    target_ref: str
    preset_ref: str
    before: WorldBodyRead
    after: WorldBodyRead | None
    prediction_ref: str | None
    action_ids: tuple[str, ...]
    action_states: tuple[ActionState, ...]
    target_outcome: OutcomeAssessment
    evidence_refs: tuple[Provenance, ...]

    @property
    def episode_key(self) -> tuple[str, str, str]:
        return (self.scope.self_id, self.scope.world_session_id or "", self.skill_execution_id)

    @property
    def memory_id(self) -> str:
        # Stable under duplicate terminal receipts and checkpoint restore.
        encoded = json.dumps(
            [self.scope.self_id, self.world_id, self.scope.world_session_id,
             self.skill_execution_id], separators=(",", ":")
        )
        return "c1-skillrun:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assemble_bounded_skill_experience(read: BoundedSkillRead) -> BoundedSkillExperience | None:
    """Return one executed terminal child SkillRun candidate, or HOLD (None).

    Reject foreign/stale owner evidence. WAL PREPARED/ISSUED and nonterminal
    SkillRuns do not create experiences. Actual child outcome may be UNKNOWN.
    """
    if not isinstance(read, BoundedSkillRead):
        raise C1AdmissionError("typed owner snapshots required")
    if not isinstance(read.cognition, PersistentCognition) or not isinstance(
        read.intent, IntentCommitment
    ) or not isinstance(read.skill, SkillExecution):
        raise C1AdmissionError("original Cognition/Intent/Skill owner required")
    if not isinstance(read.scope, ScopeRef) or not read.scope.world_session_id:
        raise C1AdmissionError("session scope required")
    if read.cognition.identity.self_id != read.scope.self_id:
        raise C1AdmissionError("foreign Self cognition owner")
    for value in (read.world_id, read.goal_ref, read.target_ref, read.preset_ref):
        _text(value)
    if not isinstance(read.bound_selection_ref, Provenance):
        raise C1AdmissionError("original selected invocation ref required")
    if read.before.scope != read.scope or read.before.world_id != read.world_id:
        raise C1AdmissionError("foreign/stale before observation")
    if read.after is not None:
        if read.after.scope != read.scope or read.after.world_id != read.world_id:
            raise C1AdmissionError("foreign/stale after observation")
        if (read.before.clock.domain != read.after.clock.domain
                or read.after.clock.value < read.before.clock.value
                or read.after.source_seq < read.before.source_seq
                or read.after.epoch < read.before.epoch):
            raise C1AdmissionError("cross-clock or backwards physical observation")
    commits = [e for e in read.intent.events if
               e.intent_id == read.skill.intent_id and e.kind is IntentEventKind.COMMITTED]
    if len(commits) != 1 or commits[0].at_ns > read.skill.events[0].at_ns:
        raise C1AdmissionError("child Skill must belong to an original committed Intent")
    if not read.skill.is_current_snapshot:
        raise C1AdmissionError("stale Skill lineage")
    if not read.skill.is_terminal:
        return None
    if not isinstance(read.actions, tuple) or not isinstance(read.wal, tuple):
        raise C1AdmissionError("typed Action and WAL tuples required")
    if not read.actions:
        # REST without native actions is a separate guarded observation contract.
        return None
    action_ids = tuple(a.action_id for a in read.actions)
    if len(set(action_ids)) != len(action_ids):
        raise C1AdmissionError("duplicate child Action ID")
    if len(read.wal) != len(read.actions) or {v.action_id for v in read.wal} != set(action_ids):
        raise C1AdmissionError("WAL/Action bijection failed")
    wal_by_id = {w.action_id: w for w in read.wal}
    last_issued_at = read.skill.events[0].at_ns
    for action in read.actions:
        if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
            raise C1AdmissionError("stale or untyped Action")
        if action.skill_execution_id != read.skill.execution_id or action.intent_id != read.skill.intent_id:
            raise C1AdmissionError("foreign Skill/Intent Action")
        wal = wal_by_id[action.action_id]
        if wal.scope != read.scope or wal.world_id != read.world_id:
            raise C1AdmissionError("foreign WAL session or World")
        if wal.disposition is WalDisposition.PREPARED_UNRESOLVED:
            return None
        if action.state not in {ActionState.OUTCOME, ActionState.UNKNOWN, ActionState.TIMEOUT}:
            return None
        issued = [e for e in action.events if e.state is ActionState.ISSUED]
        if len(issued) != 1:
            raise C1AdmissionError("non-issued Action cannot become a physical experience")
        if issued[0].at_ns < last_issued_at or action.events[-1].at_ns > read.skill.events[-1].at_ns:
            raise C1AdmissionError("Action outside child Skill time window")
        last_issued_at = issued[0].at_ns
        if (action.state is ActionState.OUTCOME) != (
            wal.disposition is WalDisposition.TERMINAL_OUTCOME
        ):
            raise C1AdmissionError("canonical Action/WAL terminal disagreement")
    if read.before_prediction is not None:
        if not isinstance(read.before_prediction, BeforePrediction):
            raise C1AdmissionError("typed before-prediction required")
        if read.before_prediction.at_ns > read.skill.events[0].at_ns:
            raise C1AdmissionError("post-hoc prediction")
    outcome = OutcomeAssessment.UNKNOWN
    if read.target is not None:
        if not isinstance(read.target, TargetRead):
            raise C1AdmissionError("typed Target assessment required")
        if read.target.disposition is not OutcomeAssessment.UNKNOWN:
            if read.after is None or read.target.observed_after_ref not in read.after.source_refs:
                raise C1AdmissionError("target check is not tied to after WorldBody evidence")
            if any(a.state is not ActionState.OUTCOME for a in read.actions):
                raise C1AdmissionError("unresolved Action cannot imply known Target")
            outcome = read.target.disposition
    evidence = (
        *read.before.source_refs,
        *(read.after.source_refs if read.after else ()),
        read.bound_selection_ref,
        *(w.wal_ref for w in read.wal),
        *(e.provenance for a in read.actions for e in a.events),
        *(read.target.check_ref for _ in (0,) if read.target is not None
          and read.target.check_ref is not None),
    )
    return BoundedSkillExperience(
        scope=read.scope, world_id=read.world_id,
        epoch_start=read.before.epoch,
        epoch_end=read.after.epoch if read.after else None,
        goal_ref=read.goal_ref, intent_id=read.skill.intent_id,
        skill_execution_id=read.skill.execution_id, skill_id=read.skill.skill_id,
        target_ref=read.target_ref, preset_ref=read.preset_ref,
        before=read.before, after=read.after,
        prediction_ref=read.before_prediction.prediction_ref if read.before_prediction else None,
        action_ids=action_ids, action_states=tuple(a.state for a in read.actions),
        target_outcome=outcome, evidence_refs=evidence,
    )


def propose_existing_memory(
    cognition: PersistentCognition,
    experience: BoundedSkillExperience,
    *,
    integration_provenance: Provenance,
) -> Memory | None:
    """Provide a native Memory value for SELF owner review; never retain it here."""
    if not isinstance(cognition, PersistentCognition) or not isinstance(
        experience, BoundedSkillExperience
    ) or not isinstance(integration_provenance, Provenance):
        raise C1AdmissionError("existing Memory owner and provenance required")
    if cognition.identity.self_id != experience.scope.self_id:
        raise C1AdmissionError("foreign Memory owner")
    if any(m.memory_id == experience.memory_id for m in cognition.memories):
        return None
    payload = {
        "kind": "C1_BOUNDED_SKILLRUN_V1",
        "episode_key": list(experience.episode_key),
        "world_id": experience.world_id,
        "epoch": [experience.epoch_start, experience.epoch_end],
        "goal_ref": experience.goal_ref,
        "intent_id": experience.intent_id,
        "skill_id": experience.skill_id,
        "target_ref": experience.target_ref,
        "preset_ref": experience.preset_ref,
        "prediction_ref": experience.prediction_ref,
        "action_ids": list(experience.action_ids),
        "action_states": [v.value for v in experience.action_states],
        "target_outcome": experience.target_outcome.value,
        "source_refs": [[p.source, p.reference] for p in experience.evidence_refs],
    }
    return Memory(
        memory_id=experience.memory_id,
        content=json.dumps(payload, sort_keys=True, ensure_ascii=False),
        source_provenance=experience.before.source_refs[0],
        integration_provenance=integration_provenance,
    )


@dataclass(frozen=True, slots=True)
class UnderstandingDraft:
    """Fallible C2 interpretation/hypothesis; never an observed World fact."""

    episode_key: tuple[str, str, str]
    lens: Lens
    observed_refs: tuple[Provenance, ...]
    prior_prediction_ref: str | None
    interpretation: str
    hypothesis: str
    counterexample_refs: tuple[str, ...]
    uncertainty: str
    epistemic_status: EpistemicStatus = EpistemicStatus.HYPOTHETICAL


def propose_c2_understanding(
    experience: BoundedSkillExperience, *,
    lens: Lens, interpretation: str, hypothesis: str,
    uncertainty: str, counterexample_refs: tuple[str, ...] = (),
) -> UnderstandingDraft:
    """L1/L2-supplied text stays hypothetical; NEVER infer a fixed world rule."""
    if not isinstance(experience, BoundedSkillExperience) or not isinstance(lens, Lens):
        raise C1AdmissionError("C2 requires source-linked experience and 3Self lens")
    for value in (interpretation, hypothesis, uncertainty):
        _text(value)
    if not isinstance(counterexample_refs, tuple) or not all(
        isinstance(v, str) and v for v in counterexample_refs
    ):
        raise C1AdmissionError("typed counterexample references required")
    return UnderstandingDraft(
        episode_key=experience.episode_key, lens=lens,
        observed_refs=experience.evidence_refs,
        prior_prediction_ref=experience.prediction_ref,
        interpretation=interpretation, hypothesis=hypothesis,
        counterexample_refs=counterexample_refs, uncertainty=uncertainty,
    )


def c3_shadow_l1_context(
    cognition: PersistentCognition,
    *,
    candidate: ConditionalReuseCandidate,
    retained: RetainedRevisionRead | None,
    current_scope: ScopeRef,
    current_source_revision_refs: tuple[str, ...],
    cues: tuple[CurrentCue, ...],
    choice_set: tuple[BoundedChoice, ...],
    current_owner_revision: int | None,
    viability_confirmed: bool,
    cost_budget_ns: int,
    contradictions: tuple[str, ...] = (),
) -> tuple[tuple[BoundedChoice, ...], CognitionDatum | None]:
    """Annotate pre-bound choices; NEVER add/remove/parameterize Skill choices.

    C3 requires a C1 entry actually accepted by the existing Memory owner and
    an accepted C2 revision before L1-retained consideration. A shadow may be
    inspected without granting retained reuse. The caller still owns adoption.
    """
    if not isinstance(cognition, PersistentCognition) or cognition.identity.self_id != current_scope.self_id:
        raise C1AdmissionError("wrong Structured Memory owner")
    if not isinstance(choice_set, tuple) or not all(isinstance(c, BoundedChoice) for c in choice_set):
        raise C1AdmissionError("original finite L1 choices required")
    if not isinstance(candidate, ConditionalReuseCandidate):
        raise C1AdmissionError("typed retained candidate required")
    accepted_keys = set()
    for memory in cognition.memories:
        if not memory.memory_id.startswith("c1-skillrun:"):
            continue
        try:
            item = json.loads(memory.content)
            if item.get("kind") == "C1_BOUNDED_SKILLRUN_V1":
                accepted_keys.add(tuple(item["episode_key"]))
        except (ValueError, TypeError, KeyError):
            continue
    if candidate.proposal.episode_key not in accepted_keys:
        return choice_set, None
    verdict = assess_conditional_reuse(
        candidate, retained=retained, current_owner_revision=current_owner_revision,
        current_scope=current_scope, current_source_revision_refs=current_source_revision_refs,
        cues=cues, allow_l1_reuse=True, viability_confirmed=viability_confirmed,
        cost_budget_ns=cost_budget_ns, current_contradiction_refs=contradictions,
    )
    if verdict.stage is ReuseStage.ABSTAIN:
        return choice_set, None
    return choice_set, CognitionDatum.from_value(
        "c3_condition_scoped_read_only",
        {"candidate_ref": candidate.candidate_ref, "stage": verdict.stage.value,
         "reason": verdict.reason, "retained_revision": verdict.retained_revision,
         "choice_ids": [c.choice_id for c in choice_set]},
        candidate.provenance,
    )


def _text(value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise C1AdmissionError("nonempty reference/text required")


def _uint(value: object) -> None:
    if type(value) is not int or value < 0:
        raise C1AdmissionError("nonnegative integer required")
