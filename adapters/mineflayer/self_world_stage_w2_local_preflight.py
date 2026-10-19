"""SelfWorld W2: read-only Linux/WSL2 isolation and raw-digest preflight.

The preflight is deliberately NOT an attestation of the original Mineflayer
raw stream, authorized issuer identity, durability, or live S10. It does not
read the issuer private key or create users, ledger, or physical World.
Use on LocalCodex's disposable WSL2 evidence root after separately
provisioning operator-owned pins and distinct issuer/consumer OS identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.self_world_stage_v_attestation import (
    fingerprint_for_public_pem,
)

_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class W2PreflightReport:
    classification: str
    checks: dict[str, bool]
    blockers: tuple[str, ...]
    public_key_fingerprint: str | None
    raw_source_sha256: str | None
    consumer_uid: int
    distinct_os_identity_qualified: bool = False
    issuer_key_custody_qualified: bool = False
    raw_native_stream_qualified: bool = False
    raw_stream_continuity_qualified: bool = False
    crash_rollback_durability_qualified: bool = False
    physical_s10_commit_permitted: bool = False
    physical_near_wait_permitted: bool = False
    science_qualified: bool = False


def _digest_file(path: Path, *, limit: int = 512 * 1024 * 1024) -> str:
    hashed = hashlib.sha256()
    seen = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            seen += len(chunk)
            if seen > limit:
                raise ValueError("offline raw input exceeds bounded size")
            hashed.update(chunk)
    return hashed.hexdigest()


def _regular_file(path: Path) -> os.stat_result | None:
    """Refuse path symlinks and absent or nonregular files."""
    try:
        info = path.lstat()
    except (OSError, ValueError):
        return None
    return info if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 else None


def _database_readonly(db: Path) -> bool:
    try:
        # No creation or schema mutation. Only inspect pre-provisioned ledger.
        with sqlite3.connect(
            db.as_uri() + "?mode=ro", uri=True, timeout=3.0,
        ) as conn:
            names = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "grant_spent" not in names:
                return False
            fields = [row[1] for row in conn.execute(
                "PRAGMA table_info(grant_spent)"
            )]
            expected = (
                "run_id", "session_id", "action_id", "feedback_id",
                "issuer_fingerprint", "archive_sha256", "evidence_sha256",
            )
            return (
                fields == list(expected)
                and conn.execute("PRAGMA quick_check").fetchone() == ("ok",)
            )
    except (OSError, sqlite3.Error, ValueError):
        return False


def inspect_w2_local_environment(
    *, public_pem_path: Path,
    expected_public_sha256: str,
    raw_source_path: Path,
    expected_raw_sha256: str,
    existing_ledger_path: Path,
    issuer_private_key_path: Path,
    issuer_uid: int,
    consumer_uid: int,
) -> W2PreflightReport:
    """Read-only local diagnostic; treats all operator pins as ASSERTIONS.

    An inaccessible private key means only that this consumer could not
    open it. It does not qualify ACLs, root access, signer provenance,
    host key custody, or provenance of the raw source supplied by operator.
    """
    actual_uid = os.geteuid() if hasattr(os, "geteuid") else -1
    paths = (
        public_pem_path, raw_source_path, existing_ledger_path,
        issuer_private_key_path,
    )
    absolute_paths = all(
        isinstance(p, Path) and p.is_absolute() for p in paths
    )
    usable_pins = all(
        type(h) is str and len(h) == 64 and all(c in _HEX for c in h)
        for h in (expected_public_sha256, expected_raw_sha256)
    )
    distinct_identity = (
        sys.platform.startswith("linux")
        and type(issuer_uid) is int and type(consumer_uid) is int
        and issuer_uid >= 0 and consumer_uid > 0
        and issuer_uid != consumer_uid and actual_uid == consumer_uid
    )
    checks = {
        "linux_separate_consumer_identity": distinct_identity,
        "absolute_operator_paths": absolute_paths,
        "externally_supplied_hash_shapes": usable_pins,
        "public_key_file_regular": False,
        "pinned_public_key_digest_matches": False,
        "raw_file_regular": False,
        "externally_pinned_raw_digest_matches": False,
        "sqlite_ledger_file_regular": False,
        "sqlite_ledger_owner_mode_0600": False,
        "sqlite_ledger_readonly_integrity": False,
        "issuer_private_key_unreadable_to_consumer": False,
    }
    fingerprint: str | None = None
    raw_hash: str | None = None
    if absolute_paths:
        public_info = _regular_file(public_pem_path)
        checks["public_key_file_regular"] = public_info is not None
        if public_info is not None:
            try:
                fingerprint = fingerprint_for_public_pem(
                    public_pem_path.read_bytes()
                )
            except (OSError, ValueError):
                fingerprint = None
        checks["pinned_public_key_digest_matches"] = bool(
            usable_pins and fingerprint == expected_public_sha256
        )
        raw_info = _regular_file(raw_source_path)
        checks["raw_file_regular"] = raw_info is not None
        if raw_info is not None:
            try:
                raw_hash = _digest_file(raw_source_path)
            except (OSError, ValueError):
                raw_hash = None
        checks["externally_pinned_raw_digest_matches"] = bool(
            usable_pins and raw_hash == expected_raw_sha256
        )
        db_info = _regular_file(existing_ledger_path)
        checks["sqlite_ledger_file_regular"] = db_info is not None
        checks["sqlite_ledger_owner_mode_0600"] = bool(
            db_info is not None and db_info.st_uid == consumer_uid
            and stat.S_IMODE(db_info.st_mode) == 0o600
        )
        checks["sqlite_ledger_readonly_integrity"] = bool(
            db_info is not None and _database_readonly(existing_ledger_path)
        )
        # Do NOT even open/read private PEM contents. os.open will reveal
        # only if the consumer can acquire a read FD; close immediately.
        # The file's cryptographic identity is not validated by this probe.
        try:
            fd = os.open(str(issuer_private_key_path), os.O_RDONLY | os.O_NONBLOCK)
        except PermissionError:
            checks["issuer_private_key_unreadable_to_consumer"] = True
        except OSError:
            pass
        else:
            os.close(fd)

    blockers = tuple(sorted(k for k, value in checks.items() if not value))
    return W2PreflightReport(
        classification=(
            "W2_LOCAL_FILESYSTEM_PRECHECK_ONLY"
            if not blockers else "W2_LOCAL_PREFLIGHT_BLOCKED"
        ),
        checks=checks, blockers=blockers,
        public_key_fingerprint=fingerprint,
        raw_source_sha256=raw_hash, consumer_uid=actual_uid,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="W2 read-only LOCAL preflight; no World or S10 authority",
    )
    parser.add_argument("--public-pem", type=Path, required=True)
    parser.add_argument("--public-sha256", required=True)
    parser.add_argument("--raw-source", type=Path, required=True)
    parser.add_argument("--raw-sha256", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--issuer-private-key", type=Path, required=True)
    parser.add_argument("--issuer-uid", type=int, required=True)
    parser.add_argument("--consumer-uid", type=int, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = inspect_w2_local_environment(
        public_pem_path=args.public_pem,
        expected_public_sha256=args.public_sha256,
        raw_source_path=args.raw_source,
        expected_raw_sha256=args.raw_sha256,
        existing_ledger_path=args.ledger,
        issuer_private_key_path=args.issuer_private_key,
        issuer_uid=args.issuer_uid, consumer_uid=args.consumer_uid,
    )
    output = args.report
    if not output.is_absolute() or output.exists() or output.is_symlink():
        parser.error("--report must be an unused absolute path")
    try:
        # Exclusive create: never overwrite frozen evidence or old receipts.
        fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        return 2
    print(json.dumps({
        "classification": report.classification,
        "blockers": report.blockers,
        "report": str(output),
    }, sort_keys=True))
    return 0 if not report.blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
