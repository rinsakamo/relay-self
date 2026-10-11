"""Deterministic RSEE one-shot bootstrap tests: NO real Java/Node/LLM."""
from __future__ import annotations

import asyncio
import gzip
import json
import struct
from dataclasses import dataclass

import pytest

from experiments.standard_env import world_bootstrap as boot
from experiments.standard_env import world_binding as bind


def _str(s: str) -> bytes:
    raw = s.encode()
    return struct.pack(">H", len(raw)) + raw


def _tag(kind: int, key: str, raw: bytes) -> bytes:
    return bytes([kind]) + _str(key) + raw


def _comp(key: str, children: bytes) -> bytes:
    return _tag(10, key, children + b"\x00")


def _root(children: bytes) -> bytes:
    return gzip.compress(b"\x0a" + _str("") + children + b"\x00", mtime=0)


def _world_bytes(*, seed: int = 575, rainy: bool = False, freeze: bool = True) -> bytes:
    rule_values = {
        "doDaylightCycle": "false" if freeze else "true",
        "doWeatherCycle": "false", "doMobSpawning": "false",
    }
    rules = b"".join(_tag(8, key, _str(value)) for key, value in rule_values.items())
    data = (
        _comp("WorldGenSettings", _tag(4, "seed", struct.pack(">q", seed)))
        + _comp("GameRules", rules)
        + _tag(4, "DayTime", struct.pack(">q", 18000))
        + _tag(1, "raining", bytes([int(rainy)]))
        + _tag(1, "thundering", b"\x00")
    )
    return _root(_comp("Data", data))


def _player_bytes(*, yaw: float = 0.7) -> bytes:
    return _root(
        _tag(9, "Pos", b"\x06" + struct.pack(">i", 3)
             + struct.pack(">ddd", 0.0, -60.0, 0.0))
        + _tag(9, "Rotation", b"\x05" + struct.pack(">i", 2)
               + struct.pack(">ff", yaw, 0.4))
        + _tag(5, "Health", struct.pack(">f", 20.0))
        + _tag(3, "foodLevel", struct.pack(">i", 20))
        + _tag(9, "Inventory", b"\x0a" + struct.pack(">i", 0))
    )


def _build_stopped(root, **kwargs):
    world = root / boot.LEVEL
    world.mkdir(parents=True)
    (world / "level.dat").write_bytes(_world_bytes(**kwargs))
    users = world / "playerdata"
    users.mkdir()
    (users / "only-player.dat").write_bytes(_player_bytes())
    return world


@dataclass(frozen=True)
class _Observation:
    seq: int
    session_id: str
    kind: str = "probe"


def test_bootstrap_requires_own_consent_and_eula_before_any_artifact_access(
    monkeypatch, tmp_path, capsys,
):
    def forbidden(*_args, **_kw):
        pytest.fail("must not read jar / start process without explicit grants")

    monkeypatch.setattr(boot, "_hash_file", forbidden)
    for options in ([], ["--authorize-world-bootstrap-once"],
                    ["--minecraft-eula-accepted"]):
        dest = tmp_path / "never-created"
        assert boot.main([
            "--jar", str(tmp_path / "missing.jar"),
            "--output-dir", str(dest),
            *options,
        ]) == 2
        assert not dest.exists()
        assert json.loads(capsys.readouterr().err)[
            "classification"
        ] == "RSEE_BOOTSTRAP_BLOCKED_NO_NEW_PROCESS"


@pytest.mark.parametrize("variant", ["valid", "seed", "rain", "cycle", "two_players"])
def test_stopped_world_native_state_is_from_saved_nbt(tmp_path, variant):
    parent = tmp_path / "server"
    world = _build_stopped(
        parent,
        seed=576 if variant == "seed" else 575,
        rainy=variant == "rain",
        freeze=variant != "cycle",
    )
    if variant == "two_players":
        (world / "playerdata" / "another.dat").write_bytes(_player_bytes())
    if variant == "valid":
        record = boot._saved_state(world)
        assert record["stored_player"]["rotation_yaw_pitch"][0] == pytest.approx(0.7)
        assert record["stored_player"]["health"] == pytest.approx(20)
        assert record["stored_player"]["food"] == 20
        assert record["stored_world"]["full_gamerules"]["doDaylightCycle"] == "false"
        assert bind._seed_from_level(world / "level.dat") == 575
    elif variant == "seed":
        # World metadata is independently validated by #581's verifier.
        assert bind._seed_from_level(world / "level.dat") == 576
    else:
        with pytest.raises(boot.BootstrapRejected):
            boot._saved_state(world)


