"""D10 independent, SECOND-PROCESS original D9 evidence inspection CLI.

Use *after* D9 Paper and native children are stopped and
stage28_d10_seal_original_dev has exclusively written the manifest.
No Paper/native/GPU/physical operation or source modification is permitted.
An independently audited readout is written outside the frozen original
evidence directory and is not allowed to change its manifest inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.exploration_d10_original_source_audit_dev import (
    D10OriginalAuditHold,
    audit_d10_original_d9_source,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--manifest-files", type=int, required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--committed-sha256", required=True)
    args = parser.parse_args()
    try:
        inspected = audit_d10_original_d9_source(
            args.evidence_dir, args.generation,
            expected_manifest_sha256=args.manifest_sha256,
            expected_files=args.manifest_files,
            expected_world_id=args.world_id,
            expected_source_branch_id=args.source_branch,
            expected_committed_sha256=args.committed_sha256,
        )
        path = args.evidence_dir.parent / "d10-independent-audit.json"
        if (
            path.is_symlink() or args.evidence_dir.parent.is_symlink()
            or path.parent.resolve() == args.evidence_dir.resolve()
        ):
            raise D10OriginalAuditHold("audit output must be outside sealed evidence")
        raw = (
            json.dumps(asdict(inspected), sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")
        # Every audit is a one-shot independent process. Never clobber old
        # results, silently retry or place report within sealed source.
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != raw:
            raise D10OriginalAuditHold("audit readback bytes differ")
        digest = hashlib.sha256(raw).hexdigest()
    except (D10OriginalAuditHold, ValueError, RuntimeError, OSError) as exc:
        print(f"D10_AUDIT_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": inspected.independent_source_classification,
        "audit_path": str(path),
        "audit_sha256": digest,
        "model_choice": inspected.original_model_choice_id,
        "original_l2_replay_authorized": False,
        "real_world_execution_attested_by_offline_report": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
