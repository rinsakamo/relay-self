"""C Lane DEV: opt-in original Stage27h REAL runner post-L0 read-only L1 audit.

Executed ONLY after original Stage27h L0 stops, while the same original A
native raw stdout recorder, resident inference owner, Paper and peer B live.
It does NOT invoke the distinct Self C1 acceptance API. No Skill/Intent/Goal
completion, Memory write, physical Action or Stage28 checkpoint here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.p0d_stage27_real_place_move_dev import (
    _native_post_model_probe_readback,
)
from relay_self.c_lane_stage27hi_multi_action_review_dev import (
    finish_stage27hi_multi_review,
    prepare_stage27hi_multi_review,
    submit_stage27hi_multi_review,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.p0d_stage27h_bounded_l0_move_dev import (
    Stage27hBoundedMoveLoop,
    Stage27hLoopStep,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.skill import SkillState


class CStage27RealReadOnlyHold(RuntimeError):
    """Original live L0/L1/native evidence incomplete. No retry or C1 write."""


def _freeze(evidence: Path, filename: str, payload: dict) -> dict[str, object]:
    """O_EXCL+fsync both original bytes and directory; never replace evidence."""
    if (
        not isinstance(evidence, Path) or evidence.is_symlink()
        or not evidence.is_dir() or type(payload) is not dict
        or filename not in (
            "c-stage27h-before-post-l0-l1.json",
            "c-stage27h-post-l0-l1-witness.json",
        )
    ):
        raise CStage27RealReadOnlyHold("original C Stage27h evidence scope invalid")
    path = evidence / filename
    try:
        raw = (json.dumps(
            payload, sort_keys=True, indent=2, allow_nan=False,
        ) + "\n").encode("utf-8")
        with path.open("xb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        fd = os.open(evidence, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError, TypeError) as exc:
        raise CStage27RealReadOnlyHold("C Stage27h evidence original freeze failed") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if path.is_symlink() or path.read_bytes() != raw:
        raise CStage27RealReadOnlyHold("C Stage27h evidence original readback changed")
    return {"path": str(path), "sha256": digest, "readback": True}


async def capture_stage27h_real_post_l0_readonly_review(
    *,
    loop: Stage27hBoundedMoveLoop,
    step: Stage27hLoopStep,
    first_action_probe: MineflayerObservation,
    last_settled_probe: MineflayerObservation,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    bridge: OwnedResidentPhysicalBridge,
    evidence: Path,
    world_uuid: str,
    original_native_stdout: Path,
    fresh_probe: Callable[[], Awaitable[MineflayerObservation]],
) -> dict[str, object]:
    """One live bounded review; original owner remains STARTED afterward.

    This will NOT be called in Stage27i's strict zero-extra-model-POST mode.
    A pre-review source is fsynced BEFORE any extra L1 HTTP request and is
    preserved even when the post-Action model/native/probe step fails.
    """
    if (
        not isinstance(loop, Stage27hBoundedMoveLoop)
        or not isinstance(step, Stage27hLoopStep)
        or not isinstance(first_action_probe, MineflayerObservation)
        or not isinstance(last_settled_probe, MineflayerObservation)
        or type(world_uuid) is not str or not world_uuid
        or not isinstance(original_native_stdout, Path)
        or original_native_stdout.is_symlink()
        or not original_native_stdout.is_file()
        or not callable(fresh_probe)
        or not isinstance(bridge, OwnedResidentPhysicalBridge)
        or loop.owner.self_id != bridge.lifecycle.self_roster[0]
        or len(bridge.lifecycle.self_roster) != 2
        or bridge.owners.get(loop.owner.self_id) is not loop.owner
        or bridge.lifecycle.world.world_id != world_uuid
        or not 1 <= loop.action_count <= 4
        or loop.owner.skills[loop.handoff.skill_execution_id].state
        is not SkillState.STARTED
        or bridge.sessions[loop.owner.self_id].process_returncode is not None
    ):
        raise CStage27RealReadOnlyHold(
            "original Stage27h Action/Owner/native review unavailable"
        )

    owner = loop.owner
    journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    journal.require_clear()
    original_memory = copy.deepcopy(owner.retained)
    original_intent = copy.deepcopy(tuple(owner.intent.events))
    original_skill = copy.deepcopy(owner.skills[loop.handoff.skill_execution_id])
    original_actions = copy.deepcopy(tuple(journal.records))
    first_frame = prepare_stage27hi_multi_review(
        loop, step, physical=physical, lane=lane, bridge=bridge,
        first_action_probe=first_action_probe,
        last_settled_probe=last_settled_probe, world_id=world_uuid,
    )
    frozen_before = _freeze(evidence, "c-stage27h-before-post-l0-l1.json", {
        "classification": "C_STAGE27H_PRE_L1_ORIGINAL_L0_SNAPSHOT_DEV",
        "world_uuid": world_uuid,
        "branch_id": bridge.lifecycle.world.branch_id,
        "paper_session_id": bridge.paper.owned_session_id,
        "world_epoch": loop.world_epoch,
        "self_id": owner.self_id,
        "native_session_id": owner.native_session_id,
        "original_skill_state": original_skill.state.value,
        "original_intent_id": loop.handoff.intent_id,
        "original_skill_execution_id": loop.handoff.skill_execution_id,
        "canonical_wal_sha256": journal.digest,
        "canonical_action_ids": list(first_frame.action_ids),
        "original_l0_terminal": asdict(step),
        "target_gap_m": step.target_gap_m,
        "action_count": loop.action_count,
        "budget": asdict(loop.invocation.budget),
        "observations_used": loop.observation_count,
        "distance_used_m": loop.cumulative_distance_m,
        "settling_observations_reserved": loop._settlement_reserved,
        "evaluation_scope": "settled terminal WAL actions only; unexecuted work UNKNOWN",
        "evaluation_recommendation_only": True,
        "original_post_action_native_seq": last_settled_probe.seq,
        "l1_request_id": first_frame.request.request_id,
        "c1_memory_retained": False,
        "model_request_issued": False,
        "goal_succeeded": False,
        "physical_action_authorized": False,
    })

    # This is the first extra model request AFTER the original L0 loop.
    # The original source transcript is still running on the same native A.
    ticket = submit_stage27hi_multi_review(
        first_frame, loop, physical=physical, lane=lane, bridge=bridge,
        first_action_probe=first_action_probe,
        last_settled_probe=last_settled_probe,
    )
    witness, fresh = await finish_stage27hi_multi_review(
        first_frame, loop, ticket=ticket, physical=physical,
        lane=lane, bridge=bridge,
        first_action_probe=first_action_probe,
        last_settled_probe=last_settled_probe,
        fresh_probe=fresh_probe,
    )
    original_stdout = _native_post_model_probe_readback(
        original_native_stdout, session_id=owner.native_session_id,
        probe_id=fresh.request_id, probe_seq=fresh.seq,
        prior_settled_seq=last_settled_probe.seq,
    )
    # Only update CURRENT source of the existing original Self; source
    # adoption is not success or physical authority.
    if fresh.snapshot.time is None:
        raise CStage27RealReadOnlyHold("post-model original native tick unavailable")
    tick = (
        fresh.snapshot.time.day * 24000
        + fresh.snapshot.time.time_of_day
    )
    owner.observe_world_tick(session_id=owner.native_session_id, world_tick=tick)
    owner.accept_rejoined_worldbody(fresh, request_id=fresh.request_id)
    after_journal = PhysicalActionJournal.restore(
        owner.files.physical_wal_file, self_id=owner.self_id,
    )
    if (
        owner.retained != original_memory
        or tuple(owner.intent.events) != original_intent
        or owner.skills[loop.handoff.skill_execution_id] != original_skill
        or after_journal.digest != journal.digest
        or tuple(after_journal.records) != original_actions
        or owner.supervisor.open_actions
    ):
        raise CStage27RealReadOnlyHold(
            "post-L0 L1 read-only review changed original Skill/Intent/Memory/WAL"
        )
    if owner.files.cognition_file.exists() and (
        load_persistent_cognition(owner.files.cognition_file) != owner.retained
    ):
        raise CStage27RealReadOnlyHold(
            "original CURRENT cognition differs from canonical on-disk Memory"
        )

    summary = {
        "classification": "REAL_STAGE27H_C_LANE_L1_REVIEW_READONLY_DEV",
        "original_l0_source": frozen_before,
        "world_uuid": world_uuid,
        "original_native_session": owner.native_session_id,
        "original_paper_session": bridge.paper.owned_session_id,
        "original_skill_state": original_skill.state.value,
        "original_action_ids": list(witness.frame.action_ids),
        "original_wal_sha256": journal.digest,
        "original_model_choice_number": witness.choice_number,
        "review_completion_selected": witness.review_completion_selected,
        "original_model_http_request_sha256":
            witness.original_model_http_request_sha256,
        "original_model_http_response_sha256":
            witness.original_model_http_response_sha256,
        "post_model_native_seq": witness.post_model_probe_seq,
        "post_model_native_request_id": witness.post_model_probe_request_id,
        "native_stdout_readback": original_stdout,
        "separate_self_approval_supplied": False,
        "original_skill_terminalized": False,
        "c1_memory_written": False,
        "goal_succeeded": False,
        "action_issue_authorized": False,
        "actual_paper_vs_model_wallclock_causality_attested": False,
        "qual_and_science_attested": False,
    }
    frozen_after = _freeze(
        evidence, "c-stage27h-post-l0-l1-witness.json", summary,
    )
    return {**summary, "frozen_review": frozen_after}
