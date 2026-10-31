"""One explicitly authorized disposable S49 World, no language model."""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from adapters.mineflayer.s49_normal_session_real_ci import qualify
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from adapters.mineflayer.slm_prior_world_dev import read_previous_s49_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument(
        "--previous-world-root", type=Path, default=None,
        help="Read-only prior S49 report.json and native W3 root; never L8 training",
    )
    parser.add_argument(
        "--previous-w3-sha256", default=None,
        help="Previously recorded raw W3 SHA256, fixed before this World",
    )
    parser.add_argument(
        "--l8-empty-memory-shadow", action="store_true",
        help="Opt in to retention-enabled L8 read-only shadow with NO admitted Goal data",
    )
    args = parser.parse_args()
    if args.confirm != "S49-SLM-ONE-DISPOSABLE-DEV-WORLD" or not args.output_dir.is_absolute():
        parser.error("fresh absolute output and explicit disposable DEV grant required")
    if (args.previous_world_root is None) != (args.previous_w3_sha256 is None):
        parser.error("both previous source root and original W3 SHA are required")
    prior = None
    if args.previous_world_root is not None:
        prior = read_previous_s49_world(
            args.previous_world_root, expected_stdout_sha256=args.previous_w3_sha256,
        )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "native").mkdir()
    os.environ["S49_REAL_SERVER_CI"] = "1"
    return asyncio.run(qualify(
        args.output_dir / "report.json", args.output_dir / "server.log",
        raw_capture_root=args.output_dir / "native",
        slm_dev_owner=S49SLMDevOwner(
            retention_enabled=args.l8_empty_memory_shadow,
            prior_world=prior,
        ),
    ))


if __name__ == "__main__":
    raise SystemExit(main())
