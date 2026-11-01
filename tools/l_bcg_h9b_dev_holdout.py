"""H9b DEV-only archived World fit freeze / heldout evaluation.

First run --freeze after FOUR independent fit Worlds, BEFORE ANY eval World.
Then store frozen-model bytes+SHA in every eval pre-World marker.
--evaluate validates original S49/S7/S16/Paper, each frozen marker,
8 distinct Worlds, and prospective second-line timestamp-only equivalence.
No new World, Action, provider or Memory writes by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from relay_self.l_bcg_h9a_config_forensics import (
    _check_arm,
    compare_h9a_archived_generated_timestamp,
)
from relay_self.l_bcg_h9b_dev_holdout import (
    SLOTS,
    H9bRecord,
    compare_h9b_dev_holdout,
    source_digest,
    validate_plan,
)
from relay_self.l_bcg_h9b_freeze import (
    freeze_h9b_dev_proxy,
    serialize_frozen,
)
from tools.l_bcg_h9a_pair_readback import _world


def _read_file(path: Path, max_bytes: int = 2_000_000) -> bytes:
    if (
        not path.is_file() or path.is_symlink()
        or not 0 < path.stat().st_size <= max_bytes
    ):
        raise ValueError(f"missing/unsafe bounded original: {path}")
    return path.read_bytes()


def _world_originals(root: Path) -> tuple[bytes, bytes, bytes]:
    return (
        _read_file(root / "run1/runtime-config/server.properties"),
        _read_file(root / "run1/runtime-assets-sha256.json"),
        _read_file(root / "original-sha256.json"),
    )


def _prospective_config_audit(roots: tuple[Path, ...]) -> tuple[str, ...]:
    """Plan-fixed timestamp exception, WITHOUT changing original H9a REJECTED."""
    originals = [_world_originals(root) for root in roots]
    references = []
    a = originals[0]
    base_sha, base_critical = _check_arm(*a)
    references.append(base_sha)
    for b in originals[1:]:
        sha, critical = _check_arm(*b)
        if critical[0] != base_critical[0] or critical[2:] != base_critical[2:]:
            raise ValueError("H9b Paper/plugin/config source assets changed")
        if sha != base_sha:
            result = compare_h9a_archived_generated_timestamp(
                a_config_original=a[0],
                a_runtime_assets_original=a[1],
                a_original_sha256_manifest=a[2],
                b_config_original=b[0],
                b_runtime_assets_original=b[1],
                b_original_sha256_manifest=b[2],
            )
            if not result.only_generated_timestamp_line_differs:
                raise ValueError("other configuration differences")
        elif b[0] != a[0]:
            raise ValueError("equal SHA but differing server.properties original")
        references.append(sha)
    return tuple(references)


def _predeclared_record(
    *, slot: str, arm: str, role: str, evidence_root: Path,
    plan_sha: str, executor_head: str, frozen_sha: str | None,
) -> tuple[H9bRecord, datetime]:
    if not evidence_root.is_dir() or evidence_root.is_symlink():
        raise ValueError("missing/unsafe distinct H9b World root")
    prereg_raw = _read_file(evidence_root / "predeclared.json")
    prereg = json.loads(prereg_raw)
    expected_meta = {
        "slot_id": slot, "role": role, "plan_sha256": plan_sha,
        "frozen_model_sha256": frozen_sha,
    }
    if prereg.get("h9b") != expected_meta:
        raise ValueError("H9b per-World prereg does not bind original plan/frozen fit")
    if prereg.get("executor_head") != executor_head:
        raise ValueError("H9b executor HEAD mismatch")
    if prereg.get("arm_id") != arm or prereg.get("requested_distance_m") != (
        2.0 if arm == "A" else 3.5
    ):
        raise ValueError("H9b wrong native S42 arm prereg")
    marker = json.loads(_read_file(evidence_root / "run1/WORLD_ATTEMPT_STARTED.json", 4096))
    if (
        marker.get("h9b_slot_id") != slot
        or marker.get("h9b_plan_sha256") != plan_sha
        or marker.get("h9b_prereg_sha256") != source_digest(prereg_raw)
        or marker.get("h9b_frozen_model_sha256") != frozen_sha
        or marker.get("max_worlds") != 1
        or marker.get("retry") != 0
    ):
        raise ValueError("World before-start marker not bound to H9b original plan/prereg/model")
    try:
        attempt_utc = datetime.fromisoformat(marker["launcher_entered_utc"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("missing marker start timestamp") from exc
    if attempt_utc.utcoffset() is None:
        raise ValueError("World attempt marker must be timezone-aware")
    # Existing _world verifies original H8 independent S7/S16/Paper/packet/
    # cleanup, then H9a original native 2m/3.5m owner readback.
    reviewed = _world(evidence_root / "run1", evidence_root / "predeclared.json", arm)
    return (
        H9bRecord(
            slot_id=slot, arm=reviewed,
            frozen_plan_sha256=plan_sha,
            prereg_sha256=source_digest(prereg_raw),
            frozen_model_sha256=frozen_sha,
        ),
        attempt_utc,
    )


def _load_records(
    *, plan: dict, plan_sha: str, root: Path, frozen_sha: str | None,
    how_many: int,
) -> tuple[H9bRecord, ...]:
    records = []
    times: list[datetime] = []
    roots = []
    for slot, arm, role in SLOTS[:how_many]:
        path = root / slot
        row, tick = _predeclared_record(
            slot=slot, arm=arm, role=role, evidence_root=path,
            plan_sha=plan_sha, executor_head=plan["executor_head"],
            frozen_sha=frozen_sha if role == "dev_eval" else None,
        )
        records.append(row)
        times.append(tick)
        roots.append(path)
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("H9b original World attempt marker chronology changed")
    _prospective_config_audit(tuple(roots))
    return tuple(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol_original", type=Path)
    parser.add_argument("eight_slot_evidence_root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    parser.add_argument("--frozen-original", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan_raw = _read_file(args.protocol_original, 8192)
        plan = json.loads(plan_raw)
        plan_sha = validate_plan(plan, raw=plan_raw)
        if args.freeze:
            if args.frozen_original:
                raise ValueError("--freeze must not use pre-existing model")
            fit = _load_records(
                plan=plan, plan_sha=plan_sha,
                root=args.eight_slot_evidence_root, frozen_sha=None, how_many=4,
            )
            frozen = freeze_h9b_dev_proxy(
                plan=plan, plan_original=plan_raw, fit_records=fit,
            )
            result = serialize_frozen(frozen)
            with args.output.open("xb") as out:
                out.write(result)
            print(json.dumps({
                "classification": frozen.classifier,
                "frozen_original_sha256": source_digest(result),
                "formal_training_worlds": 0,
                "fit_worlds": 4,
                "before_eval_worlds": True,
                "qualification": "NO_GO",
                "science": "NOT_RUN",
            }, sort_keys=True))
        else:
            if args.frozen_original is None:
                raise ValueError("--evaluate requires --frozen-original")
            frozen_bytes = _read_file(args.frozen_original, 4096)
            frozen_sha = source_digest(frozen_bytes)
            records = _load_records(
                plan=plan, plan_sha=plan_sha, root=args.eight_slot_evidence_root,
                frozen_sha=frozen_sha, how_many=8,
            )
            result = compare_h9b_dev_holdout(
                plan=plan, plan_original=plan_raw,
                records=records, frozen_model_original=frozen_bytes,
            )
            raw = (json.dumps(
                asdict(result), sort_keys=True, allow_nan=False,
                ensure_ascii=False,
            ) + "\n").encode()
            with args.output.open("xb") as out:
                out.write(raw)
            print(json.dumps({
                "classification": result.classification,
                "fit_worlds": result.fit_world_count,
                "eval_worlds": result.eval_world_count,
                "candidate_vs_cheap_threshold": result.candidate_vs_cheap_threshold,
                "qualification": "NO_GO", "science": "NOT_RUN",
            }, sort_keys=True))
        return 0
    except (OSError, ValueError, AssertionError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, "H9b DEV FIT/EVAL ORIGINAL REJECTED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
