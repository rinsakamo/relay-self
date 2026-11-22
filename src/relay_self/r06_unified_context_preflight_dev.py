"""R0.6 unified B/I read-only CURRENT compatibility audit (CPU/DEV only).

Requires the original B resident and the I unified *reader* already at one
commit. No I question candidate is registered; no L1 issuer, Memory, WAL,
World, GPU, Physical, or R1 shadow is run. All real-source gates stay HOLD.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.i_unified_original_context_dev import read_i_unified_b_current
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    context_is_live,
    read_original_owner_current,
)
from relay_self.r05_context_compat_preflight_dev import audit_r05_initial_owner_context
from relay_self.three_self_present import EpistemicStatus

R06_EXTERNAL_HOLDS = (
    "Q_INDEPENDENT_ORIGINAL_SOURCE_NOT_ATTESTED",
    "B_SCHEMA3_ORIGINAL_PRODUCER_AUTHENTICATION_NOT_ATTESTED",
    "ORIGINAL_REJOIN_COMPOSITE_NOT_QUALIFIED_FOR_R0_CURRENT",
    "C_I_E_AND_SCHEMA3_COMBINED_REGRESSION_NOT_ATTESTED",
    "I4A_S1_S2_WAL_CUSTODY_NOT_AUTHENTICATED",
    "R1_SHADOW_NOT_AUTHORIZED",
)


@dataclass(frozen=True, slots=True)
class R06UnifiedCurrentAudit:
    """Evidence of a *bounded* CPU comparison, not an admission ticket."""

    self_id: str
    r05_stage28_aligned: bool
    unified_b_i_current_aligned: bool
    schema_signal_refs: tuple[str, ...]
    source_revision_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    r1_shadow_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.r05_stage28_aligned) is not bool
            or type(self.unified_b_i_current_aligned) is not bool
            or (self.unified_b_i_current_aligned and not self.r05_stage28_aligned)
            or type(self.schema_signal_refs) is not tuple
            or any(type(v) is not str or not v for v in self.schema_signal_refs)
            or type(self.source_revision_refs) is not tuple
            or any(type(v) is not str or not v for v in self.source_revision_refs)
            or type(self.blockers) is not tuple
            or not set(R06_EXTERNAL_HOLDS).issubset(self.blockers)
            or self.r1_shadow_allowed is not False
        ):
            raise ValueError("R0.6 cannot manufacture a B/I qualification or R1 permit")


def _hold(self_id: str, problem: str) -> R06UnifiedCurrentAudit:
    return R06UnifiedCurrentAudit(
        self_id if self_id in ("A", "B") else "A",
        False, False, (), (), (problem, *R06_EXTERNAL_HOLDS),
    )


def audit_r06_unified_b_i_current(*, bridge, boot, world, links, self_id):
    """Check the real *existing* B/I unified readers against the legacy B view.

    This is initial-Stage28 only. It intentionally does not call I's
    prepare_i_unified_exploration_turn or issue_i_unified_question_once;
    the former registers a B turn, and the latter can issue GPU/adopt. Both
    are outside a mutation-free context readout and R0.6 scope.
    """
    if self_id not in ("A", "B") or type(self_id) is not str:
        return _hold("A", "FOREIGN_OR_INVALID_SELF")
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    if (
        resident is None or not isinstance(owners, dict)
        or not isinstance(getattr(resident, "owners", None), dict)
        or owners.get(self_id) is None
        or owners[self_id] is not resident.owners.get(self_id)
    ):
        return _hold(self_id, "ORIGINAL_B_OWNER_IDENTITY_HOLD")

    with resident.lock:
        first = audit_r05_initial_owner_context(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        if not first.stage28_source_aligned:
            return _hold(self_id, "ORIGINAL_STAGE28_R05_HOLD")
        try:
            receipt = read_i_unified_b_current(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            legacy = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            signal = legacy.exploration_need.signal if legacy.exploration_need else None
            signals = (signal,) if signal is not None else ()
            current = read_original_owner_current(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, signals=signals,
            )
            unified = receipt.context.current
            same = (
                receipt.original_owner is owners[self_id]
                and receipt.original_owner is resident.owners[self_id]
                and receipt.self_id == self_id
                and receipt.physical_authorized is False
                and receipt.memory_adopted is False
                and legacy.source == current.source == unified.source
                and legacy.schema == current.schema == unified.schema
                and legacy.present.three_self.scope == current.scope == unified.scope
                and legacy.present.three_self.source_revision_refs
                == current.source_revision_refs == unified.source_revision_refs
                and current.signals == signals
                and unified.signals == ()
                and current.coverage is EpistemicStatus.UNKNOWN
                and unified.coverage is EpistemicStatus.UNKNOWN
                and context_is_live(
                    CognitiveContext(current),
                    bridge=bridge, boot=boot, world=world, links=links,
                )
                and context_is_live(
                    receipt.context,
                    bridge=bridge, boot=boot, world=world, links=links,
                )
            )
            # Repeat the first-owner and I read before reporting; neither
            # read establishes an atomic, authenticated real Native/Paper
            # custody boundary.
            last = read_i_unified_b_current(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            final = audit_r05_initial_owner_context(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            same = (
                same and last.context == receipt.context
                and last.original_owner is receipt.original_owner
                and final == first
                and owners[self_id] is receipt.original_owner
            )
            if not same:
                return _hold(self_id, "B_I_UNIFIED_CONTEXT_SOURCE_DIVERGED")
            return R06UnifiedCurrentAudit(
                self_id, True, True,
                tuple(s.envelope.event_id for s in signals),
                current.source_revision_refs,
                R06_EXTERNAL_HOLDS,
            )
        except (RuntimeError, ValueError, TypeError, AttributeError, KeyError, OSError):
            return _hold(self_id, "B_I_UNIFIED_CURRENT_UNQUALIFIED")
