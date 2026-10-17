"""Offline R preworld asset identity check for a NEW, separate M0.2 Paper World.

This NEVER launches Paper/Node, grants new QUALIFICATION, mutates World files,
or promotes a DEV result, the protected Mojang Golden, or scientific claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

PROFILE_FILE = Path(__file__).with_name("m02_paper_preworld_profile.json")
PAPER_HEAD = "52d9bbf1b4ee2e8ff810d213e36d0caf347652ee"
M_HEAD = "4c2f549c6b9ed3fbe2ee04230526ac5577da8feb"
ASSET_FILES = {
    "paper-1.21.8.jar",
    "relay-metabolism-paper-dev.jar",
    "config.yml",
    "server.properties",
}


class Blocked(ValueError):
    """No physical Paper admission when a source/pin cannot be validated."""


def require(value: bool, explanation: str) -> None:
    if not value:
        raise Blocked(explanation)


def parse_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        require(k not in obj, "duplicate manifest key")
        obj[k] = v
    return obj


def read_exact(path: Path, maximum: int) -> bytes:
    require(path.is_file() and not path.is_symlink()
            and stat.S_ISREG(path.lstat().st_mode), "missing/unsafe source asset")
    before = path.stat()
    require(0 < before.st_size <= maximum, "empty or oversized source asset")
    raw = path.read_bytes()
    after = path.stat()
    require(len(raw) == before.st_size and
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "source asset changed during read")
    return raw


def load_manifest(path: Path = PROFILE_FILE) -> dict[str, Any]:
    try:
        raw = read_exact(path, 64 * 1024)
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=parse_unique,
                         parse_constant=lambda v: (_ for _ in ()).throw(
                             Blocked("nonfinite manifest scalar")))
    except (UnicodeError, ValueError, OSError) as exc:
        raise Blocked("invalid Paper preworld manifest") from exc
    return validate_profile(obj)


def validate_profile(p: Any) -> dict[str, Any]:
    require(type(p) is dict and set(p) == {
        "schema", "qualification_status", "science_status", "production_status",
        "minecraft_version", "server_flavor", "source_s_head", "reference_m_head",
        "physical_dev_source_artifact_id", "physical_dev_source_run_id",
        "physical_dev_r_archive_artifact_id", "source_classification",
        "required_jvm_major", "required_node_major", "owner_player",
        "world_mode", "vanilla_golden_replacement_allowed",
        "virtual_m0_ledger_allowed", "cognition_cost_enabled",
        "rates_calibration", "basal_exhaustion_per_world_tick_candidate",
        "walk_exhaustion_per_observed_block_candidate", "expected_assets_sha256",
    }, "unknown/missing Paper preworld profile fields")
    require(
        p["schema"] == "RSEE_M02_PAPER_PREWORLD_PROFILE_V1"
        and p["qualification_status"] == "NOT_QUALIFIED"
        and p["science_status"] == "NOT_RUN"
        and p["production_status"] == "NO_GO"
        and p["minecraft_version"] == "1.21.8"
        and p["server_flavor"] == "Paper"
        and p["source_s_head"] == PAPER_HEAD
        and p["reference_m_head"] == M_HEAD
        and type(p["physical_dev_source_artifact_id"]) is int
        and p["physical_dev_source_artifact_id"] == 11942793326
        and type(p["physical_dev_source_run_id"]) is int
        and p["physical_dev_source_run_id"] == 38668633950
        and type(p["physical_dev_r_archive_artifact_id"]) is int
        and p["physical_dev_r_archive_artifact_id"] == 11954211513
        and p["source_classification"] ==
        "RSEE_M02_PAPER_DEV_ORIGINAL_SOURCE_REVIEW_ONLY"
        and type(p["required_jvm_major"]) is int
        and p["required_jvm_major"] == 21
        and type(p["required_node_major"]) is int
        and p["required_node_major"] == 22
        and p["owner_player"] == "RelaySelf"
        and p["world_mode"] == "NEW_SEPARATE_ISOLATED_PAPER_CLONE_ONLY"
        and p["vanilla_golden_replacement_allowed"] is False
        and p["virtual_m0_ledger_allowed"] is False
        and p["cognition_cost_enabled"] is False
        and p["rates_calibration"] == "candidate_uncalibrated"
        and type(p["basal_exhaustion_per_world_tick_candidate"]) in (int, float)
        and p["basal_exhaustion_per_world_tick_candidate"] == 0.001
        and type(p["walk_exhaustion_per_observed_block_candidate"]) in (int, float)
        and p["walk_exhaustion_per_observed_block_candidate"] == 0.01,
        "Paper preworld scope/source/version/permission mismatch")
    hashes = p["expected_assets_sha256"]
    require(type(hashes) is dict and set(hashes) == ASSET_FILES
            and all(type(h) is str and re.fullmatch("[0-9a-f]{64}", h)
                    for h in hashes.values()), "missing/invalid pinned source hashes")
    return p


def inspect(asset_root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    p = validate_profile(profile) if profile is not None else load_manifest()
    require(asset_root.is_absolute() and asset_root.is_dir()
            and not asset_root.is_symlink()
            and all(not parent.is_symlink() for parent in asset_root.parents),
            "assets must be isolated absolute regular root")
    require({x.name for x in asset_root.iterdir()} == ASSET_FILES,
            "assets must be exact four-file set in dedicated directory")
    verified: dict[str, str] = {}
    for name, expected in sorted(p["expected_assets_sha256"].items()):
        max_bytes = 200_000_000 if name.endswith(".jar") else 65_536
        raw = read_exact(asset_root / name, max_bytes)
        actual = hashlib.sha256(raw).hexdigest()
        require(actual == expected, "Paper source asset digest mismatch: " + name)
        verified[name] = actual
    require(b"dev-enabled: true" in read_exact(asset_root / "config.yml", 65_536)
            and b"target-player: RelaySelf" in read_exact(
                asset_root / "config.yml", 65_536),
            "Paper plugin source config not enabled for owned test player")
    require(b"online-mode=false" in read_exact(
        asset_root / "server.properties", 65_536), "World properties not loopback test")
    require(all(hashlib.sha256(read_exact(asset_root / n,
                                         200_000_000 if n.endswith(".jar") else 65_536
                                         )).hexdigest() == sha
                for n, sha in verified.items()),
            "Paper input assets changed before/after inspection")
    return {
        "classification": "M02_PAPER_ASSETS_PINNED_PREWORLD_REVIEW_ONLY",
        "source_manifest_version": p["schema"],
        "paper_jar_sha256": verified["paper-1.21.8.jar"],
        "plugin_jar_sha256": verified["relay-metabolism-paper-dev.jar"],
        "plugin_config_sha256": verified["config.yml"],
        "server_properties_sha256": verified["server.properties"],
        "minecraft_version": p["minecraft_version"],
        "separate_from_vanilla_golden": True,
        "qualified": False,
        "science_go": False,
        "production_go": False,
        "new_physical_qualification_authorized": False,
        "physical_world_launches_by_review": 0,
        "source_artifact_historical_dev_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.asset_root is None:
            result = {
                "classification": "M02_PAPER_PREWORLD_ASSETS_UNCHECKED",
                "qualified": False, "science_go": False,
                "new_physical_qualification_authorized": False,
                "physical_world_launches_by_review": 0,
            }
        else:
            result = inspect(args.asset_root)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {
            "classification": "M02_PAPER_PREWORLD_BLOCKED",
            "reason": f"{type(exc).__name__}: {exc}",
            "qualified": False, "science_go": False,
            "new_physical_qualification_authorized": False,
            "physical_world_launches_by_review": 0,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 2 if result["classification"] == "M02_PAPER_PREWORLD_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
