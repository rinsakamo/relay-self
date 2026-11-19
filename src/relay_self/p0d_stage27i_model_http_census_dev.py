"""Stage27i: count exact owned Stage26/27 model HTTP requests from fsynced sources.

Distinct from a declaration that the L0 loop makes zero L1 calls. A caller
must take before/after snapshots and reject even incomplete extra POSTs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class Stage27iModelAuditRefusal(RuntimeError):
    """Original A/B model source or cumulative request count is untrusted."""


def census_stage27i_model_http(evidence: Path, *, lane, tickets) -> dict[str, object]:
    source = evidence / "original-model-http"
    if (
        evidence.is_symlink() or not evidence.is_dir()
        or source.is_symlink() or not source.is_dir()
        or type(tickets) is not dict or set(tickets) != {"A", "B"}
    ):
        raise Stage27iModelAuditRefusal("owned model source or tickets absent")
    ids = {sid: tickets[sid].request_id for sid in ("A", "B")}
    if any(type(v) is not str or not v for v in ids.values()) or len(set(ids.values())) != 2:
        raise Stage27iModelAuditRefusal("original A/B L1 model requests absent")
    expected: set[str] = set()
    source_receipts: dict[str, dict[str, object]] = {}
    for sid, request_id in ids.items():
        key = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
        expected.update((
            key + ".request.json", key + ".response.json",
            key + ".source.sha256.json",
        ))
        try:
            receipt = lane.provider.stage26_raw_receipt(request_id)
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            raise Stage27iModelAuditRefusal(
                "original A/B model HTTP source checksum unavailable"
            ) from exc
        source_receipts[sid] = {
            "request_id": request_id,
            "request_sha256": receipt.request_sha256,
            "response_sha256": receipt.response_sha256,
            "response_bytes": receipt.response_bytes,
        }
    files = tuple(sorted(source.iterdir(), key=lambda p: p.name))
    if any(path.is_symlink() or not path.is_file() for path in files):
        raise Stage27iModelAuditRefusal("model HTTP source not regular files")
    names = [path.name for path in files]
    return {
        "request_count": sum(x.endswith(".request.json") for x in names),
        "response_count": sum(x.endswith(".response.json") for x in names),
        "manifest_count": sum(x.endswith(".source.sha256.json") for x in names),
        "unexpected_files": sorted(set(names) - expected),
        "missing_files": sorted(expected - set(names)),
        "source_receipts": source_receipts,
        "model_http_source": str(source),
        "file_names_sha256": hashlib.sha256(json.dumps(
            names, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest(),
    }


def freeze_stage27i_model_http(
    evidence: Path, *, label: str, snapshot: dict[str, object],
) -> dict[str, object]:
    if (
        label not in ("before", "after")
        or type(snapshot) is not dict or evidence.is_symlink()
        or not evidence.is_dir()
    ):
        raise Stage27iModelAuditRefusal("model census evidence invalid")
    path = evidence / f"stage27i-model-http-{label}.json"
    raw = (json.dumps(snapshot, sort_keys=True, indent=2, allow_nan=False)
           + "\n").encode("utf-8")
    with path.open("xb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    folder_fd = os.open(evidence, os.O_RDONLY)
    try:
        os.fsync(folder_fd)
    finally:
        os.close(folder_fd)
    checksum = hashlib.sha256(raw).hexdigest()
    if path.read_bytes() != raw:
        raise Stage27iModelAuditRefusal("model HTTP census readback mismatch")
    return {"path": str(path), "sha256": checksum, "frozen_original": True}


def require_stage27i_two_initial_calls(snapshot: dict[str, object]) -> None:
    if (
        snapshot["request_count"] != 2
        or snapshot["response_count"] != 2
        or snapshot["manifest_count"] != 2
        or snapshot["missing_files"] or snapshot["unexpected_files"]
    ):
        raise Stage27iModelAuditRefusal(
            "original A/B L1 source includes an extra, missing or incomplete POST"
        )
