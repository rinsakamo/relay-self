"""Stage28c2a: reconstruct original A/B cognition behind an inert resident gate.

Source is the exact committed Stage28b typed World/Self cut and the verified
Stage28c1 fork. No Paper/native connection, no new L1, no Action/peer replay.
Only the existing canonical CheckpointedCognitiveOwner and
ResidentCognitiveWorkOwner are instantiated; no parallel cohort.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
)
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    SchemaBootstrapHold,
    bootstrap_restored_schemas,
)
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28InertRecovery,
    stage28_inert_cognitive_recovery,
)
from relay_self.stage28c1_inert_restore_dev import inspect_stage28c_source


class Stage28c2OwnerHold(RuntimeError):
    """Inconsistent source or owner, or unexpected ability to issue an Action."""


@dataclass(frozen=True, slots=True)
class Stage28c2aOwnerReceipt:
    generation_id: str
    source_world_id: str
    fork_branch_id: str
    source_cut_ticks: tuple[tuple[str, int], ...]
    original_native_sessions: tuple[tuple[str, str], ...]
    verified_self_file_sha256: tuple[tuple[str, str, str], ...]
    owner_roster: tuple[str, ...] = ("A", "B")
    active_native_rejoined: bool = False
    real_paper_started: bool = False
    fresh_worldbody_observed: bool = False
    old_skill_replayed: bool = False
    old_l1_decision_reused: bool = False
    physical_action_issue_authorized: bool = False
    l1_reevaluation_eligible: bool = False
    source_committed_sha256: str = ""


@dataclass(slots=True)
class Stage28c2aOfflineOwners:
    """Prepared owners. Object handles are not a claim of active cognition."""

    plan: Stage28InertRecovery
    owners: dict[str, CheckpointedCognitiveOwner]
    cognitive_work: ResidentCognitiveWorkOwner
    physical: PhysicalIssueAdmission
    receipt: Stage28c2aOwnerReceipt


def _hash_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Stage28c2OwnerHold("typed Self source or restored file unavailable")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while part := stream.read(1024 * 1024):
            h.update(part)
    return h.hexdigest()


def prepare_recovered_a_b_resident_owners(
    generation: Path,
    restored_directory: Path,
    *,
    expected_world_id: str,
    expected_source_branch_id: str,
    expected_committed_sha256: str,
    expected_fork_branch_id: str,
    observation_only: bool = False,
    schema_bootstrap: SchemaBootstrapConfig | None = None,
) -> Stage28c2aOfflineOwners:
    """Verify full typed source+fork, rebuild original A/B objects *offline*.

    Never constructs a new innate/default Self. The actor stays OFFLINE, original
    old session IDs are rejection tokens, original WAL remains clear and the
    existing PhysicalIssueAdmission starts with both residents OFFLINE.
    """
    generation = Path(generation)
    restored = Path(restored_directory)
    try:
        source = inspect_stage28c_source(
            generation, expected_world_id=expected_world_id,
            expected_source_branch_id=expected_source_branch_id,
        )
        if (
            source.committed_sha256 != expected_committed_sha256
            or type(expected_fork_branch_id) is not str
            or not expected_fork_branch_id
            or source.roster != ("A", "B")
        ):
            raise Stage28c2OwnerHold("source COMMITTED/fork/roster pin mismatch")
        plan = stage28_inert_cognitive_recovery(
            generation, restored, expected_self_ids=("A", "B"),
            expected_source_world_id=expected_world_id,
        )
        if plan.fork_branch_id != expected_fork_branch_id:
            raise Stage28c2OwnerHold("restored branch differs from pinned fork")
        if (
            plan.roster != source.roster
            or plan.cut_ticks != source.self_cut_ticks
            or plan.declared_world_tick != source.declared_world_tick
        ):
            raise Stage28c2OwnerHold("typed A/B recovery differs from source cut")

        owners: dict[str, CheckpointedCognitiveOwner] = {}
        sha_rows: list[tuple[str, str, str]] = []
        old_ids: dict[str, str] = {}
        for candidate in plan.candidates:
            sid = candidate.self_id
            if (
                sid not in ("A", "B")
                or sid in owners
                or candidate.retained.identity.self_id != sid
                or candidate.semantic.cut.self_id != sid
                or candidate.semantic.cut.world_id != plan.source_world_id
                or candidate.semantic.cut.branch_id != plan.source_branch_id
                or not candidate.fresh_worldbody_required
                or candidate.native_session_bound
                or candidate.issue_authorized
                or candidate.conversation_redelivery_authorized
            ):
                raise Stage28c2OwnerHold("candidate foreign or already activated")
            original_root = generation / "selves" / sid
            restored_root = restored / "selves" / sid
            if restored_root.is_symlink() or not restored_root.is_dir():
                raise Stage28c2OwnerHold("restored Self root unavailable")
            # Original Stage28a's World-file equality gate does not alone
            # byte-attest every restored Self cognition/WAL. Verify all three.
            for file in ("cognition.json", "owner-state.json", "physical-wal.json"):
                original_hash = _hash_file(original_root / file)
                if original_hash != _hash_file(restored_root / file):
                    raise Stage28c2OwnerHold(
                        "restored Self cognition/owner/WAL changed after typed restore"
                    )
                sha_rows.append((sid, file, original_hash))

            semantics = candidate.semantic
            cut = semantics.cut
            old_ids[sid] = cut.former_native_session_id
            owner = CheckpointedCognitiveOwner(
                retained=candidate.retained,
                intent=semantics.intent,
                pattern_registry=semantics.pattern_registry,
                native_session_id=cut.former_native_session_id,
                last_observed_tick=cut.last_observed_world_tick,
                files=CognitiveOwnerFiles(
                    restored_root,
                    restored_root / "cognition.json",
                    restored_root / "physical-wal.json",
                ),
                physical_supervisor=ActionSupervisor(),
                skills=semantics.skill_histories,
                peer_deliveries=cut.peer_deliveries,
                pending_questions=cut.pending_question_refs,
            )
            # Historical observations are not the new Present projection.
            owner.fresh_native_observation_required = True
            owners[sid] = owner

        if (
            tuple(sorted(owners)) != source.roster
            or len(set(old_ids.values())) != 2
        ):
            raise Stage28c2OwnerHold("full unique original A/B session roster required")
        work = ResidentCognitiveWorkOwner(owners)
        saved_cuts = tuple(candidate.semantic.cut for candidate in plan.candidates)
        if schema_bootstrap is not None or any(
            cut.schema_snapshot is not None for cut in saved_cuts
        ):
            bootstrap_restored_schemas(
                work, schema_bootstrap, source_cuts=saved_cuts,
            )
        physical = PhysicalIssueAdmission(
            old_ids,
            resident_mode=True, initially_offline=True,
            allow_resident_move=False,
            observation_only=observation_only,
        )
        if (
            not physical.all_residents_offline
            or physical.active_action_ids
            or any(owner.supervisor.open_actions for owner in owners.values())
            or any(owner.cohort is not work
                   or not owner.fresh_native_observation_required
                   for owner in owners.values())
        ):
            raise Stage28c2OwnerHold("restored original owner has live authority")
    except SchemaBootstrapHold as exc:
        raise Stage28c2OwnerHold(f"schema bootstrap HOLD: {exc}") from exc
    except Stage28c2OwnerHold:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise Stage28c2OwnerHold(
            "original typed A/B owner restore not qualified; stay offline"
        ) from exc

    receipt = Stage28c2aOwnerReceipt(
        source.generation_id,
        plan.source_world_id, plan.fork_branch_id,
        plan.cut_ticks, tuple(sorted(old_ids.items())),
        tuple(sorted(sha_rows)),
        source_committed_sha256=source.committed_sha256,
    )
    return Stage28c2aOfflineOwners(plan, owners, work, physical, receipt)
