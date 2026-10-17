"""RSEE R6 offline-only predecode source negatives; no historical raw bytes."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from experiments.standard_env import s3_v_projection as r4
from experiments.standard_env import s9_original_audit as r6
from relay_self.persistent_cognition import load_persistent_cognition
from test_rsee_s3_v_projection import original_projection as r4_fixture
from test_rsee_s3_v_projection import (
    rename_original,
    select_emitter_head,
    with_retention,
)


@pytest.fixture
def case(tmp_path, monkeypatch):
    source = r4_fixture.__wrapped__(tmp_path)
    # Source-shaped fixture session is NOT the real S9 operator's session.
    monkeypatch.setattr(r6, "SESSION", source["sid"])
    first = with_retention(source)
    original_memory = load_persistent_cognition(source["memory"]).memories[0]
    first_episode = json.loads(original_memory.content)
    second = {
        **first_episode, "action_id": "s49-native-move-8",
        "world_revision": 8, "evidence_sha256": "d" * 64,
    }
    second_id = f"l1:{source['sid']}:s49-native-move-8:8"
    source["store_memory"]([
        {"id": first, "content": first_episode},
        {"id": second_id, "content": second},
    ])

    def retained(mid, episode):
        return {
            "kind": "experience_retained_observation",
            "memory_id": mid,
            "session": source["sid"],
            "source_seq": episode["world_revision"],
            "evidence_sha256": episode["evidence_sha256"],
            "action_authority": False,
            "goal_success_attested": False,
            "learning_updates": 0,
            "habit_grants": 0,
        }

    source["store_events"]([
        {"kind": "session_started"},
        retained(first, first_episode),
        {"kind": "experience_read_only_hint", "action_authority": False},
        retained(second_id, second),
        {"kind": "session_terminal", "terminal": "ACTION_BUDGET_ENDED"},
    ])
    root = source["kwargs"]["derived_root"]
    received = root / r6.RECEIVED
    sent = root / r6.SENT
    recv_lines = [
        {"type": "adapter_started", "session_id": source["sid"], "seq": 0},
        {"type": "observation", "session_id": source["sid"], "seq": 1},
        {"type": "effect_result", "session_id": source["sid"], "seq": 2},
    ]
    sent_lines = [{"type": "observe"}, {"type": "set_control"}]

    def dump(path, rows):
        path.write_bytes(
            b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows)
        )

    dump(received, recv_lines)
    dump(sent, sent_lines)

    def expected():
        incoming = received.read_bytes()
        outgoing = sent.read_bytes()
        return r6.ExpectedS9(
            head=r6.S9_HEAD, session=source["sid"],
            received_sha256=hashlib.sha256(incoming).hexdigest(),
            sent_sha256=hashlib.sha256(outgoing).hexdigest(),
            received_lines=len(incoming.splitlines()),
            sent_lines=len(outgoing.splitlines()),
            received_bytes=len(incoming),
            sent_bytes=len(outgoing),
        )

    def write_index(exp):
        index = {
            "schema": "SELF_S7_RAW_MINEFLAYER_JSONL_RECEIPT_V1",
            "received_path": str(received),
            "sent_path": str(sent),
            "received_sha256": exp.received_sha256,
            "sent_sha256": exp.sent_sha256,
            "received_lines": exp.received_lines,
            "sent_lines": exp.sent_lines,
            "received_bytes": exp.received_bytes,
            "sent_bytes": exp.sent_bytes,
            "received_measured_before_decode": True,
            "sent_measured_before_write": True,
            "minecraft_tcp_packet_bytes": False,
            "native_execution_ack_attested": False,
            "v_science_qualified": False,
        }
        (root / r6.INDEX).write_text(json.dumps(index), encoding="utf-8")

    frozen = expected()
    write_index(frozen)
    return {
        **source,
        "root": root,
        "received": received,
        "sent": sent,
        "expected": frozen,
        "write_index": write_index,
        "recv_lines": recv_lines,
        "dump": dump,
    }


def test_s9_literal_operator_report_is_not_independent_attestation():
    x = r6.OPERATOR_REPORTED_S9
    assert x.head == "916814742567f8ff396b5c078d22f897d8418927"
    assert x.session == "dacf338b-4ba9-4e91-8eea-d4aebd0aef22"
    assert (x.received_lines, x.received_bytes) == (39, 21924)
    assert (x.sent_lines, x.sent_bytes) == (14, 897)
    assert len(x.received_sha256) == len(x.sent_sha256) == 64


def test_plan_is_zero_io(monkeypatch, capsys):
    def unexpected(*_args, **_kwargs):
        pytest.fail("default plan cannot access host originals")
    monkeypatch.setattr(r6, "audit", unexpected)
    assert r6.main([]) == 0
    x = json.loads(capsys.readouterr().out)
    assert x["classification"] == "RSEE_R6_PLAN_ONLY"
    assert x["r2_raw_handoff_admitted"] is False


def test_two_epochs_review_only_never_science(case):
    x = r6.audit(case["root"], expected=case["expected"])
    assert x["classification"] == "RSEE_R6_S9_ORIGINAL_BRIDGE_AND_MEMORY_BYTES_REVIEW_ONLY"
    assert x["retained_memory_count"] == 2
    assert x["distinct_reported_action_ids"] == 2
    assert x["typed_s16_semantics_attested"] is False
    assert x["memory_causal_effect_attested"] is False
    assert x["r1_envelope_verified"] is False
    assert x["v_admission_granted"] is False
    assert x["science_qualified"] is False
    assert x["physical_execution_authorized"] is False


@pytest.mark.parametrize("type", [
    "reported_hash", "bad_receipt_digest", "claimed_ack", "missing_capture",
    "bad_first_session", "wrong_seq", "trailing_partial", "index_wrong_path",
])
def test_original_source_corruption_or_false_claim_is_blocked(case, type):
    exp = case["expected"]
    if type == "reported_hash":
        exp = replace(exp, received_sha256="e" * 64)
    elif type == "bad_receipt_digest":
        idx = json.loads((case["root"] / r6.INDEX).read_text())
        idx["received_sha256"] = "0" * 64
        (case["root"] / r6.INDEX).write_text(json.dumps(idx))
    elif type == "claimed_ack":
        idx = json.loads((case["root"] / r6.INDEX).read_text())
        idx["native_execution_ack_attested"] = True
        (case["root"] / r6.INDEX).write_text(json.dumps(idx))
    elif type == "missing_capture":
        case["received"].unlink()
    elif type == "bad_first_session":
        rows = case["recv_lines"]
        rows[0]["session_id"] = "foreign"
        case["dump"](case["received"], rows)
        exp = replace(exp, received_sha256=hashlib.sha256(
            case["received"].read_bytes()).hexdigest())
        case["write_index"](exp)
    elif type == "wrong_seq":
        rows = case["recv_lines"]
        rows[1]["seq"] = 99
        case["dump"](case["received"], rows)
        exp = replace(exp, received_sha256=hashlib.sha256(
            case["received"].read_bytes()).hexdigest())
        case["write_index"](exp)
    elif type == "trailing_partial":
        case["received"].write_bytes(case["received"].read_bytes() + b"partial")
    elif type == "index_wrong_path":
        idx = json.loads((case["root"] / r6.INDEX).read_text())
        idx["received_path"] = str(case["sent"])
        (case["root"] / r6.INDEX).write_text(json.dumps(idx))
    with pytest.raises((r6.S9AuditRejected, r4.R4Rejected)):
        r6.audit(case["root"], expected=exp)


def test_replayed_memory_duplicate_or_wrong_session_blocks(case):
    events = case["events"]
    data = events.read_text()
    data = data.replace('"learning_updates": 0', '"learning_updates": 1', 1)
    events.write_text(data)
    with pytest.raises(r6.S9AuditRejected, match="lineage or authority"):
        r6.audit(case["root"], expected=case["expected"])


def test_wrong_reported_source_head_cannot_be_accepted(case):
    wrong = replace(case["expected"], head=r4.S7_HEAD)
    with pytest.raises(r6.S9AuditRejected, match="exact source HEAD"):
        r6.audit(case["root"], expected=wrong)


def test_r5_s9_requires_true_raw_review_before_any_r2(case, monkeypatch):
    with_retention(case)  # Replace memory with 1: S9 requires precisely 2.
    select_emitter_head(case, r6.S9_HEAD)

    def refuse(*_args, **_kwargs):
        pytest.fail("R2 must not open an envelope before two Memory observations")
    monkeypatch.setattr(r4.r2, "audit_file", refuse)
    with pytest.raises(r4.R4Rejected, match="two retained"):
        r4.audit(**case["kwargs"])


def test_s8_incomplete_derived_is_not_retroactive_two_epoch_success(case, monkeypatch):
    select_emitter_head(case, r4.S8_HEAD)

    def refuse(*_args, **_kwargs):
        pytest.fail("No retrospective R2 admission for S8 partial run")
    monkeypatch.setattr(r4.r2, "audit_file", refuse)
    x = r4.audit(**case["kwargs"])
    assert x["classification"] == "RSEE_R6_S8_PARTIAL_SESSION_NOT_V_ADMISSIBLE"
    assert x["v_admission_granted"] is False


def test_r5_s9_requires_actual_original_and_r1_envelope(case, monkeypatch):
    select_emitter_head(case, r6.S9_HEAD)
    from experiments.standard_env import s9_original_audit as s9

    # Even after independently reviewed S9 bytes, R2 must have an
    # original source envelope: the mock fixture alone cannot be promoted.
    original_audit = r6.audit
    monkeypatch.setattr(s9, "audit", lambda root: original_audit(
        root, expected=case["expected"],
    ))
    with pytest.raises(r4.R4Rejected, match="predecode received bridge"):
        r4.audit(**case["kwargs"])
    rename_original(case, "primary", r4.S7_RAW_RECEIVED)
    x = r4.audit(**case["kwargs"])
    assert x["classification"] == "RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY"
    assert x["s9_original_source_readback"] == "REVIEW_ONLY_BYTES_MATCH"
    assert x["v_admission_granted"] is False
    assert x["science_qualified"] is False
