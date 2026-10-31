"""Negative admission controls: no World may start on untrusted input."""
import json

import pytest

from adapters.mineflayer.m02_paper_dev import v8_five_world_dev as v8
from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import CloneDevRejected


def test_science_confirmation_cannot_enter_dev(tmp_path):
    with pytest.raises(CloneDevRejected, match="DEV confirmation"):
        v8.preflight(tmp_path, tmp_path, tmp_path, "0" * 64,
                     tmp_path / "fresh", "SCIENCE")
    assert not (tmp_path / "fresh").exists()


def test_existing_output_cannot_overwrite_evidence(tmp_path):
    with pytest.raises(CloneDevRejected, match="fresh absolute"):
        v8.preflight(tmp_path, tmp_path, tmp_path, "0" * 64,
                     tmp_path, v8.CONFIRM)


def test_wrong_jar_fails_before_output_or_launch(tmp_path):
    jar = tmp_path / "fake.jar"
    jar.write_bytes(b"not-Paper")
    with pytest.raises(v8.owner.M02DevRejected, match="SHA256 mismatch"):
        v8.preflight(tmp_path, jar, jar, "0" * 64,
                     tmp_path / "fresh", v8.CONFIRM)
    assert not (tmp_path / "fresh").exists()


def test_source_rows_do_not_invent_empty_ticks(tmp_path):
    p = tmp_path / "paper.log"
    p.write_text("[server] M02_DEV_MOTION id=1 blocks=0.5 billed=0.005\n")
    assert v8.source_rows(p, "M02_DEV_MOTION ") == [
        {"id": "1", "blocks": "0.5", "billed": "0.005"}]
    assert v8.source_rows(p, "M02_DEV_BASAL_WRITE ") == []


def test_original_writer_never_overwrites(tmp_path):
    p = tmp_path / "receipt.json"
    v8.write(p, {"original": True})
    with pytest.raises(FileExistsError):
        v8.write(p, {"replacement": True})
    assert json.loads(p.read_text()) == {"original": True}


def test_fixed_fixture_is_single_absolute_food_across_arms():
    assert v8.FOOD_XYZ == (-493.0, 67.2, -255.5)
    assert set(v8.ARMS) == {"BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO"}
    assert v8.ARMS["BASE_ON"] == v8.ARMS["SHAM_ON"]


@pytest.mark.parametrize("tamper", ["changed-clone", "missing-clone", "wrong-index"])
def test_archive_tampering_cannot_start_world(tmp_path, monkeypatch, tamper):
    import shutil

    from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import world_index
    from test_s50_v8_stopped_world_clone_dev import source_world

    archive = tmp_path / "archive"
    (archive / "v8-dev/isolated-server").mkdir(parents=True)
    original = source_world(archive / "v8-dev/isolated-server")
    original.rename(original.parent / "world")
    original = original.parent / "world"
    expected = world_index(original)
    clones = archive / "v8-dev/clones"
    clones.mkdir()
    for arm in v8.ARMS:
        shutil.copytree(original, clones / arm)
    v8.write(clones / "source-clone-producer.json", {
        "source_stopped_world_index": [] if tamper == "wrong-index" else expected})
    if tamper == "changed-clone":
        (clones / "WALK_ZERO/level.dat").write_bytes(b"tampered")
    if tamper == "missing-clone":
        shutil.rmtree(clones / "BOTH_ZERO")
    monkeypatch.setattr(v8, "LEVEL_SHA", v8.sha(original / "level.dat"))
    monkeypatch.setattr(v8.owner, "_fresh_asset", lambda *a: None)
    with pytest.raises(CloneDevRejected):
        v8.preflight(archive, tmp_path, tmp_path, "0" * 64,
                     tmp_path / "fresh", v8.CONFIRM)
    assert not (tmp_path / "fresh").exists()
