"""I1 original Paper ACK prefix selection: no World/Native/model execution.

These tests preserve the raw attached Paper log and verify the independent
auditor still refuses a non-line-terminated CPU digest. No SHA or ACK rewrite
of historical failed real-World originals is authorized.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from experiments.i_lane_i1_independent_cpu_audit_dev import (
    I1IndependentAuditHold,
    _audit_i1_epochs,
    _paper_prefixes,
)
from relay_self.stage28c2b_native_paper_body_link_dev import (
    Stage28NativePaperLinkHold,
    i1_complete_owned_paper_prefix,
)
from test_i_lane_i1_independent_cpu_audit_dev import _fixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def test_i1_original_attached_paper_prompt_only_uses_complete_ack_line():
    first = b"P0D_RESIDENT_READY boot=trusted\nP0D_TICK_ACK nonce=N1 source=PAPER_MAIN_THREAD\n"
    marker = b"P0D_TICK_ACK nonce=N1 source=PAPER_MAIN_THREAD"
    raw = first + b"> "
    original = raw[:]
    observed = i1_complete_owned_paper_prefix(raw, ack_marker=marker)
    assert observed == first
    assert raw == original
    assert _sha(observed) in _paper_prefixes(raw)
    assert _sha(raw) not in _paper_prefixes(raw)
    assert observed.endswith(b"\n")


def test_i1_original_console_prompt_bytes_are_not_normalized_or_rewritten():
    raw = b"ready\r\nP0D_TICK_ACK nonce=N1\r\n> "
    marker = b"P0D_TICK_ACK nonce=N1"
    full = i1_complete_owned_paper_prefix(raw, ack_marker=marker)
    assert full == b"ready\r\nP0D_TICK_ACK nonce=N1\r\n"
    assert full != raw
    assert _sha(full) in _paper_prefixes(raw)


@pytest.mark.parametrize("raw,marker", [
    (b"ready\nP0D_TICK_ACK nonce=N1", b"P0D_TICK_ACK nonce=N1"),
    (b"ready\nP0D_TICK_ACK nonce=N1> ", b"P0D_TICK_ACK nonce=N1"),
    (b"ready\n> ", b"P0D_TICK_ACK nonce=N1"),
    (b"ready\nP0D_TICK_ACK nonce=N", b"P0D_TICK_ACK nonce=N1"),
    (b"ready", b"ready"),
    (b"", b"ACK"),
    (b"ready\n", b""),
])
def test_i1_incomplete_or_missing_ack_never_promotes(raw, marker):
    with pytest.raises(Stage28NativePaperLinkHold):
        i1_complete_owned_paper_prefix(raw, ack_marker=marker)


def test_i1_source_projection_refuses_oversize_paper_stream():
    with pytest.raises(Stage28NativePaperLinkHold, match="unbounded"):
        i1_complete_owned_paper_prefix(
            b"ACK\n" + b">" * (64 * 1024 * 1024), ack_marker=b"ACK"
        )


def test_i1_realistic_paper_prompts_keep_independent_audit_strict(tmp_path: Path):
    report, evidence, executable, owners = _fixture(tmp_path)
    prestop = evidence / "prestop-paper-resident-owned.log"
    original = prestop.read_bytes()
    first_marker = b"P0D_TICK_ACK nonce=i1-nonce-1"
    second_marker = b"P0D_TICK_ACK nonce=i1-nonce-2"
    end_first = original.index(b"\n", original.index(first_marker)) + 1
    end_second = original.index(b"\n", original.index(second_marker)) + 1

    # At epoch 1 the console has already emitted a partial prompt; the same
    # bytes later precede epoch 2's valid independent Paper ACK line.
    epoch1_raw = original[:end_first] + b"> "
    new_frozen = (
        original[:end_first] + b"> " + original[end_first:end_second] + b"> "
    )
    first_canonical = i1_complete_owned_paper_prefix(
        epoch1_raw, ack_marker=first_marker,
    )
    second_canonical = i1_complete_owned_paper_prefix(
        new_frozen, ack_marker=second_marker,
    )
    assert first_canonical.endswith(b"\n")
    assert second_canonical.endswith(b"\n")
    assert epoch1_raw != first_canonical
    assert new_frozen != second_canonical
    assert _sha(epoch1_raw) not in _paper_prefixes(new_frozen)
    assert _sha(new_frozen) not in _paper_prefixes(new_frozen)

    prestop.write_bytes(new_frozen)
    (evidence / (report["paper_session_id"] + ".log")).write_bytes(
        new_frozen + b"Saved\nStopped\n"
    )
    records = report["i1_cpu_epochs"]["epochs"]
    for index, row in enumerate(records):
        chosen = first_canonical if index < 2 else second_canonical
        old = row["paper_log_sha256"]
        row["paper_log_sha256"] = _sha(chosen)
        row["source_revision_refs"][1] = row["source_revision_refs"][1].replace(
            old, _sha(chosen),
        )
    verdict = _audit_i1_epochs(
        report=report, evidence=evidence, executable=executable, owners=owners,
    )
    assert verdict["classification"] == (
        "I1_ORIGINAL_A_B_NATIVE_PAPER_CPU_SOURCE_AUDITED_DEV"
    )
    assert verdict["independent_paper_ack_per_epoch"]

    # Regress the exact previous bug: a byte-prefix SHA ending inside a live
    # console prompt is not line-complete and independent audit must HOLD,
    # even when the bytes occur literally in the frozen raw original.
    records[0]["paper_log_sha256"] = _sha(epoch1_raw)
    with pytest.raises(I1IndependentAuditHold, match="exact original Native probe"):
        _audit_i1_epochs(
            report=report, evidence=evidence, executable=executable,
            owners=owners,
        )
