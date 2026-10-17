"""Read-only R shape gate for four still-unqualified M0.2 tick-chord arms.

The qualified new-JAR BASE_ON config is an *identity reference*, not an
execution permit. A SHAM config may have identical bytes, but its physical
qualification cannot be inherited. Never imports S's producer or starts a
World, native client, Java or provider request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PAPER_SHA256 = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
PLUGIN_SHA256 = "a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f"
BASE_CONFIG_SHA256 = "939c2da60ed4ce2f5afb5609c1f784886e3b021104c28a83658c17b744159b16"
SERVER_PROPERTIES_SHA256 = "11aaf903bae3d92f3b667f464f301a513bee559f04acc33d722c7a2e966d03ae"
BASE_GRANT = "USER_M02_V7_TICK_CHORD_BASE_ON_20261016_ONCE"
OLD_GRANT = "USER_M02_PAPER_QUALIFICATION_20261015_THIRD_ONCE"
CONSUMED_GRANTS = frozenset((BASE_GRANT, OLD_GRANT))
UNQUALIFIED_ARMS = {
    "SHAM_ON": (1, 1),
    "BASAL_ZERO": (0, 1),
    "WALK_ZERO": (1, 0),
    "BOTH_ZERO": (0, 0),
}
CLASS = "R_M02_V7_REMAINING_ARM_CONFIG_SHAPE_ONLY_NOT_QUALIFIED"
BASAL_RULE = (
    "  BASAL: {unit: tick, standard: 0.001, multiplier: 1.0, "
    "additional: 0.0, enabled: true}"
)
WALK_RULE = (
    "  WALK: {unit: block, standard: 0.01, multiplier: 1.0, "
    "additional: 0.0, enabled: true}"
)


class ProfileRejected(ValueError):
    """Candidate differs from the only registered BASE_ON identity/delta."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileRejected(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_base(base: bytes) -> str:
    need(type(base) is bytes and 0 < len(base) <= 8192,
         "missing or oversized BASE_ON config bytes")
    need(digest(base) == BASE_CONFIG_SHA256,
         "BASE_ON reference is not the R-qualified original identity")
    try:
        text = base.decode("utf-8")
    except UnicodeError as exc:
        raise ProfileRejected("BASE_ON config not UTF-8") from exc
    need(
        text.count(BASAL_RULE) == 1
        and text.count(WALK_RULE) == 1
        and text.count("dev-enabled: true") == 1
        and text.count("s50-tick-meter-dev: true") == 1
        and "dev-enabled: false" not in text,
        "BASE_ON witness is not a controlled new tick-chord profile",
    )
    return text


def expected_candidate(base: bytes, arm: str) -> bytes:
    """Compute two registered multipliers independently of S's config code."""
    original = pinned_base(base)
    need(arm in UNQUALIFIED_ARMS, "not one of the four unqualified profiles")
    basal, walk = UNQUALIFIED_ARMS[arm]
    expected = original.replace(
        BASAL_RULE, BASAL_RULE.replace("multiplier: 1.0",
                                      f"multiplier: {basal:.1f}"), 1,
    ).replace(
        WALK_RULE, WALK_RULE.replace("multiplier: 1.0",
                                    f"multiplier: {walk:.1f}"), 1,
    )
    return expected.encode("utf-8")


def review_config(base: bytes, candidate: bytes, *, arm: str,
                  plugin_sha256: str, paper_sha256: str,
                  server_properties_sha256: str) -> dict[str, Any]:
    """Only validate candidate bytes; no source authentication or grant."""
    expected = expected_candidate(base, arm)
    need(type(candidate) is bytes and 0 < len(candidate) <= 8192,
         "absent/oversize intervention configuration")
    need(candidate == expected,
         "foreign config: changed nonfactor bytes or wrong two-factor arm")
    need(plugin_sha256 == PLUGIN_SHA256
         and paper_sha256 == PAPER_SHA256
         and server_properties_sha256 == SERVER_PROPERTIES_SHA256,
         "unregistered plugin/Paper/server property identity")
    basal, walk = UNQUALIFIED_ARMS[arm]
    return {
        "classification": CLASS,
        "arm": arm,
        "reference_base_on_config_sha256": BASE_CONFIG_SHA256,
        "candidate_config_sha256": digest(candidate),
        "candidate_plugin_sha256": PLUGIN_SHA256,
        "candidate_paper_sha256": PAPER_SHA256,
        "candidate_server_properties_sha256": SERVER_PROPERTIES_SHA256,
        "basal_multiplier": basal,
        "walk_multiplier": walk,
        "expected_basal_setter_input_per_player_tick": 0.001 * basal,
        "expected_walk_setter_input_per_observed_tick_chord_block": 0.01 * walk,
        "identical_config_to_base_on": candidate == base,
        "identical_config_confers_separate_world_qualification": False,
        "caller_supplied_bytes_independently_authenticated": False,
        "original_host_stop_attested": False,
        "fresh_qual_grant_issued": False,
        "physical_world_launch_authorized": False,
        "candidate_arm_engineering_qualified": False,
        "other_arms_engineering_qualified": False,
        "v7_science_trials_credited": 0,
        "science_go": False,
        "production_go": False,
    }


def read_source(path: Path) -> bytes:
    need(path.is_absolute() and path.is_file() and not path.is_symlink()
         and all(not parent.is_symlink() for parent in path.parents),
         "noncanonical, missing or aliased local config source")
    need(0 < path.stat().st_size <= 8192, "unbounded/empty config file")
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config-original", required=True, type=Path)
    parser.add_argument("--candidate-config", required=True, type=Path)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--server-properties-sha256", required=True)
    args = parser.parse_args()
    try:
        result = review_config(
            read_source(args.base_config_original), read_source(args.candidate_config),
            arm=args.arm, plugin_sha256=args.plugin_sha256,
            paper_sha256=args.paper_sha256,
            server_properties_sha256=args.server_properties_sha256,
        )
        status = 0
    except (ProfileRejected, OSError, UnicodeError, ValueError) as exc:
        result = {
            "classification": "R_M02_V7_REMAINING_ARM_CONFIG_REJECTED",
            "reason": f"{type(exc).__name__}: {exc}",
            "physical_world_launch_authorized": False,
            "candidate_arm_engineering_qualified": False,
            "science_go": False,
            "production_go": False,
        }
        status = 2
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
