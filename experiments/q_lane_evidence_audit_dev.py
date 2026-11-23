"""Q Lane: independent *read-only* evidence/pin consistency gate (DEV only).

This gate validates captured files and simple cross-file identifiers. It does NOT
authenticate who produced the externally supplied pins; it does not run/replay
an Owner, Native Bridge, Paper, WAL writer or model, and it cannot certify a
real-World result. Original I1/Stage28/B/I4a verifiers remain authoritative
for their respective domain-specific checks on their exact source branches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping


class QEvidenceHold(ValueError):
    """Source, externally pinned bytes, or the claimed scope are not qualified."""


_ID_FIELDS = (
    "head", "world_uuid", "owner_id", "self_id",
    "native_session_id", "checkpoint_generation",
)
_SOURCE_FIELDS = {
    "native_request_id", "native_seq", "paper_nonce", "paper_tick",
    "paper_boot_id", "paper_session_id", "wal_action_id", "wal_status",
    "question_ref", "gpu_ticket_id",
}
_REQUIRED = {"native_stdin", "native_stdout", "paper_log", "paper_ack", "wal", "checkpoint"}
_OPTIONAL = {"question_adopts", "gpu_tickets"}
_ROLES = _REQUIRED | _OPTIONAL
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_MAX_BYTES = 32 * 1024 * 1024


def _exact(value: object, fields: set[str], what: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise QEvidenceHold(f"{what}: exact fields required")
    return value


def _nonblank(value: object, what: str) -> str:
    if type(value) is not str or not value or any(ch.isspace() for ch in value):
        raise QEvidenceHold(f"{what}: nonblank identity required")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise QEvidenceHold("SHA256 must be an exact lowercase hex digest")
    return value


def _raw_file(root: Path, name: object) -> bytes:
    """No symlink traversal, escape, file creation, truncation or write access."""
    if type(name) is not str or not name or Path(name).is_absolute():
        raise QEvidenceHold("artifact path must be relative")
    parts = Path(name).parts
    if any(p in ("..", ".") for p in parts) or not parts:
        raise QEvidenceHold("artifact path traversal")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise QEvidenceHold("symlink evidence is not admitted")
    # Open every ancestor relative to a held directory fd. Checking
    # path.is_symlink() alone is vulnerable to a directory replacement race.
    # O_NOFOLLOW on *every* segment protects even if a parent is swapped
    # between the earlier visual check and this source read.
    opened: list[int] = []
    try:
        no_follow = getattr(os, "O_NOFOLLOW", 0)
        dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow
        directory = os.open(root, dir_flags)
        opened.append(directory)
        for part in parts[:-1]:
            directory = os.open(part, dir_flags, dir_fd=directory)
            opened.append(directory)
        flags = os.O_RDONLY | no_follow | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(parts[-1], flags, dir_fd=directory)
        opened.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > _MAX_BYTES:
            raise QEvidenceHold("bounded regular file required")
        chunks: list[bytes] = []
        remaining = _MAX_BYTES + 1
        while remaining:
            piece = os.read(fd, min(1024 * 1024, remaining))
            if not piece:
                break
            chunks.append(piece)
            remaining -= len(piece)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if (
            len(data) > _MAX_BYTES or before.st_size != len(data)
            or (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
            != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
        ):
            raise QEvidenceHold("evidence changed while being read")
        return data
    except OSError as exc:
        raise QEvidenceHold(f"missing/unreadable evidence: {name}") from exc
    finally:
        for fd in reversed(opened):
            os.close(fd)


def _jsonl(raw: bytes, role: str) -> list[dict[str, Any]]:
    if not raw or not raw.endswith(b"\n"):
        raise QEvidenceHold(f"{role}: incomplete JSONL")
    try:
        rows = [json.loads(line) for line in raw.splitlines()]
    except (UnicodeError, ValueError) as exc:
        raise QEvidenceHold(f"{role}: malformed JSONL") from exc
    if any(type(row) is not dict for row in rows):
        raise QEvidenceHold(f"{role}: object rows required")
    return rows


def _native(raw: dict[str, bytes], *, source: dict[str, Any], session: str) -> None:
    commands = _jsonl(raw["native_stdin"], "native_stdin")
    replies = _jsonl(raw["native_stdout"], "native_stdout")
    request_id = source["native_request_id"]
    seq = source["native_seq"]
    if (
        type(seq) is not int or seq < 0
        or sum(
            row.get("type") == "observe" and row.get("request_id") == request_id
            for row in commands
        ) != 1
    ):
        raise QEvidenceHold("native outbound request missing/duplicated")
    previous = -1
    hits = 0
    for row in replies:
        current = row.get("seq")
        if (
            row.get("session_id") != session or type(current) is not int
            or current <= previous
        ):
            raise QEvidenceHold("foreign/old/reordered native session or sequence")
        previous = current
        if row.get("type") == "observation" and row.get("request_id") == request_id:
            if current != seq or row.get("kind") != "probe":
                raise QEvidenceHold("native source request/seq/kind mismatch")
            hits += 1
    if hits != 1:
        raise QEvidenceHold("native response correlation not one-to-one")


def _paper(raw: dict[str, bytes], source: dict[str, Any], world: str) -> None:
    log = raw["paper_log"]
    if not log.endswith(b"\n"):
        raise QEvidenceHold("Paper log must be frozen at a complete line")
    nonce = source["paper_nonce"]
    expected = {
        "nonce": nonce, "boot": source["paper_boot_id"],
        "session": source["paper_session_id"], "world": world,
        "tick": str(source["paper_tick"]), "source": "PAPER_MAIN_THREAD",
    }
    hits = 0
    for line in log.decode("utf-8").splitlines():
        if not line.startswith("P0D_TICK_ACK "):
            continue
        pairs = line.split()[1:]
        if any("=" not in part for part in pairs):
            raise QEvidenceHold("bad Paper ACK event")
        values = dict(part.split("=", 1) for part in pairs)
        if len(values) != len(pairs):
            raise QEvidenceHold("duplicate Paper ACK field")
        if values.get("nonce") == nonce:
            hits += 1
            if values != expected:
                raise QEvidenceHold("Paper original ACK identity/tick mismatch")
    if hits != 1:
        raise QEvidenceHold("Paper ACK missing or repeated")
    try:
        lines = raw["paper_ack"].decode("utf-8").splitlines()
        fields = [line.split("=", 1) for line in lines]
        if any(len(pair) != 2 for pair in fields):
            raise ValueError("invalid receipt")
        ack = dict(fields)
    except (UnicodeError, ValueError) as exc:
        raise QEvidenceHold("malformed original Paper ACK receipt") from exc
    if len(ack) != len(fields) or ack != {
        "boot_id": source["paper_boot_id"], "nonce": nonce,
        "paper_tick": str(source["paper_tick"]),
        "server_session_id": source["paper_session_id"],
        "source": "PAPER_MAIN_THREAD", "world_uuid": world,
    }:
        raise QEvidenceHold("Paper receipt mismatches original log/identity")


def _wal(raw: dict[str, bytes], source: dict[str, Any], self_id: str) -> None:
    try:
        body = json.loads(raw["wal"])
    except (UnicodeError, ValueError) as exc:
        raise QEvidenceHold("malformed canonical WAL") from exc
    if type(body) is not dict or body.get("self_id") != self_id:
        raise QEvidenceHold("foreign canonical WAL Self")
    actions = body.get("actions")
    if type(actions) is not list:
        raise QEvidenceHold("original WAL actions missing")
    if any(
        type(row) is not dict or row.get("status") == "PREPARED_UNRESOLVED"
        for row in actions
    ):
        raise QEvidenceHold("canonical WAL unresolved/invalid")
    target = [row for row in actions if row.get("action_id") == source["wal_action_id"]]
    if len(target) != 1 or target[0].get("status") != source["wal_status"]:
        raise QEvidenceHold("original WAL Action identity/terminal mismatch")
    if source["wal_status"] not in (
        "NATIVE_MOVE_SETTLED", "NATIVE_MOVE_NO_NET_DISPLACEMENT",
    ):
        raise QEvidenceHold("Q1 minimal MOVE terminal status unsupported")


def _optional(raw: dict[str, bytes], source: dict[str, Any], self_id: str) -> None:
    question = source["question_ref"]
    ticket = source["gpu_ticket_id"]
    if question is None and "question_adopts" in raw:
        raise QEvidenceHold("unexpected Question claim")
    if question is not None:
        if "question_adopts" not in raw:
            raise QEvidenceHold("Question evidence missing")
        rows = _jsonl(raw["question_adopts"], "question_adopts")
        hits = [
            x for x in rows if x.get("question_ref") == question
            and x.get("operation") == "ADOPT" and x.get("self_id") == self_id
        ]
        if len(hits) != 1 or sum(x.get("question_ref") == question for x in rows) != 1:
            raise QEvidenceHold("duplicate/foreign Question ADOPT")
    if ticket is None and "gpu_tickets" in raw:
        raise QEvidenceHold("unexpected GPU ticket claim")
    if ticket is not None:
        if "gpu_tickets" not in raw:
            raise QEvidenceHold("GPU ticket evidence missing")
        rows = _jsonl(raw["gpu_tickets"], "gpu_tickets")
        hits = [
            x for x in rows if x.get("ticket_id") == ticket
            and x.get("request_id") == source["native_request_id"]
            and x.get("self_id") == self_id and x.get("consumed") is True
        ]
        if len(hits) != 1 or sum(x.get("ticket_id") == ticket for x in rows) != 1:
            raise QEvidenceHold("replayed/foreign GPU ticket")



def build_untrusted_file_inventory(
    evidence_dir: Path, role_paths: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Read-only manifest file-index generation; NEVER provenance/authentication.

    Identity/source claims must come from the original producer and independent
    trusted pins from a *separately controlled* boundary. This inventory alone
    must never be accepted as any proof of World/Owner/Action.
    """
    if type(role_paths) is not dict or not _REQUIRED.issubset(role_paths):
        raise QEvidenceHold("original evidence inventory roles missing")
    root = evidence_dir.resolve(strict=True)
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    for role, path in sorted(role_paths.items()):
        if role not in _ROLES or path in seen:
            raise QEvidenceHold("duplicate/unknown evidence inventory role or file")
        seen.add(path)
        raw = _raw_file(root, path)
        entries.append({
            "role": role, "path": path,
            "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return entries


def verify_evidence(
    evidence_dir: Path, manifest: Mapping[str, Any], external_pins: Mapping[str, Any],
) -> dict[str, Any]:
    """Independent scope + bytes consistency only; never cryptographic provenance."""
    header = {"schema", *_ID_FIELDS, "source", "files"}
    m = _exact(manifest, header, "manifest")
    p = _exact(external_pins, (header - {"files"}) | {"sha256"}, "external pins")
    if m["schema"] != 1 or p["schema"] != 1:
        raise QEvidenceHold("unsupported Q evidence schema")
    if not _HEAD.fullmatch(str(m["head"])):
        raise QEvidenceHold("exact 40-hex execution HEAD required")
    for field in _ID_FIELDS:
        if m[field] != p[field]:
            raise QEvidenceHold(f"{field}: independently pinned scope mismatch")
    for field in ("world_uuid", "owner_id", "self_id", "native_session_id"):
        _nonblank(m[field], field)
    if type(m["checkpoint_generation"]) is not int or m["checkpoint_generation"] < 0:
        raise QEvidenceHold("checkpoint generation must be nonnegative integer")
    source = _exact(m["source"], _SOURCE_FIELDS, "source")
    _exact(p["source"], _SOURCE_FIELDS, "pinned source")
    if source != p["source"]:
        raise QEvidenceHold("original source claims differ from external pins")
    if type(source["native_seq"]) is not int or type(source["paper_tick"]) is not int:
        raise QEvidenceHold("source sequence/tick must be integers")
    for key in (
        "native_request_id", "paper_nonce", "paper_boot_id",
        "paper_session_id", "wal_action_id", "wal_status",
    ):
        _nonblank(source[key], key)
    for key in ("question_ref", "gpu_ticket_id"):
        if source[key] is not None:
            _nonblank(source[key], key)
    entries = m["files"]
    pins = p["sha256"]
    if type(entries) is not list or type(pins) is not dict:
        raise QEvidenceHold("artifact entries/pins missing")
    raw: dict[str, bytes] = {}
    paths: set[str] = set()
    root = evidence_dir.resolve(strict=True)
    for entry in entries:
        e = _exact(entry, {"role", "path", "size", "sha256"}, "artifact")
        role, path = e["role"], e["path"]
        if role not in _ROLES or role in raw or path in paths:
            raise QEvidenceHold("unknown/duplicate artifact role or path")
        if type(e["size"]) is not int or not 0 <= e["size"] <= _MAX_BYTES:
            raise QEvidenceHold("invalid artifact length")
        digest = _digest(e["sha256"])
        if pins.get(role) != digest:
            raise QEvidenceHold("artifact SHA differs from independently supplied pin")
        data = _raw_file(root, path)
        if len(data) != e["size"] or hashlib.sha256(data).hexdigest() != digest:
            raise QEvidenceHold("original artifact bytes/size changed")
        raw[role] = data
        paths.add(path)
    if set(raw) != set(pins) or not _REQUIRED.issubset(raw):
        raise QEvidenceHold("missing/extra original artifact or external pin")
    _native(raw, source=source, session=m["native_session_id"])
    _paper(raw, source, m["world_uuid"])
    _wal(raw, source, m["self_id"])
    _optional(raw, source, m["self_id"])
    # Original product checkpoint schema is intentionally NOT reinterpreted here.
    # Bytes and independently supplied generation pins are checked; authentic
    # generation/Owner admission still requires the original Stage28 auditor.
    return {
        "classification": "Q1_EXTERNAL_PINS_AND_SOURCE_LINKS_CONSISTENT_DEV_ONLY",
        "head": m["head"],
        "artifact_sha256": {key: pins[key] for key in sorted(pins)},
        "file_count": len(raw),
        "external_pin_origin_authenticated": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
        "owner_checkpoint_semantics_attested": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--external-pins", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.evidence_dir.resolve(strict=True)
        # A pin file sitting inside the same mutable evidence folder is not
        # independent, even for this limited consistency check.
        if args.external_pins.resolve().is_relative_to(root):
            raise QEvidenceHold("external pins must be outside the evidence tree")
        manifest = json.loads(args.manifest.read_bytes())
        pins = json.loads(args.external_pins.read_bytes())
        result = verify_evidence(root, manifest, pins)
    except (QEvidenceHold, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"classification": "Q1_HOLD", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
