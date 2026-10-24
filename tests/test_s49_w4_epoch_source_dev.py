"""W4 in-process local read audit joined to pinned W3/Paper source: DEV."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    BEGIN,
    TICK,
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.s49_paper_existing_sources_dev import (
    review_s49_existing_w3_paper_files_dev,
)
from adapters.mineflayer.s49_w4_epoch_source_dev import (
    review_s49_w4_read_epoch_dev,
)
from adapters.mineflayer.self_world_stage_w4_lease import ReadAudit
from test_s49_paper_custody_dev import PLAYER
from test_s49_paper_existing_sources_dev import _files
from test_s49_paper_preaction_dev import typed_owner


def local_read_epoch(capture, *, epoch=5):
    """Synthetic W4DevLeasedSession audit *slice*, not a live lease."""
    session = capture.projection.session_id
    action = capture.projection.action_id

    def e(kind, *, phase="ACTION_READ", number=epoch, binding=action,
          issuer="1", reader="1", seq=None):
        return ReadAudit(kind, number, phase, binding, issuer, reader,
                         seq, "", session)

    result = [e("OPEN")]
    for key in ("before_observation", "dispatch_receipt",
                "cleanup_receipt", "after_observation"):
        seq = capture.projection.decoded_evidence[key]["seq"]
        result.extend((
            e("ISSUE"), e("READ", reader="2"),
            e("DECODED", reader="2", seq=seq),
            e("DELIVER", reader="2", seq=seq),
            e("READ_REVOKE", reader="2"),
        ))
    result.extend((e("REVOKE"),
                   e("OPEN", phase="HOST", number=epoch + 1,
                     binding="host")))
    assert len(result) == 23
    return tuple(result)


def setup(monkeypatch, tmp_path):
    capture = typed_owner(monkeypatch)
    w3, _path, cursor, archive = _files(
        tmp_path, capture, prefix=False,
    )
    producer = review_s49_existing_w3_paper_files_dev(
        capture, w3_root=w3, paper_cursor=cursor,
        archive=archive, expected_player_uuid=PLAYER,
    )
    return capture, w3, cursor, archive, producer


def review(capture, producer, rows):
    return review_s49_w4_read_epoch_dev(capture, producer, rows)


def test_w4_read_epoch_correlates_four_w3_stdout_s16_frames_without_grant(
    monkeypatch, tmp_path,
):
    capture, _w3, _cursor, _archive, producer = setup(monkeypatch, tmp_path)
    observed = review(capture, producer, local_read_epoch(capture))
    assert observed["status"] == "LOCAL_ACTION_READ_EPOCH_SHAPE_ONLY"
    assert observed["local_read_epoch"] == 5
    assert observed["local_s16_seq"] == [
        capture.projection.decoded_evidence[k]["seq"]
        for k in ("before_observation", "dispatch_receipt",
                  "cleanup_receipt", "after_observation")
    ]
    assert observed["w3_typed_frame_line_sha256"] == producer[
        "w3_typed_frame_line_sha256"
    ]
    for flag in ("native_tcp_attested", "os_process_identity_attested",
                 "issuer_principal_attested", "read_epoch_independently_attested",
                 "cross_source_issuer_epoch_attested", "external_custody_qualified",
                 "qualification_go", "science_go"):
        assert observed[flag] is False
    assert observed["s49_clear_caused_paper_release"] == "NOT_ATTESTED"
    assert observed["wait_interval_ref"] is None
    assert observed["source_bound_tick"] is None
    assert observed["wait_ticks_admitted"] == 0
    assert observed["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"


@pytest.mark.parametrize("case", [
    "missing_open", "duplicated_open", "missing_read", "missing_deliver",
    "missing_revoke", "missing_host", "duplicate_ack", "swapped_frames",
    "wrong_cleanup_seq", "same_read_twice", "reordered_events",
    "wrong_read_phase", "wrong_deliver_epoch", "different_action",
    "wrong_session", "wrong_reader", "wrong_issuer", "host_reader_changed",
    "denied", "stale_epoch", "closed_before_revoke", "foreign_bind",
    "fake_tcp", "fake_custody", "foreign_producer_session",
    "missing_w3_hash", "invalid_w3_hash", "changed_typed_source",
    "non_tuple", "non_audit", "bool_epoch", "read_seq_bool",
])
def test_w4_lease_epoch_drifts_fail_closed(monkeypatch, tmp_path, case):
    capture, _w3, _cursor, _archive, producer = setup(monkeypatch, tmp_path)
    rows = list(local_read_epoch(capture))
    if case == "missing_open":
        rows.pop(0)
    elif case == "duplicated_open":
        rows.insert(1, rows[0])
    elif case == "missing_read":
        rows.pop(2)
    elif case == "missing_deliver":
        rows.pop(4)
    elif case == "missing_revoke":
        rows.pop(-2)
    elif case == "missing_host":
        rows.pop()
    elif case == "duplicate_ack":
        rows.insert(9, rows[9])
    elif case == "swapped_frames":
        rows[3], rows[8] = rows[8], rows[3]
    elif case == "wrong_cleanup_seq":
        rows[13] = replace(rows[13], seq=rows[13].seq + 1)
    elif case == "same_read_twice":
        rows[8] = replace(rows[8], seq=rows[3].seq)
    elif case == "reordered_events":
        rows[8], rows[9] = rows[9], rows[8]
    elif case == "wrong_read_phase":
        rows[2] = replace(rows[2], phase="HOST")
    elif case == "wrong_deliver_epoch":
        rows[4] = replace(rows[4], epoch=6)
    elif case == "different_action":
        rows[6] = replace(rows[6], binding="other-action")
    elif case == "wrong_session":
        rows[8] = replace(rows[8], session_id="other-session")
    elif case == "wrong_reader":
        rows[3] = replace(rows[3], reader="foreign-reader")
    elif case == "wrong_issuer":
        rows[8] = replace(rows[8], issuer="foreign-issuer")
    elif case == "host_reader_changed":
        rows[-1] = replace(rows[-1], reader="new-reader")
    elif case == "denied":
        rows[7] = replace(rows[7], event="DENY")
    elif case == "stale_epoch":
        rows[-1] = replace(rows[-1], epoch=5)
    elif case == "closed_before_revoke":
        rows[-2] = replace(rows[-2], phase="CLOSED")
    elif case == "foreign_bind":
        rows[0] = replace(rows[0], binding="foreign")
    elif case == "fake_tcp":
        producer = {**producer, "raw_native_tcp_attested": True}
    elif case == "fake_custody":
        producer = {**producer, "independent_collector_custody_attested": True}
    elif case == "foreign_producer_session":
        producer = {**producer, "w3_receipt_session": "other"}
    elif case == "missing_w3_hash":
        hashes = dict(producer["w3_typed_frame_line_sha256"])
        hashes.pop("cleanup_receipt")
        producer = {**producer, "w3_typed_frame_line_sha256": hashes}
    elif case == "invalid_w3_hash":
        hashes = dict(producer["w3_typed_frame_line_sha256"])
        hashes["cleanup_receipt"] = "unsealed"
        producer = {**producer, "w3_typed_frame_line_sha256": hashes}
    elif case == "changed_typed_source":
        capture.projection.decoded_evidence["cleanup_receipt"]["seq"] += 9
    elif case == "non_tuple":
        pass
    elif case == "non_audit":
        rows[3] = {"event": "DECODED", "seq": rows[3].seq}
    elif case == "bool_epoch":
        rows[0] = replace(rows[0], epoch=True)
    elif case == "read_seq_bool":
        rows[3] = replace(rows[3], seq=True)
    with pytest.raises(BoundaryRejected):
        review(capture, producer, rows if case == "non_tuple" else tuple(rows))
    assert capture._executor.wait_phase == "NEW"


def test_owner_optional_w4_epoch_review_is_still_nonadmitting(
    monkeypatch, tmp_path,
):
    capture, w3, cursor, archive, _producer = setup(monkeypatch, tmp_path)
    paper = archive.paper_log_bytes.decode("utf-8")
    callbacks = "\n".join(
        row for row in paper.splitlines() if row.startswith((BEGIN, TICK))
    ) + "\n"
    dest = tmp_path / "owner-w4-audit.json"
    report = asyncio.run(project_s49_backward_paper_dev(
        capture, callbacks, output_path=dest,
        observer_transcript=paper, expected_player_uuid=PLAYER,
        require_preaction_edge=True, custody_archive=archive,
        w3_original_root=w3, paper_collector_cursor=cursor,
        w4_read_audit=local_read_epoch(capture),
    ))
    assert report == json.loads(dest.read_text())
    assert report["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert report["producer_file_review"]["status"] == (
        "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
    )
    assert report["w4_read_epoch_review"]["status"] == (
        "LOCAL_ACTION_READ_EPOCH_SHAPE_ONLY"
    )
    assert report["source_bound_tick"] is None
    assert report["wait_interval_ref"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0


@pytest.mark.parametrize("mode", ["no_files", "bad_epoch", "different_session"])
def test_owner_refuses_w4_claim_before_arming_original_s49(
    monkeypatch, tmp_path, mode,
):
    capture, w3, cursor, archive, _producer = setup(monkeypatch, tmp_path)
    paper = archive.paper_log_bytes.decode("utf-8")
    callbacks = "\n".join(
        row for row in paper.splitlines() if row.startswith((BEGIN, TICK))
    ) + "\n"
    records = list(local_read_epoch(capture))
    if mode == "bad_epoch":
        records[3] = replace(records[3], epoch=20)
    if mode == "different_session":
        records[4] = replace(records[4], session_id="different")
    path = tmp_path / "rejected-w4-audit.json"
    with pytest.raises(BoundaryRejected):
        asyncio.run(project_s49_backward_paper_dev(
            capture, callbacks, output_path=path,
            observer_transcript=paper, expected_player_uuid=PLAYER,
            require_preaction_edge=True, custody_archive=archive,
            w3_original_root=None if mode == "no_files" else w3,
            paper_collector_cursor=None if mode == "no_files" else cursor,
            w4_read_audit=tuple(records),
        ))
    result = json.loads(path.read_text())
    assert result["status"] == "REJECTED_NOT_QUALIFIED"
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"
