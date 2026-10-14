"""Fail-closed synthetic tests for R's separate B0 DEV original reader."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from experiments.standard_env import b0_dev_original_audit as r


def dump(x):
    return (json.dumps(x, sort_keys=True) + "\n").encode()


def fixture(tmp_path, *, edit=lambda n, c, p, d: None):
    root = tmp_path / "originals"
    root.mkdir()
    readback = tmp_path / "external-readback.json"
    frames = [
        {"type": "observation", "kind": "inventory", "session_id": r.SESSION,
         "seq": i, "snapshot": {"food": 13, "inventory": []}}
        for i in range(148)
    ]
    frames[0]["type"] = "adapter_started"
    for i, food, count in [(87, 13, 0), (88, 13, 0), (90, 13, 0),
                           (110, 13, 0), (111, 13, 0), (123, 13, 0),
                           (124, 13, 1), (134, 13, 1), (144, 17, 0),
                           (145, 17, 0)]:
        frames[i]["kind"] = "probe"
        frames[i]["snapshot"] = {"food": food, "inventory": [
            {"name": "rotten_flesh", "count": count}] if count else []}
    frames[145]["request_id"] = "b0-next-l0-native"
    frames[120] = {
        "type": "effect_result", "session_id": r.SESSION, "seq": 120,
        "action_id": "equip-child", "effect": "equip_item", "result": "applied",
    }
    frames[135] = {
        "type": "effect_result", "session_id": r.SESSION, "seq": 135,
        "action_id": "consume-child", "effect": "consume_held", "result": "applied",
    }
    frames[146]["type"] = "shutdown_ack"
    frames[147]["type"] = "connection_end"
    commands = [
        {"type": "observe", "request_id": "b0-next-l0-native"},
        {"type": "effect", "effect": "equip_item", "action_id": "equip-child",
         "item_name": "rotten_flesh"},
        {"type": "effect", "effect": "consume_held", "action_id": "consume-child"},
        {"type": "shutdown"},
    ]
    report = {
        "mode": "DEV", "classification": "DEV_ONLY",
        "status": "PASS", "owner_status": "PASS", "stage": "CLOSED",
        "session_id": r.SESSION, "food_source": "ground",
        "food_item": "rotten_flesh",
        "world_source": "NEW_DEV_MOJANG_WORLD_NOT_RSEE_GOLDEN",
        "engineering_qualified": False, "grant_consumed": False,
        "server_exit": 0, "node_exit": 0, "real_model_calls": 0,
        "ground_pickup": {
            "status": "PICKUP_SOURCE_CONSISTENT",
            "pickup_evidence": "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY",
            "pickup_inventory_delta": 1, "zombie_drop_observed": False,
            "item_contents_from_entity_metadata": "UNKNOWN",
            "m_energy_credited": False, "source_probe_seq": 87,
            "pickup_probe_seq": 124,
            "movement_outcomes": [
                {"action_id": f"b0-ground-seek-action-{j}", "before_seq": x,
                 "after_seq": y, "kind": "PROGRESSED"}
                for j, x, y in [(0, 88, 110), (1, 111, 123)]
            ],
        },
        "issued_action_id": "s51-eat-rotten_flesh",
        "action_terminal": "outcome",
        "before": {"probe_seq": 134},
        "after": {"action_id": "s51-eat-rotten_flesh", "after_seq": 144,
                  "terminal": "outcome"},
        "eat_outcome": {"action_id": "s51-eat-rotten_flesh",
                        "food_before": 13, "food_after": 17,
                        "count_before": 1, "count_after": 0},
        "metabolism_before_eat": {"energy": 5.0},
        "metabolism_after_eat": {"credited_action_id": "s51-eat-rotten_flesh",
                                 "credit_count": 1, "meals": 1, "intake": 4,
                                 "expenditure": 0.5, "energy": 8.5,
                                 "terminal": False},
        "next_native_probe": {"seq": 145},
        "next_l0": {"probe_seq": 145, "kind": "WAIT", "issued_action": False},
    }
    receipt = {
        "mode": "DEV", "classification": "DEV_ONLY", "scenario": "b0-ground",
        "run_id": r.RUN_ID, "session_id": r.SESSION,
        "git_head": r.S_HEAD, "world_source": "NEW_S51_DEV_WORLD_NOT_GOLDEN",
        "engineering_qualified": False, "science_success": False,
        "m_energy_credited": False, "g3_go": False, "stop_ack": "UNATTESTED",
        "decisions": 0, "native_actions": 0,  # historic S49 counters
        "dev_b0_m0_credit_count": None, "dev_b0_next_l0_kind": None,
    }
    edit(frames, commands, report, receipt)
    files = {
        "native_report.native.jsonl": b"".join(dump(x) for x in frames),
        "native_report.commands.jsonl": b"".join(dump(x) for x in commands),
        "minecraft_server.log": b"Done\n",
        "native_report.json": dump(report),
        "dev_receipt.json": dump(receipt),
        "host_stdout.log": b"ok\n",
        "host_stderr.log": b"",
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    shas = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    index = "".join(f"{sha}  {name}\n" for name, sha in sorted(shas.items())).encode()
    (root / "SHA256SUMS").write_bytes(index)
    rb = dump({"readback": "external corrections, not native qualification"})
    readback.write_bytes(rb)
    expect = replace(r.Expectations(),
                     shas={name: shas[name] for name in r.FILE_SHA},
                     index_sha=hashlib.sha256(index).hexdigest(),
                     indexed_count=len(files),
                     readback_sha=hashlib.sha256(rb).hexdigest())
    return root, readback, expect


def test_default_is_no_io(monkeypatch):
    monkeypatch.setattr(r, "_physical_receipt_root",
                        lambda _: pytest.fail("I/O in default plan"))
    assert r.plan()["dev_host_originals"] == "NOT_READ"
    assert r.main([]) == 0


def test_readonly_dev_audit_keeps_original_bytes(tmp_path):
    root, rb, expected = fixture(tmp_path)
    previous = {p: p.read_bytes() for p in root.iterdir()}
    previous[rb] = rb.read_bytes()
    a = r.audit(root, rb, expected)
    assert a == r.audit(root, rb, expected)
    assert a["native_rows"] == 148
    assert a["native_stop_ack_seq"] == 146
    assert a["issued_move_reports"] == 2
    assert a["m0_credits_reported"] == 1
    assert not a["golden_qualified"]
    assert not a["independent_normal_shutdown_qualified"]
    assert not a["science_go"]
    assert all(p.read_bytes() == raw for p, raw in previous.items())


@pytest.mark.parametrize("name,mutation", [
    ("foreign_session", lambda n, c, p, d: n[90].update(session_id="foreign")),
    ("duplicate_seq", lambda n, c, p, d: n[90].update(seq=89)),
    ("missing_ack", lambda n, c, p, d: n[146].update(type="observation")),
    ("duplicate_child", lambda n, c, p, d: c.insert(2, dict(c[1]))),
    ("unknown_consume", lambda n, c, p, d: n[135].update(result="rejected")),
    ("pickup_only", lambda n, c, p, d: p["metabolism_after_eat"].update(credit_count=0)),
    ("foreign_credit", lambda n, c, p, d: p["metabolism_after_eat"].update(
        credited_action_id="different-eat")),
    ("eat_unknown", lambda n, c, p, d: p.update(action_terminal="unknown")),
    ("forged_food", lambda n, c, p, d: n[144]["snapshot"].update(food=13)),
    ("forged_inventory", lambda n, c, p, d: n[124]["snapshot"].update(inventory=[])),
    ("foreign_world", lambda n, c, p, d: d.update(
        world_source="GOLDEN_COPY")),
    ("dev_escalation", lambda n, c, p, d: d.update(
        engineering_qualified=True)),
    ("fresh_probe_missing", lambda n, c, p, d: n[145].update(
        request_id="stale")),
])
def test_fail_closed_source_mismatch(tmp_path, name, mutation):
    root, rb, exp = fixture(tmp_path, edit=mutation)
    with pytest.raises(r.Rejected):
        r.audit(root, rb, exp)


def test_bytes_modified_after_index_are_rejected(tmp_path):
    root, rb, exp = fixture(tmp_path)
    (root / "native_report.json").write_bytes(b"{}\n")
    with pytest.raises(r.Rejected, match="SHA256"):
        r.audit(root, rb, exp)


def test_external_readback_modified_and_missing(tmp_path):
    root, rb, exp = fixture(tmp_path)
    rb.write_text('{"tampered":true}\n')
    with pytest.raises(r.Rejected, match="readback SHA"):
        r.audit(root, rb, exp)
    rb.unlink()
    with pytest.raises((ValueError, OSError)):
        r.audit(root, rb, exp)


def test_original_symlink_rejected(tmp_path):
    root, rb, exp = fixture(tmp_path)
    original = root / "native_report.native.jsonl"
    original.unlink()
    original.symlink_to(root / "native_report.commands.jsonl")
    with pytest.raises((ValueError, OSError)):
        r.audit(root, rb, exp)


def test_cli_incomplete_external_input_stops():
    assert r.main(["--root", "/tmp/fake"]) == 2
