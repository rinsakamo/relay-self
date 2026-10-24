"""DEV-only host-clock sidecar: bounded, no-overwrite atomic evidence.

Only an original S49 already-delivered callback can populate the source rows.
Clock results do not attest motor start, source authenticity or cognition time.
"""
from __future__ import annotations

import json
import math
import os
import sys
import uuid
from pathlib import Path

from adapters.mineflayer.self_product_passive_views import (
    DEV_SELF_ID,
    MAX_PROBES,
    verify_passive_source_join,
)
from experiments.self_body_host_clock_passive_dev import HostClockOrigin
from experiments.self_body_host_clock_s49_liveprobe_dev import S49PassiveHostClockDEV

CLOCK_FILE = "self_host_clock.jsonl"
VIEWS_FILE = "self_views.jsonl"
MAX_BYTES = 65536
MAX_RECORDS = 2 * MAX_PROBES + 2


def host_clock_rows(owner: S49PassiveHostClockDEV) -> tuple[dict, ...]:
    """One snapshot; never manufacture a sample for an aborted callback."""
    if type(owner) is not S49PassiveHostClockDEV:
        raise ValueError("original passive clock adapter required")
    samples = [
        {
            "kind": "passive_host_clock_sample",
            "classification": "DEV_ONLY_NOT_QUALIFIED",
            "self_id": DEV_SELF_ID,
            "session_id": item.session_id,
            "native_seq": item.native_seq,
            "source_ref": item.source_ref,
            "clock_origin": item.origin.value,
            "sample_kind": item.sample_kind,
            "callback_elapsed_ns": item.callback_elapsed_ns,
            "callback_elapsed_ms": item.callback_elapsed_ms,
            "action_issued": False,
            "source_qualified": False,
            "physical_timing_attested": False,
        }
        for item in owner.timer.rows()
    ]
    failures = [
        {
            "kind": "passive_host_clock_error",
            "stage": item.stage,
            "error_type": item.error_type,
            "session_id": item.session_id,
            "native_seq": item.native_seq,
            "cancelled_or_interrupted": item.cancelled_or_interrupted,
        }
        for item in owner.failures()
    ]
    summary = {
        **owner.summary(),
        "kind": "passive_host_clock_summary",
        "source_qualified": False,
        "science_qualified": False,
        "clock_origin": owner.timer.origin.value,
        "self_id": DEV_SELF_ID,
        "session_id": owner.views.summary()["session_id"],
    }
    if len(samples) > MAX_PROBES or len(failures) > MAX_PROBES + 1:
        raise ValueError("unbounded callback sidecar")
    return (*samples, *failures, summary)


