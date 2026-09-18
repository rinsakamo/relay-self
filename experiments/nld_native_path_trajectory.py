from __future__ import annotations

import argparse
import json
from pathlib import Path


def dry_run_payload() -> dict[str, object]:
    return {
        "evidence_class": "native path trajectory plan only",
        "case_id": "reversed_ridge_open",
        "modes": ["ar", "dlm", "linear_spec"],
        "measured_calls": 18,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = dry_run_payload()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(path)
    else:
        print(text)


if __name__ == "__main__":
    main()
