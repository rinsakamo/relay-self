"""V-owned L1 comparator never needs an L1 import for its negative controls."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from experiments.validation import l1_independent_audit as audit


def memory(*, session="s", revision=1, digest="a" * 64,
           disposition="outcome", reason="observed"):
    item = {
        "schema": "L1_SOURCE_EPISODE_V1",
        "session_id": session, "world_revision": revision,
        "action_id": "a1", "binding_id": "b", "action_ref": "MOVE_BACKWARD",
        "source_status": "executed" if disposition == "outcome" else "unknown",
        "disposition": disposition, "reason_code": reason,
        "evidence_sha256": digest, "cue_tags": ["near_zombie", "night"],
        "hypothesis": "not evaluated",
    }
    return SimpleNamespace(memory_id="l1:s:a1:1", content=json.dumps(item))


def query(**fields):
    base = {
        "session_id": "s", "world_revision": 1,
        "max_revision_lag": 0, "cue_tags": ("near_zombie", "night"),
        "admitted_evidence_sha256": frozenset({"a" * 64}),
    }
    base.update(fields)
    return SimpleNamespace(**base)


def scan(memories, q=None):
    return audit.cheap_scan(SimpleNamespace(memories=memories), q or query())


def test_independent_cheap_scan_uses_original_episode_fields():
    assert scan((memory(),)) == (
        "recall", ("l1:s:a1:1",), ("MOVE_BACKWARD",), 1,
    )
    assert scan(()) == ("unknown", (), (), 0)


@pytest.mark.parametrize(("q", "state"), [
    (query(session_id="foreign"), "unknown"),
    (query(world_revision=0), "stale"),
    (query(admitted_evidence_sha256=frozenset()), "unverified"),
    (query(cue_tags=("other",)), "unknown"),
])
def test_cheap_scan_denies_foreign_stale_unverified(q, state):
    assert scan((memory(),), q)[0] == state


def test_cheap_scan_unknown_is_not_an_outcome():
    assert scan((memory(disposition="unknown"),))[0] == "reconsider"


def test_cheap_scan_contradictory_evidence_not_recall():
    left = memory()
    right = memory(reason="collision")
    right.memory_id = "l1:s:a2:1"
    assert scan((left, right))[0] == "contradictory"


def test_missing_sibling_checkout_blocks_without_import(tmp_path):
    with pytest.raises(audit.AuditRejected):
        audit.checked_l1_root(tmp_path / "missing")


def test_sibling_symlink_not_admitted(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    symlink = tmp_path / "link"
    symlink.symlink_to(real, target_is_directory=True)
    with pytest.raises(audit.AuditRejected):
        audit.checked_l1_root(symlink)
