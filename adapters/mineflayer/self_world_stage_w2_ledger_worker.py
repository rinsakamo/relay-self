"""Isolated-process offline W2 ledger replay worker, no S10 or Minecraft.

This process must receive public-key PEM ONLY. Keys and extracted raw
evidence are caller-provided; their independent custody is a separate W2
qualification gate and never established by this executable.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.self_world_stage_v_attestation import StageVGrantRequest
from adapters.mineflayer.self_world_stage_w_gate import (
    StageWGateRejected,
    StageWOfflineConsumer,
    StageWPersistentGrantLedger,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="W2 offline one-use worker")
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--expected-request", type=Path, required=True)
    parser.add_argument("--public-pem", type=Path, required=True)
    parser.add_argument("--public-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)

    # No private key argument, no way to request original S49 Action, no live S10.
    try:
        if not args.receipt.is_absolute() or args.receipt.exists():
            raise StageWGateRejected("new absolute receipt pathname required")
        expected = StageVGrantRequest.from_dict(
            json.loads(args.expected_request.read_text(encoding="utf-8"))
        )
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
        consumer = StageWOfflineConsumer(
            pinned_public_pem=args.public_pem.read_bytes(),
            pinned_public_fingerprint=args.public_sha256,
            expected_run_id=args.run_id,
            ledger=StageWPersistentGrantLedger(args.ledger),
        )
        result = consumer.verify_and_reserve_once(
            envelope=envelope, expected=expected,
            independent_archive_path=args.archive,
            independently_pinned_archive_sha256=args.archive_sha256,
        )
        # Reserve has already COMMITTED. Failure to record the witness is a
        # consumed-grant/no-witness failure, NEVER permission to retry.
        fd = os.open(
            str(args.receipt), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(result), stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"W2_OFFLINE_DENIED:{type(exc).__name__}", file=sys.stderr)
        return 2
    print("W2_OFFLINE_RESERVED_READONLY", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
