"""L11: original G413 Action/Goal/T2 source ZIP audit (no Minecraft IO)."""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest

from adapters.mineflayer.l11_saved_real_goal_originals_dev import (
    ARTIFACT_ID,
    PINNED,
    L11OriginalRejected,
    audit_l11_g413_saved_originals,
    main,
)


@pytest.fixture(scope="module")
def real_original_zip() -> Path:
    """Existing real G413 artifact, never a simulated 'real' JSON fixture."""
    original = os.environ.get("L11_REAL_ORIGINAL_ZIP")
    if not original:
        pytest.skip("real historical artifact was not supplied to this local check")
    path = Path(original)
    assert path.is_absolute() and path.is_file(), "explicit real ZIP input required"
    return path


def test_missing_original_path_does_not_create_goal_labels(capsys):
    assert main([]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["classification"] == "L11_ORIGINAL_BYTES_NOT_SUPPLIED"
    assert status["verified_originals"] == 0
    assert status["action_goal_labels_admitted"] == 0
    assert status["worlds_started"] == 0


def test_absent_or_wrong_raw_archive_refused(tmp_path):
    with pytest.raises(L11OriginalRejected):
        audit_l11_g413_saved_originals(tmp_path / "missing.zip")
    not_zip = tmp_path / "not-real.zip"
    not_zip.write_bytes(b"this-is-not-a-source-zip")
    with pytest.raises(L11OriginalRejected):
        audit_l11_g413_saved_originals(not_zip)
    with pytest.raises(L11OriginalRejected):
        audit_l11_g413_saved_originals(Path("relative-original.zip"))
    with pytest.raises(L11OriginalRejected):
        audit_l11_g413_saved_originals(None)


def test_g413_exact_saved_real_world_goal_only_not_per_action_reward(real_original_zip):
    result = audit_l11_g413_saved_originals(real_original_zip)
    assert result.artifact_id == ARTIFACT_ID == 12952335343
    assert result.producer_run_id == 40997098497
    assert result.original_s49_outcomes == 11
    assert result.original_t2_world_ticks == 182
    assert [w.source for w in result.worlds] == ["WORLD-G4", "WORLD-G413"]
    assert [w.original_s49_outcomes for w in result.worlds] == [5, 6]
    assert [w.original_t2_world_ticks for w in result.worlds] == [49, 133]
    assert len({w.session_id for w in result.worlds}) == 2
    assert all(w.final_goal_within_tolerance for w in result.worlds)
    assert all(w.last_action_not_final_probe for w in result.worlds)
    assert all(w.last_s16_seq < w.final_probe_seq for w in result.worlds)
    assert result.worlds[0].last_s16_within_tolerance is True
    # Important physical distinction: controlled last S16 is *outside* L1
    # tolerance, even though a later original final probe reaches the goal.
    assert result.worlds[1].last_s16_within_tolerance is False
    assert result.worlds[1].last_s16_goal_error_m > result.worlds[1].tolerance_m
    assert result.worlds[1].final_goal_error_m < result.worlds[1].tolerance_m
    assert [w.original_report_sha256 for w in result.worlds] == [
        PINNED["WORLD-G4/goal_report.json"],
        PINNED["WORLD-G413/goal_report.json"],
    ]
    assert result.source_file_hashes_match and result.world_goal_observed
    assert result.classification == "L11_REAL_ORIGINAL_WORLD_GOAL_ONLY_NO_ACTION_LABELS"
    assert result.action_goal_labels_admitted == 0
    assert result.l10_qualified_episode_pairs == 0
    assert not result.l10_current_world_body_cues_admitted
    assert result.s10_learning_updates == result.s11_habit_grants == 0
    assert result.action_issues == result.replayed_worlds == 0
    assert result.physical_learning_attested is False
    assert result.science_go is False
    assert all(not w.independent_per_action_goal_attested for w in result.worlds)
    assert all(not w.independent_native_source_authenticated for w in result.worlds)
    assert audit_l11_g413_saved_originals(real_original_zip) == result


def _modified(original: Path, target: Path, *, member: str, payload: bytes) -> Path:
    with zipfile.ZipFile(original, "r") as source:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as out:
            for name in source.namelist():
                out.writestr(name, payload if name == member else source.read(name))
    return target


@pytest.mark.parametrize("member", sorted(PINNED))
def test_real_original_any_report_or_t2_tamper_fails_closed(
    real_original_zip, tmp_path, member,
):
    with zipfile.ZipFile(real_original_zip) as z:
        original = z.read(member)
    altered = original[:-1] + (b" " if original[-1:] != b" " else b"\n")
    source = _modified(
        real_original_zip, tmp_path / "tampered.zip", member=member, payload=altered,
    )
    with pytest.raises(L11OriginalRejected, match="historical original SHA drift"):
        audit_l11_g413_saved_originals(source)


def test_original_partial_archive_is_not_reconstructed(real_original_zip, tmp_path):
    path = tmp_path / "missing-t2.zip"
    with zipfile.ZipFile(real_original_zip) as original, zipfile.ZipFile(path, "w") as z:
        for name in original.namelist():
            if name != "WORLD-G413/l1_t2_ledger_dev.json":
                z.writestr(name, original.read(name))
    with pytest.raises(L11OriginalRejected, match="missing"):
        audit_l11_g413_saved_originals(path)


def test_original_zip_duplicate_member_rejected(real_original_zip, tmp_path):
    path = tmp_path / "duplicate.zip"
    shutil.copyfile(real_original_zip, path)
    with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_DEFLATED) as z:
        with pytest.warns(UserWarning):
            z.writestr("WORLD-G4/goal_report.json", b"{}")
    with pytest.raises(L11OriginalRejected, match="duplicate"):
        audit_l11_g413_saved_originals(path)


def test_symlink_original_archive_rejected(real_original_zip, tmp_path):
    link = tmp_path / "symlink-source.zip"
    link.symlink_to(real_original_zip)
    with pytest.raises(L11OriginalRejected, match="regular"):
        audit_l11_g413_saved_originals(link)


def test_cli_raw_original_readback_does_not_write_or_promote(real_original_zip, capsys):
    before = real_original_zip.read_bytes()
    assert main(["--artifact-zip", str(real_original_zip)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["original_s49_outcomes"] == 11
    assert report["action_goal_labels_admitted"] == 0
    assert report["l10_qualified_episode_pairs"] == 0
    assert report["replayed_worlds"] == 0
    assert real_original_zip.read_bytes() == before
