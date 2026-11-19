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
from relay_self.intent import IntentEventKind
from relay_self.persistent_cognition import Memory, load_persistent_cognition
from relay_self.physical_action_journal import PhysicalJournalError, _read
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28FreshL1Eligibility,
)
from relay_self.stage28c2b_execution_copy_dev import ExecutionCopy


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


@dataclass(frozen=True, slots=True)
class C1Stage27SourceLineageWitness:
    """Canonical original source consistency; NOT native/Paper causal proof."""

    continuity: C1TypedContinuityWitness
    physical_wal_sha256: str
    skill_execution_id: str
    action_ids: tuple[str, ...]
    historical_source_format_verified: bool = True
    real_physical_effect_attested: bool = False
    old_action_replayed: bool = False
    physical_issue_authorized: bool = False


def verify_stage27_wal_c1_across_stage28_typed_epoch(
    *,
    source_generation: Path,
    copy: ExecutionCopy,
    eligibility: Stage28FreshL1Eligibility,
    boot: Stage28ForkPaperEpoch,
    original_self_id: str,
    memory_id: str,
    new_probe: MineflayerObservation,
) -> C1Stage27SourceLineageWitness:
    """Check original Stage27 v2 WAL, accepted C1 and Stage28 typed SelfCut.

    This is explicitly a stronger *format/lineage consistency* contract than
    a standalone C1 Memory readback. It does NOT independently authenticate
    Mineflayer transport, the issuer's real physical effect or Paper causality.
    """
    continued = verify_c1_across_stage28_typed_epoch(
        source_generation=source_generation, copy=copy, eligibility=eligibility,
        boot=boot, original_self_id=original_self_id,
        memory_id=memory_id, new_probe=new_probe,
    )
    cuts = verify_typed_generation(source_generation)
    cut = next((x for x in cuts if x.self_id == original_self_id), None)
    if cut is None:
        raise C1TypedCheckpointHold("original bounded Skill owner cut not found")
    archived_path = source_generation / "selves" / original_self_id
    copied_path = copy.directory / "selves" / original_self_id
    # Use the original Stage27 canonical checksum+grammar reader directly.
    # Journal.restore() creates a sibling .lock file even for reads, which
    # would modify the *immutable COMMITTED archive*. Both files are already
    # pinned by Stage28 verify_typed_generation / verified execution copy.
    try:
        original_body, original_digest = _read(
            archived_path / "physical-wal.json",
        )
        restored_body, restored_digest = _read(
            copied_path / "physical-wal.json",
        )
    except PhysicalJournalError as exc:
        raise C1TypedCheckpointHold("original Stage27 physical WAL not canonical") from exc
    rows = original_body["actions"]
    if (
        original_digest != restored_digest
        or original_body != restored_body
        or original_body["self_id"] != original_self_id
        or original_body["schema"] != 2
        or not rows
        or rows[-1]["status"] == "PREPARED_UNRESOLVED"
    ):
        raise C1TypedCheckpointHold("source/restored Stage27 schema-v2 WAL mismatch")

    historic = load_persistent_cognition(archived_path / "cognition.json")
    matches = [x for x in historic.memories if x.memory_id == memory_id]
    if len(matches) != 1:
        raise C1TypedCheckpointHold("original C1 Memory not in committed owner")
    try:
        content = json.loads(matches[0].content)
        episode = content["episode_key"]
        chosen_action_ids = content["action_ids"]
        recorded_refs = content["source_refs"]
    except (ValueError, TypeError, KeyError) as exc:
        raise C1TypedCheckpointHold("malformed original C1 physical lineage") from exc
    if (
        type(episode) is not list or len(episode) != 3
        or episode[:2] != [original_self_id, cut.former_native_session_id]
        or type(chosen_action_ids) is not list or not chosen_action_ids
        or any(type(v) is not str or not v for v in chosen_action_ids)
        or len(set(chosen_action_ids)) != len(chosen_action_ids)
        or type(recorded_refs) is not list
    ):
        raise C1TypedCheckpointHold("C1 episode/source scope or Action set invalid")
    key = episode[2]
    matching_skills = [
        s for s in cut.skill_executions if s.execution_id == key
    ]
    if (
        len(matching_skills) != 1
        or not matching_skills[0].is_current_snapshot
        or not matching_skills[0].is_terminal
        or matching_skills[0].skill_id != content.get("skill_id")
        or matching_skills[0].intent_id != content.get("intent_id")
        or not any(
            e.intent_id == matching_skills[0].intent_id
            and e.kind is IntentEventKind.COMMITTED
            for e in cut.intent_events
        )
    ):
        raise C1TypedCheckpointHold("original C1 child Skill not terminal/committed in cut")
    selected_rows = [
        row for row in rows
        if row["skill_execution_id"] == key
    ]
    if (
        len(selected_rows) != len(chosen_action_ids)
        or [r["action_id"] for r in selected_rows] != chosen_action_ids
        or any(
            row["capability"] != "MOVE_PLACE"
            or row["session_id"] != cut.former_native_session_id
            or row["intent_id"] != matching_skills[0].intent_id
            or row["target_ref"] != content.get("target_ref")
            or row["preset_ref"] != content.get("preset_ref")
            or row["status"] not in {
                "NATIVE_PLACE_MOVE_SETTLED",
                "NATIVE_PLACE_MOVE_NO_PROGRESS",
                "NATIVE_PLACE_MOVE_OVERSHOOT",
            }
            for row in selected_rows
        )
    ):
        raise C1TypedCheckpointHold("C1 action IDs or original WAL/Target/Preset differ")
    expected_source = [
        ["canonical-physical-wal", f"{original_digest}:{aid}"]
        for aid in chosen_action_ids
    ]
    selected_source = [
        ref for ref in recorded_refs
        if type(ref) is list and len(ref) == 2
        and ref[0] == "canonical-physical-wal"
    ]
    if (
        len(selected_source) != len(expected_source)
        or sorted(selected_source) != sorted(expected_source)
        or content.get("world_id") != continued.source_world_id
    ):
        raise C1TypedCheckpointHold("C1 claims unverified WAL SHA/Action source")
    return C1Stage27SourceLineageWitness(
        continuity=continued,
        physical_wal_sha256=original_digest,
        skill_execution_id=key,
        action_ids=tuple(chosen_action_ids),
    )
