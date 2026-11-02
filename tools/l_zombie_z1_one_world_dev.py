"""DEV ONLY: one disposable Paper1.21.8 World, one unmodified Mineflayer,
one continuously sampled Zombie, exact Paper original SHA, NO L2/Action.

Call only with an explicit one-world grant and --confirm. Source-only Z1,
not pursuit learning, not L0 safety qualification. No retries or extra Worlds.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from adapters.mineflayer.s31a_real_server_ci import (
    _await_spawn,
    _command,
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _verified_target,
    _write_config,
)
from adapters.mineflayer.self_world_observation_only_native_boundary import (
    _loopback_port_can_bind,
    _read_proc_starttime,
    capture_original_native_pid,
)
from adapters.mineflayer.startup_process_ownership import _supervise
from tools.l_zombie_paper_original_audit import (
    PaperZombieSourceRejected,
    report_paper_only,
)
from tools.l_zombie_z2a_prospective_audit import audit_z2a_prospective

PAPER_SHA256 = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
PAPER_SIZE = 52811717
CONFIRM = "Z1_ONE_PAPER_ZOMBIE_SOURCE_WORLD_DEV_NO_RETRY"
PURSUIT_CONFIRM = "Z1B_ONE_PROTECTED_SURVIVAL_ZOMBIE_WORLD_DEV_NO_RETRY"
PROSPECTIVE_CONFIRM = "Z2A_ONE_PROSPECTIVE_PAPER_CHEAP_WORLD_DEV_NO_RETRY"
MARKER = "z1-source-1"
SESSION = "z1-client-1"
START = "L_ZOMBIE_ARM_V1 "
END = "L_ZOMBIE_END_V1 "
MAX_WINDOW_S = 35
EXPECTED_PLUGIN = "relay-l-zombie-paper-dev-0.1.0-dev.jar"


class ZombieWorldBlocked(RuntimeError):
    """One-world original source conditions were not satisfied."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_parent(path: Path) -> None:
    if (
        not isinstance(path, Path) or not path.is_absolute()
        or not path.is_dir() or path.is_symlink()
        or any(part.is_symlink() for part in path.parents)
    ):
        raise ZombieWorldBlocked("existing absolute no-symlink parent required")


def _clean_head(repo: Path, expected: str) -> None:
    if (
        not re.fullmatch(r"[0-9a-f]{40}", expected)
        or not repo.is_absolute() or not repo.is_dir()
    ):
        raise ZombieWorldBlocked("pinned clean worktree/exact HEAD required")
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.PIPE,
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"],
        text=True, stderr=subprocess.PIPE,
    ).strip()
    if head != expected or dirty:
        raise ZombieWorldBlocked("HEAD changed or source worktree dirty")


