"""W4 TEST-only geometry and isolated ledger attacks; no external trust."""
from __future__ import annotations

import math
import shutil
import sqlite3
from dataclasses import replace

import pytest

import test_self_world_stage_s_feedback as sf
from adapters.mineflayer.python_protocol import MineflayerPosition, mineflayer_yaw_to_target
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
    W4SyntheticOrientation,
    external_trust_readout,
    plan_synthetic_nh1_placement,
    require_native_nh1_orientation,
)
from adapters.mineflayer.self_world_stage_w_gate import (
    StageWGateRejected,
    StageWPersistentGrantLedger,
)

pytest_plugins = ("test_self_world_stage_w_gate",)


def orientation():
    return W4SyntheticOrientation("synthetic-only", 5, MineflayerPosition(0, 64, 0), 0, 0)


@pytest.mark.parametrize("yaw", (0, math.pi/2, math.pi, -math.pi/2, 0.723))
@pytest.mark.parametrize("slot", (0, 1, 2))
def test_geometry(yaw, slot):
    o = replace(orientation(), yaw_rad=yaw, pitch_rad=0.4)
    result = plan_synthetic_nh1_placement(o, expected_session=o.session_id, before_seq=6, slot=slot)
    assert math.dist((o.position.x, o.position.z), (result.spawn.x, result.spawn.z)) == pytest.approx(10 if slot == 0 else 2)
    assert result.spawn.y == o.position.y
    if slot:
        actual = mineflayer_yaw_to_target(o.position, result.spawn)
        assert math.sin(actual) == pytest.approx(math.sin(yaw))
        assert math.cos(actual) == pytest.approx(math.cos(yaw))
    else:
        assert result.spawn == MineflayerPosition(10, 64, 0)
    assert result.command.startswith("summon minecraft:zombie ")
    assert not result.physical_run_permitted and not result.source_orientation_qualified


@pytest.mark.parametrize("case", ("absent", "foreign", "replayed", "nan", "pitch", "slot"))
def test_missing_or_wrong_source_blocks(case):
    o = orientation()
    kwargs = dict(expected_session=o.session_id, before_seq=6, slot=1)
    if case == "absent":
        o = None
    elif case == "foreign":
        kwargs["expected_session"] = "other"
    elif case == "replayed":
        kwargs["before_seq"] = 5
    elif case == "nan":
        o = replace(o, yaw_rad=math.nan)
    elif case == "pitch":
        o = replace(o, pitch_rad=2)
    else:
        kwargs["slot"] = 3
    with pytest.raises(W4PreworldBlocked):
        plan_synthetic_nh1_placement(o, **kwargs)


def test_current_native_source_and_external_trust_never_enable_live():
    witness = sf._synthetic_targeted_witness()
    with pytest.raises(W4PreworldBlocked, match="source-bound yaw/pitch"):
        require_native_nh1_orientation(witness.original_probe)
    assert external_trust_readout()["classification"] == "W4_EXTERNAL_TRUST_NO_GO"


@pytest.mark.parametrize("delta", (0.099, 0.100, 0.101, -0.099, -0.100, -0.101))
def test_unchanged_exact_stage_s_boundaries(delta):
    witness = sf._synthetic_targeted_witness(-delta, 0)
    result = sf.assess_stage_s_original_separation(witness, sf.StageSPredeclaredSeparationRule())
    # Compare the actual binary native distance subtraction, without rounding.
    actual = result.distance_after_m - result.distance_before_m
    expected = "INCREASE" if actual >= .100 else "DECREASE" if actual <= -.100 else "HOLD"
    assert result.direction.value.upper() == expected
    assert not result.s10_committed


def reserve(ledger, sample):
    ledger.reserve_once(sample["request"], issuer_fingerprint="TEST", archive_sha256=sample["archive_sha"])


@pytest.mark.parametrize("attack", ("symlink", "parent_symlink", "replacement", "hardlink", "mode", "missing"))
def test_ledger_path_attack_rejected(sample, tmp_path, attack):
    path = tmp_path / "spent.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    if attack == "parent_symlink":
        link = tmp_path / "alias"
        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(StageWGateRejected):
            StageWPersistentGrantLedger(link / path.name)
        return
    if attack == "mode":
        path.chmod(0o644)
    elif attack == "hardlink":
        (tmp_path / "hard").hardlink_to(path)
    else:
        saved = tmp_path / "saved.sqlite3"
        path.rename(saved)
        if attack == "symlink":
            path.symlink_to(saved)
        elif attack == "replacement":
            shutil.copyfile(saved, path)
            path.chmod(0o600)
    with pytest.raises(StageWGateRejected):
        reserve(ledger, sample)


