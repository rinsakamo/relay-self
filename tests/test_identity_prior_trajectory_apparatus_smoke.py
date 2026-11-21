from __future__ import annotations

import argparse
import asyncio
import inspect
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from experiments import identity_prior_trajectory_apparatus_smoke as smoke
from experiments.identity_prior_trajectory_transaction import ResetEvidence


class FakeSession:
    def __init__(self, session_id: str) -> None:
        self.started = SimpleNamespace(session_id=session_id)
        self.shutdown_calls = 0

    async def shutdown(self) -> None:
        self.shutdown_calls += 1

    async def terminate(self) -> None:
        raise AssertionError("clean smoke fixture should not terminate")


def coverage(count: int) -> MineflayerNearbyEntitiesCoverage:
    return MineflayerNearbyEntitiesCoverage(
        source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        candidate_count=count,
        truncated=False,
    )


def observation(
    *,
    session_id: str,
    seq: int,
    kind: str,
    entities: tuple[MineflayerEntityFact, ...] = (),
) -> MineflayerObservation:
    return MineflayerObservation(
        session_id=session_id,
        seq=seq,
        kind=kind,
        snapshot=MineflayerSnapshot(
            health=20,
            food=20,
            food_saturation=5,
            oxygen_level=None,
            position=MineflayerPosition(x=0, y=64, z=0),
            time=MineflayerTime(time_of_day=6000, day=0, is_day=True),
            inventory=(),
            nearby_entities=entities,
            nearby_entities_coverage=coverage(len(entities)),
        ),
    )


def zombie() -> MineflayerEntityFact:
    return MineflayerEntityFact(
        entity_id=7,
        name="zombie",
        entity_type="mob",
        distance=4.0,
        position=MineflayerPosition(x=4, y=64, z=0),
    )


def test_smoke_module_has_no_provider_path() -> None:
    source = inspect.getsource(smoke)
    assert "provider_engine" not in source
    assert "LlamaCppRelayProvider" not in source
    assert "llama_origin" not in source
    assert "served_model" not in source


def test_smoke_rejects_server_command_parser_error() -> None:
    with pytest.raises(
        smoke.ApparatusSmokeError,
        match="command parser error",
    ):
        smoke._assert_no_command_parse_errors(
            "Unknown or incomplete command, see below for error"
        )


def test_provider_free_smoke_reports_grounded_reset_without_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    anchor_session = FakeSession("anchor-session")
    reset_session = FakeSession("reset-session")
    sessions = iter((anchor_session, reset_session))
    anchor_observation = observation(
        session_id="anchor-session",
        seq=1,
        kind="spawn",
    )
    zero_probe = observation(
        session_id="reset-session",
        seq=2,
        kind="probe",
    )
    one_probe = observation(
        session_id="reset-session",
        seq=3,
        kind="probe",
        entities=(zombie(),),
    )

    async def fake_launch(*_args, **_kwargs):
        return next(sessions)

    async def fake_receive_spawn(_session, *, timeout_s: float):
        assert timeout_s > 0
        return anchor_observation

    async def fake_reset(*_args, **_kwargs):
        return ResetEvidence(
            cleanup_commands=("gamerule minecraft:spawn_mobs false",),
            cleanup_server_dirty_command="execute if entity ...",
            cleanup_server_barrier_command="say ZERO",
            cleanup_server_dirty_marker="DIRTY",
            cleanup_server_barrier_marker="ZERO",
            cleanup_zero_observation=zero_probe,
            summon_command="summon minecraft:zombie",
            summon_processed_barrier_command="say SUMMON",
            summon_processed_marker="SUMMON",
            matched_observation=one_probe,
        )

    monkeypatch.setattr(smoke, "launch_recorded_session", fake_launch)
    monkeypatch.setattr(smoke, "_receive_spawn", fake_receive_spawn)
    monkeypatch.setattr(smoke, "reset_live_world", fake_reset)
    monkeypatch.setattr(smoke, "assert_process_alive", lambda *_args: None)
    monkeypatch.setattr(
        smoke,
        "_repository_identity",
        lambda _root: {
            "head": "a" * 40,
            "tree": "b" * 40,
            "working_tree_clean": True,
        },
    )
    monkeypatch.setattr(
        smoke,
        "_require_locked_mineflayer",
        lambda _root: {
            "version": "4.39.0",
            "package_lock_sha256": "c" * 64,
        },
    )

    server_log = tmp_path / "minecraft-server.log"
    server_log.write_text("clean server log\n", encoding="utf-8")
    args = argparse.Namespace(
        repo_root=str(tmp_path),
        evidence_root=str(tmp_path),
        server_log=str(server_log),
        server_control=str(tmp_path / "server.stdin"),
        minecraft_pid=4242,
        minecraft_host="127.0.0.1",
        minecraft_port=25565,
        minecraft_protocol_version=None,
        node="node",
        startup_timeout_s=1.0,
        evidence_timeout_s=1.0,
    )

    report = asyncio.run(smoke.run(args))

    assert report["status"] == "APPARATUS_SMOKE_PASS"
    assert report["provider_free"] is True
    assert report["provider_calls"] == 0
    assert report["scientific_spend"] == {
        "model_provider_calls": 0,
        "scientific_minecraft_sessions": 0,
    }
    assert report["apparatus_sessions"] == {"anchor": 1, "reset": 1}
    assert report["server_command_error_scan"] == "PASS"
    assert anchor_session.shutdown_calls == 1
    assert reset_session.shutdown_calls == 1


def test_canonical_smoke_launcher_is_provider_free_and_one_shot() -> None:
    launcher = Path(
        "experiments/run_identity_prior_trajectory_apparatus_smoke.sh"
    ).read_text(encoding="utf-8")

    assert launcher.count("--phase run") == 1
    assert launcher.count("--phase prepare") == 1
    assert "llama-server" not in launcher
    assert "--model" not in launcher
    assert "GGUF" not in launcher
    assert '"$NPM" ci --omit=dev --no-audit --no-fund' in launcher
    assert "package-lock.json" in launcher
    assert "server.jar" in launcher
    assert "MINECRAFT_SOURCE_ROOT" not in launcher
    assert "apparatus-smoke-report.json" in launcher
    assert "scientific-report.json" not in launcher

    syntax = subprocess.run(
        [
            "bash",
            "-n",
            "experiments/run_identity_prior_trajectory_apparatus_smoke.sh",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert syntax.returncode == 0, syntax.stderr
