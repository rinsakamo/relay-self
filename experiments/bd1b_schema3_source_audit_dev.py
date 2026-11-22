"""Separate process, read-only Schema3 original World/Self byte crosscheck.

No Paper/GPU/model launch or qualification; a local SHA pin is NOT trusted
operator timing, server authenticity or external custody.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.bd1b_schema3_source_readback_dev import (
    audit_schema3_original_source_bytes,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--committed-sha256", required=True)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--prelogin-sha256", required=True)
    args = parser.parse_args()
    try:
        proof = audit_schema3_original_source_bytes(
            evidence_dir=args.evidence_dir, generation=args.generation,
            expected_committed_sha256=args.committed_sha256,
            expected_producer_report_sha256=args.report_sha256,
            expected_prelogin_manifest_sha256=args.prelogin_sha256,
        )
        print(json.dumps(asdict(proof), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"BD1B_SCHEMA3_SOURCE_HOLD:{type(exc).__name__}:{exc}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
