"""Stage28c2a: inspect source-pinned recovered original A/B owners offline.

Does not start Paper, Mineflayer or Gemma, connect native sessions, send
physical effects, persist new cognition or modify the saved fork.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.stage28c2_recovered_resident_owner_dev import (
    prepare_recovered_a_b_resident_owners,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored-directory", type=Path, required=True)
    parser.add_argument("--expected-world-id", required=True)
    parser.add_argument("--expected-source-branch-id", required=True)
    parser.add_argument("--expected-committed-sha256", required=True)
    parser.add_argument("--expected-fork-branch-id", required=True)
    args = parser.parse_args()
    try:
        result = prepare_recovered_a_b_resident_owners(
            args.generation, args.restored_directory,
            expected_world_id=args.expected_world_id,
            expected_source_branch_id=args.expected_source_branch_id,
            expected_committed_sha256=args.expected_committed_sha256,
            expected_fork_branch_id=args.expected_fork_branch_id,
        )
        print(json.dumps({
            "classification": "STAGE28C2A_ORIGINAL_A_B_OFFLINE_OWNER_PREBIND",
            "receipt": asdict(result.receipt),
            "native_online": False,
            "new_worldbody_observed": False,
            "world_started": False,
            "model_post": False,
            "physical_action_issued": False,
        }, sort_keys=True), flush=True)
        return 0
    except Exception as exc:
        print(
            f"STAGE28C2A_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
