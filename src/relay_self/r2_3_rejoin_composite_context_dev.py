"""R2-3a: opt-in read-only CURRENT for the ORIGINAL first A reJOIN / continuing B.

Never reinterpret R1 Stage28's two refs as a post-reJOIN source. The original
resident source reader owns Native/Paper/Composite qualification; this module
only projects Schema CURRENT from that qualified Present and detects drift.
It is not a product L1 input, GPU/Physical permit, Memory writer or scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeSourceReceipt
from relay_self.b_np1b_rejoin_composite_source_dev import RejoinedCompositeSourceReceipt
from relay_self.b_np1b_rejoin_present_dev import RejoinedOwnerSource
from relay_self.bd1b_owner_present_dev import BD1bOwnerPresent
from relay_self.common_io import ScopeRef
from relay_self.innate_schema import CognitiveSignal, SchemaSnapshot, signal_is_current
from relay_self.three_self_present import EpistemicStatus


class R23CompositeContextHold(RuntimeError):
    """Original first reJOIN source/current Owner is missing or changed."""


@dataclass(frozen=True, slots=True)
class R23RejoinedCurrent:
    """One frozen Schema CURRENT, without any Native OBSERVED lens claims."""

    self_id: str
    source: RejoinedOwnerSource
    schema: SchemaSnapshot
    signals: tuple[CognitiveSignal, ...]
    source_revision_refs: tuple[str, str, str]
    need_refs: tuple[str, ...]
    attention_refs: tuple[str, ...]
    coverage: EpistemicStatus = EpistemicStatus.UNKNOWN

    @property
    def scope(self) -> ScopeRef:
        return ScopeRef(self.self_id, self.source.paper_session_id)

    @property
    def owner_epoch(self) -> int:
        return self.source.resident_epoch

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.source) is not RejoinedOwnerSource
            or not isinstance(self.schema, SchemaSnapshot)
            or self.source.self_id != self.self_id
            or self.schema.self_id != self.self_id
            or type(self.signals) is not tuple
            or any(type(s) is not CognitiveSignal for s in self.signals)
            or type(self.source_revision_refs) is not tuple
            or len(self.source_revision_refs) != 3
            or type(self.need_refs) is not tuple
            or type(self.attention_refs) is not tuple
            or self.coverage is not EpistemicStatus.UNKNOWN
        ):
            raise R23CompositeContextHold("typed original composite Schema CURRENT required")
        composite = self.source.composite_receipt
        if self.self_id == "A":
            valid_composite = type(composite) is RejoinedCompositeSourceReceipt
        else:
            valid_composite = type(composite) is ContinuingCompositeSourceReceipt
        expected = (
            f"native:{self.source.native_session_id}:{self.source.native_probe_ref}:"
            f"{self.source.native_probe_seq}:{self.source.native_probe_source_ref}",
            f"paper:{self.source.paper_session_id}:{self.source.paper_boot_id}:"
            f"{self.source.paper_log_sha256}:{self.source.paper_tick_source_ref}",
            f"composite:rejoin:{composite.composite_revision}",
        )
        if (
            not valid_composite
            or self.source_revision_refs != expected
            or self.source.resident_epoch != composite.resident_epoch
            or self.source.native_session_id != composite.native_session_id
            or self.source.native_probe_ref != composite.native_request_id
            or self.source.native_probe_seq != composite.native_sequence
            or self.source.native_probe_source_ref != composite.native_source_ref
            or self.source.paper_session_id != composite.paper_session_id
            or self.source.paper_log_sha256 != composite.paper_log_sha256
            or self.source.paper_tick_source_ref != composite.paper_tick_ref
            or len({s.envelope.event_id for s in self.signals}) != len(self.signals)
            or any(
                not signal_is_current(
                    signal, snapshot=self.schema, scope=self.scope,
                    source_revision_refs=self.source_revision_refs,
                    requested_mode=signal.execution_mode,
                    current_registry_revision=self.schema.revision,
                )
                for signal in self.signals
            )
            or not set(self.need_refs).issubset(
                {s.envelope.event_id for s in self.signals}
            )
            or not set(self.attention_refs).issubset(
                {s.envelope.event_id for s in self.signals}
            )
        ):
            raise R23CompositeContextHold("reJOIN provenance or Schema signal mismatch")


@dataclass(frozen=True, slots=True)
class R23RejoinedContextComparison:
    """Diagnostic bound to the original Owner *object*, not an authority token."""

    self_id: str
    original_owner: object
    current: R23RejoinedCurrent
    model_invoked: bool = False
    l1_input_switched: bool = False
    memory_adopted: bool = False
    physical_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.current) is not R23RejoinedCurrent
            or self.current.self_id != self.self_id
            or self.model_invoked is not False
            or self.l1_input_switched is not False
            or self.memory_adopted is not False
            or self.physical_authorized is not False
        ):
            raise R23CompositeContextHold("reJOIN context cannot be an L1 admission")


def read_r23_original_rejoin_context(
    *, bridge, self_id: str, initial_receipts, historical_composite,
) -> R23RejoinedContextComparison:
    """Compare the existing original reJOIN Present with a Schema-only CURRENT.

    This qualifies ONLY the first A reJOIN + B continuing-session source
    family; second reJOIN has a separately owned verifier and stays HOLD.
    """
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    if (
        self_id not in ("A", "B") or type(self_id) is not str
        or resident is None or not isinstance(owners, dict)
        or not isinstance(getattr(resident, "owners", None), dict)
        or owners.get(self_id) is None
        or owners[self_id] is not resident.owners.get(self_id)
    ):
        raise R23CompositeContextHold("original A/B resident Owner required")
    with resident.lock:
        if getattr(resident, "_normal_second_rejoin_cut", None) is not None:
            raise R23CompositeContextHold("second reJOIN has different source qualification")
        try:
            owner = owners[self_id]
            params = dict(
                bridge=bridge, self_id=self_id, initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )
            before = resident.read_present_cpu(**params)
            if type(before) is not BD1bOwnerPresent:
                raise R23CompositeContextHold("original typed Present required")
            source = before.source
            if type(source) is not RejoinedOwnerSource:
                raise R23CompositeContextHold("Stage28 source is not a reJOIN composite")
            current = R23RejoinedCurrent(
                self_id=self_id, source=source, schema=before.schema,
                signals=before.present.signals,
                source_revision_refs=before.present.three_self.source_revision_refs,
                need_refs=before.present.need_refs,
                attention_refs=before.present.attention_refs,
            )
            if (
                owner.retained.identity.self_id != self_id
                or owner.pattern_registry.revision != current.schema.revision
                or resident.present_schema(self_id) != current.schema
                or resident.current_scope(self_id) != (
                    source.resident_epoch, source.native_session_id, source.world_epoch,
                )
                or before.present.three_self.scope != current.scope
                or before.present.frame_revision != current.owner_epoch
                or before.present.registry_revision != current.schema.revision
                or getattr(resident, "_normal_second_rejoin_cut", None) is not None
            ):
                raise R23CompositeContextHold("original Owner epoch / Schema changed")
            after = resident.read_present_cpu(**params)
            if (
                after != before or owner is not owners.get(self_id)
                or owner is not resident.owners.get(self_id)
                or resident.current_scope(self_id) != (
                    current.owner_epoch, source.native_session_id, source.world_epoch,
                )
            ):
                raise R23CompositeContextHold("Native/Paper/Original Owner changed during read")
            return R23RejoinedContextComparison(self_id, owner, current)
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            raise R23CompositeContextHold("original reJOIN current source unqualified") from exc


def r23_rejoined_context_is_live(
    report: R23RejoinedContextComparison, *,
    bridge, initial_receipts, historical_composite,
) -> bool:
    """Re-read original Native/Paper/Composite and Owner. No cached admission."""
    if type(report) is not R23RejoinedContextComparison:
        return False
    try:
        fresh = read_r23_original_rejoin_context(
            bridge=bridge, self_id=report.self_id,
            initial_receipts=initial_receipts,
            historical_composite=historical_composite,
        )
        return (
            fresh.original_owner is report.original_owner
            and fresh.current == report.current
        )
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError):
        return False
