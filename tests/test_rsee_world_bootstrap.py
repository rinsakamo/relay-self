"""RSEE first-World bootstrap tests: no real Node, Java, model or EULA."""
from __future__ import annotations

import asyncio
import gzip
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.standard_env import world_bootstrap as bootstrap
from experiments.standard_env import world_binding as binding
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerInventoryItem,
    MineflayerNearbyEntitiesCoverage,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)


def _name(s):
    raw = s.encode()
    return struct.pack(">H", len(raw)) + raw


def _tag(tag, name, value):
    return bytes([tag]) + _name(name) + value


def _compound(children):
    return b"".join(children) + b"\x00"


def _nbt(root):
    return gzip.compress(b"\x0a" + _name("") + _compound(root), mtime=0)


def _fixture_world(root: Path, *, seed=575, health=20.0):
    root.mkdir(parents=True)
    gen = _tag(10, "WorldGenSettings", _compound([
        _tag(4, "seed", struct.pack(">q", seed)),
    ]))
    rules = _tag(10, "GameRules", _compound([
        _tag(8, "doDaylightCycle", _name("true")),
        _tag(8, "doMobSpawning", _name("true")),
    ]))
    data = _tag(10, "Data", _compound([
        gen, rules,
        _tag(1, "raining", b"\x00"),
        _tag(1, "thundering", b"\x00"),
        _tag(4, "Time", struct.pack(">q", 150)),
        _tag(4, "DayTime", struct.pack(">q", 150)),
    ]))
    (root / "level.dat").write_bytes(_nbt([data]))
    players = root / "playerdata"
    players.mkdir()
    player = [
        _tag(9, "Rotation", b"\x05" + struct.pack(">i", 2)
             + struct.pack(">ff", 0.0, 0.0)),
        _tag(9, "Pos", b"\x06" + struct.pack(">i", 3)
             + struct.pack(">ddd", 0.5, 64.0, 0.5)),
        _tag(9, "Inventory", b"\x0a" + struct.pack(">i", 0)),
        _tag(5, "Health", struct.pack(">f", health)),
        _tag(3, "foodLevel", struct.pack(">i", 20)),
    ]
    (players / "native-uuid.dat").write_bytes(_nbt(player))


def _fake_initial():
    coverage = MineflayerNearbyEntitiesCoverage(
        source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        candidate_count=0, truncated=False,
    )
    snap = MineflayerSnapshot(
        health=20.0, food=20.0, food_saturation=5.0,
        oxygen_level=None, position=MineflayerPosition(0.5, 64.0, 0.5),
        time=MineflayerTime(150, 0, True),
        inventory=(), nearby_entities=(),
        nearby_entities_coverage=coverage,
    )
    return SimpleNamespace(
        kind="probe", request_id="rsee-bootstrap-initial:001", seq=6,
        snapshot=snap,
    )


def test_bootstrap_saved_native_extracts_pose_weather_gamerules(tmp_path):
    root = tmp_path / "world"
    _fixture_world(root)
    found = bootstrap._saved_native_details(root)
    assert found["seed_tag_long"] == 575
    assert found["gamerules"]["doDaylightCycle"] == "true"
    assert found["raining"] is False
    assert found["thundering"] is False
    assert found["rotation"] == [0.0, 0.0]
    assert found["position"] == [0.5, 64.0, 0.5]
    assert found["inventory"] == []
    evidence = bootstrap._build_observation(_fake_initial(), "native-session", found)
    assert evidence["schema"] == bootstrap.OBSERVATION_SCHEMA
    assert evidence["bootstrap_issued_game_actions"] == 0
    assert evidence["golden_run_permitted"] is False


@pytest.mark.parametrize("variant", [
    "wrong_seed", "lost_gamerules", "two_players", "wrong_player_health",
    "wrong_player_pose", "missing_time",
])
def test_bad_stopped_world_cannot_be_qualified(tmp_path, variant):
    root = tmp_path / "world"
    _fixture_world(root, seed=576 if variant == "wrong_seed" else 575,
                   health=19 if variant == "wrong_player_health" else 20)
    if variant == "lost_gamerules":
        path = root / "level.dat"
        with gzip.open(path, "rb") as inp:
            raw = inp.read()
        # Build malformed native GameRules by altering compound name.
        path.write_bytes(gzip.compress(raw.replace(b"GameRules", b"GameRulEz"), mtime=0))
    if variant == "two_players":
        (root / "playerdata" / "second.dat").write_bytes(
            (root / "playerdata" / "native-uuid.dat").read_bytes()
        )
    if variant == "wrong_player_pose":
        path = root / "playerdata" / "native-uuid.dat"
        with gzip.open(path, "rb") as inp:
            raw = inp.read()
        # The numeric saved position may diverge even with valid bytes.
        path.write_bytes(gzip.compress(raw.replace(
            struct.pack(">ddd", 0.5, 64.0, 0.5),
            struct.pack(">ddd", 100.5, 64.0, 0.5),
        ), mtime=0))
    if variant == "missing_time":
        path = root / "level.dat"
        with gzip.open(path, "rb") as inp:
            raw = inp.read()
        path.write_bytes(gzip.compress(raw.replace(b"DayTime", b"NoTime!"), mtime=0))
    if variant == "wrong_player_health":
        saved = bootstrap._saved_native_details(root)
        with pytest.raises(bootstrap.BootstrapRejected):
            bootstrap._build_observation(_fake_initial(), "s", saved)
    elif variant == "wrong_player_pose":
        saved = bootstrap._saved_native_details(root)
        with pytest.raises(bootstrap.BootstrapRejected):
            bootstrap._build_observation(_fake_initial(), "s", saved)
    else:
        with pytest.raises((bootstrap.BootstrapRejected, binding.WorldBindingRejected)):
            bootstrap._saved_native_details(root)


