"""Fresh four-armed Paper QUAL intake: no physical starts in tests."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev import s51_paper_v7_four_arm_qualification as four
from adapters.mineflayer.m02_paper_dev import s51_paper_v7_new_qualification as spent


@pytest.mark.parametrize(("arm", "mults"), sorted(four.ARMS.items()))
def test_four_grants_config_shas_and_arm_confirmations_are_unique(arm, mults):
    assert arm != "BASE_ON"
    assert mults in ((1, 1), (0, 1), (1, 0), (0, 0))
    assert four.GRANTS[arm] == f"USER_M02_V7_{arm}_20261017_ONCE"
    assert four.GRANTS[arm] != spent.GRANT
    assert four.CONFIRMS[arm] != spent.CONFIRM
    assert len(four.CONFIGS[arm]) == 64


def test_all_grant_ids_unique_with_consumed_base_and_config_isolated():
    assert len(set(four.GRANTS.values())) == 4
    assert len(set(four.CONFIRMS.values())) == 4
    assert len(set(four.CONFIGS.values())) == 4
    assert four.CONFIGS["SHAM_ON"] == spent.ASSET_PINS["config.yml"]


@pytest.mark.parametrize("arm", sorted(four.ARMS))
def test_bad_or_shared_authority_fails_before_world_or_creating_root(tmp_path: Path, arm):
    asset = tmp_path / "empty"
    asset.mkdir()
    out = tmp_path / "out"
    with pytest.raises(four.QualificationBlocked, match="confirmation"):
        asyncio.run(four.run(asset_root=asset, output_root=out,
                             arm=arm, confirm=spent.CONFIRM))
    assert not out.exists()


@pytest.mark.parametrize("arm", ("BASE_ON", "UNKNOWN", ""))
def test_base_grant_and_unregistered_profile_are_denied(tmp_path: Path, arm):
    with pytest.raises(four.QualificationBlocked, match="unregistered"):
        asyncio.run(four.run(asset_root=tmp_path, output_root=tmp_path / "out",
                             arm=arm, confirm="WRONG"))


@pytest.mark.parametrize("arm", sorted(four.ARMS))
def test_asset_preflight_rejects_absent_and_foreign_file(tmp_path: Path, arm):
    empty = tmp_path / "assets"
    empty.mkdir()
    with pytest.raises(four.QualificationBlocked):
        four.check_assets(empty, arm)
    for name in four.ASSET_NAMES:
        (empty / name).write_bytes(b"not the original SHA")
    with pytest.raises(four.QualificationBlocked, match="tampered"):
        four.check_assets(empty, arm)
