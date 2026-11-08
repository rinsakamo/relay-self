"""D14 R3: natural-survival Minecraft World with a 10000 Paper-tick horizon.

Dedicated DEV observation entry. In particular, DO NOT import/call the staged
D4/D8/D12 ATTACK/EAT runner, create Hunger effects, weaken mobs, use NoAI,
teleport enemies or issue a second S49 physical Action. This is an observation
pilot, not an autonomous survival or Learning qualification.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from adapters.mineflayer.s31a_real_server_ci import (
    _correlated_observe,
    _ready_server,
    _shutdown_server,
    _write_config,
)
from adapters.mineflayer.s34_native_world_cognition_ci import _new_session
from adapters.mineflayer.s49_p1_paper_server import PAPER_1218_SHA256, PAPER_1218_SIZE
from tools.bug0_d6_multigen_world import _uuid
from tools.bug0_d14_tick_horizon_world import (
    _field,
    qualified_early_terminal,
)
from tools.bug0_zombie_respawn_r1_world import _qualified_file

PLUGIN_NAME = "relay-zombie-respawn-dev-0.1.0-dev.jar"
NATURAL_PLUGIN_CONFIG = (
    "dev-enabled: true\n"
    "target-player: RelaySelf\n"
    "dev-tick-endurance-enabled: true\n"
    "dev-tick-endurance-ticks: 10000\n"
    "dev-tick-sample-interval: 200\n"
    "dev-natural-world-mode: true\n"
)
R3_ENV = ("S49_REAL_SERVER_CI", "D14_10000_TICK_WORLD_ONLY", "D14_R3_NATURAL_WORLD_ONCE")
MAX_WALL_SECONDS = 1200  # Guard only. Paper-owned elapsed ticks decide qualification.
NATIVE_TIMEOUT_SECONDS = 9


class D14NaturalWorldRejected(RuntimeError):
    """Original source, natural-only configuration or World ownership invalid."""


def natural_properties(original: str) -> str:
    """Override disposable S31 flat/creative baseline before launching Paper.

    Never mutate the existing S31 runner or D4/D8 world staging.
    """
    desired = {
        "level-type": "minecraft:normal",
        "level-name": "d14-r3-natural-ephemeral",
        "gamemode": "survival",
        "force-gamemode": "true",
        "difficulty": "normal",
        "allow-flight": "false",
        "max-players": "1",
    }
    lines = original.splitlines()
    pairs = [line.split("=", 1) for line in lines if "=" in line]
    keys = [pair[0] for pair in pairs]
    if len(set(keys)) != len(keys) or not desired.keys() <= set(keys):
        raise D14NaturalWorldRejected("S31_PROPERTIES_SOURCE_NOT_UNIQUE")
    result = [f"{key}={desired[key]}" if key in desired else line
              for line in lines
              for key in [line.split("=", 1)[0]]]
    data = "\n".join(result) + "\n"
    if any(f"{key}={value}" not in data.splitlines()
           for key, value in desired.items()):
        raise D14NaturalWorldRejected("NATURAL_SURVIVAL_CONFIG_NOT_APPLIED")
    return data


def marker_kind(line: str) -> str | None:
    for kind, tag in (
        ("START", "RSELF_ENDURANCE_START world="),
        ("SAMPLE", "RSELF_ENDURANCE_SAMPLE world="),
        ("LIMIT", "RSELF_ENDURANCE_LIMIT world="),
        ("TERMINAL", "RSELF_ENDURANCE_TERMINAL world="),
        ("ZOMBIE_DEATH", "RSELF_RESPAWN_DEATH world="),
        ("ZOMBIE_RESPAWN", "RSELF_RESPAWN_SPAWN world="),
        ("ZOMBIE_INITIAL", "RSELF_RESPAWN_INITIAL world="),
        ("WORLD_FAULT", "RSELF_RESPAWN_FAULT reason="),
    ):
        if tag in line:
            return kind
    return None


class NaturalPaperTimeline:
    """Pure source boundary: no synthetic clock, observations or physical Actions."""

    def __init__(self) -> None:
        self.start: str | None = None
        self.stop: str | None = None
        self.terminal: str | None = None
        self.samples: list[str] = []
        self.deaths: list[str] = []
        self.respawns: list[str] = []
        self.initial: list[str] = []
        self.world_fault: str | None = None

    def admit(self, kind: str, original: str) -> None:
        if kind == "WORLD_FAULT":
            self.world_fault = original
            raise D14NaturalWorldRejected("PAPER_WORLD_RESPAWN_FAULT")
        if kind == "START":
            if self.start is not None:
                raise D14NaturalWorldRejected("DUPLICATE_START")
            self.start = original
            return
        if kind == "ZOMBIE_INITIAL":
            if self.initial or self.start is not None:
                raise D14NaturalWorldRejected("DUPLICATE_INITIAL_MANAGED_ZOMBIE")
            self.initial.append(original)
            return
        if self.start is None:
            # Initial managed zombie spawn precedes START in original Paper.
            raise D14NaturalWorldRejected("WORLD_EVENT_BEFORE_START")
        if kind in ("TERMINAL", "LIMIT"):
            if self.stop is not None or self.terminal is not None:
                raise D14NaturalWorldRejected("DUPLICATE_OR_CONFLICTING_END")
            if kind == "TERMINAL":
                qualified_early_terminal(self.start, original)
                self.terminal = original
            else:
                if (
                    _uuid(self.start, "world") != _uuid(original, "world")
                    or _field(original, "observed_tick") != _field(self.start, "stop_tick")
                    or _field(original, "elapsed_ticks") != 10000
                    or _field(original, "start_tick") != _field(self.start, "start_tick")
                    or _field(original, "end_tick") != _field(self.start, "stop_tick")
                    or "stop_new_spawns=true no_forced_death=true" not in original
                ):
                    raise D14NaturalWorldRejected("FALSE_WORLD_TICK_HORIZON")
                self.stop = original
            return
        if self.stop is not None or self.terminal is not None:
            raise D14NaturalWorldRejected("EVENT_AFTER_TERMINATION")
        if kind == "SAMPLE":
            elapsed = _field(original, "elapsed_ticks")
            tick = _field(original, "tick")
            if (
                len(self.samples) >= 49
                or elapsed != (len(self.samples) + 1) * 200
                or tick != _field(self.start, "start_tick") + elapsed
                or _uuid(original, "world") != _uuid(self.start, "world")
            ):
                raise D14NaturalWorldRejected("NONCONTIGUOUS_PAPER_TICK_SAMPLES")
            self.samples.append(original)
            return
        if kind in ("ZOMBIE_DEATH", "ZOMBIE_RESPAWN"):
            if _uuid(original, "world") != _uuid(self.start, "world"):
                raise D14NaturalWorldRejected("OTHER_WORLD_ZOMBIE_SOURCE")
            if kind == "ZOMBIE_DEATH":
                self.deaths.append(original)
            else:
                if not self.deaths or len(self.respawns) >= len(self.deaths):
                    raise D14NaturalWorldRejected("RESPAWN_WITHOUT_ORIGINAL_DEATH")
                if (
                    _field(original, "tick") - _field(self.deaths[len(self.respawns)], "tick")
                    != 600
                ):
                    raise D14NaturalWorldRejected("RESPAWN_NOT_AFTER_600_PAPER_TICKS")
                self.respawns.append(original)

    def finish(self) -> dict[str, Any]:
        if self.start is None or len(self.initial) != 1:
            raise D14NaturalWorldRejected("WORLD_START_OR_MANAGED_ZOMBIE_MISSING")
        if self.stop is not None:
            if len(self.samples) != 49 or self.terminal is not None:
                raise D14NaturalWorldRejected("10000_TICK_SAMPLE_OR_END_MISMATCH")
            return {
                "outcome": "WORLD_TICK_LIMIT_REACHED",
                "elapsed_ticks": 10000,
                "terminal_reason": "PAPER_WORLD_LIMIT",
                "self_died_before_limit": False,
            }
        if self.terminal is not None:
            info = qualified_early_terminal(self.start, self.terminal)
            actual = info["elapsed_ticks"]
            # Early death may occur exactly at one of the 200tick samples;
            # never manufacture a missing simultaneous Paper sampling event.
            if not len(self.samples) <= min(49, actual // 200):
                raise D14NaturalWorldRejected("SAMPLE_AFTER_SELF_TERMINAL")
            return {
                "outcome": "SELF_EARLY_TERMINAL",
                "elapsed_ticks": actual,
                "terminal_reason": info["reason"],
                "self_died_before_limit": info["reason"] == "SELF_DIED",
            }
        raise D14NaturalWorldRejected("NO_WORLD_LIMIT_OR_EARLY_TERMINAL")

    def source_summary(self) -> dict[str, Any]:
        return {
            "world_uuid": _uuid(self.start, "world") if self.start else None,
            "start_tick": _field(self.start, "start_tick") if self.start else None,
            "planned_end_tick": _field(self.start, "stop_tick") if self.start else None,
            "original_initial": self.initial,
            "original_deaths": self.deaths,
            "original_respawns": self.respawns,
            "original_start": self.start,
            "original_limit": self.stop,
            "original_early_terminal": self.terminal,
            "sample_ticks": [_field(x, "tick") for x in self.samples],
            "sample_count": len(self.samples),
            "death_count": len(self.deaths),
            "respawn_count": len(self.respawns),
            "original_source_fault": self.world_fault,
        }


async def observe_natural_world(
    session, server, paper_log: Path, journal_path: Path,
    report: dict[str, Any],
    *, max_wall_seconds: int = MAX_WALL_SECONDS,
) -> None:
    if journal_path.exists() or journal_path.is_symlink():
        raise D14NaturalWorldRejected("DERIVATIVE_JOURNAL_ALREADY_EXISTS")
    timeline = NaturalPaperTimeline()
    read_offset = 0
    unconsumed = b""
    readback_errors = 0
    readback_counter = 0
    start_wall = time.monotonic()

    with journal_path.open("x", encoding="utf8") as journal:
        def save(kind: str, line: str, *, native: dict | None = None) -> None:
            journal.write(json.dumps({
                "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
                "kind": kind, "original_paper_line": line,
                "native_observation": native,
            }, sort_keys=True, ensure_ascii=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        while time.monotonic() - start_wall < max_wall_seconds:
            if server.returncode is not None:
                raise D14NaturalWorldRejected("PAPER_SERVER_EXITED_EARLY")
            if paper_log.exists():
                with paper_log.open("rb") as stream:
                    stream.seek(0, 2)
                    if stream.tell() < read_offset:
                        raise D14NaturalWorldRejected("PAPER_LOG_ORIGINAL_TRUNCATED")
                    stream.seek(read_offset)
                    chunk = stream.read()
                    read_offset = stream.tell()
            else:
                chunk = b""
            fresh_samples: list[str] = []
            if chunk:
                rows = (unconsumed + chunk).split(b"\n")
                unconsumed = rows.pop()
                for raw in rows:
                    line = raw.decode("utf8", errors="replace").rstrip("\r")
                    kind = marker_kind(line)
                    if kind is None:
                        continue
                    timeline.admit(kind, line)
                    save(kind, line)
                    if kind == "SAMPLE":
                        fresh_samples.append(line)
                # A Paper terminal always wins over a concurrent stale native read.
                if timeline.stop is not None or timeline.terminal is not None:
                    break

            if fresh_samples:
                readback_counter += 1
                line = fresh_samples[-1]
                request_id = f"d14-r3-native-read-{readback_counter:03d}"
                try:
                    view = await asyncio.wait_for(
                        _correlated_observe(session, request_id),
                        timeout=NATIVE_TIMEOUT_SECONDS,
                    )
                    if (
                        view.session_id != session.started.session_id
                        or view.request_id != request_id
                    ):
                        raise D14NaturalWorldRejected("NATIVE_SESSION_OR_REQUEST_MISMATCH")
                    snap = view.snapshot
                    sample = {
                        "native_request_id": view.request_id,
                        "native_session_id": view.session_id,
                        "native_seq": view.seq,
                        "health": snap.health,
                        "food": snap.food,
                        "oxygen": snap.oxygen_level,
                        "rotten_inventory_count": sum(
                            item.count for item in snap.inventory
                            if item.name == "rotten_flesh"
                        ),
                        "correlation": "AFTER_PAPER_SAMPLE_NOT_SAME_TICK",
                    }
                    save("NATIVE_OBSERVATION", line, native=sample)
                    report["native_snapshots"].append(sample)
                    readback_errors = 0
                except Exception as exc:
                    readback_errors += 1
                    save("NATIVE_OBSERVATION_FAILED", line, native={
                        "error": f"{type(exc).__name__}: {exc}",
                        "request_id": request_id,
                    })
                    if readback_errors >= 2:
                        # Do not hang on a missing native session. Paper
                        # original may still contain a death marker.
                        raise D14NaturalWorldRejected("NATIVE_READBACK_REPEATEDLY_UNAVAILABLE") from exc
            await asyncio.sleep(0.5)
        else:
            raise D14NaturalWorldRejected("HOST_WATCHDOG_BEFORE_WORLD_TICK_OR_DEATH")
    result = timeline.finish()
    report["result"] = result
    report["paper_source"] = timeline.source_summary()
    report["native_readback_count"] = readback_counter
    report["new_s49_actions"] = 0
    report["model_posts"] = 0
    report["learning_updates"] = 0
    report["skill_installs"] = 0


async def run(report_path: Path, paper_log: Path, journal_path: Path) -> int:
    report: dict[str, Any] = {
        "classification": "DEV_D14_R3_NATURAL_WORLD_NOT_RUN",
        "status": "BLOCKED",
        "phase": "PRE_WORLD",
        "world_config": "NATURAL_SURVIVAL",
        "operator_commands": [],
        "staged_zombie_no_ai": False,
        "staged_zombie_low_health": False,
        "staged_hunger_effect": False,
        "staged_enemy_teleport": False,
        "natural_mob_spawning_unchanged": True,
        "world_daylight_behavior": "VANILLA",
        "managed_respawn_after_real_death_ticks": 600,
        "s49_physical_issuer": "NOT_CONNECTED_IN_R3_OBSERVER",
        "new_s49_actions": 0,
        "model_posts": 0,
        "learning_updates": 0,
        "skill_installs": 0,
        "native_snapshots": [],
        "original_log_path": str(paper_log),
        "derivative_journal_path": str(journal_path),
    }
    server = collector = session = temporary = None
    code = 2
    try:
        if (
            any(os.environ.get(key) != "1" for key in R3_ENV)
            or os.environ.get("NODE_OPTIONS") is not None
        ):
            raise D14NaturalWorldRejected("EXCLUSIVE_DEV_NATURAL_WORLD_GRANT_MISSING")
        if any(path.exists() or path.is_symlink()
               for path in (report_path, paper_log, journal_path)):
            raise D14NaturalWorldRejected("PROTECTED_OUTPUT_ALREADY_EXISTS")
        paper = _qualified_file(
            "D14_R3_PAPER_JAR", sha=PAPER_1218_SHA256, size=PAPER_1218_SIZE,
        )
        digest = os.environ.get("D14_R3_RESPAWN_SHA256", "")
        if len(digest) != 64 or any(x not in "0123456789abcdef" for x in digest):
            raise D14NaturalWorldRejected("EXACT_RESPAWN_PLUGIN_DIGEST_REQUIRED")
        plugin = _qualified_file("D14_R3_RESPAWN_JAR", sha=digest)
        if plugin.name != PLUGIN_NAME or paper == plugin:
            raise D14NaturalWorldRejected("WRONG_PAPER_OR_PLUGIN")
        temporary = tempfile.TemporaryDirectory(prefix="d14-r3-natural-oneworld-")
        root = Path(temporary.name)
        _write_config(root)
        properties = root / "server.properties"
        properties.write_text(natural_properties(properties.read_text(encoding="utf8")),
                              encoding="utf8")
        shutil.copyfile(paper, root / "minecraft.jar")
        plugindir = root / "plugins" / "RelayZombieRespawnDev"
        plugindir.mkdir(parents=True)
        shutil.copyfile(plugin, root / "plugins" / PLUGIN_NAME)
        (plugindir / "config.yml").write_text(NATURAL_PLUGIN_CONFIG, encoding="utf8")
        report["server_properties"] = properties.read_text(encoding="utf8")
        report["plugin_config"] = NATURAL_PLUGIN_CONFIG
        report["paper_sha256"] = PAPER_1218_SHA256
        report["plugin_sha256"] = digest
        report["phase"] = "WORLD_START"
        server, collector, _ = await _ready_server(root, root / "minecraft.jar",
                                                   paper_log)
        report["phase"] = "NATIVE_JOIN"
        session = await _new_session()
        report["native_session_id"] = session.started.session_id
        report["phase"] = "NATURAL_WORLD_OBSERVATION"
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        await observe_natural_world(session, server, paper_log, journal_path, report)
        report["status"] = "PASS_DEV"
        report["classification"] = (
            "DEV_D14_R3_NATURAL_10000_PAPER_TICKS_OBSERVED"
            if report["result"]["outcome"] == "WORLD_TICK_LIMIT_REACHED"
            else "DEV_D14_R3_NATURAL_EARLY_SELF_TERMINAL_OBSERVED"
        )
        code = 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["classification"] = "DEV_D14_R3_WORLD_OR_SOURCE_UNQUALIFIED"
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                report["node_exit"] = await session.shutdown(timeout_s=10)
            except Exception as exc:
                report["node_cleanup_error"] = f"{type(exc).__name__}: {exc}"
                try:
                    report["node_exit"] = await session.terminate()
                except Exception as second:
                    report["node_terminate_error"] = repr(second)
        if server is not None:
            try:
                await _shutdown_server(server, collector)
                report["java_exit"] = server.returncode
            except Exception as exc:
                report["server_cleanup_error"] = f"{type(exc).__name__}: {exc}"
                if server.returncode is None:
                    server.kill()
                    await server.wait()
                report["java_exit"] = server.returncode
        if temporary is not None:
            temporary.cleanup()
        if (any(k.endswith("_error") for k in report)
                or (server is not None and report.get("java_exit") != 0)
                or (session is not None and report.get("node_exit") != 0)):
            report["status"] = "FAIL"
            report["classification"] = "DEV_D14_R3_TEARDOWN_UNQUALIFIED"
            code = 2
        report["cleanup_done"] = True
        if paper_log.is_file():
            report["paper_original_sha256"] = hashlib.sha256(paper_log.read_bytes()).hexdigest()
        if journal_path.is_file():
            report["derivative_journal_sha256"] = hashlib.sha256(
                journal_path.read_bytes()
            ).hexdigest()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("x", encoding="utf8") as stream:
            json.dump(report, stream, sort_keys=True, indent=2, ensure_ascii=False)
            stream.write("\n")
    return code


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in ("report", "server-log", "event-journal"):
        parser.add_argument("--" + key, type=Path, required=True)
    a = parser.parse_args()
    raise SystemExit(asyncio.run(run(a.report, a.server_log, a.event_journal)))


if __name__ == "__main__":
    main()
