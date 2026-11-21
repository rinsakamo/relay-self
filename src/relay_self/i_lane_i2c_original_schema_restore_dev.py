"""I2c DEV: rebootstrap only from same-generation original recorded Schema.

This is an explicit OFFLINE call after the real Stage28c2a pinned-generation
readback. No Schema inference from the PatternRegistry and no new owner, Goal,
Question, L1 work, model HTTP call or physical execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.self_owner_checkpoint_dev import (
    load_self_owner_cut,
    verify_typed_generation,
)
from relay_self.stage28c2_recovered_resident_owner_dev import (
    Stage28c2aOfflineOwners,
    _hash_file,
)


class I2cRestoredSchemaHold(RuntimeError):
    """No complete original source-authenticated Schema activation."""


@dataclass(frozen=True, slots=True)
class I2cRestoredSchemaReceipt:
    generation_id: str
    committed_sha256: str
    restored_self_ids: tuple[str, ...]
    recorded_schema_by_self: tuple[tuple[str, int, tuple[str, ...]], ...]
    live_native_bound: bool = False
    model_invoked: bool = False
    schema_invented: bool = False
    question_adopted: bool = False
    goal_adopted: bool = False
    physical_action_authorized: bool = False


def bootstrap_original_recorded_a_b_schemas(
    *, recovered: Stage28c2aOfflineOwners,
    generation: Path,
    restored_directory: Path,
) -> I2cRestoredSchemaReceipt:
    """Register the *recorded* original A/B schemas once, before new JOIN.

    A missing record in any Self is HOLD for the operation, even if that
    Self's Registry currently contains an eligible exploration Pattern.
    Old Stage28b schema1/2 cuts never gain FULL by heuristic.
    """
    if (type(recovered) is not Stage28c2aOfflineOwners
            or not isinstance(generation, Path)
            or not isinstance(restored_directory, Path)
            or not isinstance(recovered.cognitive_work, ResidentCognitiveWorkOwner)):
        raise I2cRestoredSchemaHold("original offline restored Owner required")
    resident = recovered.cognitive_work
    with resident.lock:
        try:
            if (generation.is_symlink() or restored_directory.is_symlink()
                    or recovered.receipt.generation_id != generation.name
                    or recovered.plan.generation_id != generation.name
                    or recovered.receipt.source_committed_sha256
                    != _hash_file(generation / "COMMITTED.json")
                    or tuple(sorted(recovered.owners)) != ("A", "B")
                    or not recovered.physical.all_residents_offline
                    or recovered.physical.active_action_ids
                    or resident._present_schemas):
                raise I2cRestoredSchemaHold("source generation or offline owner stale")
            # Verify the whole original committed generation again, not an
            # owner-state.json supplied independently of its generation.
            original_cuts = verify_typed_generation(generation)
            if tuple(c.self_id for c in original_cuts) != ("A", "B"):
                raise I2cRestoredSchemaHold("missing original A/B typed cut")
            expected_files = dict(
                ((sid, filename), digest)
                for sid, filename, digest
                in recovered.receipt.verified_self_file_sha256
            )
            if len(expected_files) != 6:
                raise I2cRestoredSchemaHold("complete same-generation Self file pins required")
            candidates = {c.self_id: c.semantic.cut for c in recovered.plan.candidates}
            if set(candidates) != {"A", "B"}:
                raise I2cRestoredSchemaHold("foreign restored cut roster")
            snapshots = []
            for cut in original_cuts:
                sid = cut.self_id
                owner = recovered.owners[sid]
                state = resident._state(sid)
                restored_root = restored_directory / "selves" / sid
                archived_root = generation / "selves" / sid
                if (state.mode != "OFFLINE" or state.epoch != 0
                        or state.retired is not None or state.tasks or state.staged_peer
                        or owner.cohort is not resident
                        or not owner.fresh_native_observation_required
                        or cut.generation_id != generation.name
                        or cut.world_id != recovered.plan.source_world_id
                        or cut.branch_id != recovered.plan.source_branch_id
                        or cut.pattern_registry != owner.pattern_registry
                        or cut.recorded_schema is None
                        or cut.recorded_schema.self_id != sid
                        or cut.recorded_schema.revision != owner.pattern_registry.revision):
                    raise I2cRestoredSchemaHold("original recorded Self Schema unavailable")
                # Re-read each original and restored file, not just its name,
                # then match the reconstructed original typed owner.
                for filename in ("cognition.json", "owner-state.json", "physical-wal.json"):
                    key = (sid, filename)
                    if (key not in expected_files
                            or _hash_file(restored_root / filename) != expected_files[key]
                            or _hash_file(archived_root / filename) != expected_files[key]):
                        raise I2cRestoredSchemaHold("original/restored Self source changed")
                if (load_self_owner_cut(restored_root / "owner-state.json") != cut
                        or candidates[sid] != cut):
                    raise I2cRestoredSchemaHold("restored saved Schema differs from committed cut")
                snapshots.append((sid, cut.recorded_schema))
            # All reads and validation above are complete before publishing
            # any Schema. Existing original resident validation remains the
            # authoritative exact Pattern/Mode/Version gate.
            try:
                for sid, snapshot in snapshots:
                    resident.register_present_schema(sid, snapshot)
            except (RuntimeError, ValueError):
                # Never leave only A's Schema installed if B is invalid.
                resident._present_schemas.clear()
                raise
            return I2cRestoredSchemaReceipt(
                generation.name, recovered.receipt.source_committed_sha256,
                tuple(s for s, _ in snapshots),
                tuple((
                    sid, snapshot.revision,
                    tuple(a.spec.schema_id + ":" + a.mode.value for a in snapshot.modules),
                ) for sid, snapshot in snapshots),
            )
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
            if isinstance(exc, I2cRestoredSchemaHold):
                raise
            raise I2cRestoredSchemaHold(
                "recorded original Schema rebootstrap unqualified; stay OFFLINE"
            ) from exc
