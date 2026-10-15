"""S-owned M0.2 isolated Paper physics DEV, reusing existing S31A/S50/S51 owners.

This is NOT R qualification or V science. Unlike legacy B0, there is no
separate M0 energy ledger or virtual EAT credit. Original native source
records and server console remain evidence, with honest operator fixtures.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
import tempfile
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.eat_execution import IssuedEatingExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig, MineflayerPosition
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type
from adapters.mineflayer.seek_execution import SeekConsequenceKind, execute_seek_step
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import EatCursor, EatStatus
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekCursor, SeekStatus, SeekWaypoint
from relay_self.skill import SkillExecution

PLUGIN_ROOT = Path(__file__).resolve().parent
M02_CONFIRM = "M02-DEV-I-OWN-DISPOSABLE-PAPER-WORLD"


class M02DevRejected(RuntimeError):
    """Invalid disposable profile, source, owner authorization or cleanup."""


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as inp:
        while chunk := inp.read(1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def _fresh_asset(path: Path, digest: str) -> Path:
    if (not path.is_absolute() or not path.is_file() or path.is_symlink()
            or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
        raise M02DevRejected("absolute unlinked jar and full sha256 required")
    if _sha256(path) != digest:
        raise M02DevRejected("jar SHA256 mismatch")
    return path


def _port_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((SERVER_HOST, SERVER_PORT)) != 0


def _p(tag: str) -> Provenance:
    return Provenance("s51-m02-paper-explicit-dev-fixture", tag)


def _issue(
    supervisor: ActionSupervisor, action_id: str, skill_id: str,
    intent_id: str, objective: str, *, time_base: int,
) -> ActionLifecycle:
    intent = IntentCommitment()
    intent.commit(intent_id, objective=objective, at_ns=time_base,
                  provenance=_p(action_id + "-intent"))
    skill = SkillExecution.start(
        action_id + "-skill", skill_id=skill_id, intent_commitment=intent,
        at_ns=time_base + 1, provenance=_p(action_id + "-skill"),
    )
    proposed = ActionLifecycle.propose(
        action_id, skill_execution=skill, intent_commitment=intent,
        at_ns=time_base + 2, provenance=_p(action_id + "-proposed"),
    )
    authorized = proposed.authorize(
        at_ns=time_base + 3, authority="explicit-s51-m02-dev-operator",
        provenance=_p(action_id + "-authorized"),
    )
    return supervisor.issue(authorized, at_ns=time_base + 4,
                            deadline_ns=time_base + 50,
                            provenance=_p(action_id + "-issued"))


async def _motor_walk(session: MineflayerProcessSession) -> dict:
    before = await _correlated_observe(session, "m02-before-walk")
    p = before.snapshot.position
    # Nominal 1-block S50 plan, *not* an exact 1-block outcome guarantee.
    waypoint = SeekWaypoint(
        "m02-one-block-forward-goal",
        MineflayerPosition(p.x + 2.0, p.y, p.z),
        tolerance_m=0.7, max_step_m=1.0,
    )
    step = SeekCursor(session.started.session_id).plan(before, waypoint)
    if step.status is not SeekStatus.STEER or step.step_distance_m != 1.0:
        raise M02DevRejected("not a valid one-block S50 steering proposal")
    supervisor = ActionSupervisor()
    issued = _issue(
        supervisor, "m02-paper-walk-1", "seek-waypoint",
        "m02-walk", "move one nominal block in isolated test World", time_base=10,
    )
    effect = await execute_seek_step(session, supervisor, issued, step)
    closed = supervisor.record_outcome(
        issued.action_id, at_ns=15,
        provenance=_p("m02-paper-walk-1-outcome"),
    )
    if (closed.state is not ActionState.OUTCOME
            or supervisor.open_actions
            or effect.kind is SeekConsequenceKind.BLOCKED
            or effect.progress_m < 0.05):
        raise M02DevRejected("one authorized S50 walk had no actual World progress")
    return {
        "source_session": effect.session_id,
        "action_id": issued.action_id,
        "action_state": closed.state.value,
        "requested_max_step_blocks": 1.0,
        "observed_progress_blocks": effect.progress_m,
        "kind": effect.kind.value,
        "source_before_seq": effect.before_seq,
        "source_after_seq": effect.after_seq,
        "look_seq": effect.look_seq,
        "forward_seq": effect.forward_seq,
        "clear_seq": effect.clear_seq,
    }


async def _native_steak(session: MineflayerProcessSession, server) -> dict:
    if server.stdin is None:
        raise M02DevRejected("owned server console absent")
    _command(server, "give RelaySelf minecraft:cooked_beef 3")
    _command(server, "effect give RelaySelf minecraft:hunger 25 20 true")
    await server.stdin.drain()
    cursor = EatCursor(session.started.session_id, hunger_threshold=14)
    before = choice = None
    seen: list[dict] = []
    for i in range(16):
        await asyncio.sleep(2)
        probe = await _correlated_observe(session, f"m02-steak-appetite-{i:02d}")
        seen.append({
            "source_seq": probe.seq,
            "food": probe.snapshot.food,
            "saturation": probe.snapshot.food_saturation,
            "steak_count": sum(x.count for x in probe.snapshot.inventory
                               if x.name == "cooked_beef"),
        })
        candidate = cursor.choose(probe)
        if candidate.status is EatStatus.CANDIDATE and candidate.item_name == "cooked_beef":
            before, choice = probe, candidate
            break
    if before is None or choice is None:
        raise M02DevRejected("no authenticated native hunger+steak observation")
    _command(server, "effect clear RelaySelf minecraft:hunger")
    await server.stdin.drain()
    supervisor = ActionSupervisor()
    issued = _issue(
        supervisor, "m02-paper-eat-steak-1", "eat",
        "m02-eat", "eat owned cooked_beef when actually hungry", time_base=100,
    )
    eating = await IssuedEatingExecutor().execute(
        session, supervisor, issued, choice, before,
    )
    outcome = eating.outcome
    if (
        eating.terminal.state is not ActionState.OUTCOME
        or supervisor.open_actions
        or outcome.food_after <= outcome.food_before
        or outcome.count_before - outcome.count_after != 1
    ):
        raise M02DevRejected("real S51 steak consume+inventory effect absent")
    after = await _correlated_observe(session, "m02-after-steak")
    return {
        "source_session": before.session_id,
        "appetite_trace": seen,
        "action_id": issued.action_id,
        "action_state": eating.terminal.state.value,
        "native_outcome": asdict(outcome),
        "saturation_before": before.snapshot.food_saturation,
        "saturation_after": after.snapshot.food_saturation,
        "food_after_followup": after.snapshot.food,
        "after_source_seq": after.seq,
        "virtual_energy_credit": 0,
    }


def _read_world_receipts(server_log: Path) -> dict:
    lines = server_log.read_text(encoding="utf-8").splitlines()
    enabled = [x for x in lines if "M02_DEV_ONLY: candidate physics" in x]
    body = [x for x in lines if "M02_DEV_BODY sampled_tick=" in x]
    walk = [x for x in lines if "M02_DEV_EVENT " in x and "reason=WALK " in x]
    if not enabled or not body or not walk:
        raise M02DevRejected("Paper plugin startup/basal/WALK event evidence absent")
    # For unmodified Paper WALK original is 0; plugin must replace with >0.
    if not any("original=0.0 " in x and "replaced=1.0E-4" in x for x in walk):
        raise M02DevRejected("Paper did not expose expected 0 -> 1cm walking charge")
    return {
        "plugin_enabled_original_log_lines": enabled,
        "basal_world_tick_samples": body[:8],
        "walk_exhaustion_original_replacement_samples": walk[:12],
        "count_walk_logged": len(walk),
        "native_original_log_available": True,
        "native_event_identity_independently_qualified": False,
    }


async def run(
    output_dir: Path, paper_jar: Path, paper_sha: str,
    plugin_jar: Path, plugin_sha: str, *, confirmation: str,
) -> int:
    report: dict = {
        "milestone": "M0.2_PAPER_DEV",
        "status": "BLOCKED",
        "classification": "DEV_ONLY",
        "qualified": False,
        "science_go": False,
        "production_go": False,
        "physical_world": "NOT_RUN",
        "m0_virtual_ledger_used": False,
        "steak": "cooked_beef",
        "minecraft_version": MINECRAFT_VERSION,
    }
    root = None
    server = collector = session = native_file = commands_file = None
    rc = 2
    try:
        if confirmation != M02_CONFIRM:
            raise M02DevRejected("explicit disposable-Paper DEV confirmation missing")
        if (not output_dir.is_absolute() or output_dir.exists()
                or output_dir.is_symlink() or output_dir.parent.is_symlink()
                or not output_dir.parent.is_dir()
                or os.environ.get("NODE_OPTIONS")):
            raise M02DevRejected("fresh absolute owned output root and native Node required")
        paper_jar = _fresh_asset(paper_jar, paper_sha)
        plugin_jar = _fresh_asset(plugin_jar, plugin_sha)
        if not _port_free():
            raise M02DevRejected("existing Minecraft port must not be disturbed")
        output_dir.mkdir()
        server_log = output_dir / "paper_server.log"
        native_file = (output_dir / "original_native.jsonl").open("xb")
        commands_file = (output_dir / "owner_commands.jsonl").open("xb")
        (output_dir / "owned-worlds").mkdir()
        root = tempfile.TemporaryDirectory(prefix="m02-paper-dev-",
                                            dir=str(output_dir / "owned-worlds"))
        world = Path(root.name)
        jar = world / "paper-1.21.8.jar"
        shutil.copyfile(paper_jar, jar)
        _write_config(world)
        # Override generic S31A creative settings for real food/exhaustion.
        props = world / "server.properties"
        props.write_text(props.read_text(encoding="utf-8")
                         .replace("gamemode=creative", "gamemode=survival")
                         .replace("motd=RelaySelf S31A disposable loopback qualification",
                                  "motd=RelaySelf M0.2 isolated DEV"), encoding="utf-8")
        plugin_dir = world / "plugins"
        plugin_dir.mkdir()
        shutil.copyfile(plugin_jar, plugin_dir / "relay-metabolism-paper-dev.jar")
        conf_dir = plugin_dir / "RelayMetabolismDev"
        conf_dir.mkdir()
        source_conf = PLUGIN_ROOT / "src/main/resources/config.yml"
        config = source_conf.read_text(encoding="utf-8")
        if config.count("dev-enabled: false") != 1:
            raise M02DevRejected("untrusted default plugin config shape")
        config = config.replace("dev-enabled: false", "dev-enabled: true")
        (conf_dir / "config.yml").write_text(config, encoding="utf-8")
        report.update({
            "paper_sha256": paper_sha,
            "plugin_sha256": plugin_sha,
            "server_properties_sha256": _sha256(props),
            "plugin_config_sha256": _sha256(conf_dir / "config.yml"),
            "source_config_default_disabled": True,
        })
        report["stage"] = "JAVA_PAPER_DISPOSABLE_START"
        server, collector, _ = await _ready_server(world, jar, server_log)
        report["physical_world"] = "STARTED_NEW_DEV_PAPER"
        report["java_pid"] = server.pid
        report["stage"] = "S51_EXISTING_RECORDED_SOURCE"
        session_type = _recording_session_type(native_file, commands_file)
        session = await session_type.launch(MineflayerLaunchConfig(
            host=SERVER_HOST, port=SERVER_PORT,
            username=BOT_USERNAME, version=MINECRAFT_VERSION,
        ), startup_timeout_s=12)
        await _await_spawn(session)
        report["node_pid"] = session._process.pid
        report["source_session_id"] = session.started.session_id
        assert server.stdin is not None
        _command(server, "gamerule doMobSpawning false")
        _command(server, "gamemode survival RelaySelf")
        await server.stdin.drain()
        report["stage"] = "S50_GOVERNED_ONE_BLOCK_MOVE"
        report["movement"] = await _motor_walk(session)
        report["stage"] = "S51_GOVERNED_STEAK_EAT"
        report["eating"] = await _native_steak(session, server)
        report["stage"] = "PHYSICAL_SOURCE_COLLECTION"
        report["owner_status"] = "PASS"
        rc = 0
    except Exception as exc:
        report["owner_status"] = "BLOCKED" if isinstance(exc, (M02DevRejected, OSError)) else "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        rc = 2 if report["owner_status"] == "BLOCKED" else 1
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=12)
                if report["node_exit"] != 0:
                    raise M02DevRejected("nonzero Node shutdown")
            except Exception as exc:
                report["cleanup_failure"] = "node: " + str(exc)
                rc = 1
                report["owner_status"] = "FAIL"
                try:
                    await session.terminate()
                except Exception:
                    pass
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
                if server.returncode != 0:
                    raise M02DevRejected("nonzero Paper shutdown")
            except Exception as exc:
                report["cleanup_failure"] = "java: " + str(exc)
                rc = 1
                report["owner_status"] = "FAIL"
        for stream in (native_file, commands_file):
            if stream is not None:
                stream.close()
        if root is not None:
            root.cleanup()
        report["port_released_after_shutdown"] = _port_free()
        if not report["port_released_after_shutdown"] and server is not None:
            report["owner_status"] = "FAIL"
            rc = 1
        if output_dir.is_dir():
            server_log = output_dir / "paper_server.log"
            if rc == 0:
                try:
                    report["paper_native_diagnostics"] = _read_world_receipts(server_log)
                    report["status"] = "PASS"
                    report["classification"] = "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
                except Exception as exc:
                    report["owner_status"] = "FAIL"
                    report["status"] = "FAIL"
                    report["error"] = f"unverified World effects: {exc}"
                    rc = 1
            else:
                report["status"] = report.get("owner_status", "BLOCKED")
            raw = output_dir / "original_native.jsonl"
            log = output_dir / "paper_server.log"
            report["evidence_hashes"] = {
                x.name: _sha256(x)
                for x in (raw, log, output_dir / "owner_commands.jsonl")
                if x.is_file()
            }
            (output_dir / "m02_report.json").write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
                encoding="utf-8",
            )
        print("M02_PAPER_DEV_REPORT="+json.dumps(report, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description="M0.2 isolated Paper DEV ONLY")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    return asyncio.run(run(
        args.output_dir, args.paper_jar, args.paper_sha256,
        args.plugin_jar, args.plugin_sha256, confirmation=args.confirm,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
