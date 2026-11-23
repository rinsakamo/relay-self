"""I2e no-World preflight for a NEW original A/B v3 recorded empty Schema.

This is NOT the historical Stage28b source and does not grant World/GPU/Action
authority. A future real runner must use this qualified original Owner, never
fall back to the pinned 2026-11-18 legacy source or silently seed Registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relay_self.cognitive_minimal_dev import Predicate
from relay_self.i_lane_i2c_original_schema_restore_dev import (
    bootstrap_original_recorded_a_b_schemas,
)
from relay_self.stage28c2_recovered_resident_owner_dev import (
    Stage28c2aOfflineOwners,
    prepare_recovered_a_b_resident_owners,
)


class I2eFutureSourceHold(RuntimeError):
    """Same-Self source/Schema not independently eligible for new World."""


@dataclass(slots=True, eq=False)
class I2eFutureSourcePreflight:
    restored: Stage28c2aOfflineOwners
    committed_sha256: str
    source_world_id: str
    restored_branch_id: str
    schema_recovered_a_b: bool = True
    original_selves_offline: bool = True
    model_post_count: int = 0
    paper_started: bool = False
    native_rejoined: bool = False
    physical_action_issue_authorized: bool = False


def preflight_i2e_future_source(
    *, generation: Path, restored: Path,
    expected_world_id: str, expected_source_branch_id: str,
    expected_committed_sha256: str, expected_fork_branch_id: str,
) -> I2eFutureSourcePreflight:
    """Reverify exact committed original cognition and actual recorded OFF config.

    This returns ephemeral OFFLINE Owner handles for *future* original
    OwnedResidentPhysicalBridge execution; not a qualified real-World run.
    """
    try:
        staged = prepare_recovered_a_b_resident_owners(
            generation, restored,
            expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
            expected_committed_sha256=expected_committed_sha256,
            expected_fork_branch_id=expected_fork_branch_id,
            observation_only=True,
        )
        receipt = bootstrap_original_recorded_a_b_schemas(
            recovered=staged, generation=generation, restored_directory=restored,
        )
        if (receipt.restored_self_ids != ("A", "B")
                or receipt.committed_sha256 != expected_committed_sha256
                or not staged.physical.all_residents_offline
                or staged.physical.active_action_ids
                or not staged.physical.observation_only):
            raise I2eFutureSourceHold("original future Self/physical scope not offline")
        for sid in ("A", "B"):
            owner = staged.owners[sid]
            snapshot = staged.cognitive_work._present_schemas[sid][0]
            if (
                snapshot.modules
                or owner.retained.pattern_registry != owner.pattern_registry
                or any(p.schema_id == "exploration" or
                       p.predicate is Predicate.EXPLORE
                       for p in owner.pattern_registry.patterns)
                or owner.intent.current_intent is not None
                or not owner.fresh_native_observation_required
                or owner.supervisor.open_actions
                or owner.pending_questions
            ):
                raise I2eFutureSourceHold(
                    "new exploration adoption requires recorded empty original Schema"
                )
        return I2eFutureSourcePreflight(
            staged, receipt.committed_sha256, staged.plan.source_world_id,
            staged.plan.fork_branch_id,
        )
    except I2eFutureSourceHold:
        raise
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, AttributeError) as exc:
        raise I2eFutureSourceHold(
            "new original v3 recorded Schema source unqualified; no World"
        ) from exc
