"""D8 original source-owned A/B real-run pins, backed by D7 cognitive cut.

A JSON pin by itself is NOT proof. Every acceptance reruns D7's original
three-dimension immutable World+A/B+D Question/L2 candidate gate; the B
original native history is independently verified by the original B parser.
No source is inferred from an earlier B World or from a run result string.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from relay_self.exploration_d7_real_world_preflight_dev import (
    D7RealWorldPreflightHold,
    D7SourceCandidate,
    inspect_d7_real_world_candidate,
)


class D8PinnedSourceHold(RuntimeError):
    """Missing exact D7/B immutable original source; do not start a World."""


@dataclass(frozen=True, slots=True)
class D8OwnedSourcePins:
    generation_id: str
    world_id: str
    source_branch_id: str
    fork_branch_id: str
    committed_sha256: str
    stage28b_evidence_sha256: str
    stage28b_evidence_files: int
    d10_source_audit_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            self.d10_source_audit_sha256 is not None
            and (
                type(self.d10_source_audit_sha256) is not str
                or re.fullmatch(
                    r"[0-9a-f]{64}", self.d10_source_audit_sha256,
                ) is None
            )
        ):
            raise D8PinnedSourceHold("D10 independent evidence SHA256 required")
        if (type(self.stage28b_evidence_files) is not int
                or not 1 <= self.stage28b_evidence_files <= 100000):
            raise D8PinnedSourceHold("bounded original evidence inventory count required")
        for field in (
            "generation_id", "world_id", "source_branch_id",
            "fork_branch_id", "committed_sha256",
            "stage28b_evidence_sha256",
        ):
            value = getattr(self, field)
            if type(value) is not str or not value.strip() or len(value) > 256:
                raise D8PinnedSourceHold("typed nonempty pinned source required")
        if not re.fullmatch(r"g-[0-9]{12}", self.generation_id):
            raise D8PinnedSourceHold("exact typed generation ID required")
        for digest in (self.committed_sha256, self.stage28b_evidence_sha256):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise D8PinnedSourceHold("exact immutable source SHA256 required")


def load_d8_pins(path: Path) -> D8OwnedSourcePins:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise D8PinnedSourceHold("new source-pin manifest unavailable")
    try:
        payload = json.loads(path.read_bytes())
        fields = set(D8OwnedSourcePins.__dataclass_fields__)
        if type(payload) is not dict or set(payload) not in (
            fields, fields - {"d10_source_audit_sha256"},
        ):
            raise D8PinnedSourceHold("strict source-pin JSON fields required")
        return D8OwnedSourcePins(**payload)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise D8PinnedSourceHold("invalid source-pin manifest") from exc


def inspect_d8_original_source(
    generation: Path, restored: Path, stage28b_evidence: Path,
    *, pins: D8OwnedSourcePins,
) -> tuple[D7SourceCandidate, object]:
    """Read exact source; B independently verifies historical native ledger."""
    if not isinstance(pins, D8OwnedSourcePins):
        raise D8PinnedSourceHold("typed original D8 source pins required")
    try:
        candidate = inspect_d7_real_world_candidate(
            generation, restored,
            expected_world_id=pins.world_id,
            expected_source_branch_id=pins.source_branch_id,
            expected_fork_branch_id=pins.fork_branch_id,
            expected_committed_sha256=pins.committed_sha256,
            expected_generation_id=pins.generation_id,
        )
    except (D7RealWorldPreflightHold, OSError, ValueError) as exc:
        raise D8PinnedSourceHold("D7 original D Question source refused") from exc
    from relay_self.stage28c2b_historical_native_sessions_dev import (
        inspect_original_stage28b_native_sessions,
    )

    try:
        historical_kwargs = {
            "expected_manifest_sha256": pins.stage28b_evidence_sha256,
            "expected_files": pins.stage28b_evidence_files,
        }
        if pins.d10_source_audit_sha256 is not None:
            historical_kwargs["expected_report_classification"] = (
                "REAL_D9_SOURCE_A_B_TYPED_CUT_CAPTURED_INDEPENDENT_AUDIT_PENDING"
            )
        # Preserve ORIGINAL B exact call signature for historic B sources.
        # Only D10 explicitly opts in to the new D9 source classification.
        historical = inspect_original_stage28b_native_sessions(
            stage28b_evidence, generation, **historical_kwargs,
        )
        if pins.d10_source_audit_sha256 is not None:
            # The D10 audit was made in a SECOND process, OUTSIDE the
            # immutable source manifest. Recalculate all original sources
            # rather than trusting its filename, success bit, or HASH alone.
            import hashlib
            from dataclasses import asdict

            from relay_self.exploration_d10_original_source_audit_dev import (
                audit_d10_original_d9_source,
            )

            audit_file = (
                Path(stage28b_evidence).parent / "d10-independent-audit.json"
            )
            if audit_file.is_symlink() or not audit_file.is_file():
                raise D8PinnedSourceHold("original independent D10 audit unavailable")
            raw = audit_file.read_bytes()
            if hashlib.sha256(raw).hexdigest() != pins.d10_source_audit_sha256:
                raise D8PinnedSourceHold("D10 independent audit digest differs")
            verified = audit_d10_original_d9_source(
                stage28b_evidence, generation,
                expected_manifest_sha256=pins.stage28b_evidence_sha256,
                expected_files=pins.stage28b_evidence_files,
                expected_world_id=pins.world_id,
                expected_source_branch_id=pins.source_branch_id,
                expected_committed_sha256=pins.committed_sha256,
            )
            if json.loads(raw) != json.loads(json.dumps(asdict(verified))):
                raise D8PinnedSourceHold(
                    "original independent D10 raw proof differs from current files"
                )
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        raise D8PinnedSourceHold("B/D10 original historical source not qualified") from exc
    if (
        candidate.source_kind != "STRUCTURAL_TYPED_CUT_ONLY"
        or candidate.real_world_attested
        or candidate.l2_dispatch_authorized
        or candidate.physical_action_issue_authorized
        or candidate.generation_id != pins.generation_id
        or candidate.world_id != pins.world_id
        or candidate.source_branch_id != pins.source_branch_id
        or candidate.fork_branch_id != pins.fork_branch_id
        or candidate.committed_sha256 != pins.committed_sha256
        or candidate.owner_roster != ("A", "B")
        or len(candidate.selves) != 2
        or not set(x.prior_native_session_id for x in candidate.selves).issubset(
            historical.historical_native_sessions
        )
    ):
        raise D8PinnedSourceHold("D Question/A-B historical sources disagree")
    return candidate, historical
