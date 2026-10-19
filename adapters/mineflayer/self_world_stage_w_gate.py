"""SelfWorld Stage W1: trusted-pin inputs + durable one-use OFFLINE gate.

Verified signed request + independently pinned canonical source extraction
MUST match before a SQLite BEGIN IMMEDIATE reservation. The transaction is
durable before reporting success. This module does not issue S10 authority,
change an existing owner, or run any physical World action.

External key pinning, raw/native provenance and DB file security must be
qualified separately by W2 LocalCodex; tests use only disposable local files.
"""
from __future__ import annotations

import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.self_world_stage_v_attestation import (
    StageVGrantRequest,
    StageVPinnedGrantVerifier,
    fingerprint_for_public_pem,
)
from adapters.mineflayer.self_world_stage_w_archive import (
    StageWArchiveReadback,
    StageWArchiveRejected,
    audit_independent_source_extract,
)


class StageWGateRejected(ValueError):
    """Untrusted signer, unverifiable archive or already-spent grant."""


@dataclass(frozen=True, slots=True)
class StageWOfflineReceipt:
    run_id: str
    session_id: str
    action_id: str
    feedback_id: str
    pinned_issuer_fingerprint: str
    pinned_source_sha256: str
    signed_evidence_sha256: str
    persistent_grant_reserved: bool
    independent_source_recomputed: bool
    external_issuer_identity_qualified: bool = False
    raw_world_stream_qualified: bool = False
    real_s10_commit_permitted: bool = False
    physical_wait_permitted: bool = False
    science_qualified: bool = False


class StageWPersistentGrantLedger:
    """SQLite single-key owner; no implicit new DB; concurrent insert is atomic.

    Ledger is only a *reservation* receipt, never executable learning permission.
    DB rollback/restore/replication, physical key custody, backup and filesystem
    permissions are explicitly W2 qualification items, not proven by SQLite.
    """

    def __init__(self, database_path: Path) -> None:
        if (
            not isinstance(database_path, Path)
            or not database_path.is_absolute()
            or database_path.is_symlink()
            or not database_path.is_file()
        ):
            raise StageWGateRejected("pre-provisioned absolute ledger path required")
        self._path = database_path
        self._identity = self._checked_identity()

    def _checked_identity(self) -> tuple[int, int]:
        """Reject symlink ancestors/replacement; not a malicious-UID sandbox."""
        try:
            for part in (self._path, *self._path.parents):
                if part.is_symlink():
                    raise StageWGateRejected("ledger symlink boundary rejected")
            info = self._path.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                raise StageWGateRejected("ledger owner/mode/link boundary rejected")
            return info.st_dev, info.st_ino
        except OSError as exc:
            raise StageWGateRejected("ledger identity unavailable") from exc

    @classmethod
    def provision_new(cls, database_path: Path) -> StageWPersistentGrantLedger:
        """DEV-only first initialization: refuse path overwrite."""
        if not isinstance(database_path, Path) or not database_path.is_absolute():
            raise StageWGateRejected("absolute preselected ledger path required")
        if any(part.is_symlink() for part in database_path.parents):
            raise StageWGateRejected("ledger symlink parent rejected")
        try:
            fd = os.open(str(database_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            conn = sqlite3.connect(database_path.as_uri() + "?mode=rw", uri=True)
            try:
                conn.execute("PRAGMA journal_mode=DELETE")
                conn.execute("PRAGMA synchronous=FULL")
                conn.execute("""
                    CREATE TABLE grant_spent (
                        run_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        action_id TEXT NOT NULL,
                        feedback_id TEXT NOT NULL,
                        issuer_fingerprint TEXT NOT NULL,
                        archive_sha256 TEXT NOT NULL,
                        evidence_sha256 TEXT NOT NULL,
                        PRIMARY KEY(run_id, session_id, action_id),
                        UNIQUE(run_id, feedback_id),
                        UNIQUE(run_id, evidence_sha256)
                    )
                """)
                conn.commit()
            finally:
                conn.close()
        except (OSError, sqlite3.Error) as exc:
            raise StageWGateRejected("ledger provisioning failed") from exc
        return cls(database_path)

    def reserve_once(
        self, request: StageVGrantRequest,
        *, issuer_fingerprint: str,
        archive_sha256: str,
    ) -> None:
        """Consume before delivery; no retry or rollback after successful COMMIT."""
        if not isinstance(request, StageVGrantRequest):
            raise StageWGateRejected("typed signed request required")
        if self._checked_identity() != self._identity:
            raise StageWGateRejected("ledger replaced since admission")
        try:
            conn = sqlite3.connect(
                self._path.as_uri() + "?mode=rw", uri=True,
                timeout=5.0, isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise StageWGateRejected("ledger inaccessible") from exc
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO grant_spent VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    request.run_id, request.session_id, request.action_id,
                    request.feedback_id, issuer_fingerprint, archive_sha256,
                    request.evidence_sha256,
                ),
            )
            if self._checked_identity() != self._identity:
                raise StageWGateRejected("ledger replaced during reservation")
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise StageWGateRejected("grant already spent or ledger failed closed") from exc
        finally:
            conn.close()


class StageWOfflineConsumer:
    """Strict DEV only: verify pinned key, source and durable reservation.

    Key/archivist trust roots MUST come from operator configuration, never
    from a submitted envelope or untrusted requester. No live S10 bridge.
    """

    def __init__(
        self, *,
        pinned_public_pem: bytes,
        pinned_public_fingerprint: str,
        expected_run_id: str,
        ledger: StageWPersistentGrantLedger,
    ) -> None:
        if not isinstance(ledger, StageWPersistentGrantLedger):
            raise StageWGateRejected("independently provisioned ledger required")
        if (
            not isinstance(pinned_public_fingerprint, str)
            or fingerprint_for_public_pem(pinned_public_pem)
            != pinned_public_fingerprint
        ):
            raise StageWGateRejected("pinned signer trust root mismatched")
        self._verifier = StageVPinnedGrantVerifier(
            pinned_public_pem=pinned_public_pem,
            pinned_fingerprint=pinned_public_fingerprint,
            expected_run_id=expected_run_id,
        )
        self._ledger = ledger
        self._fingerprint = pinned_public_fingerprint

    def verify_and_reserve_once(
        self, *,
        envelope: object,
        expected: StageVGrantRequest,
        independent_archive_path: Path,
        independently_pinned_archive_sha256: str,
    ) -> StageWOfflineReceipt:
        """Full archive reprojection + signature then durable single-use log.

        A readback proves OFFLINE consistency and spent-key state only.
        External issuer trust, physical World and S10 permission stay False.
        """
        try:
            source: StageWArchiveReadback = audit_independent_source_extract(
                archive_path=independent_archive_path,
                expected_archive_sha256=independently_pinned_archive_sha256,
                expected=expected,
            )
            request = self._verifier.verify_once(envelope, expected=expected)
            self._ledger.reserve_once(
                request, issuer_fingerprint=self._fingerprint,
                archive_sha256=source.archive_sha256,
            )
        except (StageWArchiveRejected, ValueError) as exc:
            raise StageWGateRejected("signed source rejected or grant already spent") from exc
        return StageWOfflineReceipt(
            run_id=request.run_id, session_id=request.session_id,
            action_id=request.action_id, feedback_id=request.feedback_id,
            pinned_issuer_fingerprint=self._fingerprint,
            pinned_source_sha256=source.archive_sha256,
            signed_evidence_sha256=source.source_sha256,
            persistent_grant_reserved=True,
            independent_source_recomputed=True,
        )
