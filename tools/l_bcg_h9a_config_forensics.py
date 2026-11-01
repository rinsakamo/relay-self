"""H9a posthoc original config forensic ONLY. Existing pair REJECTED stays REJECTED."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_h9a_config_forensics import (
    ConfigForensicsRejected,
    compare_h9a_archived_generated_timestamp,
)


def _arm(root: Path, prefix: str) -> dict[str, bytes]:
    if not root.is_dir() or root.is_symlink():
        raise ConfigForensicsRejected("missing/unsafe archival arm")
    files = {
        prefix + "_config_original": root / "run1/runtime-config/server.properties",
        prefix + "_runtime_assets_original": root / "run1/runtime-assets-sha256.json",
        prefix + "_original_sha256_manifest": root / "original-sha256.json",
    }
    out = {}
    for key, path in files.items():
        if (
            not path.is_file() or path.is_symlink()
            or not 0 < path.stat().st_size <= 2_000_000
        ):
            raise ConfigForensicsRejected("missing/unsafe archived original: " + key)
        out[key] = path.read_bytes()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_a", type=Path)
    parser.add_argument("archive_b", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.archive_a.resolve() == args.archive_b.resolve():
        parser.error("A/B must be separate archived Worlds")
    try:
        result = compare_h9a_archived_generated_timestamp(
            **_arm(args.archive_a, "a"), **_arm(args.archive_b, "b"),
        )
        data = json.dumps(asdict(result), ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as f:
                f.write(data)
        print(data, end="")
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, "H9a posthoc config forensic REJECTED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
