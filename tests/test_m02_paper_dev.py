"""M0.2 Paper DEV source controls; no Minecraft/Java/network in these tests."""
from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev import (
    M02_CONFIRM,
    M02DevRejected,
    PAPER_PREWORLD_ASSET_PINS,
    PAPER_PREWORLD_PROFILE,
    main,
    qualification_asset_preflight,
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
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.006 "
        "cumulative_blocks=0.6 cumulative_billed=0.006\n",
        encoding="utf-8",
    )
    report = _read_world_receipts(log)
    assert report["count_walk_native_events"] == 1
    assert report["count_walk_motion_packets"] == 1
    assert report["world_measured_walk_blocks"] == pytest.approx(0.6)
    assert report["world_billed_walk_exhaustion"] == pytest.approx(0.006)
    assert report["native_event_identity_independently_qualified"] is False
    log.write_text("M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n")
    with pytest.raises(M02DevRejected, match="startup/basal/WALK"):
        _read_world_receipts(log)
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=1.0E-4\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.006\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="replaced by zero"):
        _read_world_receipts(log)
    log.write_text(
        "M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "M02_DEV_BODY sampled_tick=20\n"
        "M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.0\n"
        "M02_DEV_MOTION id=1 reason=WALK blocks=0.6 billed=0.001\n",
        encoding="utf-8",
    )
    with pytest.raises(M02DevRejected, match="differs from measured path"):
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


def _synthetic_preworld_assets(root, monkeypatch):
    import adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev as s
    root.mkdir()
    content = {
        "paper-1.21.8.jar": b"fixture-paper-jar",
        "relay-metabolism-paper-dev.jar": b"fixture-plugin-jar",
        "config.yml": b"dev-enabled: true\\ntarget-player: RelaySelf\\n",
        "server.properties": b"online-mode=false\\ngamemode=survival\\n",
    }
    hashes = {}
    for name, data in content.items():
        (root / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(s, "PAPER_PREWORLD_ASSET_PINS", hashes)
    return hashes


def test_qualification_asset_preworld_read_only_with_honest_ceiling(tmp_path, monkeypatch, capsys):
    root = tmp_path / "new-only-four-assets"
    digests = _synthetic_preworld_assets(root, monkeypatch)
    result = qualification_asset_preflight(root)
    assert result["preworld_profile"] == PAPER_PREWORLD_PROFILE
    assert result["verified_assets_sha256"] == digests
    assert result["new_paper_world"] == "NOT_CREATED"
    assert result["new_world_snapshot_seed"] == "NOT_BOUND"
    assert result["physical_world_launches"] == 0
    assert result["qualified"] is False
    assert not result["science_go"] and not result["production_go"]
    assert main(["--qualification-preflight", "--asset-root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["qualified"] is False
    assert set(p.name for p in root.iterdir()) == set(digests)


def test_qualification_preworld_rejects_tamper_extra_symlink_and_unpinned(tmp_path, monkeypatch):
    root = tmp_path / "four"
    _synthetic_preworld_assets(root, monkeypatch)
    (root / "extra").write_bytes(b"not included")
    with pytest.raises(M02DevRejected, match="exact four"):
        qualification_asset_preflight(root)
    (root / "extra").unlink()
    plugin = root / "relay-metabolism-paper-dev.jar"
    plugin.write_bytes(b"modified")
    with pytest.raises(M02DevRejected, match="non-pinned"):
        qualification_asset_preflight(root)
    plugin.unlink()
    plugin.symlink_to(root / "paper-1.21.8.jar")
    with pytest.raises(M02DevRejected, match="unsafe"):
        qualification_asset_preflight(root)
    plugin.unlink()
    # An unpinned brand-new directory never authorizes a Java start.
    assert main(["--qualification-preflight", "--asset-root", str(root)]) == 2


def test_qualification_preflight_and_dev_cli_never_mix(tmp_path):
    with pytest.raises(SystemExit):
        main(["--qualification-preflight", "--asset-root", str(tmp_path),
              "--confirm", M02_CONFIRM])
    with pytest.raises(SystemExit):
        main(["--asset-root", str(tmp_path)])
    assert len(PAPER_PREWORLD_ASSET_PINS) == 4