def test_locked_ledger_denies_and_leaves_no_spend(sample, tmp_path):
    path = tmp_path / "locked.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(StageWGateRejected):
            reserve(ledger, sample)
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)


def test_disposable_rollback_clone_demonstrates_global_single_use_gap(sample, tmp_path):
    path = tmp_path / "original.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    clone = tmp_path / "clone.sqlite3"
    shutil.copy2(path, clone)  # Only a disposable TEST ledger, never historical evidence.
    reserve(ledger, sample)
    with pytest.raises(StageWGateRejected):
        reserve(ledger, sample)
    reserve(StageWPersistentGrantLedger(clone), sample)
    # This successful cloned reservation is a demonstrated qualification gap.
    for p in (path, clone):
        with sqlite3.connect(p) as connection:
            assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (1,)
    assert external_trust_readout()["global_ledger_single_use"] == "BLOCKED"


def test_disposable_process_crash_rolls_back_uncommitted_transaction(sample, tmp_path):
    import subprocess
    import sys

    path = tmp_path / "crash.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    code = """
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO grant_spent VALUES ('TEST','TEST','TEST','TEST','TEST','TEST','TEST')")
os._exit(23)
"""
    result = subprocess.run([sys.executable, "-c", code, str(path)], timeout=15)
    assert result.returncode == 23
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT COUNT(*) FROM grant_spent").fetchone() == (0,)
    reserve(ledger, sample)


def test_source_scope_tampering_denied_even_with_new_local_hash(sample, tmp_path):
    import hashlib
    import json

    from adapters.mineflayer.self_world_stage_w_archive import canonical
    from test_self_world_stage_w_gate import _consume

    changed = json.loads(json.dumps(sample["archive"]))
    changed["native"]["source_scope"] = "unapproved_source"
    raw = canonical(changed)
    path = tmp_path / "unapproved.json"
    path.write_bytes(raw)
    ledger = StageWPersistentGrantLedger.provision_new(tmp_path / "scope.sqlite3")
    with pytest.raises(StageWGateRejected):
        _consume(sample, ledger, archive_path=path, archive_sha=hashlib.sha256(raw).hexdigest())


def test_duplicate_signed_grant_cannot_reserve_twice(sample, tmp_path):
    from test_self_world_stage_w_gate import _consume

    ledger = StageWPersistentGrantLedger.provision_new(tmp_path / "double.sqlite3")
    first = _consume(sample, ledger)
    assert not first.external_issuer_identity_qualified
    assert not first.real_s10_commit_permitted
    with pytest.raises(StageWGateRejected):
        _consume(sample, StageWPersistentGrantLedger(tmp_path / "double.sqlite3"))


def test_unsigned_handoff_cannot_invent_custody_or_capture_time(monkeypatch, tmp_path):
    import json

    from adapters.mineflayer.self_world_stage_w4_preflight import prepare_unsigned_custody_handoff
    from test_self_world_stage_w3_capture import _fixture_lines, _launch

    _launch(monkeypatch, tmp_path, _fixture_lines())
    handoff = prepare_unsigned_custody_handoff(tmp_path, received_at_utc="2026-10-19T00:00:00Z")
    assert handoff["frame_count"] == 3
    assert handoff["signature"] is None and handoff["archivist_public_key_pin"] is None
    assert handoff["capture_start_utc"] is None and handoff["capture_end_utc"] is None
    assert not handoff["independent_custody_qualified"] and not handoff["s10_permission"]
    assert json.dumps(handoff)
    with pytest.raises(W4PreworldBlocked):
        prepare_unsigned_custody_handoff(tmp_path, received_at_utc="2026-10-19T00:00:00")


def test_disposable_in_place_rollback_demonstrates_monotonic_authority_gap(sample, tmp_path):
    path = tmp_path / "rollback-copy.sqlite3"
    ledger = StageWPersistentGrantLedger.provision_new(path)
    pristine = tmp_path / "pristine-copy.sqlite3"
    shutil.copy2(path, pristine)
    reserve(ledger, sample)
    # Explicitly isolated TEST storage: no actual grant/evidence is restored.
    shutil.copyfile(pristine, path)
    reserve(ledger, sample)
    assert external_trust_readout()["global_ledger_single_use"] == "BLOCKED"
