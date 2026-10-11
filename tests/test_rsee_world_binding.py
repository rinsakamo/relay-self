"""RSEE stopped-World source tests: synthetic NBT, no Java/LLM/World process."""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import struct
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo
from experiments.standard_env import world_binding as world


def _named(name: str) -> bytes:
    encoded = name.encode("utf-8")
    return struct.pack(">H", len(encoded)) + encoded


def _level(seed=575) -> bytes:
    # Exactly what the offline NBT reader needs: nested compound native long.
    inner = b"\x04" + _named("seed") + struct.pack(">q", seed) + b"\x00"
    generation = b"\x0a" + _named("WorldGenSettings") + inner
    data = b"\x0a" + _named("Data") + generation + b"\x00"
    return gzip.compress(b"\x0a" + _named("") + data + b"\x00", mtime=0)


def _fixture(tmp_path, *, seed=575):
    jar = tmp_path / "minecraft-1.21.8.jar"
    jar.write_bytes(b"SYNTHETIC_JAR_NOT_MOJANG")
    root = tmp_path / "stopped-world"
    root.mkdir()
    (root / "level.dat").write_bytes(_level(seed))
    region = root / "region"
    region.mkdir()
    (region / "r.0.0.mca").write_bytes(b"synthetic region")
    evidence = tmp_path / "synthetic-initial-observation.json"
    evidence.write_text('{"source":"synthetic-not-physically-attested"}')
    manifest = tmp_path / "manifest.json"
    jar_sha = world._hash_file(jar)
    document = {
        "schema": world.SCHEMA, "minecraft_version": "1.21.8",
        "level_name": world.LEVEL, "seed": 575,
        "jar_sha256": jar_sha,
        "initial_evidence_sha256": world._hash_file(evidence),
        "files": [
            {"path": name, "size": size, "sha256": digest}
            for name, size, digest in world._world_files(root)
        ],
    }
    manifest.write_text(json.dumps(document, sort_keys=True))
    return jar, root, manifest, evidence, jar_sha


def test_seed_read_from_native_nbt_not_manifest(tmp_path):
    path = tmp_path / "level.dat"
    path.write_bytes(_level(575))
    assert world._seed_from_level(path) == 575
    path.write_bytes(_level(576))
    assert world._seed_from_level(path) == 576


def test_stopped_snapshot_copy_exact_with_frozen_seed_and_no_source_mutation(tmp_path):
    jar, root, manifest, evidence, jar_sha = _fixture(tmp_path)
    original = world._world_files(root)
    binding = world.verify_world_binding(
        jar, root, manifest, evidence, expected_jar_sha256=jar_sha,
    )
    assert binding.files == original
    fresh = tmp_path / "fresh-temporary"
    fresh.mkdir()
    with pytest.raises(world.WorldBindingRejected, match="EULA"):
        world.prepare_stopped_world(fresh, binding, eula_accepted=False)
    assert list(fresh.iterdir()) == []
    result = world.prepare_stopped_world(fresh, binding, eula_accepted=True)
    assert result["snapshot_bytes_verified"] is True
    assert result["native_initial_world_attested"] is False
    assert result["world_launched"] is False
    assert result["physical_execution_authorized"] is False
    assert world._world_files(fresh / world.LEVEL) == original
    assert world._world_files(root) == original
    assert world._hash_file(fresh / "minecraft.jar") == jar_sha
    conf = (fresh / "server.properties").read_text()
    assert conf.count("level-seed=575\n") == 1
    assert "level-name=s31a-ephemeral\n" in conf
    assert "level-type=minecraft:flat\n" in conf
    assert (fresh / "eula.txt").read_text() == "eula=true\n"
    with pytest.raises(world.WorldBindingRejected, match="destination"):
        world.prepare_stopped_world(fresh, binding, eula_accepted=True)


