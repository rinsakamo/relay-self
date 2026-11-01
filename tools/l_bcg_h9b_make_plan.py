"""Create an H9b prospective protocol BEFORE first real World; not a launcher."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.l_bcg_h9b_dev_holdout import build_h9b_plan, source_digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--executor-head", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    plan = build_h9b_plan(executor_head=args.executor_head)
    raw = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with args.output.open("xb") as f:
        f.write(raw)
    print(json.dumps({
        "plan_sha256": source_digest(raw),
        "worlds": 8, "dev_fit_worlds": 4, "dev_eval_worlds": 4,
        "formal_training_worlds": 0,
        "first_real_world_must_not_have_started": True,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
