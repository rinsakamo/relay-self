"""#860 stage 12: safe real-Paper runner preflight (no Minecraft process in CI)."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import pytest

from experiments.p0d_real_paper_smoke_dev import (
    RealPaperSmokeRefusal,
    _wait_log,
    _world_manifest,
    _world_uuid,
    prepare_assets,
    run_real_paper_smoke,
)


def test_missing_plugin_ready_holds(tmp_path):
    log = tmp_path / "paper.log"
    with log.open("wb") as output:
        proc = subprocess.Popen(
            (sys.executable, "-u", "-c", "import time; print('Done (',flush=True); time.sleep(1)"),
            stdout=output,
        )
    try:
        with pytest.raises(RealPaperSmokeRefusal, match="timed out"):
            _wait_log(proc, log, markers=(b"Done (", b"P0D_TICK_READY"), timeout_s=0.2)
    finally:
        proc.wait(timeout=3)


def _jar(
    path: Path, *, paper: bool = False, witness: bool = True,
    resident_witness: bool = True,
) -> str:
    with zipfile.ZipFile(path, "w") as jar:
        if paper:
            jar.writestr("META-INF/MANIFEST.MF", "Main-Class: io.papermc.paperclip.Paperclip\n")
        else:
            jar.writestr("plugin.yml", "name: P0BRecorder\nversion: dev\n")
            jar.writestr("io/github/rinsakamo/p0b/Recorder.class", b"stub")
            if witness:
                jar.writestr("io/github/rinsakamo/p0b/TickWitness.class", b"stub")
            if resident_witness:
                jar.writestr("io/github/rinsakamo/p0b/ResidentPresenceWitness.class", b"stub")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resources(tmp_path):
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / "P0BRecorder.jar"
    return paper, _jar(paper, paper=True), plugin, _jar(plugin)


def test_no_operator_eula_confirmation_never_creates_world(tmp_path):
    paper, sha, plugin, plugin_sha = _resources(tmp_path)
    with pytest.raises(RealPaperSmokeRefusal, match="explicitly accept"):
        run_real_paper_smoke(
            paper_jar=paper, paper_sha256=sha,
            plugin_jar=plugin, plugin_sha256=plugin_sha,
            scratch_parent=tmp_path, accepted_eula=False,
        )
    assert not list(tmp_path.glob("p0d-real-paper-only-*"))
    assert not (tmp_path / "eula.txt").exists()


@pytest.mark.parametrize(("fault", "expected"), [
    ("paper-sha", "SHA256"),
    ("plugin-sha", "SHA256"),
    ("missing-witness", "Paper tick witness plugin not compiled"),
    ("missing-resident-witness", "Paper resident presence witness plugin not compiled"),
    ("missing-eula", "explicitly accept"),
])
def test_preflight_fail_closed_before_any_process(tmp_path, fault, expected):
    paper, sha, plugin, plugin_sha = _resources(tmp_path)
    if fault == "paper-sha":
        sha = "0" * 64
    if fault == "plugin-sha":
        plugin_sha = "0" * 64
    if fault == "missing-witness":
        plugin_sha = _jar(plugin, witness=False)
    if fault == "missing-resident-witness":
        plugin_sha = _jar(plugin, resident_witness=False)
    with pytest.raises(RealPaperSmokeRefusal, match=expected):
        prepare_assets(
            paper_jar=paper, paper_sha256=sha,
            plugin_jar=plugin, plugin_sha256=plugin_sha,
            scratch_parent=tmp_path, accepted_eula=fault != "missing-eula",
        )
    assert not list(tmp_path.glob("p0d-real-paper-only-*"))


def test_preflight_only_returns_exact_jar_paths_without_start(tmp_path):
    paper, sha, plugin, plugin_sha = _resources(tmp_path)
    result = prepare_assets(
        paper_jar=paper, paper_sha256=sha,
        plugin_jar=plugin, plugin_sha256=plugin_sha,
        scratch_parent=tmp_path, accepted_eula=True,
    )
    assert result == (paper.resolve(), plugin.resolve(), tmp_path.resolve())
    assert not list(tmp_path.glob("p0d-real-paper-only-*"))


def test_real_paper_smoke_rejects_symlinked_source(tmp_path):
    paper, sha, plugin, plugin_sha = _resources(tmp_path)
    link = tmp_path / "link.jar"
    link.symlink_to(paper)
    with pytest.raises(RealPaperSmokeRefusal, match="source"):
        prepare_assets(
            paper_jar=link, paper_sha256=sha,
            plugin_jar=plugin, plugin_sha256=plugin_sha,
            scratch_parent=tmp_path, accepted_eula=True,
        )


def test_world_uuid_and_all_present_dimension_files_hashed(tmp_path):
    original = uuid.uuid4()
    world = tmp_path / "world"
    world.mkdir()
    (world / "uid.dat").write_bytes(original.bytes)
    (world / "level.dat").write_bytes(b"NBT")
    nether = tmp_path / "world_nether"
    nether.mkdir()
    (nether / "region").mkdir()
    (nether / "region" / "r.0.0.mca").write_bytes(b"region")
    assert _world_uuid(world) == str(original)
    snapshot = _world_manifest(tmp_path)
    assert set(snapshot) == {
        "world/uid.dat", "world/level.dat",
        "world_nether/region/r.0.0.mca",
    }
    (world / "region").symlink_to(nether / "region")
    with pytest.raises(RealPaperSmokeRefusal, match="symlink"):
        _world_manifest(tmp_path)


def test_malformed_world_uuid_refused_as_no_paper_source(tmp_path):
    root = tmp_path / "world"
    root.mkdir()
    (root / "uid.dat").write_bytes(b"not-a-uuid")
    with pytest.raises(RealPaperSmokeRefusal, match="exactly 16"):
        _world_uuid(root)



def test_only_official_reviewed_paper_build_can_be_launched(tmp_path):
    paper, sha, plugin, plugin_sha = _resources(tmp_path)
    with pytest.raises(RealPaperSmokeRefusal, match="only pinned official Paper"):
        run_real_paper_smoke(
            paper_jar=paper, paper_sha256=sha,
            plugin_jar=plugin, plugin_sha256=plugin_sha,
            scratch_parent=tmp_path, accepted_eula=True,
        )
    # This test does not accept a fake Paper binary or create a World.
    assert not list(tmp_path.glob("p0d-real-paper-only-*"))
