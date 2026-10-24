"""DEV-only replay of existing W3 Node stdout and W4 Paper log cursor.

The original W3 process session is the sole Node stdout reader. The
existing Paper collector is the sole server stdout reader. This only
examines *saved* producer files. Node stdout is NOT Minecraft TCP; the
collector is NOT independent R custody. No shared source clock is inferred.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.s49_paper_custody_dev import (
    S49PaperArchiveInputsDev,
    review_s49_paper_archive_dev,
)
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    audit_w3_sealed_stdout,
)
from adapters.mineflayer.self_world_stage_w4_logtap import (
    W4CollectorCursor,
    _tail_bytes,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked

_RAW_NAME = "w3-node-stdout.raw.jsonl"


def _sha(buf: bytes) -> str:
    return hashlib.sha256(buf).hexdigest()


def _typed_frame(value) -> dict:
    # Match the original lossless *decoded typed* S16 projection.
    result = json.loads(json.dumps(asdict(value), allow_nan=False))
    result["provenance"] = asdict(value.provenance)
    return result


def _replay_exact_s16_frames(raw: bytes, frames: dict, *, session: str) -> dict:
    decoder = MineflayerStreamDecoder()
    targets: dict[int, str] = {}
    for name, frame in frames.items():
        index = frame["seq"]
        if type(index) is not int or index in targets:
            raise BoundaryRejected("duplicate original typed S16 sequence")
        targets[index] = name
    found: dict[str, str] = {}
    for line in raw.splitlines(keepends=True):
        # W3 audit separately establishes whole-stream seq/session and EOF.
        msg = decoder.decode(line.decode("utf-8"))
        if msg.seq not in targets:
            continue
        kind = targets[msg.seq]
        if (msg.session_id != session
                or _typed_frame(msg) != frames[kind]
                or kind in found):
            raise BoundaryRejected("W3 decoded stdout frame differs from original S16")
        found[kind] = _sha(line)
    if set(found) != set(frames):
        raise BoundaryRejected("missing original S16 frame in W3 stdout")
    return found


def review_s49_existing_w3_paper_files_dev(
    capture: S49TypedClosureCaptureDev,
    *, w3_root: Path, paper_cursor: W4CollectorCursor,
    archive: S49PaperArchiveInputsDev, expected_player_uuid: str,
) -> dict:
    """Read sealed W3 + existing Paper append bytes, without any process I/O.

    Content can now be tied to locally retained producer files, not to an
    independently attested issuer, Minecraft packet or an external clock.
    """
    if (not isinstance(capture, S49TypedClosureCaptureDev)
            or capture.state != "CAPTURED" or capture.projection is None
            or not isinstance(w3_root, Path) or not w3_root.is_absolute()
            or any(path.is_symlink() for path in (w3_root, *w3_root.parents))
            or type(paper_cursor) is not W4CollectorCursor
            or not isinstance(archive, S49PaperArchiveInputsDev)):
        raise BoundaryRejected("S49 typed close and safe original source locators required")
    # Verify exactly the W3 project's unchanged original stdout + exit
    # receipt, rather than introducing a competing stream/reader.
    try:
        receipt = audit_w3_sealed_stdout(w3_root)
    except (W3CaptureRejected, OSError, ValueError) as exc:
        raise BoundaryRejected("original sealed W3 stdout audit rejected") from exc
    if receipt["session_id"] != capture.projection.session_id:
        raise BoundaryRejected("W3 archived session not original S49 session")
    raw = (w3_root / _RAW_NAME).read_bytes()
    if _sha(raw) != receipt["stdout_sha256"]:
        raise BoundaryRejected("W3 original changed after audit")
    decoded = capture.projection.decoded_evidence
    frames = {
        name: decoded[name] for name in (
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        )
    }
    try:
        matched = _replay_exact_s16_frames(
            raw, frames, session=capture.projection.session_id,
        )
    except (ValueError, TypeError, UnicodeError) as exc:
        raise BoundaryRejected("W3 original does not decode as S16 source") from exc
    # Keep the existing collector the sole server stdout reader.
    try:
        added = _tail_bytes(paper_cursor, paper_cursor.start_byte)
    except (W4PreworldBlocked, OSError, ValueError) as exc:
        raise BoundaryRejected("original Paper collector file invalid") from exc
    if (not added or len(added) > 65536 or not added.endswith(b"\n")
            or added != archive.paper_log_bytes):
        raise BoundaryRejected("Paper appended bytes differ from archived input")
    source = review_s49_paper_archive_dev(
        capture, archive, expected_player_uuid=expected_player_uuid,
    )
    if source["native_decoded_sha256"] != capture.projection.evidence_sha256:
        raise BoundaryRejected("typed S16 digest changed after archive review")
    return {
        "schema": "S49_EXISTING_W3_PAPER_PRODUCER_FILES_DEV_V1",
        "status": "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY",
        "action_id": source["action_id"],
        "session_id": source["session_id"],
        "world": source["paper_world"],
        "observer_run_id": source["paper_observer_run_id"],
        "w3_stdout_sha256": receipt["stdout_sha256"],
        "w3_receipt_session": receipt["session_id"],
        "w3_frame_count": receipt["frame_count"],
        "w3_typed_frame_line_sha256": matched,
        "paper_collector_start_byte": paper_cursor.start_byte,
        "paper_collector_end_byte": paper_cursor.start_byte + len(added),
        "paper_collector_window_sha256": _sha(added),
        "paper_collector_device": paper_cursor.device,
        "paper_collector_inode": paper_cursor.inode,
        "w3_bytes_scope": "NODE_BRIDGE_STDOUT_NOT_MINECRAFT_TCP",
        "paper_bytes_scope": "EXISTING_SERVER_CONSOLE_COLLECTOR_APPEND",
        "raw_native_tcp_attested": False,
        "independent_collector_custody_attested": False,
        "cross_source_issuer_epoch_attested": False,
        "cross_clock_order_attested": False,
        "s49_clear_caused_paper_release": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
