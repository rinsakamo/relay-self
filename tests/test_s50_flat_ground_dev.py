"""V8 separate FLAT-DEV Paper World: offline isolation and adversarial controls."""
from __future__ import annotations

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_ground_dev as flat


def test_separate_superflat_not_natural_v8_source():
    props = flat.properties().decode()
    assert "level-type=minecraft:flat\n" in props
    assert "level-seed=63101\n" in props
    assert "level-type=minecraft:normal" not in props
    assert "level-seed=62101" not in props
    assert "spawn-monsters=false" in props
    assert "spawn-animals=false" in props
    assert "spawn-npcs=false" in props
    assert "difficulty=hard" in props
    assert "gamemode=survival" in props
    assert "server-ip=127.0.0.1" in props
    assert "online-mode=false" in props
    assert props.count("level-type=") == props.count("level-seed=") == 1
    assert flat.FLAT_DEV_SEED not in tuple(range(62101, 62109))


def test_native_grid_requires_real_grass_under_and_air_above():
    cmds = flat.native_surface_commands()
    assert len(cmds) == 25
    assert len({marker for marker, _ in cmds}) == 25
    assert all("execute in minecraft:overworld" in cmd for _, cmd in cmds)
    assert all("if block" in cmd and "minecraft:grass_block" in cmd
               and cmd.count("minecraft:air") == 2 for _, cmd in cmds)
    assert all(f" {flat.GROUND_Y} " in cmd for _, cmd in cmds)
    assert all(f" {flat.PLAYER_FEET_Y} " in cmd for _, cmd in cmds)
    assert any("if block 4 -61 0" in cmd for _, cmd in cmds)


def test_source_log_ack_must_be_real_server_chat_line():
    marks = [m for m, _ in flat.native_surface_commands()]
    log = "".join(f"[12:00] [Server thread/INFO]: [Server] {m}\n" for m in marks)
    assert flat.extract_native_witnesses(log) == set(marks)
    assert flat.extract_native_witnesses(
        "\n".join("sent command run say " + marker for marker in marks)) == set()
    assert flat.extract_native_witnesses(
        "\n".join("[Server] " + marker for marker in marks[:23])) == set(marks[:23])
    assert flat.extract_native_witnesses("") == set()


@pytest.mark.parametrize("bad", ["", "SCIENCE", "V8-FIVE-WORLD-DEV-ONLY"])
def test_preflight_forbids_other_modes_without_creating_world(tmp_path, bad):
    paper = tmp_path / "paper.jar"
    paper.write_bytes(b"not a real official binary")
    target = tmp_path / "new"
    with pytest.raises(ValueError, match="confirmation"):
        flat.preflight(paper, target, bad)
    assert not target.exists()


def test_preflight_rejects_forged_jar_before_world(tmp_path):
    paper = tmp_path / "paper.jar"
    paper.write_bytes(b"fake")
    target = tmp_path / "new"
    with pytest.raises(ValueError, match="pinned Paper"):
        flat.preflight(paper, target, flat.CONFIRM)
    assert not target.exists()


def test_preflight_rejects_overwritten_root_and_symlink(tmp_path, monkeypatch):
    paper = tmp_path / "paper.jar"
    paper.write_bytes(b"fixture")
    monkeypatch.setattr(flat, "sha", lambda p: flat.PAPER_JAR_SHA256)
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(ValueError, match="isolated absolute"):
        flat.preflight(paper, existing, flat.CONFIRM)
    link = tmp_path / "paper-link.jar"
    link.symlink_to(paper)
    with pytest.raises(ValueError, match="pinned Paper"):
        flat.preflight(link, tmp_path / "new", flat.CONFIRM)
    assert paper.read_bytes() == b"fixture"


def test_flat_recipe_proves_nothing_about_foraging_or_v8_admission(tmp_path):
    """No Java needed to prove receipt shape and disjoint future authority."""
    assert flat.CLASSIFICATION.endswith("NOT_QUALIFIED")
    assert flat.CONFIRM != "V8-FIVE-WORLD-DEV-ONLY"
    assert flat.CONFIRM != "V8-DEV-ISOLATED-PAPER-STOPPED-CLONES-ONLY"
    assert len(flat.GROUND_POINTS) == 25
    assert flat.PLAYER_FEET_Y > flat.GROUND_Y


def test_cli_rejects_bad_credentials_with_no_java(tmp_path, monkeypatch, capsys):
    import json
    import sys

    p = tmp_path / "fake.jar"
    p.write_bytes(b"fake")
    dest = tmp_path / "world"
    monkeypatch.setattr(sys, "argv", [
        "flat", "--paper-jar", str(p), "--output", str(dest),
        "--confirm", "SCIENCE",
    ])
    assert flat.main() == 2
    data = json.loads(capsys.readouterr().out)
    assert data["classification"] == "S50_FLAT_DEV_PREFLIGHT_REJECTED"
    assert data["v8_science_trials"] == 0 and data["science_go"] is False
    assert not dest.exists()


def test_native_surface_commands_do_not_execute_until_authorized(tmp_path):
    # Test never starts native Paper, Minecraft, Node, Mineflayer or LLM.
    lines = [cmd for _, cmd in flat.native_surface_commands()]
    assert all("minecraft:cooked_beef" not in cmd for cmd in lines)
    assert all("summon " not in cmd for cmd in lines)
    assert all("setblock " not in cmd and "fill " not in cmd for cmd in lines)
    assert all("tp " not in cmd for cmd in lines)
    assert all("minecraft:stone" not in cmd for cmd in lines)
