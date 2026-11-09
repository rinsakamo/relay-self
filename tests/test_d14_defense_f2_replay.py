"""F2 counterfactual on immutable native W3 with a sheep bystander."""
from __future__ import annotations

import hashlib
import json

from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture
from test_d14_defense_f1_replay import _raw_frame
from test_mineflayer_process_session import started_line
from tools.bug0_d14_defense_f1_replay import replay_w3_f1


def _with_sheep(raw_line: bytes) -> bytes:
    record = json.loads(raw_line)
    record["snapshot"]["nearby_entities"].append({
        "id": 19, "name": "sheep", "type": "mob", "distance": 2,
        "position": {"x": 2, "y": 64, "z": 0},
    })
    record["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 2
    return (json.dumps(record) + "\n").encode()


def test_f2_archived_native_replay_counts_bystander_reflex_without_action(tmp_path):
    raw = [
        started_line(),
        _with_sheep(_raw_frame(
            1, request="d14-r4-001-pre", health=20, distance=3.7,
        )),
        _with_sheep(_raw_frame(
            2, request="d14-r4-001-fresh", health=20, distance=3.5,
        )),
        _with_sheep(_raw_frame(
            3, request="d14-r4-002-pre", health=17, distance=2.5,
        )),
        _with_sheep(_raw_frame(
            4, request="d14-r4-002-fresh", health=17, distance=1.8,
        )),
        (
            json.dumps({"type": "shutdown_ack", "session_id": "session-1", "seq": 5})
            + "\n"
        ).encode(),
    ]
    recorder = W3RawNodeStdoutCapture(tmp_path)
    decoder = MineflayerStreamDecoder()
    for line in raw:
        recorder.append_before_decode(line)
        frame = decoder.decode(line.decode())
        recorder.after_decoder(
            session_id=frame.session_id, seq=frame.seq,
            message_type=(
                "adapter_started" if frame.seq == 0
                else "shutdown_ack" if frame.seq == 5
                else "MineflayerObservation"
            ),
        )
    recorder.mark_eof()
    assert recorder.seal(
        exit_code=0, reason="clean_shutdown",
    )["status"] == "COMPLETE_NODE_STDOUT"
    sha = hashlib.sha256(b"".join(raw)).hexdigest()
    recorded = (tmp_path / "w3-node-stdout.raw.jsonl").read_bytes()
    result = replay_w3_f1(
        tmp_path, expected_session="session-1",
        expected_w3_sha256=sha,
    )
    assert result["r9_stationary_pair_candidates"] == 0
    assert result["f1_health_loss_reactive_candidates"] == 0
    assert result["f2_single_zombie_with_known_bystanders_candidates"] == 1
    assert result["decision_rows"][1]["f2_native_target_candidate"] == 7
    assert result["decision_rows"][1]["f2_native_witness_seq"] == 2
    assert result["f2_original_s49_reactive_authority_exercised"] is False
    assert result["original_action_issued_or_outcome_proven_by_replay"] is False
    assert (tmp_path / "w3-node-stdout.raw.jsonl").read_bytes() == recorded
