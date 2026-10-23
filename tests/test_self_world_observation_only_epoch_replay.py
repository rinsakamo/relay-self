"""Synthetic source-bound W4 saved-record replay. No Minecraft or subprocesses."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyRawWorldMarker,
    review_observation_only_dev_offline,
)
from adapters.mineflayer.self_world_observation_only_entry import ObservationOnlyEntryInventory
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    W4OfflineEpochBlocked, replay_w4_saved_self_world_epochs,
)
from adapters.mineflayer.self_world_observation_only_lifetime import (
    join_observation_only_local_lifetime,
)
from adapters.mineflayer.self_world_observation_only_native_boundary import (
    NativeLocalDisposalReadback,
)
from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture
from relay_self.self_world import WorldPredictionReviewStatus

from test_self_world_stage_w4_prehost import _offline_lines

RUN = "0123456789abcdef"
MARKER = b"[21:00:00] [Server thread/INFO]: The time is 1234\n"


def _case(root: Path, *, target_before=False, later_kind="zombie"):
    """Only artificial W3 source frames; NEVER relabel them as a real W4 run."""
    root.mkdir()
    _, _, raws = _offline_lines()
    raws = list(raws)
    if target_before:
        for index, kind in ((3, "zombie"), (5, later_kind)):
            obj = json.loads(raws[index])
            if kind == "missing":
                obj["snapshot"]["nearby_entities"] = []
                obj["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 0
            else:
                obj["snapshot"]["nearby_entities"] = [{
                    "entity_id": 23, "name": kind, "entity_type": "mob",
                    "distance": 2.0,
                    "position": {"x": 2.0, "y": 64.0, "z": 0.0},
                }]
                obj["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 1
            raws[index] = (json.dumps(obj) + "\n").encode()
    decoder = MineflayerStreamDecoder()
    frames = [decoder.decode(raw.decode()) for raw in raws]
    for frame_type, seq in (("shutdown_ack", len(raws)),
                            ("connection_end", len(raws) + 1)):
        extra = {
            "type": frame_type, "session_id": frames[0].session_id,
            "seq": seq,
        }
        if frame_type == "connection_end":
            extra["reason"] = "synthetic test session ended"
        raws.append((json.dumps(extra) + "\n").encode())
    capture = W3RawNodeStdoutCapture(root)
    for raw in raws:
        msg = json.loads(raw)
        capture.append_before_decode(raw)
        capture.after_decoder(
            session_id=msg["session_id"], seq=msg["seq"],
            message_type=msg["type"],
        )
    capture.mark_eof()
    receipt = capture.seal(exit_code=0, reason="clean_shutdown")
    started, spawn, before, after = frames[0], frames[1], frames[3], frames[5]
    marker = ObservationOnlyRawWorldMarker(
        raw_start_byte=8, raw_end_byte=8 + len(MARKER),
        raw_sha256=hashlib.sha256(MARKER).hexdigest(), local_game_time=1234,
    )
    (root / "java-collector.raw").write_bytes(b"12345678" + MARKER)
    readback = review_observation_only_dev_offline(
        started=started, spawn=spawn, before=before, after=after,
        before_request=before.request_id, after_request=after.request_id,
        raw_marker_line=MARKER, marker_sha256=marker.raw_sha256,
        marker_after_before=True, after_marker=True,
    )
    inventory = ObservationOnlyEntryInventory(
        schema="W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1",
        exact_head="a" * 40, jar_sha256="b" * 64, bridge_sha256="c" * 64,
    )
    close = {
        "schema": "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1",
        "classification": "LOCAL_PRODUCER_CLOSE_ONLY",
        "node_exit": 0, "java_exit": 0,
        "node_stdout_receipt": receipt,
        "java_collector_settled": True, "java_stop_requested": True,
        "errors": [],
        "action_count": 0, "outcome_count": 0, "s10_update_count": 0,
        "external_custody_qualified": False,
        "physical_run_permitted": False, "science_qualified": False,
    }
    lifetime = join_observation_only_local_lifetime(
        inventory=inventory, readback=readback, marker=marker,
        close=close, node_raw_root=root,
    )
    disposal = NativeLocalDisposalReadback(
        schema="W4_OBSERVATION_ONLY_NATIVE_LOCAL_DISPOSAL_V1",
        java_pid=12001, node_pid=12002, boot_id="synthetic-only",
        port=25565, world_dir_name=f"w4-observe-{RUN}",
    )
    report = {
        "schema": "W4_OBSERVATION_ONLY_REAL_DEV_V1",
        "head": "a" * 40, "run_id": RUN,
        "status": "PASS", "verdict": "DEV_LOCAL_OBSERVATION_ONLY_PASS",
        "classification": "DEV_LOCAL_OBSERVATION_ONLY_PASS",
        "cleanup_confirmed": True, "world_root_removed": True,
        "collector_settled_normally": True, "port_released": True,
        "qualification_approved": False, "science_qualified": False,
        "external_grant_qualified": False,
        "action_count": 0, "outcome_count": 0, "s10_update_count": 0,
        "server_pid": 12001, "node_pid": 12002,
        "adapter_started": asdict(started),
        "spawn": asdict(spawn), "before": asdict(before), "after": asdict(after),
        "readback": asdict(readback), "marker": asdict(marker),
        "inventory": asdict(inventory), "close": close,
        "local_lifetime": asdict(lifetime), "local_disposal": asdict(disposal),
    }
    return report


def _pin(root, report):
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode()
    (root / "report.json").write_bytes(data)
    return dict(
        evidence_root=root, expected_report_sha256=hashlib.sha256(data).hexdigest(),
        expected_source_head="a" * 40, expected_run_id=RUN, self_id="A",
    )


def test_local_record_replays_two_epochs_without_claiming_cognition_action(tmp_path):
    root = tmp_path / "case"
    report = _case(root)
    replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
    assert replay.prior.session_id == replay.following.session_id
    assert replay.prior.epoch_id != replay.following.epoch_id
    assert replay.prior.observation.native_seq == 3
    assert replay.following.observation.native_seq == 5
    assert replay.prior.observation.source_ref != replay.following.observation.source_ref
    assert replay.source_scope == "LOCAL_DEV_SAVED_NODE_JSONL_NOT_MINECRAFT_TCP"
    assert replay.prediction_review is None  # No observed target, no invented prediction.
    assert replay.physical_action_count == replay.outcome_count == replay.s10_update_count == 0
    assert not replay.cognition_route_executed and not replay.retained_memory_written
    assert not replay.world_qualification and not replay.science_qualified


@pytest.mark.parametrize("later,expected", [
    ("zombie", WorldPredictionReviewStatus.MATCH),
    ("skeleton", WorldPredictionReviewStatus.MISMATCH),
    ("missing", WorldPredictionReviewStatus.UNDETERMINED),
])
def test_observed_target_review_is_epistemic_only(tmp_path, later, expected):
    root = tmp_path / later
    report = _case(root, target_before=True, later_kind=later)
    replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
    assert replay.prior_attention.considered_count == 1
    assert len(replay.prior_attention.selected) == 1
    assert replay.prediction_review.status is expected
    assert replay.prediction_review.target_ref == "entity-23"
    assert replay.prediction_review.later_observation_ref == (
        replay.following.observation.source_ref
    )
    if later == "missing":
        assert replay.prediction_review.observed_value is None


def test_source_gap_is_undetermined_not_a_prediction_error_reward(tmp_path):
    root = tmp_path / "bounded"
    report = _case(root, target_before=True)
    kwargs = _pin(root, report)
    replay = replay_w4_saved_self_world_epochs(**kwargs, max_native_seq_gap=1)
    assert replay.prediction_review.status is WorldPredictionReviewStatus.UNDETERMINED
    assert replay.prediction_review.reason_code == "source_gap_beyond_explicit_bound"


@pytest.mark.parametrize("attack", [
    "wrong_pin", "changed_report", "changed_w3", "missing_w3", "changed_java",
    "false_pass", "nonzero_action", "no_disposal", "wrong_phase",
    "wrong_close", "wrong_source", "foreign_session", "bad_marker",
    "forged_qual", "other_run", "bad_receipt", "missing_report",
])
def test_replay_refuses_source_changes_and_false_promotion(tmp_path, attack):
    root = tmp_path / "case"
    report = _case(root, target_before=True)
    kwargs = _pin(root, report)
    if attack == "wrong_pin":
        kwargs["expected_report_sha256"] = "f" * 64
    elif attack == "changed_report":
        (root / "report.json").write_bytes(b"{}\n")
    elif attack == "changed_w3":
        with (root / "w3-node-stdout.raw.jsonl").open("ab") as f:
            f.write(b"{}\n")
    elif attack == "missing_w3":
        (root / "w3-node-stdout.raw.jsonl").unlink()
    elif attack == "changed_java":
        (root / "java-collector.raw").write_bytes(b"12345678" + b"fake\n")
    elif attack == "false_pass":
        report["status"] = "FAIL"
    elif attack == "nonzero_action":
        report["action_count"] = 1
    elif attack == "no_disposal":
        report["world_root_removed"] = False
    elif attack == "wrong_phase":
        report["before"] = report["after"]
    elif attack == "wrong_close":
        report["close"]["node_exit"] = 1
    elif attack == "wrong_source":
        report["readback"]["before_seq"] = 7
    elif attack == "foreign_session":
        report["after"]["session_id"] = "foreign"
    elif attack == "bad_marker":
        report["marker"]["raw_sha256"] = "0" * 64
    elif attack == "forged_qual":
        report["qualification_approved"] = True
    elif attack == "other_run":
        report["run_id"] = "fedcba9876543210"
    elif attack == "bad_receipt":
        report["local_lifetime"]["session_id"] = "foreign"
    else:
        (root / "report.json").unlink()
    if attack in {
        "false_pass", "nonzero_action", "no_disposal", "wrong_phase",
        "wrong_close", "wrong_source", "foreign_session", "bad_marker",
        "forged_qual", "other_run", "bad_receipt",
    }:
        kwargs = _pin(root, report)  # Even an attacker-re-pinned report is rejected.
    with pytest.raises(W4OfflineEpochBlocked):
        replay_w4_saved_self_world_epochs(**kwargs)


def test_replay_is_read_only_no_process_or_world(monkeypatch, tmp_path):
    import asyncio

    async def forbid(*args, **kwargs):
        raise AssertionError("replay may not start Java, Node, Action or World")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbid)
    root = tmp_path / "case"
    report = _case(root)
    pins = _pin(root, report)
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir() if p.is_file()
    }
    replay_w4_saved_self_world_epochs(**pins)
    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir() if p.is_file()
    }
    assert before == after
