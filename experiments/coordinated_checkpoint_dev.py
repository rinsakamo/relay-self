"""#860 CLI: offline coordinated World + multi-Self generation operations.

Does not run or stop Minecraft, quiesce Self owners, or grant Action issue.
Only use capture while World and all Self persistence writers are stopped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.coordinated_checkpoint_dev import (
    CoordinatedCheckpointError,
    SelfSnapshotSource,
    capture_generation,
    latest_verified_generation,
    restore_generation,
    verify_generation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--source-world", type=Path, required=True)
    capture.add_argument("--store", type=Path, required=True)
    capture.add_argument("--sequence", type=int, required=True)
    capture.add_argument("--self-sources-json", type=Path, required=True)
    capture.add_argument("--world-id", required=True)
    capture.add_argument("--branch-id", required=True)
    capture.add_argument("--logical-tick", type=int, required=True)
    capture.add_argument("--tick-source-ref", required=True)
    capture.add_argument("--stopped-server-ref", required=True)
    capture.add_argument("--quiesced-selves-ref", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--generation", type=Path, required=True)
    latest = sub.add_parser("latest")
    latest.add_argument("--store", type=Path, required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--generation", type=Path, required=True)
    restore.add_argument("--new-destination", type=Path, required=True)
    restore.add_argument("--restore-id", required=True)
    args = parser.parse_args()
    try:
        if args.operation == "capture":
            raw = json.loads(args.self_sources_json.read_text(encoding="utf-8"))
            if type(raw) is not dict or set(raw) != {"self_ids", "sources"}:
                raise CoordinatedCheckpointError("expected Self roster and source list")
            sources = tuple(
                SelfSnapshotSource(
                    self_id=row["self_id"],
                    cognition_file=Path(row["cognition_file"]),
                    physical_wal_file=Path(row["physical_wal_file"]),
                    owner_state_file=(
                        Path(row["owner_state_file"])
                        if row.get("owner_state_file") is not None else None
                    ),
                )
                for row in raw["sources"]
            )
            generation = capture_generation(
                args.source_world, args.store, sequence=args.sequence,
                expected_self_ids=tuple(raw["self_ids"]), selves=sources,
                world_id=args.world_id, branch_id=args.branch_id,
                logical_tick=args.logical_tick, tick_source_ref=args.tick_source_ref,
                stopped_server_ref=args.stopped_server_ref,
                quiesced_selves_ref=args.quiesced_selves_ref,
            )
            result = {"generation": str(generation), "verified": verify_generation(generation)}
        elif args.operation == "verify":
            result = verify_generation(args.generation)
        elif args.operation == "latest":
            found = latest_verified_generation(args.store)
            result = {"latest_verified": str(found) if found is not None else None}
        else:
            result = restore_generation(
                args.generation, args.new_destination, restore_id=args.restore_id,
            )
    except (CoordinatedCheckpointError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"COORDINATED_CHECKPOINT_DEV_REFUSED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
