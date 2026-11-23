"""Q6: independent read-only validation of U16 raw evidence manifest.

Never grants original physical action, World DEV PASS or producer authenticity.
Requires an already-sealed U16 manifest and the unmodified local evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from experiments.q_lane_q4_raw_native_wal_audit_dev import (
    Q4EvidenceHold,
    _parse,
    audit_two_nominal_moves,
)

_EXPECTED = frozenset({
    "native_stdout", "native_stdin", "paper_ticks", "owner_wal",
    "owner_cognition", "host_monotonic", "process_exit",
})
_MAX_BYTES = 32 * 1024 * 1024


class Q6ManifestHold(ValueError):
    """Raw custody disagrees with the claimed manifest or expected trial."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Q6ManifestHold(message)


def _read_pinned(root: Path, relative: str, expected: dict) -> str:
    _require(type(relative) is str and relative and "\\" not in relative,
             "invalid relative evidence path")
    rel = Path(relative)
    _require(not rel.is_absolute() and len(rel.parts) <= 4
             and all(x not in ("", ".", "..") for x in rel.parts),
             "unsafe relative evidence path")
    path = root / rel
    _require(not any((root.joinpath(*rel.parts[:i])).is_symlink()
                     for i in range(1, len(rel.parts) + 1)),
             "symlink within evidence path")
    _require(set(expected) == {
        "path", "sha256", "size_bytes", "device", "inode", "mtime_ns",
    }, "unexpected evidence manifest fields")
    _require(expected["path"] == relative, "unmatched evidence path")
    _require(type(expected["size_bytes"]) is int
             and 0 < expected["size_bytes"] <= _MAX_BYTES
             and type(expected["device"]) is int
             and type(expected["inode"]) is int
             and type(expected["mtime_ns"]) is int
             and type(expected["sha256"]) is str
             and len(expected["sha256"]) == 64,
             "malformed pinned evidence metadata")
    fd = None
    try:
        before = path.stat(follow_symlinks=False)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                 "original is not a single-linked regular file")
        _require(
            (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
            == (expected["device"], expected["inode"],
                expected["mtime_ns"], expected["size_bytes"]),
            "original evidence identity/size/mtime changed",
        )
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        opened = os.fstat(fd)
        _require(
            (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
            "original file swapped between stat/open",
        )
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(fd, 128 * 1024)
            if not chunk:
                break
            count += len(chunk)
            _require(count <= _MAX_BYTES, "oversized evidence")
            digest.update(chunk)
        after_fd = os.fstat(fd)
        after = path.stat(follow_symlinks=False)
        _require(
            count == expected["size_bytes"]
            and (after_fd.st_dev, after_fd.st_ino, after_fd.st_size,
                 after_fd.st_mtime_ns, after_fd.st_ctime_ns)
            == (opened.st_dev, opened.st_ino, opened.st_size,
                opened.st_mtime_ns, opened.st_ctime_ns)
            and (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)
            == (before.st_dev, before.st_ino, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns),
            "original evidence mutated during verification",
        )
        _require(digest.hexdigest() == expected["sha256"],
                 "original evidence content hash mismatch")
        return relative
    except OSError as exc:
        raise Q6ManifestHold("original source unreadable") from exc
    finally:
        if fd is not None:
            os.close(fd)


def audit_u16_manifest(
    *, root: Path, manifest_path: Path, trial: str,
    inspect_two_moves: bool = False,
) -> dict:
    """Check immutable custody and optionally Q's independent two-MOVE shape."""
    _require(root.is_absolute() and not root.is_symlink()
             and root.is_dir() and root.resolve() == root,
             "absolute isolated root required")
    _require(type(trial) is str and trial in {"two_moves", "stop_failure"},
             "recognized trial mode required")
    _require(manifest_path.parent == root and not manifest_path.is_symlink()
             and manifest_path.is_file(), "same-root manifest required")
    _require(not inspect_two_moves or trial == "two_moves",
             "two-move check cannot audit a fault trial")
    payload = _parse(manifest_path.read_bytes())
    _require(type(payload) is dict and set(payload) == {
        "schema", "trial", "status", "real_world_dev_pass",
        "qual_go", "science_run", "independent_paper_source_audited",
        "independent_q_audited", "evidence",
    }, "manifest top-level contract mismatch")
    _require(
        payload["schema"] == "q4-original-raw-evidence-dev-v1"
        and payload["trial"] == trial
        and payload["status"] == "RAW_EVIDENCE_MANIFEST_SEALED_NOT_VERIFIED"
        and all(payload[k] is False for k in (
            "real_world_dev_pass", "qual_go", "science_run",
            "independent_paper_source_audited", "independent_q_audited",
        )), "unexpected success, scope or trial claim",
    )
    evidence = payload["evidence"]
    _require(type(evidence) is dict and set(evidence) == _EXPECTED,
             "all seven exact original evidence roles required")
    paths = set()
    identities = set()
    for role in sorted(_EXPECTED):
        item = evidence[role]
        _require(type(item) is dict, "evidence item not a mapping")
        relative = _read_pinned(root, item.get("path"), item)
        identity = (item["device"], item["inode"])
        _require(relative not in paths and identity not in identities,
                 "two roles point to same original file")
        paths.add(relative)
        identities.add(identity)
    result = {
        "status": "Q6_RAW_MANIFEST_INDEPENDENT_CONTENT_PASS",
        "trial": trial,
        "roles": 7,
        "world_dev_pass": False,
        "paper_producer_authenticated": False,
    }
    if inspect_two_moves:
        try:
            receipts = audit_two_nominal_moves(
                root / evidence["owner_wal"]["path"],
                root / evidence["native_stdout"]["path"],
            )
        except Q4EvidenceHold as exc:
            raise Q6ManifestHold("Native/WAL two-move structure not proven") from exc
        result["native_wal_structure"] = "CPU_PASS_ONLY"
        result["moves"] = receipts
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trial", choices=("two_moves", "stop_failure"), required=True)
    parser.add_argument("--check-two-moves", action="store_true")
    args = parser.parse_args()
    try:
        receipt = audit_u16_manifest(
            root=args.root, manifest_path=args.manifest, trial=args.trial,
            inspect_two_moves=args.check_two_moves,
        )
    except (Q6ManifestHold, Q4EvidenceHold, OSError, ValueError, TypeError) as exc:
        print("Q6_MANIFEST_HOLD: " + str(exc))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
