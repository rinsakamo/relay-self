from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from experiments.identity_prior_trajectory_transaction import (
    IdentityPriorTransactionError,
    _receive_spawn,
    reset_live_world,
)
from experiments.minecraft_terminal_qualification import (
    EXPECTED_MINECRAFT_SHA256,
    EXPECTED_MINEFLAYER_VERSION,
    RecordedMineflayerSession,
    assert_process_alive,
    jsonable,
    launch_recorded_session,
    message_json,
    prepare_server_root,
    sha256_file,
    write_json,
)

SMOKE_NAME = "relay-self-220-provider-free-apparatus-smoke"
ANCHOR_USERNAME = "RS220SmokeAnchor"
SMOKE_USERNAME = "RS220Smoke"
COMMAND_ERROR_PATTERNS = (
    "Unknown or incomplete command",
    "Incorrect argument for command",
    "Unknown game rule",
)


class ApparatusSmokeError(RuntimeError):
    """Raised when provider-free #220 apparatus qualification cannot complete."""


def _repository_identity(repo_root: Path) -> dict[str, object]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    status = git("status", "--porcelain")
    if status:
        raise ApparatusSmokeError("apparatus smoke requires a clean checkout")
    return {
        "head": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "working_tree_clean": True,
    }


def _require_locked_mineflayer(repo_root: Path) -> dict[str, object]:
    package_path = repo_root / "adapters" / "mineflayer" / "node_modules" / "mineflayer" / "package.json"
    lock_path = repo_root / "adapters" / "mineflayer" / "package-lock.json"
    if not lock_path.is_file():
        raise ApparatusSmokeError("tracked Mineflayer package-lock.json is missing")
    if not package_path.is_file():
        raise ApparatusSmokeError("Mineflayer node_modules is not prepared")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("version") != EXPECTED_MINEFLAYER_VERSION:
        raise ApparatusSmokeError(
            "unexpected Mineflayer version: "
            f"{package.get('version')!r}; expected {EXPECTED_MINEFLAYER_VERSION}"
        )
    return {
        "version": package["version"],
        "package_lock_sha256": sha256_file(lock_path),
    }


