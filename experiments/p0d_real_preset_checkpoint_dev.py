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
from relay_self.p0d_real_preset_reselect_dev import reselect_restored_move_preset
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
) -> dict[str, object]:
    """One admitted real-world no-motor attempt with full saved Self cohort."""
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
            "exploration-move", "OperatorNearProbe", 1,
            definition.definition_ref,
            SkillConstraints(), SkillBudget(1, 1500, 2.0, 4),
            Provenance("operator-dev-proposed", f"stage25:{sid}"),
            expected_cost=SkillCostEstimate(1, 1200, 1.0),
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
    for sid in ("A", "B"):
        session = bridge.sessions[sid]
        first = await _bounded_b_probe(session)
        refreshed = await _bounded_b_probe(session)
        source = staged_by_id[sid]
        observed = reselect_restored_move_preset(
            source, first, refreshed,
            source_self_id=sid,
            expected_native_session_id=session.started.session_id,
            definition=definition,
        )
        if (
            observed.preset_ref != accepted_refs[sid]
            or observed.old_native_session_id != original_native[sid]
            or observed.new_native_session_id != session.started.session_id
            or observed.physical_action_issued or observed.native_action_granted
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
        }

    for sid in ("A", "B"):
        await bridge.logout(sid)
    if not bridge.world_only_quiescence().no_unresolved_physical_actions:
        raise RealPresetCheckpointRefusal("new source resident WAL not clear")

    return {
        "classification": "REAL_PAPER_2SELF_PRESET_CHECKPOINT_SCRIPTED_L1_DEV",
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
        "real_native_physical_action_issued": False,
        "old_action_or_skill_replayed": False,
        "old_gpu_output_reused": False,
        "owner_acceptance": "OPERATOR_DEV_TEMPLATE_NOT_AUTONOMOUS_SELF",
        "physical_action_issue_authorized": False,
    }


async def run_real_two_self_preset_checkpoint(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    real_world_dev_grant: bool,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
) -> Path:
    """Never launches Paper absent explicit EULA/World DEV flags and pinned jars."""
    if accepted_eula is not True or real_world_dev_grant is not True:
        raise RealPresetCheckpointRefusal(
            "HOLD: user-authorized Minecraft EULA and real World DEV required"
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
            initially_offline=True, allow_resident_move=False,
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
            probe_timeout_s=min(30.0, timeout_s / 3),
        )
        trial = await _real_preset_trial(
            paper=paper, bridge=bridge, physical=physical,
            work=work, lifecycle=lifecycle, owners=originals,
            evidence=evidence, world_uuid=world_uuid,
        )
        report.update(trial)
    except BaseException as exc:
        report["classification"] = "HOLD"
        report["reason"] = f"{type(exc).__name__}: {exc}"
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
    if report["classification"] != (
        "REAL_PAPER_2SELF_PRESET_CHECKPOINT_SCRIPTED_L1_DEV"
    ):
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
    a = p.parse_args()
    try:
        result = asyncio.run(run_real_two_self_preset_checkpoint(
            paper_jar=a.paper_jar, paper_sha256=a.paper_sha256,
            plugin_jar=a.plugin_jar, plugin_sha256=a.plugin_sha256,
            scratch_parent=a.scratch_parent, accepted_eula=a.eula_accepted,
            real_world_dev_grant=a.real_world_dev_grant,
            java=a.java, node=a.node,
            timeout_s=a.timeout_s, heap_mb=a.heap_mb,
        ))
    except Exception as exc:
        print(f"P0D_REAL_PRESET_HOLD={type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2
    print(f"P0D_REAL_PRESET_RESULT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
