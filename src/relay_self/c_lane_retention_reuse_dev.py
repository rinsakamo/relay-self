"""C Lane C1-R/C3 original-owner DEV adapter (CPU/offline only).

Reuses B's CheckpointedCognitiveOwner and PersistentCognition, C's bounded
SkillRun assessment, and the original physical journal. A caller-supplied WAL
pin is a consistency fence, NOT proof of an independently authenticated source
or of an actual Self decision. No new store, scheduler or physical authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_learning_contract import (
    ConditionalReuseCandidate,
    CurrentCue,
    OutcomeAssessment,
    RetainedRevisionRead,
    ReuseStage,
    assess_conditional_reuse,
)
from relay_self.cognitive_learning_owner_adapter import (
    BoundedSkillExperience,
    BoundedSkillRead,
    WalDisposition,
    assemble_bounded_skill_experience,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentEvent, IntentEventKind
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, CognitionDatum


class C1RetentionHold(RuntimeError):
    """Owner, source, historical receipt, or durable state was not qualified."""


_TERMINAL = frozenset({
    IntentEventKind.COMPLETED, IntentEventKind.FAILED,
    IntentEventKind.INVALIDATED, IntentEventKind.RECONSIDERED_RELEASE,
})
_KIND = "C1_ORIGINAL_INTENT_V1"


@dataclass(frozen=True, slots=True)
class OriginalWalPrefixPin:
    """Previously retained by the original issuer; NOT a self-authenticating pin."""

    row_count: int
    prefix_digest: str
    # Preserve earlier receipt out-of-band for a rehash attack to be detected.
    producer_ref: str


@dataclass(frozen=True, slots=True)
class OriginalIntentExperience:
    """One parent attempted Intent with all of its bounded child SkillRuns."""

    episode_key: tuple[str, str, str]
    world_id: str
    skill_runs: tuple[BoundedSkillExperience, ...]
    action_ids: tuple[str, ...]
    wal_statuses: tuple[str, ...]
    target_outcome: OutcomeAssessment
    owner_retained: PersistentCognition
    intent_events: tuple[IntentEvent, ...]
    wal_digest: str
    source_prefix_digest: str

    @property
    def memory_id(self) -> str:
        encoded = json.dumps(self.episode_key, separators=(",", ":"))
        return "c1-intent:" + hashlib.sha256(encoded.encode()).hexdigest()


def _canonical_payload(memory: Memory) -> dict:
    """Reject malformed/foreign memory rather than trusting an arbitrary JSON string."""
    try:
        value = json.loads(memory.content)
        if type(value) is not dict or set(value) != {
            "kind", "episode_key", "world_id", "skill_runs", "action_ids",
            "wal_statuses",
            "target_outcome", "wal_digest", "source_prefix_digest",
        } or value["kind"] != _KIND:
            raise ValueError("C1 record schema")
        key = value["episode_key"]
        if (type(key) is not list or len(key) != 3
                or any(type(x) is not str or not x for x in key)
                or not isinstance(value["world_id"], str) or not value["world_id"]
                or not isinstance(value["skill_runs"], list) or not value["skill_runs"]
                or not isinstance(value["action_ids"], list) or not value["action_ids"]
                or len(set(value["action_ids"])) != len(value["action_ids"])
                or type(value["wal_statuses"]) is not list
                or len(value["wal_statuses"]) != len(value["action_ids"])
                or any(type(status) is not str or not status.startswith("NATIVE_")
                       for status in value["wal_statuses"])
                or any(type(x) is not str or not x for x in value["action_ids"])
                or value["target_outcome"] not in OutcomeAssessment._value2member_map_
                or any(type(value[k]) is not str or len(value[k]) != 64
                       or any(ch not in "0123456789abcdef" for ch in value[k])
                       for k in ("wal_digest", "source_prefix_digest"))):
            raise ValueError("C1 record lineage")
        identifier = "c1-intent:" + hashlib.sha256(
            json.dumps(key, separators=(",", ":")).encode()
        ).hexdigest()
        if memory.memory_id != identifier:
            raise ValueError("C1 record identity")
        return value
    except (TypeError, ValueError, KeyError) as exc:
        raise C1RetentionHold("untrusted retained C1 record") from exc


def assemble_original_intent(
    owner: CheckpointedCognitiveOwner,
    reads: tuple[BoundedSkillRead, ...],
    *,
    prefix_pin: OriginalWalPrefixPin,
) -> OriginalIntentExperience:
    """Read original owner and full canonical WAL; no memory mutation.

    The prefix pin must have been independently held BEFORE any later WAL
    modification. Comparing recomputed checksums alone does not authenticate it.
    """
    if (not isinstance(owner, CheckpointedCognitiveOwner)
            or owner.cohort is None or not isinstance(reads, tuple)
            or not reads or not isinstance(prefix_pin, OriginalWalPrefixPin)
            or type(prefix_pin.row_count) is not int or prefix_pin.row_count < 1
            or type(prefix_pin.producer_ref) is not str or not prefix_pin.producer_ref):
        raise C1RetentionHold("original Owner/earlier WAL witness required")
    with owner.cohort.lock:
        owner._eligible()
        first = reads[0]
        if (not isinstance(first, BoundedSkillRead)
                or first.scope.self_id != owner.self_id
                or first.scope.world_session_id != owner.native_session_id
                or first.world_id != owner.cohort.world_id
                or first.intent is not owner.intent
                or first.cognition is not owner.retained):
            raise C1RetentionHold("original Self/session/Intent/Memory revision mismatch")
        intent_id = first.skill.intent_id
        relevant = tuple(e for e in owner.intent.events if e.intent_id == intent_id)
        if (sum(e.kind is IntentEventKind.COMMITTED for e in relevant) != 1
                or len([e for e in relevant if e.kind in _TERMINAL]) != 1
                or relevant[-1].kind not in _TERMINAL):
            raise C1RetentionHold("attempted parent Intent has no final original terminal")
        expected_runs = {k for k, skill in owner.skills.items() if skill.intent_id == intent_id}
        if not expected_runs or len(expected_runs) != len(reads):
            raise C1RetentionHold("missing/duplicate original child SkillRun")
        episodes: list[BoundedSkillExperience] = []
        for read in reads:
            if (not isinstance(read, BoundedSkillRead)
                    or read.intent is not owner.intent or read.cognition is not owner.retained
                    or read.scope != first.scope or read.world_id != first.world_id
                    or read.skill.intent_id != intent_id
                    or read.skill is not owner.skills.get(read.skill.execution_id)):
                raise C1RetentionHold("foreign or stale child readout")
            episode = assemble_bounded_skill_experience(read)
            if episode is None:
                raise C1RetentionHold("unattempted, unfinished or unresolved SkillRun")
            episodes.append(episode)
        if {e.skill_execution_id for e in episodes} != expected_runs:
            raise C1RetentionHold("original Intent children not exhaustively represented")
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        if (prefix_pin.row_count > len(journal.records)
                or journal.certified_prefix_digest(prefix_pin.row_count)
                != prefix_pin.prefix_digest):
            raise C1RetentionHold("historical owner-held WAL prefix changed")
        own_rows = tuple(row for row in journal.records if row["intent_id"] == intent_id)
        action_ids = tuple(a for e in episodes for a in e.action_ids)
        if (not action_ids or len(set(action_ids)) != len(action_ids)
                or len(own_rows) != len(action_ids)
                or {row["action_id"] for row in own_rows} != set(action_ids)):
            raise C1RetentionHold("original Intent physical Action aggregation mismatch")
        reads_by_id = {
            wal.action_id: wal for read in reads for wal in read.wal
        }
        for row in own_rows:
            receipt = reads_by_id[row["action_id"]]
            if (row["session_id"] != first.scope.world_session_id
                    or row["skill_execution_id"] not in expected_runs
                    or receipt.digest_sha256 != journal.digest
                    or row["status"] == "PREPARED_UNRESOLVED"
                    or receipt.disposition is WalDisposition.PREPARED_UNRESOLVED):
                raise C1RetentionHold("physical WAL session, issuer or outcome changed")
        outcomes = {e.target_outcome for e in episodes}
        # A single unknown child cannot be promoted to an observed partial result.
        outcome = (
            OutcomeAssessment.UNKNOWN if OutcomeAssessment.UNKNOWN in outcomes
            else outcomes.pop() if len(outcomes) == 1
            else OutcomeAssessment.PARTIAL
        )
        statuses = {row["action_id"]: row["status"] for row in own_rows}
        return OriginalIntentExperience(
            (owner.self_id, owner.native_session_id, intent_id),
            first.world_id, tuple(episodes), action_ids,
            tuple(statuses[action_id] for action_id in action_ids), outcome,
            owner.retained, owner.intent.events,
            journal.digest, prefix_pin.prefix_digest,
        )


def propose_intent_memory(experience: OriginalIntentExperience, *,
                          integration_provenance: Provenance) -> Memory:
    """Convert a source-qualified C1 readout to existing B-owned Memory."""
    if not isinstance(experience, OriginalIntentExperience):
        raise C1RetentionHold("typed Intent experience required")
    if not isinstance(integration_provenance, Provenance):
        raise C1RetentionHold("explicit original Owner review provenance required")
    payload = {
        "kind": _KIND, "episode_key": list(experience.episode_key),
        "world_id": experience.world_id,
        "skill_runs": [
            {"skill_execution_id": e.skill_execution_id, "skill_id": e.skill_id,
             "target_ref": e.target_ref, "goal_ref": e.goal_ref,
             "before_epoch": e.epoch_start, "after_epoch": e.epoch_end,
             "action_ids": list(e.action_ids),
             "action_states": [a.value for a in e.action_states],
             "target_outcome": e.target_outcome.value,
             "evidence_refs": [[p.source, p.reference] for p in e.evidence_refs]}
            for e in experience.skill_runs
        ],
        "action_ids": list(experience.action_ids),
        "wal_statuses": list(experience.wal_statuses),
        "target_outcome": experience.target_outcome.value,
        "wal_digest": experience.wal_digest,
        "source_prefix_digest": experience.source_prefix_digest,
    }
    return Memory(
        experience.memory_id, json.dumps(payload, sort_keys=True, separators=(",", ":")),
        experience.skill_runs[0].before.source_refs[0], integration_provenance,
    )


def retain_original_intent_memory(owner: CheckpointedCognitiveOwner,
                                  experience: OriginalIntentExperience,
                                  memory: Memory) -> None:
    """Synchronous original-cohort write/readback; fail-closed on uncertain disk.

    This proves CPU/offline consistency, not a genuine Self adoption decision.
    The B/I owner must supply that decision and independently anchored sources.
    """
    if not isinstance(owner, CheckpointedCognitiveOwner) or owner.cohort is None:
        raise C1RetentionHold("original cohort owner required")
    with owner.cohort.lock:
        owner._eligible()
        if isinstance(memory, Memory) and any(
            m.memory_id == memory.memory_id for m in owner.retained.memories
        ):
            raise C1RetentionHold("duplicate original Intent adoption")
        if (not isinstance(experience, OriginalIntentExperience)
                or not isinstance(memory, Memory)
                or experience.episode_key[0] != owner.self_id
                or experience.episode_key[1] != owner.native_session_id
                or experience.world_id != owner.cohort.world_id
                or experience.owner_retained is not owner.retained
                or experience.intent_events != owner.intent.events
                or any(owner.skills.get(run.skill_execution_id) is None
                       for run in experience.skill_runs)
                or experience.memory_id != memory.memory_id
                or _canonical_payload(memory)["episode_key"] != list(experience.episode_key)
                or memory != propose_intent_memory(
                    experience, integration_provenance=memory.integration_provenance,
                )):
            raise C1RetentionHold("foreign or altered C1 Memory")
        if any(m.memory_id == memory.memory_id for m in owner.retained.memories):
            raise C1RetentionHold("duplicate original Intent adoption")
        # Admission must not race a later S2 WAL write, including a rehashed row.
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        journal.require_clear()
        current_rows = tuple(row for row in journal.records
                             if row["intent_id"] == experience.episode_key[2])
        if (journal.digest != experience.wal_digest
                or {row["action_id"] for row in current_rows}
                != set(experience.action_ids)
                or tuple(next(row["status"] for row in current_rows
                              if row["action_id"] == action_id)
                         for action_id in experience.action_ids)
                != experience.wal_statuses):
            raise C1RetentionHold("original physical WAL changed after C1 evaluation")
        path = owner.files.cognition_file
        # Original owner has the only durable cognition path; no C-side DB.
        if path.exists() and load_persistent_cognition(path) != owner.retained:
            owner.cohort.hold = True
            raise C1RetentionHold("original cognition file diverged: Owner quarantined")
        try:
            owner.retain_memory(memory)
            save_persistent_cognition(path, owner.retained)
            if load_persistent_cognition(path) != owner.retained:
                raise C1RetentionHold("original Memory write/readback mismatch")
        except BaseException:
            owner.cohort.hold = True
            raise



def assemble_quiescent_original_intent(
    owner: CheckpointedCognitiveOwner,
    reads: tuple[BoundedSkillRead, ...],
    *,
    physical: PhysicalIssueAdmission,
    prefix_pin: OriginalWalPrefixPin,
) -> OriginalIntentExperience:
    """Original Owner -> physical issuer -> WAL readout, no parallel issuer.

    A local quiescence window is not evidence of independent Native/Paper
    authentication. The original I/B/Q source qualifications remain required.
    """
    if (not isinstance(owner, CheckpointedCognitiveOwner)
            or owner.cohort is None
            or not isinstance(physical, PhysicalIssueAdmission)):
        raise C1RetentionHold("original physical issuer required for C1 read")
    with owner.cohort.lock:
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id, native_session_id=owner.native_session_id,
            ):
                return assemble_original_intent(owner, reads, prefix_pin=prefix_pin)
        except PhysicalIssueFenceError as exc:
            raise C1RetentionHold("original physical issuer not quiescent") from exc


def retain_quiescent_original_intent_memory(
    owner: CheckpointedCognitiveOwner,
    experience: OriginalIntentExperience,
    memory: Memory,
    *,
    physical: PhysicalIssueAdmission,
    reads: tuple[BoundedSkillRead, ...],
    prefix_pin: OriginalWalPrefixPin,
) -> None:
    """Reassemble C1 under the original Owner + issuer lock before Memory save.

    A caller-built C1 dataclass is never itself an admission token. Source
    validation and the existing B save/readback share the same quiescence
    window; unguarded external writers/real Self acceptance remain separate.
    """
    if (not isinstance(owner, CheckpointedCognitiveOwner)
            or owner.cohort is None
            or not isinstance(physical, PhysicalIssueAdmission)):
        raise C1RetentionHold("original physical issuer required for C1 retention")
    with owner.cohort.lock:
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id, native_session_id=owner.native_session_id,
            ):
                verified = assemble_original_intent(
                    owner, reads, prefix_pin=prefix_pin,
                )
                if verified != experience:
                    raise C1RetentionHold(
                        "C1 candidate differs from freshly qualified original readout"
                    )
                retain_original_intent_memory(owner, experience, memory)
        except PhysicalIssueFenceError as exc:
            raise C1RetentionHold("original physical issuer not quiescent") from exc


def c3_next_epoch_read(
    cognition: PersistentCognition,
    *,
    candidate: ConditionalReuseCandidate,
    current_scope: ScopeRef,
    current_world_id: str,
    current_source_revision_refs: tuple[str, ...],
    cues: tuple[CurrentCue, ...],
    choice_set: tuple[BoundedChoice, ...],
    retained: RetainedRevisionRead | None = None,
    current_owner_revision: int | None = None,
    viability_confirmed: bool = False,
    cost_budget_ns: int = 0,
    contradictions: tuple[str, ...] = (),
) -> tuple[tuple[BoundedChoice, ...], CognitionDatum | None, str]:
    """Historical episode is read-only; fresh cues must be independently supplied."""
    if not isinstance(cognition, PersistentCognition) or (
        cognition.identity.self_id != current_scope.self_id
    ):
        raise C1RetentionHold("foreign original Memory owner")
    if not isinstance(choice_set, tuple) or not all(
        isinstance(c, BoundedChoice) for c in choice_set
    ):
        raise C1RetentionHold("prebound original L1 choice set required")
    memories = tuple(m for m in cognition.memories if m.memory_id.startswith("c1-intent:"))
    matching = []
    for mem in memories:
        payload = _canonical_payload(mem)
        if payload["episode_key"][0] != current_scope.self_id:
            raise C1RetentionHold("foreign Self memory embedded in original cognition")
        if tuple(payload["episode_key"]) == candidate.proposal.episode_key:
            matching.append(payload)
    if len(matching) != 1:
        return choice_set, None, "MISSING_OR_DUPLICATE_C1"
    if matching[0]["world_id"] != current_world_id:
        return choice_set, None, "WORLD_MISMATCH"
    if matching[0]["target_outcome"] != OutcomeAssessment.SUCCESS.value:
        return choice_set, None, "HISTORICAL_RESULT_NOT_SUCCESS"
    if candidate.proposal.counterexample_refs:
        return choice_set, None, "KNOWN_COUNTEREXAMPLE_NOT_RECONCILED"
    # Old session is only a historical provenance key; NEVER current World fact.
    result = assess_conditional_reuse(
        candidate, retained=retained,
        current_owner_revision=current_owner_revision,
        current_scope=current_scope,
        current_source_revision_refs=current_source_revision_refs,
        cues=cues, allow_l1_reuse=True,
        viability_confirmed=viability_confirmed,
        cost_budget_ns=cost_budget_ns,
        current_contradiction_refs=contradictions,
    )
    if result.stage is ReuseStage.ABSTAIN:
        return choice_set, None, result.reason
    datum = CognitionDatum.from_value(
        "c3_historical_intent_read_only",
        {"memory_id": "c1-intent:" + hashlib.sha256(json.dumps(
            list(candidate.proposal.episode_key), separators=(",", ":")
        ).encode()).hexdigest(),
         "historical_session": candidate.proposal.episode_key[1],
         "current_session": current_scope.world_session_id,
         "stage": result.stage.value, "choice_ids": [c.choice_id for c in choice_set],
         "world_id": current_world_id},
        candidate.provenance,
    )
    return choice_set, datum, result.reason
