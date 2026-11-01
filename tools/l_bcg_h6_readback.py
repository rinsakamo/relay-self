"""Read ONLY existing H5 archived originals as an explicitly provisional H6 proxy."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_dev_proxy import (
    DevProxyRejected,
    read_h6_provisional_world,
    summarize_h6_provisional_worlds,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("--audit-classification", default="DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED")
    args = parser.parse_args()
    root = args.evidence_root
    try:
        names = {
            "host_report_original": "run1/s49-report.json",
            "independent_audit_original": "independent-audit.json",
            "s16_original": "run1/capture/l18_s16_terminal_original.jsonl",
            "s7_received_prefix_original":
                "run1/capture/pre-next-l0-prefix/native_bridge_received_original.jsonl",
            "paper_server_original": "run1/server.log",
        }
        evidence = {}
        for name, rel in names.items():
            path = root / rel
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 2_000_000:
                raise DevProxyRejected(f"missing/symlink/oversized {name}")
            evidence[name] = path.read_bytes()
        episode = read_h6_provisional_world(**evidence, audit_classification=args.audit_classification)
        comparison = summarize_h6_provisional_worlds((episode,))
        print(json.dumps({
            "episode": asdict(episode),
            "comparison": asdict(comparison),
            "evidence_ceiling": "PER_WORLD_DIGEST_MATCHED_NO_PHYSICAL_CLEAR",
            "qualified_training": False,
            "l1_action_authority": False,
            "qualification": "NO_GO",
            "science": "NOT_RUN",
        }, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"H6 PROVISIONAL READBACK REJECTED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
