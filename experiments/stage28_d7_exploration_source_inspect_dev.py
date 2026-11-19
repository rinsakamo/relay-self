"""D7 local DEV: inspect candidate ONLY, never operate Paper/Native/Gemma.

The B source-bound real rejoin runner has independent hardcoded World/cut
pins. A D candidate is not eligible for that runner until a genuine D-carrying
Stage28b cut exists and B accepts a new source-pinned live runner integration.
This command refuses to promote a synthetic candidate to a live trial.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.exploration_d7_real_world_preflight_dev import (
    D7RealWorldPreflightHold,
    inspect_d7_real_world_candidate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--fork-branch", required=True)
    parser.add_argument("--committed-sha256", required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if not args.inspect_only or args.execute_once:
            raise D7RealWorldPreflightHold(
                "inspection cannot execute Paper; use original B owned-runner "
                "only after a genuine D-journal typed source and independent "
                "runtime authority have been verified"
            )
        candidate = inspect_d7_real_world_candidate(
            args.generation, args.restored,
            expected_world_id=args.world_id,
            expected_source_branch_id=args.source_branch,
            expected_fork_branch_id=args.fork_branch,
            expected_committed_sha256=args.committed_sha256,
            expected_generation_id=args.generation_id,
        )
        print(json.dumps(asdict(candidate), sort_keys=True, indent=2))
        return 0
    except (D7RealWorldPreflightHold, OSError, ValueError) as exc:
        print(f"D7_REAL_WORLD_PRE_WORLD_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
