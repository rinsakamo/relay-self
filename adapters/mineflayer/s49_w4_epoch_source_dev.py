"""W4 owner-local ACTION_READ epoch → previously checked W3/S16 frames, DEV.

An in-process W4DevLeasedSession audit records cooperative Python reader
operations. It is not an external process or issuer attestation; its task IDs,
epoch, and action binding cannot be authenticated from these bytes alone.
All output is non-admitting regardless of apparent shape validity.
"""
from __future__ import annotations

import re

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev
from adapters.mineflayer.self_world_stage_w4_lease import ReadAudit

_ORDER = ("before_observation", "dispatch_receipt",
          "cleanup_receipt", "after_observation")
_READ = ("ISSUE", "READ", "DECODED", "DELIVER", "READ_REVOKE")
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _subject(row: ReadAudit, *, epoch: int, phase: str, session: str) -> bool:
    return (
        type(row) is ReadAudit and type(row.epoch) is int
        and row.epoch == epoch and row.phase == phase
        and row.session_id == session
        and type(row.issuer) is str and _ID.fullmatch(row.issuer) is not None
        and type(row.reader) is str and _ID.fullmatch(row.reader) is not None
        and type(row.binding) is str and _ID.fullmatch(row.binding) is not None
        and row.detail == ""
    )


def review_s49_w4_read_epoch_dev(
    capture: S49TypedClosureCaptureDev, producer_review: dict,
    read_audit: tuple[ReadAudit, ...],
) -> dict:
    """Validate one narrow original-owner ACTION_READ audit slice.

    Expected: OPEN; four exact W3/S16 source-message receive operations;
    REVOKE; OPEN(HOST next epoch). Callers must not reconstruct this as an
    attested native read lease, real-process identity or cross-clock proof.
    """
    if (type(capture) is not S49TypedClosureCaptureDev
            or capture.state != "CAPTURED" or capture.projection is None
            or type(producer_review) is not dict
            or producer_review.get("schema")
            != "S49_EXISTING_W3_PAPER_PRODUCER_FILES_DEV_V1"
            or producer_review.get("status")
            != "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
            or type(read_audit) is not tuple or len(read_audit) != 23
            or any(type(row) is not ReadAudit for row in read_audit)):
        raise BoundaryRejected("requires bounded original S49/W3 producer and W4 local audit")
    native = capture.projection.decoded_evidence
    action, session = capture.projection.action_id, capture.projection.session_id
    if (producer_review.get("action_id") != action
            or producer_review.get("session_id") != session
            or producer_review.get("w3_receipt_session") != session
            or producer_review.get("w3_bytes_scope")
            != "NODE_BRIDGE_STDOUT_NOT_MINECRAFT_TCP"
            or producer_review.get("paper_bytes_scope")
            != "EXISTING_SERVER_CONSOLE_COLLECTOR_APPEND"
            or producer_review.get("independent_collector_custody_attested") is not False
            or producer_review.get("cross_source_issuer_epoch_attested") is not False
            or producer_review.get("raw_native_tcp_attested") is not False
            or producer_review.get("s49_clear_caused_paper_release") != "NOT_ATTESTED"):
        raise BoundaryRejected("producer evidence claims incorrect issuer authority")
    line_hashes = producer_review.get("w3_typed_frame_line_sha256")
    if (type(line_hashes) is not dict or set(line_hashes) != set(_ORDER)
            or any(type(value) is not str or _SHA.fullmatch(value) is None
                   for value in line_hashes.values())):
        raise BoundaryRejected("W3 source frame line hashes absent or malformed")
    frames = [native.get(key) for key in _ORDER]
    if (any(type(f) is not dict or type(f.get("seq")) is not int for f in frames)
            or not all(a["seq"] < b["seq"] for a, b in zip(frames, frames[1:]))):
        raise BoundaryRejected("typed original S16 has no monotonic frame sequence")
    open_row = read_audit[0]
    epoch = open_row.epoch
    if type(epoch) is not int or epoch < 2:
        raise BoundaryRejected("invalid local read epoch")
    if (not _subject(open_row, epoch=epoch, phase="ACTION_READ", session=session)
            or open_row.event != "OPEN" or open_row.binding != action
            or open_row.seq is not None):
        raise BoundaryRejected("missing same-Action read epoch OPEN")
    owner_task = open_row.reader
    actual_source_lines = {}
    for index, key in enumerate(_ORDER):
        group = read_audit[1 + 5 * index: 6 + 5 * index]
        expected_seq = frames[index]["seq"]
        if len(group) != 5 or tuple(row.event for row in group) != _READ:
            raise BoundaryRejected("W4 read operation incomplete, reordered or replayed")
        issuer = group[0].issuer
        read_task = group[1].reader
        if not all(
            _subject(row, epoch=epoch, phase="ACTION_READ", session=session)
            and row.binding == action and row.issuer == issuer
            and (row.reader == read_task if row.event in {"READ", "DECODED", "DELIVER", "READ_REVOKE"}
                 else row.reader == issuer)
            for row in group
        ):
            raise BoundaryRejected("W4 read issuer/Task/epoch mismatch")
        if (any(row.seq is not None for row in (group[0], group[1], group[4]))
                or type(group[2].seq) is not int or type(group[3].seq) is not int
                or group[2].seq != expected_seq or group[3].seq != expected_seq
                or read_task != group[2].reader or read_task != group[3].reader):
            raise BoundaryRejected("W4 decoded/delivered seq not the original S16 source")
        actual_source_lines[key] = line_hashes[key]
    end, next_open = read_audit[-2:]
    if (not _subject(end, epoch=epoch, phase="ACTION_READ", session=session)
            or end.event != "REVOKE" or end.binding != action
            or end.reader != owner_task or end.seq is not None
            or not _subject(next_open, epoch=epoch + 1, phase="HOST", session=session)
            or next_open.event != "OPEN" or next_open.reader != owner_task
            or next_open.seq is not None):
        raise BoundaryRejected("read lease not closed into fresh HOST epoch")
    # The audit is a local Python capability history. No external identity.
    return {
        "schema": "S49_W4_LOCAL_READ_EPOCH_SOURCE_DEV_V1",
        "status": "LOCAL_ACTION_READ_EPOCH_SHAPE_ONLY",
        "action_id": action,
        "session_id": session,
        "local_read_epoch": epoch,
        "local_reader_task_claim": owner_task,
        "local_s16_seq": [item["seq"] for item in frames],
        "w3_typed_frame_line_sha256": actual_source_lines,
        "lease_source": "W4DEV_IN_PROCESS_READ_AUDIT_UNAUTHENTICATED",
        "native_tcp_attested": False,
        "os_process_identity_attested": False,
        "issuer_principal_attested": False,
        "read_epoch_independently_attested": False,
        "cross_source_issuer_epoch_attested": False,
        "external_custody_qualified": False,
        "s49_clear_caused_paper_release": "NOT_ATTESTED",
        "server_effective_control_release": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
