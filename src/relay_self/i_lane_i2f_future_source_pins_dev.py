"""I2f explicit fresh-source pins for a NEW ORIGINAL typed A/B v3 World.

The historic Stage28b source remains frozen and is not a default. A caller
must supply independently archived SHA pins for the NEW typed generation and
for its own original Native/Paper source manifest; never infer pins from files.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from relay_self.i_lane_i2e_future_original_preflight_dev import (
    preflight_i2e_future_source,
)
from relay_self.stage28c2b_historical_native_sessions_dev import (
    inspect_original_stage28b_native_sessions,
)


class I2fFuturePinsHold(RuntimeError):
    """Original fresh A/B v3 source not admissible for any World."""


_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class I2fFutureSourcePins:
    """Caller supplied pins, NOT a claim that the source was verified."""

    source_world_id: str
    source_branch_id: str
    source_committed_sha256: str
    fork_branch_id: str
    original_manifest_sha256: str
    original_manifest_files: int

    def __post_init__(self) -> None:
        if (
            any(type(value) is not str or not value.strip()
                for value in (
                    self.source_world_id, self.source_branch_id,
                    self.fork_branch_id,
                ))
            or any(type(sha) is not str or _SHA.fullmatch(sha) is None
                   for sha in (
                       self.source_committed_sha256,
                       self.original_manifest_sha256,
                   ))
            or type(self.original_manifest_files) is not int
            or not 1 <= self.original_manifest_files <= 100000
        ):
            raise I2fFuturePinsHold("explicit immutable new original source pins required")


def read_i2f_future_source_pins(path: Path) -> I2fFutureSourcePins:
    """No implicit/latest GitHub HEAD, random UUID or default old Stage28b."""
    if not isinstance(path, Path) or path.is_symlink() or not path.is_file():
        raise I2fFuturePinsHold("new original pinned-source JSON file missing")
    try:
        raw = json.loads(path.read_bytes())
        fields = {
            "source_world_id", "source_branch_id", "source_committed_sha256",
            "fork_branch_id", "original_manifest_sha256",
            "original_manifest_files",
        }
        if type(raw) is not dict or set(raw) != fields:
            raise I2fFuturePinsHold("exact new original pin fields required")
        return I2fFutureSourcePins(**raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise I2fFuturePinsHold("new original pin JSON malformed") from exc


def inspect_i2f_future_original_sources(
    *, generation: Path, restored: Path, original_evidence: Path,
    pins: I2fFutureSourcePins,
):
    """Same-generation typed A/B Schema and independently pinned raw lineage.

    Historical source/manifest check requires a full original live trial
    receipt, never a synthetic Session list or a manifest derived at runtime.
    """
    if not isinstance(pins, I2fFutureSourcePins):
        raise I2fFuturePinsHold("new original pinned generation required")
    try:
        prepared = preflight_i2e_future_source(
            generation=generation, restored=restored,
            expected_world_id=pins.source_world_id,
            expected_source_branch_id=pins.source_branch_id,
            expected_committed_sha256=pins.source_committed_sha256,
            expected_fork_branch_id=pins.fork_branch_id,
        )
        history = inspect_original_stage28b_native_sessions(
            original_evidence, generation,
            expected_manifest_sha256=pins.original_manifest_sha256,
            expected_files=pins.original_manifest_files,
        )
        if (
            prepared.committed_sha256 != pins.source_committed_sha256
            or prepared.source_world_id != pins.source_world_id
            or prepared.restored_branch_id != pins.fork_branch_id
            or not set(
                dict(prepared.restored.plan.old_native_sessions).values()
            ).issubset(history.historical_native_sessions)
        ):
            raise I2fFuturePinsHold("new original historical Native/Owner lineage not pinned")
        for source in (generation, restored, original_evidence):
            if source.is_symlink() or not source.is_dir():
                raise I2fFuturePinsHold("new immutable original evidence root unavailable")
        return history, prepared
    except I2fFuturePinsHold:
        raise
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        raise I2fFuturePinsHold(
            "new original typed v3 Native/Paper evidence unqualified before World"
        ) from exc


def verify_i2f_original_source_unchanged(
    *, generation: Path, original_evidence: Path,
    pins: I2fFutureSourcePins,
) -> None:
    """Read-only end-of-trial recheck, no silent source resynthesis."""
    try:
        observed = inspect_original_stage28b_native_sessions(
            original_evidence, generation,
            expected_manifest_sha256=pins.original_manifest_sha256,
            expected_files=pins.original_manifest_files,
        )
        if (observed.source_manifest_sha256 != pins.original_manifest_sha256
                or hashlib.sha256(
                    (generation / "COMMITTED.json").read_bytes()
                ).hexdigest() != pins.source_committed_sha256):
            raise I2fFuturePinsHold("new original evidence/commit changed during World")
    except (OSError, RuntimeError, ValueError) as exc:
        raise I2fFuturePinsHold("new original evidence no longer immutable") from exc
