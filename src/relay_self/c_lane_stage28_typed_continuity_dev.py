"""C Lane: C1 Memory continuity across ORIGINAL Stage28 typed A/B World cut.

Read-only verification boundary. The original Stage28 source and restored
execution-copy paths own physical persistence and rejoin. This code never
issues Actions, inserts Memory, resumes Skills, starts inference or constructs
an alternate cognition owner.

A committed C1-shaped Memory surviving a *typed* World+A/B checkpoint is NOT
proof that a historical Action happened in a real World, nor that C2 was
learned or an L1 choice changed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.persistent_cognition import Memory, load_persistent_cognition
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28FreshL1Eligibility,
)
from relay_self.stage28c2b_execution_copy_dev import ExecutionCopy
from relay_self.self_owner_checkpoint_dev import verify_typed_generation


class C1TypedCheckpointHold(RuntimeError):
    """Original committed A/B memory source or current World is unqualified."""


@dataclass(frozen=True, slots=True)
class C1TypedContinuityWitness:
    """Historical source readback; NEVER Action/Skill/Goal authorization."""

    memory_id: str
    self_id: str
    source_world_id: str
    generation_id: str
    source_committed_sha256: str
    source_cognition_sha256: str
    original_native_session_id: str
    new_native_session_id: str
    new_world_epoch: int
    new_native_seq: int
    historical_memory_retained: bool = True
    new_l1_reassessment_required: bool = True
    historical_action_replayed: bool = False
    old_skill_resume_authorized: bool = False
    physical_action_issue_authorized: bool = False
    real_historical_world_action_attested: bool = False


def _safe_sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise C1TypedCheckpointHold("typed source/copy file is not regular")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_c1_across_stage28_typed_epoch(
    *,
    source_generation: Path,
    copy: ExecutionCopy,
    eligibility: Stage28FreshL1Eligibility,
    boot: Stage28ForkPaperEpoch,
    original_self_id: str,
    memory_id: str,
    new_probe: MineflayerObservation,
) -> C1TypedContinuityWitness:
    """Read one original C1 across *the same* committed World+A/B typed cut.

    This independently rechecks the archived and restored cognition bytes,
    original two-Self owner identities, source COMMITTED SHA and the exact
    new-session qualified Stage28 native/Paper epoch. The typed Stage28 L1
    eligibility is an upstream live-source verifier receipt, not synthesized
    or recalculated from old C1 content here.

    No WORLD_ONLY cut can pass. Old and new Paper ticks are never compared.
    """
    if (
        not isinstance(source_generation, Path)
        or not isinstance(copy, ExecutionCopy)
        or not isinstance(eligibility, Stage28FreshL1Eligibility)
        or not isinstance(boot, Stage28ForkPaperEpoch)
        or original_self_id not in ("A", "B")
        or type(memory_id) is not str
        or not memory_id.startswith("c1-skillrun:")
        or not isinstance(new_probe, MineflayerObservation)
    ):
        raise C1TypedCheckpointHold("typed complete source/owner/probe required")
    source = source_generation
    plan, recovered = copy.recovered.plan, copy.recovered
    if (
        source.is_symlink() or not source.is_dir()
        or copy.directory.is_symlink() or not copy.directory.is_dir()
        or tuple(sorted(recovered.owners)) != ("A", "B")
        or plan.roster != ("A", "B")
        or plan.generation_id != source.name
        or plan.source_world_id != eligibility.world_id
        or eligibility.generation_id != plan.generation_id
        or eligibility.fork_branch_id != plan.fork_branch_id
        or boot.generation_id != plan.generation_id
        or boot.source_world_id != plan.source_world_id
        or boot.source_branch_id != plan.source_branch_id
        or boot.fork_branch_id != plan.fork_branch_id
        or boot.world_epoch != eligibility.world_epoch
        or boot.paper_session_id != eligibility.paper_session_id
        or boot.paper_boot_id != eligibility.new_paper_boot_id
        or boot.committed_sha256 != plan.source_committed_sha256
        or not eligibility.l1_reevaluation_eligible
        or eligibility.old_l1_decision_reusable
        or eligibility.old_skill_resume_authorized
        or eligibility.historical_action_replayed
        or eligibility.physical_action_issue_authorized
        or boot.replay_authorized or boot.physical_action_issue_authorized
    ):
        raise C1TypedCheckpointHold("source and new World/L1 epoch identity disagrees")
    try:
        cuts = verify_typed_generation(source)
    except (OSError, ValueError, RuntimeError) as exc:
        raise C1TypedCheckpointHold("not a verified original typed World+A/B cut") from exc
    if (
        {c.self_id for c in cuts} != {"A", "B"}
        or plan.source_committed_sha256 != _safe_sha(source / "COMMITTED.json")
        or len(eligibility.native_sessions) != 2
        or {sid for sid, _ in eligibility.native_sessions} != {"A", "B"}
        or len({s for _, s in eligibility.native_sessions}) != 2
    ):
        raise C1TypedCheckpointHold("incomplete or changed canonical A/B generation")
    by_cut = {c.self_id: c for c in cuts}
    old_native = by_cut[original_self_id].former_native_session_id
    if (
        dict(plan.old_native_sessions).get(original_self_id) != old_native
        or old_native not in boot.historical_native_sessions
    ):
        raise C1TypedCheckpointHold("old Self native lineage absent from source cut")
    owner = recovered.owners[original_self_id]
    new_session = dict(eligibility.native_sessions)[original_self_id]
    if (
        owner.self_id != original_self_id
        or owner.cohort is not recovered.cognitive_work
        or recovered.cognitive_work.owners.get(original_self_id) is not owner
        or owner.fresh_native_observation_required
        or owner.native_session_id != new_session
        or new_session == old_native
        or new_session in boot.historical_native_sessions
        or new_probe.session_id != new_session
        or new_probe.kind != "probe"
        or not new_probe.request_id
        or new_probe.provenance.source != "mineflayer"
        or new_probe.provenance.reference != f"{new_session}:{new_probe.seq}"
        or new_probe.snapshot.time is None
        or owner.current_worldbody_observation != new_probe
        or recovered.cognitive_work.current_scope(original_self_id)[1:] != (
            new_session, eligibility.world_epoch
        )
    ):
        raise C1TypedCheckpointHold("original Owner did not adopt a fresh new native source")

    # The source is a COMMITTED original generation, not an arbitrary
    # post-rejoin JSON. Each staged executable owner must inherit the exact
    # archived cognition bytes, including any retained C1 episode.
    archived = source / "selves" / original_self_id / "cognition.json"
    copied = copy.directory / "selves" / original_self_id / "cognition.json"
    if (
        owner.files.cognition_file.resolve() != copied.resolve()
        or _safe_sha(archived) != _safe_sha(copied)
    ):
        raise C1TypedCheckpointHold("original and restored source cognition changed")
    try:
        historical = load_persistent_cognition(archived)
        on_disk = load_persistent_cognition(copied)
    except (OSError, ValueError, RuntimeError) as exc:
        raise C1TypedCheckpointHold("original/restored C1 cognition cannot be trusted") from exc
    if (
        historical != on_disk
        or historical != owner.retained
        or historical.identity.self_id != original_self_id
    ):
        raise C1TypedCheckpointHold("restored Owner differs from committed cognitive state")
    candidates = [m for m in historical.memories if m.memory_id == memory_id]
    if len(candidates) != 1 or not isinstance(candidates[0], Memory):
        raise C1TypedCheckpointHold("historical C1 not accepted by original Memory owner")
    stored = candidates[0]
    try:
        body = json.loads(stored.content)
    except (ValueError, TypeError) as exc:
        raise C1TypedCheckpointHold("C1 payload invalid") from exc
    if (
        not isinstance(body, dict)
        or body.get("kind") != "C1_BOUNDED_SKILLRUN_V1"
        or body.get("world_id") != plan.source_world_id
        or not isinstance(body.get("episode_key"), list)
        or len(body["episode_key"]) != 3
        or body["episode_key"][0] != original_self_id
        or not isinstance(body.get("action_ids"), list)
        or not body["action_ids"]
    ):
        raise C1TypedCheckpointHold("historical C1 shape/World/Self changed")
    # Never read old C1 as current motor authorization or fresh Target.
    return C1TypedContinuityWitness(
        memory_id=memory_id, self_id=original_self_id,
        source_world_id=plan.source_world_id,
        generation_id=plan.generation_id,
        source_committed_sha256=plan.source_committed_sha256,
        source_cognition_sha256=_safe_sha(archived),
        original_native_session_id=old_native,
        new_native_session_id=new_session,
        new_world_epoch=eligibility.world_epoch,
        new_native_seq=new_probe.seq,
    )