def prepare(args: argparse.Namespace) -> dict[str, object]:
    repo_root = Path(args.repo_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    minecraft_jar = Path(args.minecraft_jar).resolve()
    server_root = Path(args.server_root).resolve()

    repository = _repository_identity(repo_root)
    mineflayer = _require_locked_mineflayer(repo_root)
    if sha256_file(minecraft_jar) != EXPECTED_MINECRAFT_SHA256:
        raise ApparatusSmokeError("unexpected Minecraft server.jar SHA256")

    server = prepare_server_root(
        server_root=server_root,
        minecraft_jar=minecraft_jar,
        source_root=None,
        port=args.minecraft_port,
    )
    report = {
        "smoke": SMOKE_NAME,
        "phase": "prepare",
        "scientific_spend": {
            "model_provider_calls": 0,
            "scientific_minecraft_sessions": 0,
        },
        "repository": repository,
        "mineflayer": mineflayer,
        "server": server,
    }
    write_json(evidence_root / "apparatus-smoke-prepare.json", report)
    return report


def _server_log_segment(path: Path, start_offset: int) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(start_offset)
            return handle.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise ApparatusSmokeError(f"could not read Minecraft server log: {exc}") from exc


def _assert_no_command_parse_errors(segment: str) -> None:
    found = [pattern for pattern in COMMAND_ERROR_PATTERNS if pattern in segment]
    if found:
        raise ApparatusSmokeError(
            "Minecraft command parser error observed during apparatus smoke: "
            + ", ".join(found)
        )


async def run(args: argparse.Namespace) -> dict[str, object]:
    repo_root = Path(args.repo_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    server_log = Path(args.server_log).resolve()
    assert_process_alive(args.minecraft_pid, "Minecraft")
    repository = _repository_identity(repo_root)
    mineflayer = _require_locked_mineflayer(repo_root)

    anchor_session: RecordedMineflayerSession | None = None
    smoke_session: RecordedMineflayerSession | None = None
    try:
        anchor_session = await launch_recorded_session(
            args,
            phase="apparatus-smoke-anchor",
            username=ANCHOR_USERNAME,
        )
        anchor_observation = await _receive_spawn(
            anchor_session,
            timeout_s=args.evidence_timeout_s,
        )
        anchor = anchor_observation.snapshot.position
    finally:
        if anchor_session is not None:
            try:
                await anchor_session.shutdown()
            except Exception:
                try:
                    await anchor_session.terminate()
                except Exception:
                    pass

    log_offset = server_log.stat().st_size
    try:
        smoke_session = await launch_recorded_session(
            args,
            phase="apparatus-smoke-reset",
            username=SMOKE_USERNAME,
        )
        reset = await reset_live_world(
            smoke_session,
            args=args,
            username=SMOKE_USERNAME,
            anchor=anchor,
            evidence_path=evidence_root / "apparatus-smoke-server-commands.jsonl",
        )
        segment = _server_log_segment(server_log, log_offset)
        _assert_no_command_parse_errors(segment)
        (evidence_root / "apparatus-smoke-server-segment.log").write_text(
            segment,
            encoding="utf-8",
        )

        report = {
            "smoke": SMOKE_NAME,
            "status": "APPARATUS_SMOKE_PASS",
            "provider_free": True,
            "provider_calls": 0,
            "scientific_spend": {
                "model_provider_calls": 0,
                "scientific_minecraft_sessions": 0,
            },
            "apparatus_sessions": {
                "anchor": 1,
                "reset": 1,
            },
            "repository": repository,
            "mineflayer": mineflayer,
            "minecraft_pid": args.minecraft_pid,
            "anchor": {
                "username": ANCHOR_USERNAME,
                "position": jsonable(anchor),
                "observation": message_json(anchor_observation),
            },
            "reset": {
                "username": SMOKE_USERNAME,
                "cleanup_commands": list(reset.cleanup_commands),
                "cleanup_dirty_marker": reset.cleanup_server_dirty_marker,
                "cleanup_barrier_marker": reset.cleanup_server_barrier_marker,
                "cleanup_zero_probe": message_json(
                    reset.cleanup_zero_observation
                ),
                "summon_command": reset.summon_command,
                "summon_barrier_marker": reset.summon_processed_marker,
                "matched_one_zombie_probe": message_json(
                    reset.matched_observation
                ),
            },
            "server_command_error_patterns": list(COMMAND_ERROR_PATTERNS),
            "server_command_error_scan": "PASS",
        }
        write_json(evidence_root / "apparatus-smoke-report.json", report)
        return report
    finally:
        if smoke_session is not None:
            try:
                await smoke_session.shutdown()
            except Exception:
                try:
                    await smoke_session.terminate()
                except Exception:
                    pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run provider-free live apparatus smoke for RelaySelf #220."
    )
    result.add_argument("--phase", choices=("prepare", "run"), required=True)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--evidence-root", required=True)
    result.add_argument("--server-root")
    result.add_argument("--server-log")
    result.add_argument("--server-control")
    result.add_argument("--minecraft-jar")
    result.add_argument("--minecraft-host", default="127.0.0.1")
    result.add_argument("--minecraft-port", type=int, default=25565)
    result.add_argument("--minecraft-protocol-version")
    result.add_argument("--minecraft-pid", type=int)
    result.add_argument("--node", default="node")
    result.add_argument("--startup-timeout-s", type=float, default=15.0)
    result.add_argument("--evidence-timeout-s", type=float, default=8.0)
    return result


def validate_args(args: argparse.Namespace) -> None:
    args.repo_root = str(Path(args.repo_root).resolve())
    args.evidence_root = str(Path(args.evidence_root).resolve())
    Path(args.evidence_root).mkdir(parents=True, exist_ok=True)
    if args.phase == "prepare":
        for name in ("server_root", "minecraft_jar"):
            if not getattr(args, name, None):
                raise ApparatusSmokeError(
                    f"prepare requires --{name.replace('_', '-')}"
                )
    if args.phase == "run":
        for name in ("server_log", "server_control", "minecraft_pid"):
            if not getattr(args, name, None):
                raise ApparatusSmokeError(
                    f"run requires --{name.replace('_', '-')}"
                )
        if args.minecraft_pid <= 0:
            raise ApparatusSmokeError("--minecraft-pid must be positive")


async def async_main(args: argparse.Namespace) -> int:
    validate_args(args)
    if args.phase == "prepare":
        report = prepare(args)
    else:
        report = await run(args)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    args = parser().parse_args()
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        evidence_root = Path(args.evidence_root).resolve()
        evidence_root.mkdir(parents=True, exist_ok=True)
        failure = {
            "smoke": SMOKE_NAME,
            "status": "APPARATUS_SMOKE_FAIL",
            "provider_free": True,
            "provider_calls": 0,
            "scientific_spend": {
                "model_provider_calls": 0,
                "scientific_minecraft_sessions": 0,
            },
            "phase": args.phase,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "retry_count": 0,
            "replay_count": 0,
        }
        write_json(evidence_root / "apparatus-smoke-failure.json", failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
