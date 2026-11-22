"""Generate one passive, isolated, original B typed Paper checkpoint."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
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
from experiments.p0d_real_two_native_smoke_dev import (
    _verify_local_runtime,
    two_native_server_properties,
)
from experiments.stage24g_pinned_assets_launch_dev import check_stage24g_pinned_assets
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import CognitiveOwnerFiles
from relay_self.cognitive_minimal_dev import initial_move_pattern
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.innate_schema import SchemaMode
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    bootstrap_fresh_schemas,
    create_fresh_owner,
)
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.skill_invocation import SkillBudget, SkillConstraints, SkillParameterPreset
from relay_self.stage28_cognitive_recovery_gate_dev import stage28_inert_cognitive_recovery
from relay_self.stage28b_retired_resident_typed_cut_dev import capture_retired_resident_typed_world
from relay_self.world_resident_lifecycle_dev import WorldLifetime, WorldResidentLifecycle


def _record(path: Path, record: dict) -> None:
    _write_bytes_new(path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())


async def generate_checkpoint(args: argparse.Namespace) -> Path:
    if not args.real_world_dev_grant:
        raise ValueError("explicit isolated World grant required")
    _verify_local_runtime(args.java, args.node)
    assets = check_stage24g_pinned_assets(
        paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
        scratch_parent=args.scratch_parent, accepted_eula=args.eula_accepted,
    )
    root = Path(tempfile.mkdtemp(prefix="u24-original-b-", dir=assets.scratch_parent))
    print(f"U24_ROOT={root}", flush=True)
    evidence = root / "evidence"
    evidence.mkdir()
    store = evidence / "generations"
    store.mkdir()
    plugins = root / "plugins"
    plugins.mkdir()
    shutil.copyfile(assets.paper_jar, root / "paper.jar")
    shutil.copyfile(assets.plugin_jar, plugins / "P0BRecorder.jar")
    if (file_sha256(root / "paper.jar"), file_sha256(plugins / "P0BRecorder.jar")) != (
        assets.paper_sha256, assets.plugin_sha256,
    ):
        raise ValueError("copied Paper assets differ from pins")
    _write_bytes_new(root / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(root / "server.properties", two_native_server_properties(port).encode())
    command = (
        args.java, "-Xms512M", "-Xmx1536M", "-jar", str(root / "paper.jar"), "--nogui",
    )

    report = {"status": "PRE_WORLD_HOLD", "paper_bootstrap_attempted": False,
              "owned_paper_started": False, "native_b_launched": False,
              "model_posts": 0, "physical_actions": 0}
    paper = None
    native = None
    physical = PhysicalIssueAdmission(
        {"B": "offline-born-B"}, resident_mode=True, initially_offline=True,
        allow_resident_move=False,
    )
    try:
        folder = root / "self-B"
        folder.mkdir()
        files = CognitiveOwnerFiles(folder, folder / "cognition.json", folder / "physical-wal.json")
        PhysicalActionJournal.create(files.physical_wal_file, self_id="B")
        config = SchemaBootstrapConfig(exploration_enabled=True, destination_move=True)
        owner = create_fresh_owner(
            config=config, retained=PersistentCognition(IdentitySpecification(
                "B", ("World-independent retained identity",), Provenance("u24-original", "B"),
            )),
            intent=IntentCommitment(), native_session_id="offline-born-B",
            last_observed_tick=0, files=files, physical_supervisor=ActionSupervisor(),
        )
        work = ResidentCognitiveWorkOwner({"B": owner})
        bootstrap_fresh_schemas(work, config)

        report["paper_bootstrap_attempted"] = True
        bootstrap = await asyncio.to_thread(
            _bootstrap_paper, world_root=root, launch=command, timeout_s=90.0,
        )
        report["paper_bootstrap_log"] = str(bootstrap)
        world_id = _world_uuid(root / "world")

        def read_log(session_id: str) -> bytes:
            return paper.read_owned_log(session_id)

        tick_reader = PaperMainThreadTickReader(
            spool_dir=plugins / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_id, read_owned_log=read_log,
            timeout_seconds=15.0, allow_repeated_same_boot=True,
        )
        branch = "u24-original-b"
        paper = OwnedPaperWorld(
            server_dir=root, world_dir=root / "world", evidence_dir=evidence,
            command=command, world_id=world_id, branch_id=branch,
            tick_readback=tick_reader, timeout_seconds=90.0,
        )
        paper_session = await asyncio.to_thread(paper.start_owned)
        report["owned_paper_started"] = True
        lifecycle = WorldResidentLifecycle(
            world=WorldLifetime(world_id, branch, paper_session, 0, 0),
            persisted_self_refs={"B": "boot-original-cognition:B"},
        )

        async def launch(config: MineflayerLaunchConfig) -> MineflayerProcessSession:
            nonlocal native
            native = await MineflayerProcessSession.launch(
                config, node_executable=args.node, startup_timeout_s=30.0,
            )
            report["native_b_launched"] = True
            native.start_raw_source_audit(evidence / "B-native-stdout.jsonl")
            native.start_raw_stdin_audit(evidence / "B-native-stdin.jsonl")
            return native

        bridge = OwnedResidentPhysicalBridge(
            lifecycle=lifecycle, physical=physical, paper=paper, owners={"B": owner},
            configs={"B": MineflayerLaunchConfig(
                host="127.0.0.1", port=port, username="RelayB", version="1.21.8",
            )},
            launch=launch, cognitive_work=work, adopt_login_worldbody_dev=True,
            probe_timeout_s=30.0,
        )
        await bridge.login("B")
        definition = next(d for d in initial_skill_definitions() if d.skill_id == "MOVE")
        proposal = SkillParameterPreset(
            initial_move_pattern().pattern_id, "Walk", 1, definition.definition_ref,
            SkillConstraints(), SkillBudget(1, 1500, 2.0, 4),
            Provenance("u24-preset-proposal", "initial-exploration"),
        )
        decision = work.decide_initial_move_preset(proposal)
        _record(evidence / "B-owner-preset-acceptance.json", {
            "receipt": asdict(decision), "scope": list(work.current_scope("B")),
            "login": asdict(bridge.last_login_evidence["B"]),
            "registry_revision": owner.pattern_registry.revision,
        })
        logout = await bridge.logout("B")
        _record(evidence / "B-logout.json", asdict(logout))
        cut = capture_retired_resident_typed_world(
            bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
            expected_self_ids=("B",),
        )
        (saved,) = verify_typed_generation(cut.generation)
        restored = root / "restored"
        restore_generation(cut.generation, restored, restore_id=root.name)
        plan = stage28_inert_cognitive_recovery(
            cut.generation, restored, expected_self_ids=("B",),
            expected_source_world_id=world_id,
        )
        (candidate,) = plan.candidates
        (accepted,) = saved.pattern_registry.accepted_presets
        if (
            saved.self_id != "B" or saved.schema_snapshot is None
            or saved.schema_snapshot.get("exploratory").mode is not SchemaMode.FULL
            or accepted.receipt != decision or accepted.preset != proposal
            or saved.intent_events or saved.skill_executions
            or candidate.semantic.cut != saved
            or PhysicalActionJournal.read_snapshot(
                candidate.physical_wal_path, self_id="B", require_clear=True,
            )
        ):
            raise RuntimeError("new B typed generation or restore disagrees with original Owner")
        report.update(status="U24_TYPED_SOURCE_VERIFIED", generation=str(cut.generation),
                      restored=str(restored), world_id=world_id, roster=["B"])
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        physical.hold_for_operator()
        raise
    finally:
        try:
            if native is not None:
                try:
                    if native.process_returncode is None:
                        await asyncio.wait_for(native.terminate(), timeout=8.0)
                finally:
                    native.finish_raw_source_audit()
                    native.finish_raw_stdin_audit()
            if paper is not None and paper.owned_session_id is not None and not paper.held_uncertain:
                await asyncio.to_thread(paper.stop_and_save)
        except BaseException:
            report.update(status="PRE_WORLD_HOLD", cleanup_uncertain=True)
            raise
        finally:
            if paper is not None and paper.owned_session_id is not None:
                report.update(status="PRE_WORLD_HOLD", cleanup_uncertain=True)
            _record(evidence / "u24-result.json", report)
    return evidence / "u24-result.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("paper-jar", "plugin-jar", "scratch-parent"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    print(asyncio.run(generate_checkpoint(parser.parse_args())))


if __name__ == "__main__":
    main()
