"""Stage28c1: source-pinned one-time typed World+A/B inert branch restore.

This copies no existing Self into a running process. It only invokes the
existing typed-generation copier, verifies every new Paper dimension's own
restore sidecar and original archived bytes, and rehydrates inert cognition.
No Paper, Mineflayer, Gemma, peer transport or physical Action is started.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from relay_self.coordinated_checkpoint_dev import (
    restore_generation,
    verify_generation,
)
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28InertRecovery,
    stage28_inert_cognitive_recovery,
)
from relay_self.world_checkpoint_dev import (
    verify_restored_world,
    verify_world_checkpoint,
)


class Stage28cRestoreHold(RuntimeError):
    """Do not adopt a partial, foreign, or non-reproducible cognitive restore."""


@dataclass(frozen=True, slots=True)
class Stage28cSource:
    generation_id: str
    world_id: str
    source_branch_id: str
    declared_world_tick: int
    roster: tuple[str, ...]
    self_cut_ticks: tuple[tuple[str, int], ...]
    paper_dimensions: tuple[str, ...]
    committed_sha256: str
    full_cognition_restored: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Stage28cInertRestore:
    generation_id: str
    source_commit_sha256: str
    restored_directory: str
    world_id: str
    restored_branch_id: str
    declared_world_tick: int
    self_cut_ticks: tuple[tuple[str, int], ...]
    roster: tuple[str, ...]
    paper_dimensions: tuple[str, ...]
    self_pattern_revisions: tuple[tuple[str, int], ...]
    fresh_worldbody_required: bool = True
    old_native_session_reuse_forbidden: bool = True
    old_action_replay_authorized: bool = False
    old_l1_decision_reusable: bool = False
    old_skill_resume_authorized: bool = False
    old_peer_redelivery_authorized: bool = False
    l1_reevaluation_eligible: bool = False
    physical_action_issue_authorized: bool = False
    new_paper_session_attested: bool = False


def _hash_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Stage28cRestoreHold("source commit marker missing or symlinked")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_stage28c_source(
    generation: Path, *, expected_world_id: str,
    expected_source_branch_id: str,
    expected_generation_id: str = "g-000000000000",
) -> Stage28cSource:
    """No filesystem mutation; exact typed A/B and three Paper dimension cut."""
    if (
        type(expected_world_id) is not str or not expected_world_id
        or type(expected_source_branch_id) is not str
        or not expected_source_branch_id
        or type(expected_generation_id) is not str
        or not expected_generation_id
    ):
        raise Stage28cRestoreHold("source World and generation pins required")
    generation = Path(generation)
    if (
        generation.is_symlink()
        or not generation.is_dir()
        or generation.name != expected_generation_id
    ):
        raise Stage28cRestoreHold("foreign or missing typed source generation")
    try:
        manifest = verify_generation(generation)
        cuts = verify_typed_generation(generation)
        world = verify_world_checkpoint(generation / "world")
        if (
            manifest["schema"] != 2
            or tuple(manifest["roster"]) != ("A", "B")
            or tuple(c.self_id for c in cuts) != ("A", "B")
            or world["world_id"] != expected_world_id
            or manifest["world_id"] != expected_world_id
            or world["branch_id"] != manifest["branch_id"]
            or world["branch_id"] != expected_source_branch_id
            or tuple(sorted(manifest["paper_dimensions"]))
            != ("world_nether", "world_the_end")
            or any(c.last_observed_world_tick > manifest["declared_tick"] for c in cuts)
        ):
            raise Stage28cRestoreHold("source typed World/A+B cut does not match pins")
        digest = _hash_file(generation / "COMMITTED.json")
    except Stage28cRestoreHold:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise Stage28cRestoreHold(
            "source generation is unverified or not a typed A/B Paper cut"
        ) from exc
    return Stage28cSource(
        generation.name, world["world_id"], world["branch_id"],
        manifest["declared_tick"], tuple(manifest["roster"]),
        tuple((c.self_id, c.last_observed_world_tick) for c in cuts),
        tuple(sorted(manifest["paper_dimensions"])), digest,
    )


def _fresh_destination(generation: Path, destination: Path) -> None:
    """Reject any path that would overwrite/overlap the historical source."""
    source = generation.absolute()
    target = destination.absolute()
    if (
        destination.is_symlink() or destination.exists()
        or destination.parent.is_symlink()
        or not destination.parent.is_dir()
        or generation.is_symlink()
        or source in target.parents
        or target in source.parents or target == source
        or source.resolve(strict=True) != source
        or destination.parent.resolve(strict=True) != destination.parent.absolute()
    ):
        raise Stage28cRestoreHold(
            "restoration must use a new directory outside immutable source"
        )


def prepare_stage28c_inert_restore(
    generation: Path, destination: Path, *,
    expected_world_id: str, expected_source_branch_id: str,
    expected_committed_sha256: str, restore_id: str,
    expected_generation_id: str = "g-000000000000",
) -> Stage28cInertRestore:
    """Create one fresh branch, independently verify it, never activate A/B."""
    source = inspect_stage28c_source(
        generation, expected_world_id=expected_world_id,
        expected_source_branch_id=expected_source_branch_id,
        expected_generation_id=expected_generation_id,
    )
    if (
        type(expected_committed_sha256) is not str
        or expected_committed_sha256 != source.committed_sha256
        or type(restore_id) is not str or not restore_id
    ):
        raise Stage28cRestoreHold(
            "independently pinned source COMMITTED SHA256 or restore ID missing"
        )
    generation = Path(generation)
    destination = Path(destination)
    _fresh_destination(generation, destination)

    # No rollback on failed restore: a failed dest is frozen evidence, never
    # reused in a second attempt or silently upgraded to a valid generation.
    try:
        result = restore_generation(
            generation, destination, restore_id=restore_id,
        )
        if (
            tuple(result["self_ids"]) != source.roster
            or result["generation_id"] != source.generation_id
            or result["physical_action_issue_authorized"] is not False
            or result["replay_performed"] is not False
            or result["full_self_owner_restored"] is not False
        ):
            raise Stage28cRestoreHold("copied generation tries to authorize replay")

        # Stage28a checks copied bytes; additionally revalidate EVERY new
        # dimension's sidecar including shared fork branch and saved tick.
        restored_sidecars = []
        for dim in ("world", *source.paper_dimensions):
            archived = (
                generation / "world" if dim == "world"
                else generation / "paper-dimensions" / dim
            )
            checked = verify_restored_world(archived, destination / dim)
            if (
                checked["new_branch_id"] != result["fork_branch_id"]
                or checked["source_checkpoint_id"] != source.generation_id
                or checked["world_id"] != source.world_id
                or checked["source_declared_logical_tick"]
                != source.declared_world_tick
                or checked["physical_action_authorized"] is not False
                or checked["semantic_owner_restored"] is not False
            ):
                raise Stage28cRestoreHold(
                    "Paper dimension sidecar disagrees with typed fork"
                )
            restored_sidecars.append(checked["new_branch_id"])
        if len(set(restored_sidecars)) != 1:
            raise Stage28cRestoreHold("Paper dimensions refer to separate forks")

        candidates: Stage28InertRecovery = stage28_inert_cognitive_recovery(
            generation, destination,
            expected_self_ids=source.roster,
            expected_source_world_id=source.world_id,
        )
        if (
            candidates.fork_branch_id != result["fork_branch_id"]
            or candidates.cut_ticks != source.self_cut_ticks
            or candidates.roster != source.roster
            or any(c.issue_authorized or c.native_session_bound
                   or c.conversation_redelivery_authorized
                   or not c.fresh_worldbody_required
                   for c in candidates.candidates)
        ):
            raise Stage28cRestoreHold("restored Self candidate not inert")

        # Final independent re-check: even the original COMMITTED marker
        # cannot silently change while a multi-dimensional copy is made.
        if inspect_stage28c_source(
            generation, expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
            expected_generation_id=expected_generation_id,
        ) != source:
            raise Stage28cRestoreHold("source generation changed during restore")
    except Stage28cRestoreHold:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise Stage28cRestoreHold(
            "typed restore failed; preserve incomplete destination as evidence"
        ) from exc

    return Stage28cInertRestore(
        source.generation_id, source.committed_sha256,
        str(destination.absolute()), source.world_id,
        result["fork_branch_id"], source.declared_world_tick,
        source.self_cut_ticks, source.roster, source.paper_dimensions,
        tuple((c.self_id, c.semantic.pattern_registry.revision)
              for c in candidates.candidates),
    )
