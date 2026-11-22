"""Internal storage for a previously admitted inquiry; no decision issuer exists.

This private primitive has no production caller. A future issuer must authenticate
its own decision before calling it; a proposal alone is never an authorization.
"""
from dataclasses import replace

from relay_self.bd1b_coverage_inquiry_dev import CoverageInquiryProposal
from relay_self.exploration_continuity_dev import ExplorationContinuity, QuestionRecord
from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
from relay_self.provenance import Provenance


class QuestionStoreHold(RuntimeError):
    """The inquiry cannot be stored safely."""


def _store_admitted_inquiry(resident, *, bridge, boot, world, links, self_id,
                            inquiry, expected_revision):
    """Store only after an internal owner admission (currently test-only).

    Caller-supplied data is not evidence of an autonomous Self decision.
    """
    with resident.lock:
        owner = resident.owners[self_id]
        owner._eligible()
        current = resident.read_coverage_inquiry_cpu(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        if type(inquiry) is not CoverageInquiryProposal or current is None or inquiry != current:
            raise QuestionStoreHold("stale or foreign inquiry")
        return _store_current_inquiry(
            resident, owner=owner, self_id=self_id, inquiry=inquiry,
            expected_revision=expected_revision,
            origin=Provenance("coverage-inquiry", inquiry.question_ref),
        )


def _store_current_inquiry(resident, *, owner, self_id, inquiry, expected_revision,
                           origin, revalidate=lambda: None):
    """Shared storage core. Caller holds resident lock and authenticates inquiry."""
    owner._eligible()
    previous = owner.retained
    continuity = previous.exploration_continuity
    revision = 0 if continuity is None else continuity.revision
    if type(expected_revision) is not int or expected_revision != revision:
        raise QuestionStoreHold("stale continuity revision")
    if previous.pattern_registry is not None and previous.pattern_registry != owner.pattern_registry:
        raise QuestionStoreHold("owner registry disagreement")
    if (type(owner.pending_questions) is not set or any(
        type(ref) is not str or not ref.strip() for ref in owner.pending_questions
    )):
        raise QuestionStoreHold("invalid pending questions")
    if continuity is not None and not {
        q.question_ref for q in continuity.questions if q.open
    }.issubset(owner.pending_questions):
        raise QuestionStoreHold("open question absent from pending refs")
    path = owner.files.cognition_file
    root = owner.files.self_root
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        if (path != root / "cognition.json" or not root.is_dir()
                or any(p.is_symlink() for p in (path, root, *root.parents))
                or not path.is_file() or path.stat().st_nlink != 1
                or temporary.exists() or temporary.is_symlink()):
            raise QuestionStoreHold("invalid canonical cognition path")
        if load_persistent_cognition(path) != previous:
            raise QuestionStoreHold("disk and owner cognition differ")
    except BaseException:
        resident.fence_self(self_id)
        raise
    if continuity is not None and any(q.question_ref == inquiry.question_ref for q in continuity.questions):
        return previous
    state = continuity or ExplorationContinuity(self_id, 0)
    record = QuestionRecord(inquiry.question_ref, origin)
    state = replace(state, revision=revision + 1, questions=(*state.questions, record))
    updated = previous.retain_exploration_continuity(state, expected_revision=revision)
    pending = owner.pending_questions | {inquiry.question_ref}
    try:
        revalidate()
        save_persistent_cognition(path, updated)
        if load_persistent_cognition(path) != updated:
            raise QuestionStoreHold("cognition readback mismatch")
        revalidate()
    except BaseException:
        resident.fence_self(self_id)
        raise
    owner.retained = updated
    owner.pending_questions = pending
    return updated
