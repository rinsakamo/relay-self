"""L14: synthetic original byte-shaped single-Action receipt windows + real no-go."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

import test_l13_independent_goal_receipt as l13
from adapters.mineflayer.l12_archived_action_progress_no_reward_dev import (
    audit_l12_real_action_goal_gate,
)
from adapters.mineflayer.python_protocol import (
    encode_clear_controls,
    encode_observe,
)
from relay_self.l13_independent_goal_receipt import L13ReceiptStatus
from relay_self.l14_original_bridge_goal_window import (
    L14SourceRejected,
    audit_l14_native_goal_window,
)


def _index(received: bytes, sent: bytes):
    return {
        "schema": "SELF_S7_RAW_MINEFLAYER_JSONL_RECEIPT_V1",
        "received_path": "/synthetic/received.jsonl",
        "sent_path": "/synthetic/sent.jsonl",
        "received_sha256": hashlib.sha256(received).hexdigest(),
        "sent_sha256": hashlib.sha256(sent).hexdigest(),
        "received_bytes": len(received), "sent_bytes": len(sent),
        "received_lines": len(received.splitlines()),
        "sent_lines": len(sent.splitlines()),
        "received_measured_before_decode": True,
        "sent_measured_before_write": True,
        "minecraft_tcp_packet_bytes": False,
        "native_execution_ack_attested": False,
        "v_science_qualified": False,
    }


def _native_postprobe(item, seq: int, px: float, pz: float) -> bytes:
    native = item.native
    p = native.observation
    return l13.native_line(replace(
        native, observation=replace(
            p, seq=seq, request_id=f"goal-probe-{seq}",
            snapshot=replace(
                p.snapshot,
                position=replace(p.snapshot.position, x=px, z=pz),
            ),
        ),
    ))


def source(*, status="REACHED"):
    item, adm, current = l13.fixture(seq=1, result=status)
    p = item.native.observation.snapshot.position
    x, z = p.x + 0.8, p.z + 0.8
    if status == "NOT_REACHED":
        x += 2.0
    first = _native_postprobe(item, 3, x, z)
    if status == "UNDETERMINED":
        second = _native_postprobe(item, 4, x+3, z+3)
    else:
        second = _native_postprobe(item, 4, x+0.005, z)
    started = l13.raw({
        "type": "adapter_started",
        "session_id": item.native.observation.session_id, "seq": 0,
        "mineflayer_version": "4.39.0",
        "config": {
            "host": "127.0.0.1", "port": 25565,
            "username": "RelaySelf", "version": None,
        },
    })
    effect = l13.raw({
        "type": "effect_result", "session_id": item.native.observation.session_id,
        "seq": 2, "action_id": item.action.action_id,
        "effect": "clear_controls", "result": "applied", "error": None,
    })
    received = started + item.raw_native_probe + effect + first + second
    sent = (
        encode_clear_controls(item.action.action_id)
        + encode_observe("goal-probe-3")
        + encode_observe("goal-probe-4")
    ).encode()
    external = l13.raw({
        "schema": "L14_PREDECLARED_SPATIAL_GOAL_V1",
        "session_id": item.native.observation.session_id,
        "action_id": item.action.action_id,
        "criterion_id": "independent-spatial-criterion-001",
        "owner_ref": adm.goal_owner,
        "created_before_seq": 0,
        "target_x": p.x+0.8, "target_z": p.z+0.8,
        "tolerance_m": 0.49, "stable_probe_delta_max_m": 0.05,
    })
    return {
        "received_original": received, "sent_original": sent,
        "s7_source_receipt": _index(received, sent),
        "external_criterion_original": external,
        "independently_admitted_criterion_sha256":
            frozenset({hashlib.sha256(external).hexdigest()}),
        "item": item, "admission": adm, "current": current,
    }


@pytest.mark.parametrize(("status", "expected", "label"), [
    ("REACHED", "REACHED", True),
    ("NOT_REACHED", "NOT_REACHED", False),
    ("UNDETERMINED", "UNDETERMINED", None),
])
def test_complete_original_bridge_and_independent_goal_criterion(status, expected, label):
    args = source(status=status)
    before = {k: v for k, v in args.items() if isinstance(v, bytes)}
    read = audit_l14_native_goal_window(**args)
    assert read.source_session_id == args["item"].native.observation.session_id
    assert read.before_native_seq == 1
    assert read.action_end_native_seq == 2
    assert read.goal_probe_seq == 3 and read.second_stable_probe_seq == 4
    assert read.observed_goal_status == expected
    assert read.criterion_matches_external_goal_result
    assert read.no_other_outbound_action_in_captured_bytes
    assert read.captured_native_effect_ack_for_action
    assert read.original_positive_present_sha256 == hashlib.sha256(
        args["item"].raw_native_probe,
    ).hexdigest()
    assert read.original_received_sha256 == hashlib.sha256(
        args["received_original"],
    ).hexdigest()
    assert read.original_sent_sha256 == hashlib.sha256(
        args["sent_original"],
    ).hexdigest()
    assert read.independent_physical_goal_authenticated is False
    assert read.native_tcp_authenticated is False
    assert read.actual_intervention_absence_proven is False
    assert not read.physical_learning_attested
    assert read.qualified_real_learning_pairs == 0
    assert read.s10_updates == read.habit_grants == 0
    assert read.action_issues == read.new_worlds == 0
    if label is None:
        assert read.l13_source_shaped_candidate.status is L13ReceiptStatus.UNKNOWN_NO_GOAL_LABEL
        assert read.l13_source_shaped_candidate.goal_label is None
    else:
        assert read.l13_source_shaped_candidate.goal_label.goal_reached is label
    assert before == {k: v for k, v in args.items() if isinstance(v, bytes)}


@pytest.mark.parametrize("fault", [
    "received_sha", "sent_sha", "no_receipt",
    "received_count", "sent_count", "received_flag", "sent_flag",
    "wrong_s7_schema", "fake_tcp", "fake_ack",
    "lost_probe_4", "gapped_probe_4", "effect_wrong_action",
    "effect_rejected", "outbound_second_action", "outbound_other_type",
    "outbound_missing_action", "criterion_wrong_goal", "criterion_wrong_action",
    "criterion_wrong_owner", "criterion_after_present",
    "criterion_not_admitted", "criterion_ambiguous_duplicate",
    "goal_wrong_result", "probe_unstable_claimed_reached",
    "probe_missing_pre", "native_duplicate_key", "original_malformed_sent",
])
def test_fail_closed_on_source_criterion_and_outbound_controls(fault):
    kwargs = source()
    if fault in ("received_sha", "sent_sha"):
        key = "received_sha256" if fault == "received_sha" else "sent_sha256"
        kwargs["s7_source_receipt"] = {**kwargs["s7_source_receipt"], key: "a"*64}
    elif fault == "no_receipt":
        kwargs["s7_source_receipt"] = {}
    elif fault in ("received_count", "sent_count"):
        key = "received_lines" if fault == "received_count" else "sent_bytes"
        kwargs["s7_source_receipt"] = {**kwargs["s7_source_receipt"],
                                      key: kwargs["s7_source_receipt"][key]+1}
    elif fault in ("received_flag", "sent_flag"):
        key = ("received_measured_before_decode" if fault == "received_flag"
               else "sent_measured_before_write")
        kwargs["s7_source_receipt"] = {**kwargs["s7_source_receipt"], key: False}
    elif fault == "wrong_s7_schema":
        kwargs["s7_source_receipt"] = {**kwargs["s7_source_receipt"],
                                      "schema": "foreign"}
    elif fault in ("fake_tcp", "fake_ack"):
        key = ("minecraft_tcp_packet_bytes" if fault == "fake_tcp"
               else "native_execution_ack_attested")
        kwargs["s7_source_receipt"] = {**kwargs["s7_source_receipt"], key: True}
    elif fault.startswith("criterion_"):
        if fault == "criterion_not_admitted":
            kwargs["independently_admitted_criterion_sha256"] = frozenset()
        else:
            d = json.loads(kwargs["external_criterion_original"])
            change = {
                "criterion_wrong_goal": ("criterion_id", "wrong-criterion"),
                "criterion_wrong_action": ("action_id", "fake-action"),
                "criterion_wrong_owner": ("owner_ref", "s16-action-owner"),
                "criterion_after_present": ("created_before_seq", 1),
            }
            if fault == "criterion_ambiguous_duplicate":
                raw = kwargs["external_criterion_original"].replace(
                    b'"criterion_id":"independent-spatial-criterion-001",',
                    b'"criterion_id":"independent-spatial-criterion-001",'
                    b'"criterion_id":"different",',
                )
                assert raw != kwargs["external_criterion_original"]
            else:
                key, value = change[fault]
                d[key] = value
                raw = l13.raw(d)
            kwargs["external_criterion_original"] = raw
            kwargs["independently_admitted_criterion_sha256"] = frozenset({
                hashlib.sha256(raw).hexdigest(),
            })
    elif fault == "goal_wrong_result":
        d = json.loads(kwargs["item"].raw_external_goal)
        d["goal_status"] = "NOT_REACHED"
        altered = l13.raw(d)
        kwargs["item"] = replace(kwargs["item"], raw_external_goal=altered)
        kwargs["admission"] = replace(
            kwargs["admission"], admitted_goal_sha256=frozenset({
                hashlib.sha256(altered).hexdigest(),
            }),
        )
    else:
        received, sent = kwargs["received_original"], kwargs["sent_original"]
        lines = received.splitlines(keepends=True)
        if fault == "lost_probe_4":
            received = b"".join(lines[:4])
        elif fault == "gapped_probe_4":
            d = json.loads(lines[4])
            d["seq"] = 7
            received = b"".join(lines[:4]) + l13.raw(d)
        elif fault == "effect_wrong_action":
            d = json.loads(lines[2])
            d["action_id"] = "wrong-action"
            received = b"".join(lines[:2]) + l13.raw(d) + b"".join(lines[3:])
        elif fault == "effect_rejected":
            d = json.loads(lines[2])
            d["result"] = "rejected"
            d["error"] = "not applied"
            received = b"".join(lines[:2]) + l13.raw(d) + b"".join(lines[3:])
        elif fault == "probe_unstable_claimed_reached":
            d = json.loads(lines[4])
            d["snapshot"]["position"]["x"] += 0.5
            received = b"".join(lines[:4]) + l13.raw(d)
        elif fault == "probe_missing_pre":
            received = b"".join([lines[0], *lines[2:]])
        elif fault == "native_duplicate_key":
            d = lines[3].replace(b'"kind":"probe",',
                b'"kind":"probe","kind":"probe",')
            assert d != lines[3]
            received = b"".join(lines[:3]) + d + lines[4]
        elif fault == "outbound_second_action":
            sent += encode_clear_controls("intruding-action").encode()
        elif fault == "outbound_other_type":
            sent += l13.raw({"type": "shutdown"})
        elif fault == "outbound_missing_action":
            sent = encode_observe("goal-probe-3").encode()
        else:
            sent += b"not-json\n"
        kwargs["received_original"] = received
        kwargs["sent_original"] = sent
        kwargs["s7_source_receipt"] = _index(received, sent)
    with pytest.raises((ValueError, TypeError)):
        audit_l14_native_goal_window(**kwargs)


def test_old_real_g413_has_no_s7_independent_goal_originals():
    path = os.environ.get("L11_REAL_ORIGINAL_ZIP")
    if not path:
        pytest.skip("exact real archived G4.13 source not available")
    l12 = audit_l12_real_action_goal_gate(Path(path))
    assert l12.original_s49_action_rows == 11
    assert l12.independent_per_action_goal_receipts == 0
    assert l12.independent_native_s16_jsonl_receipts == 0
    assert l12.original_native_pre_action_world_body_receipts == 0
    assert l12.qualified_l10_training_pairs == 0
    # These real reports never secretly become a complete S7 raw stream.
    with pytest.raises((L14SourceRejected, TypeError, ValueError)):
        audit_l14_native_goal_window(
            received_original=b"", sent_original=b"",
            s7_source_receipt={}, external_criterion_original=b"",
            independently_admitted_criterion_sha256=frozenset(),
            item=None, admission=None, current=None,
        )
