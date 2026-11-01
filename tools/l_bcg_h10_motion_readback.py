"""Read preserved H9b eight real World originals for H10 timing/proxy diagnosis.

Reads saved S49 reports AND independently authored H8 readback SHA.
NEVER launches Minecraft, touches executors or promotes qualified labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_h10_motion_variability import (
    H10Rejected, SLOTS, inspect_h10_world, summarize_h10,
)


def _bytes(path: Path, max_bytes: int = 2_000_000) -> bytes:
    if (
        not path.is_file() or path.is_symlink()
        or not 0 < path.stat().st_size <= max_bytes
    ):
        raise H10Rejected("missing/unsafe archived source: " + str(path))
    return path.read_bytes()


def audit_archived_eight_worlds(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise H10Rejected("H9b original root missing/symlink")
    records = []
    for slot in SLOTS:
        base = root / "worlds" / slot
        run = base / "run1"
        original = _bytes(run / "s49-report.json")
        report = json.loads(original)
        audit = json.loads(_bytes(base / "independent-audit.json"))
        manifest_raw = _bytes(base / "original-sha256.json")
        manifest = json.loads(manifest_raw)
        _sha = hashlib.sha256(original).hexdigest()
        if (
            manifest.get("s49-report.json") != _sha
            or audit.get("original_sha256", {}).get("s49-report.json") != _sha
        ):
            raise H10Rejected("source report digest mismatch: " + slot)
        result = inspect_h10_world(
            slot=slot, report=report, report_original=original,
            audit=audit, original_manifest=manifest,
        )
        records.append(result)
    forensic = summarize_h10(tuple(records))
    # Reconfirm original H9b paper proxy totals were those scored;
    # H10 cannot retroactively change H9b FIT/EVAL, scores or source split.
    eval_original = _bytes(root / "eval-result.json", 15_000)
    eval_report = json.loads(eval_original)
    if (
        eval_report.get("classification") != "H9B_8_WORLD_DEV_PROXY_FIT_EVAL_ONLY"
        or eval_report.get("candidate_vs_cheap_threshold") != "EQUIVALENT_WITHIN_1E-9_M"
        or eval_report.get("fit_world_count") != 4
        or eval_report.get("eval_world_count") != 4
        or eval_report.get("qualification") != "NO_GO"
        or eval_report.get("science") != "NOT_RUN"
        or eval_report.get("learned_l1_attention") != "DEFER_UNKNOWN"
    ):
        raise H10Rejected("original H9b frozen evaluation classification changed")
    refs = {w.slot: w.paper_proxy_total_m for w in forensic.worlds}
    originals = eval_report["scores"]
    if (
        len(originals) != 4
        or set(x["slot_id"] for x in originals) != set(SLOTS[4:])
        or any(
            abs(refs[s["slot_id"]] - s["outcome_proxy_m"]) > 1e-10
            for s in originals
        )
    ):
        raise H10Rejected("H10 Paper proxy differs from preserved H9b EVAL result")
    return {
        **asdict(forensic),
        "eval_result_sha256": hashlib.sha256(eval_original).hexdigest(),
        "eval_paper_proxy_matches_frozen_score_source": True,
        "source_is_same_preserved_h9b_originals": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("h9b_archived_root", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        report = audit_archived_eight_worlds(args.h9b_archived_root)
        output = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
        if args.output is not None:
            with args.output.open("xb") as f:
                f.write(output)
        print(json.dumps({
            "classification": report["classification"],
            "modal_baseline_worlds": report["modal_baseline_worlds"],
            "unique_proxy_patterns": report["unique_proxy_patterns"],
            "max_proxy_total_slot": report["max_proxy_total_slot"],
            "min_proxy_total_slot": report["min_proxy_total_slot"],
            "clock_alignment": report["paper_native_clock_alignment"],
            "cause_of_variability": report["cause_of_variability"],
            "qualification": report["qualification"],
            "science": report["science"],
        }, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError, AssertionError) as exc:
        ap.exit(2, "H10 original retrospective source REJECTED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
