"""Fresh M0.2 V7 BASE_ON one-shot: no old consumed grant, prelaunch negatives."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev import (
    s51_paper_v7_new_qualification as q,
    s51_paper_qualification as old,
)


def test_new_auth_and_all_four_sources_are_exact_and_independent():
    assert q.GRANT == "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE"
    assert q.GRANT != old.GRANT
    assert q.CONFIRM != old.CONFIRM
    assert q.SEED == "61021"
    assert q.ASSET_PINS["relay-metabolism-paper-dev.jar"] == (
        "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f"
    )
    assert q.ASSET_PINS["config.yml"] == (
        "939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16"
    )
    assert q.ASSET_PINS["relay-metabolism-paper-dev.jar"] != (
        old.dev.PAPER_PREWORLD_ASSET_PINS["relay-metabolism-paper-dev.jar"]
    )
    assert q.ASSET_NAMES == {
        "paper-1.21.8.jar", "relay-metabolism-paper-dev.jar",
        "config.yml", "server.properties",
    }


def test_wrong_confirmation_refuses_before_output_or_world(tmp_path: Path):
    root = tmp_path / "untrusted"
    root.mkdir()
    target = tmp_path / "new-qual"
    with pytest.raises(q.QualificationBlocked, match="confirmation"):
        asyncio.run(q.run(
            asset_root=root, output_root=target, confirm=old.CONFIRM))
    assert not target.exists()


def test_foreign_or_tampered_assets_refused(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(q.QualificationBlocked):
        q.check_assets(empty)
    for name in q.ASSET_NAMES:
        (empty / name).write_bytes(b"not the qualified SHA")
    with pytest.raises(q.QualificationBlocked, match="tampered"):
        q.check_assets(empty)
    (empty / "fifth-extra").write_text("foreign", encoding="utf-8")
    with pytest.raises(q.QualificationBlocked, match="four-asset"):
        q.check_assets(empty)


def test_preserved_old_separate_grant_source():
    assert old.GRANT == "USER_M02_PAPER_QUALIFICATION_20261015_THIRD_ONCE"
    assert q.GRANT not in old.CONFIRM
