"""W3 sealed Node stdout + unchanged existing Paper collector: DEV-only joins."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    BEGIN,
    TICK,
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.s49_paper_existing_sources_dev import (
    review_s49_existing_w3_paper_files_dev,
)
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3RawNodeStdoutCapture,
)
from adapters.mineflayer.self_world_stage_w4_logtap import (
    capture_w4_collector_cursor,
)
from test_mineflayer_process_session import started_line
from test_s49_paper_custody_dev import PLAYER, packet
from test_s49_paper_preaction_dev import pre_transcript, typed_owner


def _line(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _existing_w3(tmp_path, capture):
    root = tmp_path / "w3"
    root.mkdir()
    evidence = capture.projection.decoded_evidence
    session = capture.projection.session_id
    frames = [
        evidence[key] for key in (
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        )
    ]
    seqs = {frame["seq"]: (i, frame) for i, frame in enumerate(frames)}
    assert 0 not in seqs and len(seqs) == 4
    first = json.loads(started_line())
    first["session_id"] = session
    lines = [_line(first)]
    for seq in range(1, max(seqs) + 1):
        if seq in seqs:
            index, frame = seqs[seq]
            row = {k: v for k, v in frame.items() if k != "provenance"}
            row["type"] = "observation" if index in (0, 3) else "effect_result"
            if index in (0, 3) and row.get("request_id") is None:
                row.pop("request_id", None)
        else:
            row = {
                "type": "observation", "session_id": session,
                "seq": seq, "kind": "probe",
                "snapshot": frames[0]["snapshot"],
            }
        lines.append(_line(row))
    lines.append(_line({
        "type": "shutdown_ack", "session_id": session,
        "seq": max(seqs) + 1,
    }))
    writer = W3RawNodeStdoutCapture(root)
    decoder = MineflayerStreamDecoder()
    for raw in lines:
        writer.append_before_decode(raw)
        message = decoder.decode(raw.decode())
        writer.after_decoder(
            session_id=message.session_id, seq=message.seq,
            message_type=json.loads(raw)["type"],
        )
    writer.mark_eof()
    receipt = writer.seal(exit_code=0, reason="clean_shutdown")
    assert receipt["status"] == "COMPLETE_NODE_STDOUT"
    return root


def _files(tmp_path, capture, *, prefix=True, old=b"old unrelated\n"):
    root = _existing_w3(tmp_path, capture)
    path = tmp_path / "existing-single-paper-collector.log"
    path.write_bytes(old)
    cursor = capture_w4_collector_cursor(path)
    text = pre_transcript(capture)
    if prefix:
        text = "".join("[Server thread/INFO]: " + row
                       for row in text.splitlines(keepends=True))
    with path.open("ab") as f:
        f.write(text.encode())
    return root, path, cursor, packet(capture, paper_text=text)


def _review(capture, w3, cursor, archived):
    return review_s49_existing_w3_paper_files_dev(
        capture, w3_root=w3, paper_cursor=cursor, archive=archived,
        expected_player_uuid=PLAYER,
    )


def test_w3_and_paper_saved_producer_files_replay_without_source_grant(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    w3, _path, cursor, archived = _files(tmp_path, capture)
    out = _review(capture, w3, cursor, archived)
    assert out["status"] == "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
    assert out["session_id"] == capture.projection.session_id
    assert out["w3_frame_count"] >= 6
    assert set(out["w3_typed_frame_line_sha256"]) == {
        "before_observation", "dispatch_receipt",
        "cleanup_receipt", "after_observation",
    }
    assert out["paper_collector_start_byte"] == len(b"old unrelated\n")
    assert out["paper_collector_window_sha256"] == archived.paper_sha256
    assert out["raw_native_tcp_attested"] is False
    assert out["independent_collector_custody_attested"] is False
    assert out["cross_source_issuer_epoch_attested"] is False
    assert out["cross_clock_order_attested"] is False
    assert out["s49_clear_caused_paper_release"] == "NOT_ATTESTED"
    assert out["whole_tick_self_inactivity"] == "NOT_ATTESTED"
    assert out["source_bound_tick"] is None
    assert out["wait_interval_ref"] is None
    assert out["wait_ticks_admitted"] == 0
    assert out["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"


@pytest.mark.parametrize("mutation", [
    "native_wrong_receipt", "native_truncated", "native_missing",
    "native_session", "native_receipt_forged", "native_seq_corrupt",
    "native_effect_forged", "native_capture_symlink", "native_absent_root",
    "paper_old_only", "paper_replaced", "paper_truncated", "paper_symlink",
    "paper_hardlink", "paper_tampered", "paper_trailing_partial",
    "paper_replayed", "paper_different_bytes", "paper_invalid_utf8",
    "paper_wrong_session", "paper_foreign_run", "paper_wrong_world",
    "reader_labels_aliased", "native_archive_forged",
])
def test_w3_or_paper_producer_file_drift_fails_closed(
    monkeypatch, tmp_path, mutation,
):
    capture = typed_owner(monkeypatch)
    w3, path, cursor, archived = _files(tmp_path, capture)
    raw = w3 / "w3-node-stdout.raw.jsonl"
    receipt = w3 / "w3-node-stdout-receipt.json"
    if mutation == "native_wrong_receipt":
        receipt.write_bytes(receipt.read_bytes().replace(b"COMPLETE_NODE_STDOUT", b"INCOMPLETE_UNQUALIFIED"))
    elif mutation == "native_truncated":
        raw.write_bytes(raw.read_bytes()[:-1])
    elif mutation == "native_missing":
        raw.unlink()
    elif mutation == "native_session":
        receipt.write_bytes(receipt.read_bytes().replace(
            capture.projection.session_id.encode(), b"foreign", 1,
        ))
    elif mutation == "native_receipt_forged":
        receipt.write_bytes(receipt.read_bytes().replace(b"false", b"true", 1))
    elif mutation == "native_seq_corrupt":
        lines = raw.read_bytes().splitlines(keepends=True)
        lines[2] = lines[2].replace(b'"seq":2', b'"seq":7')
        raw.write_bytes(b"".join(lines))
    elif mutation == "native_effect_forged":
        raw.write_bytes(raw.read_bytes().replace(b"clear_controls", b"set_control", 1))
    elif mutation == "native_capture_symlink":
        other = tmp_path / "alias"
        other.symlink_to(w3, target_is_directory=True)
        w3 = other
    elif mutation == "native_absent_root":
        w3 = tmp_path / "absent"
    elif mutation == "paper_old_only":
        path.write_bytes(b"old unrelated\n")
    elif mutation == "paper_replaced":
        path.rename(tmp_path / "rotated-collector.log")
        path.write_bytes(archived.paper_log_bytes)
    elif mutation == "paper_truncated":
        path.write_bytes(b"")
    elif mutation == "paper_symlink":
        path.rename(tmp_path / "old-real-file.log")
        path.symlink_to(tmp_path / "old-real-file.log")
    elif mutation == "paper_hardlink":
        os.link(path, tmp_path / "hardlink.log")
    elif mutation == "paper_tampered":
        path.write_bytes(path.read_bytes().replace(b"back=false", b"back=true", 1))
    elif mutation == "paper_trailing_partial":
        with path.open("ab") as f:
            f.write(b"partial")
    elif mutation == "paper_replayed":
        with path.open("ab") as f:
            f.write(archived.paper_log_bytes)
    elif mutation == "paper_different_bytes":
        archived = replace(archived, paper_log_bytes=b"other bytes")
    elif mutation == "paper_invalid_utf8":
        path.write_bytes(path.read_bytes() + b"\xff\n")
    elif mutation == "paper_wrong_session":
        archived = packet(capture, paper_text=archived.paper_log_bytes.decode().replace(
            "session_id=" + capture.projection.session_id, "session_id=foreign", 1,
        ))
        path.write_bytes(b"old unrelated\n" + archived.paper_log_bytes)
    elif mutation == "paper_foreign_run":
        archived = packet(capture, paper_text=archived.paper_log_bytes.decode().replace(
            "run_id=12345678", "run_id=22345678", 1,
        ))
        path.write_bytes(b"old unrelated\n" + archived.paper_log_bytes)
    elif mutation == "paper_wrong_world":
        archived = packet(capture, paper_text=archived.paper_log_bytes.decode().replace(
            "world=paper-dev-world-s49", "world=foreign", 1,
        ))
        path.write_bytes(b"old unrelated\n" + archived.paper_log_bytes)
    elif mutation == "reader_labels_aliased":
        archived = replace(archived, paper_reader_label=archived.native_reader_label)
    else:
        archived = replace(archived, native_decoded_json=b"{}")
    with pytest.raises(BoundaryRejected):
        _review(capture, w3, cursor, archived)
    assert capture._executor.wait_phase == "NEW"


def test_only_log_bytes_after_prior_cursor_are_eligible(monkeypatch, tmp_path):
    capture = typed_owner(monkeypatch)
    w3 = _existing_w3(tmp_path, capture)
    old = pre_transcript(capture).encode()
    log = tmp_path / "existing-paper.log"
    log.write_bytes(old)
    after_existing = capture_w4_collector_cursor(log)
    with pytest.raises(BoundaryRejected):
        _review(capture, w3, after_existing, packet(capture))
    # Same bytes appended after cursor are structurally reviewable but
    # still unauthenticated producer-local content.
    with log.open("ab") as f:
        f.write(old)
    out = _review(capture, w3, after_existing, packet(capture))
    assert out["status"] == "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
    assert out["wait_ticks_admitted"] == 0


def test_existing_owner_projection_consumes_only_saved_w3_and_paper(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    w3, _file, cursor, archive = _files(tmp_path, capture, prefix=False)
    paper = archive.paper_log_bytes.decode()
    sliced = "\n".join(
        row for row in paper.splitlines()
        if row.startswith((BEGIN, TICK))
    ) + "\n"
    path = tmp_path / "owner-source-result.json"
    report = asyncio.run(project_s49_backward_paper_dev(
        capture, sliced, output_path=path, observer_transcript=paper,
        expected_player_uuid=PLAYER, require_preaction_edge=True,
        custody_archive=archive, w3_original_root=w3,
        paper_collector_cursor=cursor,
    ))
    assert json.loads(path.read_text()) == report
    assert report["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert report["producer_file_review"]["status"] == (
        "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
    )
    assert report["producer_file_review"]["s49_clear_caused_paper_release"] == (
        "NOT_ATTESTED"
    )
    assert report["source_bound_tick"] is None
    assert report["wait_interval_ref"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0


@pytest.mark.parametrize("case", ["without_archive", "without_cursor",
                                  "bad_capture"])
def test_owner_rejects_partial_or_forged_file_join_before_wait_arm(
    monkeypatch, tmp_path, case,
):
    capture = typed_owner(monkeypatch)
    w3, _file, cursor, archive = _files(tmp_path, capture, prefix=False)
    paper = archive.paper_log_bytes.decode()
    sliced = "\n".join(
        row for row in paper.splitlines()
        if row.startswith((BEGIN, TICK))
    ) + "\n"
    if case == "bad_capture":
        archive = replace(archive, paper_sha256="0" * 64)
    dest = tmp_path / "invalid-producer-join.json"
    with pytest.raises(BoundaryRejected):
        asyncio.run(project_s49_backward_paper_dev(
            capture, sliced, output_path=dest, observer_transcript=paper,
            expected_player_uuid=PLAYER, require_preaction_edge=True,
            custody_archive=None if case == "without_archive" else archive,
            w3_original_root=w3,
            paper_collector_cursor=None if case == "without_cursor" else cursor,
        ))
    data = json.loads(dest.read_text())
    assert data["status"] == "REJECTED_NOT_QUALIFIED"
    assert data["wait_interval_ref"] is None
    assert data["wait_ticks_admitted"] == 0
    assert data["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"
