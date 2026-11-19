"""D7: strict READ-ONLY source gate for an actual D-owned A/B World DEV trial.

No local Paper/Gemma process is accessible from a GitHub-only assistant run.
This module therefore qualifies a *candidate* committed source, not live truth.
It refuses to relabel B's original real-world cut as a D exploration trial
unless BOTH Self own durable OPEN Questions and referenced L2 attempts in
the same, independently pinned Stage28 typed World/Self generation.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from relay_self.exploration_checkpoint_bridge_dev import inspect_d4_inert_recovery
from relay_self.exploration_continuity_dev import AttemptPhase
from relay_self.stage28c1_inert_restore_dev import inspect_stage28c_source


class D7RealWorldPreflightHold(RuntimeError):
    """Original full World/Self or durable D evidence is not qualified."""


@dataclass(frozen=True, slots=True)
class D7SelfSource:
    self_id: str
    question_refs: tuple[str, ...]
    attempt_refs: tuple[str, ...]
    prior_native_session_id: str
    attempts_reserved: int
    no_old_l2_replay_authorized: bool = True
    no_old_action_replay_authorized: bool = True


@dataclass(frozen=True, slots=True)
class D7SourceCandidate:
    """Not a live Paper receipt, GPU lease, or action permission."""

    generation_id: str
    world_id: str
    source_branch_id: str
    fork_branch_id: str
    committed_sha256: str
    owner_roster: tuple[str, ...]
    selves: tuple[D7SelfSource, ...]
    source_kind: str = "STRUCTURAL_TYPED_CUT_ONLY"
    real_world_attested: bool = False
    real_native_rejoin_attested: bool = False
    real_gemma_l1_attested: bool = False
    l2_dispatch_authorized: bool = False
    physical_action_issue_authorized: bool = False
    historical_action_or_l2_replay_authorized: bool = False


def inspect_d7_real_world_candidate(
    generation: Path,
    restored: Path,
    *,
    expected_world_id: str,
    expected_source_branch_id: str,
    expected_fork_branch_id: str,
    expected_committed_sha256: str,
    expected_generation_id: str,
) -> D7SourceCandidate:
    """Validate an *already existing* source; never start or create a World.

    Stage28 B owns World process/source/roster/WAL proof. D may only constrain
    the same cut with its original Self-owned Question/attempt history.
    """
    if not all(
        type(v) is str and 0 < len(v) <= 256
        for v in (
            expected_world_id, expected_source_branch_id,
            expected_fork_branch_id, expected_committed_sha256,
            expected_generation_id,
        )
    ):
        raise D7RealWorldPreflightHold("exact pinned World/branch/generation required")
    if (
        re.fullmatch(r"g-[0-9]{12}", expected_generation_id) is None
        or re.fullmatch(r"[0-9a-f]{64}", expected_committed_sha256) is None
    ):
        raise D7RealWorldPreflightHold("invalid immutable COMMITTED/generation pin")
    root, dest = Path(generation), Path(restored)
    if (
        root.is_symlink() or dest.is_symlink()
        or not root.is_dir() or not dest.is_dir()
        or root.name != expected_generation_id
        or root.resolve() == dest.resolve()
        or root.resolve() in dest.resolve().parents
        or dest.resolve() in root.resolve().parents
    ):
        raise D7RealWorldPreflightHold("distinct immutable archive and fork required")
    marker = root / "COMMITTED.json"
    try:
        if (
            marker.is_symlink() or not marker.is_file()
            or hashlib.sha256(marker.read_bytes()).hexdigest()
            != expected_committed_sha256
        ):
            raise D7RealWorldPreflightHold("COMMITTED marker pin differs")
        # Actual Stage28c requires three Paper dimensions and exact A/B.
        source = inspect_stage28c_source(
            root, expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
            expected_generation_id=expected_generation_id,
        )
        if (
            source.committed_sha256 != expected_committed_sha256
            or source.paper_dimensions != ("world_nether", "world_the_end")
            or source.roster != ("A", "B")
        ):
            raise D7RealWorldPreflightHold("not the complete original A/B Paper cut")
        # B recovery verifies the World+WAL+Owner cohort and D4 also compares
        # every archived/restored Self's cognition, owner-state and WAL hash.
        recovered = inspect_d4_inert_recovery(
            root, dest, expected_self_ids=("A", "B"),
            expected_source_world_id=expected_world_id,
            expected_committed_sha256=expected_committed_sha256,
        )
        if (
            recovered.generation_id != expected_generation_id
            or recovered.source_world_id != expected_world_id
            or recovered.fork_branch_id != expected_fork_branch_id
            or recovered.current_native_session_attested
            or recovered.l2_dispatch_authorized
            or recovered.physical_action_issue_authorized
            or tuple(s.self_id for s in recovered.restored) != ("A", "B")
        ):
            raise D7RealWorldPreflightHold("recovered original Owner branch mismatch")
        from relay_self.persistent_cognition import load_persistent_cognition
        from relay_self.self_owner_checkpoint_dev import verify_typed_generation

        cuts = verify_typed_generation(root)
        selves = []
        all_attempts: set[str] = set()
        old_natives: set[str] = set()
        for sid, inert, cut in zip(("A", "B"), recovered.restored, cuts, strict=True):
            cognition = load_persistent_cognition(
                dest / "selves" / sid / "cognition.json"
            )
            continuity = cognition.exploration_continuity
            if (
                inert.self_id != sid or cut.self_id != sid
                or cognition.identity.self_id != sid
                or not inert.question_refs or not inert.attempt_refs
                or continuity is None or continuity.self_id != sid
                or len(set(inert.question_refs)) != len(inert.question_refs)
                or not set(inert.question_refs).issubset(cut.pending_question_refs)
                or inert.historical_native_session_id
                != cut.former_native_session_id
                or inert.historical_native_session_id in old_natives
                or any(q.open and not q.question_ref in inert.question_refs
                       for q in continuity.questions)
                or any(not a.attempt_ref in inert.attempt_refs
                       for a in continuity.attempts)
            ):
                raise D7RealWorldPreflightHold(
                    "Self-owned original OPEN Question/L2 attempt missing or foreign"
                )
            # Never use a stale L2 inference as positive L1/World authority.
            if (
                not all(
                    a.question_ref in inert.question_refs
                    and a.phase in (
                        AttemptPhase.RESERVED, AttemptPhase.CANCELLED,
                        AttemptPhase.TIMEOUT, AttemptPhase.UNRESOLVED,
                        AttemptPhase.REFERENCED_OBSERVED_TARGET,
                    )
                    for a in continuity.attempts
                )
                or set(inert.attempt_refs) & all_attempts
            ):
                raise D7RealWorldPreflightHold("orphan/duplicate L2 reservation")
            old_natives.add(inert.historical_native_session_id)
            all_attempts.update(inert.attempt_refs)
            selves.append(D7SelfSource(
                sid, inert.question_refs, inert.attempt_refs,
                inert.historical_native_session_id,
                sum(a.phase is AttemptPhase.RESERVED for a in continuity.attempts),
            ))
        return D7SourceCandidate(
            source.generation_id, source.source_world_id,
            source.source_branch_id, recovered.fork_branch_id,
            expected_committed_sha256, ("A", "B"), tuple(selves),
        )
    except D7RealWorldPreflightHold:
        raise
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        raise D7RealWorldPreflightHold(
            "original full Paper/typed A+B/WAL/D cognition source not verified"
        ) from exc
