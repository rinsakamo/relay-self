"""C Lane: read-only Stage27 real-run -> *later* Stage28 typed A/B cut preflight.

No World/process/model launch, no Memory/Skill/Action adoption, no replay and
no claim of independent native/Paper causal attestation. This can only check
whether operator-supplied immutable sources are mutually consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from relay_self.coordinated_checkpoint_dev import verify_generation
from relay_self.intent import IntentEventKind
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalJournalError, _read
from relay_self.self_owner_checkpoint_dev import verify_typed_generation


class C1RealSourcePreflightHold(RuntimeError):
    """The named original source cannot establish even a shared C1 lineage."""


@dataclass(frozen=True, slots=True)
class Stage27Stage28SourcePreflight:
    """DEV-only source consistency, NOT physical causality or learning benefit."""

    classification: str
    source_world_uuid: str
    source_branch_id: str
    stage27_report_sha256: str
    preaction_generation: str
    postaction_generation: str
    postaction_committed_sha256: str
    c1_memory_id: str
    stage27_skill_execution_id: str
    action_ids: tuple[str, ...]
    original_wal_sha256: str
    stage27_hook_sha256: str
    archived_c1_retained: bool = True
    exact_wal_and_skill_lineage: bool = True
    physical_causality_attested: bool = False
    c2_understanding_attested: bool = False
    new_epoch_l1_attested: bool = False
    qual_authorized: bool = False
    science_attested: bool = False


def _file(path: Path) -> bytes:
    if not isinstance(path, Path) or path.is_symlink() or not path.is_file():
        raise C1RealSourcePreflightHold("source is missing, linked or nonregular")
    return path.read_bytes()


def _sha(path: Path) -> str:
    return hashlib.sha256(_file(path)).hexdigest()


def _json_object(path: Path) -> dict:
    try:
        data = json.loads(_file(path))
    except (OSError, ValueError, TypeError) as exc:
        raise C1RealSourcePreflightHold("original JSON cannot be decoded") from exc
    if type(data) is not dict:
        raise C1RealSourcePreflightHold("original JSON is not an object")
    return data


def inspect_stage27_to_stage28_original_sources(
    *, stage27_report: Path, stage27_wal: Path,
    preaction_generation: Path, postaction_generation: Path,
    c1_memory_id: str, self_id: str = "A",
) -> Stage27Stage28SourcePreflight:
    """Inspect existing original bytes; never reconstruct, repair or authorize.

    The Stage27 report's pre-action COMMITTED generation is NOT the new cut.
    A *separately captured* post-action typed World+A/B generation must
    contain a terminal owner-reviewed Skill and retained C1 from that WAL.
    Independent raw native/Paper/auditor evidence remains a separate gate.
    """
    if (
        self_id != "A" or type(c1_memory_id) is not str
        or not c1_memory_id.startswith("c1-skillrun:")
        or any(not isinstance(p, Path) for p in (
            stage27_report, stage27_wal, preaction_generation,
            postaction_generation,
        ))
    ):
        raise C1RealSourcePreflightHold("original Self A and exact C1 ID required")
    original = _json_object(stage27_report)
    hook = original.get("stage27")
    snapshot = original.get("stage27h_hook_snapshot")
    if (
        type(hook) is not dict or type(snapshot) is not dict
        or original.get("classification") != hook.get("classification")
        or not str(hook.get("classification", "")).startswith(
            ("REAL_STAGE27H_L0_", "REAL_STAGE27I_L0_")
        )
        or hook.get("physical_effect_observed") is not True
        or original.get("real_native_physical_action_issued") is not True
        or hook.get("stage27h_goal_success") is not False
        or hook.get("stage27h_skill_success") is not False
        or hook.get("stage27h_self_a_skill_state") != "started"
        or hook.get("self_a_selected_number") != "1"
        or original.get("world_uuid") != hook.get("original_world_uuid")
        or original.get("physical_action_issue_authorized") is not True
        or snapshot.get("original_hook_contract_valid") is not True
        or snapshot.get("original_hook_frozen_before_parent_aggregation") is not True
    ):
        raise C1RealSourcePreflightHold("original Stage27h/i terminal report unqualified")
    hook_path = snapshot.get("original_hook_return_path")
    if type(hook_path) is not str or type(snapshot.get("original_hook_return_sha256")) is not str:
        raise C1RealSourcePreflightHold("original hook freeze path/digest missing")
    saved_hook = Path(hook_path)
    frozen_sha = _sha(saved_hook)
    if (
        frozen_sha != snapshot["original_hook_return_sha256"]
        or _json_object(saved_hook) != hook
    ):
        raise C1RealSourcePreflightHold("Stage27 hook frozen evidence changed")
    if (
        type(original.get("committed_generation")) is not str
        or Path(original["committed_generation"]).resolve()
        != preaction_generation.resolve()
        or preaction_generation.resolve() == postaction_generation.resolve()
    ):
        raise C1RealSourcePreflightHold("pre-action generation reused as post-action")
    try:
        before = verify_generation(preaction_generation)
        after = verify_generation(postaction_generation)
        cuts = verify_typed_generation(postaction_generation)
    except (OSError, ValueError, RuntimeError) as exc:
        raise C1RealSourcePreflightHold("original World+A/B COMMITTED cut not qualified") from exc
    world = original.get("world_uuid")
    if (
        type(world) is not str or not world
        or before["world_id"] != world or after["world_id"] != world
        or before["branch_id"] != after["branch_id"]
        or before["roster"] != ["A", "B"]
        or after["roster"] != ["A", "B"]
        or {c.self_id for c in cuts} != {"A", "B"}
        or _sha(preaction_generation / "COMMITTED.json")
        == _sha(postaction_generation / "COMMITTED.json")
    ):
        raise C1RealSourcePreflightHold("post-action cut is not same World/branch A+B")
    skill_id = hook.get("stage27h_original_skill")
    intent_id = hook.get("stage27h_original_intent")
    witnesses = hook.get("stage27h_original_action_witnesses")
    action_count = hook.get("stage27h_l0_action_count")
    if (
        type(skill_id) is not str or not skill_id
        or type(intent_id) is not str or not intent_id
        or type(action_count) is not int or not 1 <= action_count <= 4
        or type(witnesses) is not list or len(witnesses) != action_count
        or any(type(w) is not dict or type(w.get("action")) is not str
               for w in witnesses)
        or hook.get("stage27_native_action_count") != action_count
    ):
        raise C1RealSourcePreflightHold("Stage27 physical child roster absent")
    ids = tuple(w["action"] for w in witnesses)
    if len(set(ids)) != len(ids):
        raise C1RealSourcePreflightHold("duplicate original Action witness")
    owner = next(x for x in cuts if x.self_id == self_id)
    skills = [s for s in owner.skill_executions if s.execution_id == skill_id]
    if (
        len(skills) != 1
        or not skills[0].is_current_snapshot
        or not skills[0].is_terminal
        or skills[0].intent_id != intent_id
        or not any(e.intent_id == intent_id and e.kind is IntentEventKind.COMMITTED
                   for e in owner.intent_events)
    ):
        raise C1RealSourcePreflightHold(
            "Stage27 Skill still STARTED: original Owner must review before C1"
        )
    try:
        source_body, source_sha = _read(stage27_wal)
        archive_path = postaction_generation / "selves" / self_id / "physical-wal.json"
        archive_body, archive_sha = _read(archive_path)
    except (OSError, ValueError, PhysicalJournalError) as exc:
        raise C1RealSourcePreflightHold("original Stage27 WAL source unverified") from exc
    rows = source_body["actions"]
    selected = [x for x in rows if x["skill_execution_id"] == skill_id]
    if (
        source_body != archive_body or source_sha != archive_sha
        or source_body["self_id"] != self_id or source_body["schema"] != 2
        or not rows or rows[-1]["status"] == "PREPARED_UNRESOLVED"
        or tuple(x["action_id"] for x in selected) != ids
        or any(x["session_id"] != owner.former_native_session_id
               or x["intent_id"] != intent_id
               or x["capability"] != "MOVE_PLACE"
               or x["status"] not in {
                   "NATIVE_PLACE_MOVE_SETTLED", "NATIVE_PLACE_MOVE_NO_PROGRESS",
                   "NATIVE_PLACE_MOVE_OVERSHOOT",
               }
               for x in selected)
    ):
        raise C1RealSourcePreflightHold("original source WAL differs from retained typed cut")
    old = load_persistent_cognition(
        postaction_generation / "selves" / self_id / "cognition.json"
    )
    matching = [m for m in old.memories if m.memory_id == c1_memory_id]
    if len(matching) != 1 or old.identity.self_id != self_id:
        raise C1RealSourcePreflightHold("C1 not adopted in original Self checkpoint")
    try:
        memory = json.loads(matching[0].content)
        recorded_refs = memory["source_refs"]
        reported_actions = memory["action_ids"]
        episode = memory["episode_key"]
    except (ValueError, KeyError, TypeError) as exc:
        raise C1RealSourcePreflightHold("C1 retained payload malformed") from exc
    required = [
        ["canonical-physical-wal", f"{source_sha}:{action}"] for action in ids
    ]
    actual = [
        r for r in recorded_refs if type(r) is list and len(r) == 2
        and r[0] == "canonical-physical-wal"
    ] if type(recorded_refs) is list else []
    if (
        memory.get("kind") != "C1_BOUNDED_SKILLRUN_V1"
        or memory.get("world_id") != world
        or episode != [self_id, owner.former_native_session_id, skill_id]
        or reported_actions != list(ids)
        or memory.get("intent_id") != intent_id
        or memory.get("skill_id") != skills[0].skill_id
        or any(x["target_ref"] != memory.get("target_ref")
               or x["preset_ref"] != memory.get("preset_ref")
               for x in selected)
        or sorted(actual) != sorted(required)
    ):
        raise C1RealSourcePreflightHold("C1 source lineage does not match original WAL")
    first_sha = _sha(stage27_report)
    if (
        first_sha != _sha(stage27_report)
        or frozen_sha != _sha(saved_hook)
        or source_sha != _read(stage27_wal)[1]
        or archive_sha != _read(archive_path)[1]
    ):
        raise C1RealSourcePreflightHold("original evidence changed during readback")
    return Stage27Stage28SourcePreflight(
        classification="DEV_SOURCE_LINEAGE_COMPATIBLE_NOT_PHYSICAL_CAUSALITY",
        source_world_uuid=world,
        source_branch_id=after["branch_id"],
        stage27_report_sha256=first_sha,
        preaction_generation=before["generation_id"],
        postaction_generation=after["generation_id"],
        postaction_committed_sha256=_sha(postaction_generation / "COMMITTED.json"),
        c1_memory_id=c1_memory_id,
        stage27_skill_execution_id=skill_id,
        action_ids=ids,
        original_wal_sha256=source_sha,
        stage27_hook_sha256=frozen_sha,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage27-report", type=Path, required=True)
    parser.add_argument("--stage27-wal", type=Path, required=True)
    parser.add_argument("--preaction-generation", type=Path, required=True)
    parser.add_argument("--postaction-generation", type=Path, required=True)
    parser.add_argument("--c1-memory-id", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = inspect_stage27_to_stage28_original_sources(
            stage27_report=args.stage27_report, stage27_wal=args.stage27_wal,
            preaction_generation=args.preaction_generation,
            postaction_generation=args.postaction_generation,
            c1_memory_id=args.c1_memory_id,
        )
    except (C1RealSourcePreflightHold, OSError, ValueError, KeyError) as exc:
        print(json.dumps({
            "classification": "PRE_WORLD_HOLD",
            "reason": type(exc).__name__ + ": " + str(exc),
            "real_world_trials": 0,
        }, sort_keys=True))
        return 2
    print(json.dumps(asdict(receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
