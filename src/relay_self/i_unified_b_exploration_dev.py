"""Unified I U1: original B Schema CURRENT -> original B bounded L1 Question path.

This adapts I2's exploration *purpose* to B's current source/Schema3 APIs.
It deliberately does not call obsolete I2 shadow Source, mint an L1 ticket,
adopt an Intent, touch Memory, or issue an Action. B's original adoption turn,
GPU lane, issuer and persistence authority are reused unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from relay_self.bd1b_coverage_adoption_turn_dev import (
    CHOICES,
    CoverageAdoptionTurn,
    prepare_coverage_adoption_turn,
    validate_coverage_adoption_turn_cpu,
)
from relay_self.bd1b_original_issuer_once_dev import (
    OriginalAdoptionOutcome,
    issue_original_adoption_once,
)
from relay_self.i_unified_original_context_dev import IUnifiedSourceHold, _owner
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    context_is_live,
    read_original_owner_current,
)


class IUnifiedExplorationHold(IUnifiedSourceHold):
    """Original B exploration/source/Question candidate cannot be admitted."""


@dataclass(frozen=True, slots=True)
class IUnifiedExplorationTurn:
    """Immutable I2->B bridge; B's registered turn remains the only issuer input."""

    self_id: str
    original_owner: Any
    context: CognitiveContext
    original_turn: CoverageAdoptionTurn
    question_adopted: bool = False
    physical_issue_authorized: bool = False
    memory_writer: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.context) is not CognitiveContext
            or type(self.original_turn) is not CoverageAdoptionTurn
            or self.original_owner is not self.original_turn.owner
            or self.original_turn.self_id != self.self_id
            or self.context.current.scope.self_id != self.self_id
            or self.context.current.source != self.original_turn.source
            or self.context.current.owner_epoch != self.original_turn.owner_scope[0]
            or self.context.current.schema.revision != self.original_turn.inquiry.schema_revision
            or self.context.current.source_revision_refs
            != self.original_turn.inquiry.source_revision_refs
            or len(self.context.current.signals) != 1
            or self.context.current.signals[0].signal_kind != "EXPLORATION_NEED"
            or self.context.current.signals[0].envelope.event_id
            != self.original_turn.inquiry.need_signal_ref
            or self.original_turn.request.choices != CHOICES
            or self.original_turn.request.focus != self.original_turn.inquiry.question_ref
            or self.original_turn.request.think_allowed
            or self.question_adopted or self.physical_issue_authorized or self.memory_writer
        ):
            raise IUnifiedExplorationHold("unqualified original B exploration L1 binding")


def _qualified_present(*, bridge, boot, world, links, self_id, current):
    """Re-read actual B Present; old 3Self projection is not a second CURRENT."""
    present = bridge.cognitive_work.read_present_cpu(
        bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
    )
    need = present.exploration_need
    if (
        need is None
        or present.source != current.source
        or present.schema != current.schema
        or present.present.three_self.source_revision_refs != current.source_revision_refs
        or (need.signal,) != current.signals
        or need.signal.signal_kind != "EXPLORATION_NEED"
        or need.signal.source_revision_refs != current.source_revision_refs
    ):
        raise IUnifiedExplorationHold("original CURRENT exploration Need not qualified")
    return present


def prepare_i_unified_exploration_turn(
    *, bridge: Any, boot: Any, world: Any, links: Any, self_id: str,
) -> IUnifiedExplorationTurn:
    """Issue *no* L1 request. Freeze and pair R0 CURRENT with B's real turn."""
    try:
        owner = _owner(bridge, self_id)
        resident = bridge.cognitive_work
        with resident.lock:
            present = resident.read_present_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            if present.exploration_need is None:
                raise IUnifiedExplorationHold("unregistered/unknown exploration stays absent")
            current = read_original_owner_current(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
                signals=(present.exploration_need.signal,),
            )
            _qualified_present(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=self_id, current=current,
            )
            turn = prepare_coverage_adoption_turn(
                bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            )
            receipt = IUnifiedExplorationTurn(
                self_id, owner, CognitiveContext(current), turn,
            )
            verify_i_unified_exploration_turn(
                receipt=receipt, bridge=bridge, boot=boot, world=world, links=links,
            )
            return receipt
    except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise IUnifiedExplorationHold("B original exploration turn unqualified") from exc


def verify_i_unified_exploration_turn(
    *, receipt: IUnifiedExplorationTurn, bridge: Any,
    boot: Any, world: Any, links: Any,
) -> None:
    """After source/epoch change no ticket may be issued for this original turn."""
    if type(receipt) is not IUnifiedExplorationTurn:
        raise IUnifiedExplorationHold("exact original B turn required")
    try:
        owner = _owner(bridge, receipt.self_id)
        with bridge.cognitive_work.lock:
            if owner is not receipt.original_owner or not context_is_live(
                receipt.context, bridge=bridge, boot=boot, world=world, links=links,
            ):
                raise IUnifiedExplorationHold("B Owner or R0 CURRENT retired/stale")
            _qualified_present(
                bridge=bridge, boot=boot, world=world, links=links,
                self_id=receipt.self_id, current=receipt.context.current,
            )
            validate_coverage_adoption_turn_cpu(
                bridge=bridge, boot=boot, world=world, links=links,
                turn=receipt.original_turn,
            )
            if receipt.original_turn.owner is not owner:
                raise IUnifiedExplorationHold("B registered turn bound to foreign Owner")
    except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise IUnifiedExplorationHold("B original exploration result stale") from exc


async def issue_i_unified_question_once(
    *, receipt: IUnifiedExplorationTurn, bridge: Any, boot: Any,
    world: Any, links: Any, lane: Any, timeout_s: float = 60.0,
) -> OriginalAdoptionOutcome:
    """Delegate exactly once to B's registered original GPU issuer/ADOPT authority.

    Only B may commit an OPEN Question; HOLD/DECLINE/UNRESOLVED are valid.
    No I-owned Memory, Goal, Intent, Skill, Action or physical authorization.
    """
    if type(receipt) is not IUnifiedExplorationTurn:
        raise IUnifiedExplorationHold("exact original turn required")
    verify_i_unified_exploration_turn(
        receipt=receipt, bridge=bridge, boot=boot, world=world, links=links,
    )
    # B locks, requalifies and submits atomically, and fences on uncertainty.
    return await issue_original_adoption_once(
        bridge=bridge, boot=boot, world=world, links=links, lane=lane,
        turn=receipt.original_turn, timeout_s=timeout_s,
    )
