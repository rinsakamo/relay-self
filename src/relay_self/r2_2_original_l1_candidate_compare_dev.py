"""R2-2: opt-in, non-issuing comparison of the ORIGINAL Stage28 L1 request.

The existing I/B CoverageAdoptionTurn owns the *actual* frozen L1 request.
R2-1's Owner Context is compared with that original request's qualified
Source/Need, not used to rebuild a different prompt or select a model choice.
First-login Stage28 only; U31 post-reJOIN/S2 is explicitly NOT qualified.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.bd1b_coverage_adoption_turn_dev import CHOICES
from relay_self.i_unified_b_exploration_dev import (
    IUnifiedExplorationTurn,
    verify_i_unified_exploration_turn,
)
from relay_self.r1_owner_context_shadow_dev import R1ShadowStatus, r1_shadow_is_live
from relay_self.three_self_present import EpistemicStatus


class R22CandidateContextHold(RuntimeError):
    """Original frozen L1 request or new read-only Context is not coherent."""


@dataclass(frozen=True, slots=True)
class R22CandidateContextComparison:
    """Diagnostics only: never an L1 ticket, prompt replacement or admission."""

    self_id: str
    original_request_id: str
    original_question_ref: str
    original_choice_ids: tuple[str, ...]
    current_source_revision_refs: tuple[str, ...]
    original_need_signal_ref: str
    current_owner_epoch: int
    original_request_unchanged: bool = True
    context_matches_original_l1_source: bool = True
    model_invoked: bool = False
    l1_input_switched: bool = False
    question_adopted: bool = False
    memory_written: bool = False
    action_issue_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.self_id not in ("A", "B")
            or not self.original_request_id or not self.original_question_ref
            or not self.original_choice_ids or not self.current_source_revision_refs
            or not self.original_need_signal_ref
            or type(self.current_owner_epoch) is not int
            or self.current_owner_epoch != 1
            or self.original_request_unchanged is not True
            or self.context_matches_original_l1_source is not True
            or any((self.model_invoked, self.l1_input_switched,
                    self.question_adopted, self.memory_written,
                    self.action_issue_authorized))
        ):
            raise R22CandidateContextHold("Context comparison cannot authorize L1/physical")


def compare_r2_2_original_l1_candidate_context(
    *, bridge, boot, world, links, receipt: IUnifiedExplorationTurn,
) -> R22CandidateContextComparison:
    """Read existing original L1 choices and compare to Owner's R2-1 Context.

    Never calls prepare_coverage_adoption_turn, a new L1 request generator,
    the inference lane, a GPU ticket, an issuer, or any persistent writer.
    A previously original-registered IUnifiedExplorationTurn is mandatory.
    """
    if type(receipt) is not IUnifiedExplorationTurn:
        raise R22CandidateContextHold("original registered I/B L1 turn required")
    resident = getattr(bridge, "cognitive_work", None)
    owners = getattr(bridge, "owners", None)
    sid = receipt.self_id
    if (
        resident is None or not isinstance(owners, dict)
        or owners.get(sid) is None
        or getattr(resident, "owners", {}).get(sid) is not owners[sid]
        or receipt.original_owner is not owners[sid]
    ):
        raise R22CandidateContextHold("second or missing Original Owner")
    with resident.lock:
        try:
            verify_i_unified_exploration_turn(
                receipt=receipt, bridge=bridge, boot=boot, world=world, links=links,
            )
            turn = receipt.original_turn
            original_request = turn.request
            report = resident.read_context_shadow_cpu(
                bridge=bridge, boot=boot, world=world, links=links, self_id=sid,
                memory_ids=(), recent_limit=8,
            )
            if report.status is not R1ShadowStatus.MATCH or report.context is None:
                raise R22CandidateContextHold("R2-1 Context Shadow is not MATCH")
            current = report.context.current
            if (
                current != receipt.context.current
                or current.owner_epoch != 1
                or current.source != turn.source
                or current.source_revision_refs != turn.inquiry.source_revision_refs
                or current.owner_epoch != turn.owner_scope[0]
                or current.schema.revision != turn.inquiry.schema_revision
                or current.scope.self_id != sid
                or current.coverage is not EpistemicStatus.UNKNOWN
                or len(current.signals) != 1
                or current.signals[0].signal_kind != "EXPLORATION_NEED"
                or current.signals[0].envelope.event_id != turn.inquiry.need_signal_ref
                or original_request.choices != CHOICES
                or original_request.focus != turn.inquiry.question_ref
                or original_request.think_allowed
                or original_request.identity_context is None
                or receipt.question_adopted or receipt.memory_writer
                or receipt.physical_issue_authorized
            ):
                raise R22CandidateContextHold(
                    "original L1 choices/Need/Source differ from R2-1 Context"
                )
            # Paper is external to the resident lock. Re-validate *both*
            # original request and read-only R1 Context before returning.
            verify_i_unified_exploration_turn(
                receipt=receipt, bridge=bridge, boot=boot, world=world, links=links,
            )
            if (
                turn.request is not original_request
                or not r1_shadow_is_live(
                    report, bridge=bridge, boot=boot, world=world, links=links,
                )
                or owners.get(sid) is not receipt.original_owner
            ):
                raise R22CandidateContextHold("original request or Context became stale")
            return R22CandidateContextComparison(
                self_id=sid,
                original_request_id=original_request.request_id,
                original_question_ref=turn.inquiry.question_ref,
                original_choice_ids=tuple(c.choice_id for c in original_request.choices),
                current_source_revision_refs=current.source_revision_refs,
                original_need_signal_ref=turn.inquiry.need_signal_ref,
                current_owner_epoch=current.owner_epoch,
            )
        except (RuntimeError, ValueError, KeyError, AttributeError, TypeError) as exc:
            raise R22CandidateContextHold(
                "original L1 request and R2-1 Context not simultaneously qualified"
            ) from exc
