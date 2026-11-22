"""Stage28c2b: immutable Stage28b raw evidence -> full historical native denylist.

A user-supplied session list is NOT source evidence. Read the original
Stage28b manifest and its unique actual resident report, cross-check the
typed generation's final historical native IDs, and deny every original
initial/rejoined native session before launching a new child.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from relay_self.self_owner_checkpoint_dev import verify_typed_generation


class HistoricalSessionHold(RuntimeError):
    """The original A/B session lineage is incomplete or unverified."""


@dataclass(frozen=True, slots=True)
class HistoricalNativeSessionReceipt:
    evidence_root: str
    source_manifest_sha256: str
    resident_report_sha256: str
    historical_native_sessions: tuple[str, ...]
    original_a_initial: str
    original_a_rejoined: str
    original_b_initial: str
    manifest_files: int
    source_verified: bool = True
    new_native_session_authorized: bool = False


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise HistoricalSessionHold("missing original evidence or symlink")
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def inspect_original_stage28b_native_sessions(
    evidence_root: Path, generation: Path, *,
    expected_manifest_sha256: str,
    expected_files: int = 285,
    expected_report_classification: str = (
        "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV"
    ),
) -> HistoricalNativeSessionReceipt:
    """Verify every original file, then recover the complete real A/B history.

    The outer manifest covers all evidence files except itself and the
    generation's three checksum files, which the typed verifier checks.
    This routine is read-only and never authorizes an Action.
    """
    root = Path(evidence_root)
    if (
        root.is_symlink() or not root.is_dir()
        or type(expected_manifest_sha256) is not str
        or re.fullmatch(r"[a-f0-9]{64}", expected_manifest_sha256) is None
        or type(expected_files) is not int or expected_files < 1
        or expected_report_classification not in (
            "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV",
            "I2G_REAL_ORIGINAL_V3_TYPED_A_B_CAPTURED_AUDIT_PENDING",
        )
    ):
        raise HistoricalSessionHold("original Stage28b evidence pins required")
    manifest = root / "SHA256SUMS"
    if _sha(manifest) != expected_manifest_sha256:
        raise HistoricalSessionHold("Stage28b manifest SHA256 differs")
    try:
        entries = manifest.read_text(encoding="utf-8").splitlines()
        expected: dict[str, str] = {}
        for line in entries:
            matched = re.fullmatch(r"([a-f0-9]{64}) [ *](.+)", line)
            if matched is None:
                raise HistoricalSessionHold("unsupported SHA256SUMS entry")
            digest, raw = matched.groups()
            rel = PurePosixPath(raw)
            if (
                rel.is_absolute() or ".." in rel.parts
                or not rel.parts or rel.as_posix() in expected
            ):
                raise HistoricalSessionHold("unsafe/duplicate evidence path")
            expected[rel.as_posix()] = digest
        if len(expected) != expected_files:
            raise HistoricalSessionHold("original evidence manifest size mismatch")
        got: set[str] = set()
        for file in root.rglob("*"):
            if file.is_symlink():
                raise HistoricalSessionHold("symlink in original evidence")
            if file.is_file():
                rel = file.relative_to(root).as_posix()
                if rel != "SHA256SUMS":
                    got.add(rel)
            elif not file.is_dir():
                raise HistoricalSessionHold("unsupported evidence node")
        # The archived outer manifest excludes files named SHA256SUMS.  The
        # three nested checksum files are verified by verify_typed_generation
        # against the committed, outer-manifest-covered inventory.
        generation_path = Path(generation).resolve()
        try:
            generation_rel = generation_path.relative_to(root.resolve())
        except ValueError:
            generation_rel = None
        nested = set()
        if generation_rel is not None:
            committed_rel = (generation_rel / "COMMITTED.json").as_posix()
            if committed_rel not in expected:
                raise HistoricalSessionHold("generation commit is not in original manifest")
            for path in (
                "world/SHA256SUMS",
                "paper-dimensions/world_nether/SHA256SUMS",
                "paper-dimensions/world_the_end/SHA256SUMS",
            ):
                rel = (generation_rel / path).as_posix()
                nested.add(rel)
        if got != set(expected) | nested:
            raise HistoricalSessionHold("missing/untracked original evidence files")
        for relative, digest in expected.items():
            if _sha(root / relative) != digest:
                raise HistoricalSessionHold("original evidence bytes modified")
        candidates = [
            name for name in expected
            if name.endswith("resident-presence-result.json")
        ]
        if len(candidates) != 1:
            raise HistoricalSessionHold("unique original Paper/native report missing")
        report_file = root / candidates[0]
        report = json.loads(report_file.read_bytes())
        if (
            report.get("classification") != expected_report_classification
            or (expected_report_classification.startswith("I2G_") and (
                report.get("i2g_original_v3_source") is not True
                or report.get("i2g_initial_source_verified") is not True
                or type(report.get("i2g_original_raw_native")) is not list
                or len(report["i2g_original_raw_native"]) != 3
                or report.get("i2g_source_manifest_independent_verified") is not False
            ))
            or type(report.get("steps")) is not list
            or len(report["steps"]) != 1
        ):
            raise HistoricalSessionHold("original real typed resident trial not attested")
        trial = report["steps"][0]
        a0 = trial["a_original_native_session"]
        b0 = trial["b_original_native_session"]
        a1 = trial["a_relogin_evidence"]["native_session_id"]
        if (
            not all(type(s) is str and s for s in (a0, b0, a1))
            or len({a0, b0, a1}) != 3
        ):
            raise HistoricalSessionHold("Stage28b A/B native history ambiguous")
        cuts = verify_typed_generation(Path(generation))
        former = {cut.self_id: cut.former_native_session_id for cut in cuts}
        if (
            set(former) != {"A", "B"}
            or former["A"] != a1 or former["B"] != b0
        ):
            raise HistoricalSessionHold("typed cognitive cut native sessions disagree")
    except HistoricalSessionHold:
        raise
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise HistoricalSessionHold("original A/B native evidence invalid") from exc
    return HistoricalNativeSessionReceipt(
        str(root.absolute()), expected_manifest_sha256,
        expected[candidates[0]], tuple(sorted((a0, a1, b0))),
        a0, a1, b0, len(expected),
    )