def preflight(
    *, confirm: str, repo: Path, expected_head: str,
    paper_jar: Path, plugin_jar: Path, plugin_sha256: str,
    world_parent: Path, evidence_parent: Path, run_id: str,
    pursuit_dev: bool = False,
    prospective_cheap_dev: bool = False,
) -> dict:
    """Pure local entry check: no World, Java, Node or disk mutation."""
    expected_confirm = (
        PROSPECTIVE_CONFIRM if prospective_cheap_dev
        else PURSUIT_CONFIRM if pursuit_dev else CONFIRM
    )
    if (
        confirm != expected_confirm
        or os.environ.get("L_ZOMBIE_Z1_ONE_WORLD_DEV") != "1"
        or (pursuit_dev and os.environ.get("L_ZOMBIE_Z1_PURSUIT_DEV") != "1")
        or (prospective_cheap_dev and (
            not pursuit_dev
            or os.environ.get("L_ZOMBIE_Z2A_CHEAP_DEV") != "1"
        ))
    ):
        raise ZombieWorldBlocked("one-world pursuit/safe-target DEV flag missing")
    if os.environ.get("NODE_OPTIONS"):
        raise ZombieWorldBlocked("native Node substitution/options prohibited")
    if not re.fullmatch(r"[0-9a-f]{16}", run_id):
        raise ZombieWorldBlocked("unique 16-hex run_id required")
    _safe_parent(world_parent)
    _safe_parent(evidence_parent)
    _safe_parent(repo)
    _clean_head(repo, expected_head)
    for asset in (paper_jar, plugin_jar):
        if (
            not asset.is_absolute() or not asset.is_file()
            or asset.is_symlink() or any(p.is_symlink() for p in asset.parents)
        ):
            raise ZombieWorldBlocked("pinned real JAR must be absolute and regular")
    if (
        _sha256(paper_jar) != PAPER_SHA256
        or paper_jar.stat().st_size != PAPER_SIZE
        or not re.fullmatch(r"[0-9a-f]{64}", plugin_sha256)
        or _sha256(plugin_jar) != plugin_sha256
        or plugin_jar.name != EXPECTED_PLUGIN
    ):
        raise ZombieWorldBlocked("original Paper / Java plugin SHA, size or name mismatch")
    if (
        (world_parent / f"l-z1-world-{run_id}").exists()
        or (evidence_parent / f"l-z1-evidence-{run_id}").exists()
        or not _loopback_port_can_bind(25565)
    ):
        raise ZombieWorldBlocked("one new World/evidence root or free port unavailable")
    return {
        "classification": "Z1_PREWORLD_SOURCE_ONLY",
        "expected_head": expected_head, "paper_sha256": PAPER_SHA256,
        "plugin_sha256": plugin_sha256, "run_id": run_id,
        "world_budget_max": 1, "world_retries_max": 0,
        "real_gemma_calls": 0, "self_actions": 0, "l0_qualified": False,
        "pursuit_dev": pursuit_dev,
        "prospective_cheap_dev": prospective_cheap_dev,
    }


def active_plugin_config(default: str, *, prospective_cheap_dev: bool = False) -> str:
    """Only two flags from the versioned default, with no other overrides."""
    if (
        default.count("dev-enabled: false") != 1
        or default.count("zombie-tick-readonly-dev: false") != 1
        or default.count("minecraft-version: 1.21.8") != 1
    ):
        raise ZombieWorldBlocked("unknown disabled Z1 Paper plugin configuration")
    modified = (
        default.replace("dev-enabled: false", "dev-enabled: true")
        .replace("zombie-tick-readonly-dev: false", "zombie-tick-readonly-dev: true")
    )
    if prospective_cheap_dev:
        if default.count("zombie-prospective-cheap-dev: false") != 1:
            raise ZombieWorldBlocked("Z2a requires exact disabled plugin forecast flag")
        modified = modified.replace(
            "zombie-prospective-cheap-dev: false",
            "zombie-prospective-cheap-dev: true",
        )
    return modified


async def wait_original_window(
    log_path: Path, *, marker: str, session: str,
    timeout_s: int = MAX_WINDOW_S,
) -> None:
    """Follow sole original Paper stdout collector's saved file (NO second reader)."""
    if not 0 < timeout_s <= MAX_WINDOW_S:
        raise ZombieWorldBlocked("bounded exact original window timeout required")
    deadline = time.monotonic() + timeout_s
    expected = f"{END}marker={marker} session={session} result="
    while time.monotonic() < deadline:
        if log_path.is_file():
            raw = log_path.read_bytes()
            if len(raw) > 16_000_000:
                raise ZombieWorldBlocked("Paper original too large")
            for line in raw.decode("utf-8", errors="replace").splitlines():
                if expected in line:
                    if "result=PAPER_WINDOW_COMPLETE " in line:
                        return
                    raise ZombieWorldBlocked("Paper same-zombie window ended without completion")
        await asyncio.sleep(0.1)
    raise ZombieWorldBlocked("Paper same-zombie bounded 31-tick window not complete")


