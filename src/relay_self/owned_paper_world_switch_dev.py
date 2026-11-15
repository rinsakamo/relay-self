"""#860 DEV: switch two explicitly owned stopped/started Paper World instances.

The candidate World must match a PREEXISTING committed World-only archive,
pinned by the operator-provided external commit digest. No files are copied,
restored over, or imported into another server. Both owned Paper processes
use their own directories. No Self may be online or quarantined at switch.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from relay_self.coordinated_checkpoint_dev import _paper_siblings
from relay_self.owned_paper_world_dev import (
    OwnedPaperWorld,
    PaperTickReceipt,
)
from relay_self.world_checkpoint_dev import (
    _hash_file,
    _scan,
    verify_world_checkpoint,
)
from relay_self.world_only_owned_checkpoint_dev import (
    verify_world_only_generation,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldInstallationEvidence,
    WorldLifetime,
    WorldOnlyQuiescenceEvidence,
    WorldResidentLifecycle,
)


class WorldOwnershipSwitchError(RuntimeError):
    """World cannot be switched under a stale, foreign or partial owner scope."""


@dataclass(frozen=True, slots=True)
class WorldOwnershipSwitchResult:
    from_world: WorldLifetime
    to_world: WorldLifetime
    candidate_generation: Path
    candidate_commit_sha256: str
    old_paper_stop_ref: str
    new_paper_readback_ref: str
    previous_self_issued_actions_replayed: bool = False
    self_cognition_rewritten: bool = False
    body_state_transferred: bool = False


def _check_disk_matches_archive(
    source: Path, archived: Path,
) -> None:
    """Read-only, regular-file exact inventory/size/hash comparison."""
    manifest = verify_world_checkpoint(archived)
    expected = tuple(row["path"] for row in manifest["files"])
    if _scan(source, require_level_dat=(manifest["schema"] == 1)) != expected:
        raise WorldOwnershipSwitchError("candidate World file roster differs from archive")
    for row in manifest["files"]:
        if _hash_file(source / row["path"]) != (row["sha256"], row["size"]):
            raise WorldOwnershipSwitchError("candidate World files differ from pinned archive")


def verify_owned_world_candidate(
    paper: OwnedPaperWorld,
    *, candidate_generation: Path,
    expected_commit_sha256: str,
) -> dict:
    """Check pinned snapshot, all dimensions, and exact stopped source bytes.

    The hash pin must come from outside this candidate and its server directory;
    a self-referential hash in the same archive is not proof of authenticity.
    """
    if (
        not isinstance(paper, OwnedPaperWorld)
        or paper.owned_session_id is not None or paper.held_uncertain
        or type(expected_commit_sha256) is not str
        or len(expected_commit_sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in expected_commit_sha256)
    ):
        raise WorldOwnershipSwitchError("stopped owned candidate and external SHA256 pin required")
    root = Path(candidate_generation)
    marker = root / "WORLD_ONLY_COMMITTED.json"
    if marker.is_symlink() or not marker.is_file():
        raise WorldOwnershipSwitchError("pinned World-only generation absent")
    actual = hashlib.sha256(marker.read_bytes()).hexdigest()
    if actual != expected_commit_sha256:
        raise WorldOwnershipSwitchError("candidate external commit pin mismatch")
    manifest = verify_world_only_generation(root)
    if (
        manifest["world_id"] != paper.world_id
        or manifest["branch_id"] != paper.branch_id
    ):
        raise WorldOwnershipSwitchError("candidate World identity/branch differs")
    _check_disk_matches_archive(paper.world_dir, root / "world")
    found = dict(_paper_siblings(paper.world_dir))
    archived_names = set(manifest["paper_dimensions"])
    if set(found) != archived_names:
        raise WorldOwnershipSwitchError("candidate Paper dimension roster differs")
    for name, source in found.items():
        _check_disk_matches_archive(
            source, root / "paper-dimensions" / name,
        )
    return manifest


class OwnedPaperWorldSwitcher:
    """One operator-invoked transition, no implicit new Action owner."""

    def __init__(
        self, *, lifecycle: WorldResidentLifecycle,
        previous_paper: OwnedPaperWorld,
        candidate_paper: OwnedPaperWorld,
        issuer_quiescence: Callable[[], WorldOnlyQuiescenceEvidence],
    ) -> None:
        if (
            not isinstance(lifecycle, WorldResidentLifecycle)
            or not isinstance(previous_paper, OwnedPaperWorld)
            or not isinstance(candidate_paper, OwnedPaperWorld)
            or previous_paper.server_dir == candidate_paper.server_dir
            or previous_paper.world_dir == candidate_paper.world_dir
            or not callable(issuer_quiescence)
        ):
            raise WorldOwnershipSwitchError("two distinct owned Paper roots required")
        self.lifecycle = lifecycle
        self.previous_paper = previous_paper
        self.candidate_paper = candidate_paper
        self.issuer_quiescence = issuer_quiescence
        self._held = False

    @property
    def held_after_failure(self) -> bool:
        return self._held

    def switch_to_preverified_world(
        self, *, candidate_generation: Path,
        expected_commit_sha256: str,
    ) -> WorldOwnershipSwitchResult:
        """Only swap after zero Online/uncertain Self and a pinned candidate.

        A failed verification before begin_world_transition leaves the old
        World alone. Any failure after the transition fence HOLDs the World;
        never silently restart the old Paper or issue old native Actions.
        """
        original = self.lifecycle.world
        old = self.previous_paper
        new = self.candidate_paper
        if (
            self._held or not self.lifecycle.can_world_only_checkpoint()
            or old.held_uncertain or old.owned_session_id != original.paper_session_id
            or old.world_id != original.world_id
            or old.branch_id != original.branch_id
        ):
            raise WorldOwnershipSwitchError("old World/online roster not controlled")
        # Validate everything possible before disturbing the running World.
        verify_owned_world_candidate(
            new, candidate_generation=candidate_generation,
            expected_commit_sha256=expected_commit_sha256,
        )
        # No one may claim empty/retired physical actors merely because
        # a local presence ledger happens to show zero online.
        self.lifecycle.require_world_only_quiescence(self.issuer_quiescence())
        self.lifecycle.begin_world_transition()
        try:
            stopped = old.stop_and_save()
            if (
                stopped.world_id != original.world_id
                or stopped.branch_id != original.branch_id
                or stopped.old_server_session_id != original.paper_session_id
                or type(stopped.logical_tick) is not int
                or stopped.logical_tick < original.world_tick
                or stopped.process_exit_code != 0
                or stopped.all_dimensions_saved is not True
            ):
                raise WorldOwnershipSwitchError("former Paper not cleanly stopped")
            # No candidate World mutation may occur between the pinned
            # preflight and owned process startup.
            verify_owned_world_candidate(
                new, candidate_generation=candidate_generation,
                expected_commit_sha256=expected_commit_sha256,
            )
            new_session = new.start_owned()
            tick = new.tick_readback(new_session)
            if (
                not isinstance(tick, PaperTickReceipt)
                or tick.server_session_id != new_session
                or type(tick.tick) is not int or tick.tick < 0
                or type(tick.source_ref) is not str
                or not tick.source_ref.strip()
            ):
                raise WorldOwnershipSwitchError("new Paper tick source absent")
            installed = WorldLifetime(
                new.world_id, new.branch_id,
                new_session, original.epoch + 1, tick.tick,
            )
            self.lifecycle.install_world(WorldInstallationEvidence(
                previous_world=original, installed_world=installed,
                source_ref="owned-new-paper:" + tick.source_ref,
                former_paper_terminated=True, fresh_paper_owned=True,
                world_file_integrity_verified=True,
                old_world_actions_fenced=True,
            ))
            return WorldOwnershipSwitchResult(
                original, installed, Path(candidate_generation),
                expected_commit_sha256, stopped.stopped_server_ref,
                tick.source_ref,
            )
        except BaseException:
            self._held = True
            self.lifecycle.abort_world_transition()
            raise
