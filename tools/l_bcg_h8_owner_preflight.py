"""Archived H5 H8 owner availability preflight (no World or Action)."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_dev_proxy import DevProxyRejected
from relay_self.l_bcg_h8_owner_availability import inspect_h8_owner_sources


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("evidence_root", type=Path)
    p.add_argument("--audit-classification", default="DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED")
    args = p.parse_args()
    names = {
        "host_report_original": "run1/s49-report.json",
        "independent_audit_original": "independent-audit.json",
        "s16_original": "run1/capture/l18_s16_terminal_original.jsonl",
        "s7_received_prefix_original":
            "run1/capture/pre-next-l0-prefix/native_bridge_received_original.jsonl",
        "paper_server_original": "run1/server.log",
        "operator_goal_plan_original": "run1/capture/l16_pre_world_goal_plan.json",
    }
    try:
        inp = {}
        for key, value in names.items():
            path = args.evidence_root / value
            if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 2_000_000:
                raise DevProxyRejected("missing, symlink or oversized H5 source: " + key)
            inp[key] = path.read_bytes()
        result = inspect_h8_owner_sources(**inp, audit_classification=args.audit_classification)
        print(json.dumps(asdict(result), ensure_ascii=False, allow_nan=False, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        p.exit(2, "H8 OWNER SOURCE PREFLIGHT REJECTED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
