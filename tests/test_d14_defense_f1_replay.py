"""F1 source-only archived W3 replay never mutates old World or fences."""
from __future__ import annotations

import hashlib
import json

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerStreamDecoder,
)
from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture
from test_mineflayer_process_session import observation_line, started_line
from tools.bug0_d14_defense_f1_replay import F1ReplayRejected, replay_w3_f1


def _raw_frame(seq, *, request, health, distance):
    value = json.loads(observation_line())
    value["seq"] = seq
    value["kind"] = "probe"
    value["request_id"] = request
    value["snapshot"]["health"] = health
    value["snapshot"]["nearby_entities"] = [{
        "id": 7, "name": "zombie", "type": "mob", "distance": distance,
        "position": {"x": distance, "y": 64, "z": 2},
    }]
    value["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 1
    return (json.dumps(value) + "\n").encode()


def _source(tmp_path):
    raw = [
        started_line(),
        _raw_frame(1, request="d14-r4-001-pre", health=20, distance=3.7),
        _raw_frame(2, request="d14-r4-001-fresh", health=20, distance=3.5),
        _raw_frame(3, request="d14-r4-002-pre", health=17, distance=2.5),
        _raw_frame(4, request="d14-r4-002-fresh", health=17, distance=1.8),
        (
            json.dumps({"type": "shutdown_ack", "session_id": "session-1", "seq": 5})
            + "\n"
        ).encode(),
    ]
    cap = W3RawNodeStdoutCapture(tmp_path)
    decoder = MineflayerStreamDecoder()
    for line in raw:
        cap.append_before_decode(line)
        frame = decoder.decode(line.decode())
        cap.after_decoder(
            session_id=frame.session_id, seq=frame.seq,
            message_type=(
                "adapter_started" if frame.seq == 0
                else "shutdown_ack" if frame.seq == 5 else "MineflayerObservation"
            ),
        )
    cap.mark_eof()
    receipt = cap.seal(exit_code=0, reason="clean_shutdown")
    assert receipt["status"] == "COMPLETE_NODE_STDOUT"
    return hashlib.sha256(b"".join(raw)).hexdigest()


def test_f1_old_w3_source_only_replay_finds_dynamic_reaction_without_action(tmp_path):
    original_sha = _source(tmp_path)
    original_data = (tmp_path / "w3-node-stdout.raw.jsonl").read_bytes()
    original_receipt = (tmp_path / "w3-node-stdout-receipt.json").read_bytes()
    result = replay_w3_f1(
        tmp_path, expected_session="session-1", expected_w3_sha256=original_sha,
    )
    assert result["status"] == "SOURCE_ONLY_COUNTERFACTUAL_NOT_REAL_WORLD"
    assert result["r12_complete_native_decision_pairs"] == 2
    assert result["r9_stationary_pair_candidates"] == 0
    assert result["f1_health_loss_reactive_candidates"] == 1
    assert result["decision_rows"][1]["all_diagnostic_failures"] == []
    assert result["decision_rows"][1]["native_zombies"][1][0]["id"] == 7
    assert result["decision_rows"][1]["f1_witness_seq"] == 2
    assert result["decision_rows"][1]["f1_candidate_health_loss"] == 3
    assert result["zombie_causality_attested"] is False
    assert result["original_action_issued_or_outcome_proven_by_replay"] is False
    assert result["new_world_created"] is False
    assert (tmp_path / "w3-node-stdout.raw.jsonl").read_bytes() == original_data
    assert (tmp_path / "w3-node-stdout-receipt.json").read_bytes() == original_receipt


def test_f1_original_w3_hash_and_session_are_mandatory(tmp_path):
    sha = _source(tmp_path)
    for session, digest in (("foreign", sha), ("session-1", "0" * 64)):
        with pytest.raises(F1ReplayRejected):
            replay_w3_f1(
                tmp_path, expected_session=session, expected_w3_sha256=digest,
            )


def test_f1_replay_refuses_corrupt_legacy_w3_raw_not_audit_pass(tmp_path):
    sha = _source(tmp_path)
    with (tmp_path / "w3-node-stdout.raw.jsonl").open("ab") as output:
        output.write(b"malformed-added-after-seal\n")
    with pytest.raises(F1ReplayRejected, match="NOT_COMPLETE"):
        replay_w3_f1(
            tmp_path, expected_session="session-1", expected_w3_sha256=sha,
        )
