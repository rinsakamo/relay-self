"""D9 pre-retirement proof and original B Stage28b full typed source handoff.

No shadow Owner, no fake L1 selection, no fabricated source-world receipt.
The external B source producer may call this before/after REAL native retirement
and Paper stop; only original B Stage28b cut owns World/Paper/WAL.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relay_self.exploration_continuity_dev import AttemptPhase, open_question_refs
from relay_self.exploration_d9_original_l1_dev import D9OriginalL1Outcome
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    Stage28bRetiredCutResult,
    capture_retired_resident_typed_world,
)


class D9SourceCutHold(RuntimeError):
    """Original A/B L1 selection or typed World/Owner source is incomplete."""


@dataclass(frozen=True, slots=True)
class D9SourceSelectionReadback:
    self_id: str
    native_session_id: str
    open_question_refs: tuple[str, ...]
    genuine_attempt_refs: tuple[str, ...]
    l1_selected_status: str
    no_l2_post_attested: bool = False
    physical_action_issue_authorized: bool = False


def verify_d9_original_owner_sources(
    owners: dict, outcomes: tuple[D9OriginalL1Outcome, ...],
) -> tuple[D9SourceSelectionReadback, ...]:
    """Owner+disk equality, real L1 result semantics and no invented L2 ref."""
    from relay_self.checkpointed_cognitive_runtime_dev import (
        CheckpointedCognitiveOwner,
    )

    if (
        type(owners) is not dict or set(owners) != {"A", "B"}
        or type(outcomes) is not tuple or len(outcomes) != 2
        or {out.self_id for out in outcomes
            if isinstance(out, D9OriginalL1Outcome)} != {"A", "B"}
    ):
        raise D9SourceCutHold("two original A/B Self and completed L1 receipts required")
    by_self = {out.self_id: out for out in outcomes}
    readouts = []
    any_reserved = False
    for sid in ("A", "B"):
        owner = owners[sid]
        out = by_self[sid]
        if (
            not isinstance(owner, CheckpointedCognitiveOwner)
            or owner.self_id != sid
            or owner.native_session_id != out.old_native_session_id
            or not out.question_ref or not out.native_probe_request_id
            or not out.l1_request_id or not out.work_ref
            or not out.backend_ref
            or out.l1_model_invoked is not True
            or out.l2_model_invoked is not False
            or out.physical_action_issue_authorized is not False
            or out.selected_status not in ("DEFER", "ESCALATE_L2", "RECONSIDER")
            or owner.supervisor.open_actions
            or owner.files.cognition_file.is_symlink()
        ):
            raise D9SourceCutHold("original resident source not genuinely L1-only")
        try:
            PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=sid,
            ).require_clear()
            persisted = load_persistent_cognition(owner.files.cognition_file)
        except (RuntimeError, ValueError, OSError) as exc:
            raise D9SourceCutHold("original source cognition/WAL unreadable") from exc
        state = persisted.exploration_continuity
        if state is None or persisted != owner.retained:
            raise D9SourceCutHold("original D Question not canonically persisted")
        question_refs = open_question_refs(persisted, expected_self_id=sid)
        attempts = tuple(a.attempt_ref for a in state.attempts)
        if (
            out.question_ref not in question_refs
            or not set(question_refs).issubset(owner.pending_questions)
            or len({x.attempt_ref for x in state.attempts}) != len(state.attempts)
            or len(attempts) > 256
        ):
            raise D9SourceCutHold("original Source Question/attempt differs from Owner")
        if out.selected_status == "ESCALATE_L2":
            if (
                out.attempted_l2_ref is None
                or out.attempted_l2_ref not in attempts
                or not any(
                    x.attempt_ref == out.attempted_l2_ref
                    and x.phase is AttemptPhase.RESERVED
                    for x in state.attempts
                )
            ):
                raise D9SourceCutHold("model-selected L2 not durably RESERVED")
            any_reserved = True
        elif out.attempted_l2_ref is not None:
            raise D9SourceCutHold("DEFER/RECONSIDER may not invent L2 attempt")
        readouts.append(D9SourceSelectionReadback(
            sid, out.old_native_session_id, question_refs, attempts,
            out.selected_status,
        ))
    # Do NOT convert genuine two-Self DEFER into an artificial L2 reservation.
    # It is a valid observational outcome but does not qualify the D7
    # previous-reservation non-replay experiment.
    if not any_reserved:
        raise D9SourceCutHold(
            "both original Self legitimately deferred; D7 old-L2 trial is HOLD"
        )
    return tuple(readouts)


def capture_d9_retired_source(
    *, bridge, paper, store: Path, evidence_dir: Path,
    outcomes: tuple[D9OriginalL1Outcome, ...],
) -> Stage28bRetiredCutResult:
    """Same ORIGINAL B paper/native/owner/physical freeze with D source proof.

    Actual original B bridge owns the real native logout and physical
    quiescence. Its existing Stage28b source function is the ONLY source
    for stopping and saving Paper and typed World+Self+WAL.
    """
    from relay_self.owned_paper_world_dev import OwnedPaperWorld
    from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge

    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(paper, OwnedPaperWorld)
        or bridge.paper is not paper
        or bridge.sessions
        or not bridge.physical.all_residents_offline
        or type(store) is not Path or not store.is_dir()
        or type(evidence_dir) is not Path or not evidence_dir.is_dir()
    ):
        raise D9SourceCutHold("original World/Native owners not safely retired")
    records = verify_d9_original_owner_sources(bridge.owners, outcomes)
    # Stronger than a report: the B source-cut implementation checks original
    # physical quiescence and writes the same-generation typed Owner files.
    original = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence_dir,
    )
    cuts = verify_typed_generation(original.generation)
    if (
        tuple(c.self_id for c in cuts) != ("A", "B")
        or not original.actual_typed_owner_cut
        or original.physical_action_issue_authorized
        or original.automatic_l1_replay
        or any(
            c.former_native_session_id != r.native_session_id
            or not set(r.open_question_refs).issubset(c.pending_question_refs)
            for c, r in zip(cuts, records, strict=True)
        )
    ):
        raise D9SourceCutHold("B original typed cut no longer matches D journal")
    return original
