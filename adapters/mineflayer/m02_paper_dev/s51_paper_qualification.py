"""Single-run S-owned M0.2 Paper engineering QUALIFICATION producer.

Physically new Paper 1.21.8 sandbox, governed S50 MOVE and S51 EAT, one
Java process / one native Mineflayer session. R independently decides outcome.
Not DEV relabeling, not V SCIENCE, not a calibrated ecology or production GO.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

from adapters.mineflayer.m02_paper_dev import s51_paper_physics_dev as dev
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    BOT_USERNAME,
    MINECRAFT_VERSION,
    SERVER_HOST,
    SERVER_PORT,
    _await_spawn,
    _command,
    _ready_server,
    _shutdown_server,
)
from adapters.mineflayer.s51_eat_real_ci import _recording_session_type
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

# Distinct user approval for THIS one-shot M0.2 qualification, not B0.
GRANT = "USER_M02_PAPER_QUALIFICATION_20261015_ONCE"
CONFIRM = "M02-PAPER-QUALIFICATION-ONE-JAVA-NO-RETRY"
SEED = "2026101501"
ASSET_NAMES = frozenset(dev.PAPER_PREWORLD_ASSET_PINS)


class QualificationBlocked(RuntimeError):
    pass


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while part := f.read(1 << 20):
            h.update(part)
    return h.hexdigest()


def _p(tag: str) -> Provenance:
    return Provenance("s-m02-paper-qualification-authority", tag)


def _issue(
    sup: ActionSupervisor, action_id: str, skill_id: str,
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
        at_ns=time_base + 3, authority=GRANT,
        provenance=_p(action_id + "-authorized"),
    )
    return sup.issue(authorized, at_ns=time_base + 4,
                     deadline_ns=time_base + 50,
                     provenance=_p(action_id + "-issued"))


def check_assets(root: Path) -> dict[str, str]:
    if (not root.is_absolute() or not root.is_dir() or root.is_symlink()
            or any(parent.is_symlink() for parent in root.parents)
            or {p.name for p in root.iterdir()} != ASSET_NAMES):
        raise QualificationBlocked("not a dedicated four-asset pinned root")
    hashes = {}
    for name, pinned in sorted(dev.PAPER_PREWORLD_ASSET_PINS.items()):
        file = root / name
        if not file.is_file() or file.is_symlink() or _sha(file) != pinned:
            raise QualificationBlocked("missing/tampered source asset: " + name)
        hashes[name] = pinned
    raw_props = (root / "server.properties").read_text(encoding="utf-8")
    conf = (root / "config.yml").read_text(encoding="utf-8")
    if ("server-ip=127.0.0.1" not in raw_props.splitlines()
            or "online-mode=false" not in raw_props.splitlines()
            or "gamemode=survival" not in raw_props.splitlines()
            or "target-player: RelaySelf" not in conf.splitlines()
            or "dev-enabled: true" not in conf.splitlines()):
        raise QualificationBlocked("unauthorized/foreign isolated World or player")
    return hashes



def _java21_runtime() -> dict[str, str]:
    """Fail before creating a World or consuming a grant on wrong PATH Java."""
    executable = shutil.which("java")
    if executable is None:
        raise QualificationBlocked("Java 21 executable absent from PATH")
    try:
        result = subprocess.run(
            [executable, "-version"], capture_output=True,
            text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationBlocked("Java runtime preflight unavailable") from exc
    version_text = (result.stderr + "\n" + result.stdout).strip()
    parsed = re.search(r'(?:openjdk|java) version "(\d+)(?:[."]|$)', version_text)
    if result.returncode != 0 or parsed is None or parsed.group(1) != "21":
        raise QualificationBlocked("Paper 1.21.8 requires Java 21, not installed PATH Java")
    return {"java_executable": str(Path(executable).resolve()),
            "java_major": "21"}


def _port_unused() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((SERVER_HOST, SERVER_PORT)) != 0


def _pid_absent(pid: int | None) -> bool:
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _sha_index(root: Path) -> dict[str, str]:
    names = ("paper_server.log", "original_native.jsonl",
             "owner_commands.jsonl", "qualification_producer.json")
    values = {}
    for name in names:
        file = root / name
        if file.is_file() and not file.is_symlink():
            values[name] = _sha(file)
    (root / "SHA256SUMS").write_text(
        "".join(f"{v}  {k}\n" for k, v in sorted(values.items())),
        encoding="ascii",
    )
    return values


def _terminal_native(path: Path, session_id: str) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise QualificationBlocked("native original absent")
    rows = [json.loads(line) for line in lines]
    if (len(rows) < 10 or
            any(row.get("session_id") != session_id
                or type(row.get("seq")) is not int
                or row["seq"] != i for i, row in enumerate(rows)) or
            rows[-2].get("type") != "shutdown_ack" or
            rows[-1].get("type") != "connection_end"):
        raise QualificationBlocked("raw native session/STOP sequence unavailable")
    return {"native_rows": len(rows),
            "native_stop_ack_seq": rows[-2]["seq"],
            "native_connection_end_seq": rows[-1]["seq"]}


async def run(*, asset_root: Path, output_root: Path, confirm: str) -> int:
    receipt: dict = {
        "classification": "M02_PAPER_QUALIFICATION_PREWORLD_BLOCKED",
        "owner": "S", "mode": "QUALIFICATION",
        "grant_id": GRANT, "authorization_consumed": False,
        "qual_engineering": False, "science_success": False,
        "production_go": False, "v_trials": 0, "new_world": "NOT_RUN",
        "retry_count": 0, "java_launch_count": 0, "node_session_count": 0,
        "virtual_m0_ledger_used": False, "source_mode": "PAPER_CANDIDATE",
    }
    # Every gate here precedes first potentially irreversible Java start.
    if confirm != CONFIRM:
        raise QualificationBlocked("single-run qualifier confirmation absent")
    pins = check_assets(asset_root)
    receipt["java_runtime_preflight"] = _java21_runtime()
    if (not output_root.is_absolute() or output_root.exists()
            or not output_root.parent.is_dir()
            or output_root.parent.is_symlink()
            or not _port_unused()
            or os.environ.get("NODE_OPTIONS")):
        raise QualificationBlocked("existing World/output/port/Node overrides")
    # New independent ID, no inheritance of previous B0 or DEV root.
    receipt["run_id"] = secrets.token_hex(16)
    receipt["source_session_id"] = "NOT_STARTED"
    receipt["source_asset_hashes"] = pins
    receipt["seed"] = SEED
    receipt["paper_version"] = MINECRAFT_VERSION
    output_root.mkdir(mode=0o700)
    (output_root / "owned-worlds").mkdir()
    native_file = (output_root / "original_native.jsonl").open("xb")
    commands_file = (output_root / "owner_commands.jsonl").open("xb")
    owned = tempfile.TemporaryDirectory(prefix="m02-paper-qualification-",
                                         dir=output_root / "owned-worlds")
    world = Path(owned.name)
    java = collector = session = None
    rc = 2
    try:
        # One new isolated World; no previous vanilla Golden or personal World.
        shutil.copyfile(asset_root / "paper-1.21.8.jar",
                        world / "paper-1.21.8.jar")
        (world / "plugins" / "RelayMetabolismDev").mkdir(parents=True)
        shutil.copyfile(asset_root / "relay-metabolism-paper-dev.jar",
                        world / "plugins" / "relay-metabolism-paper-dev.jar")
        shutil.copyfile(asset_root / "config.yml",
                        world / "plugins" / "RelayMetabolismDev" / "config.yml")
        properties = (asset_root / "server.properties").read_bytes()
        (world / "server.properties").write_bytes(
            properties + f"level-seed={SEED}\n".encode("ascii"))
        (world / "eula.txt").write_text("eula=true\n", encoding="ascii")
        receipt["world_seeded_properties_sha256"] = _sha(world / "server.properties")
        receipt["stage"] = "ONE_JAVA_START"
        # Consume the one-shot grant BEFORE beginning physical Java startup.
        receipt["authorization_consumed"] = True
        receipt["java_launch_count"] = 1
        java, collector, _ = await _ready_server(
            world, world / "paper-1.21.8.jar", output_root / "paper_server.log")
        receipt["new_world"] = "NEW_ISOLATED_PAPER"
        receipt["java_pid"] = java.pid
        level = world / "s31a-ephemeral" / "level.dat"
        if level.is_file():
            receipt["initial_level_dat_sha256"] = _sha(level)
        receipt["stage"] = "ONE_NODE_SESSION"
        receipt["node_session_count"] = 1
        session_type = _recording_session_type(native_file, commands_file)
        session = await session_type.launch(MineflayerLaunchConfig(
            host=SERVER_HOST, port=SERVER_PORT, username=BOT_USERNAME,
            version=MINECRAFT_VERSION), startup_timeout_s=12)
        await _await_spawn(session)
        receipt["node_pid"] = session._process.pid
        receipt["source_session_id"] = session.started.session_id
        _command(java, "gamerule doMobSpawning false")
        _command(java, "gamemode survival RelaySelf")
        assert java.stdin is not None
        await java.stdin.drain()
        receipt["stage"] = "S50_QUAL_GOVERNED_MOVE"
        receipt["movement"] = await dev._motor_walk(
            session, issuer=_issue, provenance=_p)
        receipt["stage"] = "S51_QUAL_GOVERNED_EAT"
        receipt["eating"] = await dev._native_steak(session, java, issuer=_issue)
        receipt["stage"] = "SOURCE_AND_EXIT_CAPTURE"
        rc = 0
    except BaseException as exc:
        receipt["failure"] = f"{type(exc).__name__}: {exc}"
        rc = 1
    finally:
        if session is not None:
            try:
                receipt["node_exit"] = await session.shutdown(timeout_s=12)
                if receipt["node_exit"] != 0:
                    raise QualificationBlocked("Node nonzero shutdown")
            except BaseException as exc:
                receipt["node_shutdown_failure"] = str(exc)
                rc = 1
                try:
                    await session.terminate()
                except BaseException:
                    pass
        if java is not None:
            try:
                await _shutdown_server(java, collector)
                receipt["java_exit"] = java.returncode
                if receipt["java_exit"] != 0:
                    raise QualificationBlocked("Java nonzero shutdown")
            except BaseException as exc:
                receipt["java_shutdown_failure"] = str(exc)
                rc = 1
        native_file.close()
        commands_file.close()
        owned.cleanup()
        receipt["owned_world_cleaned"] = not world.exists()
        receipt["port_released"] = _port_unused()
        receipt["owned_java_pid_absent"] = _pid_absent(receipt.get("java_pid"))
        receipt["owned_node_pid_absent"] = _pid_absent(receipt.get("node_pid"))
        if rc == 0:
            try:
                receipt.update(_terminal_native(
                    output_root / "original_native.jsonl",
                    receipt["source_session_id"]))
                receipt["paper_source_samples"] = dev._read_world_receipts(
                    output_root / "paper_server.log")
                if not (receipt["owned_world_cleaned"]
                        and receipt["port_released"]
                        and receipt["owned_java_pid_absent"]
                        and receipt["owned_node_pid_absent"]):
                    raise QualificationBlocked("cleanup not independently closed")
                receipt["classification"] = "S_M02_PAPER_QUALIFICATION_SOURCE_CLOSED_R_REVIEW_REQUIRED"
            except BaseException as exc:
                receipt["failure"] = str(exc)
                receipt["classification"] = "S_M02_PAPER_QUALIFICATION_SOURCE_UNDETERMINED"
                rc = 1
        else:
            receipt["classification"] = (
                "S_M02_PAPER_QUALIFICATION_ATTEMPT_FAILED_CONSUMED"
                if receipt["authorization_consumed"] else
                "M02_PAPER_QUALIFICATION_PREWORLD_BLOCKED")
        receipt["qual_engineering"] = False  # R must decide independently.
        (output_root / "qualification_producer.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False)+"\n",
            encoding="utf-8")
        receipt["evidence_hashes"] = _sha_index(output_root)
        print("S_M02_PAPER_QUAL_SOURCE="+json.dumps(receipt, sort_keys=True))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    return asyncio.run(run(asset_root=args.asset_root,
                           output_root=args.output_root,
                           confirm=args.confirm))


if __name__ == "__main__":
    raise SystemExit(main())
