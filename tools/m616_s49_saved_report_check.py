"""Offline-only S49 saved JSON M intake with automatic pinned source bootstrap.

No manual sys.path shims, World, server, LLM, native read or Action.
Requires an existing clean original S49 #674 checkout at the exact SHA.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.m616_s49_owner_bootstrap import (
    S49OwnerBootstrapRejected,
    bootstrap_original_s49_owner,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="M #616 DEV original S49 report")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--s49-owner-dir", type=Path)
    parser.add_argument("--admit-dev", action="store_true")
    args = parser.parse_args()
    if not args.admit_dev:
        print(json.dumps({
            "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
            "status": "DISABLED", "reason": "explicit_admit_dev_required",
        }, sort_keys=True))
        return 2
    if args.s49_owner_dir is None:
        print(json.dumps({
            "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
            "status": "DEFERRED", "reason": "original_s49_owner_dir_required",
        }, sort_keys=True))
        return 2
    try:
        bootstrap_original_s49_owner(args.s49_owner_dir)
    except S49OwnerBootstrapRejected:
        print(json.dumps({
            "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
            "status": "DEFERRED", "reason": "original_s49_checkout_unverified",
        }, sort_keys=True))
        return 2
    from experiments.metabolism_s49_owner_admission import (
        S49MAdmissionLease,
        bounded_s49_m_admission_row,
    )

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