def test_one_bootstrap_java_one_bridge_and_stop_before_snapshot(
    monkeypatch, tmp_path,
):
    out = tmp_path / "new-run"
    out.mkdir()
    jar = tmp_path / "minecraft.jar"
    jar.write_bytes(b"SYNTHETIC_TEST_JAR_NOT_REAL")
    monkeypatch.setattr(boot, "JAR_SHA256", bind._hash_file(jar))
    monkeypatch.setattr(bind, "JAR_SHA256", bind._hash_file(jar))
    # #581 verifier uses a fixed default (bound at definition time): explicitly
    # mock only its source artifact identity for the synthetic offline fixture.
    real_verify = boot.verify_world_binding

    def test_verify(file, snap, manifest, evidence):
        return real_verify(
            file, snap, manifest, evidence,
            expected_jar_sha256=bind._hash_file(jar),
        )

    monkeypatch.setattr(boot, "verify_world_binding", test_verify)
    launches = []
    commands = []
    shutdowns = []

    class _Stdin:
        async def drain(self):
            return None

    class _Server:
        stdin = _Stdin()
        returncode = None

    server = _Server()

    async def start_server(root, _jar, _log):
        launches.append("JAVA_ONCE")
        _build_stopped(root)
        return server, None, None

    monkeypatch.setattr(boot, "_ready_server", start_server)
    monkeypatch.setattr(boot, "_command", lambda _server, cmd: commands.append(cmd))

    class _FakeSession:
        async def shutdown(self, *, timeout_s):
            shutdowns.append("BRIDGE_CLEAN_STOP")
            return 0

        async def terminate(self):
            pytest.fail("no forced termination in successful fixture")

    async def fake_launch(*_args, **_kwargs):
        launches.append("NODE_ONCE")
        return _FakeSession()

    async def spawn(*_args, **_kwargs):
        return _Observation(1, "synthetic-session", "spawn")

    async def probe(*_args, **_kwargs):
        return _Observation(2, "synthetic-session", "probe")

    async def stop_server(_server, _collector):
        shutdowns.append("JAVA_CLEAN_STOP")
        server.returncode = 0

    monkeypatch.setattr(boot.MineflayerProcessSession, "launch", fake_launch)
    monkeypatch.setattr(boot, "_await_spawn", spawn)
    monkeypatch.setattr(boot, "_correlated_observe", probe)
    monkeypatch.setattr(boot, "_shutdown_server", stop_server)

    assert asyncio.run(boot._execute(jar, out)) == 0
    assert launches == ["JAVA_ONCE", "NODE_ONCE"]
    assert shutdowns == ["BRIDGE_CLEAN_STOP", "JAVA_CLEAN_STOP"]
    assert "gamerule doDaylightCycle false" in commands
    assert "time set midnight" in commands
    assert "weather clear 1000000" in commands
    receipt = json.loads((out / "bootstrap_receipt.json").read_text())
    assert receipt["status"] == "STOPPED_WORLD_BYTES_SEALED_PHYSICAL_AUDIT_PENDING"
    assert receipt["llm_post"] == 0 and receipt["self_actions"] == 0
    assert receipt["sealed"]["golden_run_performed"] is False
    assert receipt["sealed"]["stop_ack_inferred"] is False
    observation = json.loads((out / "initial_native_observation.json").read_text())
    assert observation["native_stopped_state"]["stored_player"][
        "rotation_yaw_pitch"
    ][0] == pytest.approx(0.7)
    assert (out / "snapshot" / "level.dat").is_file()
    assert (out / "snapshot_manifest.json").is_file()


def test_nonzero_java_exit_preserves_failure_without_snapshot(monkeypatch, tmp_path):
    out = tmp_path / "failed"
    out.mkdir()
    jar = tmp_path / "jar"
    jar.write_bytes(b"fake")
    stages = []

    class _Stdin:
        async def drain(self):
            return None

    class _Server:
        stdin = _Stdin()
        returncode = None

    server = _Server()

    async def start_server(root, _jar, _log):
        _build_stopped(root)
        return server, None, None

    async def fake_launch(*_args, **_kw):
        class _Session:
            async def shutdown(self, *, timeout_s):
                return 0
        return _Session()

    async def fake_observation(*_args, **_kw):
        if not stages:
            stages.append("spawn")
            return _Observation(1, "s", "spawn")
        return _Observation(2, "s", "probe")

    async def stop(_server, _collector):
        server.returncode = -9

    monkeypatch.setattr(boot, "_ready_server", start_server)
    monkeypatch.setattr(boot, "_command", lambda *_a: None)
    monkeypatch.setattr(boot.MineflayerProcessSession, "launch", fake_launch)
    monkeypatch.setattr(boot, "_await_spawn", fake_observation)
    monkeypatch.setattr(boot, "_correlated_observe", fake_observation)
    monkeypatch.setattr(boot, "_shutdown_server", stop)
    assert asyncio.run(boot._execute(jar, out)) == 1
    report = json.loads((out / "bootstrap_receipt.json").read_text())
    assert report["status"] == "BOOTSTRAP_TERMINAL_UNQUALIFIED"
    assert report["java_clean_exit_observed"] is False
    assert not (out / "snapshot_manifest.json").exists()
    assert (out / "server" / boot.LEVEL / "level.dat").exists()
