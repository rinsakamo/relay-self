"""Q1b hostile pre-S2 historical WAL tests using synthetic bytes, NOT World."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.q_lane_s1_boundary_audit_dev import (
    QS1BoundaryHold,
    verify_s1_s2_anchor,
)

HEAD = "1" * 40
WORLD = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
OWNER = "owner-original-A"
SELF = "A"
SESSION = "native-A-epoch-4"


def _bytes(row: object) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _setup(tmp_path: Path) -> tuple[Path, bytes, dict, dict]:
    root = tmp_path / "original"
    root.mkdir(parents=True)
    s1 = {
        "action_id": "action-s1", "intent_id": "intent-s1",
        "skill_execution_id": "skill-s1",
        "status": "NATIVE_PLACE_MOVE_SETTLED",
    }
    s2 = {
        "action_id": "action-s2", "intent_id": "intent-s2",
        "skill_execution_id": "skill-s2",
        "status": "NATIVE_PLACE_MOVE_NO_PROGRESS",
    }
    before = {"schema": 2, "self_id": SELF, "actions": [s1]}
    after = {"schema": 2, "self_id": SELF, "actions": [copy.deepcopy(s1), s2]}
    (root / "s1-wal.json").write_bytes(_bytes(before))
    (root / "s2-wal.json").write_bytes(_bytes(after))
    (root / "s1-checkpoint.json").write_bytes(_bytes({
        "generation": 4, "actor": SELF, "owner": OWNER,
    }))
    anchor = {
        "schema": 1, "phase": "S1_TERMINAL_PRE_S2",
        "head": HEAD, "world_uuid": WORLD,
        "owner_id": OWNER, "self_id": SELF,
        "native_session_id": SESSION, "checkpoint_generation": 4,
        "s1_intent_id": "intent-s1", "s1_skill_execution_id": "skill-s1",
        "s1_action_id": "action-s1", "s1_status": "NATIVE_PLACE_MOVE_SETTLED",
        "s1_wal_sha256": _sha((root / "s1-wal.json").read_bytes()),
        "s1_checkpoint_sha256": _sha((root / "s1-checkpoint.json").read_bytes()),
        "s1_action_count": 1,
    }
    raw_anchor = _bytes(anchor)
    args = {
        "expected_pre_s2_anchor_sha256": _sha(raw_anchor),
        "s1_wal_path": "s1-wal.json", "s1_checkpoint_path": "s1-checkpoint.json",
        "s2_wal_path": "s2-wal.json", "expected_s2_action_id": "action-s2",
        "expected_head": HEAD, "expected_world_uuid": WORLD,
        "expected_owner_id": OWNER, "expected_self_id": SELF,
        "expected_native_session_id": SESSION, "expected_checkpoint_generation": 4,
    }
    return root, raw_anchor, anchor, args


def _verify(root: Path, anchor: bytes, args: dict):
    return verify_s1_s2_anchor(root, anchor_bytes=anchor, **args)


def test_q1b_synthetic_preanchor_and_wal_continuity_read_only(tmp_path):
    root, anchor, _row, args = _setup(tmp_path)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    verdict = _verify(root, anchor, args)
    assert verdict["classification"] == "Q1B_PINNED_S1_S2_WAL_PREFIX_CPU_OFFLINE_DEV"
    assert verdict["s1_action_count"] == 1
    assert verdict["s2_total_action_count"] == 2
    assert verdict["trusted_external_anchor_origin_verified"] is False
    assert verdict["pre_s2_temporal_order_verified"] is False
    assert verdict["original_stage28_checkpoint_restored"] is False
    assert verdict["original_owner_semantics_verified"] is False
    assert verdict["real_world_attested"] is False and verdict["qual_go"] is False
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in root.iterdir()}


@pytest.mark.parametrize(("field", "replacement"), [
    ("expected_head", "2" * 40),
    ("expected_world_uuid", "different-world"),
    ("expected_owner_id", "different-owner"),
    ("expected_self_id", "B"),
    ("expected_native_session_id", "stale-native-session"),
    ("expected_checkpoint_generation", 5),
    ("expected_pre_s2_anchor_sha256", "0" * 64),
])
def test_q1b_rejects_scope_and_externally_pinned_digest_changes(
    tmp_path, field, replacement,
):
    root, anchor, _row, args = _setup(tmp_path)
    args[field] = replacement
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)


@pytest.mark.parametrize(("field", "replacement"), [
    ("head", "2" * 40), ("owner_id", "foreign-owner"),
    ("native_session_id", "old-session"),
    ("s1_status", "PREPARED_UNRESOLVED"),
    ("s1_action_count", 2),
    ("phase", "S1_TERMINAL_AFTER_S2"),
    ("s1_action_id", "stale-action"),
])
def test_q1b_rejects_rehashed_manifest_claims_without_external_preanchor(
    tmp_path, field, replacement,
):
    root, anchor, row, args = _setup(tmp_path)
    row[field] = replacement
    forged = _bytes(row)
    # Recompute the attacker's local manifest SHA. The independent pin
    # remains the ORIGINAL digest, so this does not establish origin.
    assert _sha(forged) != args["expected_pre_s2_anchor_sha256"]
    with pytest.raises(QS1BoundaryHold, match="external digest"):
        _verify(root, forged, args)


@pytest.mark.parametrize(("file", "replace", "with_text"), [
    ("s1-wal.json", b"action-s1", b"action-SWAPPED"),
    ("s1-wal.json", b"NATIVE_PLACE_MOVE_SETTLED", b"PREPARED_UNRESOLVED"),
    ("s1-checkpoint.json", b'"generation":4', b'"generation":5'),
    ("s1-checkpoint.json", b"owner-original-A", b"owner-SWAPPED"),
])
def test_q1b_s1_raw_bytes_cannot_be_modified_and_rehashed_locally(
    tmp_path, file, replace, with_text,
):
    root, anchor, row, args = _setup(tmp_path)
    path = root / file
    old = path.read_bytes()
    new = old.replace(replace, with_text)
    assert new != old
    path.write_bytes(new)
    # Recomputing the local manifest SHA cannot update trusted earlier pin.
    row["s1_wal_sha256" if file == "s1-wal.json" else "s1_checkpoint_sha256"] = (
        _sha(new)
    )
    with pytest.raises(QS1BoundaryHold):
        _verify(root, _bytes(row), args)


@pytest.mark.parametrize(("change", "expected"), [
    ("s1-action-id", "Historical S1 WAL row"),
    ("s1-action-status", "Historical S1 WAL row"),
    ("s1-intent", "Historical S1 WAL row"),
    ("reordered", "Historical S1 WAL row"),
    ("duplicate-id", "Duplicate/replayed"),
    ("no-s2", "later S2 Action missing"),
    ("prepared-s2", "Unresolved PREPARED"),
    ("foreign-self", "schema or Self mismatch"),
    ("wrong-s2-id", "S2 new Action"),
])
def test_q1b_rejects_s2_history_replay_or_reinterpretation(
    tmp_path, change, expected,
):
    root, anchor, _row, args = _setup(tmp_path)
    path = root / "s2-wal.json"
    body = json.loads(path.read_bytes())
    old = body["actions"][0]
    next_row = body["actions"][1]
    if change == "s1-action-id":
        old["action_id"] = "changed-then-rehashed"
    elif change == "s1-action-status":
        old["status"] = "NATIVE_MOVE_SETTLED"
    elif change == "s1-intent":
        old["intent_id"] = "foreign-intent"
    elif change == "reordered":
        body["actions"].reverse()
    elif change == "duplicate-id":
        next_row["action_id"] = old["action_id"]
    elif change == "no-s2":
        body["actions"].pop()
    elif change == "prepared-s2":
        next_row["status"] = "PREPARED_UNRESOLVED"
    elif change == "foreign-self":
        body["self_id"] = "B"
    elif change == "wrong-s2-id":
        args["expected_s2_action_id"] = "stale-action"
    path.write_bytes(_bytes(body))
    with pytest.raises(QS1BoundaryHold, match=expected):
        _verify(root, anchor, args)


def test_q1b_rejects_missing_symlinked_or_incomplete_evidence(tmp_path):
    root, anchor, row, args = _setup(tmp_path)
    (root / "s1-checkpoint.json").unlink()
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)
    root, anchor, row, args = _setup(tmp_path / "second")
    checkpoint = root / "s1-checkpoint.json"
    checkpoint.unlink()
    checkpoint.symlink_to(root / "s1-wal.json")
    with pytest.raises(QS1BoundaryHold):
        _verify(root, anchor, args)


def test_q1b_both_modified_pin_and_wal_can_pass_but_is_not_authenticated(tmp_path):
    """Demonstrates why Q refuses to claim independent source authentication."""
    root, _old_anchor, row, args = _setup(tmp_path)
    original = json.loads((root / "s1-wal.json").read_bytes())
    original["actions"][0]["action_id"] = "attacker-s1"
    new = json.loads((root / "s2-wal.json").read_bytes())
    new["actions"][0]["action_id"] = "attacker-s1"
    (root / "s1-wal.json").write_bytes(_bytes(original))
    (root / "s2-wal.json").write_bytes(_bytes(new))
    row["s1_wal_sha256"] = _sha((root / "s1-wal.json").read_bytes())
    row["s1_action_id"] = "attacker-s1"
    forged_anchor = _bytes(row)
    # If the presumed out-of-band anchor digest is also writable by the
    # attacker, all hashes can agree. This is exactly why result says NOT
    # authenticated, even when this limited consistency check passes.
    args["expected_pre_s2_anchor_sha256"] = _sha(forged_anchor)
    receipt = _verify(root, forged_anchor, args)
    assert receipt["trusted_external_anchor_origin_verified"] is False
    assert receipt["pre_s2_temporal_order_verified"] is False
