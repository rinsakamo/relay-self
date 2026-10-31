"""W4 observation-only source/lifecycle local join; no physical World."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace

import pytest

from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyRawWorldMarker,
    review_observation_only_dev_offline,
)
from adapters.mineflayer.self_world_observation_only_entry import (
    ObservationOnlyEntryInventory,
)
from adapters.mineflayer.self_world_observation_only_lifetime import (
    ObservationOnlyLifetimeBlocked,
    join_observation_only_local_lifetime,
)
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3RawNodeStdoutCapture,
)
from test_self_world_observation_only_dev import _valid_review
from test_self_world_stage_w4_prehost import _offline_lines


def _case(tmp_path):
    params = _valid_review()
    typed = review_observation_only_dev_offline(**params)
    marker = ObservationOnlyRawWorldMarker(
        raw_start_byte=8,
        raw_end_byte=8 + len(params["raw_marker_line"]),
        raw_sha256=hashlib.sha256(params["raw_marker_line"]).hexdigest(),
        local_game_time=1234,
    )
    inventory = ObservationOnlyEntryInventory(
        schema="W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1",
        exact_head="a" * 40, jar_sha256="b" * 64,
        bridge_sha256="c" * 64,
    )
    # Original W3 stdout writer receives complete bytes BEFORE decode.
    # This is a standalone in-memory DEV capture, not a live bridge.
    _pre, _post, raw_frames = _offline_lines()
    del _pre, _post
    ack = (json.dumps({
        "type": "shutdown_ack", "session_id": typed.session_id,
        "seq": len(raw_frames),
    }) + "\n").encode()
    ended = (json.dumps({
        "type": "connection_end", "session_id": typed.session_id,
        "seq": len(raw_frames) + 1, "reason": "synthetic normal end",
    }) + "\n").encode()
    capture = W3RawNodeStdoutCapture(tmp_path)
    for raw in [*raw_frames, ack, ended]:
        payload = json.loads(raw)
        capture.append_before_decode(raw)
        capture.after_decoder(
            session_id=payload["session_id"], seq=payload["seq"],
            message_type=payload["type"],
        )
    capture.mark_eof()
    receipt = capture.seal(exit_code=0, reason="clean_shutdown")
    close = {
        "schema": "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1",
        "classification": "LOCAL_PRODUCER_CLOSE_ONLY",
        "node_exit": 0, "java_exit": 0,
        "node_stdout_receipt": receipt,
        "java_collector_settled": True, "java_stop_requested": True,
        "errors": [],
        "action_count": 0, "outcome_count": 0, "s10_update_count": 0,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "science_qualified": False,
    }
    return dict(
        inventory=inventory, readback=typed, marker=marker, close=close,
        node_raw_root=tmp_path,
    )


def test_lifetime_join_accepts_local_content_but_never_physical_authority(tmp_path):
    outcome = join_observation_only_local_lifetime(**_case(tmp_path))
    result = asdict(outcome)
    assert result["schema"] == "W4_OBSERVATION_ONLY_LOCAL_LIFETIME_JOIN_V1"
    assert result["before_seq"] == 3 and result["after_seq"] == 5
    assert result["local_game_time"] == 1234
    assert result["classification"] == "LOCAL_PRODUCER_LIFETIME_ONLY"
    assert result["exact_head"] == "a" * 40
    assert all(result[k] is False for k in (
        "external_grant_verified", "external_owner_attested",
        "external_source_qualified", "actual_pid_port_disposal_attested",
        "physical_run_permitted", "qualification_approved",
        "science_qualified",
    ))
    assert result["action_count"] == result["outcome_count"] == 0
    assert result["s10_update_count"] == 0


@pytest.mark.parametrize("fault", (
    "fake_inventory", "dirty_inventory", "grant_claim", "action_claim",
    "wrong_head", "foreign_marker", "malformed_marker", "marker_attested",
    "bad_probe", "stale_source", "missing_stop", "missing_collector",
    "java_nonzero", "node_nonzero", "node_without_ack", "node_no_eof",
    "foreign_node_session", "early_node_shutdown", "missing_scope",
    "external_custody_claim", "s10_claim", "incomplete_close", "missing_receipt",
    "tampered_raw_archive", "missing_raw_archive", "wrong_raw_root",
))
def test_lifetime_join_rejects_missing_or_spoofed_source(tmp_path, fault):
    case = _case(tmp_path)
    close = case["close"]
    receipt = close["node_stdout_receipt"]
    if fault == "fake_inventory":
        case["inventory"] = {"schema": case["inventory"].schema}
    elif fault == "dirty_inventory":
        case["inventory"] = replace(case["inventory"], disposition="PASS")
    elif fault == "grant_claim":
        case["inventory"] = replace(case["inventory"], external_grant_verified=True)
    elif fault == "action_claim":
        case["readback"] = replace(case["readback"], action_count=1)
    elif fault == "wrong_head":
        case["inventory"] = replace(case["inventory"], exact_head="unverified")
    elif fault == "foreign_marker":
        case["marker"] = replace(case["marker"], raw_sha256="0" * 64)
    elif fault == "malformed_marker":
        case["marker"] = replace(case["marker"], raw_end_byte=0)
    elif fault == "marker_attested":
        case["marker"] = replace(case["marker"], external_world_attested=True)
    elif fault == "bad_probe":
        case["readback"] = replace(case["readback"], after_seq=3)
    elif fault == "stale_source":
        case["readback"] = replace(case["readback"], before_source="spoof")
    elif fault == "missing_stop":
        close["java_stop_requested"] = False
    elif fault == "missing_collector":
        close["java_collector_settled"] = False
    elif fault == "java_nonzero":
        close["java_exit"] = 137
    elif fault == "node_nonzero":
        close["node_exit"] = 1
    elif fault == "node_without_ack":
        receipt["shutdown_ack_count"] = 0
    elif fault == "node_no_eof":
        receipt["eof_observed"] = False
    elif fault == "foreign_node_session":
        receipt["session_id"] = "foreign"
    elif fault == "early_node_shutdown":
        receipt["last_seq"] = case["readback"].after_seq
    elif fault == "missing_scope":
        receipt.pop("scope")
    elif fault == "external_custody_claim":
        receipt["external_source_independence_attested"] = True
    elif fault == "s10_claim":
        close["s10_update_count"] = 1
    elif fault == "incomplete_close":
        close["classification"] = "LOCAL_CLOSE_UNCONFIRMED"
    elif fault == "missing_receipt":
        close["node_stdout_receipt"] = None
    elif fault == "tampered_raw_archive":
        raw = tmp_path / "w3-node-stdout.raw.jsonl"
        raw.write_bytes(raw.read_bytes() + b"forged\n")
    elif fault == "missing_raw_archive":
        (tmp_path / "w3-node-stdout.raw.jsonl").unlink()
    elif fault == "wrong_raw_root":
        other = tmp_path / "unrelated-archive"
        other.mkdir()
        case["node_raw_root"] = other
    with pytest.raises(ObservationOnlyLifetimeBlocked):
        join_observation_only_local_lifetime(**case)


def test_lifetime_join_has_no_launcher_or_grant_argument(tmp_path):
    with pytest.raises(TypeError):
        join_observation_only_local_lifetime(**_case(tmp_path), grant=True)
