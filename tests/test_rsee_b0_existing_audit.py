"""R B0 archived-original audit: deterministic source-shaped tests, no World."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from experiments.standard_env import b0_original_audit as r


def _serialize(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True) + "\n").encode()


def _fixture(tmp_path):
    native = [
        {"type": "adapter_started", "session_id": r.B0_SESSION, "seq": 0},
        *({"type": "observation", "session_id": r.B0_SESSION, "seq": n}
          for n in range(1, 4)),
        {"type": "shutdown_ack", "session_id": r.B0_SESSION, "seq": 4},
        {"type": "connection_end", "session_id": r.B0_SESSION, "seq": 5},
    ]
    episodes = []
    for n in range(2):
        aid = f"b0-multi-e{n}-eat-rotten_flesh"
        episodes.append({
            "epoch": n,
            "stage": "CLOSED",
            "eat_action_terminal": "outcome",
            "eat_action_id": aid,
            "eat_outcome": {
                "action_id": aid, "food_before": 13, "food_after": 17,
                "count_before": 1, "count_after": 0,
            },
            "metabolism_after_credit": {
                "credited_action_id": aid, "credit_count": n + 1,
                "meals": n + 1, "tick": (14, 21)[n], "energy": 8.5,
                "intake": 4, "terminal": False,
            },
            "ground_pickup": {
                "epoch": n, "item_entity_id": n + 2,
                "pickup_inventory_delta": 1,
                "item_contents_from_entity_metadata": "UNKNOWN",
                "zombie_drop_observed": False,
                "movement_outcomes": [
                    {"action_id": f"b0-e{n}-move-{i}",
                     "before_seq": 0, "after_seq": 1}
                    for i in range(2)
                ],
            },
            "next_l0": {"kind": "WAIT", "issued_action": False},
            "next_native_probe": {"seq": (2, 3)[n]},
        })
    report = {
        "status": "PASS", "stage": "CLOSED", "session_id": r.B0_SESSION,
        "food_source": "ground2", "food_item": "rotten_flesh",
        "classification": "B0_TWO_OPERATOR_STAGED_GROUND_EPOCHS_ENGINEERING_ONLY",
        "m_energy_credited": True, "server_exit": 0, "node_exit": 0,
        "real_model_calls": 0, "zombie_drop_observed": False,
        "rsee_preflight": {
            "jar_sha256": "2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7",
            "world_file_count": 26,
        },
        "two_ground_epochs": episodes,
        "metabolism_terminal": {
            "tick": 21, "meals": 2, "energy": 8.5, "terminal": False,
        },
    }
    files = {
        "physical.json": _serialize(report),
        "physical.native.jsonl": b"".join(_serialize(row) for row in native),
        "physical.commands.jsonl": _serialize({"type": "shutdown"}),
        "minecraft.log": b"server stopped\n",
    }
    return _write(tmp_path, files)


def _write(root, files):
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    digests = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    index = "".join(f"{digest}  {name}\n" for name, digest in sorted(digests.items()))
    (root / "SHA256SUMS").write_text(index)
    expected = r.ExpectedB0(
        r.B0_HEAD, r.B0_SESSION, digests,
        hashlib.sha256(index.encode()).hexdigest(),
        len(digests), 6, (2, 3), 4, 5,
    )
    return root, expected


def _mutate(root, name, mutation):
    files = {p.name: p.read_bytes() for p in root.iterdir()
             if p.is_file() and p.name != "SHA256SUMS"}
    files[name] = mutation(files[name])
    return _write(root, files)


def test_default_plan_does_not_access_host(monkeypatch):
    monkeypatch.setattr(r, "_physical_receipt_root", lambda _: pytest.fail("I/O"))
    assert r.plan()["b0_host_original_bytes"] == "NOT_READ"
    assert r.main([]) == 0


def test_source_shaped_bytes_review_and_repeat_read_only(tmp_path):
    root, expected = _fixture(tmp_path)
    pre = {p.name: p.read_bytes() for p in root.iterdir()}
    a = r.audit(root, expected=expected)
    b = r.audit(root, expected=expected)
    assert a == b
    assert a["classification"] == "RSEE_B0_ORIGINAL_BYTES_AND_REPORTED_EPOCHS_REVIEW_ONLY"
    assert a["indexed_files_sha256_checked"] == 4
    assert a["reported_issued_moves"] == 4
    assert a["reported_m0_credits"] == 2
    assert a["native_shutdown_ack_row"] == 4
    assert a["typed_s16_independent_semantics_attested"] is False
    assert a["science_qualified"] is False
    assert {p.name: p.read_bytes() for p in root.iterdir()} == pre


def test_unindexed_tamper_fails_even_if_report_still_pass(tmp_path):
    root, expected = _fixture(tmp_path)
    (root / "physical.native.jsonl").write_bytes(b"corruption\n")
    with pytest.raises(r.B0AuditRejected, match="SHA256"):
        r.audit(root, expected=expected)


def test_missing_native_ack_is_not_process_exit_ack(tmp_path):
    root, _ = _fixture(tmp_path)
    _, expected = _mutate(root, "physical.native.jsonl", lambda data:
        data.replace(b'"shutdown_ack"', b'"observation"'))
    with pytest.raises(r.B0AuditRejected, match="STOP ACK"):
        r.audit(root, expected=expected)


def test_changed_session_rejected_with_consistent_new_index(tmp_path):
    root, _ = _fixture(tmp_path)
    _, expected = _mutate(root, "physical.native.jsonl", lambda data:
        data.replace(r.B0_SESSION.encode(), b"foreign-session"))
    with pytest.raises(r.B0AuditRejected, match="session sequence"):
        r.audit(root, expected=expected)


def test_duplicate_json_key_rejected_even_with_rehashed_original(tmp_path):
    root, _ = _fixture(tmp_path)
    _, expected = _mutate(root, "physical.commands.jsonl", lambda _: b'{"type":"shutdown","type":"shutdown"}\n')
    with pytest.raises(r.B0AuditRejected, match="invalid/duplicate-key"):
        r.audit(root, expected=expected)


def test_fake_second_credit_not_accepted_with_matching_bytes(tmp_path):
    root, _ = _fixture(tmp_path)

    def fake_credit(raw):
        obj = json.loads(raw)
        obj["two_ground_epochs"][1]["metabolism_after_credit"]["credit_count"] = 1
        return _serialize(obj)

    _, expected = _mutate(root, "physical.json", fake_credit)
    with pytest.raises(r.B0AuditRejected, match="M0 credit"):
        r.audit(root, expected=expected)


def test_missing_native_file_and_symlink_denied(tmp_path):
    root, expected = _fixture(tmp_path)
    orig = root / "physical.native.jsonl"
    orig.unlink()
    with pytest.raises((ValueError, OSError)):
        r.audit(root, expected=expected)
    orig.symlink_to(root / "physical.commands.jsonl")
    with pytest.raises((ValueError, OSError)):
        r.audit(root, expected=expected)


def test_cannot_promote_foreign_head_or_derive_expectations_from_report(tmp_path):
    root, expected = _fixture(tmp_path)
    forged = replace(expected, producer_head="0" * 40)
    with pytest.raises(r.B0AuditRejected, match="HEAD/session"):
        r.audit(root, expected=forged)
    assert r.S_REPORTED.index_count == 50
    assert r.S_REPORTED.native_count == 172