def _set_up_world(
    *, repo: Path, world_root: Path, evidence_root: Path, plugin_jar: Path,
    prospective_cheap_dev: bool = False,
) -> None:
    _write_config(world_root)  # pinned flat/creative/loopback S31A source
    plugin_dir = world_root / "plugins"
    plugin_dir.mkdir(mode=0o700)
    shutil.copyfile(plugin_jar, plugin_dir / EXPECTED_PLUGIN)
    default_path = (
        repo / "adapters/mineflayer/l_zombie_paper_dev/src/main/resources/config.yml"
    )
    settings = active_plugin_config(default_path.read_text(encoding="utf-8"), prospective_cheap_dev=prospective_cheap_dev)
    # The pinned plugin name in plugin.yml is RelayZombieTickDev.
    config_dir = plugin_dir / "RelayZombieTickDev"
    config_dir.mkdir(mode=0o700)
    (config_dir / "config.yml").write_text(settings, encoding="utf-8")
    (evidence_root / "activated-paper-plugin-original.yml").write_text(
        settings, encoding="utf-8",
    )


async def one_world(
    *, confirm: str, repo: Path, expected_head: str,
    paper_jar: Path, plugin_jar: Path, plugin_sha256: str,
    world_parent: Path, evidence_parent: Path, run_id: str,
    pursuit_dev: bool = False,
    prospective_cheap_dev: bool = False,
) -> dict:
    """Exactly one World and Node client, no user/LLM Actions or retries."""
    checked = preflight(
        confirm=confirm, repo=repo, expected_head=expected_head,
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        plugin_sha256=plugin_sha256, world_parent=world_parent,
        evidence_parent=evidence_parent, run_id=run_id,
        pursuit_dev=pursuit_dev,
        prospective_cheap_dev=prospective_cheap_dev,
    )
    world_root = world_parent / f"l-z1-world-{run_id}"
    evidence_root = evidence_parent / f"l-z1-evidence-{run_id}"
    evidence_root.mkdir(mode=0o700)  # exclusive one physical attempt marker
    report: dict = {
        **checked,
        "status": "BLOCKED", "stage": "PREWORLD",
        "world_started": False, "java_pid": None, "node_pid": None,
        "paper_original_ok": False, "mineflayer_join_attested": False,
        "client_sample_count": 0, "zombie_pursuit_attested": False,
        "pursuit_horizontal_motion_m": None,
        "pursuit_target_survival": pursuit_dev,
        "pursuit_motion_observed": False,
        "l2_model_calls": 0, "self_actions": 0,
        "b1_prediction_qualified": False,
        "prospective_cheap_frozen": False,
        "qualifying_science": False, "retries": 0,
    }
    java = collector = session = None
    java_pid = node_pid = None
    expected_world_identity = None
    try:
        world_root.mkdir(mode=0o700)
        world_st = world_root.stat()
        expected_world_identity = (world_st.st_dev, world_st.st_ino)
        _set_up_world(
            repo=repo, world_root=world_root,
            evidence_root=evidence_root, plugin_jar=plugin_jar,
            prospective_cheap_dev=prospective_cheap_dev,
        )
        report["stage"] = "JAVA_START"
        java, collector, _ = await _ready_server(
            world_root, paper_jar, evidence_root / "paper-console-original.log",
            raw_stdout_path=evidence_root / "paper-console-original.raw",
        )
        java_pid = capture_original_native_pid(java)
        report["java_pid"] = asdict(java_pid)
        report["world_started"] = True
        report["stage"] = "CLIENT_LOGIN"
        node_raw = evidence_root / "mineflayer-original"
        node_raw.mkdir(mode=0o700)
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host="127.0.0.1", port=25565, username="RelaySelf",
                version="1.21.8",
            ),
            bridge_path=repo / "adapters/mineflayer/bridge.mjs",
            raw_capture_root=node_raw, startup_timeout_s=15,
        )
        node_pid = capture_original_native_pid(session._process)
        report["node_pid"] = asdict(node_pid)
        spawn = await _await_spawn(session)
        report["actual_spawn"] = asdict(spawn)
        report["actual_client_session_id"] = session.started.session_id
        _command(java, "gamerule doMobSpawning false")
        _command(java, "time set midnight")
        _command(java, "gamerule doDaylightCycle false")
        if pursuit_dev:
            # An actively targetable survival player with high resistance,
            # regeneration and saturation. Only the disposable World is affected.
            # This is NOT an L0 survival-safety qualification.
            _command(java, "effect give RelaySelf minecraft:resistance 90 4 true")
            _command(java, "effect give RelaySelf minecraft:regeneration 90 4 true")
            _command(java, "effect give RelaySelf minecraft:saturation 90 0 true")
            _command(java, "gamemode survival RelaySelf")
            # Four blocks leaves observable pursuit time without immediate contact.
            summon_distance = 4
        else:
            summon_distance = 2  # prior creative Z1 behavior unchanged
        _command(
            java,
            "execute at RelaySelf run summon minecraft:zombie "
            f"~{summon_distance} ~ ~ "
            "{NoAI:0b,PersistenceRequired:1b}",
        )
        assert java.stdin is not None
        await java.stdin.drain()
        report["stage"] = "ZOMBIE_CLIENT_OBSERVATION"
        target = None
        for idx in range(5):
            current = await _correlated_observe(
                session, f"z1-before-{run_id}-{idx}",
            )
            target = _verified_target(current)
            if target is not None:
                report["before"] = target
                break
            await asyncio.sleep(0.3)
        if target is None:
            raise ZombieWorldBlocked("one zombie not visible in bounded native probe")
        report["client_sample_count"] = 1
        report["stage"] = "PAPER_SOURCE_ARM"
        _command(java, f"relayzombietrack start {MARKER} {SESSION}")
        await java.stdin.drain()
        await wait_original_window(
            evidence_root / "paper-console-original.log",
            marker=MARKER, session=SESSION,
        )
        after = await _correlated_observe(session, f"z1-after-{run_id}")
        post = _verified_target(after)
        if post is None or post["entity_id"] != target["entity_id"]:
            raise ZombieWorldBlocked(
                "client zombie vanished/changed entity id after Paper window"
            )
        report["after"] = post
        report["client_sample_count"] = 2
        report["stage"] = "ORIGINAL_COLLECTION_COMPLETE"
    except BaseException as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        async def finish() -> None:
            if session is not None:
                try:
                    report["node_exit"] = await session.shutdown(timeout_s=10)
                except BaseException as exc:
                    report["node_shutdown_failure"] = f"{type(exc).__name__}: {exc}"
                    try:
                        await session.terminate()
                        report["node_terminated_fallback"] = True
                    except BaseException as secondary:
                        report["node_reap_failure"] = repr(secondary)
            if java is not None:
                try:
                    await _shutdown_server(java, collector)
                    report["java_exit"] = java.returncode
                except BaseException as exc:
                    report["java_shutdown_failure"] = f"{type(exc).__name__}: {exc}"
            if collector is not None:
                report["collector_settled"] = (
                    collector.done() and not collector.cancelled()
                    and collector.exception() is None
                )
            if java_pid is not None:
                report["java_pid_absent"] = _read_proc_starttime(java_pid.pid) is None
            if node_pid is not None:
                report["node_pid_absent"] = _read_proc_starttime(node_pid.pid) is None
            report["port_released"] = _loopback_port_can_bind(25565)
            original = evidence_root / "paper-console-original.raw"
            if original.is_file():
                report["original_sha256"] = _sha256(original)
                report["original_bytes"] = original.stat().st_size
                try:
                    paper = report_paper_only(
                        original.read_bytes(), sha256=report["original_sha256"],
                        marker=MARKER, session=SESSION,
                    )
                    report["paper_source"] = paper
                    report["paper_original_ok"] = True
                    if prospective_cheap_dev:
                        cheap = audit_z2a_prospective(
                            original.read_bytes(), sha256=report["original_sha256"],
                            marker=MARKER, session=SESSION,
                        )
                        report["prospective_cheap"] = cheap
                        report["prospective_cheap_frozen"] = True
                    x0, z0 = paper["pre_source_xz_m"]
                    x1, z1 = paper["target_xz_m"]
                    displacement = math.hypot(x1-x0, z1-z0)
                    report["pursuit_horizontal_motion_m"] = displacement
                    report["pursuit_motion_observed"] = displacement > 0.02
                    # A move alone isn't a confirmed zombie pursuit/AI model.
                    report["zombie_pursuit_attested"] = False
                except (PaperZombieSourceRejected, OSError) as exc:
                    report["paper_source_failure"] = f"{type(exc).__name__}: {exc}"
            clean = (
                java is not None and node_pid is not None and java_pid is not None
                and report.get("node_exit") == 0
                and report.get("java_exit") == 0
                and report.get("collector_settled") is True
                and report.get("java_pid_absent") is True
                and report.get("node_pid_absent") is True
                and report["port_released"] is True
                and not any(
                    key in report for key in (
                        "node_shutdown_failure", "java_shutdown_failure",
                        "node_reap_failure",
                    )
                )
            )
            report["cleanup_confirmed"] = clean
            if clean and expected_world_identity is not None and (
                world_root.is_dir() and not world_root.is_symlink()
                and (world_root.stat().st_dev, world_root.stat().st_ino)
                    == expected_world_identity
            ):
                try:
                    shutil.rmtree(world_root)
                    report["world_removed"] = not world_root.exists()
                except OSError as exc:
                    report["world_disposal_failure"] = repr(exc)
            else:
                report["world_removed"] = False
            if (
                report.get("stage") == "ORIGINAL_COLLECTION_COMPLETE"
                and report["paper_original_ok"]
                and (not prospective_cheap_dev or report["prospective_cheap_frozen"])
                and clean and report.get("world_removed") is True
                and report["before"]["entity_id"] == report["paper_source"]["entity_id"]
                and report["after"]["entity_id"] == report["paper_source"]["entity_id"]
            ):
                if pursuit_dev and not report["pursuit_motion_observed"]:
                    report["status"] = "FAIL_DEV"
                    report["classification"] = "Z1B_PAPER_SOURCE_PASS_MOTION_NOT_OBSERVED"
                else:
                    report["status"] = "PASS_DEV"
                    report["classification"] = (
                        "Z2A_PAPER_CHEAP_PREOUTCOME_DEV_ONLY"
                        if prospective_cheap_dev else
                        "Z1B_PAPER_MOVING_ZOMBIE_SOURCE_DEV_ONLY"
                        if pursuit_dev else "Z1_PAPER_SAME_ZOMBIE_SOURCE_DEV_ONLY"
                    )
            else:
                report["classification"] = "Z1_WORLD_OR_SOURCE_NOT_ESTABLISHED"
            # Paper and client tick pairing is *not* attested by these probes.
            report["mineflayer_join_attested"] = False
            report["zombie_pursuit_attested"] = False
            report["qualifying_science"] = False
            (evidence_root / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
                encoding="utf-8",
            )
        await _supervise(finish())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True, choices=[CONFIRM, PURSUIT_CONFIRM, PROSPECTIVE_CONFIRM])
    parser.add_argument("--prospective-cheap-dev", action="store_true")
    parser.add_argument("--pursuit-dev", action="store_true")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--world-parent", type=Path, required=True)
    parser.add_argument("--evidence-parent", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        report = asyncio.run(one_world(
            confirm=args.confirm, repo=args.repo,
            expected_head=args.expected_head, paper_jar=args.paper_jar,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            world_parent=args.world_parent,
            evidence_parent=args.evidence_parent, run_id=args.run_id,
            pursuit_dev=args.pursuit_dev,
            prospective_cheap_dev=args.prospective_cheap_dev,
        ))
    except (ZombieWorldBlocked, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"Z1_PREWORLD_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["status"], "classification": report["classification"],
        "stage": report["stage"], "world_started": report["world_started"],
        "paper_original_ok": report["paper_original_ok"],
        "client_tick_join_attested": report["mineflayer_join_attested"],
        "action_count": 0, "model_calls": 0,
        "moving_zombie": report["pursuit_motion_observed"],
        "prospective_cheap_frozen": report["prospective_cheap_frozen"],
        "horizontal_displacement_m": report["pursuit_horizontal_motion_m"],
    }, sort_keys=True))
    return 0 if report["status"] == "PASS_DEV" else 2


if __name__ == "__main__":
    raise SystemExit(main())
