"""Read-only exact-owner retained snapshot handoff for explicit caller epochs.

This file does not schedule epochs, mutate an owner or define a PLAN policy.
The caller supplies the authoritative current owner snapshot; no persistent
LearningPreferenceStore exists in S10/S18.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.learning import LearningCommitRecord, LearningPreferenceState
from relay_self.provenance import Provenance


class RetainedReadError(ValueError):
    """Invalid cross-epoch retained read request."""


class StaleRetainedSnapshot(RetainedReadError):
    """The supplied read is not the exact current owner snapshot."""


class UnauthorizedRetainedRead(RetainedReadError):
    """The declared owner/target/lineage does not authorize this read."""


@dataclass(frozen=True, slots=True)
class RetainedPreferenceRead:
    """Read-only audit envelope; not a new owner or a commit token."""

    snapshot: LearningPreferenceState
    revision: int
    origin_provenance: Provenance
    last_update: LearningCommitRecord | None
    read_provenance: Provenance


def read_retained_preference(
    owner_snapshot: LearningPreferenceState,
    supplied_snapshot: LearningPreferenceState,
    *,
    required_target_id: str,
    expected_revision: int,
    provenance: Provenance,
) -> RetainedPreferenceRead:
    """Check exact immutable handoff before explicit PLAN work consumes it.

    Identity (not merely equality) prevents an equal-valued reconstructed
    snapshot from impersonating the caller-owned current snapshot. The caller
    remains responsible for truthfully supplying the current owner snapshot.
    """
    if not isinstance(owner_snapshot, LearningPreferenceState):
        raise UnauthorizedRetainedRead("owner_snapshot must be LearningPreferenceState")
    if not isinstance(supplied_snapshot, LearningPreferenceState):
        raise UnauthorizedRetainedRead("supplied_snapshot must be LearningPreferenceState")
    if not isinstance(required_target_id, str) or not required_target_id.strip():
        raise UnauthorizedRetainedRead("required_target_id must be a nonempty target")
    if not isinstance(provenance, Provenance):
        raise UnauthorizedRetainedRead("read provenance must be Provenance")
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise UnauthorizedRetainedRead("expected_revision must be an integer")
    if expected_revision < 0:
        raise UnauthorizedRetainedRead("expected_revision cannot be negative")
    if owner_snapshot.target_id != required_target_id:
        raise UnauthorizedRetainedRead("owner target mismatch")
    if supplied_snapshot is not owner_snapshot:
        raise StaleRetainedSnapshot("supplied snapshot is not exact current owner object")
    if supplied_snapshot.revision != expected_revision:
        raise StaleRetainedSnapshot("supplied snapshot revision mismatch")
    if expected_revision and supplied_snapshot.last_update is None:
        raise UnauthorizedRetainedRead("noninitial snapshot lacks committed update evidence")
    return RetainedPreferenceRead(
        snapshot=supplied_snapshot,
        revision=supplied_snapshot.revision,
        origin_provenance=supplied_snapshot.origin_provenance,
        last_update=supplied_snapshot.last_update,
        read_provenance=provenance,
    )
