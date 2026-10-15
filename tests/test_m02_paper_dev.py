"""M0.2 Paper DEV source controls; no Minecraft/Java/network in these tests."""
from __future__ import annotations

import asyncio
import hashlib

import pytest

from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import (
    M02_CONFIRM,
    M02DevRejected,
    _fresh_asset,
    _port_free,
    _read_world_receipts,
    _sha256,
    run,
)


def test_hash_asset_requires_original_bytes(tmp_path):
    path = tmp_path / "paper-test.jar"
    path.write_bytes(b"paper-dev-just-test-bytes")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert _fresh_asset(path, sha) == path
    assert _sha256(path) == sha
    with pytest.raises(M02DevRejected, match="SHA256 mismatch"):
        _fresh_asset(path, "0" * 64)
    link = tmp_path / "symlink.jar"
    link.symlink_to(path)
    with pytest.raises(M02DevRejected, match="absolute unlinked"):
        _fresh_asset(link, sha)


def test_original_event_log_must_prove_walk_basal_and_plugin(tmp_path):
    log = tmp_path / "server.log"
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20 player=RelaySelf food=20 saturation=5 exhaustion=0.02\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=1.0E-4\n",
        encoding="utf-8",
    )
    report = _read_world_receipts(log)
    assert report["count_walk_logged"] == 1
    assert report["native_event_identity_independently_qualified"] is False
    log.write_text("M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=1.0E-4\n")
    with pytest.raises(M02DevRejected, match="startup/basal/WALK"):
        _read_world_receipts(log)
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
    )
    with pytest.raises(M02DevRejected, match="expected"):
        _read_world_receipts(log)


def test_absent_confirmation_prevents_java_and_creation(tmp_path):
    out = tmp_path / "new-world"
    rc = asyncio.run(run(
        out, tmp_path / "absent.jar", "0" * 64,
        tmp_path / "absent-plugin.jar", "1" * 64,
        confirmation="NOT_AUTHORIZED",
    ))
    assert rc == 2
    assert not out.exists()


def test_confirmation_is_typed_and_not_default():
    assert M02_CONFIRM == "M02-DEV-I-OWN-DISPOSABLE-PAPER-WORLD"
    assert callable(_port_free)
