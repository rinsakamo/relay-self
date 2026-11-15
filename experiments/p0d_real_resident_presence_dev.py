"""#860 Stage22: operator-gated REAL Paper + two resident Self body presence.

Limited to native login/logout, source-correlated B observation and World
continuity. Does NOT issue MOVE/EAT/ATTACK, use GPU, attach to an existing
server, or assert B caused a physical Action. The original Stage19 physical
issuer explicitly denies control effects until a proper MOVE/WAL owner exists.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from experiments.p0d_real_paper_smoke_dev import (
    _bootstrap_paper,
    _free_local_port,
    _world_uuid,
    _write_bytes_new,
    file_sha256,
)
from experiments.p0d_real_two_native_smoke_dev import (
    preflight_two_native,
    two_native_server_properties,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_paper_presence_join_dev import (
    join_resident_paper_presence,
    parse_owned_paper_resident_trace,
)
from relay_self.world_only_owned_checkpoint_dev import (
    WorldOnlyOwnedPaperCheckpoint,
    verify_world_only_generation,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldLifetime,
    WorldResidentLifecycle,
)


class RealResidentPresenceRefusal(RuntimeError):
    """Real Paper observation or explicit operator/owner evidence not qualified."""


async def _bounded_b_probe(
    native: MineflayerProcessSession, *, timeout_s: float = 12.0,
) -> MineflayerObservation:
    """Native B sensor source after A logout; not a physical Action issuer."""
    native_id = native.started.session_id
    request_id = "p0d-b-online-" + uuid.uuid4().hex
    await native.send_observe(request_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    for _ in range(256):
        left = deadline - loop.time()
        if left <= 0:
            break
        try:
            item = await asyncio.wait_for(native.receive(), left)
        except TimeoutError as exc:
            raise RealResidentPresenceRefusal("B native probe timeout") from exc
        if item.session_id != native_id or isinstance(
            item, (
                MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                MineflayerCommandError,
            ),
        ):
            raise RealResidentPresenceRefusal("B native stream ended/foreign during A logout")
        if isinstance(item, MineflayerObservation) and item.kind == "probe":
            if (
                item.request_id != request_id
                or item.snapshot.health <= 0
                or item.snapshot.time is None
            ):
                raise RealResidentPresenceRefusal("B live native source mismatched")
            return item
    raise RealResidentPresenceRefusal("B requested probe not received")


async def _owned_resident_trial(
    *,
    paper: OwnedPaperWorld,
    bridge: OwnedResidentPhysicalBridge,
    physical: PhysicalIssueAdmission,
    lifecycle: WorldResidentLifecycle,
    world_uuid: str,
    evidence_dir: Path,
    b_heartbeat_s: float,
    world_only: bool,
) -> dict[str, object]:
    """One strictly bounded native body scenario. No model/Skill/Action issue."""
    if (
        paper.owned_session_id is None
        or not 2 <= b_heartbeat_s <= 12
        or bridge.lifecycle is not lifecycle
        or bridge.physical is not physical
        or tuple(sorted(bridge.owners)) != ("A", "B")
        or not physical.resident_mode
        or not physical.all_residents_offline
    ):
        raise RealResidentPresenceRefusal("two initial offline residents and owned Paper required")

    paper_session = paper.owned_session_id
    assert paper_session is not None
    original_a = await bridge.login("A")
    original_b = await bridge.login("B")
    old_a = bridge.sessions["A"].started.session_id
    original_b_native = bridge.sessions["B"].started.session_id
    # The passive Paper sampler emits a PRESENT heartbeat per player each
    # 40 Bukkit ticks. No native effect is sent to produce that heartbeat.
    await asyncio.sleep(float(b_heartbeat_s))
    a_logout = await bridge.logout("A")
    if a_logout.native_session_id != old_a:
        raise RealResidentPresenceRefusal("A native terminal source mismatch")
    await asyncio.sleep(float(b_heartbeat_s))
    b_probe = await _bounded_b_probe(bridge.sessions["B"])
    if (
        physical.current_native_sessions["B"] != original_b_native
        or bridge.sessions["B"].started.session_id != original_b_native
    ):
        raise RealResidentPresenceRefusal("B changed original native owner after A quit")
    a_relogin_ticket = await bridge.login("A")
    a_relogin = bridge.last_login_evidence["A"]
    if a_relogin.native_session_id == old_a:
        raise RealResidentPresenceRefusal("A reused native process")
    await asyncio.sleep(1.0)
    # This reads ONLY the explicitly owned Paper Popen stdout log.
    source = paper.read_owned_log(paper_session)
    import hashlib

    source_ref = (
        f"paper-owned-log:{paper_session}:sha256:"
        f"{hashlib.sha256(source).hexdigest()}"
    )
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session,
        expected_world_uuid=world_uuid,
        owned_paper_log=source, log_ref=source_ref,
    )
    result = join_resident_paper_presence(
        trace=trace, world=lifecycle.world,
        a_name="RelayA", b_name="RelayB",
        a_logout=a_logout, a_relogin=a_relogin,
        original_b_native=original_b_native,
        surviving_b_native=physical.current_native_sessions["B"],
    )
    # No B physical Action was issued: even a Paper MOVE source event cannot
    # be credited to an original WAL Action without a separate native ticket.
    result_data: dict[str, object] = {
        "classification": "REAL_PAPER_RESIDENT_PRESENCE_DEV",
        "paper_player_continuity": result.status.value,
        "independent_paper_source": result.paper_source_ref,
        "paper_boot": trace.boot_id,
        "world_uuid": world_uuid,
        "paper_session_id": paper_session,
        "a_original_ticket": asdict(original_a),
        "b_original_ticket": asdict(original_b),
        "a_original_native_session": old_a,
        "a_logout": asdict(a_logout),
        "a_relogin_ticket": asdict(a_relogin_ticket),
        "a_relogin_evidence": asdict(a_relogin),
        "b_original_native_session": original_b_native,
        "b_probe": {
            "session": b_probe.session_id,
            "seq": b_probe.seq,
            "request_id": b_probe.request_id,
            "provenance": b_probe.provenance.reference,
            "world_day": b_probe.snapshot.time.day if b_probe.snapshot.time else None,
            "time_of_day": (
                b_probe.snapshot.time.time_of_day if b_probe.snapshot.time else None
            ),
            "health": b_probe.snapshot.health,
            "x": b_probe.snapshot.position.x,
            "y": b_probe.snapshot.position.y,
            "z": b_probe.snapshot.position.z,
        },
        "b_actor_uuid": result.b_actor_uuid,
        "a_actor_uuid": result.a_actor_uuid,
        "a_paper_quit_tick": result.a_quit_tick,
        "b_paper_continuation_tick": result.b_later_tick,
        "a_paper_rejoin_tick": result.a_rejoin_tick,
        "b_paper_displacement_m": result.b_movement_m,
        "b_actual_physical_action": False,
        "b_physical_wal_outcome": False,
        "b_move_action_causality": False,
        "real_l1_l2_gpu_executed": False,
        "real_peer_transport_executed": False,
    }
    await bridge.logout("A")
    await bridge.logout("B")
    if not bridge.world_only_quiescence().no_unresolved_physical_actions:
        raise RealResidentPresenceRefusal("not all original issuer receipts retired")
    if world_only:
        store = evidence_dir / "world-only-generations"
        store.mkdir(mode=0o700)
        result_world = WorldOnlyOwnedPaperCheckpoint(
            lifecycle=lifecycle, owned_paper=paper, store=store,
            issuer_quiescence=bridge.world_only_quiescence,
        ).cycle()
        verify_world_only_generation(result_world.checkpoint_dir)
        result_data["world_only_generation"] = str(result_world.checkpoint_dir)
        result_data["world_only_new_session"] = (
            result_world.new_world.paper_session_id
        )
        result_data["world_only_new_epoch"] = result_world.new_world.epoch
    return result_data


async def run_real_resident_presence(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    real_world_dev_grant: bool,
    java: str = "java", node: str = "node",
    timeout_s: float = 120.0, heap_mb: int = 1536,
    b_heartbeat_s: float = 4.0, world_only: bool = False,
) -> Path:
    """One genuine Paper/Mineflayer scenario, no implicit EULA/DEV grants."""
    if real_world_dev_grant is not True:
        raise RealResidentPresenceRefusal(
            "HOLD_REAL_WORLD_GRANT: explicit real Paper/native DEV approval required"
        )
    if type(b_heartbeat_s) not in (int, float) or not 2 <= b_heartbeat_s <= 12:
        raise RealResidentPresenceRefusal("bounded Paper heartbeat delay required")
    paper_src, plugin_src, scratch = preflight_two_native(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
        java=java, node=node, timeout_s=timeout_s, heap_mb=heap_mb,
    )
    root = Path(tempfile.mkdtemp(prefix="p0d-resident-presence-", dir=scratch))
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
        root / "server.properties",
        two_native_server_properties(port).encode(),
    )
    launch_command = (
        java, "-Xms512M", f"-Xmx{heap_mb}M",
        "-jar", str(root / "paper.jar"), "--nogui",
    )
    report_path = evidence / "resident-presence-result.json"
    report: dict[str, object] = {
        "schema": 1,
        "classification": "HOLD",
        "real_world_permission": True,
        "paper_sha256": paper_sha256,
        "plugin_sha256": plugin_sha256,
        "scratch": str(root),
        "localhost_port": port,
        "real_b_physical_action": False,
        "real_gpu": False,
        "steps": [],
    }
    owner = None
    bridge = None
    physical = None
    try:
        bootstrap = _bootstrap_paper(
            world_root=root, launch=launch_command, timeout_s=timeout_s,
        )
        world_uuid = _world_uuid(root / "world")
        report["bootstrap_sha256"] = file_sha256(bootstrap)
        report["world_uuid"] = world_uuid
        holder: dict[str, OwnedPaperWorld] = {}
        tick = PaperMainThreadTickReader(
            spool_dir=plugins / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_uuid,
            read_owned_log=lambda sess: holder["paper"].read_owned_log(sess),
            timeout_seconds=min(15.0, timeout_s / 3),
        )
        owner = OwnedPaperWorld(
            server_dir=root, world_dir=root / "world",
            evidence_dir=evidence, command=launch_command,
            world_id=world_uuid, branch_id="p0d-real-resident-presence",
            tick_readback=tick, timeout_seconds=timeout_s,
        )
        holder["paper"] = owner
        paper_session = owner.start_owned()
        names = ("A", "B")
        initial_native = {sid: "offline-born-" + sid for sid in names}
        physical = PhysicalIssueAdmission(
            initial_native, resident_mode=True, initially_offline=True,
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
                        sid, ("World-independent retained identity",),
                        Provenance("p0d-real-resident", sid),
                    )
                ),
                intent=IntentCommitment(),
                pattern_registry=initial_patterns(),
                native_session_id=initial_native[sid],
                last_observed_tick=0,
                files=CognitiveOwnerFiles(
                    folder, folder / "cognition.json", wal,
                ),
                physical_supervisor=ActionSupervisor(),
            )
        cognition = ResidentCognitiveWorkOwner(originals)
        lifecycle = WorldResidentLifecycle(
            world=WorldLifetime(
                world_uuid, "p0d-real-resident-presence", paper_session, 0, 0,
            ),
            persisted_self_refs={
                sid: f"boot-original-cognition:{sid}" for sid in names
            },
        )

        async def native_factory(config: MineflayerLaunchConfig):
            return await MineflayerProcessSession.launch(
                config, node_executable=node,
                startup_timeout_s=min(30.0, timeout_s / 3),
            )

        bridge = OwnedResidentPhysicalBridge(
            lifecycle=lifecycle, physical=physical, paper=owner,
            configs=configs, owners=originals,
            launch=native_factory, cognitive_work=cognition,
            probe_timeout_s=min(30.0, timeout_s / 3),
        )
        report["steps"] = [await _owned_resident_trial(
            paper=owner, bridge=bridge, physical=physical,
            lifecycle=lifecycle, world_uuid=world_uuid,
            evidence_dir=evidence,
            b_heartbeat_s=b_heartbeat_s, world_only=world_only,
        )]
        report["classification"] = (
            "REAL_PAPER_RESIDENT_PRESENCE_AND_WORLD_ONLY_DEV"
            if world_only else "REAL_PAPER_RESIDENT_PRESENCE_DEV"
        )
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        if physical is not None:
            physical.hold_for_operator()
        raise
    finally:
        if bridge is not None:
            for session in {id(s): s for s in bridge.sessions.values()}.values():
                try:
                    if session.process_returncode is None:
                        await asyncio.wait_for(session.terminate(), timeout=8.0)
                except BaseException:
                    report["cleanup_uncertain"] = True
                    report["classification"] = "HOLD"
        if owner is not None and owner.owned_session_id is not None and not owner.held_uncertain:
            try:
                owner.stop_and_save()
            except BaseException:
                report["cleanup_uncertain"] = True
                report["classification"] = "HOLD"
        _write_bytes_new(
            report_path, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
        )
        print(f"P0D_RESIDENT_REAL_AUDIT={report_path}", file=sys.stderr, flush=True)
        if owner is not None and owner.owned_session_id is not None:
            print(
                "P0D_HOLD: owned disposable Paper may still run; inspect"
                " this exact PID/source, no blind kill/retry.",
                file=sys.stderr, flush=True,
            )
    if report["classification"] not in (
        "REAL_PAPER_RESIDENT_PRESENCE_DEV",
        "REAL_PAPER_RESIDENT_PRESENCE_AND_WORLD_ONLY_DEV",
    ):
        raise RealResidentPresenceRefusal("resident Paper evidence unqualified")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--heap-mb", type=int, default=1536)
    parser.add_argument("--b-heartbeat-s", type=float, default=4.0)
    parser.add_argument("--world-only", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(run_real_resident_presence(
            paper_jar=args.paper_jar, paper_sha256=args.paper_sha256,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            scratch_parent=args.scratch_parent, accepted_eula=args.eula_accepted,
            real_world_dev_grant=args.real_world_dev_grant,
            java=args.java, node=args.node,
            timeout_s=args.timeout_s, heap_mb=args.heap_mb,
            b_heartbeat_s=args.b_heartbeat_s, world_only=args.world_only,
        ))
    except Exception as exc:
        print(f"P0D_RESIDENT_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    print(f"P0D_RESIDENT_REAL_RESULT={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
