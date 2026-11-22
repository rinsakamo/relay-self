"""One ORIGINAL A/B Resident pre-login Schema3 cognition source (CPU DEV).

Called only after existing explicit fresh Schema registration and BEFORE any
native login. This records the same original retained cognition Registry to
the canonical files. No new owner, inference, model POST, World or Action.
A failure leaves partial evidence for operator HOLD and forbids retry.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from relay_self.exploration_schema_record_dev import (
    encode_recorded_schema,
    require_recorded_schema,
)
from relay_self.innate_schema import SchemaMode
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class BD1bSchema3ProducerHold(RuntimeError):
    """No original fresh A/B source. Do not start Native work or retry."""


@dataclass(frozen=True, slots=True)
class OriginalSchema3PreloginReceipt:
    self_ids: tuple[str, str]
    schema_modes: tuple[str, str]
    cognition_sha256: tuple[tuple[str, str], ...]
    wal_sha256: tuple[tuple[str, str], ...]
    original_registered_before_native: bool = True
    real_paper_independently_audited: bool = False
    real_model_post_attempted: bool = False


def _write_once(path: Path, raw: bytes) -> None:
    """Exclusive original bytes, no overwrite or replay on partial failure."""
    if (path.parent.is_symlink() or not path.parent.is_dir()
            or not isinstance(raw, bytes)):
        raise BD1bSchema3ProducerHold("unqualified original evidence sink")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    if path.read_bytes() != raw:
        raise BD1bSchema3ProducerHold("original evidence bytes changed")


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise BD1bSchema3ProducerHold("unsafe original Owner file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_original_schema3_prelogin(
    resident: ResidentCognitiveWorkOwner, *, evidence_dir: Path,
) -> OriginalSchema3PreloginReceipt:
    """Write canonical Owner cognition before first Native login, once only.

    A previous cognition file (even semantically equal) is forbidden: this
    must be the original source creation, not a post-login retrofit.
    """
    if (not isinstance(resident, ResidentCognitiveWorkOwner)
            or not isinstance(evidence_dir, Path)
            or evidence_dir.is_symlink() or not evidence_dir.is_dir()
            or evidence_dir.stat().st_nlink < 1):
        raise BD1bSchema3ProducerHold("original Resident and separate evidence root required")
    with resident.lock:
        if set(resident.owners) != {"A", "B"} or set(resident._present_schemas) != {"A", "B"}:
            raise BD1bSchema3ProducerHold("complete original A/B Schema registration required")
        snapshots = {}
        for sid in ("A", "B"):
            owner = resident.owners[sid]
            state = resident._state(sid)
            path = owner.files.cognition_file
            root = owner.files.self_root
            wal = owner.files.physical_wal_file
            if (state.mode != "OFFLINE" or state.epoch != 0 or state.native is not None
                    or state.tasks or state.staged_peer or state.retired is not None
                    or owner.fresh_native_observation_required
                    or owner.retained.identity.self_id != sid
                    or owner.retained.pattern_registry is not None
                    or owner.retained.exploration_continuity is not None
                    or owner.intent.events or owner.skills or owner.pending_questions
                    or owner.supervisor.open_actions
                    or root.is_symlink() or not root.is_dir()
                    or path != root / "cognition.json" or path.exists() or path.is_symlink()
                    or wal != root / "physical-wal.json"):
                raise BD1bSchema3ProducerHold("original fresh Self is already mutated or rejoined")
            PhysicalActionJournal.restore(wal, self_id=sid).require_clear()
            snapshot, pinned = resident._present_schemas[sid]
            if pinned != owner.pattern_registry:
                raise BD1bSchema3ProducerHold("original Registry changed after Schema bootstrap")
            require_recorded_schema(snapshot, self_id=sid, registry=owner.pattern_registry)
            if snapshot.get("exploratory").mode is not SchemaMode.FULL:
                raise BD1bSchema3ProducerHold("FULL original exploration activation required")
            snapshots[sid] = snapshot
        record_file = evidence_dir / "stage28b-schema3-prelogin.json"
        if record_file.exists() or record_file.is_symlink():
            raise BD1bSchema3ProducerHold("duplicate immutable prelogin record")
        cognition = []
        wal_rows = []
        for sid in ("A", "B"):
            owner = resident.owners[sid]
            new_retained = replace(owner.retained, pattern_registry=owner.pattern_registry)
            # Existing canonical persistence path, no parallel owner or file.
            save_persistent_cognition(owner.files.cognition_file, new_retained)
            if load_persistent_cognition(owner.files.cognition_file) != new_retained:
                raise BD1bSchema3ProducerHold("original cognition persisted source differs")
            owner.retained = new_retained
            cognition_raw = owner.files.cognition_file.read_bytes()
            wal_raw = owner.files.physical_wal_file.read_bytes()
            _write_once(
                evidence_dir / f"stage28b-schema3-{sid}-prelogin-cognition.json",
                cognition_raw,
            )
            _write_once(
                evidence_dir / f"stage28b-schema3-{sid}-prelogin-wal.json",
                wal_raw,
            )
            cognition.append((sid, _digest(owner.files.cognition_file)))
            wal_rows.append((sid, _digest(owner.files.physical_wal_file)))
        receipt = OriginalSchema3PreloginReceipt(
            ("A", "B"), ("FULL", "FULL"), tuple(cognition), tuple(wal_rows),
        )
        payload = {
            "classification": "BD1B_ORIGINAL_PRELOGIN_SCHEMA3_UNAUDITED_DEV",
            "self_ids": list(receipt.self_ids),
            "schema_modes": list(receipt.schema_modes),
            "cognition_sha256": [list(v) for v in receipt.cognition_sha256],
            "wal_sha256": [list(v) for v in receipt.wal_sha256],
            "registrations": [
                encode_recorded_schema(
                    snapshots[sid], self_id=sid,
                    registry=resident.owners[sid].pattern_registry,
                ) for sid in ("A", "B")
            ],
            "original_registered_before_native": True,
            "real_paper_independently_audited": False,
            "real_model_post_attempted": False,
        }
        raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        _write_once(record_file, raw)
        return receipt
