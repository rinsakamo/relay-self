"""Stage28c1: inspect or prepare one new inert A/B + Paper World branch.

Only copies a previously committed **typed** stopped-Paper generation;
never starts Minecraft, joins Self A/B, uses a GPU or issues an Action.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.stage28c1_inert_restore_dev import (
    inspect_stage28c_source,
    prepare_stage28c_inert_restore,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--expected-world-id", required=True)
    parser.add_argument("--expected-source-branch-id", required=True)
    parser.add_argument(
        "--expected-generation-id", default="g-000000000000",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--prepare-once", action="store_true")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source-committed-sha256")
    parser.add_argument("--restore-id")
    args = parser.parse_args()

    try:
        if args.inspect_only:
            if (
                args.destination is not None or args.restore_id is not None
                or args.source_committed_sha256 is not None
            ):
                raise ValueError("inspect-only must not accept restore arguments")
            source = inspect_stage28c_source(
                args.generation,
                expected_world_id=args.expected_world_id,
                expected_source_branch_id=args.expected_source_branch_id,
                expected_generation_id=args.expected_generation_id,
            )
            print(json.dumps({
                "classification": "STAGE28C1_SOURCE_TYPED_INSPECT_ONLY",
                "source": asdict(source),
                "world_created": False,
                "new_paper_started": False,
                "native_joined": False,
                "model_post": False,
            }, sort_keys=True), flush=True)
            return 0
        if (
            args.destination is None
            or args.restore_id is None or not args.restore_id.strip()
            or args.source_committed_sha256 is None
            or len(args.source_committed_sha256) != 64
        ):
            raise ValueError("prepare requires fresh destination, restore ID and pinned SHA256")
        result = prepare_stage28c_inert_restore(
            args.generation, args.destination,
            expected_world_id=args.expected_world_id,
            expected_source_branch_id=args.expected_source_branch_id,
            expected_committed_sha256=args.source_committed_sha256,
            restore_id=args.restore_id,
            expected_generation_id=args.expected_generation_id,
        )
        print(json.dumps({
            "classification": "STAGE28C1_INERT_TYPED_WORLD_SELF_RESTORE_DEV",
            "receipt": asdict(result),
            "world_created": False,
            "new_paper_started": False,
            "native_joined": False,
            "model_post": False,
        }, sort_keys=True), flush=True)
        return 0
    except Exception as exc:
        print(
            f"STAGE28C1_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
