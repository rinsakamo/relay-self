"""S7 read-only S6 host-local SHA256SUMS reconciliation; never rewrites evidence.

The two published values are *claims about file identities* and cannot be
resolved from GitHub comments, which do not include original host bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path

MAX_INDEX_BYTES = 64 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FILES = 256
SHA = re.compile(r"[0-9a-f]{64}\Z")
ENTRY = re.compile(r"([0-9a-f]{64})  ([^\r\n]+)\Z")


class S7EvidenceRejected(ValueError):
    """Original evidence unavailable or unsafe. No guess or backfill."""


def _regular(path: Path, *, max_bytes: int) -> None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
            or not stat.S_ISREG(path.lstat().st_mode)):
        raise S7EvidenceRejected("canonical original regular file required")
    if any(p.is_symlink() for p in path.parents):
        raise S7EvidenceRejected("symlinked original ancestor")
    if path.resolve(strict=True) != path or path.stat().st_size > max_bytes:
        raise S7EvidenceRejected("original file unsafe or over size limit")


def sha256(path: Path) -> str:
    _regular(path, max_bytes=MAX_FILE_BYTES)
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def audit(root: Path, *, index: str = "SHA256SUMS",
          reported_index_sha256: str, user_supplied_sha256: str) -> dict:
    if not all(
        isinstance(x, str) and SHA.fullmatch(x)
        for x in (reported_index_sha256, user_supplied_sha256)
    ):
        raise S7EvidenceRejected("two exact hexadecimal SHA256 claims required")
    if (not root.is_absolute() or not root.is_dir() or root.is_symlink()
            or any(p.is_symlink() for p in root.parents)
            or root.resolve(strict=True) != root):
        raise S7EvidenceRejected("original physical evidence directory required")
    if index != "SHA256SUMS":
        raise S7EvidenceRejected("original index name is fixed")
    path = root / index
    _regular(path, max_bytes=MAX_INDEX_BYTES)
    raw = path.read_bytes()
    try:
        rows = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise S7EvidenceRejected("index must be UTF8") from exc
    if not 1 <= len(rows) <= MAX_FILES:
        raise S7EvidenceRejected("index file count out of bounds")
    entries: list[tuple[str, str]] = []
    names: set[str] = set()
    for row in rows:
        match = ENTRY.fullmatch(row)
        if match is None:
            raise S7EvidenceRejected("noncanonical SHA256SUMS entry")
        digest, name = match.groups()
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts
                or any(part in ("", ".") for part in relative.parts)
                or name == index or name in names):
            raise S7EvidenceRejected("ambiguous/duplicate/traversing index path")
        names.add(name)
        entries.append((digest, name))
    outcomes = []
    for expected, name in entries:
        actual = sha256(root / name)
        outcomes.append({
            "path": name,
            "sha256_matches_index": expected == actual,
            "matches_user_supplied_sha256": actual == user_supplied_sha256,
            "matches_reported_index_sha256": actual == reported_index_sha256,
        })
    index_sha = hashlib.sha256(raw).hexdigest()
    all_match = all(row["sha256_matches_index"] for row in outcomes)
    index_reported = index_sha == reported_index_sha256
    index_user = index_sha == user_supplied_sha256
    if not all_match:
        classification = "S7_ORIGINAL_INDEX_CONTENT_MISMATCH_BLOCKED"
    elif index_reported and index_user:
        classification = "S7_BOTH_HASH_CLAIMS_AGREE"
    elif index_reported:
        classification = "S7_REPORTED_INDEX_MATCH_USER_HASH_DIFFERENT"
    elif index_user:
        classification = "S7_USER_INDEX_MATCH_REPORTED_HASH_DIFFERENT"
    else:
        classification = "S7_NEITHER_INDEX_HASH_CLAIM_MATCHES"
    return {
        "classification": classification,
        "read_only": True,
        "world_sessions_started": 0,
        "minecraft_replayed": False,
        "original_bytes_modified": False,
        "index_path": str(path),
        "index_actual_sha256": index_sha,
        "reported_index_sha256": reported_index_sha256,
        "user_supplied_sha256": user_supplied_sha256,
        "indexed_original_files": len(outcomes),
        "indexed_files_all_sha256_match": all_match,
        "user_hash_other_original_matches": [
            x["path"] for x in outcomes if x["matches_user_supplied_sha256"]
        ],
        "claim_equivalence_proven": index_reported and index_user,
        "raw_mineflayer_jsonl_available_in_s6": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--reported-index-sha256",
                        default="b22598cc985d5fce4f8c8ffbb15452a8e6f79578aa18d5326650eaa4143536e7")
    parser.add_argument("--user-sha256",
                        default="baa0e633a10f2cfd64107d1aee77250e56b4fa56405c826ff27e2f3f3652fd47")
    args = parser.parse_args(argv)
    if args.root is None:
        print(json.dumps({
            "classification": "S7_READ_ONLY_AUDIT_PLAN",
            "original_host_evidence_read": False,
            "user_hash": args.user_sha256,
            "reported_index_hash": args.reported_index_sha256,
            "physical_execution_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        result = audit(
            args.root,
            reported_index_sha256=args.reported_index_sha256,
            user_supplied_sha256=args.user_sha256,
        )
    except (OSError, UnicodeError, S7EvidenceRejected) as exc:
        result = {
            "classification": "S7_ORIGINAL_INDEX_AUDIT_BLOCKED",
            "reason_type": type(exc).__name__,
            "read_only": True,
            "world_sessions_started": 0,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if result["classification"] in {
        "S7_REPORTED_INDEX_MATCH_USER_HASH_DIFFERENT",
        "S7_BOTH_HASH_CLAIMS_AGREE",
        "S7_USER_INDEX_MATCH_REPORTED_HASH_DIFFERENT",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
