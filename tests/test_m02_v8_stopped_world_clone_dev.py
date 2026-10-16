"""S V8 stopped World DEV clone producer: pure offline negative controls."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev import v8_stopped_world_clone_dev as s


def source_world(tmp_path: Path) -> Path:
    root = tmp_path / "immutable-stopped-world"
    (root / "region").mkdir(parents=True)
    (root / "entities").mkdir()
    (root / "data").mkdir()
    (root / "level.dat").write_bytes(b"synthetic-NBT-not-an-actual-world")
    (root / "region" / "r.0.0.mca").write_bytes(b"synthetic-region")
    (root / "entities" / "r.0.0.mca").write_bytes(b"synthetic-entities")
    (root / "data" / "scoreboard.dat").write_bytes(b"synthetic-scoreboard")
    (root / "session.lock").write_bytes(b"synthetic-lock")
    return root


def do_clone(tmp_path, *, seed=62101, confirm=s.DEV_CONFIRM):
    root = source_world(tmp_path)
    output = tmp_path / "clones"
    return root, output, s.clone_stopped_world(
        root, output, seed=seed, confirm=confirm,
    )


def test_offline_clone_exact_full_bytes_and_explicit_dev_limit(tmp_path):
    original, output, result = do_clone(tmp_path)
    assert result["classification"] == s.CLASS
    assert result["mode"] == "DEV_ONLY"
    assert result["arms"] == list(s.ARMS)
    assert result["source_file_count"] == 5
    assert result["all_five_stopped_copies_byte_identical_to_source"]
    assert not result["paper_producer_stop_attested"]
    assert not result["engineering_qualification"]
    assert result["science_grant"] is None
    assert result["v8_science_trials_credited"] == 0
    assert not result["science_go"]
    assert not result["production_go"]
    expected = s.world_index(original)
    assert len({str((output / arm).resolve()) for arm in s.ARMS}) == 5
    for arm in s.ARMS:
        assert s.world_index(output / arm) == expected
    assert json.loads((output / "source-clone-producer.json").read_text()) == result
    assert all(not (original / name).is_symlink() for name in
               ("level.dat", "session.lock"))


@pytest.mark.parametrize("seed", [61021, 62100, 62109, True, -1, 0])
def test_refuse_any_seed_outside_v8(seed, tmp_path):
    original = source_world(tmp_path)
    output = tmp_path / "candidate"
    with pytest.raises(s.CloneDevRejected, match="seed"):
        s.clone_stopped_world(
            original, output, seed=seed, confirm=s.DEV_CONFIRM,
        )
    assert not output.exists()


def test_requires_explicit_dev_scope(tmp_path):
    original = source_world(tmp_path)
    output = tmp_path / "clones"
    with pytest.raises(s.CloneDevRejected, match="confirmation"):
        s.clone_stopped_world(original, output, seed=62101, confirm="SCIENCE")
    assert not output.exists()


def test_existing_or_overlapping_source_or_output_rejected_before_writing(tmp_path):
    original = source_world(tmp_path)
    with pytest.raises(s.CloneDevRejected):
        s.clone_stopped_world(original, original, seed=62101,
                              confirm=s.DEV_CONFIRM)
    with pytest.raises(s.CloneDevRejected, match="nested"):
        s.clone_stopped_world(
            original, original / "clones", seed=62101, confirm=s.DEV_CONFIRM,
        )
    output = tmp_path / "occupied"
    output.mkdir()
    with pytest.raises(s.CloneDevRejected, match="fresh"):
        s.clone_stopped_world(original, output, seed=62101,
                              confirm=s.DEV_CONFIRM)


def test_source_symlink_and_forged_nonworld_rejected(tmp_path):
    original = source_world(tmp_path)
    (original / "data" / "alias.dat").symlink_to(original / "level.dat")
    with pytest.raises(s.CloneDevRejected, match="symlink"):
        s.clone_stopped_world(
            original, tmp_path / "clones", seed=62101, confirm=s.DEV_CONFIRM,
        )
    (original / "data" / "alias.dat").unlink()
    (original / "region" / "r.0.0.mca").unlink()
    with pytest.raises(s.CloneDevRejected, match="terrain"):
        s.clone_stopped_world(
            original, tmp_path / "clones", seed=62101, confirm=s.DEV_CONFIRM,
        )


def test_copy_error_does_not_damage_original_or_leave_half_copy(tmp_path, monkeypatch):
    original = source_world(tmp_path)
    original_index = s.world_index(original)
    output = tmp_path / "clones"
    real_copy = shutil.copytree
    seen = 0

    def fail_third(src, dest, *args, **kwargs):
        nonlocal seen
        seen += 1
        if seen == 3:
            raise OSError("synthetic io error")
        return real_copy(src, dest, *args, **kwargs)

    monkeypatch.setattr(s.shutil, "copytree", fail_third)
    with pytest.raises(OSError, match="synthetic io"):
        s.clone_stopped_world(
            original, output, seed=62101, confirm=s.DEV_CONFIRM,
        )
    assert not output.exists()
    assert s.world_index(original) == original_index


def test_candidate_modification_after_copy_does_not_edit_source(tmp_path):
    original, out, result = do_clone(tmp_path)
    old = s.world_index(original)
    assert result["source_file_count"] == 5
    (out / "WALK_ZERO" / "region" / "r.0.0.mca").write_bytes(b"changed")
    assert s.world_index(out / "WALK_ZERO") != old
    assert s.world_index(original) == old


def test_fixed_paper_properties_prohibit_open_world_and_mobs():
    settings = s._server_properties(62101).decode("ascii")
    assert "server-ip=127.0.0.1" in settings
    assert "online-mode=false" in settings
    assert "difficulty=hard" in settings
    assert "level-type=minecraft:normal" in settings
    assert "level-seed=62101" in settings
    assert "spawn-monsters=false" in settings
    assert "spawn-animals=false" in settings
    assert "spawn-npcs=false" in settings
    assert "level-name=world" in settings
    assert settings.count("level-seed=") == 1


def test_cli_source_copy_is_offline_and_does_not_create_science(tmp_path, capsys, monkeypatch):
    import sys

    original = source_world(tmp_path)
    output = tmp_path / "five"
    monkeypatch.setattr(sys, "argv", [
        "v8-stopped-dev", "--source", str(original), "--output", str(output),
        "--seed", "62101", "--confirm", s.DEV_CONFIRM,
    ])
    assert s.main() == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["classification"] == s.CLASS
    assert verdict["v8_science_trials_credited"] == 0
    assert not verdict["science_go"]
    monkeypatch.setattr(sys, "argv", [
        "v8-stopped-dev", "--source", str(original), "--output", str(output),
        "--seed", "62101", "--confirm", s.DEV_CONFIRM,
    ])
    assert s.main() == 2
    assert json.loads(capsys.readouterr().out)["science_go"] is False
