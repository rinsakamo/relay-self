"""Independent PROCESS entrypoint: S1/S2 Native append source-content audit.

No World/Native/GPU/Physical effects. Input hashes and S1 capture metadata
are supplied by the caller; they do NOT authenticate custody after restart.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, fields
from pathlib import Path

from relay_self.i_lane_i4a_s1_source_capture_dev import I4AS1SourceCapture
from relay_self.i_lane_i4a_s2_native_append_audit_dev import (
    audit_i4a_s2_native_append,
)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate receipt property")
        obj[k] = v
    return obj


def _capture(path: Path) -> I4AS1SourceCapture:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("original S1 receipt must be a regular absolute file")
    raw = path.read_bytes()
    if len(raw) > 16384:
        raise ValueError("oversize S1 receipt")
    data = json.loads(raw, object_pairs_hook=_unique)
    if type(data) is not dict or set(data) != {
        field.name for field in fields(I4AS1SourceCapture)
    }:
        raise ValueError("original S1 receipt exact schema required")
    ids = data["action_ids"]
    if (
        type(ids) is not list or not ids
        or any(type(x) is not str or not x for x in ids)
        or type(data["world_epoch"]) is not int
        or data["world_epoch"] < 0
        or any(type(data[k]) is not str or not data[k] for k in (
            "path", "raw_sha256", "wal_sha256", "self_id",
            "native_session_id", "old_skill_id", "old_intent_id",
            "classification",
        ))
        or type(data["raw_length"]) is not int or data["raw_length"] < 1
        or type(data["physical_authorized"]) is not bool
        or type(data["restart_authenticated"]) is not bool
    ):
        raise ValueError("unqualified original S1 receipt fields")
    data["action_ids"] = tuple(ids)
    return I4AS1SourceCapture(**data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--s2-wal", required=True, type=Path)
    parser.add_argument("--before-stdout", required=True, type=Path)
    parser.add_argument("--after-stdout", required=True, type=Path)
    parser.add_argument("--before-sha256", required=True)
    parser.add_argument("--after-sha256", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--skill-id", required=True)
    parser.add_argument("--intent-id", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = audit_i4a_s2_native_append(
            _capture(args.capture), s2_wal=args.s2_wal,
            before_stdout=args.before_stdout,
            after_stdout=args.after_stdout,
            before_sha256=args.before_sha256,
            after_sha256=args.after_sha256,
            action_id=args.action_id, skill_id=args.skill_id,
            intent_id=args.intent_id,
        )
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"I4A_S1_S2_NATIVE_CONTENT_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr, flush=True)
        return 2
    print(json.dumps(asdict(receipt), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
