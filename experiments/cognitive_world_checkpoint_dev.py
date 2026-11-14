"""Operator-facing offline World checkpoint CLI (#853).

The process never stops/starts a server, copies a live World by permission,
deletes an archive, edits a physical WAL, or issues a Minecraft Action.
"""
from __future__ import annotations

import argparse
import json

from relay_self.world_checkpoint_dev import (
    WorldCheckpointError,
    capture_stopped_world,
    restore_world_to_new_branch,
    verify_restored_world,
    verify_world_checkpoint,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    options = p.add_subparsers(dest="operation", required=True)

    capture = options.add_parser("capture", help="copy an externally stopped server World")
    capture.add_argument("--source-world", required=True)
    capture.add_argument("--archive-dir", required=True)
    capture.add_argument("--world-id", required=True)
    capture.add_argument("--branch-id", required=True)
    capture.add_argument("--checkpoint-id", required=True)
    capture.add_argument("--logical-tick", type=int, required=True)
    capture.add_argument("--tick-source-ref", required=True)
    capture.add_argument(
        "--stopped-server-ref", required=True,
        help="external server exit/save provenance, NOT checked by this command",
    )

    verify = options.add_parser("verify", help="read-only exact inventory/hash validation")
    verify.add_argument("--archive-dir", required=True)
    verify.add_argument("--expected-manifest-sha256", help="optional out-of-band DEV pin")

    restore = options.add_parser("restore", help="create a fresh branched World, NEVER overwrite")
    restore.add_argument("--archive-dir", required=True)
    restore.add_argument("--new-world-dir", required=True)
    restore.add_argument("--restore-id", required=True)
    restore.add_argument("--expected-manifest-sha256", help="optional out-of-band DEV pin")

    verify_restored = options.add_parser(
        "verify-restored", help="verify restored World bytes and new-branch receipt before launch",
    )
    verify_restored.add_argument("--archive-dir", required=True)
    verify_restored.add_argument("--restored-world-dir", required=True)
    verify_restored.add_argument("--expected-manifest-sha256", help="optional out-of-band DEV pin")

    args = p.parse_args()
    try:
        if args.operation == "capture":
            result = capture_stopped_world(
                args.source_world, args.archive_dir,
                world_id=args.world_id, branch_id=args.branch_id,
                checkpoint_id=args.checkpoint_id, logical_tick=args.logical_tick,
                tick_source_ref=args.tick_source_ref,
                stopped_server_ref=args.stopped_server_ref,
            )
        elif args.operation == "verify":
            result = verify_world_checkpoint(
                args.archive_dir, expected_manifest_sha256=args.expected_manifest_sha256,
            )
        elif args.operation == "verify-restored":
            result = verify_restored_world(
                args.archive_dir, args.restored_world_dir,
                expected_manifest_sha256=args.expected_manifest_sha256,
            )
        else:
            result = restore_world_to_new_branch(
                args.archive_dir, args.new_world_dir, restore_id=args.restore_id,
                expected_manifest_sha256=args.expected_manifest_sha256,
            )
    except (WorldCheckpointError, OSError) as exc:
        p.exit(2, f"WORLD_CHECKPOINT_DEV_REFUSED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
