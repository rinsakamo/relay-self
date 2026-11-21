"""#860 Stage25: real Paper / two original Self / accepted Preset cut DEV.

ONE new localhost-only Paper 1.21.8 World, original Mineflayer processes,
two original cognitive owners, original PhysicalIssueAdmission, canonical WAL.
The only model 'L1' used in this stage is a SCRIPTED number-only decision:
no Gemma/GPU is called; no MOVE/EAT/ATTACK effect is ever issued.

The real saved World+2 Self generation is verified and fork-staged offline.
The running Paper restarts from its SAME source World, not the forked copy.
Both original Self are populated with the *verified restored cognition* before
new native sessions log in. Do not claim live fork rollback or AI autonomy.

This runner is deliberately separate from the successful Stage22/23 runners.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.p0d_real_paper_smoke_dev import (
    _bootstrap_paper,
    _free_local_port,
    _world_uuid,
    _write_bytes_new,
    file_sha256,
)
from experiments.p0d_real_resident_presence_dev import _bounded_b_probe
from experiments.p0d_real_two_native_smoke_dev import (
    preflight_two_native,
    two_native_server_properties,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
    staged_recover_cognition_cohort,
)
from relay_self.cognitive_minimal_dev import initial_patterns_with_move
from relay_self.coordinated_checkpoint_dev import (
    SelfSnapshotSource,
    restore_generation,
)
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.p0d_real_preset_reselect_dev import reselect_restored_move_preset_live
from relay_self.p0d_stage26_gemma_l1_dev import (
    finish_restored_preset_l1,
    prepare_restored_preset_l1,
    submit_restored_preset_l1,
)
from relay_self.p0d_stage27i_precision_gait_dev import STAGE27I_PRESET_ID
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    load_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)
from relay_self.self_owner_checkpoint_dev import (
    SelfOwnerCut,
    capture_typed_generation,
    save_self_owner_cut,
    verify_typed_generation,
)
from relay_self.skill_invocation import (
    SkillBudget,
    SkillConstraints,
    SkillCostEstimate,
    SkillParameterPreset,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldInstallationEvidence,
    WorldLifetime,
    WorldResidentLifecycle,
)


class RealPresetCheckpointRefusal(RuntimeError):
    """Source-qualified World, Self or Preset knowledge is not admissible."""


def _preserve_and_validate_stage27h_hook_return(
    result: object, *, evidence: Path,
) -> dict[str, object]:
    """Durably freeze original motor-hook output BEFORE parent aggregation.

    A returned-but-incompatible hook may follow irreversible physical
    effects. Capture its raw mapping before checking the contract, then HOLD
    on any inconsistency. This is evidence durability, NOT retry permission.
    """
    if (
        type(result) is not dict
        or not isinstance(evidence, Path)
        or evidence.is_symlink() or not evidence.is_dir()
    ):
        raise RealPresetCheckpointRefusal(
            "Stage27h original motor-hook return cannot be preserved"
        )
    try:
        payload = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False)
                   + "\n").encode("utf-8")
    except (ValueError, TypeError, OverflowError) as exc:
        raise RealPresetCheckpointRefusal(
            "Stage27h original motor-hook result is not serializable"
        ) from exc
    filename = evidence / "stage27h-original-motor-hook-return.json"
    _write_bytes_new(filename, payload)
    directory_fd = os.open(evidence, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    digest = hashlib.sha256(payload).hexdigest()
    if filename.read_bytes() != payload or file_sha256(filename) != digest:
        raise RealPresetCheckpointRefusal(
            "Stage27h motor-hook frozen original readback mismatch"
        )

    # No broad bool(...) conversion: a missing/non-boolean key would have
    # caused the former KeyError after the one real physical Action.
    if type(result.get("physical_effect_observed")) is not bool:
        raise RealPresetCheckpointRefusal(
            "Stage27h motor-hook missing typed physical_effect_observed"
        )
    classification = result.get("classification")
    nonselected = classification == "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV"
    if nonselected:
        if (
            result["physical_effect_observed"]
            or result.get("stage27_native_action_count") != 0
            or result.get("original_peer_b_before")
            != result.get("original_peer_b_after")
        ):
            raise RealPresetCheckpointRefusal(
                "Stage27h nonselected motor hook reported physical effect"
            )
    else:
        feedback = result.get("stage27h_l0_feedback")
        actions = result.get("stage27h_original_action_witnesses")
        before = result.get("stage27h_peer_b_before")
        after = result.get("stage27h_peer_b_after")
        action_count = result.get("stage27h_l0_action_count")
        stage = "27I" if result.get("stage27i_precision_enabled") is True else "27H"
        expected_status = {
            "L0_TARGET_REACHED_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
            "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_BUDGET_EXHAUSTED_DEV",
            "L0_NO_PROGRESS_YIELD_EVALUATION":
                f"REAL_STAGE{stage}_L0_NO_PROGRESS_DEV",
        }
        if (
            type(action_count) is not int or not 0 <= action_count <= 4
            or result["physical_effect_observed"] != (action_count > 0)
            or result.get("stage27_native_action_count") != action_count
            or type(feedback) is not dict
            or feedback.get("action_count") != action_count
            or type(actions) is not list or len(actions) != action_count
            or feedback.get("status") is None
            or classification != expected_status.get(
                feedback["status"], f"REAL_STAGE{stage}_L0_UNREACHED_DEV",
            )
            or type(before) is not dict or type(after) is not dict
            or before != after
            or result.get("original_peer_b_before") != before
            or result.get("original_peer_b_after") != after
            or result.get("stage27h_self_a_skill_state") != "started"
            or not result.get("stage27h_self_a_intent_current")
            or result.get("stage27h_goal_success") is not False
            or result.get("stage27h_skill_success") is not False
            or any(
                type(row) is not dict or not row.get("action")
                or row.get("goal_success") is not False
                or row.get("skill_success") is not False
                or row.get("l0_feedback", {}).get("action_count") != i + 1
                for i, row in enumerate(actions)
            )
            or len({row["action"] for row in actions}) != len(actions)
        ):
            raise RealPresetCheckpointRefusal(
                "Stage27h motor-hook original result violates parent contract"
            )
    if result.get("stage27i_precision_enabled") is True:
        # Refuse an otherwise equal-looking B snapshot that omits Memory.
        # Read back BOTH separately fsynced source snapshots, not merely the
        # in-memory hook-return JSON written above.
        b_before = result.get("stage27h_peer_b_before")
        b_after = result.get("stage27h_peer_b_after")
        if type(b_before) is not dict or type(b_after) is not dict:
            raise RealPresetCheckpointRefusal(
                "Stage27i original peer B evidence missing"
            )
        required = {
            "intent_event_count", "intent_events_sha256", "intent_current",
            "skill_execution_count", "skill_histories_sha256",
            "memory_count", "memory_records_sha256", "memory_record_digests",
            "physical_wal_sha256", "physical_wal_action_rows",
            "physical_wal_unresolved", "open_action_count",
        }
        for label, snapshot in (("before", b_before), ("after", b_after)):
            if set(snapshot) != required:
                raise RealPresetCheckpointRefusal(
                    "Stage27i peer B Intent/Skill/Memory/WAL fields missing"
                )
            digest_fields = (
                "intent_events_sha256", "skill_histories_sha256",
                "memory_records_sha256", "physical_wal_sha256",
            )
            if (
                snapshot["intent_current"] is not None
                or snapshot["physical_wal_unresolved"] is not False
                or any(type(snapshot[key]) is not int or snapshot[key] < 0
                    for key in (
                        "intent_event_count", "skill_execution_count",
                        "memory_count", "physical_wal_action_rows",
                        "open_action_count",
                    ))
                or any(
                    type(snapshot[key]) is not str
                    or len(snapshot[key]) != 64
                    or any(c not in "0123456789abcdef" for c in snapshot[key])
                    for key in digest_fields
                )
                or type(snapshot["memory_record_digests"]) is not list
                or len(snapshot["memory_record_digests"]) != snapshot["memory_count"]
                or any(
                    type(item) is not dict
                    or set(item) != {"memory_id", "sha256"}
                    or type(item["memory_id"]) is not str or not item["memory_id"]
                    or type(item["sha256"]) is not str
                    or len(item["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in item["sha256"])
                    for item in snapshot["memory_record_digests"]
                )
            ):
                raise RealPresetCheckpointRefusal(
                    "Stage27i peer B typed Memory content witness invalid"
                )
            receipt = result.get(f"stage27i_peer_b_{label}_evidence")
            expected_path = evidence / f"stage27i-peer-b-{label}.json"
            if (
                type(receipt) is not dict
                or set(receipt) != {
                    "path", "sha256", "frozen_original",
                    "memory_content_compared_by_sha256",
                }
                or receipt["path"] != str(expected_path)
                or receipt["frozen_original"] is not True
                or receipt["memory_content_compared_by_sha256"] is not True
                or expected_path.is_symlink() or not expected_path.is_file()
                or file_sha256(expected_path) != receipt["sha256"]
                or json.loads(expected_path.read_bytes()) != snapshot
            ):
                raise RealPresetCheckpointRefusal(
                    "Stage27i original B Memory snapshot readback mismatch"
                )
        if b_before != b_after:
            raise RealPresetCheckpointRefusal(
                "Stage27i original peer B Memory/Intent/Skill/WAL changed"
            )
        # Mandatory independently frozen provider HTTP source census, not
        # merely the former literal "additional_model_requests": 0.
        http_before = result.get("stage27i_model_http_before")
        http_after = result.get("stage27i_model_http_after")
        if (
            type(http_before) is not dict or type(http_after) is not dict
            or http_before != http_after
            or result.get("stage27h_additional_model_requests") != 0
        ):
            raise RealPresetCheckpointRefusal(
                "Stage27i original model HTTP before/after census changed"
            )
        model_source = evidence / "original-model-http"
        if model_source.is_symlink() or not model_source.is_dir():
            raise RealPresetCheckpointRefusal("Stage27i model source missing")
        actual_names = sorted(p.name for p in model_source.iterdir())
        expected_fields = {
            "request_count", "response_count", "manifest_count",
            "unexpected_files", "missing_files", "source_receipts",
            "model_http_source", "file_names_sha256",
        }
        if (
            set(http_before) != expected_fields
            or any(type(http_before[k]) is not int or http_before[k] != 2
                   for k in ("request_count", "response_count", "manifest_count"))
            or http_before["unexpected_files"] != []
            or http_before["missing_files"] != []
            or http_before["model_http_source"] != str(model_source)
            or type(http_before["source_receipts"]) is not dict
            or set(http_before["source_receipts"]) != {"A", "B"}
            or http_before["file_names_sha256"] != hashlib.sha256(
                json.dumps(actual_names, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            or len(actual_names) != 6
            or any(p.is_symlink() or not p.is_file()
                   for p in model_source.iterdir())
        ):
            raise RealPresetCheckpointRefusal(
                "Stage27i model HTTP source census not exactly two calls"
            )
        expected_names: set[str] = set()
        for sid in ("A", "B"):
            receipt = http_before["source_receipts"][sid]
            if type(receipt) is not dict or set(receipt) != {
                "request_id", "request_sha256", "response_sha256",
                "response_bytes",
            }:
                raise RealPresetCheckpointRefusal(
                    "Stage27i original L1 source receipt incomplete"
                )
            request_id = receipt["request_id"]
            if type(request_id) is not str or not request_id:
                raise RealPresetCheckpointRefusal("Stage27i bad L1 request ID")
            key = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
            request_file = model_source / (key + ".request.json")
            response_file = model_source / (key + ".response.json")
            manifest_file = model_source / (key + ".source.sha256.json")
            expected_names.update((
                request_file.name, response_file.name, manifest_file.name,
            ))
            try:
                model_manifest = json.loads(manifest_file.read_bytes())
                request_hash = file_sha256(request_file)
                response_hash = file_sha256(response_file)
                response_size = response_file.stat().st_size
            except (OSError, ValueError, KeyError) as exc:
                raise RealPresetCheckpointRefusal(
                    "Stage27i original model HTTP files missing"
                ) from exc
            if (
                model_manifest.get("request_id") != request_id
                or model_manifest.get("request_sha256") != request_hash
                or model_manifest.get("response_sha256") != response_hash
                or model_manifest.get("response_bytes") != response_size
                or receipt["request_sha256"] != request_hash
                or receipt["response_sha256"] != response_hash
                or receipt["response_bytes"] != response_size
            ):
                raise RealPresetCheckpointRefusal(
                    "Stage27i original model HTTP SHA evidence inconsistent"
                )
        if sorted(expected_names) != actual_names:
            raise RealPresetCheckpointRefusal(
                "Stage27i extra or missing model HTTP request source"
            )
        for label, snapshot in (("before", http_before), ("after", http_after)):
            saved = result.get(f"stage27i_model_http_{label}_evidence")
            path = evidence / f"stage27i-model-http-{label}.json"
            if (
                type(saved) is not dict
                or set(saved) != {"path", "sha256", "frozen_original"}
                or saved["path"] != str(path)
                or saved["frozen_original"] is not True
                or path.is_symlink() or not path.is_file()
                or file_sha256(path) != saved["sha256"]
                or json.loads(path.read_bytes()) != snapshot
            ):
                raise RealPresetCheckpointRefusal(
                    "Stage27i L1 HTTP census frozen readback mismatch"
                )
    return {
        "original_hook_return_path": str(filename),
        "original_hook_return_sha256": digest,
        "original_hook_contract_valid": True,
        "original_hook_frozen_before_parent_aggregation": True,
    }


def _paper_join_witness(
    paper: OwnedPaperWorld, *, paper_session_id: str, world_uuid: str,
) -> dict[str, object]:
    """Read the current original Paper stdout, not a replayed arbitrary log."""
    source = paper.read_owned_log(paper_session_id)
    digest = hashlib.sha256(source).hexdigest()
    parsed = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session_id,
        expected_world_uuid=world_uuid,
        owned_paper_log=source,
        log_ref=f"owned-paper:{paper_session_id}:sha256:{digest}",
    )
    joins: dict[str, str] = {}
    for event in parsed.events:
        if event.event == "JOIN" and event.name in ("RelayA", "RelayB"):
            if event.name in joins:
                raise RealPresetCheckpointRefusal(
                    "duplicate Paper JOIN for original one-session actor"
                )
            joins[event.name] = event.actor_uuid
    if set(joins) != {"RelayA", "RelayB"} or len(set(joins.values())) != 2:
        raise RealPresetCheckpointRefusal(
            "both independent Paper player JOIN sources required"
        )
    return {
        "paper_session": paper_session_id,
        "boot_id": parsed.boot_id,
        "world_uuid": parsed.world_uuid,
        "owned_stdout_sha256": parsed.lines_sha256,
        "actor_uuids": joins,
        "read_only_source": True,
    }


def _readback_native_probe_source(
    native_raw: Path, *, first_request: str, second_request: str,
    native_session: str, first_seq: int, second_seq: int,
) -> str:
    """Compare exact frozen stdout with BOTH parsed source-qualified replies."""
    if (
        not first_request or not second_request
        or first_request == second_request
        or not native_session
        or type(first_seq) is not int or type(second_seq) is not int
        or not 0 <= first_seq < second_seq
        or native_raw.is_symlink() or not native_raw.is_file()
    ):
        raise RealPresetCheckpointRefusal("native source transcript inputs stale")
    try:
        raw = native_raw.read_bytes()
        observed_pairs: list[tuple[str, int, str]] = []
        for line in raw.splitlines():
            row = json.loads(line)
            if type(row) is not dict:
                raise RealPresetCheckpointRefusal("native JSONL non-object")
            if row.get("type") == "observation" and row.get("kind") == "probe":
                observed_pairs.append((
                    row.get("session_id"), row.get("seq"), row.get("request_id"),
                ))
    except (OSError, ValueError, UnicodeError) as exc:
        if isinstance(exc, RealPresetCheckpointRefusal):
            raise
        raise RealPresetCheckpointRefusal(
            "native original source transcript not readable JSONL"
        ) from exc
    expected = (
        (native_session, first_seq, first_request),
        (native_session, second_seq, second_request),
    )
    if any(observed_pairs.count(entry) != 1 for entry in expected):
        raise RealPresetCheckpointRefusal(
            "new native source probe missing/duplicated in exact stdout"
        )
    return file_sha256(native_raw)


def _stage_owner_cuts(
    *, owners: dict[str, CheckpointedCognitiveOwner],
    work: ResidentCognitiveWorkOwner,
    physical: PhysicalIssueAdmission,
    bridge: OwnedResidentPhysicalBridge,
    evidence: Path,
    world: WorldLifetime,
    generation_id: str,
) -> tuple[SelfSnapshotSource, ...]:
    """Capture original retired Self owners BEFORE Paper stop, no new issuer."""
    if (
        tuple(sorted(owners)) != ("A", "B")
        or bridge.sessions
        or not physical.all_residents_offline
        or not all(work.retired_clean(sid) for sid in ("A", "B"))
        or not bridge.world_only_quiescence().no_unresolved_physical_actions
    ):
        raise RealPresetCheckpointRefusal(
            "both original Self/Work/WAL must be retired before capture"
        )
    result = []
    for sid in ("A", "B"):
        owner = owners[sid]
        if (
            owner.supervisor.open_actions
            or owner.retained.pattern_registry != owner.pattern_registry
            or not owner.pattern_registry.accepted_presets
            or any(e.receipt.self_id != sid
                   for e in owner.pattern_registry.accepted_presets)
        ):
            raise RealPresetCheckpointRefusal(
                "Self learned Preset revision or original Action state missing"
            )
        PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=sid,
        ).require_clear()
        if load_persistent_cognition(owner.files.cognition_file) != owner.retained:
            raise RealPresetCheckpointRefusal(
                "retired original Self cognition file not persistent"
            )
        owner_dir = evidence / ("cut-" + sid)
        owner_dir.mkdir(mode=0o700)
        cut = SelfOwnerCut(
            generation_id=generation_id,
            self_id=sid,
            world_id=world.world_id,
            branch_id=world.branch_id,
            former_native_session_id=owner.native_session_id,
            last_observed_world_tick=owner.last_observed_tick,
            intent_events=owner.intent.events,
            skill_executions=tuple(owner.skills[k] for k in sorted(owner.skills)),
            pattern_registry=owner.pattern_registry,
            peer_deliveries=tuple(
                owner.peer_deliveries[k] for k in sorted(owner.peer_deliveries)
            ),
            pending_question_refs=tuple(sorted(owner.pending_questions)),
        )
        owner_file = owner_dir / "owner-state.json"
        save_self_owner_cut(owner_file, cut)
        result.append(SelfSnapshotSource(
            sid, owner.files.cognition_file,
            owner.files.physical_wal_file, owner_file,
        ))
    return tuple(result)


async def _real_preset_trial(
    *, paper: OwnedPaperWorld, bridge: OwnedResidentPhysicalBridge,
    physical: PhysicalIssueAdmission,
    work: ResidentCognitiveWorkOwner,
    lifecycle: WorldResidentLifecycle,
    owners: dict[str, CheckpointedCognitiveOwner],
    evidence: Path, world_uuid: str,
    inference_lane: ResidentLlamaInferenceLane | None = None,
    stage27_motor_hook: Callable[..., Awaitable[dict[str, object]]] | None = None,
    stage27h_multi_preset: bool = False,
    stage27i_precision_target: bool = False,
) -> dict[str, object]:
    """Original saved/rejoined Self cohort; Stage26 remains nonissuing by default."""
    original_world = lifecycle.world
    first_paper_session = paper.owned_session_id
    if first_paper_session != original_world.paper_session_id:
        raise RealPresetCheckpointRefusal("foreign original Paper owner")

    for sid in ("A", "B"):
        await bridge.login(sid)
    definition = next(
        d for d in initial_skill_definitions() if d.skill_id == "MOVE"
    )
    accepted_refs: dict[str, str] = {}
    for sid in ("A", "B"):
        # Explicitly operator-accepted DEV template, not generated by Gemma:
        # actual Self-owner acceptance/authorization is not established.
        preset = SkillParameterPreset(
            "exploration-move",
            STAGE27I_PRESET_ID if stage27i_precision_target
            else "OperatorNearProbe",
            1,
            definition.definition_ref,
            SkillConstraints(), (
                SkillBudget(4, 15000, 2.0, 256) if stage27h_multi_preset
                else SkillBudget(1, 1500, 2.0, 4)
            ),
            Provenance("operator-dev-proposed", f"stage25:{sid}"),
            expected_cost=(
                SkillCostEstimate(4, 8000, 1.0) if stage27h_multi_preset
                else SkillCostEstimate(1, 1200, 1.0)
            ),
        )
        owners[sid].accept_parameter_preset(
            preset, definition=definition,
            acceptance_event_id="stage25-operator-template-" + sid,
            acceptance_provenance=Provenance(
                "operator-dev-authorized", "test-preset-not-autonomous",
            ),
            available_skills=frozenset({("MOVE", 1)}),
        )
        accepted_refs[sid] = preset.preset_ref
    # An initial Paper presence sample is independent from native readback.
    await asyncio.sleep(2.2)
    paper_before = _paper_join_witness(
        paper, paper_session_id=first_paper_session,
        world_uuid=world_uuid,
    )
    original_native = {
        sid: bridge.sessions[sid].started.session_id for sid in ("A", "B")
    }
    original_pid = {
        sid: bridge.sessions[sid].owned_child_pid for sid in ("A", "B")
    }
    for sid in ("A", "B"):
        await bridge.logout(sid)
    quiescence = bridge.world_only_quiescence()
    lifecycle.require_world_only_quiescence(quiescence)
    specs = _stage_owner_cuts(
        owners=owners, work=work, physical=physical, bridge=bridge,
        evidence=evidence, world=original_world,
        generation_id="g-000000000001",
    )
    # Only Paper's owned process may be stopped. No global commands/restarts.
    lifecycle.begin_world_transition()
    stopped = paper.stop_and_save()
    if (
        stopped.old_server_session_id != first_paper_session
        or stopped.world_id != world_uuid
        or stopped.branch_id != original_world.branch_id
        or stopped.process_exit_code != 0
        or stopped.all_dimensions_saved is not True
    ):
        raise RealPresetCheckpointRefusal("owned Paper save/STOP source invalid")
    store = evidence / "coordinated-generations"
    store.mkdir(mode=0o700)
    checkpoint = capture_typed_generation(
        paper.world_dir, store,
        sequence=1, expected_self_ids=("A", "B"), selves=specs,
        world_id=world_uuid, branch_id=original_world.branch_id,
        logical_tick=stopped.logical_tick,
        tick_source_ref=stopped.tick_source_ref,
        stopped_server_ref=stopped.stopped_server_ref,
        quiesced_selves_ref=quiescence.source_ref,
        paper_layout=True,
    )
    committed_cuts = verify_typed_generation(checkpoint)
    if (
        len(committed_cuts) != 2
        or any(
            c.pattern_registry.accepted_presets[0].preset.preset_ref
            != accepted_refs[c.self_id] for c in committed_cuts
        )
    ):
        raise RealPresetCheckpointRefusal(
            "coordinated generation missing actual Self accepted Presets"
        )
    fork = evidence / "verified-fork-readonly"
    restore_receipt = restore_generation(
        checkpoint, fork, restore_id="stage25-preset-cut",
    )
    staged = staged_recover_cognition_cohort(checkpoint, fork)
    if (
        restore_receipt.get("physical_action_issue_authorized") is not False
        or len(staged) != 2
        or any(s.issue_authorized or s.native_session_bound
               for s in staged)
    ):
        raise RealPresetCheckpointRefusal(
            "fork restore illegally revived physical/runtime authority"
        )
    staged_by_id = {s.self_id: s for s in staged}
    if tuple(sorted(staged_by_id)) != ("A", "B"):
        raise RealPresetCheckpointRefusal("restored original Self roster changed")

    # Adopt only verified retained knowledge into the EXISTING offlined
    # original Self owner objects. Do not resurrect Intent/Skill/Action cursors.
    for sid in ("A", "B"):
        source = staged_by_id[sid]
        original = owners[sid]
        if (
            original.intent.current_intent is not None
            or original.skills or original.peer_deliveries
            or source.semantic.skill_histories
        ):
            raise RealPresetCheckpointRefusal(
                "old active Intent/Skill or communication replay prohibited"
            )
        original.retained = source.retained
        original.pattern_registry = source.semantic.pattern_registry
        original.fresh_native_observation_required = True
    restarted = paper.restart_same_source_world()
    if (
        restarted.new_server_session_id == first_paper_session
        or restarted.new_server_session_id != paper.owned_session_id
        or restarted.world_id != world_uuid
    ):
        raise RealPresetCheckpointRefusal("Paper process did not restart fresh")
    new_world = WorldLifetime(
        world_uuid, original_world.branch_id,
        restarted.new_server_session_id,
        original_world.epoch + 1, stopped.logical_tick,
    )
    lifecycle.install_world(WorldInstallationEvidence(
        original_world, new_world,
        "owned-paper:" + restarted.new_server_session_id,
        True, True, True, True,
    ))
    for sid in ("A", "B"):
        await bridge.login(sid)
    # Fresh native sensors MUST come from newly launched owned processes.
    # Both probes are independently request-correlated in native session.
    await asyncio.sleep(1.2)
    paper_after = _paper_join_witness(
        paper, paper_session_id=restarted.new_server_session_id,
        world_uuid=world_uuid,
    )
    if (
        paper_after["boot_id"] == paper_before["boot_id"]
        or paper_after["actor_uuids"] != paper_before["actor_uuids"]
    ):
        raise RealPresetCheckpointRefusal(
            "new Paper boot or stable player UUIDs not corroborated"
        )
    witnessed: dict[str, object] = {}
    pending: dict[str, object] = {}
    rawfiles: dict[str, Path] = {}
    first_probes: dict[str, object] = {}
    completed: dict[str, tuple[object, object]] = {}
    if inference_lane is not None:
        # Both Self submit BEFORE awaiting either result. The original shared
        # one-slot lane serializes actual provider access; no forked GPU owner.
        for sid in ("A", "B"):
            session = bridge.sessions[sid]
            raw = evidence / ("native-rejoin-" + sid + ".jsonl")
            session.start_raw_source_audit(raw)
            first = await _bounded_b_probe(session)
            prepared = prepare_restored_preset_l1(
                self_id=sid, restored=staged_by_id[sid],
                first=first, owner=owners[sid], lane=inference_lane,
                definition=definition,
                stage27i_precision_target=stage27i_precision_target,
            )
            ticket = submit_restored_preset_l1(
                prepared, lane=inference_lane,
            )
            pending[sid] = (prepared, ticket)
            rawfiles[sid] = raw
            first_probes[sid] = first
    for sid in ("A", "B"):
        session = bridge.sessions[sid]
        source = staged_by_id[sid]
        if inference_lane is None:
            native_raw = evidence / ("native-rejoin-" + sid + ".jsonl")
            session.start_raw_source_audit(native_raw)
            first = await _bounded_b_probe(session)
            observed, refreshed = await reselect_restored_move_preset_live(
                source, first, lambda: _bounded_b_probe(session),
                source_self_id=sid,
                expected_native_session_id=session.started.session_id,
                definition=definition,
            )
        else:
            native_raw = rawfiles[sid]
            first = first_probes[sid]
            prepared, ticket = pending[sid]
            observed, refreshed = await finish_restored_preset_l1(
                prepared, ticket=ticket, lane=inference_lane,
                fresh_probe=lambda: _bounded_b_probe(session),
            )
        if stage27_motor_hook is None or sid != "A":
            session.finish_raw_source_audit()
        if stage27_motor_hook is not None:
            completed[sid] = (observed, refreshed)
        # Frozen ORIGINAL Mineflayer stdout is independently reread, not
        # inferred from the parsed Python receipts alone.
        native_digest = _readback_native_probe_source(
            native_raw,
            first_request=first.request_id,
            second_request=refreshed.request_id,
            native_session=session.started.session_id,
            first_seq=first.seq, second_seq=refreshed.seq,
        )
        prior_native = (
            observed.old_native_session_id if inference_lane is None
            else observed.former_native_session_id
        )
        if (
            observed.preset_ref != accepted_refs[sid]
            or prior_native != original_native[sid]
            or observed.new_native_session_id != session.started.session_id
            or (inference_lane is None and (
                observed.physical_action_issued or observed.native_action_granted
            ))
            or (inference_lane is not None and (
                observed.issued_native_effect or observed.selection_is_action_permission
            ))
        ):
            raise RealPresetCheckpointRefusal(
                "fresh native L1 candidate not bound to restored Self Preset"
            )
        witnessed[sid] = {
            **asdict(observed),
            "owned_native_pid": session.owned_child_pid,
            "source_first": first.provenance.reference,
            "source_refreshed": refreshed.provenance.reference,
            "first_position": asdict(first.snapshot.position),
            "refreshed_position": asdict(refreshed.snapshot.position),
            "exact_native_stdout_path": str(native_raw),
            "exact_native_stdout_sha256": native_digest,
            "exact_native_stdout_two_correlated_probes": True,
        }
    if inference_lane is not None:
        inference_lane.require_world_idle()

    stage27_result: dict[str, object] | None = None
    stage27h_hook_snapshot: dict[str, object] | None = None
    if stage27_motor_hook is not None:
        if inference_lane is None or tuple(sorted(completed)) != ("A", "B"):
            raise RealPresetCheckpointRefusal("original Stage27 real model witnesses absent")
        try:
            stage27_result = await stage27_motor_hook(
                paper=paper, bridge=bridge, physical=physical,
                lane=inference_lane, owners=owners,
                world_epoch=lifecycle.world.epoch,
                prepared={sid: pending[sid][0] for sid in ("A", "B")},
                tickets={sid: pending[sid][1] for sid in ("A", "B")},
                witnesses={sid: completed[sid][0] for sid in ("A", "B")},
                refreshed={sid: completed[sid][1] for sid in ("A", "B")},
                evidence=evidence, world_uuid=world_uuid,
                native_audit=rawfiles["A"],
            )
        finally:
            # The original A native stdout audit stays active across the
            # physical children and STOP samples. Freeze it only after issue.
            bridge.sessions["A"].finish_raw_source_audit()
            witnessed["A"]["exact_native_stdout_sha256"] = file_sha256(rawfiles["A"])

    if stage27h_multi_preset:
        # Persist source-qualified original A/B state, feedback, and raw
        # physical-action summaries *before* peer logout or parent dict keys.
        stage27h_hook_snapshot = _preserve_and_validate_stage27h_hook_return(
            stage27_result, evidence=evidence,
        )

    for sid in ("A", "B"):
        await bridge.logout(sid)
    if not bridge.world_only_quiescence().no_unresolved_physical_actions:
        raise RealPresetCheckpointRefusal("new source resident WAL not clear")

    return {
        "classification": (
            stage27_result["classification"]
            if stage27_result is not None else
            "REAL_PAPER_2SELF_PRESET_LLAMA_L1_OBSERVED_DEV"
            if inference_lane is not None else
            "REAL_PAPER_2SELF_PRESET_CHECKPOINT_SCRIPTED_L1_DEV"
        ),
        "world_uuid": world_uuid,
        "original_paper_session": first_paper_session,
        "new_paper_session": restarted.new_server_session_id,
        "paper_join_before": paper_before,
        "paper_join_after": paper_after,
        "restored_fork_branch": restore_receipt["fork_branch_id"],
        "fork_used_as_running_world": False,
        "same_source_paper_restart": True,
        "committed_generation": str(checkpoint),
        "original_native_sessions": original_native,
        "original_owned_pids": original_pid,
        "new_l1_option_witnesses": witnessed,
        "real_gemma_systemone_executed": False,
        "real_llama_cpp_bounded_inference_executed": inference_lane is not None,
        "backend_model_operator_declared": (
            inference_lane.provider.model if inference_lane is not None else None
        ),
        "backend_model_weights_independently_verified": False,
        "stage27": stage27_result,
        "stage27h_hook_snapshot": stage27h_hook_snapshot,
        "real_native_physical_action_issued": (
            bool(stage27_result["physical_effect_observed"])
            if stage27_result is not None else False
        ),
        "old_action_or_skill_replayed": False,
        "old_gpu_output_reused": False,
        "owner_acceptance": "OPERATOR_DEV_TEMPLATE_NOT_AUTONOMOUS_SELF",
        "physical_action_issue_authorized": (
            bool(stage27_result["physical_effect_observed"])
            if stage27_result is not None else False
        ),
    }


async def run_real_two_self_preset_checkpoint(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    real_world_dev_grant: bool,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
    real_gemma_l1: bool = False,
    gemma_l1_endpoint: str | None = None,
    gemma_l1_model: str | None = None,
    gemma_l1_jev: bool = False,
    _stage27_motor_hook: Callable[..., Awaitable[dict[str, object]]] | None = None,
    _stage27h_multi_preset: bool = False,
    _stage27i_precision_target: bool = False,
) -> Path:
    """Never launches Paper absent explicit EULA/World DEV flags and pinned jars."""
    if accepted_eula is not True or real_world_dev_grant is not True:
        raise RealPresetCheckpointRefusal(
            "HOLD: user-authorized Minecraft EULA and real World DEV required"
        )
    # A real bounded-model path is strict opt-in and MUST be an owned,
    # exclusive loopback llama-server with exactly one currently idle slot.
    # Do not launch an isolated Paper World when the model source is invalid.
    if type(real_gemma_l1) is not bool or type(gemma_l1_jev) is not bool:
        raise RealPresetCheckpointRefusal("typed real-Gemma L1 mode required")
    if real_gemma_l1 != (gemma_l1_endpoint is not None):
        raise RealPresetCheckpointRefusal(
            "real-Gemma opt-in needs exactly one explicit local endpoint"
        )
    if real_gemma_l1 != (gemma_l1_model is not None):
        raise RealPresetCheckpointRefusal(
            "real-Gemma opt-in requires operator-declared model identity"
        )
    if _stage27_motor_hook is not None and (
        not callable(_stage27_motor_hook) or not real_gemma_l1 or gemma_l1_jev
    ):
        raise RealPresetCheckpointRefusal(
            "Stage27 native MOVE requires a separate real bounded model hook"
        )
    if (
        type(_stage27h_multi_preset) is not bool
        or type(_stage27i_precision_target) is not bool
        or (_stage27i_precision_target and not _stage27h_multi_preset)
        or (_stage27h_multi_preset and _stage27_motor_hook is None)
    ):
        raise RealPresetCheckpointRefusal(
            "Stage27h multi-action budget requires explicit original motor hook"
        )
    provider = None
    slot_witness = None
    if real_gemma_l1:
        provider = LlamaCppRelayProvider(
            endpoint=gemma_l1_endpoint, model=gemma_l1_model,
            timeout=55.0,
            systemone_endpoint=gemma_l1_endpoint if gemma_l1_jev else None,
        )
        slot_witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref="stage26-owned-one-slot-llama",
            timeout_s=2.0,
        )
        slot_witness.require_idle()
    elif gemma_l1_jev:
        raise RealPresetCheckpointRefusal(
            "JEV/choice mode requires explicit real bounded L1 opt-in"
        )
    paper_src, plugin_src, scratch = preflight_two_native(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
        java=java, node=node, timeout_s=timeout_s, heap_mb=heap_mb,
    )
    root = Path(tempfile.mkdtemp(prefix="p0d-real-preset-cut-", dir=scratch))
    os.chmod(root, 0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    if provider is not None:
        model_source = evidence / "original-model-http"
        model_source.mkdir(mode=0o700)
        provider.enable_stage26_raw_audit(model_source)
    plugins = root / "plugins"
    plugins.mkdir(mode=0o700)
    shutil.copyfile(paper_src, root / "paper.jar")
    shutil.copyfile(plugin_src, plugins / "P0BRecorder.jar")
    _write_bytes_new(root / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(
        root / "server.properties", two_native_server_properties(port).encode(),
    )
    launch = (
        java, "-Xms512M", f"-Xmx{heap_mb}M",
        "-jar", str(root / "paper.jar"), "--nogui",
    )
    report_path = evidence / "preset-two-self-result.json"
    report: dict[str, object] = {
        "classification": "HOLD", "eula_accepted": True,
        "real_world_dev_grant": True,
        "paper_sha256": paper_sha256,
        "plugin_sha256": plugin_sha256,
        "scratch": str(root),
        "real_gemma_systemone_executed": False,
        "physical_action_issue_authorized": False,
    }
    paper: OwnedPaperWorld | None = None
    bridge: OwnedResidentPhysicalBridge | None = None
    physical: PhysicalIssueAdmission | None = None
    lane: ResidentLlamaInferenceLane | None = None
    try:
        bootstrap = _bootstrap_paper(
            world_root=root, launch=launch, timeout_s=timeout_s,
        )
        world_uuid = _world_uuid(root / "world")
        report["bootstrap_sha256"] = file_sha256(bootstrap)
        holder: dict[str, OwnedPaperWorld] = {}
        tick = PaperMainThreadTickReader(
            spool_dir=plugins / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_uuid,
            read_owned_log=lambda session: holder["paper"].read_owned_log(session),
            timeout_seconds=min(15.0, timeout_s / 3),
        )
        paper = OwnedPaperWorld(
            server_dir=root, world_dir=root / "world",
            evidence_dir=evidence, command=launch,
            world_id=world_uuid, branch_id="p0d-real-preset-cut",
            tick_readback=tick, timeout_seconds=timeout_s,
        )
        holder["paper"] = paper
        first_paper = paper.start_owned()
        names = ("A", "B")
        original_ids = {sid: "offline-born-" + sid for sid in names}
        physical = PhysicalIssueAdmission(
            original_ids, resident_mode=True,
            initially_offline=True,
            allow_resident_move=_stage27_motor_hook is not None,
        )
        configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=port,
                username="Relay" + sid, version="1.21.8",
            ) for sid in names
        }
        originals: dict[str, CheckpointedCognitiveOwner] = {}
        for sid in names:
            folder = root / ("self-" + sid)
            folder.mkdir(mode=0o700)
            wal = folder / "physical-wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            originals[sid] = CheckpointedCognitiveOwner(
                retained=PersistentCognition(
                    IdentitySpecification(
                        sid, ("Keep original Self learning distinct.",),
                        Provenance("stage25-real-preset", sid),
                    ),
                ),
                intent=IntentCommitment(),
                pattern_registry=initial_patterns_with_move(),
                native_session_id=original_ids[sid],
                last_observed_tick=0,
                files=CognitiveOwnerFiles(
                    folder, folder / "cognition.json", wal,
                ),
                physical_supervisor=ActionSupervisor(),
            )
        work = ResidentCognitiveWorkOwner(originals)
        if provider is not None:
            assert slot_witness is not None
            lane = ResidentLlamaInferenceLane(
                provider=provider, cognitive_work=work,
                witness=slot_witness,
            )
        lifecycle = WorldResidentLifecycle(
            world=WorldLifetime(
                world_uuid, "p0d-real-preset-cut", first_paper, 0, 0,
            ),
            persisted_self_refs={
                sid: f"original-cognition:{sid}" for sid in names
            },
        )

        async def launch_owned(config: MineflayerLaunchConfig):
            return await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=min(30.0, timeout_s / 3),
            )

        bridge = OwnedResidentPhysicalBridge(
            lifecycle=lifecycle, physical=physical, paper=paper,
            configs=configs, owners=originals,
            launch=launch_owned, cognitive_work=work,
            inference_lane=lane,
            probe_timeout_s=min(30.0, timeout_s / 3),
        )
        trial = await _real_preset_trial(
            paper=paper, bridge=bridge, physical=physical,
            work=work, lifecycle=lifecycle, owners=originals,
            evidence=evidence, world_uuid=world_uuid,
            inference_lane=lane,
            stage27_motor_hook=_stage27_motor_hook,
            stage27h_multi_preset=_stage27h_multi_preset,
            stage27i_precision_target=_stage27i_precision_target,
        )
        report.update(trial)
    except BaseException as exc:
        report["classification"] = "HOLD"
        report["reason"] = f"{type(exc).__name__}: {exc}"
        # Even when a result-contract error propagates, the hook return may
        # already be fsynced after irreversible native movement. Keep a
        # pointer in the terminal HOLD report; never infer it is validated.
        captured = evidence / "stage27h-original-motor-hook-return.json"
        if _stage27h_multi_preset and captured.is_file() and not captured.is_symlink():
            report["stage27h_hook_return_evidence"] = str(captured)
            report["stage27h_hook_return_sha256"] = file_sha256(captured)
            report["stage27h_hook_contract_valid"] = False
        if _stage27i_precision_target:
            # When B mutates during physical motion, its original before/after
            # snapshots still survive even though the hook cannot return.
            peer_evidence: dict[str, object] = {}
            for label in ("before", "after"):
                path = evidence / f"stage27i-peer-b-{label}.json"
                if path.is_file() and not path.is_symlink():
                    peer_evidence[label] = {
                        "path": str(path), "sha256": file_sha256(path),
                    }
            report["stage27i_peer_b_evidence"] = peer_evidence
            report["stage27i_peer_b_comparison_attested"] = False
            model_files: dict[str, object] = {}
            for label in ("before", "after"):
                path = evidence / f"stage27i-model-http-{label}.json"
                if path.is_file() and not path.is_symlink():
                    model_files[label] = {
                        "path": str(path), "sha256": file_sha256(path),
                    }
            report["stage27i_model_http_evidence"] = model_files
            report["stage27i_no_extra_model_calls_attested"] = False
        if physical is not None:
            physical.hold_for_operator()
        raise
    finally:
        if bridge is not None:
            for session in {
                id(s): s for s in bridge.sessions.values()
            }.values():
                try:
                    if session.process_returncode is None:
                        await asyncio.wait_for(session.terminate(), timeout=8)
                except BaseException:
                    report["cleanup_uncertain"] = True
                    report["classification"] = "HOLD"
        if paper is not None and paper.owned_session_id is not None:
            if not paper.held_uncertain:
                try:
                    paper.stop_and_save()
                except BaseException:
                    report["cleanup_uncertain"] = True
                    report["classification"] = "HOLD"
        _write_bytes_new(
            report_path, (json.dumps(report, sort_keys=True, indent=2)
                          + "\n").encode(),
        )
        print(f"P0D_REAL_PRESET_AUDIT={report_path}", file=sys.stderr, flush=True)
        if paper is not None and paper.owned_session_id is not None:
            print(
                "P0D_HOLD: owned disposable Paper may still run; inspect PID.",
                file=sys.stderr, flush=True,
            )
    expected_classification = (
        "REAL_PAPER_2SELF_PRESET_LLAMA_L1_OBSERVED_DEV"
        if real_gemma_l1
        else "REAL_PAPER_2SELF_PRESET_CHECKPOINT_SCRIPTED_L1_DEV"
    )
    if _stage27_motor_hook is not None:
        expected_classifications = {
            "REAL_STAGE27_A_PLACE_MOVE_NATIVE_OBSERVED_DEV",
            "REAL_STAGE27_A_PLACE_NO_PROGRESS_NATIVE_OBSERVED_DEV",
            "REAL_STAGE27_A_PLACE_MOVE_OVERSHOOT_DEV",
            "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV",
            "REAL_STAGE27H_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
            "REAL_STAGE27H_L0_BUDGET_EXHAUSTED_DEV",
            "REAL_STAGE27H_L0_NO_PROGRESS_DEV",
            "REAL_STAGE27H_L0_UNREACHED_DEV",
            "REAL_STAGE27I_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
            "REAL_STAGE27I_L0_BUDGET_EXHAUSTED_DEV",
            "REAL_STAGE27I_L0_NO_PROGRESS_DEV",
            "REAL_STAGE27I_L0_UNREACHED_DEV",
        }
    else:
        expected_classifications = {expected_classification}
    if report["classification"] not in expected_classifications:
        raise RealPresetCheckpointRefusal("unqualified real PRESET World result")
    return report_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paper-jar", type=Path, required=True)
    p.add_argument("--paper-sha256", required=True)
    p.add_argument("--plugin-jar", type=Path, required=True)
    p.add_argument("--plugin-sha256", required=True)
    p.add_argument("--scratch-parent", type=Path, required=True)
    p.add_argument("--eula-accepted", action="store_true")
    p.add_argument("--real-world-dev-grant", action="store_true")
    p.add_argument("--java", default="java")
    p.add_argument("--node", default="node")
    p.add_argument("--timeout-s", type=float, default=120.0)
    p.add_argument("--heap-mb", type=int, default=1536)
    p.add_argument("--real-gemma-l1", action="store_true")
    p.add_argument("--gemma-l1-endpoint")
    p.add_argument("--gemma-l1-model")
    p.add_argument("--gemma-l1-jev", action="store_true")
    a = p.parse_args()
    try:
        result = asyncio.run(run_real_two_self_preset_checkpoint(
            paper_jar=a.paper_jar, paper_sha256=a.paper_sha256,
            plugin_jar=a.plugin_jar, plugin_sha256=a.plugin_sha256,
            scratch_parent=a.scratch_parent, accepted_eula=a.eula_accepted,
            real_world_dev_grant=a.real_world_dev_grant,
            java=a.java, node=a.node,
            timeout_s=a.timeout_s, heap_mb=a.heap_mb,
            real_gemma_l1=a.real_gemma_l1,
            gemma_l1_endpoint=a.gemma_l1_endpoint,
            gemma_l1_model=a.gemma_l1_model,
            gemma_l1_jev=a.gemma_l1_jev,
        ))
    except Exception as exc:
        print(f"P0D_REAL_PRESET_HOLD={type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2
    print(f"P0D_REAL_PRESET_RESULT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
