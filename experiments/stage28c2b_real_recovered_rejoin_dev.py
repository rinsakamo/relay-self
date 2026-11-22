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
from relay_self.i_lane_i2c_original_schema_restore_dev import (
    bootstrap_original_recorded_a_b_schemas,
)
from relay_self.i_lane_i2f_future_source_pins_dev import (
    I2fFutureSourcePins,
    inspect_i2f_future_original_sources,
    verify_i2f_original_source_unchanged,
)
from relay_self.i_lane_i1_native_preflight_dev import (
    require_i1_native_preflight,
)
from relay_self.i_lane_i1_normal_runtime_dev import (
    install_i1_original_schema_bootstrap,
    prepare_i1_original_schema_bootstrap,
    sample_i1_original_cpu_epochs,
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


def freeze_i1_bd1b_hold_readback(
    *, exception: BaseException, evidence: Path, report: dict[str, object],
) -> bool:
    """Freeze exactly the original BD1b failed read, not a later Paper reread.

    Failure evidence only: it never affects original-owner source validation,
    independent audit, World lifecycle or success classification. The original
    BD1b reader remains read-only and attaches its actual read bytes to HOLD.
    """
    cause = exception
    for _ in range(5):
        raw = getattr(cause, "i1_original_paper_readback", None)
        facts = getattr(cause, "i1_source_debug", None)
        if type(raw) is bytes and type(facts) is dict:
            digest = hashlib.sha256(raw).hexdigest()
            if (len(raw) > 64 * 1024 * 1024
                    or facts.get("raw_sha256") != digest
                    or facts.get("raw_size") != len(raw)):
                report["i1_bd1b_failure_capture_uncertain"] = True
                return False
            name = "i1-bd1b-failure-time-owned-paper-readback.log"
            try:
                _write_bytes_new(evidence / name, raw)
                report["i1_bd1b_failure_readback"] = {
                    **facts,
                    "filename": name,
                    "sha256": digest,
                    "bytes": len(raw),
                    "diagnostic_only": True,
                    "independent_audit_pass": False,
                }
                return True
            except (OSError, ValueError) as capture_error:
                report["i1_bd1b_failure_capture_error"] = (
                    f"{type(capture_error).__name__}: {capture_error}"
                )
                return False
        next_cause = cause.__cause__
        if next_cause is None or next_cause is cause:
            break
        cause = next_cause
    return False


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
    # A failed I1 observation may have already drained bytes into the
    # original Native child. Preserve its outbound transcript too: never
    # convert an incomplete command journal into a successful capture.
    if getattr(session, "_raw_command_audit_fd", None) is not None:
        try:
            session.finish_raw_command_audit()
        except BaseException:
            report["raw_source_audit_uncertain"] = True


def inspect_real_recovered_sources(
    generation: Path, restored: Path, evidence28b: Path,
    *, future_pins: I2fFutureSourcePins | None = None,
):
    """No World launch or filesystem mutation; source pins cannot be guessed."""
    from relay_self.stage28c2_recovered_resident_owner_dev import (
        prepare_recovered_a_b_resident_owners,
    )

    if future_pins is not None:
        qualified, prepared = inspect_i2f_future_original_sources(
            generation=generation, restored=restored,
            original_evidence=evidence28b, pins=future_pins,
        )
        return qualified, prepared.restored
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


def require_stage28_capture_classification(
    report: dict, *, i1_original_cpu_sense: bool,
    future_pins: I2fFutureSourcePins | None = None,
) -> None:
    """Distinct original Stage28 and new I1 pending-audit statuses."""
    expected_classification = (
        "I2F_FUTURE_V3_ORIGINAL_A_B_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        if future_pins is not None else
        "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        if i1_original_cpu_sense
        else "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
    )
    if (type(i1_original_cpu_sense) is not bool
            or report.get("classification") != expected_classification
            or (future_pins is not None and (
                report.get("i2f_future_source") is not True
                or report.get("i2f_dual_model_completed") is not True
                or report.get("real_gemma_post") != 2
                or report.get("model_post_attempted") != 2
                or report.get("real_action_issued") != 0
                or report.get("physical_action_issue_authorized") is not False
            ))
            or report.get("i1_original_cpu_sense_enabled") is not i1_original_cpu_sense
            or (i1_original_cpu_sense and (
                report.get("i1_normal_continuous_native_observed") is not True
                or type(report.get("i1_cpu_epochs")) is not dict
            ))):
        raise Stage28c2bRealRejoinHold("original Paper/native/I1 capture incomplete")


async def run_restored_a_b_real_observation(
    *, generation: Path, restored: Path, stage28b_evidence: Path,
    execution_dir: Path, evidence_dir: Path, paper_jar: Path,
    plugin_jar: Path, java: str, node: str,
    timeout_s: float = 120, presence_timeout_s: float = 12.0,
    on_reconnected: Callable[..., Awaitable[None]] | None = None,
    i1_original_cpu_sense: bool = False,
    future_pins: I2fFutureSourcePins | None = None,
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
        or type(i1_original_cpu_sense) is not bool
        or (i1_original_cpu_sense and on_reconnected is not None
            and future_pins is None)
        or (future_pins is not None and (
            not isinstance(future_pins, I2fFutureSourcePins)
            or not i1_original_cpu_sense
            or not callable(on_reconnected)
        ))
    ):
        raise Stage28c2bRealRejoinHold("bounded real-run/presence timeout required")
    _verify_local_runtime(java, node)
    # The original Mineflayer Node process refuses symlink ancestors even
    # when Python's older package.json path check passed. This must be
    # enforced before copying a World, creating a real Paper child or any
    # Native process. The check itself starts only the read-only Node inspector.
    preflight = (
        require_i1_native_preflight(node=node)
        if i1_original_cpu_sense else None
    )
    history, source = inspect_real_recovered_sources(
        generation, restored, stage28b_evidence,
        future_pins=future_pins,
    )
    if not (
        source.receipt.source_committed_sha256 == _SOURCE_COMMITTED_SHA
        and source.receipt.fork_branch_id == _FORK_BRANCH
    ):
        raise Stage28c2bRealRejoinHold("original historical Self receipt mismatched")
    if i1_original_cpu_sense and future_pins is None:
        # Fail pre-copy/pre-World if the original restored registry cannot
        # be reconfigured without inventing a new Pattern or capability.
        prepare_i1_original_schema_bootstrap(source.cognitive_work)
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

    source_world = (_SOURCE_WORLD if future_pins is None else future_pins.source_world_id)
    source_branch = (_SOURCE_BRANCH if future_pins is None else future_pins.source_branch_id)
    source_commit = (_SOURCE_COMMITTED_SHA if future_pins is None
                     else future_pins.source_committed_sha256)
    fork_branch = (_FORK_BRANCH if future_pins is None else future_pins.fork_branch_id)
    prepared = create_execution_copy(
        generation, restored, dest,
        expected_world_id=source_world,
        expected_source_branch_id=source_branch,
        expected_committed_sha256=source_commit,
        expected_fork_branch_id=fork_branch,
    )
    if i1_original_cpu_sense and future_pins is None:
        install_i1_original_schema_bootstrap(prepared.recovered.cognitive_work)
    if future_pins is not None:
        bootstrap_original_recorded_a_b_schemas(
            recovered=prepared.recovered,
            generation=generation,
            restored_directory=dest,
        )
    if _world_uuid(dest / "world") != source_world:
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
                expected_world_uuid=source_world,
                read_owned_log=lambda sess: holder["paper"].read_owned_log(sess),
                timeout_seconds=min(timeout_s / 3, 15.0),
                allow_repeated_same_boot=True,
            )
        return reader(owned_paper_session)

    paper = OwnedPaperWorld(
        server_dir=dest, world_dir=dest / "world", evidence_dir=evidence,
        command=(java, "-Xms512M", "-Xmx1536M", "-jar", str(dest / "paper.jar"),
                 "--nogui"),
        world_id=source_world, branch_id=fork_branch,
        tick_readback=tick_readback, timeout_seconds=timeout_s,
    )
    holder["paper"] = paper
    native_sessions = []
    raw_paths: dict[str, Path] = {}
    command_paths: dict[str, Path] = {}
    bridge: OwnedResidentPhysicalBridge | None = None
    physical = prepared.recovered.physical
    report: dict[str, object] = {
        "classification": "REAL_REJOIN_HOLD",
        "schema": 1,
        "original_generation": prepared.recovered.plan.generation_id,
        "original_world_uuid": source_world,
        "original_committed_sha256": source_commit,
        "fork_branch_id": fork_branch,
        "i2f_future_source": future_pins is not None,
        "i2f_dual_model_completed": False,
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
        "i1_original_cpu_sense_enabled": i1_original_cpu_sense,
        "i1_normal_continuous_native_observed": False,
        **({"i1_native_preflight": asdict(preflight)}
           if preflight is not None else {}),
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
        if i1_original_cpu_sense:
            command_path = evidence / (
                "native-commands-" + config.username + "-" +
                session.started.session_id + ".jsonl"
            )
            session.start_raw_command_audit(command_path)
            command_paths[config.username] = command_path
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
            enable_sense=i1_original_cpu_sense,
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
            i1_require_complete_paper_prefix=i1_original_cpu_sense,
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
        if i1_original_cpu_sense:
            # Same original A/B dispatcher/owner; two distinct read-only
            # native observations and independently refreshed Paper receipts.
            # No GPU, Goal/Intent admission, Physical Action or Memory write.
            async def refresh_original_native():
                # Preserve the exact matched Native reply per Self from the
                # original session; an intervening passive move/entities
                # notification must never satisfy the I1 CPU correlation.
                observed = {}
                for sid in ("A", "B"):
                    observed[sid] = await bridge.refresh_i1_read_only_sense(
                        sid, timeout_s=2.0,
                    )
                return observed

            def refresh_original_paper():
                return link_recovered_a_b_native_paper_body(
                    bridge=bridge, paper=paper, boot=boot,
                    forbidden_native_sessions=frozenset(
                        history.historical_native_sessions
                    ),
                    i1_require_complete_paper_prefix=True,
                )

            observed = await sample_i1_original_cpu_epochs(
                bridge=bridge, boot=boot, world=current, links=linked,
                refresh_native_source=refresh_original_native,
                refresh_paper_source=refresh_original_paper, timeout_s=8.0,
            )
            report["i1_cpu_epochs"] = asdict(observed)
            report["i1_normal_continuous_native_observed"] = (
                observed.continuous_native_updates_observed
            )
            if (not observed.continuous_native_updates_observed
                    or observed.model_invoked or observed.action_issue_authorized
                    or any(count != 2 for _, count in observed.per_self_counts)):
                raise Stage28c2bRealRejoinHold(
                    "normal I1 A/B repeated Native/CPU epochs incomplete"
                )
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
            expected_world_uuid=source_world, owned_paper_log=log,
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
            if i1_original_cpu_sense:
                native.finish_raw_command_audit()
        if future_pins is not None:
            verify_i2f_original_source_unchanged(
                generation=generation, original_evidence=stage28b_evidence,
                pins=future_pins,
            )
            report["original_stage28b_reverified"] = True
        else:
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
        if i1_original_cpu_sense:
            if set(command_paths) != {"RelayA", "RelayB"}:
                raise Stage28c2bRealRejoinHold(
                    "original A/B Native command transcript incomplete"
                )
            report["raw_native_command_file_sha256"] = {
                name: file_sha256(path) for name, path in command_paths.items()
            }
        report["classification"] = (
            "I2F_FUTURE_V3_ORIGINAL_A_B_CAPTURED_INDEPENDENT_AUDIT_PENDING"
            if future_pins is not None else
            "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING"
            if i1_original_cpu_sense
            else "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        )
    except BaseException as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        if i1_original_cpu_sense:
            correlation = getattr(exc, "i1_correlated_cpu_readback", None)
            if type(correlation) is dict:
                report["i1_native_cpu_correlation_hold"] = correlation
            # Original read bytes are retained ONLY on an I1 BD1b failure.
            # Never reread a changing Paper log after an exception and pretend
            # the new bytes prove the exact earlier mismatch.
            freeze_i1_bd1b_hold_readback(
                exception=exc, evidence=evidence, report=report,
            )
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
    require_stage28_capture_classification(
        report, i1_original_cpu_sense=i1_original_cpu_sense,
        future_pins=future_pins,
    )
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
    parser.add_argument("--i1-original-cpu-sense", action="store_true")
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
        if args.i1_original_cpu_sense:
            native_receipt = require_i1_native_preflight(node=args.node)
            print(
                "I1_NATIVE_DEPENDENCIES_PRE_WORLD_PASS "
                f"mineflayer={native_receipt.mineflayer_version} "
                f"source_sha256={native_receipt.entities_sha256} "
                f"node_warning={native_receipt.node_module_warning_code or 'NONE'} "
                f"node_stderr_sha256={native_receipt.node_module_stderr_sha256} "
                "world_started=false", flush=True,
            )
            if native_receipt.node_module_warning_code is not None:
                # Do not silently hide an admitted diagnostic in inspect-only.
                # The direct I1 runner also saves the *raw* bytes in
                # i1_native_preflight on its terminal evidence report.
                print(
                    "I1_NATIVE_NODE_WARNING_OBSERVED "
                    f"code={native_receipt.node_module_warning_code} "
                    f"stderr_sha256={native_receipt.node_module_stderr_sha256}",
                    file=sys.stderr, flush=True,
                )
                sys.stderr.write(native_receipt.node_module_stderr_raw)
                sys.stderr.flush()
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
            i1_original_cpu_sense=args.i1_original_cpu_sense,
        ))
        print(f"STAGE28C2B_CAPTURED_UNAUDITED={result}", flush=True)
        return 0
    except BaseException as exc:
        print(f"STAGE28C2B_HOLD={type(exc).__name__}:{exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
