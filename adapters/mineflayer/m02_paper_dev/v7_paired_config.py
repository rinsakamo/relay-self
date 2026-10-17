"""M0.2 prospective V7 Paper BASAL/WALK factorial configs (OFFLINE DEV ONLY).

This produces candidate text bytes, NOT a replacement for the qualified
Paper config SHA, not a World, not a SCIENCE grant. Only BASAL/WALK multipliers
may differ. SHAM_ON is bit-identical to BASE_ON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent
TEMPLATE = PLUGIN_ROOT / "src/main/resources/config.yml"
BASELINE_ENABLED_SHA256 = "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e"
ARMS = {
    "BASE_ON": (1, 1),
    "SHAM_ON": (1, 1),
    "BASAL_ZERO": (0, 1),
    "WALK_ZERO": (1, 0),
    "BOTH_ZERO": (0, 0),
}
EXPECTED_KINDS = frozenset((
    "BASAL", "WALK", "CROUCH", "SPRINT", "SWIM", "WALK_ON_WATER",
    "WALK_UNDERWATER", "JUMP", "JUMP_SPRINT", "ATTACK", "DAMAGED",
    "BLOCK_MINED", "REGEN", "HUNGER_EFFECT", "UNKNOWN", "COGNITION",
))


class V7ProfileRejected(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def enabled_source(raw: bytes) -> bytes:
    try:
        source = raw.decode("utf-8")
    except UnicodeError as exc:
        raise V7ProfileRejected("invalid source config bytes") from exc
    if source.count("dev-enabled: false") != 1 or len(raw) > 8192:
        raise V7ProfileRejected("foreign source config or oversize input")
    enabled = source.replace("dev-enabled: false", "dev-enabled: true", 1)
    if sha256(enabled.encode("utf-8")) != BASELINE_ENABLED_SHA256:
        raise V7ProfileRejected("not the pinned baseline M0.2 Paper settings")
    return enabled.encode("utf-8")


def render_arm(raw: bytes, arm: str) -> bytes:
    if arm not in ARMS:
        raise V7ProfileRejected("unregistered arm")
    baseline = enabled_source(raw).decode("utf-8")
    found = re.findall(r"^  ([A-Z_]+): \{", baseline, flags=re.MULTILINE)
    if len(found) != 16 or set(found) != EXPECTED_KINDS:
        raise V7ProfileRejected("missing or duplicated action rules")
    modified = baseline
    for kind, standard, unit, mult in (
        ("BASAL", "0.001", "tick", ARMS[arm][0]),
        ("WALK", "0.01", "block", ARMS[arm][1]),
    ):
        original = (f"  {kind}: {{unit: {unit}, standard: {standard}, "
                    "multiplier: 1.0, additional: 0.0, enabled: true}")
        if modified.count(original) != 1:
            raise V7ProfileRejected("candidate changed the original cost structure")
        modified = modified.replace(original, original.replace(
            "multiplier: 1.0", f"multiplier: {float(mult):.1f}"), 1)
    rendered = modified.encode("utf-8")
    if not (arm in ("BASE_ON", "SHAM_ON") and rendered == enabled_source(raw)
            or arm not in ("BASE_ON", "SHAM_ON")):
        raise V7ProfileRejected("sham source bytes changed unexpectedly")
    return rendered


def stage_candidate_configs(source: bytes, destination: Path) -> dict:
    """Exclusive new directory, config files only, fail before filesystem writes."""
    configs = {arm: render_arm(source, arm) for arm in ARMS}
    if sha256(configs["BASE_ON"]) != sha256(configs["SHAM_ON"]):
        raise V7ProfileRejected("sham differs from ON")
    if len({sha256(x) for x in configs.values()}) != 4:
        raise V7ProfileRejected("two-factor intervention lost expected identity")
    if (not destination.is_absolute() or destination.exists()
            or destination.is_symlink()
            or not destination.parent.is_dir() or destination.parent.is_symlink()):
        raise V7ProfileRejected("fresh isolated absolute destination required")
    receipt = {
        "classification": "S_V7_M02_FIVE_CANDIDATE_CONFIGS_OFFLINE_ONLY",
        "profile_source_sha256": BASELINE_ENABLED_SHA256,
        "science_go": False, "qualification_reused": False,
        "real_world_starts": 0, "physics_ecologically_calibrated": False,
        "configs": {
            arm: {"basal_multiplier": ARMS[arm][0],
                  "walk_multiplier": ARMS[arm][1],
                  "sha256": sha256(payload)}
            for arm, payload in configs.items()
        },
    }
    destination.mkdir(mode=0o700)
    for arm, data in configs.items():
        folder = destination / arm
        folder.mkdir(mode=0o700)
        with (folder / "config.yml").open("xb") as target:
            target.write(data)
    with (destination / "offline-only-manifest.json").open("x", encoding="utf-8") as output:
        json.dump(receipt, output, sort_keys=True, indent=2)
        output.write("\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-root", type=Path)
    args = parser.parse_args()
    raw = TEMPLATE.read_bytes()
    if args.stage_root is not None:
        report = stage_candidate_configs(raw, args.stage_root)
    else:
        configs = {a: render_arm(raw, a) for a in ARMS}
        report = {
            "classification": "S_V7_M02_CANDIDATE_CONFIG_SOURCE_REVIEW_ONLY",
            "real_world_starts": 0, "science_go": False,
            "configs_sha256": {a: sha256(x) for a, x in configs.items()},
        }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
