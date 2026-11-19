"""Stage28c2b: one isolated *real* Paper + ORIGINAL recovered A/B observer.

This is an explicitly opt-in DEV entrypoint for LOCAL Codex, NOT a
GitHub Actions real-World trial. It uses the verified Stage28b original
and Stage28c1 restored fork, always creates a NEW executable copy,
never runs Gemma or sends an Action, and leaves original evidence alone.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.p0d_real_paper_smoke_dev import (
    _free_local_port,
    _world_uuid,
    _write_bytes_new,
    file_sha256,
)
from experiments.p0d_real_two_native_smoke_dev import (
    _verify_local_runtime,
    two_native_server_properties,
)
from experiments.stage24g_pinned_assets_launch_dev import (
    check_stage24g_pinned_assets,
)
from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)
from relay_self.stage28c2b_bounded_paper_presence_dev import (
    await_both_recovered_paper_present,
)
from relay_self.stage28c2b_execution_copy_dev import (
    create_execution_copy,
)
from relay_self.stage28c2b_fork_paper_epoch_dev import (
    observe_new_fork_paper_epoch,
)
from relay_self.stage28c2b_historical_native_sessions_dev import (
    inspect_original_stage28b_native_sessions,
)
from relay_self.stage28c2b_native_paper_body_link_dev import (
    link_recovered_a_b_native_paper_body,
)
from relay_self.world_resident_lifecycle_dev import (
    WorldResidentLifecycle,
)


class Stage28c2bRealRejoinHold(RuntimeError):
    """The first restored original A/B real Paper trial is not attested."""


_STAGE28B_EVIDENCE_SHA = (
    "7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4"
)
_SOURCE_WORLD = "f9221410-b99e-417d-98f4-e98938586472"
_SOURCE_BRANCH = "p0d-real-resident-presence"
_SOURCE_COMMITTED_SHA = (
    "d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee"
)
_FORK_BRANCH = "fork-3883122c-6edb-4017-bd82-00fc4324aded"


async def _cleanup_native(session, report: dict[str, object]) -> None:
    """Retire only an owned child and never hide an incomplete raw transcript."""
    if session.process_returncode is None:
        try:
            await asyncio.wait_for(session.terminate(), 8.0)
        except BaseException:
            report["cleanup_uncertain"] = True
    if session.process_returncode is None:
        report["cleanup_uncertain"] = True
    try:
        if not session._raw_source_audit_finished:
            session.finish_raw_source_audit()
    except BaseException:
        report["raw_source_audit_uncertain"] = True


def inspect_real_recovered_sources(
    generation: Path, restored: Path, evidence28b: Path,
):
    """No World launch or filesystem mutation; source pins cannot be guessed."""
    from relay_self.stage28c2_recovered_resident_owner_dev import (
        prepare_recovered_a_b_resident_owners,
    )

    history = inspect_original_stage28b_native_sessions(
        evidence28b, generation,
        expected_manifest_sha256=_STAGE28B_EVIDENCE_SHA,
    )
    state = prepare_recovered_a_b_resident_owners(
        generation, restored, expected_world_id=_SOURCE_WORLD,
        expected_source_branch_id=_SOURCE_BRANCH,
        expected_committed_sha256=_SOURCE_COMMITTED_SHA,
        expected_fork_branch_id=_FORK_BRANCH,
        observation_only=True,
    )
    if (
        not state.physical.all_residents_offline
        or not state.physical.observation_only
        or state.plan.roster != ("A", "B")
        or not set(dict(state.plan.old_native_sessions).values()).issubset(
            history.historical_native_sessions
        )
    ):
        raise Stage28c2bRealRejoinHold("Stage28b/28c1 original Self source incomplete")
    return history, state


async def run_restored_a_b_real_observation(
    *, generation: Path, restored: Path, stage28b_evidence: Path,
    execution_dir: Path, evidence_dir: Path, paper_jar: Path,
    plugin_jar: Path, java: str, node: str,
    timeout_s: float = 120, presence_timeout_s: float = 12.0,
    on_reconnected: Callable[..., Awaitable[None]] | None = None,
) -> Path:
    """One real Paper/native A/B trial, no auto retries; no model by default.

    Any failure is HOLD; never silently start a second new World. First
    validate source/pins/assets on disk, then create one new executable copy.
    """
    if (
        type(timeout_s) not in (int, float)
        or not math.isfinite(timeout_s) or not 30 <= timeout_s <= 180
        or type(presence_timeout_s) not in (int, float)
        or not math.isfinite(presence_timeout_s)
        or not 1 <= presence_timeout_s <= 30
        or presence_timeout_s > timeout_s / 2
    ):
        raise Stage28c2bRealRejoinHold("bounded real-run/presence timeout required")
    _verify_local_runtime(java, node)
    history, source = inspect_real_recovered_sources(
        generation, restored, stage28b_evidence,
    )
    if not (
        source.receipt.source_committed_sha256 == _SOURCE_COMMITTED_SHA
        and source.receipt.fork_branch_id == _FORK_BRANCH
    ):
        raise Stage28c2bRealRejoinHold("original historical Self receipt mismatched")
    # Refuse even equivalent nested/overlapping paths for mutable execution.
    roots = [Path(x).resolve(strict=True) for x in (
        generation, restored, stage28b_evidence,
    )]
    dest, evidence = Path(execution_dir).absolute(), Path(evidence_dir).absolute()
    if (
        dest.exists() or dest.is_symlink()
        or evidence.exists() or evidence.is_symlink()
        or not dest.parent.is_dir() or not evidence.parent.is_dir()
        or dest == evidence or dest in evidence.parents or evidence in dest.parents
        or any(
            root == dest or root in dest.parents or dest in root.parents
            or root == evidence or root in evidence.parents or evidence in root.parents
            for root in roots
        )
    ):
        raise Stage28c2bRealRejoinHold("new isolated execution/evidence roots required")

    prepared = create_execution_copy(
        generation, restored, dest,
        expected_world_id=_SOURCE_WORLD,
        expected_source_branch_id=_SOURCE_BRANCH,
        expected_committed_sha256=_SOURCE_COMMITTED_SHA,
        expected_fork_branch_id=_FORK_BRANCH,
    )
    if _world_uuid(dest / "world") != _SOURCE_WORLD:
        raise Stage28c2bRealRejoinHold("copied World UUID is not original restored World")
    evidence.mkdir(mode=0o700)
    _write_bytes_new(
        evidence / "execution-copy-prestart-SHA256SUMS",
        "".join(f"{digest}  {name}\n" for name, digest in prepared.files).encode(),
    )
    checked = check_stage24g_pinned_assets(
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        scratch_parent=dest.parent, accepted_eula=True,
    )
    plugin_dir = dest / "plugins"
    plugin_dir.mkdir(mode=0o700)
    shutil.copyfile(checked.paper_jar, dest / "paper.jar")
    shutil.copyfile(checked.plugin_jar, plugin_dir / "P0BRecorder.jar")
    _write_bytes_new(dest / "eula.txt", b"eula=true\n")
    port = _free_local_port()
    _write_bytes_new(
        dest / "server.properties",
        two_native_server_properties(port).encode(),
    )

    holder: dict[str, OwnedPaperWorld] = {}
    reader: PaperMainThreadTickReader | None = None

    def tick_readback(owned_paper_session: str):
        nonlocal reader
        if reader is None:
            reader = PaperMainThreadTickReader(
                spool_dir=plugin_dir / "P0BRecorder" / "p0d-ticks",
                expected_world_uuid=_SOURCE_WORLD,
                read_owned_log=lambda sess: holder["paper"].read_owned_log(sess),
                timeout_seconds=min(timeout_s / 3, 15.0),
                allow_repeated_same_boot=True,
            )
        return reader(owned_paper_session)

    paper = OwnedPaperWorld(
        server_dir=dest, world_dir=dest / "world", evidence_dir=evidence,
        command=(java, "-Xms512M", "-Xmx1536M", "-jar", str(dest / "paper.jar"),
                 "--nogui"),
        world_id=_SOURCE_WORLD, branch_id=_FORK_BRANCH,
        tick_readback=tick_readback, timeout_seconds=timeout_s,
    )
    holder["paper"] = paper
    native_sessions = []
    raw_paths: dict[str, Path] = {}
    bridge: OwnedResidentPhysicalBridge | None = None
    physical = prepared.recovered.physical
    report: dict[str, object] = {
        "classification": "REAL_REJOIN_HOLD",
        "schema": 1,
        "original_generation": prepared.recovered.plan.generation_id,
        "original_world_uuid": _SOURCE_WORLD,
        "original_committed_sha256": _SOURCE_COMMITTED_SHA,
        "fork_branch_id": _FORK_BRANCH,
        "original_history": asdict(history),
        "paper_jar_sha256": checked.paper_sha256,
        "plugin_jar_sha256": checked.plugin_sha256,
        "real_world_trials": 1,
        "real_gemma_post": 0,
        "real_action_issued": 0,
        "real_peer_sent": 0,
        "physical_action_issue_authorized": False,
        "fresh_l1_run": False,
        "independent_audit_pass": False,
    }
    report_path = evidence / "stage28c2b-recovered-world-result.json"

    async def spawn_native(config: MineflayerLaunchConfig):
        session = await MineflayerProcessSession.launch(
            config, node_executable=node,
            startup_timeout_s=min(timeout_s / 3, 30.0),
        )
        # Register ownership before any further operation can fail.
        native_sessions.append(session)
        # This records the original raw stdout consumed by the existing
        # guarded bridge.login() spawn/probe path. No new native issuer.
        raw_path = evidence / (
            "native-" + config.username + "-" + session.started.session_id + ".jsonl"
        )
        session.start_raw_source_audit(raw_path)
        raw_paths[config.username] = raw_path
        return session

    try:
        paper_session = paper.start_owned()
        world, boot = observe_new_fork_paper_epoch(
            prepared, paper,
            historical_native_sessions=history.historical_native_sessions,
        )
        report["paper_session_id"] = paper_session
        report["paper_boot"] = asdict(boot)
        report["paper_pid"] = boot.paper_pid
        life = WorldResidentLifecycle(
            world=world,
            persisted_self_refs={
                sid: "source-verified:" + str(owner.files.cognition_file)
                for sid, owner in prepared.recovered.owners.items()
            },
            independent_native_world_clock=True,
        )
        configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=port,
                username="Relay" + sid, version="1.21.8",
            ) for sid in ("A", "B")
        }
        bridge = OwnedResidentPhysicalBridge(
            lifecycle=life, physical=physical, paper=paper,
            configs=configs, owners=prepared.recovered.owners,
            cognitive_work=prepared.recovered.cognitive_work,
            inference_lane=None, launch=spawn_native,
            forbidden_native_sessions=frozenset(
                history.historical_native_sessions
            ),
            probe_timeout_s=min(timeout_s / 3, 30.0),
        )
        await bridge.login("A")
        await bridge.login("B")
        # Do NOT guess B PRESENT after a fixed 1.5s. Paper witnesses
        # stationary presence only after >=40 Bukkit ticks per native JOIN.
        # Await BOTH original actors; any missing/foreign/retired one is HOLD.
        ready = await await_both_recovered_paper_present(
            bridge=bridge, paper=paper, boot=boot,
            timeout_seconds=presence_timeout_s,
        )
        report["bounded_paper_presence"] = asdict(ready)
        current, linked = link_recovered_a_b_native_paper_body(
            bridge=bridge, paper=paper, boot=boot,
            forbidden_native_sessions=frozenset(
                history.historical_native_sessions
            ),
        )
        for link in linked:
            owner = prepared.recovered.owners[link.self_id]
            observation = bridge.last_login_observations[link.self_id]
            owner.accept_rejoined_worldbody(observation, request_id=link.native_probe_ref)
            if owner.current_worldbody_observation is not observation:
                raise Stage28c2bRealRejoinHold("original owner did not accept native WorldBody")
        report["owner_worldbody_observations"] = {
            sid: asdict(prepared.recovered.owners[sid].current_worldbody_observation)
            for sid in ("A", "B")
        }
        report["new_world_process_tick"] = current.world_tick
        report["fresh_body_links"] = [asdict(link) for link in linked]
        report["native_login_evidence"] = {
            sid: asdict(bridge.last_login_evidence[sid])
            for sid in ("A", "B")
        }
        report["new_native_pids"] = {
            sid: bridge.sessions[sid].owned_child_pid for sid in ("A", "B")
        }
        # Read-only observation succeeds only if the *same original*
        # recovered Owners were promoted by the actual original bridge.
        for sid in ("A", "B"):
            owner = prepared.recovered.owners[sid]
            if (
                owner.retained.identity.self_id != sid
                or owner.fresh_native_observation_required
                or owner.cohort is not prepared.recovered.cognitive_work
                or owner.native_session_id
                != bridge.last_login_evidence[sid].native_session_id
                or owner.supervisor.open_actions
            ):
                raise Stage28c2bRealRejoinHold(
                    "original persisted cognition not connected to fresh WorldBody"
                )
            PhysicalActionJournal.restore(
                owner.files.physical_wal_file, self_id=sid,
            ).require_clear()
        if on_reconnected is not None:
            # Stage28c2c explicitly opts into an already verified original
            # A/B source-linked Body. Default Stage28c2b remains model-free.
            if not callable(on_reconnected):
                raise Stage28c2bRealRejoinHold("foreign reconnected cognition hook")
            await on_reconnected(
                prepared=prepared, bridge=bridge, boot=boot,
                world=current, links=linked, paper=paper,
                evidence=evidence, report=report,
            )
        report["retirement_A"] = asdict(await bridge.logout("A"))
        report["retirement_B"] = asdict(await bridge.logout("B"))
        await asyncio.sleep(0.5)
        # Independent Paper source observed both Self native QUITs after
        # the actual owned children were terminated, before saving World.
        log = paper.read_owned_log(paper_session)
        digest = hashlib.sha256(log).hexdigest()
        _write_bytes_new(evidence / "prestop-paper-resident-owned.log", log)
        trace = parse_owned_paper_resident_trace(
            owned_paper_session_id=paper_session,
            expected_world_uuid=_SOURCE_WORLD, owned_paper_log=log,
            log_ref="paper-owned-log:" + paper_session + ":sha256:" + digest,
        )
        for name in ("RelayA", "RelayB"):
            events = [x for x in trace.events if x.name == name]
            if (
                not events or events[0].event != "JOIN"
                or len([x for x in events if x.event == "QUIT"]) != 1
                or len([x for x in events if x.event == "JOIN"]) != 1
                or events[-1].event != "QUIT"
            ):
                raise Stage28c2bRealRejoinHold(
                    "original Paper JOIN/PRESENT/QUIT incomplete"
                )
        report["world_only_quiescence"] = asdict(bridge.world_only_quiescence())
        report["final_paper_resident_log_sha256"] = digest
        report["final_paper_resident_boot_id"] = trace.boot_id
        stopped = paper.stop_and_save()
        if stopped.process_exit_code != 0 or not stopped.all_dimensions_saved:
            raise Stage28c2bRealRejoinHold("owned Paper failed clean save/stop")
        report["paper_stopped"] = asdict(stopped)
        for native in native_sessions:
            native.finish_raw_source_audit()
        report["original_stage28b_reverified"] = (
            inspect_original_stage28b_native_sessions(
                stage28b_evidence, generation,
                expected_manifest_sha256=_STAGE28B_EVIDENCE_SHA,
            ) == history
        )
        if not report["original_stage28b_reverified"]:
            raise Stage28c2bRealRejoinHold("immutable Stage28b original changed")
        # An external verifier must inspect raw native/Paper evidence before
        # promotion to REAL_RESTORED_WORLD_ORIGINAL_A_B_NATIVE_REJOIN_WORLDBODY_DEV.
        report["raw_native_file_sha256"] = {
            name: file_sha256(path) for name, path in raw_paths.items()
        }
        report["classification"] = "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        physical.hold_for_operator()
        raise
    finally:
        for native in native_sessions:
            await _cleanup_native(native, report)
        if paper.owned_session_id is not None:
            if not paper.held_uncertain:
                try:
                    report["paper_cleanup_stopped"] = asdict(paper.stop_and_save())
                except BaseException:
                    report["cleanup_uncertain"] = True
            if paper.held_uncertain or report.get("cleanup_uncertain"):
                report["cleanup_uncertain"] = True
                # HOLD remains HOLD. Bound cleanup to the actual Popen owned by
                # this invocation, including failures before Paper readiness.
                process = paper._process
                if process is not None:
                    report["paper_cleanup_pid"] = process.pid
                    try:
                        if process.poll() is None:
                            process.terminate()
                            try:
                                process.wait(timeout=8)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=8)
                        report["paper_cleanup_exit_code"] = process.poll()
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        report["paper_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        if report.get("cleanup_uncertain") or report.get("raw_source_audit_uncertain"):
            report["classification"] = "REAL_REJOIN_HOLD"
        _write_bytes_new(
            report_path, (json.dumps(report, sort_keys=True, indent=2) + "\n").encode(),
        )
        print(f"STAGE28C2B_REAL_CAPTURE={report_path}", file=sys.stderr, flush=True)
    if report["classification"] != "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING":
        raise Stage28c2bRealRejoinHold("original real Paper native source unavailable")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--stage28b-evidence", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--presence-timeout-s", type=float, default=12.0)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inspect-only", action="store_true")
    modes.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if not args.eula_accepted:
            raise Stage28c2bRealRejoinHold("EULA consent required")
        if args.inspect_only and (
            args.real_world_dev_grant or args.execution_dir is not None
            or args.evidence_dir is not None
        ):
            raise Stage28c2bRealRejoinHold("inspect-only may not activate a World")
        if args.execute_once and (
            not args.real_world_dev_grant
            or args.execution_dir is None or args.evidence_dir is None
        ):
            raise Stage28c2bRealRejoinHold(
                "exact one World DEV grant and fresh execution/evidence paths required"
            )
        checked = check_stage24g_pinned_assets(
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=(
                args.execution_dir.parent if args.execution_dir
                else args.restored.parent
            ),
            accepted_eula=True,
        )
        _verify_local_runtime(args.java, args.node)
        history, original = inspect_real_recovered_sources(
            args.generation, args.restored, args.stage28b_evidence,
        )
        print(
            "STAGE28C2B_RESTORED_SOURCE_INSPECT_PASS "
            f"historical_native_count={len(history.historical_native_sessions)} "
            f"original_owner_count={len(original.owners)} "
            "world_started=false model_post=false",
            flush=True,
        )
        if args.inspect_only:
            return 0
        assert args.execution_dir is not None and args.evidence_dir is not None
        result = asyncio.run(run_restored_a_b_real_observation(
            generation=args.generation, restored=args.restored,
            stage28b_evidence=args.stage28b_evidence,
            execution_dir=args.execution_dir, evidence_dir=args.evidence_dir,
            paper_jar=checked.paper_jar, plugin_jar=checked.plugin_jar,
            java=args.java, node=args.node, timeout_s=args.timeout_s,
            presence_timeout_s=args.presence_timeout_s,
        ))
        print(f"STAGE28C2B_CAPTURED_UNAUDITED={result}", flush=True)
        return 0
    except BaseException as exc:
        print(f"STAGE28C2B_HOLD={type(exc).__name__}:{exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
