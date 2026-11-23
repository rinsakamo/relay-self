"""R1 Shadow: compare original Present with Schema CURRENT/accepted RECENT/Memory.

This opt-in, CPU read-only diagnostic is NOT installed in the original L1
prompt, scheduler, U31 S1/S2 motor or WAL path. It never adopts cognition,
issues a ticket, creates a store, or claims to authenticate a Native/Paper
producer. Only an original Owner-retained OPEN Question with an issuer-adopt
record is eligible as *subjective* RECENT, never as observed World truth.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from relay_self.exploration_continuity_dev import ExplorationContinuity, QuestionRecord
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    Recent3SelfView,
    RecentCognitionEntry,
    context_is_live,
    read_original_owner_current,
    retrieve_original_owner_memory,
)
from relay_self.three_self_present import EpistemicStatus, Lens, LensClaim


class R1ShadowStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    HOLD = "HOLD"


EXPECTED_SEMANTIC_DIFFERENCES = (
    "LEGACY_NATIVE_3SELF_OBSERVED_NOT_SCHEMA_CURRENT",
    "OWNER_QUESTION_IS_SUBJECTIVE_NOT_NATIVE_OBSERVATION",
    "RETRIEVED_MEMORY_REMAINS_REMEMBERED_APPLICABILITY_UNKNOWN",
)


@dataclass(frozen=True, slots=True)
class R1ShadowComparison:
    """Ephemeral result; diagnostics only, never a decision/admission token."""

    self_id: str
    status: R1ShadowStatus
    context: CognitiveContext | None
    mismatch_codes: tuple[str, ...]
    legacy_body_claim_count: int
    accepted_question_refs: tuple[str, ...]
    selected_memory_refs: tuple[str, ...]
    expected_differences: tuple[str, ...] = EXPECTED_SEMANTIC_DIFFERENCES
    l1_input_switched: bool = False
    physical_authorized: bool = False
    memory_adopted: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or not isinstance(self.status, R1ShadowStatus)
            or type(self.mismatch_codes) is not tuple
            or any(type(s) is not str or not s for s in self.mismatch_codes)
            or type(self.legacy_body_claim_count) is not int
            or self.legacy_body_claim_count < 0
            or type(self.accepted_question_refs) is not tuple
            or type(self.selected_memory_refs) is not tuple
            or self.expected_differences != EXPECTED_SEMANTIC_DIFFERENCES
            or self.l1_input_switched is not False
            or self.physical_authorized is not False
            or self.memory_adopted is not False
            or (self.status is R1ShadowStatus.MATCH and (
                self.context is None or self.mismatch_codes
            ))
            or (self.status is not R1ShadowStatus.MATCH and not self.mismatch_codes)
        ):
            raise ValueError("R1 Shadow cannot act as a cognition/physical admission")


def _hold(self_id: str, reason: str) -> R1ShadowComparison:
    return R1ShadowComparison(
        self_id if self_id in ("A", "B") else "A",
        R1ShadowStatus.HOLD, None, (reason,), 0, (), (),
    )


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate original issuer adoption key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonfinite original issuer adoption value")


def _accepted_original_questions(*, owner, current, limit: int) -> Recent3SelfView:
    """Project only original B persisted issuer-adopt Questions as hypotheses.

    An issuer-adopt *string* is not a portable GPU ticket or independent
    proof of original model execution. Never invent unretained L1 results,
    even if a caller passes a plausible cancelled/timeout/foreign receipt.
    """
    continuity = owner.retained.exploration_continuity
    if continuity is None:
        return Recent3SelfView(current.scope.self_id, current.owner_epoch)
    if (
        type(continuity) is not ExplorationContinuity
        or continuity.self_id != current.scope.self_id
        or any(q.open and q.question_ref not in owner.pending_questions
               for q in continuity.questions)
    ):
        raise ValueError("original Question continuity and owner pending refs differ")
    selected: list[QuestionRecord] = []
    for question in continuity.questions:
        if not question.open or question.origin.source != "issuer-adopt":
            continue  # coverage-only proposals and declined/held work are not RECENT
        claim = json.loads(
            question.origin.reference,
            object_pairs_hook=_unique_pairs, parse_constant=_reject_constant,
        )
        if (
            type(claim) is not dict or set(claim) != {
                "work_ref", "request_id", "choice_id",
            } or claim["choice_id"] != "1"
            or any(type(claim[k]) is not str or not claim[k]
                   for k in ("work_ref", "request_id"))
        ):
            raise ValueError("retained issuer-adopt Question is not a valid OPEN acceptance")
        selected.append(question)
    entries = tuple(
        RecentCognitionEntry(
            current.scope.self_id, current.owner_epoch,
            f"owner-question:{question.question_ref}", 0, Lens.MYSELF,
            LensClaim(
                current.scope, Lens.MYSELF,
                f"accepted-open-question:{question.question_ref}",
                EpistemicStatus.HYPOTHETICAL, (question.origin,),
                value_ref=question.question_ref,
            ),
        )
        for question in selected[-limit:]
    )
    return Recent3SelfView(current.scope.self_id, current.owner_epoch, entries)


def compare_original_owner_r1_shadow(
    *, bridge, boot, world, links, self_id: str,
    memory_ids: tuple[str, ...] = (),
    recent_limit: int = 8,
) -> R1ShadowComparison:
    """One bounded original-B owner lock and non-mutating Stage28 comparison.

    Original reJOIN has a different Composite source: no old boot/links
    substitution is permitted. A caller must supply the actual original
    Stage28 source and can only *read* a qualified result.
    """
    if type(self_id) is not str or self_id not in ("A", "B"):
        return _hold("A", "FOREIGN_SELF")
    if (
        type(memory_ids) is not tuple or len(set(memory_ids)) != len(memory_ids)
        or any(type(m) is not str or not m for m in memory_ids)
        or type(recent_limit) is not int or not 1 <= recent_limit <= 16
    ):
        return _hold(self_id, "INVALID_SHADOW_SELECTOR")
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    if (
        resident is None or not isinstance(owners, dict)
        or not isinstance(getattr(resident, "owners", None), dict)
        or owners.get(self_id) is None or owners[self_id] is not resident.owners.get(self_id)
    ):
        return _hold(self_id, "FOREIGN_OR_ABSENT_ORIGINAL_OWNER")

    with resident.lock:
        try:
            owner = owners[self_id]
            # Check that RECENT/RETRIEVED came from the *same persisted* original
            # cognition, never caller-provided L2 results or a second DB.
            retained = owner.retained
            if load_persistent_cognition(owner.files.cognition_file) != retained:
                raise ValueError("original retained cognition does not match canonical file")
            legacy = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            current = read_original_owner_current(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, signals=legacy.present.signals,
            )
            recent = _accepted_original_questions(
                owner=owner, current=current, limit=recent_limit,
            )
            retrieved = retrieve_original_owner_memory(
                bridge=bridge, boot=boot, world=world, links=links,
                current=current, memory_ids=memory_ids,
            )
            context = CognitiveContext(current, recent=recent, retrieved=retrieved)
            mismatches = []
            if legacy.source != current.source:
                mismatches.append("LEGACY_SOURCE_DIFFERS_FROM_R1_CURRENT")
            if legacy.schema != current.schema:
                mismatches.append("LEGACY_SCHEMA_DIFFERS_FROM_R1_CURRENT")
            if legacy.present.three_self.scope != current.scope:
                mismatches.append("LEGACY_SELF_OR_WORLD_SCOPE_MISMATCH")
            if legacy.present.three_self.source_revision_refs != current.source_revision_refs:
                mismatches.append("LEGACY_NATIVE_PAPER_REVISION_MISMATCH")
            if legacy.present.frame_revision != current.owner_epoch:
                mismatches.append("LEGACY_OWNER_EPOCH_MISMATCH")
            if legacy.present.registry_revision != current.schema.revision:
                mismatches.append("LEGACY_REGISTRY_REVISION_MISMATCH")
            if legacy.present.signals != current.signals:
                mismatches.append("LEGACY_SCHEMA_SIGNAL_MISMATCH")
            if legacy.present.need_refs != current.need_refs:
                mismatches.append("LEGACY_NEED_REFERENCE_MISMATCH")
            if legacy.present.attention_refs != current.attention_refs:
                mismatches.append("LEGACY_ATTENTION_REFERENCE_MISMATCH")
            # Expected: legacy 3Self can have original OBSERVED Body claims.
            # Those observations are not copied into schema CURRENT/RECENT.
            if any(
                e.claim.status is EpistemicStatus.OBSERVED
                for e in recent.entries
            ):
                mismatches.append("RECENT_WORLD_TRUTH_PROMOTION")
            if (
                current.coverage is not EpistemicStatus.UNKNOWN
                or any(ref.status is not EpistemicStatus.REMEMBERED
                       or ref.applicability != "UNKNOWN"
                       for ref in retrieved.references)
            ):
                mismatches.append("UNSUPPORTED_MEMORY_OR_WORLD_PROMOTION")

            # Paper is outside the Python lock; a second original legacy read
            # and R0 source recheck refuse drift without freezing real World.
            after = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            if after != legacy:
                mismatches.append("LEGACY_PRESENT_CHANGED_DURING_SHADOW")
            if owner is not owners.get(self_id) or owner is not resident.owners.get(self_id):
                mismatches.append("ORIGINAL_OWNER_REPLACED_DURING_SHADOW")
            if owner.retained != retained:
                mismatches.append("ORIGINAL_RETAINED_COGNITION_CHANGED")
            if not context_is_live(
                context, bridge=bridge, boot=boot, world=world, links=links,
            ):
                mismatches.append("SHADOW_CURRENT_OR_MEMORY_SOURCE_STALE")
            return R1ShadowComparison(
                self_id,
                R1ShadowStatus.MISMATCH if mismatches else R1ShadowStatus.MATCH,
                context, tuple(mismatches),
                len(legacy.present.three_self.self_body.claims),
                tuple(e.claim.value_ref for e in recent.entries),
                tuple(r.memory_id for r in retrieved.references),
            )
        except (RuntimeError, ValueError, TypeError, AttributeError, KeyError, OSError):
            return _hold(self_id, "UNQUALIFIED_OR_CHANGED_ORIGINAL_SOURCE")
