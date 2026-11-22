"""B-origin I2 ingress for unified I (DEV read-only).

This is a source/identity fence, NOT a second cognitive owner, L1 issuer,
physical lease, checkpoint, Memory writer, Q auditor, or S2 qualification.
E2 stream continuity must be separately attested before real admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from relay_self.bd1b_owner_source_dev import BD1bOwnerSource
from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    I2OriginalGoalHandoff,
    prepare_i2_original_goal_handoff,
    verify_i2_original_goal_handoff,
)
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    context_is_live,
    read_original_owner_current,
)


class IUnifiedSourceHold(RuntimeError):
    """Reject a stale, foreign or unqualified shared B/I2 original source."""


def _same_original_source(
    source: BD1bOwnerSource, handoff: I2OriginalGoalHandoff, self_id: str,
) -> bool:
    """Bind original owner session/epoch; later I2 SENSE has its own seq/request.

    The bounded I2 request validates its later source separately. The initial
    B login probe and later qualified SENSE are never asserted identical.
    """
    return (
        source.self_id == self_id == handoff.self_id
        and source.native_session_id == handoff.native_session_id
        and source.paper_session_id == handoff.paper_session_id
        and source.paper_log_sha256 == handoff.paper_log_sha256
        and source.resident_epoch == handoff.resident_epoch
    )


@dataclass(frozen=True, slots=True)
class IUnifiedOriginalIngress:
    """Ephemeral, explicitly non-authorizing, same-owner readout."""

    self_id: str
    original_owner: Any
    context: CognitiveContext
    handoff: I2OriginalGoalHandoff
    physical_authorized: bool = False
    memory_adopted: bool = False
    s2_replay_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or type(self.context) is not CognitiveContext
            or type(self.handoff) is not I2OriginalGoalHandoff
            or self.context.current.scope.self_id != self.self_id
            or not _same_original_source(self.context.current.source, self.handoff, self.self_id)
            or self.context.current.source_revision_refs != self.handoff.source_revision_refs
            or self.physical_authorized or self.memory_adopted or self.s2_replay_authorized
        ):
            raise IUnifiedSourceHold("original B / I2 admission mismatch")


def _owner(bridge: Any, sid: str) -> Any:
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    if (
        sid not in ("A", "B") or resident is None or not isinstance(owners, dict)
        or not isinstance(getattr(resident, "owners", None), dict)
        or owners.get(sid) is None
        or owners.get(sid) is not resident.owners.get(sid)
    ):
        raise IUnifiedSourceHold("only the live B original cognitive owner qualifies")
    return owners[sid]


def prepare_i_unified_original_ingress(
    *, bridge: Any, boot: Any, world: Any, links: Any, self_id: str,
    i2b_read_attached_lane: bool = False,
) -> IUnifiedOriginalIngress:
    """Read original B Schema CURRENT and I2 candidate without adoption.

    The two independent reads are reconciled and rechecked, since Paper may
    advance outside the B lock. No model, Memory or physical API is called.
    """
    try:
        owner = _owner(bridge, self_id)
        context = CognitiveContext(read_original_owner_current(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        ))
        handoff = prepare_i2_original_goal_handoff(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        receipt = IUnifiedOriginalIngress(self_id, owner, context, handoff)
        verify_i_unified_original_ingress(
            receipt=receipt, bridge=bridge, boot=boot, world=world, links=links,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        return receipt
    except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise IUnifiedSourceHold("shared original B/I2 CURRENT unqualified") from exc


def verify_i_unified_original_ingress(
    *, receipt: IUnifiedOriginalIngress, bridge: Any, boot: Any,
    world: Any, links: Any, i2b_read_attached_lane: bool = False,
) -> None:
    """Fail closed on altered source, epoch, owner pointer or bounded request."""
    if type(receipt) is not IUnifiedOriginalIngress:
        raise IUnifiedSourceHold("typed original ingress required")
    try:
        if _owner(bridge, receipt.self_id) is not receipt.original_owner:
            raise IUnifiedSourceHold("original B owner changed")
        if not context_is_live(
            receipt.context, bridge=bridge, boot=boot, world=world, links=links,
        ):
            raise IUnifiedSourceHold("R0 CURRENT source is stale")
        current = read_original_owner_current(
            bridge=bridge, boot=boot, world=world, links=links,
            self_id=receipt.self_id,
        )
        if current != receipt.context.current:
            raise IUnifiedSourceHold("R0 CURRENT changed")
        verify_i2_original_goal_handoff(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=receipt.handoff,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        if not _same_original_source(
            current.source, receipt.handoff, receipt.self_id,
        ):
            raise IUnifiedSourceHold("I2 and B describe different source")
        if current.source_revision_refs != receipt.handoff.source_revision_refs:
            raise IUnifiedSourceHold("I2 and B source revisions differ")
    except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise IUnifiedSourceHold("shared original B/I2 readback unqualified") from exc
