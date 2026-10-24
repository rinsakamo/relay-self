"""Two-archive custody readiness: prevent digest/source laundering, no P1."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    BEGIN,
    TICK,
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.s49_paper_custody_dev import (
    NATIVE_MODE,
    PAPER_MODE,
    S49PaperArchiveInputsDev,
    review_s49_paper_archive_dev,
)
from test_s49_paper_preaction_dev import pre_transcript, typed_owner

PLAYER = "32345678-1234-4234-8234-123456789abc"


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def packet(capture, paper_text=None):
    decoded = json.dumps(
        capture.projection.decoded_evidence,
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    text = pre_transcript(capture) if paper_text is None else paper_text
    paper = text.encode("utf-8")
    return S49PaperArchiveInputsDev(
        native_decoded_json=decoded,
        paper_log_bytes=paper,
        native_sha256=_digest(decoded),
        paper_sha256=_digest(paper),
        native_reader_label="s49-owner-claimed-reader",
        paper_reader_label="paper-log-claimed-reader",
    )


def review(capture, archived):
    return review_s49_paper_archive_dev(
        capture, archived, expected_player_uuid=PLAYER,
    )


def test_two_buffers_correlate_content_but_not_causal_custody(monkeypatch):
    capture = typed_owner(monkeypatch)
    archived = packet(capture)
    result = review(capture, archived)
    assert result["status"] == "TWO_BUFFER_CONTENT_CORRELATED_ONLY"
    assert result["native_decoded_sha256"] == archived.native_sha256
    assert result["paper_log_sha256"] == archived.paper_sha256
    assert result["native_archive_type"] == NATIVE_MODE
    assert result["paper_archive_type"] == PAPER_MODE
    assert result["raw_native_wire_attested"] is False
    assert result["native_reader_attested"] is False
    assert result["paper_reader_attested"] is False
    assert result["independent_custody_attested"] is False
    assert result["cross_clock_order_attested"] is False
    assert result["s49_native_clear_caused_edge"] == "NOT_ATTESTED"
    assert result["source_bound_tick"] is None
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"


@pytest.mark.parametrize("case", [
    "native_digest", "paper_digest", "native_byte_mutation", "paper_byte_mutation",
    "native_forged_json", "noncanonical_native", "paper_utf8",
    "native_is_paper", "paper_is_native", "reader_collision",
    "reader_empty", "reader_control_char", "reader_wrong_type",
    "source_mode_fake_raw", "source_mode_fake_attested", "native_not_bytes",
    "paper_not_bytes", "oversized_native", "oversized_paper",
    "native_seq_forged", "native_cleanup_rejected",
    "foreign_paper_action", "paper_replay", "paper_abort",
])
def test_two_source_buffer_substitution_fails_closed(monkeypatch, case):
    capture = typed_owner(monkeypatch)
    archived = packet(capture)
    native = archived.native_decoded_json
    paper = archived.paper_log_bytes
    if case == "native_digest":
        archived = replace(archived, native_sha256="0" * 64)
    elif case == "paper_digest":
        archived = replace(archived, paper_sha256="0" * 64)
    elif case == "native_byte_mutation":
        archived = replace(archived, native_decoded_json=native + b" ")
    elif case == "paper_byte_mutation":
        archived = replace(archived, paper_log_bytes=paper + b" ")
    elif case == "native_forged_json":
        obj = json.loads(native)
        obj["cleanup_receipt"]["result"] = "rejected"
        forged = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        archived = replace(archived, native_decoded_json=forged,
                           native_sha256=_digest(forged))
    elif case == "noncanonical_native":
        forged = json.dumps(json.loads(native), indent=2).encode()
        archived = replace(archived, native_decoded_json=forged,
                           native_sha256=_digest(forged))
    elif case == "paper_utf8":
        forged = paper + b"\xff"
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    elif case == "native_is_paper":
        archived = replace(archived, native_decoded_json=paper,
                           native_sha256=_digest(paper))
    elif case == "paper_is_native":
        archived = replace(archived, paper_log_bytes=native,
                           paper_sha256=_digest(native))
    elif case == "reader_collision":
        archived = replace(archived,
                           paper_reader_label=archived.native_reader_label)
    elif case == "reader_empty":
        archived = replace(archived, paper_reader_label="")
    elif case == "reader_control_char":
        archived = replace(archived, paper_reader_label="paper\nforged")
    elif case == "reader_wrong_type":
        archived = replace(archived, native_reader_label=123)
    elif case == "source_mode_fake_raw":
        archived = replace(archived, native_capture_mode="NATIVE_RAW_WIRE")
    elif case == "source_mode_fake_attested":
        archived = replace(archived, paper_capture_mode="PAPER_ATTESTED")
    elif case == "native_not_bytes":
        archived = replace(archived, native_decoded_json=bytearray(native))
    elif case == "paper_not_bytes":
        archived = replace(archived, paper_log_bytes=paper.decode())
    elif case == "oversized_native":
        forged = b"x" * 262145
        archived = replace(archived, native_decoded_json=forged,
                           native_sha256=_digest(forged))
    elif case == "oversized_paper":
        forged = paper + b"x" * 65536
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    elif case == "native_seq_forged":
        obj = json.loads(native)
        obj["cleanup_receipt"]["seq"] = obj["dispatch_receipt"]["seq"]
        forged = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        archived = replace(archived, native_decoded_json=forged,
                           native_sha256=_digest(forged))
    elif case == "native_cleanup_rejected":
        capture.projection.decoded_evidence["cleanup_receipt"]["result"] = "rejected"
    elif case == "foreign_paper_action":
        forged = paper.replace(b"action_id=", b"action_id=forged", 1)
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    elif case == "paper_replay":
        forged = paper + paper
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    elif case == "paper_abort":
        forged = paper + b"S49_DEV_BACK_WAIT_ABORT reason=PLUGIN_DISABLED\n"
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    with pytest.raises(BoundaryRejected):
        review(capture, archived)


def _callback_slice(raw):
    return "\n".join(
        row for row in raw.splitlines() if row.startswith((BEGIN, TICK))
    ) + "\n"


def test_owner_archive_handoff_records_only_untrusted_byte_correspondence(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    archived = packet(capture)
    raw = archived.paper_log_bytes.decode()
    dest = tmp_path / "joined-archive.json"
    result = asyncio.run(project_s49_backward_paper_dev(
        capture, _callback_slice(raw), output_path=dest,
        observer_transcript=raw, expected_player_uuid=PLAYER,
        require_preaction_edge=True, custody_archive=archived,
    ))
    assert json.loads(dest.read_text()) == result
    assert result["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert result["two_buffer_archive_review"]["status"] == (
        "TWO_BUFFER_CONTENT_CORRELATED_ONLY"
    )
    assert result["two_buffer_archive_review"]["independent_custody_attested"] is False
    assert result["source_bound_tick"] is None
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0.0


@pytest.mark.parametrize("mode", ["no_prearm", "changed_paper", "changed_digest"])
def test_owner_handoff_invalid_archive_never_arms_wait(
    monkeypatch, tmp_path, mode,
):
    capture = typed_owner(monkeypatch)
    archived = packet(capture)
    original = archived.paper_log_bytes.decode()
    if mode == "changed_paper":
        forged = archived.paper_log_bytes + b"\n"
        archived = replace(archived, paper_log_bytes=forged,
                           paper_sha256=_digest(forged))
    if mode == "changed_digest":
        archived = replace(archived, native_sha256="f" * 64)
    dest = tmp_path / "rejected.json"
    with pytest.raises(BoundaryRejected):
        asyncio.run(project_s49_backward_paper_dev(
            capture, _callback_slice(original),
            output_path=dest, observer_transcript=original,
            expected_player_uuid=PLAYER,
            require_preaction_edge=mode != "no_prearm",
            custody_archive=archived,
        ))
    result = json.loads(dest.read_text())
    assert result["status"] == "REJECTED_NOT_QUALIFIED"
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"
