"""Q1i Original SelfOwnerCut typed-envelope source invariants (synthetic only)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.q_lane_typed_owner_cut_audit_dev import (
    QTypedOwnerCutHold,
    audit_q1i_typed_owner_cut,
)

GEN = "g-000000000004"
SESSION = "session-A"
PROVENANCE = {"source": "synthetic-source", "reference": "synthetic:4"}


def _canon(obj):
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _cut_payload(*, schema=1):
    payload = {
        "schema": schema,
        "generation_id": GEN,
        "self_id": "A",
        "world_id": "World-A",
        "branch_id": "dev-branch",
        "former_native_session_id": SESSION,
        "last_observed_world_tick": 105,
        "intent_events": [
            {
                "kind": "committed", "intent_id": "intent-1",
                "objective": "MOVE", "reason": None,
                "at_ns": 1000, "provenance": PROVENANCE,
            },
            {
                "kind": "completed", "intent_id": "intent-1",
                "objective": None, "reason": "reviewed S1 terminal",
                "at_ns": 1030, "provenance": PROVENANCE,
            },
        ],
        "skills": [{
            "execution_id": "skill-1", "skill_id": "MOVE_PLACE",
            "intent_id": "intent-1",
            "events": [
                {"state": "started", "at_ns": 1010,
                 "reason": None, "provenance": PROVENANCE},
                {"state": "cancelled", "at_ns": 1020,
                 "reason": "reviewed S1 stop", "provenance": PROVENANCE},
            ],
        }],
        "peer_deliveries": [],
        "pending_question_refs": ["question-A"],
    }
    if schema == 1:
        payload["pattern_registry"] = {
            "revision": 0, "patterns": [],
        }
    else:
        registry = {
            "schema": 2, "self_id": "A", "revision": 0,
            "patterns": [], "accepted_presets": [],
        }
        registry["registry_ref"] = "schema-registry:v2@" + _sha(json.dumps(
            registry, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode())
        payload["pattern_registry"] = registry
        payload["cognition_sha256"] = "a" * 64
    return payload


def _fixture(tmp_path: Path, *, schema=1):
    root = tmp_path / "owner-evidence"
    root.mkdir(parents=True)
    p = _cut_payload(schema=schema)
    path = root / "owner-cut.json"
    encoded = _canon({"payload": p, "sha256": _sha(_canon(p))})
    path.write_bytes(encoded)
    claims = {
        "checkpoint_file": "owner-cut.json",
        "expected_checkpoint_sha256": _sha(encoded),
        "expected_generation_id": GEN,
        "expected_self_id": "A",
        "expected_world_id": "World-A",
        "expected_branch_id": "dev-branch",
        "expected_former_native_session_id": SESSION,
    }
    return root, p, claims


def _audit(root, claims):
    return audit_q1i_typed_owner_cut(root, **claims)


@pytest.mark.parametrize("schema", [1, 2])
def test_q1i_canonical_original_cut_shape_and_terminal_lineage_read_only(
    tmp_path, schema,
):
    root, _payload, claims = _fixture(tmp_path, schema=schema)
    old = (root / "owner-cut.json").read_bytes()
    old_stat = (root / "owner-cut.json").stat().st_mtime_ns
    receipt = _audit(root, claims)
    assert receipt["classification"] == (
        "Q1I_TYPED_OWNER_CUT_SHAPE_AND_LINEAGE_CPU_OFFLINE_DEV"
    )
    assert receipt["generation_id"] == GEN
    assert receipt["intent_count"] == receipt["skill_count"] == 1
    assert receipt["skills"]["skill-1"]["last_state"] == "cancelled"
    assert receipt["intents"]["intent-1"]["final_kind"] == "completed"
    assert receipt["owner_schema"] == schema
    assert receipt["independent_original_producer_attested"] is False
    assert receipt["full_product_semantic_decode_attested"] is False
    assert receipt["pattern_registry_semantics_attested"] is False
    assert receipt["real_world_attested"] is False
    assert receipt["qual_go"] is False and receipt["science_run"] is False
    assert (root / "owner-cut.json").read_bytes() == old
    assert (root / "owner-cut.json").stat().st_mtime_ns == old_stat


def _forge(root, payload, claims, *, repin=True):
    raw = _canon({"payload": payload, "sha256": _sha(_canon(payload))})
    (root / "owner-cut.json").write_bytes(raw)
    if repin:
        claims["expected_checkpoint_sha256"] = _sha(raw)


@pytest.mark.parametrize(("field", "value"), [
    ("expected_generation_id", "g-000000000005"),
    ("expected_self_id", "B"),
    ("expected_world_id", "World-B"),
    ("expected_branch_id", "other-branch"),
    ("expected_former_native_session_id", "session-old"),
    ("expected_checkpoint_sha256", "0"*64),
    ("expected_generation_id", "bad-format"),
])
def test_q1i_external_scope_pin_mismatch_hold(tmp_path, field, value):
    root, _p, args = _fixture(tmp_path)
    args[field] = value
    with pytest.raises(QTypedOwnerCutHold):
        _audit(root, args)


@pytest.mark.parametrize("bad", [
    "gen", "self", "world", "branch", "native-session",
    "replay-intent", "stale-skill", "pending-duplicate",
    "unknown-skill-state", "reason-for-start", "reason-missing",
    "uncommitted-skill", "duplicate-skill", "future-peer",
    "out-of-order-time", "double-commit", "future-skill-start",
    "missing-provenance", "unknown-field", "bool-time",
])
def test_q1i_attacker_rehash_of_semantically_bad_owner_cut_still_holds(
    tmp_path, bad,
):
    root, payload, claims = _fixture(tmp_path)
    p = copy.deepcopy(payload)
    if bad == "gen":
        p["generation_id"] = "g-000000000005"
    elif bad == "self":
        p["self_id"] = "B"
    elif bad == "world":
        p["world_id"] = "World-B"
    elif bad == "branch":
        p["branch_id"] = "other"
    elif bad == "native-session":
        p["former_native_session_id"] = "stale"
    elif bad == "replay-intent":
        p["intent_events"].append(copy.deepcopy(p["intent_events"][0]))
    elif bad == "stale-skill":
        p["skills"][0]["events"][-1]["at_ns"] = 999
    elif bad == "pending-duplicate":
        p["pending_question_refs"] = ["question-A", "question-A"]
    elif bad == "unknown-skill-state":
        p["skills"][0]["events"][-1]["state"] = "phantom_success"
    elif bad == "reason-for-start":
        p["skills"][0]["events"][0]["reason"] = "impossible"
    elif bad == "reason-missing":
        p["skills"][0]["events"][-1]["reason"] = None
    elif bad == "uncommitted-skill":
        p["skills"][0]["intent_id"] = "never-committed"
    elif bad == "duplicate-skill":
        p["skills"].append(copy.deepcopy(p["skills"][0]))
    elif bad == "future-peer":
        p["peer_deliveries"] = [{
            "message_id": "m1", "sender_self_id": "A",
            "recipient_self_id": "B", "sent_world_tick": 100,
            "received_world_tick": 999, "payload_ref": "sha:abc",
        }]
    elif bad == "out-of-order-time":
        p["intent_events"][-1]["at_ns"] = 100
    elif bad == "double-commit":
        p["intent_events"][1] = copy.deepcopy(p["intent_events"][0])
        p["intent_events"][1]["intent_id"] = "intent-2"
    elif bad == "future-skill-start":
        p["skills"][0]["events"][0]["at_ns"] = 900
    elif bad == "missing-provenance":
        p["skills"][0]["events"][0]["provenance"] = {"source": ""}
    elif bad == "unknown-field":
        p["forged_issuer_grant"] = True
    else:
        p["last_observed_world_tick"] = True
    _forge(root, p, claims)
    with pytest.raises(QTypedOwnerCutHold):
        _audit(root, claims)


@pytest.mark.parametrize("bad", [
    "wrong-registry-sha", "foreign-self", "duplicate-pattern",
    "missing-cognition-digest", "invalid-cognition-digest",
])
def test_q1i_v2_registry_attacker_rehash_still_holds(tmp_path, bad):
    root, payload, claims = _fixture(tmp_path, schema=2)
    p = copy.deepcopy(payload)
    registry = p["pattern_registry"]
    if bad == "wrong-registry-sha":
        registry["registry_ref"] = "schema-registry:v2@" + "0"*64
    elif bad == "foreign-self":
        registry["self_id"] = "B"
    elif bad == "duplicate-pattern":
        entry = {
            "pattern_id": "p1", "version": 1, "schema_id": "s",
            "kind": "goal", "predicate": "always", "goal_id": "goal",
            "skill_id": None, "skill_version": None, "target_kind": None,
            "origin": "learned", "provenance": PROVENANCE,
        }
        registry["patterns"] = [entry, copy.deepcopy(entry)]
    elif bad == "missing-cognition-digest":
        del p["cognition_sha256"]
    else:
        p["cognition_sha256"] = "not-a-digest"
    if bad not in ("wrong-registry-sha", "foreign-self"):
        raw = {k: v for k, v in registry.items() if k != "registry_ref"}
        registry["registry_ref"] = "schema-registry:v2@" + _sha(json.dumps(
            raw, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode())
    _forge(root, p, claims)
    with pytest.raises(QTypedOwnerCutHold):
        _audit(root, claims)


def test_q1i_local_rehash_without_original_external_pin_rejected(tmp_path):
    root, payload, claims = _fixture(tmp_path)
    p = copy.deepcopy(payload)
    p["skills"][0]["events"][-1]["reason"] = "locally rewritten"
    _forge(root, p, claims, repin=False)
    with pytest.raises(QTypedOwnerCutHold, match="external SHA"):
        _audit(root, claims)


def test_q1i_symlink_fails_closed(tmp_path):
    root, _p, claims = _fixture(tmp_path)
    old = root / "owner-cut.json"
    old.unlink()
    old.symlink_to(root / "surrogate.json")
    with pytest.raises(QTypedOwnerCutHold):
        _audit(root, claims)


def test_q1i_attacker_can_rewrite_all_bytes_and_pin_but_not_authenticate(tmp_path):
    root, payload, claims = _fixture(tmp_path)
    p = copy.deepcopy(payload)
    p["intent_events"][1]["reason"] = "attacker-wrote-late"
    _forge(root, p, claims, repin=True)
    receipt = _audit(root, claims)
    assert receipt["independent_original_producer_attested"] is False
    assert receipt["independent_actual_checkpoint_capture_time_attested"] is False
    assert receipt["real_world_attested"] is False
