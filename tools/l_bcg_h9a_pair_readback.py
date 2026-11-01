"""H9a: separately audit TWO real archived World roots before any pair comparison.

No Minecraft launch, no extra native read or Action, no Goal/physical admission.
Each World must have an independently frozen pre-World declaration.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from relay_self.l_bcg_h9a_pair import compare_h9a_pair, review_h9a_arm
from tools.l_bcg_h8_world_readback import audit as independently_audit_h8

_CRITICAL_ASSET_SUFFIXES = (
    "/minecraft.jar",
    "/server.properties",
    "/plugins/relay-metabolism-paper-dev.jar",
    "/plugins/RelayMetabolismDev/config.yml",
)


def _critical_runtime_assets(root: Path) -> tuple[str, ...]:
    """Compare original Paper/Plugin/config asset bytes by stored SHA, not temp paths."""
    path = root / "runtime-assets-sha256.json"
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 2_000_000:
        raise ValueError("missing/unsafe source runtime-asset manifest")
    manifest = json.loads(path.read_bytes())
    if type(manifest) is not dict:
        raise ValueError("runtime asset manifest must be object")
    values = []
    for suffix in _CRITICAL_ASSET_SUFFIXES:
        matches = [
            v.get("sha256") for k, v in manifest.items()
            if type(k) is str and k.endswith(suffix) and type(v) is dict
        ]
        if (
            len(matches) != 1 or type(matches[0]) is not str
            or len(matches[0]) != 64
            or any(ch not in "0123456789abcdef" for ch in matches[0])
        ):
            raise ValueError("missing/duplicate/invalid source critical runtime asset: " + suffix)
        values.append(matches[0])
    return tuple(values)


def _world(root: Path, prereg_path: Path, expected_id: str):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("missing/symlink independent World root")
    if not prereg_path.is_file() or prereg_path.is_symlink():
        raise ValueError("missing/symlink arm prereg")
    original_path = root / "s49-report.json"
    if not original_path.is_file() or original_path.is_symlink():
        raise ValueError("missing/symlink original report")
    for path in (original_path, prereg_path):
        if not 0 < path.stat().st_size <= 2_000_000:
            raise ValueError("invalid bounded original/prereg size")
    prereg = json.loads(prereg_path.read_bytes())
    if prereg.get("arm_id") != expected_id:
        raise ValueError("arm A/B prereg swapped")
    original = original_path.read_bytes()
    report = json.loads(original)
    # This independently reviews S49 command sequence, S7/S16/Paper,
    # same-source pre-Action sidecar and cleanup before evaluating H9a.
    audit = independently_audit_h8(root)
    result = review_h9a_arm(
        report=report, independent_h8_audit=audit,
        prereg=prereg, original_report_bytes=original,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arm_a_run_root", type=Path)
    parser.add_argument("arm_a_prereg", type=Path)
    parser.add_argument("arm_b_run_root", type=Path)
    parser.add_argument("arm_b_prereg", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.arm_a_run_root.resolve() == args.arm_b_run_root.resolve():
        parser.error("cannot compare same World directory")
    try:
        assets_a = _critical_runtime_assets(args.arm_a_run_root)
        assets_b = _critical_runtime_assets(args.arm_b_run_root)
        if assets_a != assets_b:
            raise ValueError("critical Paper/plugin/config asset SHA differs between Worlds")
        a = _world(args.arm_a_run_root, args.arm_a_prereg, "A")
        b = _world(args.arm_b_run_root, args.arm_b_prereg, "B")
        pair = compare_h9a_pair(a, b)
        text = json.dumps(asdict(pair), ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as f:
                f.write(text)
        print(text, end="")
        return 0
    except (OSError, ValueError, AssertionError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"H9a pair original review REJECTED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
