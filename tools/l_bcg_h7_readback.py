"""H7 source-timed read-only Action PRE-observation, using archived H5 originals."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_dev_proxy import DevProxyRejected
from relay_self.l_bcg_h7_preaction import audit_h7_pre_action, compare_h7_cheap_pre_action


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archived_h5_root", type=Path)
    args = parser.parse_args()
    root = args.archived_h5_root
    names = {
        "host_report_original": "run1/s49-report.json",
        "independent_audit_original": "independent-audit.json",
        "s16_original": "run1/capture/l18_s16_terminal_original.jsonl",
        "s7_received_prefix_original":
            "run1/capture/pre-next-l0-prefix/native_bridge_received_original.jsonl",
        "paper_server_original": "run1/server.log",
    }
    try:
        originals: dict[str, bytes] = {}
        for name, rel in names.items():
            p = root / rel
            if not p.is_file() or p.is_symlink() or not (0 < p.stat().st_size <= 2_000_000):
                raise DevProxyRejected("missing/symlink/oversized original: " + name)
            originals[name] = p.read_bytes()
        result = audit_h7_pre_action(**originals)
        print(json.dumps({
            "pre_action": asdict(result),
            "cheap_compare": compare_h7_cheap_pre_action((result,)),
            "evidence_ceiling": "DEV_SOURCE_TIED_H5_NO_NEW_WORLD_NO_PHYSICAL_CLEAR",
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, f"H7 PRE-ACTION READBACK REJECTED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
