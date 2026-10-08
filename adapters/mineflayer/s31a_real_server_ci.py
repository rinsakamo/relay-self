"""S31-A disposable *real* Minecraft server / unmodified Mineflayer CI probe.

This module never starts a server on import. Run only under an explicitly
opted-in GitHub Actions job. The only listener is 127.0.0.1:25565 in the
runner; every resource is torn down and every attempt writes a receipt.
No Self Action, cognition epoch, Skill state, or learning is invoked.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerLaunchConfig,
    MineflayerObservation,
)

MINECRAFT_VERSION = "1.21.8"
MINEFLAYER_VERSION = "4.39.0"
MOJANG_MANIFEST_URL = (
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 25565
BOT_USERNAME = "RelaySelf"
ID_INITIAL = "s31a-initial:001"
ID_TARGET_PREFIX = "s31a-target:"
MAX_TARGET_ATTEMPTS = 5


class S31AQualificationError(RuntimeError):
    """A real server or observation did not meet the bounded qualification."""


class S31ABlocked(RuntimeError):
    """Required external artifact/process could not be provisioned."""


def _download_json(url: str, *, timeout: float = 45) -> dict[str, Any]:
    _assert_official_url(url)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        raw = response.read(6_000_001)
    if len(raw) > 6_000_000:
        raise S31ABlocked("official version metadata exceeded bound")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise S31ABlocked("official metadata is not a JSON object")
    return value


def _assert_official_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {
            "piston-meta.mojang.com",
            "piston-data.mojang.com",
            "launchermeta.mojang.com",
            "launcher.mojang.com",
        }
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise S31ABlocked("Minecraft download URL is not an approved Mojang HTTPS host")


def _fetch_official_server(target: Path) -> dict[str, str | int]:
    manifest = _download_json(MOJANG_MANIFEST_URL)
    matches = [
        v for v in manifest.get("versions", [])
        if v.get("id") == MINECRAFT_VERSION and v.get("type") == "release"
    ]
    if len(matches) != 1:
        raise S31ABlocked("exact official Minecraft 1.21.8 release not found")
    version_url = matches[0].get("url")
    version_info = _download_json(version_url)
    if version_info.get("id") != MINECRAFT_VERSION:
        raise S31ABlocked("Mojang version identity mismatch")
    entry = version_info.get("downloads", {}).get("server")
    if not isinstance(entry, dict):
        raise S31ABlocked("Mojang metadata has no vanilla server download")
    url = entry.get("url")
    _assert_official_url(url)
    expected = entry.get("sha1")
    expected_size = entry.get("size")
    if (
        not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-f]{40}", expected) is None
        or not isinstance(expected_size, int)
        or not 100_000 < expected_size < 200_000_000
    ):
        raise S31ABlocked("invalid server download size/hash in Mojang metadata")
    digest = hashlib.sha1()  # noqa: S324 - required published Mojang content checksum, not signatures
    total = 0
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as dst:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > expected_size:
                raise S31ABlocked("download exceeds official server size")
            digest.update(chunk)
            dst.write(chunk)
    if total != expected_size or digest.hexdigest() != expected:
        raise S31ABlocked("download failed exact official server size/SHA1 check")
    return {
        "minecraft_version": MINECRAFT_VERSION,
        "server_sha1": digest.hexdigest(),
        "server_size_bytes": total,
        "download_host": urllib.parse.urlparse(url).hostname or "",
        "manifest_version_url_host": (
            urllib.parse.urlparse(version_url).hostname or ""
        ),
    }


def _write_config(root: Path) -> None:
    # Acceptance of the Minecraft server EULA is limited to a throwaway
    # runner, under the user's explicit request to provision this CI server.
    (root / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    settings = {
        "server-ip": SERVER_HOST,
        "server-port": SERVER_PORT,
        "online-mode": "false",
        "max-players": "2",
        "level-type": "minecraft:flat",
        "level-name": "s31a-ephemeral",
        "gamemode": "creative",
        "force-gamemode": "true",
        "difficulty": "easy",
        "spawn-protection": "0",
        "simulation-distance": "4",
        "view-distance": "4",
        "enable-rcon": "false",
        "enforce-secure-profile": "false",
        "white-list": "false",
        "allow-flight": "true",
        "motd": "RelaySelf S31A disposable loopback qualification",
    }
    (root / "server.properties").write_text(
        "".join(f"{key}={value}\n" for key, value in settings.items()),
        encoding="utf-8",
    )


def _command(server: asyncio.subprocess.Process, command: str) -> None:
    if server.returncode is not None or server.stdin is None:
        raise S31AQualificationError("Minecraft server ended before command")
    server.stdin.write((command + "\n").encode("utf-8"))


async def _ready_server(
    root: Path, jar: Path, log_path: Path,
) -> tuple[asyncio.subprocess.Process, asyncio.Task[None], asyncio.Event]:
    server = await asyncio.create_subprocess_exec(
        "java", "-Xms512M", "-Xmx1536M", "-jar", str(jar), "nogui",
        cwd=str(root),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    ready = asyncio.Event()

    async def collect() -> None:
        assert server.stdout is not None
        with log_path.open("w", encoding="utf-8") as logfile:
            while raw := await server.stdout.readline():
                line = raw.decode("utf-8", errors="replace")
                logfile.write(line)
                logfile.flush()
                if "Done (" in line and "For help" in line:
                    ready.set()

    task = asyncio.create_task(collect())
    try:
        await asyncio.wait_for(ready.wait(), timeout=190)
        if server.returncode is not None:
            raise S31ABlocked("server exited even though startup was signalled")
    except (TimeoutError, S31ABlocked) as exc:
        raise S31ABlocked("Minecraft server startup did not complete") from exc
    return server, task, ready


async def _receive_bounded(session: MineflayerProcessSession, *,
                           timeout: float = 30) -> Any:
    try:
        return await asyncio.wait_for(session.receive(), timeout=timeout)
    except TimeoutError as exc:
        raise S31AQualificationError("Mineflayer message timed out") from exc


def _terminal_check(message: object) -> None:
    if isinstance(message, (MineflayerConnectionEnd, MineflayerAdapterErrorMessage)):
        raise S31AQualificationError(f"Mineflayer ended/error: {message}")
    if isinstance(message, MineflayerCommandError):
        raise S31AQualificationError(f"Mineflayer command rejected: {message.message}")


async def _await_spawn(session: MineflayerProcessSession) -> MineflayerObservation:
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        message = await _receive_bounded(
            session, timeout=max(1, deadline - time.monotonic())
        )
        _terminal_check(message)
        if isinstance(message, MineflayerObservation) and message.kind == "spawn":
            return message
    raise S31AQualificationError("actual Mineflayer spawn not observed")


async def _correlated_observe(
    session: MineflayerProcessSession, request_id: str,
) -> MineflayerObservation:
    await session.send_observe(request_id)
    deadline = time.monotonic() + 30
    for _ in range(120):
        message = await _receive_bounded(
            session, timeout=max(0.1, deadline - time.monotonic())
        )
        _terminal_check(message)
        if isinstance(message, MineflayerObservation) and message.kind == "probe":
            if message.request_id != request_id:
                raise S31AQualificationError(
                    "probe request ID was not matched to explicit request"
                )
            return message
        if time.monotonic() >= deadline:
            break
    raise S31AQualificationError("no exact correlated probe in bounded frames/time")


def _verified_target(observation: MineflayerObservation) -> dict[str, Any] | None:
    coverage = observation.snapshot.nearby_entities_coverage
    if coverage.truncated or coverage.candidate_count != len(
        observation.snapshot.nearby_entities
    ):
        raise S31AQualificationError("actual Mineflayer bounded coverage incomplete")
    origin = observation.snapshot.position
    matches = [
        entity for entity in observation.snapshot.nearby_entities
        if entity.name == "zombie"
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise S31AQualificationError("ambiguous zombie entity identity")
    entity = matches[0]
    pos = entity.position
    calculated = math.dist(
        (origin.x, origin.y, origin.z), (pos.x, pos.y, pos.z)
    )
    if not math.isclose(entity.distance, calculated, rel_tol=0, abs_tol=1e-6):
        raise S31AQualificationError("entity distance differs from World positions")
    if not (0 < calculated <= coverage.max_distance):
        raise S31AQualificationError("zombie lies outside observed bounded distance")
    return {
        "entity_id": entity.entity_id,
        "name": entity.name,
        "distance_m": round(calculated, 6),
        "bot_position": [origin.x, origin.y, origin.z],
        "entity_position": [pos.x, pos.y, pos.z],
        "coverage_scope": coverage.source_scope,
        "coverage_candidates": coverage.candidate_count,
        "coverage_truncated": coverage.truncated,
        "observation_seq": observation.seq,
        "provenance": observation.provenance.reference,
        "request_id": observation.request_id,
    }


async def _shutdown_server(
    server: asyncio.subprocess.Process | None,
    collector: asyncio.Task[None] | None,
) -> None:
    if server is None:
        return
    if server.returncode is None:
        try:
            _command(server, "stop")
            assert server.stdin is not None
            await server.stdin.drain()
            await asyncio.wait_for(server.wait(), timeout=35)
        except (TimeoutError, OSError):
            if server.returncode is None:
                server.kill()
            await server.wait()
    if collector is not None:
        try:
            await asyncio.wait_for(collector, timeout=5)
        except TimeoutError:
            collector.cancel()


async def qualify(report_path: Path, server_log: Path) -> int:
    report: dict[str, Any] = {
        "milestone": "S31-A",
        "classification": "PENDING_REAL_SERVER_EVIDENCE",
        "status": "BLOCKED",
        "stage": "START",
        "server_host": SERVER_HOST,
        "server_port": SERVER_PORT,
        "minecraft_version": MINECRAFT_VERSION,
        "mineflayer_version": MINEFLAYER_VERSION,
        "real_minecraft_server": False,
        "real_mineflayer_package": False,
        "node_test_shim": False,
        "live_minecraft": "NOT_ESTABLISHED",
        "action_issued": False,
        "autonomous_cognition": False,
        "world_evidence_projected_into_s27": False,
    }
    server: asyncio.subprocess.Process | None = None
    collector: asyncio.Task[None] | None = None
    session: MineflayerProcessSession | None = None
    try:
        if os.environ.get("NODE_OPTIONS"):
            raise S31ABlocked("NODE_OPTIONS must be empty: no S30 test substitution")
        if os.environ.get("S31A_REAL_SERVER_CI") != "1":
            raise S31ABlocked("explicit S31A_REAL_SERVER_CI=1 gate not satisfied")
        report["stage"] = "OFFICIAL_DOWNLOAD"
        with tempfile.TemporaryDirectory(prefix="relay-self-s31a-") as temp:
            root = Path(temp)
            jar = root / "minecraft-server.jar"
            try:
                metadata = await asyncio.to_thread(_fetch_official_server, jar)
            except Exception as exc:
                raise S31ABlocked(f"official server unavailable: {exc}") from exc
            report.update(metadata)
            _write_config(root)
            report["stage"] = "SERVER_START"
            try:
                server, collector, _ready = await _ready_server(
                    root, jar, server_log
                )
            except Exception as exc:
                raise S31ABlocked(f"server start failed: {exc}") from exc
            report["real_minecraft_server"] = True
            report["stage"] = "MINEFLAYER_CONNECT"
            try:
                session = await MineflayerProcessSession.launch(
                    MineflayerLaunchConfig(
                        host=SERVER_HOST, port=SERVER_PORT,
                        username=BOT_USERNAME, version=MINECRAFT_VERSION,
                    ),
                    startup_timeout_s=12,
                )
                spawned = await _await_spawn(session)
            except Exception as exc:
                raise S31ABlocked(f"unmodified Mineflayer could not spawn: {exc}") from exc
            report["real_mineflayer_package"] = True
            report["session_id"] = session.started.session_id
            report["spawn_seq"] = spawned.seq
            report["spawn_position"] = [
                spawned.snapshot.position.x,
                spawned.snapshot.position.y,
                spawned.snapshot.position.z,
            ]
            report["stage"] = "INITIAL_PROBE"
            initial = await _correlated_observe(session, ID_INITIAL)
            report["initial_probe"] = {
                "request_id": initial.request_id, "seq": initial.seq,
                "position": [
                    initial.snapshot.position.x,
                    initial.snapshot.position.y,
                    initial.snapshot.position.z,
                ],
            }
            report["stage"] = "CONTROLLED_WORLD_ENTITY"
            _command(server, "gamerule doMobSpawning false")
            _command(server, "time set midnight")
            _command(
                server,
                "execute at RelaySelf run summon minecraft:zombie ~2 ~ ~ "
                "{NoAI:1b,Silent:1b,PersistenceRequired:1b}",
            )
            assert server.stdin is not None
            await server.stdin.drain()
            target = None
            for attempt in range(MAX_TARGET_ATTEMPTS):
                await asyncio.sleep(2)
                request_id = f"{ID_TARGET_PREFIX}{attempt:03d}"
                observed = await _correlated_observe(session, request_id)
                report["last_world_probe_id"] = request_id
                candidate = _verified_target(observed)
                if candidate is not None:
                    target = candidate
                    break
            if target is None:
                raise S31AQualificationError(
                    "controlled zombie never appeared in native Mineflayer registry"
                )
            report["target"] = target
            report["stage"] = "DUPLICATE_REQUEST_REJECTION"
            await session.send_observe(target["request_id"])
            rejected = None
            for _ in range(80):
                message = await _receive_bounded(session, timeout=20)
                if isinstance(message, MineflayerCommandError):
                    rejected = message
                    break
                _terminal_check(message)
            if rejected is None or rejected.message != "duplicate_probe_request_id":
                raise S31AQualificationError("duplicate request did not fail closed")
            report["duplicate_rejected_seq"] = rejected.seq
            report["stage"] = "SUCCESS"
            report["status"] = "PASS"
            report["classification"] = (
                "REAL_MINEFLAYER_LOCAL_MINECRAFT_CORRELATED_WORLD_PROBE_QUALIFIED"
            )
            report["live_minecraft"] = "QUALIFIED_LOCAL_CI_SANDBOX"
            return 0
    except S31ABlocked as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
        print(f"S31A BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(f"S31A FAIL at {report['stage']}: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            try:
                report["bridge_exit_code"] = await session.shutdown(
                    timeout_s=10
                )
            except Exception as exc:
                report["bridge_shutdown_error"] = type(exc).__name__ + ": " + str(exc)
                await session.terminate()
        await _shutdown_server(server, collector)
        if server is not None:
            report["server_exit_code"] = server.returncode
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("S31A_REPORT=" + json.dumps(report, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    args = parser.parse_args()
    return asyncio.run(qualify(args.report, args.server_log))


if __name__ == "__main__":
    raise SystemExit(main())
