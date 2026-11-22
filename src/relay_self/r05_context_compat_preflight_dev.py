"""R0.5 read-only initial-Source comparison against B's original Present.

DEV/offline diagnostics only. Never starts an R1 shadow, changes the CPU/GPU
scheduler, imports a second owner, or accepts independently unauthenticated
Paper/Native/Q evidence. B reJOIN needs a distinct later source contract.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    context_is_live,
    read_original_owner_current,
)

# No "Q passed" boolean is accepted from an untrusted caller here. Only Q's
# independently anchored, exact-head real source review can retire this gate.
R1_EXTERNAL_HOLDS = (
    "B_I_SAME_HEAD_NOT_ATTESTED",
    "Q_INDEPENDENT_OWNER_SOURCE_NOT_ATTESTED",
    "SCHEMA3_REJOIN_C_I_REGRESSION_NOT_ATTESTED",
    "R1_SHADOW_NOT_AUTHORIZED",
)


@dataclass(frozen=True, slots=True)
class R05CompatibilityAudit:
    """Non-authoritative R0.5 Stage28 comparison, never a shadow permit."""

    self_id: str
    stage28_source_aligned: bool
    schema_signal_count: int
    blockers: tuple[str, ...]
    r1_shadow_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            not self.self_id
            or type(self.stage28_source_aligned) is not bool
            or type(self.schema_signal_count) is not int
            or self.schema_signal_count < 0
            or type(self.blockers) is not tuple
            or not all(type(b) is str and b for b in self.blockers)
            or self.r1_shadow_allowed is not False
            or not set(R1_EXTERNAL_HOLDS).issubset(self.blockers)
        ):
            raise ValueError("R0.5 diagnostics cannot grant R1 shadow admission")


def _hold(self_id: str, problem: str) -> R05CompatibilityAudit:
    return R05CompatibilityAudit(
        self_id or "UNKNOWN", False, 0, (problem, *R1_EXTERNAL_HOLDS),
    )


def audit_r05_initial_owner_context(*, bridge, boot, world, links, self_id):
    """Compare legacy owner Present and R0 schema-only CURRENT under B's lock.

    Only the original Stage28 initial source is supported. Rejoined sources
    are deliberately not adapted with old boot/links, because reJOIN adds a
    distinct composite revision and A/B generation qualification.
    The result stays HOLD even when the synthetic CPU comparison is green.
    """
    if type(self_id) is not str or not self_id:
        return _hold("UNKNOWN", "INVALID_SELF")
    resident = getattr(bridge, "cognitive_work", None)
    if (
        resident is None
        or bridge.owners.get(self_id) is not resident.owners.get(self_id)
    ):
        return _hold(self_id, "FOREIGN_OR_MISSING_ORIGINAL_OWNER")

    with resident.lock:
        try:
            before = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id,
            )
            signals = (
                (before.exploration_need.signal,)
                if before.exploration_need is not None else ()
            )
            current = read_original_owner_current(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, signals=signals,
            )
            legacy = before.present.three_self
            # These are identity/source checks only, NOT approval to move an
            # OBSERVED 3Self claim to schema-only CURRENT.
            same = (
                before.source == current.source
                and before.schema == current.schema
                and legacy.scope == current.scope
                and legacy.source_revision_refs == current.source_revision_refs
                and all(s in current.signals for s in signals)
                and current.coverage.value == "UNKNOWN"
                and context_is_live(
                    CognitiveContext(current),
                    bridge=bridge, boot=boot, world=world, links=links,
                )
            )
            # Re-read the original legacy source after CURRENT: detect drift
            # across the two comparison reads without treating them as atomic
            # Native/Paper producer captures.
            after = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id,
            )
            if not same or after != before:
                return _hold(self_id, "LEGACY_R0_SOURCE_OR_SCHEMA_MISMATCH")
            return R05CompatibilityAudit(
                self_id, True, len(current.signals), R1_EXTERNAL_HOLDS,
            )
        except (ValueError, RuntimeError, AttributeError, KeyError, TypeError, OSError):
            return _hold(self_id, "ORIGINAL_STAGE28_SOURCE_UNQUALIFIED")
