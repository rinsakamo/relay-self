"""Stage28b: stopped Paper + retired original A/B -> one typed World/Self cut.

This deliberately does NOT attach CognitionOwnerCohort a second time to
ResidentCognitiveWorkOwner, does NOT use World-only as a cognitive source,
and does NOT revive old physical Actions or resume L1 work.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.coordinated_autosave_runtime_dev import (
    StoppedWorldReceipt,
    next_generation_sequence,
)
from relay_self.coordinated_checkpoint_dev import (
    SelfSnapshotSource,
    verify_generation,
)
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    capture_typed_generation,
    load_self_owner_cut,
    save_self_owner_cut,
    verify_typed_generation,
)


class Stage28bRetiredCutHold(RuntimeError):
    """Original source, typed cut, or stopped-world provenance is not qualified."""


@dataclass(frozen=True, slots=True)
class Stage28bRetiredCutResult:
    generation: Path
    stopped_world_tick: int
    world_id: str
    branch_id: str
    old_paper_session_id: str
    verified_self_ids: tuple[str, ...]
    actual_typed_owner_cut: bool = True
    automatic_l1_replay: bool = False
    physical_action_issue_authorized: bool = False
    real_60_second_autosave_attested: bool = False


def _retired_owner_snapshots(
    *, owners: dict[str, CheckpointedCognitiveOwner],
    root: Path, generation_id: str,
    world_id: str, branch_id: str,
    resident: ResidentCognitiveWorkOwner | None = None,
) -> tuple[SelfSnapshotSource, ...]:
    """Serialize canonical original owners, never parallel shadow owners."""
    if tuple(sorted(owners)) != ("A", "B"):
        raise Stage28bRetiredCutHold("exact A/B original Self roster required")
    sources = []
    for self_id in ("A", "B"):
        owner = owners[self_id]
        if (
            not isinstance(owner, CheckpointedCognitiveOwner)
            or owner.self_id != self_id
            or owner.supervisor.open_actions
            or not owner.files.cognition_file.is_file()
            or load_persistent_cognition(owner.files.cognition_file) != owner.retained
        ):
            raise Stage28bRetiredCutHold(
                "original retired cognition source absent or unflushed"
            )
        recorded_schema = None
        if resident is not None:
            if (type(resident) is not ResidentCognitiveWorkOwner
                    or resident.owners.get(self_id) is not owner):
                raise Stage28bRetiredCutHold("foreign original resident Schema source")
            recorded_schema = resident.recorded_retired_schema(self_id)
            if recorded_schema is not None and (
                owner.retained.pattern_registry is None
                or owner.retained.pattern_registry != owner.pattern_registry
            ):
                raise Stage28bRetiredCutHold(
                    "recorded Schema requires same-Self persisted registry"
                )
        wal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=self_id,
        )
        wal.require_clear()
        cut = SelfOwnerCut(
            generation_id=generation_id, self_id=self_id,
            world_id=world_id, branch_id=branch_id,
            former_native_session_id=owner.native_session_id,
            last_observed_world_tick=owner.last_observed_tick,
            intent_events=owner.intent.events,
            skill_executions=tuple(owner.skills[key] for key in sorted(owner.skills)),
            pattern_registry=owner.pattern_registry,
            peer_deliveries=tuple(
                owner.peer_deliveries[key] for key in sorted(owner.peer_deliveries)
            ),
            pending_question_refs=tuple(sorted(owner.pending_questions)),
            recorded_schema=recorded_schema,
            cognition_sha256=(
                hashlib.sha256(owner.files.cognition_file.read_bytes()).hexdigest()
                if recorded_schema is not None else None
            ),
        )
        destination = root / self_id
        destination.mkdir(mode=0o700)
        owner_file = destination / "owner-state.json"
        save_self_owner_cut(owner_file, cut)
        if load_self_owner_cut(owner_file) != cut:
            raise Stage28bRetiredCutHold("typed canonical Self write/readback differs")
        sources.append(SelfSnapshotSource(
            self_id, owner.files.cognition_file,
            owner.files.physical_wal_file, owner_file,
        ))
    return tuple(sources)


def capture_retired_resident_typed_world(
    *, bridge: OwnedResidentPhysicalBridge,
    paper: OwnedPaperWorld,
    store: Path,
    evidence_dir: Path,
) -> Stage28bRetiredCutResult:
    """One foreground original-owner cut after real A/B logout.

    The original bridge's world-only quiescence verifies *absence* of all
    native children, unresolved WAL, unretired CPU/GPU tasks, peer traffic and
    original Action leases. World-only is used as a *quiescence witness*, not
    as a checkpoint! This function captures a NEW typed World+Self generation.
    If stopping Paper or verifying the cut fails, do not restart/retry it.
    """
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(paper, OwnedPaperWorld)
        or bridge.paper is not paper
        or not isinstance(store, Path) or store.is_symlink() or not store.is_dir()
        or not isinstance(evidence_dir, Path)
        or evidence_dir.is_symlink() or not evidence_dir.is_dir()
        or store == evidence_dir
    ):
        raise Stage28bRetiredCutHold("one original bridge/owned Paper and separate stores")
    lifecycle = bridge.lifecycle
    world = lifecycle.world
    if tuple(sorted(bridge.owners)) != ("A", "B"):
        raise Stage28bRetiredCutHold("exact A/B original Self roster required")
    if (
        paper.held_uncertain
        or paper.owned_session_id != world.paper_session_id
        or paper.world_id != world.world_id
        or paper.branch_id != world.branch_id
        or tuple(sorted(bridge.owners)) != lifecycle.self_roster
        or lifecycle.self_roster != ("A", "B")
    ):
        raise Stage28bRetiredCutHold("resident/Paper source World identity mismatch")
    source = bridge.world_only_quiescence()
    if (
        source.checked_self_ids != ("A", "B")
        or source.world_epoch != world.epoch
        or not source.original_physical_issuer_closed
        or not source.native_sessions_absent
        or not source.no_unresolved_physical_actions
        or not source.all_gpu_epochs_retired
        or not source.pending_peer_messages_empty
    ):
        raise Stage28bRetiredCutHold("original A/B retirement not independently qualified")

    # Keep an independently new typed generation. Do not infer saved cognition
    # from a World-only generation or borrow any earlier owner-state.json.
    sequence = next_generation_sequence(store)
    generation_id = f"g-{sequence:012d}"
    prepared = evidence_dir / ("stage28b-typed-staging-" + generation_id)
    prepared.mkdir(mode=0o700)
    sources = _retired_owner_snapshots(
        owners=bridge.owners, root=prepared, generation_id=generation_id,
        world_id=world.world_id, branch_id=world.branch_id,
        resident=getattr(bridge, "cognitive_work", None),
    )
    # Recheck source lease immediately before stopping Paper. A second
    # concurrent native login/action must force HOLD instead of a mixed cut.
    bridge.world_only_quiescence()
    stopped = paper.stop_and_save()
    if (
        not isinstance(stopped, StoppedWorldReceipt)
        or stopped.old_server_session_id != world.paper_session_id
        or stopped.world_id != world.world_id
        or stopped.branch_id != world.branch_id
        or stopped.process_exit_code != 0
        or not stopped.all_dimensions_saved
        or stopped.logical_tick < world.world_tick
        or any(bridge.owners[sid].last_observed_tick > stopped.logical_tick
               for sid in ("A", "B"))
    ):
        raise Stage28bRetiredCutHold(
            "stopped Paper tick/source incompatible with original Self cut"
        )
    generation = capture_typed_generation(
        paper.world_dir, store, sequence=sequence,
        expected_self_ids=("A", "B"), selves=sources,
        world_id=world.world_id, branch_id=world.branch_id,
        logical_tick=stopped.logical_tick,
        tick_source_ref=stopped.tick_source_ref,
        stopped_server_ref=stopped.stopped_server_ref,
        quiesced_selves_ref=source.source_ref + ":" + generation_id,
        paper_layout=True,
    )
    verify_generation(generation)
    cuts = verify_typed_generation(generation)
    if tuple(c.self_id for c in cuts) != ("A", "B"):
        raise Stage28bRetiredCutHold("typed generation missing original A/B owners")
    # Deliberate no Paper restart here. A Stage28c fresh World branch restore
    # must be a separately qualified action, with completely new native IDs.
    return Stage28bRetiredCutResult(
        generation, stopped.logical_tick, world.world_id, world.branch_id,
        world.paper_session_id, tuple(c.self_id for c in cuts),
    )
