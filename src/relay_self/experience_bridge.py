"""L1 read-only bridge: typed S16 evidence -> existing Memory -> next cognitive hint.

The source/Action and Memory owners stay external. No World authentication is
created by serializing data; the S owner supplies admitted evidence digests.
Neither movement nor a produced S17 feedback proves goal success or S10 authority.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.learning import LearningFeedback
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.provenance import Provenance

SCHEMA = "L1_SOURCE_EPISODE_V1"
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]+\\Z")


class ExperienceRejected(ValueError):
    """Untrusted source identity or invalid retained experience."""


class ReuseStatus(str, Enum):
    NO_RETENTION = "no_retention"
    RECALL = "recall"
    RECONSIDER = "reconsider"
    CONTRADICTORY = "contradictory"
    STALE = "stale"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExperienceRejected(f"{name} must be nonempty")


def _tags(value: object) -> None:
    if (
        not isinstance(value, tuple)
        or not value
        or any(not isinstance(x, str) or _TOKEN.fullmatch(x) is None for x in value)
        or len(set(value)) != len(value)
        or value != tuple(sorted(value))
    ):
        raise ExperienceRejected("tags must be sorted unique nonempty tokens")


@dataclass(frozen=True, slots=True)
class SourceEpisode:
    session_id: str
    world_revision: int
    action_id: str
    binding_id: str
    action_ref: str
    source_status: str
    disposition: ActionOutcomeDisposition
    reason_code: str
    evidence_sha256: str
    cue_tags: tuple[str, ...]
    source_provenance: Provenance
    hypothesis: str | None = None

    def __post_init__(self) -> None:
        for name in ("session_id", "action_id", "binding_id", "action_ref",
                     "source_status", "reason_code"):
            _text(name, getattr(self, name))
        if type(self.world_revision) is not int or self.world_revision < 0:
            raise ExperienceRejected("world_revision must be nonnegative")
        if not isinstance(self.disposition, ActionOutcomeDisposition):
            raise ExperienceRejected("S16 disposition required")
        if self.disposition is ActionOutcomeDisposition.UNAVAILABLE:
            raise ExperienceRejected("UNAVAILABLE is not a terminal episode")
        if not isinstance(self.evidence_sha256, str) or not _SHA256.fullmatch(
            self.evidence_sha256
        ):
            raise ExperienceRejected("exact lowercase evidence SHA256 required")
        _tags(self.cue_tags)
        if not isinstance(self.source_provenance, Provenance):
            raise ExperienceRejected("source provenance required")
        if self.hypothesis is not None:
            _text("hypothesis", self.hypothesis)

    @property
    def memory_id(self) -> str:
        return f"l1:{self.session_id}:{self.action_id}:{self.world_revision}"


@dataclass(frozen=True, slots=True)
class QualifiedEpisode:
    """An observation-shaped episode and *separate* S17 feedback, if provided."""

    episode: SourceEpisode
    feedback: LearningFeedback | None

    def __post_init__(self) -> None:
        if not isinstance(self.episode, SourceEpisode):
            raise ExperienceRejected("typed episode required")
        if self.feedback is not None and not isinstance(self.feedback, LearningFeedback):
            raise ExperienceRejected("feedback must come from S17")


def qualify_episode(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    *,
    world_revision: int,
    evidence_sha256: str,
    cue_tags: tuple[str, ...],
    feedback: LearningFeedbackInterpretation | None = None,
    hypothesis: str | None = None,
) -> QualifiedEpisode:
    """Check S16/S17 lineage, not independent physical source authenticity.

    The S owner must validate original frames and digest before invoking this.
    The returned feedback is NEVER committed or treated as a goal-success label.
    """
    if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
        raise ExperienceRejected("current typed Action owner snapshot required")
    if not isinstance(outcome, ActionOutcomeInterpretation):
        raise ExperienceRejected("typed S16 interpretation required")
    if (
        action.action_id != outcome.action_id
        or action.skill_execution_id != outcome.skill_execution_id
        or action.intent_id != outcome.intent_id
        or action.events[-1].provenance != outcome.world_provenance
        or (action.state is ActionState.OUTCOME)
        != (outcome.disposition is ActionOutcomeDisposition.OUTCOME)
        or action.state not in (ActionState.OUTCOME, ActionState.UNKNOWN)
        or outcome.disposition is ActionOutcomeDisposition.UNAVAILABLE
    ):
        raise ExperienceRejected("terminal Action/S16 lineage mismatch")
    retained_feedback = None
    if feedback is not None:
        if not isinstance(feedback, LearningFeedbackInterpretation):
            raise ExperienceRejected("typed S17 feedback interpretation required")
        if (
            feedback.action_id != action.action_id
            or feedback.skill_execution_id != action.skill_execution_id
            or feedback.intent_id != action.intent_id
            or feedback.binding_id != outcome.binding_id
            or feedback.action_ref != outcome.action_ref
            or feedback.outcome_reason != outcome.reason_code
            or feedback.world_provenance != outcome.world_provenance
        ):
            raise ExperienceRejected("S17 feedback lineage mismatch")
        if feedback.status is LearningFeedbackInterpretationStatus.PRODUCED:
            if (
                action.state is not ActionState.OUTCOME
                or feedback.feedback is None
                or feedback.feedback.target_id != feedback.target_id
            ):
                raise ExperienceRejected("non-observed or invalid S17 feedback")
            retained_feedback = feedback.feedback
        elif feedback.feedback is not None:
            raise ExperienceRejected("non-produced S17 cannot contain feedback")
    episode = SourceEpisode(
        session_id=outcome.session_id,
        world_revision=world_revision,
        action_id=action.action_id,
        binding_id=outcome.binding_id,
        action_ref=outcome.action_ref,
        source_status=outcome.source_status,
        disposition=outcome.disposition,
        reason_code=outcome.reason_code,
        evidence_sha256=evidence_sha256,
        cue_tags=cue_tags,
        source_provenance=outcome.world_provenance,
        hypothesis=hypothesis,
    )
    return QualifiedEpisode(episode, retained_feedback)


def retain_observation(
    cognition: PersistentCognition,
    qualified: QualifiedEpisode,
    *,
    integration_provenance: Provenance,
) -> PersistentCognition:
    """Delegate all retention, duplicate checks and persistence to existing owner."""
    if not isinstance(cognition, PersistentCognition):
        raise ExperienceRejected("existing Memory owner required")
    if not isinstance(qualified, QualifiedEpisode):
        raise ExperienceRejected("qualified episode required")
    if not isinstance(integration_provenance, Provenance):
        raise ExperienceRejected("integration provenance required")
    episode = qualified.episode
    data = {
        "schema": SCHEMA,
        "session_id": episode.session_id,
        "world_revision": episode.world_revision,
        "action_id": episode.action_id,
        "binding_id": episode.binding_id,
        "action_ref": episode.action_ref,
        "source_status": episode.source_status,
        "disposition": episode.disposition.value,
        "reason_code": episode.reason_code,
        "evidence_sha256": episode.evidence_sha256,
        "cue_tags": list(episode.cue_tags),
        "hypothesis": episode.hypothesis,
    }
    return cognition.retain_memory(Memory(
        memory_id=episode.memory_id,
        content=json.dumps(data, sort_keys=True, separators=(",", ":")),
        source_provenance=episode.source_provenance,
        integration_provenance=integration_provenance,
    ))


@dataclass(frozen=True, slots=True)
class ReuseQuery:
    session_id: str
    world_revision: int
    cue_tags: tuple[str, ...]
    admitted_evidence_sha256: frozenset[str]
    max_revision_lag: int = 0

    def __post_init__(self) -> None:
        _text("session_id", self.session_id)
        if type(self.world_revision) is not int or self.world_revision < 0:
            raise ExperienceRejected("world_revision must be nonnegative")
        if type(self.max_revision_lag) is not int or self.max_revision_lag < 0:
            raise ExperienceRejected("max_revision_lag must be nonnegative")
        _tags(self.cue_tags)
        if (
            not isinstance(self.admitted_evidence_sha256, frozenset)
            or any(not isinstance(x, str) or not _SHA256.fullmatch(x)
                   for x in self.admitted_evidence_sha256)
        ):
            raise ExperienceRejected("S-owned admitted evidence digests required")


@dataclass(frozen=True, slots=True)
class CognitiveHint:
    """Read-only evidence reference, not an Action candidate or authority token."""

    status: ReuseStatus
    memory_ids: tuple[str, ...] = ()
    observed_action_refs: tuple[str, ...] = ()
    examined: int = 0
    reason: str = ""


def _decode(memory: Memory) -> SourceEpisode | None:
    if not memory.memory_id.startswith("l1:"):
        return None
    try:
        data = json.loads(memory.content)
        if not isinstance(data, dict) or set(data) != {
            "schema", "session_id", "world_revision", "action_id", "binding_id",
            "action_ref", "source_status", "disposition", "reason_code",
            "evidence_sha256", "cue_tags", "hypothesis",
        } or data["schema"] != SCHEMA or not isinstance(data["cue_tags"], list):
            raise ExperienceRejected("invalid Memory episode schema")
        episode = SourceEpisode(
            session_id=data["session_id"],
            world_revision=data["world_revision"],
            action_id=data["action_id"],
            binding_id=data["binding_id"],
            action_ref=data["action_ref"],
            source_status=data["source_status"],
            disposition=ActionOutcomeDisposition(data["disposition"]),
            reason_code=data["reason_code"],
            evidence_sha256=data["evidence_sha256"],
            cue_tags=tuple(data["cue_tags"]),
            source_provenance=memory.source_provenance,
            hypothesis=data["hypothesis"],
        )
        if memory.memory_id != episode.memory_id:
            raise ExperienceRejected("Memory identity and episode lineage differ")
        return episode
    except (ValueError, TypeError, KeyError) as exc:
        raise ExperienceRejected("malformed retained L1 episode") from exc


def retrieve_experience(
    cognition: PersistentCognition,
    query: ReuseQuery,
) -> CognitiveHint:
    """Safe full-scan/tag baseline with no graph, index, mutation or action selection."""
    if not isinstance(cognition, PersistentCognition) or not isinstance(query, ReuseQuery):
        raise ExperienceRejected("typed existing Memory owner and query required")
    matched: list[tuple[Memory, SourceEpisode]] = []
    stale = False
    unverified = False
    examined = 0
    for memory in cognition.memories:
        examined += 1
        try:
            episode = _decode(memory)
        except ExperienceRejected:
            return CognitiveHint(ReuseStatus.UNKNOWN, examined=examined,
                                 reason="invalid_retained_episode")
        if episode is None or episode.session_id != query.session_id:
            continue
        if not set(episode.cue_tags).issubset(query.cue_tags):
            continue
        if (episode.world_revision > query.world_revision
                or query.world_revision - episode.world_revision > query.max_revision_lag):
            stale = True
            continue
        if episode.evidence_sha256 not in query.admitted_evidence_sha256:
            unverified = True
            continue
        matched.append((memory, episode))
    if not matched:
        status = (ReuseStatus.UNVERIFIED if unverified else
                  ReuseStatus.STALE if stale else ReuseStatus.UNKNOWN)
        return CognitiveHint(status, examined=examined, reason="no_admitted_matching_episode")
    ids = tuple(sorted(memory.memory_id for memory, _ in matched))
    observed = [e for _, e in matched
                if e.disposition is ActionOutcomeDisposition.OUTCOME]
    # For the same source cue/action, inconsistent terminal meanings prohibit recall.
    grouped: dict[tuple[str, tuple[str, ...]], set[tuple[str, str]]] = {}
    for item in observed:
        grouped.setdefault((item.action_ref, item.cue_tags), set()).add(
            (item.source_status, item.reason_code)
        )
    if any(len(v) > 1 for v in grouped.values()):
        return CognitiveHint(ReuseStatus.CONTRADICTORY, ids, examined=examined,
                             reason="conflicting_observed_outcomes")
    if len(observed) != len(matched):
        return CognitiveHint(ReuseStatus.RECONSIDER, ids, examined=examined,
                             reason="unknown_outcome_requires_reconsideration")
    return CognitiveHint(
        ReuseStatus.RECALL, ids,
        tuple(sorted({item.action_ref for item in observed})),
        examined=examined, reason="observation_only_not_goal_or_learning",
    )


def cheap_tag_baseline(cognition: PersistentCognition, query: ReuseQuery) -> CognitiveHint:
    """Source-matched cheapest comparator: identical full scan/tag data, no new algorithm.

    Keeping the strongest cheap control identical is intentional. There is no
    demonstrated indexed/graph/model gain to justify an extra cognitive owner.
    """
    return retrieve_experience(cognition, query)
