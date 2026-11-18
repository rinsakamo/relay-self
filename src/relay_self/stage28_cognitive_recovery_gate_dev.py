"""Stage28a: inert same-generation World + A/B Self recovery admission.

This is a *read-only* checkpoint verification and fresh-source reevaluation
boundary. It does not revive a Self, issue an Action, replay a WAL or invoke L1.
World-only checkpoint archives are intentionally NOT cognitive checkpoints.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from relay_self.checkpointed_cognitive_runtime_dev import (
    StagedRecoveredCognition,
    staged_recover_cognition_cohort,
)
from relay_self.coordinated_checkpoint_dev import verify_generation
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.world_checkpoint_dev import verify_world_checkpoint
from relay_self.world_resident_lifecycle_dev import (
    NativeLoginEvidence,
    WorldLifetime,
)


class Stage28RecoveryHold(RuntimeError):
    """The source and new WorldBody cannot be admitted as one continuity cut."""


@dataclass(frozen=True, slots=True)
class Stage28InertRecovery:
    """Validated snapshots only. Cannot issue or redeliver any physical effect."""

    generation_id: str
    source_world_id: str
    source_branch_id: str
    fork_branch_id: str
    declared_world_tick: int
    roster: tuple[str, ...]
    old_native_sessions: tuple[tuple[str, str], ...]
    cut_ticks: tuple[tuple[str, int], ...]
    candidates: tuple[StagedRecoveredCognition, ...]
    old_action_replay_authorized: bool = False
    old_skill_resume_authorized: bool = False
    old_message_redelivery_authorized: bool = False
    old_l1_decision_reusable: bool = False
    physical_action_issue_authorized: bool = False
    l1_reevaluation_eligible: bool = False
    source_committed_sha256: str = ""


@dataclass(frozen=True, slots=True)
class Stage28ForkPaperEpoch:
    """Owned Paper boot proof for the *new* process tick domain.

    The source stopped tick remains immutable history, NOT a comparable
    wall-clock or process tick offset. A live runner must create this from
    a source-validated execution copy and Paper main-thread ACK/log.
    """

    generation_id: str
    source_world_id: str
    source_branch_id: str
    source_declared_tick: int
    fork_branch_id: str
    committed_sha256: str
    paper_session_id: str
    paper_boot_id: str
    world_epoch: int
    boot_tick: int
    paper_tick_source_ref: str
    paper_pid: int
    historical_native_sessions: tuple[str, ...]
    old_ticks_directly_comparable: bool = False
    replay_authorized: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Stage28NativePaperBodyLink:
    """Paper process tick and native Minecraft day time are DIFFERENT clocks.

    A verifier must obtain this from the original live native owner and
    independently owned Paper JOIN/PRESENT log + fresh tick nonce ACK.
    Merely constructing this dataclass is NOT evidence of a real World trial.
    """

    self_id: str
    native_session_id: str
    native_probe_ref: str
    native_world_time_tick: int
    paper_session_id: str
    tick_boot_id: str
    presence_boot_id: str
    paper_observed_tick: int
    paper_tick_source_ref: str
    paper_log_sha256: str
    paper_actor_uuid: str
    clocks_numerically_comparable: bool = False
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Stage28FreshL1Eligibility:
    generation_id: str
    world_id: str
    fork_branch_id: str
    paper_session_id: str
    world_epoch: int
    native_sessions: tuple[tuple[str, str], ...]
    l1_reevaluation_eligible: bool = True
    old_l1_decision_reusable: bool = False
    old_skill_resume_authorized: bool = False
    historical_action_replayed: bool = False
    physical_action_issue_authorized: bool = False
    source_saved_world_tick: int = 0
    new_process_boot_tick: int = 0
    new_paper_boot_id: str = ""
    source_and_new_ticks_comparable: bool = False


def _file_hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Stage28RecoveryHold("restored World file missing or symlinked")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def _require_restored_world_files(directory: Path, archived: dict) -> None:
    """Compare every restored World byte against the verified archived cut."""
    if directory.is_symlink() or not directory.is_dir():
        raise Stage28RecoveryHold("restored World directory unavailable")
    expected = {row["path"]: row for row in archived["files"]}
    observed: set[str] = set()
    for item in directory.rglob("*"):
        if item.is_symlink():
            raise Stage28RecoveryHold("restored World symlink forbidden")
        if item.is_file():
            rel = item.relative_to(directory).as_posix()
            if rel in observed:
                raise Stage28RecoveryHold("duplicate restored file")
            observed.add(rel)
        elif not item.is_dir():
            raise Stage28RecoveryHold("unknown restored World node")
    if observed != set(expected):
        raise Stage28RecoveryHold("restored World inventory differs from exact generation")
    for rel, row in expected.items():
        file = directory / rel
        if file.stat().st_size != row["size"] or _file_hash(file) != row["sha256"]:
            raise Stage28RecoveryHold("restored World bytes differ from committed cut")


def stage28_inert_cognitive_recovery(
    generation: Path, restored_directory: Path, *,
    expected_self_ids: tuple[str, ...],
    expected_source_world_id: str,
) -> Stage28InertRecovery:
    """Qualify one *typed* World+A/B cut, never pair independent C and W ticks.

    Both the source generation and branched restore must be independently
    committed/verified. The returned candidate is *still inert*: restoring
    JSON/WAL files neither authorizes a physical Action nor an L1 inference.
    """
    if (
        type(expected_self_ids) is not tuple
        or not expected_self_ids
        or any(type(sid) is not str or not sid for sid in expected_self_ids)
        or len(set(expected_self_ids)) != len(expected_self_ids)
        or not isinstance(expected_source_world_id, str)
        or not expected_source_world_id
    ):
        raise Stage28RecoveryHold("explicit exact Self roster and source World ID required")
    generation = Path(generation)
    restored_directory = Path(restored_directory)
    try:
        # A World-only archive has no COMMITTED typed Self roster, and fails.
        cuts = verify_typed_generation(generation)
        manifest = verify_generation(generation)
        archived = verify_world_checkpoint(generation / "world")
        if (
            tuple(sorted(expected_self_ids)) != tuple(manifest["roster"])
            or archived["world_id"] != expected_source_world_id
            or not cuts
            or any(c.last_observed_world_tick > manifest["declared_tick"] for c in cuts)
        ):
            raise Stage28RecoveryHold(
                "Self cut roster/tick is inconsistent with the same World generation"
            )
        # This further validates typed copied owners, original WAL and
        # world.restore/RESTORE_PREPARED source-generation receipts.
        candidates = staged_recover_cognition_cohort(generation, restored_directory)
        if tuple(c.self_id for c in candidates) != tuple(sorted(expected_self_ids)):
            raise Stage28RecoveryHold("restored Self roster incomplete or foreign")
        _require_restored_world_files(restored_directory / "world", archived)
        for dim in manifest.get("paper_dimensions", {}):
            companion = verify_world_checkpoint(
                generation / "paper-dimensions" / dim
            )
            _require_restored_world_files(restored_directory / dim, companion)
        prepared = json.loads(
            (restored_directory / "RESTORE_PREPARED.json").read_bytes()
        )
        fork_branch = prepared["fork_branch_id"]
        if (
            type(fork_branch) is not str or not fork_branch
            or fork_branch == archived["branch_id"]
            or any(c.native_session_bound or c.issue_authorized
                   or c.conversation_redelivery_authorized for c in candidates)
            or any(not c.fresh_worldbody_required for c in candidates)
        ):
            raise Stage28RecoveryHold("new branch or inert recovery boundary missing")
    except Stage28RecoveryHold:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise Stage28RecoveryHold(
            "typed World+A/B recovery source unverified; World-only is insufficient"
        ) from exc
    return Stage28InertRecovery(
        generation.name, archived["world_id"], archived["branch_id"],
        fork_branch, manifest["declared_tick"],
        tuple(manifest["roster"]),
        tuple((c.self_id, c.former_native_session_id) for c in cuts),
        tuple((c.self_id, c.last_observed_world_tick) for c in cuts),
        candidates,
        source_committed_sha256=_file_hash(generation / "COMMITTED.json"),
    )


def stage28_require_fresh_l1_eligibility(
    plan: Stage28InertRecovery, *,
    world: WorldLifetime,
    logins: tuple[NativeLoginEvidence, ...],
    idle: LlamaSlotIdleReceipt,
    boot: Stage28ForkPaperEpoch,
    links: tuple[Stage28NativePaperBodyLink, ...],
) -> Stage28FreshL1Eligibility:
    """One fresh evidence gate for *reevaluation*, not physical Action issue.

    Callers must obtain actual native probes, GPU owner and Paper session
    evidence through the existing owners. This does not call the L1 model.
    """
    if (
        not isinstance(plan, Stage28InertRecovery)
        or not isinstance(boot, Stage28ForkPaperEpoch)
        or not isinstance(world, WorldLifetime)
        or type(logins) is not tuple
        or type(links) is not tuple
        or not isinstance(idle, LlamaSlotIdleReceipt)
        or world.world_id != plan.source_world_id
        or world.branch_id != plan.fork_branch_id
        or type(world.epoch) is not int or world.epoch < 1
        or boot.generation_id != plan.generation_id
        or boot.source_world_id != plan.source_world_id
        or boot.source_branch_id != plan.source_branch_id
        or boot.source_declared_tick != plan.declared_world_tick
        or boot.fork_branch_id != plan.fork_branch_id
        or boot.paper_session_id != world.paper_session_id
        or boot.world_epoch != world.epoch
        or type(boot.boot_tick) is not int or boot.boot_tick < 0
        or world.world_tick < boot.boot_tick
        or type(boot.committed_sha256) is not str
        or len(boot.committed_sha256) != 64
        or boot.committed_sha256 != plan.source_committed_sha256
        or not boot.paper_session_id.startswith("paper-owned-")
        or not boot.paper_boot_id
        or not boot.paper_tick_source_ref.startswith(
            "paper-main-thread:p0d:" + boot.paper_boot_id + ":"
        )
        or boot.paper_pid <= 0
        or boot.old_ticks_directly_comparable is not False
        or boot.replay_authorized is not False
        or boot.physical_action_issue_authorized is not False
        or type(boot.historical_native_sessions) is not tuple
        or len(set(boot.historical_native_sessions)) != len(boot.historical_native_sessions)
        or not set(dict(plan.old_native_sessions).values()).issubset(
            boot.historical_native_sessions
        )
        or not idle.backend_ref or idle.is_processing
        or idle.slot_id != 0 or idle.n_slots != 1
        or idle.request_issue_authorized
    ):
        raise Stage28RecoveryHold("fresh World and single idle GPU slot required")
    old = dict(plan.old_native_sessions)
    if len(logins) != len(plan.roster) or any(
        not isinstance(proof, NativeLoginEvidence) for proof in logins
    ):
        raise Stage28RecoveryHold("full A/B native evidence required")
    by_self = {p.self_id: p for p in logins}
    if set(by_self) != set(plan.roster):
        raise Stage28RecoveryHold("new native roster missing, duplicate or foreign")
    if (
        len(links) != len(plan.roster)
        or any(not isinstance(link, Stage28NativePaperBodyLink)
               for link in links)
        or len({link.self_id for link in links}) != len(links)
        or {link.self_id for link in links} != set(plan.roster)
        or len({link.paper_actor_uuid for link in links}) != len(links)
    ):
        raise Stage28RecoveryHold("original Paper/native A+B body links required")
    by_link = {link.self_id: link for link in links}
    sessions = [p.native_session_id for p in logins]
    if len(set(sessions)) != len(sessions) or set(sessions) & (
        set(old.values()) | set(boot.historical_native_sessions)
    ):
        raise Stage28RecoveryHold("replayed original or duplicate native session")
    for sid in plan.roster:
        p = by_self[sid]
        if (
            p.world_id != world.world_id
            or p.branch_id != world.branch_id
            or p.paper_session_id != world.paper_session_id
            or p.world_epoch != world.epoch
            # Native World time is Minecraft day clock, not Bukkit tick.
            # Require native/Paper source linkage instead of numeric compare.
            or type(p.observed_world_tick) is not int
            or p.observed_world_tick < 0
            or not p.observation_ref
            or not p.old_native_invalidated
            or not p.physical_wal_clear
            or not p.stale_gpu_fenced
            or not p.stale_transport_fenced
            or not p.new_native_source_verified
            or p.action_issue_authorized
            or by_link[sid].native_session_id != p.native_session_id
            or by_link[sid].native_probe_ref != p.observation_ref
            or by_link[sid].native_world_time_tick != p.observed_world_tick
            or by_link[sid].paper_session_id != world.paper_session_id
            or by_link[sid].tick_boot_id != boot.paper_boot_id
            or not by_link[sid].presence_boot_id
            or by_link[sid].paper_observed_tick < boot.boot_tick
            or by_link[sid].paper_observed_tick > world.world_tick
            or not by_link[sid].paper_tick_source_ref.startswith(
                "paper-main-thread:p0d:" + boot.paper_boot_id + ":"
            )
            or len(by_link[sid].paper_log_sha256) != 64
            or not by_link[sid].paper_actor_uuid
            or by_link[sid].clocks_numerically_comparable is not False
            or by_link[sid].physical_action_issue_authorized is not False
        ):
            raise Stage28RecoveryHold(
                "fresh WorldBody/stale-work fence missing for one Self"
            )
    return Stage28FreshL1Eligibility(
        plan.generation_id, world.world_id, world.branch_id,
        world.paper_session_id, world.epoch,
        tuple((sid, by_self[sid].native_session_id) for sid in plan.roster),
        source_saved_world_tick=plan.declared_world_tick,
        new_process_boot_tick=boot.boot_tick,
        new_paper_boot_id=boot.paper_boot_id,
    )
