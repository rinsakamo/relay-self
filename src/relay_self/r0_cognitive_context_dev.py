"""R0 only: read-only owner-qualified context vocabulary (#1117, #833 §15).

No product L1/L2 prompt routing, Recent adoption, persistence, GPU admission or
physical execution. A Python dataclass is not a native/Paper authentication
receipt. All live reads must be rechecked against the original B owner.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from relay_self.bd1b_owner_source_dev import BD1bOwnerSource, build_bd1b_owner_source
from relay_self.common_io import (
    CognitiveTask,
    CognitionResultReceipt,
    PreemptionTrace,
    Profile,
    ProfileDecision,
    ScopeRef,
    result_is_current,
)
from relay_self.innate_schema import CognitiveSignal, SchemaSnapshot, signal_is_current
from relay_self.persistent_cognition import Memory
from relay_self.three_self_present import EpistemicStatus, Lens, LensClaim


class R0ContextHold(ValueError):
    """The owner/source/epistemic preconditions have not been demonstrated."""


def _source_refs(source: BD1bOwnerSource) -> tuple[str, str]:
    return (
        f"native:{source.native_session_id}:{source.native_probe_ref}:{source.native_probe_seq}:{source.native_probe_source_ref}",
        f"paper:{source.paper_session_id}:{source.paper_boot_id}:{source.paper_log_sha256}:{source.paper_tick_source_ref}",
    )


@dataclass(frozen=True, slots=True)
class CurrentSchemaFrame:
    """CURRENT: Schema output, never native facts copied through 3Self."""

    scope: ScopeRef
    source: BD1bOwnerSource
    schema: SchemaSnapshot
    signals: tuple[CognitiveSignal, ...] = ()
    coverage: EpistemicStatus = EpistemicStatus.UNKNOWN
    attention_refs: tuple[str, ...] = ()
    need_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, BD1bOwnerSource) or not isinstance(self.scope, ScopeRef):
            raise R0ContextHold("typed original owner source and scope required")
        if self.scope != ScopeRef(self.source.self_id, self.source.paper_session_id):
            raise R0ContextHold("foreign source scope")
        if not isinstance(self.schema, SchemaSnapshot) or self.schema.self_id != self.scope.self_id:
            raise R0ContextHold("foreign schema")
        if self.coverage is not EpistemicStatus.UNKNOWN:
            raise R0ContextHold("R0 cannot attest complete or partial coverage from native")
        if type(self.signals) is not tuple or any(type(s) is not CognitiveSignal for s in self.signals):
            raise R0ContextHold("CURRENT accepts Schema signals only, not raw World/LensClaim")
        if len({s.envelope.event_id for s in self.signals}) != len(self.signals):
            raise R0ContextHold("duplicate Schema signal")
        refs = _source_refs(self.source)
        for signal in self.signals:
            if (
                not signal_is_current(
                    signal, snapshot=self.schema, scope=self.scope,
                    source_revision_refs=refs, requested_mode=signal.execution_mode,
                    current_registry_revision=self.schema.revision,
                )
                or not signal.envelope.source_refs
            ):
                raise R0ContextHold("unqualified Schema signal")
        # R0 cannot invent Attention or Need references not issued by a Schema.
        available = {s.envelope.event_id for s in self.signals}
        if (
            type(self.need_refs) is not tuple or type(self.attention_refs) is not tuple
            or not set(self.need_refs).issubset(available)
            or not set(self.attention_refs).issubset(available)
        ):
            raise R0ContextHold("Need/Attention must reference eligible Schema signals")

    @property
    def source_revision_refs(self) -> tuple[str, str]:
        return _source_refs(self.source)

    @property
    def owner_epoch(self) -> int:
        return self.source.resident_epoch


@dataclass(frozen=True, slots=True)
class RecentCognitionEntry:
    """Historical subjective lens reference, not a new source of World truth.

    In R0 these are *input contract examples only*: only a future original
    Owner adoption interface can authoritatively append accepted episodes.
    """

    self_id: str
    owner_epoch: int
    task_ref: str
    generation: int
    lens: Lens
    claim: LensClaim

    def __post_init__(self) -> None:
        if (
            not self.self_id or type(self.owner_epoch) is not int or self.owner_epoch < 0
            or not self.task_ref or type(self.generation) is not int or self.generation < 0
            or not isinstance(self.lens, Lens) or not isinstance(self.claim, LensClaim)
            or self.claim.scope.self_id != self.self_id or self.claim.lens is not self.lens
            or self.claim.status is EpistemicStatus.OBSERVED
        ):
            raise R0ContextHold("RECENT is bounded subjective cognition, never OBSERVED")


@dataclass(frozen=True, slots=True)
class Recent3SelfView:
    """Single-Self bounded view; absent lenses remain absent, not refreshed."""

    self_id: str
    owner_epoch: int
    entries: tuple[RecentCognitionEntry, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.self_id or type(self.owner_epoch) is not int or self.owner_epoch < 0
            or type(self.entries) is not tuple
            or any(not isinstance(e, RecentCognitionEntry)
                   or e.self_id != self.self_id or e.owner_epoch != self.owner_epoch
                   for e in self.entries)
        ):
            raise R0ContextHold("foreign/old epoch or malformed recent entry")
        keys = [(e.task_ref, e.generation, e.lens, e.claim.claim_key) for e in self.entries]
        if len(keys) != len(set(keys)):
            raise R0ContextHold("duplicate RECENT cognitive entry")


def recent_result_eligible(
    *,
    result: CognitionResultReceipt,
    task: CognitiveTask,
    decision: ProfileDecision,
    current: CurrentSchemaFrame,
    now_ns: int,
    compute_admitted: bool,
    expected_gpu_ticket_ref: str | None,
    actual_gpu_ticket_ref: str | None,
    preemption: PreemptionTrace | None = None,
) -> bool:
    """Only a pre-adoption negative-control check; NEVER appends to RECENT.

    No caller-supplied ticket strings can prove original GPU admission or
    accepted Owner cognition. R1 needs a real typed B receipt before append.
    """
    if (
        task.requirement.value == "FAST_REACTION"
        or decision.selected not in (Profile.L1, Profile.L2)
        or not expected_gpu_ticket_ref or actual_gpu_ticket_ref != expected_gpu_ticket_ref
        or not compute_admitted
    ):
        return False
    return result_is_current(
        result, task, decision, scope=current.scope,
        current_source_revision_refs=current.source_revision_refs,
        now_ns=now_ns, compute_admitted=compute_admitted, preemption=preemption,
    )


def _memory_digest(memory: Memory) -> str:
    return hashlib.sha256(json.dumps(
        (
            memory.memory_id, memory.content,
            (memory.source_provenance.source, memory.source_provenance.reference),
            (memory.integration_provenance.source, memory.integration_provenance.reference),
        ), ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrievedMemoryRef:
    """Reference to the existing owner Memory, never a copied Memory record."""

    memory_id: str
    revision_sha256: str
    status: EpistemicStatus = EpistemicStatus.REMEMBERED
    applicability: str = "UNKNOWN"
    counterexample_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.memory_id or len(self.revision_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.revision_sha256)
            or self.status is not EpistemicStatus.REMEMBERED
            or self.applicability != "UNKNOWN"
            or type(self.counterexample_refs) is not tuple
            or any(type(x) is not str or not x for x in self.counterexample_refs)
        ):
            raise R0ContextHold("retrieval cannot establish current applicability")


@dataclass(frozen=True, slots=True)
class RetrievedMemoryBundle:
    self_id: str
    owner_epoch: int
    query_need_refs: tuple[str, ...]
    references: tuple[RetrievedMemoryRef, ...]

    def __post_init__(self) -> None:
        if (
            not self.self_id or type(self.owner_epoch) is not int or self.owner_epoch < 0
            or type(self.query_need_refs) is not tuple
            or type(self.references) is not tuple
            or any(not isinstance(ref, RetrievedMemoryRef) for ref in self.references)
            or len({r.memory_id for r in self.references}) != len(self.references)
        ):
            raise R0ContextHold("malformed retrieval")


@dataclass(frozen=True, slots=True)
class CognitiveContext:
    current: CurrentSchemaFrame
    recent: Recent3SelfView | None = None
    retrieved: RetrievedMemoryBundle | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.current, CurrentSchemaFrame):
            raise R0ContextHold("Schema CURRENT required")
        for view in (self.recent, self.retrieved):
            if view is not None and (
                view.self_id != self.current.scope.self_id
                or view.owner_epoch != self.current.owner_epoch
            ):
                raise R0ContextHold("foreign or retired original owner epoch")


def read_original_owner_current(*, bridge, boot, world, links, self_id, signals=()):
    """R0 CPU read: B's original source reader + resident schema; NO 3Self path.

    External Paper can advance outside the resident lock, so reread immediately
    before returning; consumers MUST revalidate before using the result.
    """
    from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError

    resident = bridge.cognitive_work
    if resident is None or bridge.owners.get(self_id) is not resident.owners.get(self_id):
        raise R0ContextHold("original resident bridge required")
    with resident.lock:
        source = build_bd1b_owner_source(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        try:
            schema = resident.present_schema(self_id)
            scope = resident.current_scope(self_id)
        except ResidentCognitiveWorkError as exc:
            raise R0ContextHold("original owner unavailable") from exc
        owner = bridge.owners[self_id]
        if (
            scope != (source.resident_epoch, source.native_session_id, source.world_epoch)
            or owner.pattern_registry.revision != schema.revision
            or owner.retained.identity.self_id != self_id
        ):
            raise R0ContextHold("original epoch / registry mismatch")
        frame = CurrentSchemaFrame(
            ScopeRef(self_id, source.paper_session_id), source, schema, tuple(signals),
        )
        if (
            build_bd1b_owner_source(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            ) != source
            or resident.present_schema(self_id) != schema
            or resident.current_scope(self_id) != scope
        ):
            raise R0ContextHold("source changed while constructing CURRENT")
        return frame


def retrieve_original_owner_memory(*, bridge, boot, world, links, current, memory_ids=()):
    """Read digest pointers under the original lock; no new DB or C2 adoption."""
    if type(memory_ids) is not tuple or len(set(memory_ids)) != len(memory_ids):
        raise R0ContextHold("duplicate/invalid memory selector")
    resident = bridge.cognitive_work
    if resident is None:
        raise R0ContextHold("original owner unavailable")
    with resident.lock:
        if not context_is_live(
            CognitiveContext(current), bridge=bridge, boot=boot,
            world=world, links=links,
        ):
            raise R0ContextHold("expired original current source")
        memories = {m.memory_id: m for m in bridge.owners[current.scope.self_id].retained.memories}
        if any(i not in memories for i in memory_ids):
            raise R0ContextHold("memory is not accepted in original owner")
        refs = tuple(RetrievedMemoryRef(i, _memory_digest(memories[i])) for i in memory_ids)
        return RetrievedMemoryBundle(
            current.scope.self_id, current.owner_epoch, current.need_refs, refs,
        )


def context_is_live(context: CognitiveContext, *, bridge, boot, world, links) -> bool:
    """Revalidate against original source, epoch, schema and Memory CAS snapshot."""
    if not isinstance(context, CognitiveContext):
        return False
    resident = bridge.cognitive_work
    sid = context.current.scope.self_id
    if resident is None or bridge.owners.get(sid) is not resident.owners.get(sid):
        return False
    with resident.lock:
        try:
            fresh = read_original_owner_current(
                bridge=bridge, boot=boot, world=world, links=links, self_id=sid,
                signals=context.current.signals,
            )
            if fresh != context.current:
                return False
            if context.retrieved is not None:
                originals = {m.memory_id: m for m in bridge.owners[sid].retained.memories}
                for item in context.retrieved.references:
                    original = originals.get(item.memory_id)
                    if original is None or _memory_digest(original) != item.revision_sha256:
                        return False
            return True
        except (R0ContextHold, ValueError, RuntimeError, AttributeError, TypeError, KeyError):
            return False
