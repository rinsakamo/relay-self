"""Q1g offline canonical physical MOVE_PLACE WAL shape and attacks.

The fixture writes the actual PhysicalActionJournal v2 envelope and field
names documented in the I lane, but is NOT a trusted original World source.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.q_lane_original_move_place_wal_dev import (
    QMovePlaceWalHold,
    audit_q1g_original_move_place_wal,
)

SESSION = "session-A"
SELF = "A"


def _canon(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _envelope(body: dict) -> bytes:
    return _canon({
        "body": body, "sha256": hashlib.sha256(_canon(body)).hexdigest(),
    }) + b"\n"


def _row(*, number: int, status: str, started: float,
         delta: float, gait: str | None = None) -> dict:
    seq = 1 if number == 1 else 8
    first = {
        "session_id": SESSION,
        "intent_id": f"intent-{number}", "skill_execution_id": f"skill-{number}",
        "action_id": f"action-{number}",
        "capability": "MOVE_PLACE",
        "target_ref": f"destination:goal-{number}",
        "probe_seq": seq, "probe_request_id": f"request-{number}",
        "source_ref": f"{SESSION}:{seq}",
        "status": status,
        "effect_seqs": [seq+1, seq+2, seq+3],
        "after_seq": seq+6,
        "food_before": None, "food_after": None,
        "count_before": None, "count_after": None,
        "control": "forward",
        "started_position": {"x": started, "y": 64.0, "z": 0.0},
        "settled_position": {"x": started+delta, "y": 64.0, "z": 0.0},
        "initial_stop_seq": seq+4, "first_stable_seq": seq+5,
        "initial_stop_tick": 20*number,
        "first_stable_tick": 20*number+10,
        "settled_tick": 20*number+20,
        "displacement_m": delta,
        "invocation_ref": f"skill-invocation:v1@invocation-{number}",
        "preset_ref": f"skill-preset:v1@preset-{number}",
        "target_contract_ref": f"target-contract:v1@target-{number}",
        "aim_yaw_rad": 0.0,
        "target_position": {"x": 3.0, "y": 64.0, "z": 0.0},
        "budget_actions": 4, "budget_duration_ms": 1000,
        "budget_distance_m": 1.0,
    }
    if gait is not None:
        first["gait_mode"] = gait
        first["gait_ack_seq"] = None
    return first


def _setup(tmp_path: Path):
    root = tmp_path / "original"
    root.mkdir(parents=True)
    s1 = _row(number=1, status="NATIVE_PLACE_MOVE_SETTLED",
              started=0.0, delta=0.5)
    s2 = _row(number=2, status="NATIVE_PLACE_MOVE_NO_PROGRESS",
              started=0.5, delta=0.03)
    old = {"schema": 2, "self_id": SELF, "actions": [s1]}
    next_ = {"schema": 2, "self_id": SELF, "actions": [copy.deepcopy(s1), s2]}
    old_path = root / "s1-original-wal.json"
    later_path = root / "s2-original-wal.json"
    old_path.write_bytes(_envelope(old))
    later_path.write_bytes(_envelope(next_))
    claims = {
        "s1_wal_file": old_path.name,
        "s2_wal_file": later_path.name,
        "expected_s1_wal_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
        "expected_self_id": SELF,
        "expected_native_session_id": SESSION,
        "expected_s1_action_count": 1,
        "expected_last_s1_action_id": "action-1",
        "expected_s2_action_id": "action-2",
    }
    return root, claims


def _verify(root: Path, claims: dict):
    return audit_q1g_original_move_place_wal(root, **claims)


def _edit(root: Path, file: str, update) -> None:
    p = root / file
    obj = json.loads(p.read_bytes())
    update(obj["body"])
    p.write_bytes(_envelope(obj["body"]))


def test_q1g_real_canonical_v2_shape_synthetic_read_only(tmp_path):
    root, claims = _setup(tmp_path)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
              for p in root.iterdir()}
    receipt = _verify(root, claims)
    assert receipt["classification"] == "Q1G_CANONICAL_MOVE_PLACE_WAL_SHAPE_CPU_OFFLINE_DEV"
    assert receipt["original_wal_format"] == "physical-action-journal-v2-envelope"
    assert receipt["s2_action_count"] == 2
    assert receipt["s2_terminal_status_label"] == "NATIVE_PLACE_MOVE_NO_PROGRESS"
    assert receipt["s2_outcome_original_native_paper_attested"] is False
    assert receipt["original_owner_attested"] is False
    assert receipt["independent_external_s1_origin_attested"] is False
    assert receipt["original_checkpoint_attested"] is False
    assert receipt["real_world_attested"] is False
    assert receipt["qual_go"] is False and receipt["science_run"] is False
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in root.iterdir()}


@pytest.mark.parametrize("change", [
    "missing-status", "unknown-status", "fake-terminal",
    "bad-native-source", "replayed-native-seq", "bad-effects-order",
    "stop-before-start", "short-stop-settling", "long-stability",
    "wrong-displacement", "wrong-position", "missing-field",
    "additional-field", "foreign-session", "unbound-skill",
    "wrong-capability", "invalid-budget", "invalid-pos",
    "fake-gait", "unsupported-gait", "bool-probe-seq",
    "nan-position", "duplicate-action", "extra-action",
])
def test_q1g_rejects_manufactured_terminal_source_after_rehash(
    tmp_path, change,
):
    root, claims = _setup(tmp_path)
    def corrupt(body):
        a = body["actions"][-1]
        if change == "missing-status":
            a.pop("status")
        elif change == "unknown-status":
            a["status"] = "PREPARED_FAKE_OUTCOME"
        elif change == "fake-terminal":
            a["status"] = "NATIVE_PLACE_MOVE_SETTLED"  # delta < 0.1
        elif change == "bad-native-source":
            a["source_ref"] = "session-A:99"
        elif change == "replayed-native-seq":
            a["probe_seq"] = 7  # prior S1 after_seq=7
        elif change == "bad-effects-order":
            a["effect_seqs"][0] = 11
        elif change == "stop-before-start":
            a["effect_seqs"][2] = 9
        elif change == "short-stop-settling":
            a["first_stable_tick"] = a["initial_stop_tick"] + 1
        elif change == "long-stability":
            a["settled_tick"] = a["first_stable_tick"] + 201
        elif change == "wrong-displacement":
            a["displacement_m"] = 0.4
        elif change == "wrong-position":
            a["settled_position"]["x"] = 2.0
        elif change == "missing-field":
            a.pop("invocation_ref")
        elif change == "additional-field":
            a["untrusted_field"] = True
        elif change == "foreign-session":
            a["session_id"] = "old-session"
        elif change == "unbound-skill":
            a["skill_execution_id"] = ""
        elif change == "wrong-capability":
            a["capability"] = "ATTACK"
        elif change == "invalid-budget":
            a["budget_actions"] = 65
        elif change == "invalid-pos":
            a["target_position"] = {"x": 1.0, "z": 2.0}
        elif change == "fake-gait":
            a["gait_mode"] = "SNEAK"
            a["gait_ack_seq"] = None
        elif change == "unsupported-gait":
            a["gait_mode"] = "DASH"
            a["gait_ack_seq"] = 9
        elif change == "bool-probe-seq":
            a["probe_seq"] = True
        elif change == "nan-position":
            a["started_position"]["x"] = float("nan")
            # allow_nan=False in _envelope would reject before verifier.
            a["started_position"]["x"] = "NaN"
        elif change == "duplicate-action":
            a["action_id"] = body["actions"][0]["action_id"]
        elif change == "extra-action":
            body["actions"].append(copy.deepcopy(a))
    _edit(root, claims["s2_wal_file"], corrupt)
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


@pytest.mark.parametrize("change", [
    "tamper-original-and-rehash", "change-s1-source", "change-s1-status",
    "change-s1-balance", "change-s2-intent", "change-s2-skill",
    "trim-old-action", "relabel-s1",
])
def test_q1g_original_historical_s1_is_not_rebased_by_local_rehash(
    tmp_path, change,
):
    root, claims = _setup(tmp_path)
    if change == "trim-old-action":
        claims["expected_s1_action_count"] = 2
    elif change == "relabel-s1":
        claims["expected_last_s1_action_id"] = "foreign-action"
    elif change in ("change-s2-intent", "change-s2-skill"):
        key = "intent_id" if change == "change-s2-intent" else "skill_execution_id"
        _edit(root, claims["s2_wal_file"],
              lambda body: body["actions"][-1].__setitem__(
                  key, body["actions"][0][key],
              ))
    elif change == "tamper-original-and-rehash":
        _edit(root, claims["s1_wal_file"],
              lambda body: body["actions"][0].__setitem__(
                  "action_id", "tampered-and-rehashed",
              ))
        _edit(root, claims["s2_wal_file"],
              lambda body: body["actions"][0].__setitem__(
                  "action_id", "tampered-and-rehashed",
              ))
    else:
        _edit(root, claims["s2_wal_file"],
              lambda body: body["actions"][0].__setitem__(
                  "source_ref" if change == "change-s1-source"
                  else "status" if change == "change-s1-status"
                  else "budget_distance_m",
                  "foreign:99" if change == "change-s1-source"
                  else "NATIVE_PLACE_MOVE_NO_PROGRESS" if change == "change-s1-status"
                  else 0.4,
              ))
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


def test_q1g_original_schema_requires_actual_body_and_sha_envelope(tmp_path):
    root, claims = _setup(tmp_path)
    p = root / claims["s2_wal_file"]
    old = json.loads(p.read_bytes())
    p.write_bytes(_canon(old["body"]) + b"\n")
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


def test_q1g_rejects_envelope_self_consistent_rehash_not_canonical(tmp_path):
    root, claims = _setup(tmp_path)
    p = root / claims["s2_wal_file"]
    raw = p.read_bytes()
    p.write_bytes(b" " + raw)
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


def test_q1g_rejects_symlinked_original_wal(tmp_path):
    root, claims = _setup(tmp_path)
    p = root / claims["s2_wal_file"]
    p.unlink()
    p.symlink_to(root / claims["s1_wal_file"])
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


def test_q1g_rejects_prior_digest_claim_from_later_wal(tmp_path):
    root, claims = _setup(tmp_path)
    new = root / claims["s2_wal_file"]
    claims["expected_s1_wal_sha256"] = hashlib.sha256(new.read_bytes()).hexdigest()
    with pytest.raises(QMovePlaceWalHold):
        _verify(root, claims)


def test_q1g_rewritten_original_and_attacker_rewritten_pin_not_authenticated(tmp_path):
    root, claims = _setup(tmp_path)
    _edit(root, claims["s1_wal_file"],
          lambda body: body["actions"][0].__setitem__(
              "action_id", "rewritten-s1",
          ))
    _edit(root, claims["s2_wal_file"],
          lambda body: body["actions"][0].__setitem__(
              "action_id", "rewritten-s1",
          ))
    claims["expected_last_s1_action_id"] = "rewritten-s1"
    claims["expected_s1_wal_sha256"] = hashlib.sha256(
        (root / claims["s1_wal_file"]).read_bytes(),
    ).hexdigest()
    verdict = _verify(root, claims)
    assert verdict["independent_external_s1_origin_attested"] is False
    assert verdict["original_owner_attested"] is False
    assert verdict["real_world_attested"] is False
