"""Emit *synthetic-only* source-shaped S1 proof stream via unchanged pinned S1 code.

CI-only. Uses existing S1 bounded driver tests, no processes, socket, world,
model call, physical Action or external evidence directory.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from test_self_continuous_host import _fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.out
    if not out.is_absolute() or out.is_symlink() or out.exists() or not out.parent.is_dir():
        raise ValueError("new absolute CI-only fixture path required")
    with tempfile.TemporaryDirectory(prefix="v-s1-source-shaped-") as scratch:
        scratch_path = Path(scratch)
        driver, probe, grant, execute, _requests, source = _fixture(scratch_path)
        result = asyncio.run(driver.run(
            probe=probe, grant=grant, on_action=execute,
        ))
        if (
            result.get("events") != 2
            or result.get("action_requests") != 1
            or result.get("closed_outcomes") != 1
            or source.calls != 2
        ):
            raise ValueError("pinned S1 synthetic fixture changed")
        native = (scratch_path / "events.jsonl").read_bytes()
        with out.open("xb") as output:
            output.write(native)
    print(json.dumps({
        "status": "PINNED_S1_SYNTHETIC_SOURCE_SHAPED_ONLY",
        "events": 2, "closed_outcomes": 1, "physical_actions": 0,
        "real_world_origin": "NOT_ATTESTED", "out": str(out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