def test_no_world_launch_when_consent_or_eula_missing(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("no host setup/start without explicit EULA and grant")

    monkeypatch.setattr(bootstrap, "_port_free", forbidden)
    empty = tmp_path / "evidence"
    empty.mkdir()
    jar = tmp_path / "unused.jar"
    jar.write_bytes(b"synthetic-only")
    for opts in (
        ["--confirm", "incorrect"],
        ["--confirm", bootstrap.CONSENT],
    ):
        assert bootstrap.main([
            "--jar", str(jar), "--output-dir", str(empty), *opts,
        ]) == 2
        assert json.loads(capsys.readouterr().out)["minecraft_launch_attempts"] == 0
    assert list(empty.iterdir()) == []


def test_first_world_one_shot_mock_creates_bytebound_snapshot(tmp_path, monkeypatch):
    jar = tmp_path / "minecraft-1.21.8.jar"
    jar.write_bytes(b"synthetic-minecraft-jar")
    monkeypatch.setattr(bootstrap, "JAR_SHA256", binding.JAR_SHA256)
    # The production verify_world_binding retains the real jar grant. Synthetic
    # validation is mocked *only* here, not in product runtime.
    def verify_no_physical_origin(jar_path, snap, manifest, obs):
        manifest_data = json.loads(manifest.read_text())
        assert manifest_data["jar_sha256"] == binding.JAR_SHA256
        assert manifest_data["initial_evidence_sha256"] == binding._hash_file(obs)
        assert binding._world_files(snap)
        return SimpleNamespace(
            jar_sha256=binding.JAR_SHA256,
            manifest_sha256=binding._hash_file(manifest),
            initial_evidence_sha256=binding._hash_file(obs),
            files=binding._world_files(snap),
        )
    monkeypatch.setattr(bootstrap, "verify_world_binding", verify_no_physical_origin)
    monkeypatch.setattr(bootstrap, "_hash_file", lambda path: (
        binding.JAR_SHA256 if path.name == "minecraft.jar"
        else binding._hash_file(path)
    ))
    class Server:
        returncode = None
    server = Server()
    async def fake_ready(root, jar_path, log_path):
        assert jar_path.read_bytes() == jar.read_bytes()
        assert "level-seed=575" in (root / "server.properties").read_text()
        _fixture_world(root / binding.LEVEL)
        return server, None, None
    async def fake_stop(_server, _collector):
        server.returncode = 0
    @dataclass
    class Started:
        session_id: str = "mock-session"
    class Bridge:
        started = Started()
        process_returncode = 0
        async def shutdown(self, *, timeout_s):
            return 0
    async def fake_launch(*args, **kwargs):
        return Bridge()
    async def fake_spawn(*args, **kwargs):
        return SimpleNamespace(seq=5)
    async def fake_observe(*args, **kwargs):
        return _fake_initial()
    monkeypatch.setattr(bootstrap, "_ready_server", fake_ready)
    monkeypatch.setattr(bootstrap, "_shutdown_server", fake_stop)
    monkeypatch.setattr(bootstrap.MineflayerProcessSession, "launch", fake_launch)
    monkeypatch.setattr(bootstrap, "_await_spawn", fake_spawn)
    monkeypatch.setattr(bootstrap, "_correlated_observe", fake_observe)
    out = tmp_path / "fresh"
    out.mkdir()
    assert asyncio.run(bootstrap._run_once(jar, out)) == 0
    receipt = json.loads((out / bootstrap.REPORT).read_text())
    assert receipt["status"] == "PASS"
    assert receipt["snapshot_qualified"] is True
    assert receipt["llm_posts"] == receipt["self_actions"] == 0
    assert (out / "snapshot" / "level.dat").exists()
    assert (out / bootstrap.OBSERVATION).exists()
    assert (out / bootstrap.MANIFEST).exists()
    assert binding._world_files(out / "snapshot") == binding._world_files(
        out / "game" / binding.LEVEL
    )