@pytest.mark.parametrize("change", [
    "wrong_seed", "jar", "region", "additional_file", "evidence",
    "manifest_wrong_seed", "manifest_extra_field", "symlink", "no_level",
])
def test_byte_or_provenance_drift_fails_closed(tmp_path, change):
    jar, root, manifest, evidence, jar_sha = _fixture(tmp_path)
    if change == "wrong_seed":
        (root / "level.dat").write_bytes(_level(576))
    elif change == "jar":
        jar.write_bytes(b"substituted jar")
    elif change == "region":
        (root / "region" / "r.0.0.mca").write_bytes(b"unbound region")
    elif change == "additional_file":
        (root / "unexpected.dat").write_bytes(b"not recorded")
    elif change == "evidence":
        evidence.write_bytes(b"wrong initial evidence")
    elif change.startswith("manifest_"):
        data = json.loads(manifest.read_text())
        if change == "manifest_wrong_seed":
            data["seed"] = 576
        else:
            data["new_qualification"] = True
        manifest.write_text(json.dumps(data))
    elif change == "symlink":
        (root / "region" / "linked").symlink_to(root / "level.dat")
    elif change == "no_level":
        (root / "level.dat").unlink()
    with pytest.raises(world.WorldBindingRejected):
        world.verify_world_binding(
            jar, root, manifest, evidence, expected_jar_sha256=jar_sha,
        )


def test_snapshot_change_after_binding_blocks_before_copy(tmp_path):
    jar, root, manifest, evidence, jar_sha = _fixture(tmp_path)
    binding = world.verify_world_binding(
        jar, root, manifest, evidence, expected_jar_sha256=jar_sha,
    )
    (root / "region" / "r.0.0.mca").write_bytes(b"tampered between gates")
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    with pytest.raises(world.WorldBindingRejected):
        world.prepare_stopped_world(fresh, binding, eula_accepted=True)
    assert list(fresh.iterdir()) == []


def test_rsee_requires_snapshot_and_independent_eula_before_any_native_run(
    tmp_path, monkeypatch, capsys,
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("no Java/Node/server/LLM on missing World evidence")

    monkeypatch.setattr(self_demo.shutil, "which", forbidden)
    for add, reason in (
        ([], "RSEE_WORLD_INPUT_OR_EULA_MISSING"),
        (["--rsee-eula-accepted"], "RSEE_WORLD_INPUT_OR_EULA_MISSING"),
    ):
        args = [
            "--run-disposable", "--confirm", self_demo.CONFIRM,
            "--output-dir", str(tmp_path), "--live-think", "--rsee-standard",
            "--model-alias", "fake", "--model-port", "1234",
            *add,
        ]
        assert self_demo.main(args) == 2
        assert json.loads(capsys.readouterr().out)["reason"] == reason


def test_s49_rsee_uses_checked_world_and_skips_original_download(tmp_path, monkeypatch):
    from adapters.mineflayer import s49_normal_session_real_ci as s49
    from adapters.mineflayer.s31a_real_server_ci import S31ABlocked

    jar, root, manifest, evidence, jar_sha = _fixture(tmp_path)
    binding = world.verify_world_binding(
        jar, root, manifest, evidence, expected_jar_sha256=jar_sha,
    )
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")

    def forbidden(*_args, **_kwargs):
        pytest.fail("RSEE must not fetch Mojang jar, issue Action or run Node")

    monkeypatch.setattr(s49, "_fetch_official_server", forbidden)
    monkeypatch.setattr(s49, "_new_session", forbidden)
    seen = []

    async def observe_staged_world_and_stop(before_java, jar_path, _log):
        assert world._hash_file(jar_path) == jar_sha
        assert world._world_files(before_java / world.LEVEL) == binding.files
        assert "level-seed=575" in (before_java / "server.properties").read_text()
        seen.append("PRE_JAVA_BYTES_VERIFIED")
        raise S31ABlocked("simulated stop, Java NOT started")

    monkeypatch.setattr(s49, "_ready_server", observe_staged_world_and_stop)
    report_path = tmp_path / "native.json"
    rc = asyncio.run(s49.qualify(
        report_path, tmp_path / "java.log", rsee_world=binding,
        rsee_eula_accepted=True,
    ))
    assert rc == 2 and seen == ["PRE_JAVA_BYTES_VERIFIED"]
    report = json.loads(report_path.read_text())
    assert report["status"] == "BLOCKED"
    assert report["rsee_world_binding"]["world_launched"] is False
    assert report["actual_native_actions"] == []


def test_stopped_world_manifest_source_is_not_qualification(tmp_path):
    jar, root, manifest, evidence, jar_sha = _fixture(tmp_path)
    binding = world.verify_world_binding(
        jar, root, manifest, evidence, expected_jar_sha256=jar_sha,
    )
    assert binding.manifest_sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert binding.initial_evidence_sha256 == hashlib.sha256(
        evidence.read_bytes()
    ).hexdigest()
    # Even perfect byte matching cannot certify physical acquisition or consent.
    assert binding.files and not hasattr(binding, "physical_execution_authorized")
