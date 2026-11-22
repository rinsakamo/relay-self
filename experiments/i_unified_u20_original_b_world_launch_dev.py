"""U20: isolated real Paper + ORIGINAL restored B Stage26 S1 -> S2 DEV.

LOCAL WSL operator entry, not a GitHub Actions World test or success claim.
Requires a verified *single-B*, same-generation typed World/Self checkpoint
whose saved B Schema already contains the accepted MOVE Preset. Historical
A/B read-only restore is deliberately NOT coerced to this issuing B roster.

All actual effects pass the existing B Owner, GPU lane, Native final gate,
PhysicalIssueAdmission, original WAL and U17 two-PLACE entry. No retries.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
)
from experiments.i_unified_u17_original_two_place_trial_dev import (
    run_original_u17_two_place_trial_dev,
)
from experiments.i_unified_u20_stage26_raw_provider_dev import (
    U20Stage26RawBoundedProvider,
)
from experiments.p0d_real_paper_smoke_dev import (
    _free_local_port,
    _world_uuid,
    _write_bytes_new,
)
from experiments.p0d_real_two_native_smoke_dev import (
    _verify_local_runtime,
    two_native_server_properties,
)
from experiments.stage24g_model_gate_dev import (
    Stage24gModelGateReceipt,
    verify_stage24g_model_gate,
)
from experiments.stage24g_pinned_assets_launch_dev import (
    check_stage24g_pinned_assets,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
    StagedRecoveredCognition,
)
from relay_self.innate_schema import SchemaMode
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionBinding
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    bootstrap_restored_schemas,
)
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28InertRecovery,
    stage28_inert_cognitive_recovery,
)
from relay_self.stage28c2b_execution_copy_dev import _inventory
from relay_self.world_resident_lifecycle_dev import (
    WorldLifetime,
    WorldResidentLifecycle,
)
from relay_self.q4_place_abort_dev import Q4DevOperatorPermit


class U20OriginalWorldHold(RuntimeError):
    """No standalone Q4 success without actual source-qualified World evidence."""


def inspect_u20_original_b_source(
    *, generation: Path, restored: Path, paper_jar: Path, plugin_jar: Path,
    scratch_parent: Path, gguf: Path, llama_pid: int,
    model_alias: str, llama_endpoint: str, java: str, node: str,
) -> tuple[Stage28InertRecovery, Stage24gModelGateReceipt]:
    """Read-only preflight, performed BEFORE copying or launching any World.

    Existing original Stage28 typed same-generation verification, original
    Schema activation, pinned Paper jars and existing RTX/llama PID+socket
    checks are mandatory. Never mint a missing original MOVE Preset.
    """
    _verify_local_runtime(java, node)
    for directory in (generation, restored, scratch_parent):
        if (
            not isinstance(directory, Path) or directory.is_symlink()
            or not directory.is_dir()
        ):
            raise U20OriginalWorldHold("real source and scratch directories required")
    source_world = _world_uuid(restored / "world")
    plan = stage28_inert_cognitive_recovery(
        generation, restored, expected_self_ids=("B",),
        expected_source_world_id=source_world,
    )
    if (
        plan.roster != ("B",) or len(plan.candidates) != 1
        or plan.candidates[0].self_id != "B"
        or plan.candidates[0].native_session_bound
        or plan.candidates[0].issue_authorized
        or plan.candidates[0].semantic.cut.schema_snapshot is None
        or plan.candidates[0].semantic.cut.schema_snapshot.get(
            "exploratory",
        ).mode is not SchemaMode.FULL
        or plan.candidates[0].semantic.skill_histories
        or plan.candidates[0].semantic.intent.current_intent is not None
    ):
        raise U20OriginalWorldHold(
            "single original B saved ACTIVE exploration Schema/Preset, "
            "empty Intent and no replayable Skill required"
        )
    candidate = plan.candidates[0]
    journal = PhysicalActionJournal.restore(
        candidate.physical_wal_path, self_id="B",
    )
    journal.require_clear()
    if journal.records:
        raise U20OriginalWorldHold("Q4 first original S1 WAL must start empty")
    check_stage24g_pinned_assets(
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        scratch_parent=scratch_parent, accepted_eula=True,
    )
    gate = verify_stage24g_model_gate(
        gguf_path=gguf, llama_pid=llama_pid, model_alias=model_alias,
        llama_endpoint=llama_endpoint, systemone_endpoint=llama_endpoint,
    )
    if gate.slot_count != 1 or gate.slot_id != 0:
        raise U20OriginalWorldHold("original B requires one idle owned model slot")
    return plan, gate


def _require_isolated_u20_paths(
    generation: Path, restored: Path, execution: Path, evidence: Path,
) -> None:
    """Never overwrite or run from archived checkpoint or mutable source."""
    gen = generation.resolve(strict=True)
    src = restored.resolve(strict=True)
    ex = execution.absolute()
    ev = evidence.absolute()
    if (
        execution != ex or evidence != ev
        or execution.exists() or execution.is_symlink()
        or evidence.exists() or evidence.is_symlink()
        or not ex.parent.is_dir() or ex.parent.is_symlink()
        or not ev.parent.is_dir() or ev.parent.is_symlink()
        or ex == ev or ex in ev.parents or ev in ex.parents
        or any(
            source == target or source in target.parents
            or target in source.parents
            for source in (gen, src) for target in (ex, ev)
        )
    ):
        raise U20OriginalWorldHold("fresh separated absolute execution/evidence roots required")


def _restore_original_b_for_u20(
    *, plan: Stage28InertRecovery, execution: Path,
) -> tuple[StagedRecoveredCognition, CheckpointedCognitiveOwner,
           ResidentCognitiveWorkOwner, PhysicalIssueAdmission]:
    """One exact B existing Owner; never construct a shadow cognition engine."""
    if plan.roster != ("B",) or len(plan.candidates) != 1:
        raise U20OriginalWorldHold("original single-B typed source unavailable")
    candidate = plan.candidates[0]
    cut = candidate.semantic.cut
    root = execution / "selves" / "B"
    owner = CheckpointedCognitiveOwner(
        retained=candidate.retained, intent=candidate.semantic.intent,
        pattern_registry=candidate.semantic.pattern_registry,
        native_session_id=cut.former_native_session_id,
        last_observed_tick=cut.last_observed_world_tick,
        files=CognitiveOwnerFiles(
            root, root / "cognition.json", root / "physical-wal.json",
        ),
        physical_supervisor=ActionSupervisor(),
        skills=candidate.semantic.skill_histories,
        peer_deliveries=cut.peer_deliveries,
        pending_questions=cut.pending_question_refs,
    )
    owner.fresh_native_observation_required = True
    work = ResidentCognitiveWorkOwner({"B": owner})
    bootstrap_restored_schemas(
        work, SchemaBootstrapConfig(True), source_cuts=(cut,),
    )
    physical = PhysicalIssueAdmission(
        {"B": cut.former_native_session_id},
        resident_mode=True, initially_offline=True,
        allow_resident_move=True, allow_resident_place_move=True,
    )
    return candidate, owner, work, physical


def _u20_scoped_original_grants(
    binding: PhysicalActionBinding,
) -> tuple[PhysicalDevGrant, PhysicalDevGrant]:
    """Explicit operator DEV labels, still checked by original issuer/WAL."""
    if not isinstance(binding, PhysicalActionBinding):
        raise U20OriginalWorldHold("original ActionPort binding required")
    def one(stage: PhysicalGrantStage) -> PhysicalDevGrant:
        return PhysicalDevGrant(
            stage=stage,
            authority_id="u20-operator-q4-" + stage.value.lower()
            + ":" + binding.action_id,
            provenance=Provenance(
                "u20-explicit-dev-" + stage.value.lower(),
                binding.native_source.reference,
            ),
            intent_id=binding.intent_id,
            action_id=binding.action_id,
            session_id=binding.scope.world_session_id,
            probe_seq=binding.native_seq,
            probe_request_id=binding.native_request_id,
            selected_target_ref=binding.target_ref,
            granted=True,
        )
    return one(PhysicalGrantStage.PROPOSE), one(PhysicalGrantStage.ISSUE)


async def run_u20_original_b_world_once(
    *, generation: Path, restored: Path, execution_dir: Path,
    evidence_dir: Path, paper_jar: Path, plugin_jar: Path,
    gguf: Path, llama_pid: int, model_alias: str, llama_endpoint: str,
    java: str = "java", node: str = "node",
    trial_mode: str = "two_moves", real_world_dev_granted: bool = False,
    model_post_granted: bool = False, accepted_eula: bool = False,
) -> Path:
    """One real owned Paper + one Native B + original L1 S1/S2 or STOP fault.

    Only raw CAPTURED_UNAUDITED/FAULT_CAPTURED_UNAUDITED may be returned.
    Independent Q audits original producer bytes later; this code never
    reports REAL_WORLD_DEV_PASS, QUAL_GO or SCIENCE.
    """
    if (
        not accepted_eula or not real_world_dev_granted
        or not model_post_granted
        or trial_mode not in ("two_moves", "stop_failure")
    ):
        raise U20OriginalWorldHold("explicit one-run Paper/EULA/Gemma grants required")
    plan, model_gate = inspect_u20_original_b_source(
        generation=generation, restored=restored,
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        scratch_parent=execution_dir.parent, gguf=gguf,
        llama_pid=llama_pid, model_alias=model_alias,
        llama_endpoint=llama_endpoint, java=java, node=node,
    )
    _require_isolated_u20_paths(
        generation, restored, execution_dir, evidence_dir,
    )
    before = _inventory(restored)
    shutil.copytree(restored, execution_dir, symlinks=True)
    if _inventory(restored) != before or _inventory(execution_dir) != before:
        raise U20OriginalWorldHold("source or owned execution copy differs in bytes")
    copy_plan = stage28_inert_cognitive_recovery(
        generation, execution_dir, expected_self_ids=("B",),
        expected_source_world_id=plan.source_world_id,
    )
    if (
        copy_plan.roster != plan.roster
        or copy_plan.old_native_sessions != plan.old_native_sessions
        or copy_plan.source_committed_sha256 != plan.source_committed_sha256
        or copy_plan.candidates[0].retained != plan.candidates[0].retained
    ):
        raise U20OriginalWorldHold("original B restore changed during executable copy")
    restored_b, owner, work, physical = _restore_original_b_for_u20(
        plan=copy_plan, execution=execution_dir,
    )
    evidence_dir.mkdir(mode=0o700)
    _write_bytes_new(
        evidence_dir / "u20-preworld-source.json",
        (json.dumps({
            "source_generation": plan.generation_id,
            "source_commit_sha256": plan.source_committed_sha256,
            "world_uuid": plan.source_world_id,
            "branch": plan.fork_branch_id,
            "roster": ["B"],
            "former_native": dict(plan.old_native_sessions)["B"],
            "model_gate": asdict(model_gate),
            "original_preset_from_saved_source": True,
            "real_world_dev_pass": False,
        }, sort_keys=True) + "\n").encode(),
    )
    plugin_dir = execution_dir / "plugins"
    plugin_dir.mkdir(mode=0o700, exist_ok=True)
    shutil.copyfile(paper_jar, execution_dir / "paper.jar")
    shutil.copyfile(plugin_jar, plugin_dir / "P0BRecorder.jar")
    _write_bytes_new(execution_dir / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(
        execution_dir / "server.properties",
        two_native_server_properties(port).encode(),
    )

    paper_holder: dict[str, OwnedPaperWorld] = {}
    tick_reader = PaperMainThreadTickReader(
        spool_dir=plugin_dir / "P0BRecorder" / "p0d-ticks",
        expected_world_uuid=plan.source_world_id,
        read_owned_log=lambda sid: paper_holder["world"].read_owned_log(sid),
        timeout_seconds=15.0, allow_repeated_same_boot=True,
    )
    paper = OwnedPaperWorld(
        server_dir=execution_dir, world_dir=execution_dir / "world",
        evidence_dir=evidence_dir,
        command=(
            java, "-Xms512M", "-Xmx1536M", "-jar",
            str(execution_dir / "paper.jar"), "--nogui",
            "-Drelay.q4.paper.fine_samples=true",
        ),
        world_id=plan.source_world_id, branch_id=plan.fork_branch_id,
        tick_readback=tick_reader, timeout_seconds=90.0,
    )
    paper_holder["world"] = paper
    sessions: list[MineflayerProcessSession] = []
    bridge: OwnedResidentPhysicalBridge | None = None
    report: dict[str, object] = {
        "schema": 1, "trial_mode": trial_mode,
        "classification": "U20_PRE_WORLD_HOLD",
        "world_started": False, "gemma_posts_attempted": 0,
        "real_world_dev_pass": False, "qual_go": False,
        "science_run": False, "independent_q_audited": False,
    }
    provider: U20Stage26RawBoundedProvider | None = None
    try:
        session_id = await asyncio.to_thread(paper.start_owned)
        report["world_started"] = True
        report["paper_owned_session"] = session_id
        tick = await asyncio.to_thread(paper.tick_readback, session_id)
        paper_bytes = paper.read_owned_log(session_id)
        if (
            tick.server_session_id != session_id
            or not tick.source_ref.startswith("paper-main-thread:p0d:")
            or not paper_bytes or paper._assert_owned().pid <= 0
        ):
            raise U20OriginalWorldHold("owned Paper tick/process source absent")
        life = WorldResidentLifecycle(
            world=WorldLifetime(
                plan.source_world_id, plan.fork_branch_id,
                session_id, 1, tick.tick,
            ),
            persisted_self_refs={
                "B": "verified-original:" + str(owner.files.cognition_file),
            },
            independent_native_world_clock=True,
        )
        raw_dir = evidence_dir / "original-model-http"
        raw_dir.mkdir(mode=0o700)
        provider = U20Stage26RawBoundedProvider(
            endpoint=llama_endpoint, model=model_alias,
            raw_dir=raw_dir, timeout=45.0,
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref="u20-original-pid-" + str(llama_pid),
        )
        witness.require_idle()
        lane = ResidentLlamaInferenceLane(
            provider=provider, cognitive_work=work, witness=witness,
        )

        async def launch_original(config: MineflayerLaunchConfig):
            native = await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=30.0,
                enable_q4_bounded_place_dev=True,
            )
            sessions.append(native)
            return native

        bridge = OwnedResidentPhysicalBridge(
            lifecycle=life, physical=physical, paper=paper,
            configs={"B": MineflayerLaunchConfig(
                host="127.0.0.1", port=port,
                username="RelayB", version="1.21.8",
            )},
            owners={"B": owner}, cognitive_work=work,
            inference_lane=lane, launch=launch_original,
            forbidden_native_sessions=frozenset(
                dict(plan.old_native_sessions).values(),
            ), probe_timeout_s=30.0,
        )
        await bridge.login("B")
        actual_native = bridge.sessions["B"]
        report["owned_native_pid"] = actual_native.owned_child_pid
        report["original_native_session"] = actual_native.started.session_id
        permit1 = Q4DevOperatorPermit("B", actual_native.started.session_id)
        permit2 = Q4DevOperatorPermit("B", actual_native.started.session_id)
        try:
            receipts = await run_original_u17_two_place_trial_dev(
                bridge=bridge, self_id="B", evidence_dir=evidence_dir,
                restored=restored_b,
                grant_for_action=_u20_scoped_original_grants,
                s1_operator_permit=permit1,
                s2_operator_permit=permit2,
                provenance=Provenance(
                    "u20-original-b-world-dev", session_id,
                ),
                real_world_granted=True, trial_mode=trial_mode,
            )
        except BaseException:
            if trial_mode != "stop_failure":
                raise
            if (
                not actual_native._q4_stop_failure_used
                or actual_native.process_returncode is None
            ):
                raise U20OriginalWorldHold(
                    "STOP fault not consumed or original Native still alive"
                )
            report["classification"] = "U20_STOP_FAULT_CAPTURED_UNAUDITED"
            report["fault_node_exit_confirmed"] = True
        else:
            if trial_mode != "two_moves":
                raise U20OriginalWorldHold("STOP fault trial unexpectedly completed")
            first, second = receipts
            if (
                first.action_id == second.action_id
                or first.native_session_id != second.native_session_id
            ):
                raise U20OriginalWorldHold("original two-MOVE identity mismatch")
            report["classification"] = "U20_TWO_PLACE_CAPTURED_UNAUDITED"
            report["original_s1_action_id"] = first.action_id
            report["original_s2_action_id"] = second.action_id
        report["gemma_posts_attempted"] = provider.attempted
        report["gemma_posts_completed"] = provider.completed
        if not 1 <= provider.attempted <= 2:
            raise U20OriginalWorldHold("real Stage26 model POST count unqualified")
    except BaseException as exc:
        report["reason"] = type(exc).__name__ + ": " + str(exc)
        physical.hold_for_operator()
        raise
    finally:
        # Never attach to an existing Paper/process or silently retry.
        # The original U17 child cleanup already forces exit; this parent
        # independently attempts cleanup for failure before it was reached.
        for native in sessions:
            if native.process_returncode is None:
                try:
                    await asyncio.shield(
                        native.force_terminate_owned(timeout_s=0.5),
                    )
                except BaseException:
                    report["native_cleanup_uncertain"] = True
        if provider is not None:
            report["gemma_posts_attempted"] = provider.attempted
            report["gemma_posts_completed"] = provider.completed
        if paper.owned_session_id is not None:
            try:
                report["paper_stopped"] = asdict(
                    await asyncio.to_thread(paper.stop_and_save),
                )
            except BaseException as exc:
                report["paper_cleanup_uncertain"] = type(exc).__name__
                proc = paper._process
                if proc is not None and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=8)
                    except (OSError, subprocess.TimeoutExpired):
                        proc.kill()
                        proc.wait(timeout=8)
                report["paper_terminated_pid"] = proc.pid if proc else None
        if report.get("native_cleanup_uncertain") or report.get("paper_cleanup_uncertain"):
            report["classification"] = "U20_CLEANUP_UNCERTAIN_HOLD"
        _write_bytes_new(
            evidence_dir / "u20-original-world-capture.json",
            (json.dumps(report, sort_keys=True, indent=2) + "\n").encode(),
        )
    return evidence_dir / "u20-original-world-capture.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", required=True, type=Path)
    parser.add_argument("--restored", required=True, type=Path)
    parser.add_argument("--paper-jar", required=True, type=Path)
    parser.add_argument("--plugin-jar", required=True, type=Path)
    parser.add_argument("--gguf", required=True, type=Path)
    parser.add_argument("--llama-pid", required=True, type=int)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--llama-endpoint", required=True)
    parser.add_argument("--execution-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--trial-mode", choices=("two_moves", "stop_failure"),
                        default="two_moves")
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--model-post-grant", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if args.inspect_only:
            if (
                args.real_world_dev_grant or args.model_post_grant
                or args.execution_dir is not None or args.evidence_dir is not None
            ):
                raise U20OriginalWorldHold("read-only mode cannot grant world or execution")
            plan, _ = inspect_u20_original_b_source(
                generation=args.generation, restored=args.restored,
                paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
                scratch_parent=args.restored.parent,
                gguf=args.gguf, llama_pid=args.llama_pid,
                model_alias=args.model_alias, llama_endpoint=args.llama_endpoint,
                java=args.java, node=args.node,
            )
            print("U20_PREWORLD_SOURCE_PASS no_world=true no_model_post=true "
                  + "source_generation=" + plan.generation_id)
            return 0
        if args.execution_dir is None or args.evidence_dir is None:
            raise U20OriginalWorldHold("fresh execution and evidence paths required")
        result = asyncio.run(run_u20_original_b_world_once(
            generation=args.generation, restored=args.restored,
            execution_dir=args.execution_dir, evidence_dir=args.evidence_dir,
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            gguf=args.gguf, llama_pid=args.llama_pid,
            model_alias=args.model_alias, llama_endpoint=args.llama_endpoint,
            java=args.java, node=args.node,
            trial_mode=args.trial_mode,
            real_world_dev_granted=args.real_world_dev_grant,
            model_post_granted=args.model_post_grant,
            accepted_eula=args.eula_accepted,
        ))
        print("U20_CAPTURED_UNAUDITED=" + str(result))
        return 0
    except BaseException as exc:
        print("U20_HOLD=" + type(exc).__name__ + ":" + str(exc),
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