def atomic_write_jsonl_new(path: Path, rows: tuple[dict, ...]) -> None:
    """Create one complete sidecar in a prepared dir without replacing evidence."""
    if type(rows) is not tuple or not 1 <= len(rows) <= MAX_RECORDS:
        raise ValueError("invalid bounded record count")
    if any(type(row) is not dict for row in rows):
        raise ValueError("JSONL objects required")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("sidecar needs existing trusted directory")
    if path.exists() or path.is_symlink():
        raise FileExistsError("sidecar must not overwrite existing evidence")
    encoded = "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
                      for row in rows).encode("utf-8")
    if not encoded or len(encoded) > MAX_BYTES:
        raise ValueError("invalid bounded sidecar bytes")
    tmp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        # Atomic link-if-absent; never os.replace() over a protected file.
        os.link(tmp, path)
        directory = os.open(str(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        primary = sys.exc_info()[1]
        try:
            tmp.unlink(missing_ok=True)
        except BaseException as cleanup_error:
            if primary is None:
                raise
            primary.add_note("temporary sidecar cleanup: " + type(cleanup_error).__name__)


def verify_host_clock_source_join(
    native: dict, view_rows: list[dict], clock_rows: list[dict],
) -> bool:
    """Strict DEV receipt only; source/pair equivalence is NOT attestation."""
    if (type(native) is not dict or native.get("status") != "PASS"
            or type(native.get("server_exit")) is not int or native["server_exit"] != 0
            or type(native.get("node_exit")) is not int or native["node_exit"] != 0):
        return False
    if not verify_passive_source_join(native, view_rows):
        return False
    if type(clock_rows) is not list or len(clock_rows) != MAX_PROBES + 1:
        return False
    summary = clock_rows[-1]
    if type(summary) is not dict or any(
        (type(summary.get(k)) is not type(v) or summary.get(k) != v)
        for k, v in {
            "kind": "passive_host_clock_summary",
            "classification": "DEV_ONLY_NOT_QUALIFIED",
            "sample_kind": "PASSIVE_CALLBACK_PROCESSING_ONLY",
            "clock_origin": HostClockOrigin.PYTHON_PROCESS_MONOTONIC.value,
            "self_id": DEV_SELF_ID,
            "session_id": native["session_id"],
            "native_probes_joined": MAX_PROBES,
            "clock_samples": MAX_PROBES,
            "aborted_callbacks": 0,
            "advisory_failures": 0,
            "failure_overflow": 0,
            "legacy_error_overflow": 0,
            "additional_native_receives": 0,
            "additional_native_probes": 0,
            "action_issuer": "EXISTING_S49_ONLY",
            "physical_timing_attested": False,
            "cognition_time_attested": False,
            "source_qualified": False,
            "science_qualified": False,
            "s10_updates": 0,
            "memory_writes": 0,
        }.items()
    ):
        return False
    seen: set[tuple[str, int]] = set()
    requests: set[str] = set()
    previous_seq = -1
    previous_event = -1
    for sample, view, pair in zip(
        clock_rows[:-1], view_rows[:-1], native["source_pair_trace"], strict=True,
    ):
        if type(sample) is not dict:
            return False
        ns = sample.get("callback_elapsed_ns")
        ms = sample.get("callback_elapsed_ms")
        if (
            view.get("self_id") != DEV_SELF_ID
            or type(view.get("native_seq")) is not int
            or view["native_seq"] <= previous_seq
            or pair["event_seq"] <= previous_event
            or pair["event_seq"] >= pair["probe_seq"]
            or view["request_id"] in requests
            or sample.get("kind") != "passive_host_clock_sample"
            or sample.get("classification") != "DEV_ONLY_NOT_QUALIFIED"
            or sample.get("sample_kind") != "PASSIVE_CALLBACK_PROCESSING_ONLY"
            or sample.get("clock_origin")
            != HostClockOrigin.PYTHON_PROCESS_MONOTONIC.value
            or sample.get("self_id") != DEV_SELF_ID
            or sample.get("session_id") != view["session_id"]
            or type(sample.get("native_seq")) is not int
            or sample.get("native_seq") != view["native_seq"]
            or sample.get("source_ref") != view["body_source_ref"]
            or sample.get("action_issued") is not False
            or sample.get("source_qualified") is not False
            or sample.get("physical_timing_attested") is not False
            or type(ns) is not int or ns < 0 or ns >= 2**63
            or type(ms) is not float or not math.isfinite(ms)
            or ms != ns / 1_000_000
        ):
            return False
        key = (sample["session_id"], sample["native_seq"])
        if key in seen:
            return False
        seen.add(key)
        requests.add(view["request_id"])
        previous_seq = view["native_seq"]
        previous_event = pair["event_seq"]
    return True


def read_sidecar_jsonl(path: Path) -> list[dict]:
    """Bounded complete JSONL only; missing/partial pairs never yield a receipt."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symlink sidecar")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES or not raw.endswith(b"\n"):
        raise ValueError("incomplete or oversized JSONL")
    lines = raw.decode("utf-8").splitlines()
    if not 1 <= len(lines) <= MAX_RECORDS:
        raise ValueError("unbounded JSONL records")
    rows = [json.loads(line) for line in lines]
    if any(type(row) is not dict for row in rows):
        raise ValueError("JSONL objects required")
    return rows
