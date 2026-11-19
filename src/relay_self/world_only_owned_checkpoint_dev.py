"""#860 DEV: World-only stopped-Paper generation while ALL registered Self offline.

Reuses the original OwnedPaperWorld owner, stopped-world file archive and
Paper dimension inventory. No cognition snapshot or physical Action issuer
appears in this World-only generation; no mixed World/Self rollback claims.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from relay_self.coordinated_checkpoint_dev import (
    _hash,
    _new_json,
    _paper_siblings,
)
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.world_checkpoint_dev import (
    capture_stopped_world,
    verify_world_checkpoint,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldInstallationEvidence,
    WorldLifetime,
    WorldOnlyQuiescenceEvidence,
    WorldResidentLifecycle,
)


class WorldOnlyCheckpointError(ValueError):
    """No verified World-only cut or invalid owned Paper transition."""


@dataclass(frozen=True, slots=True)
class WorldOnlyResult:
    checkpoint_dir: Path
    old_world: WorldLifetime
    new_world: WorldLifetime
    saved_world_tick: int
    no_self_cognition_rewritten: bool = True
    historical_actions_replayed: bool = False
    physical_action_authorized: bool = False


def verify_world_only_generation(path: Path) -> dict:
    """Typed exact roster-free manifest, but NEVER a Self-owner restore."""
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise WorldOnlyCheckpointError("World-only checkpoint unavailable")
    commit = root / "WORLD_ONLY_COMMITTED.json"
    if commit.is_symlink() or not commit.is_file():
        raise WorldOnlyCheckpointError("World-only generation not committed")
    try:
        body = json.loads(commit.read_bytes())
    except (ValueError, OSError) as exc:
        raise WorldOnlyCheckpointError("malformed World-only commit") from exc
    keys = {
        "schema", "generation_id", "world_id", "branch_id",
        "world_manifest_sha256", "old_paper_session_id",
        "declared_tick", "paper_dimensions", "owner_self_count",
        "self_cognition_mutated", "historical_replay_performed",
        "action_issue_authorized",
    }
    if (
        type(body) is not dict or set(body) != keys or body["schema"] != 1
        or body["generation_id"] != root.name
        or body["owner_self_count"] != 0
        or body["self_cognition_mutated"] is not False
        or body["historical_replay_performed"] is not False
        or body["action_issue_authorized"] is not False
        or type(body["declared_tick"]) is not int
        or body["declared_tick"] < 0
        or type(body["paper_dimensions"]) is not dict
    ):
        raise WorldOnlyCheckpointError("World-only commit schema invalid")
    expected = {"world", "WORLD_ONLY_COMMITTED.json"}
    if body["paper_dimensions"]:
        expected.add("paper-dimensions")
    if set(p.name for p in root.iterdir()) != expected:
        raise WorldOnlyCheckpointError("partial/foreign World-only files")
    first = verify_world_checkpoint(root / "world")
    if (
        first["world_id"] != body["world_id"]
        or first["branch_id"] != body["branch_id"]
        or first["declared_logical_tick"] != body["declared_tick"]
        or first["checkpoint_id"] != body["generation_id"]
        or _hash(root / "world" / "manifest.json")
        != body["world_manifest_sha256"]
    ):
        raise WorldOnlyCheckpointError("World-only main dimension mismatch")
    pins = body["paper_dimensions"]
    if pins:
        if not (root / "paper-dimensions").is_dir():
            raise WorldOnlyCheckpointError("Paper dimension archive missing")
        if set(p.name for p in (root / "paper-dimensions").iterdir()) != set(pins):
            raise WorldOnlyCheckpointError("Paper companion roster mismatch")
        for name, digest in pins.items():
            if name not in ("world_nether", "world_the_end"):
                raise WorldOnlyCheckpointError("unknown Paper companion")
            other = root / "paper-dimensions" / name
            row = verify_world_checkpoint(other)
            if (
                row["world_file_role"] != "PAPER_COMPANION"
                or row["world_id"] != body["world_id"]
                or row["branch_id"] != body["branch_id"]
                or row["checkpoint_id"] != body["generation_id"]
                or row["declared_logical_tick"] != body["declared_tick"]
                or _hash(other / "manifest.json") != digest
            ):
                raise WorldOnlyCheckpointError("Paper companion archive differs")
    if (
        type(body["old_paper_session_id"]) is not str
        or not body["old_paper_session_id"]
    ):
        raise WorldOnlyCheckpointError("old Paper process source absent")
    return body


class WorldOnlyOwnedPaperCheckpoint:
    """Explicit foreground cycle; Paper controls ONLY its owned process."""

    def __init__(
        self, *, lifecycle: WorldResidentLifecycle,
        owned_paper: OwnedPaperWorld, store: Path,
        issuer_quiescence: Callable[[], WorldOnlyQuiescenceEvidence],
    ) -> None:
        if (
            not isinstance(lifecycle, WorldResidentLifecycle)
            or not isinstance(owned_paper, OwnedPaperWorld)
            or not Path(store).is_dir() or Path(store).is_symlink()
            or not callable(issuer_quiescence)
        ):
            raise WorldOnlyCheckpointError("one owned Paper and preexisting store required")
        self.lifecycle = lifecycle
        self.owned_paper = owned_paper
        self.store = Path(store)
        self.issuer_quiescence = issuer_quiescence
        self._held = False
        self._sequence = 0

    @property
    def held_after_failure(self) -> bool:
        return self._held

    def cycle(self) -> WorldOnlyResult:
        if self._held or not self.lifecycle.can_world_only_checkpoint():
            raise WorldOnlyCheckpointError("World not exclusively offline/available")
        before = self.lifecycle.world
        paper = self.owned_paper
        if (
            paper.held_uncertain or paper.owned_session_id != before.paper_session_id
            or paper.world_id != before.world_id
            or paper.branch_id != before.branch_id
        ):
            raise WorldOnlyCheckpointError("foreign/uncertain owned Paper session")
        # An OFFLINE list alone is NOT evidence of native physical issuer
        # retirement. Refuse to touch Paper without its independent owner.
        self.lifecycle.require_world_only_quiescence(self.issuer_quiescence())
        self.lifecycle.begin_world_transition()
        try:
            stopped = paper.stop_and_save()
            if (
                stopped.old_server_session_id != before.paper_session_id
                or stopped.world_id != before.world_id
                or stopped.branch_id != before.branch_id
                or type(stopped.logical_tick) is not int
                or stopped.logical_tick < before.world_tick
                or stopped.process_exit_code != 0
                or stopped.all_dimensions_saved is not True
            ):
                raise WorldOnlyCheckpointError("stopped Paper World source mismatch")
            generation_id = f"world-only-{self._sequence:012d}"
            target = self.store / generation_id
            if target.exists() or target.is_symlink():
                raise WorldOnlyCheckpointError("World-only generation already exists")
            target.mkdir(mode=0o700)
            capture_stopped_world(
                paper.world_dir, target / "world",
                world_id=before.world_id, branch_id=before.branch_id,
                checkpoint_id=generation_id, logical_tick=stopped.logical_tick,
                tick_source_ref=stopped.tick_source_ref,
                stopped_server_ref=stopped.stopped_server_ref,
            )
            companions = _paper_siblings(paper.world_dir)
            hashes: dict[str, str] = {}
            if companions:
                folder = target / "paper-dimensions"
                folder.mkdir(mode=0o700)
                for name, source in companions:
                    result_dir = folder / name
                    capture_stopped_world(
                        source, result_dir,
                        world_id=before.world_id, branch_id=before.branch_id,
                        checkpoint_id=generation_id,
                        logical_tick=stopped.logical_tick,
                        tick_source_ref=stopped.tick_source_ref,
                        stopped_server_ref=stopped.stopped_server_ref,
                        paper_companion=True,
                    )
                    hashes[name] = _hash(result_dir / "manifest.json")
            _new_json(target / "WORLD_ONLY_COMMITTED.json", {
                "schema": 1, "generation_id": generation_id,
                "world_id": before.world_id, "branch_id": before.branch_id,
                "old_paper_session_id": before.paper_session_id,
                "declared_tick": stopped.logical_tick,
                "world_manifest_sha256": _hash(
                    target / "world" / "manifest.json"
                ),
                "paper_dimensions": hashes, "owner_self_count": 0,
                "self_cognition_mutated": False,
                "historical_replay_performed": False,
                "action_issue_authorized": False,
            })
            verify_world_only_generation(target)
            restarted = paper.restart_same_source_world()
            if (
                restarted.world_id != before.world_id
                or restarted.branch_id != before.branch_id
                or restarted.server_started is not True
                or restarted.new_server_session_id == before.paper_session_id
                or restarted.new_server_session_id != paper.owned_session_id
            ):
                raise WorldOnlyCheckpointError("new owned Paper process unavailable")
            new = WorldLifetime(
                before.world_id, before.branch_id,
                restarted.new_server_session_id, before.epoch + 1,
                stopped.logical_tick,
            )
            self.lifecycle.install_world(WorldInstallationEvidence(
                before, new, "owned-paper:" + restarted.new_server_session_id,
                True, True, True, True,
            ))
            self._sequence += 1
            return WorldOnlyResult(target, before, new, stopped.logical_tick)
        except BaseException:
            self._held = True
            self.lifecycle.abort_world_transition()
            raise
