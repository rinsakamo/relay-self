"""Read-only SHA-preserving M616 S49 original evidence energy coverage audit.

Accept a previously archived, separate S49/B0 real World DEV artifact. A
successful audit means the *missing WorldTick energy source was honestly
reported*, not that physical World time, B0 energy debit, or native/Paper
independent source attestation succeeded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from experiments.metabolism_s49_worldtick_energy_gate import (
    audit_original_s49_energy_coverage,
    bounded_world_tick_energy_gate,
)

_REQUIRED = frozenset({
    "exit.json", "m-original-b0.json", "minecraft.log", "preflight.log",
    "s49-report.json", "stderr.log", "stdout.log",
})
_SHA_LINE = re.compile(r"([0-9a-f]{64})  (m616-b0-evidence/([^/]+))")


class M616OriginalEnergyAuditRejected(ValueError):
    """Incomplete, corrupted or foreign prior-World source evidence."""


def audit_preserved_b0_evidence(root: Path) -> dict[str, object]:
    if not isinstance(root, Path) or not root.is_dir() or root.is_symlink():
        raise M616OriginalEnergyAuditRejected("untrusted evidence directory")
    checksum_file = root / "SHA256SUMS"
    if not checksum_file.is_file() or checksum_file.is_symlink():
        raise M616OriginalEnergyAuditRejected("missing protected SHA list")
    try:
        text = checksum_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise M616OriginalEnergyAuditRejected("SHA list unreadable") from exc
    lines = text.splitlines()
    if len(lines) != len(_REQUIRED):
        raise M616OriginalEnergyAuditRejected("source file count changed")
    observed = set()
    for line in lines:
        match = _SHA_LINE.fullmatch(line)
        if match is None:
            raise M616OriginalEnergyAuditRejected("invalid source SHA declaration")
        expected_sha, _, name = match.groups()
        if name in observed or name not in _REQUIRED:
            raise M616OriginalEnergyAuditRejected("missing/duplicate evidence file")
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise M616OriginalEnergyAuditRejected("original source is missing/linked")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise M616OriginalEnergyAuditRejected("original saved source SHA changed")
        observed.add(name)
    if observed != _REQUIRED:
        raise M616OriginalEnergyAuditRejected("source manifest is incomplete")
    try:
        exit_status = json.loads((root / "exit.json").read_text(encoding="utf-8"))
        s49 = json.loads((root / "s49-report.json").read_text(encoding="utf-8"))
        m = json.loads((root / "m-original-b0.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise M616OriginalEnergyAuditRejected("original JSON invalid") from exc
    if (
        type(exit_status) is not dict or exit_status.get("process_exit") != 0
        or exit_status.get("world_attempts") != 1
        or exit_status.get("retries") != 0
    ):
        raise M616OriginalEnergyAuditRejected("one original World success unconfirmed")
    audit = audit_original_s49_energy_coverage(s49, m)
    if audit.status != "DEFERRED":
        raise M616OriginalEnergyAuditRejected("original source join invalid")
    saved = bounded_world_tick_energy_gate(audit)
    return {
        **saved,
        "source_evidence": "PR_711_ORIGINAL_WORLD_ARTIFACT_SHA_READBACK_DEV",
        "original_evidence_files_sha_matched": len(_REQUIRED),
        "original_world_attempts": 1,
        "original_retries": 0,
        "original_process_exit": 0,
        "original_artifact_sha_list_authenticated_by_independent_custodian": False,
        "original_artifact_bytes_unchanged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M #616 saved S49/B0 WorldTick energy NO_DEBIT audit"
    )
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("refusing to overwrite an existing original or audit")
    saved = audit_preserved_b0_evidence(args.evidence_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as file:
        json.dump(saved, file, ensure_ascii=False, sort_keys=True, allow_nan=False)
        file.write("\n")
    print(json.dumps(saved, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
