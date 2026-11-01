"""Offline-only S49 report intake for M #616, never starts a World/model.

Example:
 PYTHONPATH=src:. python -m tools.m616_s49_saved_report_check \
   --report /absolute/path/to/s49-report.json --admit-dev
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.metabolism_s49_owner_admission import (
    S49MAdmissionLease,
    bounded_s49_m_admission_row,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="M DEV read-only S49 report intake")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--admit-dev", action="store_true")
    args = parser.parse_args()

    # Default-off even for the CLI. No new native/LLM/Action operations.
    if not args.admit_dev:
        print(json.dumps({
            "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
            "status": "DISABLED", "reason": "explicit_admit_dev_required",
        }, sort_keys=True))
        return 2
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({
            "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
            "status": "DEFERRED", "reason": "unreadable_saved_report",
            "error_type": type(exc).__name__,
        }, sort_keys=True))
        return 2
    observed = S49MAdmissionLease(enabled=True).admit_report(report)
    output = bounded_s49_m_admission_row(observed)
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if observed.status == "RECORDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
