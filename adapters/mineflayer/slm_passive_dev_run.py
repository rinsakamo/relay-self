"""One explicitly authorized disposable S49 World, no language model."""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from adapters.mineflayer.s49_normal_session_real_ci import qualify
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "S49-SLM-ONE-DISPOSABLE-DEV-WORLD" or not args.output_dir.is_absolute():
        parser.error("fresh absolute output and explicit disposable DEV grant required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "native").mkdir()
    os.environ["S49_REAL_SERVER_CI"] = "1"
    return asyncio.run(qualify(
        args.output_dir / "report.json", args.output_dir / "server.log",
        raw_capture_root=args.output_dir / "native",
        slm_dev_owner=S49SLMDevOwner(),
    ))


if __name__ == "__main__":
    raise SystemExit(main())
