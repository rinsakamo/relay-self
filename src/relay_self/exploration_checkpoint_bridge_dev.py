"""D Lane D4: opt-in Stage28 original-resident/typed-cut integration boundary.

The implementation accepts ONLY the original B Lane owner classes when the
unmerged Stage28 stack is integrated. In D-only builds it fails closed rather
than claiming a fake resident is an attested Self. No new Owner or ActionPort.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypeVar

from relay_self.exploration_continuity_dev import (
    AttemptPhase,
    ExplorationContinuityError,
    L2Reservation,
    open_question_refs,
    record_l2_attempt_result,
    reserve_exploration_l2,
    retain_open_question,
)
from relay_self.exploration_goal_dev import ExplorationRound
from relay_self.persistent_cognition import (
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.three_self_present import PresentFrame

if TYPE_CHECKING:
    from relay_self.cognitive_minimal_dev import Selection
    from relay_self.exploration_goal_dev import L2TargetReview
    from relay_self.cognitive_minimal_dev import WorldPercept


class D4OwnerHold(RuntimeError):
    """Existing resident, checkpoint, source, or durability is not admitted."""


@dataclass(frozen=True, slots=True)
class ResidentD4Scope:
    """Existing Stage28 resident lease readout; NOT a new model/physical lease."""

    self_id: str
    cognition_epoch: int
    native_session_id: str
    world_epoch: int
    intent_event_count: int
    last_intent_at_ns: int | None


@dataclass(frozen=True, slots=True)
class D4RecoveredSelf:
    """Only inert old Questions/attempt refs from verified Stage28 cut."""

    self_id: str
    question_refs: tuple[str, ...]
    attempt_refs: tuple[str, ...]
    historical_native_session_id: str
    old_l2_replay_authorized: bool = False
    physical_action_issue_authorized: bool = False
    old_skill_resume_authorized: bool = False


@dataclass(frozen=True, slots=True)
class D4RestoredCohort:
    generation_id: str
    committed_sha256: str
    source_world_id: str
    fork_branch_id: str
    restored: tuple[D4RecoveredSelf, ...]
    current_native_session_attested: bool = False
    l2_dispatch_authorized: bool = False
    physical_action_issue_authorized: bool = False


def _b_owner_types() -> tuple[type, type]:
    """No import-time circular dependency; missing parallel B stack is HOLD."""
    try:
        from relay_self.checkpointed_cognitive_runtime_dev import (
            CheckpointedCognitiveOwner,
        )
        from relay_self.resident_cognitive_work_owner_dev import (
            ResidentCognitiveWorkOwner,
        )
    except ImportError as exc:
        raise D4OwnerHold("Stage28 original resident Owner is not integrated") from exc
    return CheckpointedCognitiveOwner, ResidentCognitiveWorkOwner


def _check_owner(owner: object, resident: object, expected: ResidentD4Scope) -> None:
    own_type, res_type = _b_owner_types()
    if (
        not isinstance(owner, own_type)
        or not isinstance(resident, res_type)
        or not isinstance(expected, ResidentD4Scope)
        or owner.self_id != expected.self_id
        or owner.cohort is not resident
        or resident.owners.get(expected.self_id) is not owner
        or resident.current_scope(expected.self_id) != (
            expected.cognition_epoch,
            expected.native_session_id,
            expected.world_epoch,
        )
        or owner.native_session_id != expected.native_session_id
        or owner.fresh_native_observation_required
        or owner.current_worldbody_observation is None
        or len(owner.intent.events) != expected.intent_event_count
        or owner.intent.last_at_ns != expected.last_intent_at_ns
    ):
        raise D4OwnerHold("original Self resident epoch/Intent/native source is stale")
    if not isinstance(owner.retained, PersistentCognition):
        raise D4OwnerHold("original Self retained cognition unavailable")
    files = owner.files
    if (
        files.self_root.is_symlink()
        or files.cognition_file.is_symlink()
        or not files.self_root.is_dir()
        or not files.cognition_file.is_file()
        or files.cognition_file != files.self_root / "cognition.json"
    ):
        raise D4OwnerHold("canonical original Self cognition path required")


def _assert_cut_questions(
    cognition: PersistentCognition,
    pending_questions: set[str] | tuple[str, ...],
    *,
    expected_self_id: str,
) -> tuple[str, ...]:
    if type(pending_questions) not in (set, tuple) or any(
        type(q) is not str or not q.strip() for q in pending_questions
    ):
        raise D4OwnerHold("typed original owner Question refs required")
    if len(set(pending_questions)) != len(pending_questions):
        raise D4OwnerHold("duplicate owner Question refs")
    questions = open_question_refs(cognition, expected_self_id=expected_self_id)
    if not set(questions).issubset(pending_questions):
        raise D4OwnerHold("open D Question absent from same original owner cut")
    return questions


_T = TypeVar("_T")


def _write_original_owner(
    owner: object,
    resident: object,
    scope: ResidentD4Scope,
    update: Callable[[PersistentCognition], tuple[PersistentCognition, _T]],
    *,
    published_question_ref: str | None = None,
) -> _T:
    """Stage28's actual shared RLock + actual resident _mutating admission.

    The *original* owner retains and writes the *original* cognition file;
    no D-owned file, lock, checkpoint, or mutation policy exists. Failure after
    attempted disk mutation fences the same B resident before releasing lock.
    """
    own_type, res_type = _b_owner_types()
    if not isinstance(owner, own_type) or not isinstance(resident, res_type):
        raise D4OwnerHold("foreign/unspecified owner cannot mutate cognition")
    if not isinstance(scope, ResidentD4Scope):
        raise D4OwnerHold("typed original resident scope required")
    with resident.lock:
        _check_owner(owner, resident, scope)
        try:
            owner._eligible()
        except RuntimeError as exc:
            raise D4OwnerHold("original Self writing is fenced") from exc
        previous = owner.retained
        _assert_cut_questions(
            previous, owner.pending_questions, expected_self_id=owner.self_id,
        )
        if load_persistent_cognition(owner.files.cognition_file) != previous:
            raise D4OwnerHold("original cognition disk/current owner disagreement")
        updated, result = update(previous)
        if updated is previous:
            return result
        if (
            not isinstance(updated, PersistentCognition)
            or updated.identity.self_id != owner.self_id
            or updated.exploration_continuity is None
        ):
            raise D4OwnerHold("new state is foreign or untyped")
        new_pending = set(owner.pending_questions)
        if published_question_ref is not None:
            new_pending.add(published_question_ref)
        _assert_cut_questions(
            updated, new_pending, expected_self_id=owner.self_id,
        )
        # Only the original save/load writer. A half-written/corrupt readback
        # must NOT leave this Self ONLINE for further mutation or L2 dispatch.
        try:
            save_persistent_cognition(owner.files.cognition_file, updated)
            if load_persistent_cognition(owner.files.cognition_file) != updated:
                raise D4OwnerHold("original cognition durable readback mismatch")
        except BaseException:
            resident.fence_self(owner.self_id)
            raise
        owner.retained = updated
        owner.pending_questions = new_pending
        return result


def retain_resident_question(
    owner: object,
    resident: object,
    *,
    scope: ResidentD4Scope,
    present: PresentFrame,
    question_ref: str,
    owner_provenance: Provenance,
) -> None:
    """Owner ADOPT via its original file and pending_question_refs together."""
    if (
        not isinstance(present, PresentFrame)
        or not isinstance(owner_provenance, Provenance)
        or present.three_self.scope.self_id != scope.self_id
    ):
        raise D4OwnerHold("foreign/unprojected original Present Question")
    def write(cognition: PersistentCognition) -> tuple[PersistentCognition, None]:
        revision = (
            0 if cognition.exploration_continuity is None
            else cognition.exploration_continuity.revision
        )
        changed = retain_open_question(
            cognition, question_ref=question_ref, origin=owner_provenance,
            expected_revision=revision,
            current_present_question_refs=present.active_question_refs,
        )
        return changed, None

    _write_original_owner(
        owner, resident, scope, write, published_question_ref=question_ref,
    )


def reserve_resident_l2(
    owner: object,
    resident: object,
    *,
    scope: ResidentD4Scope,
    round_: ExplorationRound,
    selection: Selection,
    owner_provenance: Provenance,
) -> L2Reservation | None:
    """Original owner persists RESERVED BEFORE any external GPU call."""
    if (
        not isinstance(round_, ExplorationRound)
        or not isinstance(owner_provenance, Provenance)
        or round_.present.three_self.scope.self_id != scope.self_id
    ):
        raise D4OwnerHold("foreign/unprojected L2 round")
    def write(
        cognition: PersistentCognition,
    ) -> tuple[PersistentCognition, L2Reservation | None]:
        state = cognition.exploration_continuity
        if state is None:
            raise D4OwnerHold("L2 Question not retained by original Self")
        return reserve_exploration_l2(
            cognition, round_=round_, selection=selection,
            expected_revision=state.revision,
            current_intent_owner_revision=round_.owner_revision,
            native_session_ref=scope.native_session_id,
            owner_provenance=owner_provenance,
        )
    return _write_original_owner(owner, resident, scope, write)


def record_resident_l2_result(
    owner: object,
    resident: object,
    *,
    scope: ResidentD4Scope,
    reservation: L2Reservation,
    phase: AttemptPhase,
    reviewed_target: L2TargetReview | None = None,
    current_percept: WorldPercept | None = None,
    current_source_revision_refs: tuple[str, ...] = (),
) -> None:
    """No stale task after B resident retirement/new JOIN can change history."""
    if (
        not isinstance(reservation, L2Reservation)
        or not isinstance(phase, AttemptPhase)
        or reservation.task.scope.self_id != scope.self_id
        or reservation.native_session_ref != scope.native_session_id
        or reservation.intent_owner_revision < 0
    ):
        raise D4OwnerHold("stale/foreign resident L2 completion")
    def write(cognition: PersistentCognition) -> tuple[PersistentCognition, None]:
        state = cognition.exploration_continuity
        if state is None:
            raise D4OwnerHold("original Self L2 reservation missing")
        next_cognition = record_l2_attempt_result(
            cognition, reservation=reservation, phase=phase,
            expected_revision=state.revision,
            reviewed_target=reviewed_target,
            current_percept=current_percept,
            current_source_revision_refs=current_source_revision_refs,
        )
        return next_cognition, None

    _write_original_owner(owner, resident, scope, write)


def inspect_d4_inert_recovery(
    generation: Path,
    restored_directory: Path,
    *,
    expected_self_ids: tuple[str, ...],
    expected_source_world_id: str,
    expected_committed_sha256: str,
) -> D4RestoredCohort:
    """Requires B Stage28's actual full typed World/WAL/roster recovery gate.

    Never use D's own hash or user-provided fake receipt to authorize recovery.
    Works only after D and unmerged B code share a source tree.
    """
    try:
        from relay_self.stage28_cognitive_recovery_gate_dev import (
            stage28_inert_cognitive_recovery,
        )
    except ImportError as exc:
        raise D4OwnerHold("real Stage28 typed recovery stack unavailable") from exc
    if (
        type(expected_self_ids) is not tuple
        or not expected_self_ids
        or type(expected_committed_sha256) is not str
        or len(expected_committed_sha256) != 64
        or any(c not in "0123456789abcdef"
               for c in expected_committed_sha256)
    ):
        raise D4OwnerHold("original typed commit identity required")
    try:
        plan = stage28_inert_cognitive_recovery(
            Path(generation), Path(restored_directory),
            expected_self_ids=expected_self_ids,
            expected_source_world_id=expected_source_world_id,
        )
        marker = Path(generation) / "COMMITTED.json"
        if (
            marker.is_symlink()
            or hashlib.sha256(marker.read_bytes()).hexdigest()
            != expected_committed_sha256
            or plan.source_committed_sha256 != expected_committed_sha256
            or tuple(plan.roster) != tuple(sorted(expected_self_ids))
            or plan.physical_action_issue_authorized
            or plan.old_l1_decision_reusable
            or plan.old_skill_resume_authorized
            or plan.l1_reevaluation_eligible
        ):
            raise D4OwnerHold("wrong committed cohort or resumed old authority")
        restored = []
        for candidate in plan.candidates:
            cut = candidate.semantic.cut
            if (
                candidate.retained.identity.self_id != candidate.self_id
                or cut.self_id != candidate.self_id
                or cut.generation_id != plan.generation_id
                or cut.world_id != plan.source_world_id
                or cut.branch_id != plan.source_branch_id
                or candidate.native_session_bound
                or candidate.issue_authorized
                or not candidate.fresh_worldbody_required
            ):
                raise D4OwnerHold("inert restored Self/source mismatch")
            questions = _assert_cut_questions(
                candidate.retained, cut.pending_question_refs,
                expected_self_id=candidate.self_id,
            )
            state = candidate.retained.exploration_continuity
            restored.append(D4RecoveredSelf(
                self_id=candidate.self_id,
                question_refs=questions,
                attempt_refs=() if state is None else tuple(
                    a.attempt_ref for a in state.attempts
                ),
                historical_native_session_id=cut.former_native_session_id,
            ))
        return D4RestoredCohort(
            plan.generation_id, expected_committed_sha256,
            plan.source_world_id, plan.fork_branch_id, tuple(restored),
        )
    except D4OwnerHold:
        raise
    except (OSError, ValueError, RuntimeError, AttributeError, TypeError) as exc:
        raise D4OwnerHold("Stage28 typed cohort or D cognition recovery HOLD") from exc
