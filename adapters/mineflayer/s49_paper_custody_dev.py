"""Two-input, source-honest S49/Paper custody *readiness* screen (DEV).

The "native" input is a canonical serialization of already decoded S16
typed frames, not original Mineflayer wire bytes. The Paper input is supplied
log bytes, not independently attested Paper output. Reader labels and hashes
are self-declared; matching them never proves provenance or causality.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_preaction_dev import (
    review_s49_preaction_paper_dev,
)
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev
from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
READER_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
NATIVE_MODE = "S16_DECODED_TYPED_JSON_NOT_WIRE"
PAPER_MODE = "CALLER_PROVIDED_PAPER_LOG_NOT_CUSTODIED"


@dataclass(frozen=True, slots=True)
class S49PaperArchiveInputsDev:
    """Distinct declared inputs; no cryptographic proof of collection owner."""

    native_decoded_json: bytes
    paper_log_bytes: bytes
    native_sha256: str
    paper_sha256: str
    native_reader_label: str
    paper_reader_label: str
    native_capture_mode: str = NATIVE_MODE
    paper_capture_mode: str = PAPER_MODE


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ensure_ascii=True,
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def review_s49_paper_archive_dev(
    capture: S49TypedClosureCaptureDev,
    archive: S49PaperArchiveInputsDev, *,
    expected_player_uuid: str,
) -> dict:
    """Screen exact byte identity + two claimed readers. NEVER attest custody."""
    if (not isinstance(capture, S49TypedClosureCaptureDev)
            or capture.state != "CAPTURED" or capture.projection is None
            or not isinstance(archive, S49PaperArchiveInputsDev)):
        raise BoundaryRejected("typed original closure and two input buffers required")
    native, paper = archive.native_decoded_json, archive.paper_log_bytes
    if (type(native) is not bytes or type(paper) is not bytes
            or not 0 < len(native) <= 262144
            or not 0 < len(paper) <= 65536
            or archive.native_capture_mode != NATIVE_MODE
            or archive.paper_capture_mode != PAPER_MODE):
        raise BoundaryRejected("archive lacks bounded exact input kind")
    for digest, source in (
        (archive.native_sha256, native), (archive.paper_sha256, paper),
    ):
        if (not isinstance(digest, str)
                or not SHA256_PATTERN.fullmatch(digest)
                or not _sha(source) == digest):
            raise BoundaryRejected("declared source digest does not match bytes")
    for reader in (archive.native_reader_label, archive.paper_reader_label):
        if not isinstance(reader, str) or not READER_PATTERN.fullmatch(reader):
            raise BoundaryRejected("invalid claimed reader label")
    if archive.native_reader_label == archive.paper_reader_label:
        raise BoundaryRejected("same claimed reader for two logical sources")
    try:
        decoded = json.loads(native)
        if (not isinstance(decoded, dict)
                or _canonical_json(decoded) != native
                or decoded != capture.projection.decoded_evidence
                or _sha(native) != capture.projection.evidence_sha256):
            raise BoundaryRejected("decoded S16 archive differs from typed owner")
        verify_native_action_evidence(
            decoded, action_id=capture.projection.action_id,
            session_id=capture.projection.session_id,
            movement_m=decoded.get("movement_m"),
        )
    except (UnicodeDecodeError, ValueError, TypeError, NativeEvidenceRejected) as exc:
        raise BoundaryRejected("invalid typed S16 canonical bytes") from exc
    try:
        text = paper.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BoundaryRejected("invalid Paper text bytes") from exc
    if text.encode("utf-8") != paper:
        raise BoundaryRejected("Paper text byte roundtrip failed")
    paper_review = review_s49_preaction_paper_dev(
        capture, text, expected_player_uuid=expected_player_uuid,
    )
    if paper_review["original_text_sha256"] != archive.paper_sha256:
        raise BoundaryRejected("Paper parser did not preserve whole input digest")
    return {
        "schema": "S49_PAPER_TWO_BUFFER_CUSTODY_READINESS_DEV_V1",
        "status": "TWO_BUFFER_CONTENT_CORRELATED_ONLY",
        "session_id": paper_review["session_id"],
        "action_id": paper_review["action_id"],
        "paper_world": paper_review["world"],
        "paper_observer_run_id": paper_review["observer_run_id"],
        "native_decoded_sha256": archive.native_sha256,
        "paper_log_sha256": archive.paper_sha256,
        "native_reader_claim": archive.native_reader_label,
        "paper_reader_claim": archive.paper_reader_label,
        "native_archive_type": NATIVE_MODE,
        "paper_archive_type": PAPER_MODE,
        "raw_native_wire_attested": False,
        "native_reader_attested": False,
        "paper_reader_attested": False,
        "independent_custody_attested": False,
        "cross_clock_order_attested": False,
        "server_effective_control_release": "NOT_ATTESTED",
        "s49_native_clear_caused_edge": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
