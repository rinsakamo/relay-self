"""Independent R read-only BASAL + S50 tick-chord source gate, four arms only.

This validates source *shape* against the already registered exact new JAR
profile bytes. It never authenticates who produced the log or upgrades a
DEV source to an engineering qualification, even if all measurements match.
Only a separately approved new physical run + independent original-host
review may make that determination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.standard_env import m02_v7_remaining_profile_preflight as profile
from experiments.standard_env import s50_tick_chord_original_audit as motion
from experiments.standard_env import v7_m02_direct_basal_readback as basal

CLASS = "R_M02_V7_REMAINING_ARM_BASAL_WALK_ORIGINAL_SHAPE_REVIEW_ONLY"
FAIL = "R_M02_V7_REMAINING_ARM_ORIGINAL_SOURCE_FAILED_OR_UNDETERMINED"
MAX_PAPER = min(motion.__dict__.get("MAX_LOG_BYTES", 12 * 1024 * 1024),
                basal.MAX_LOG_BYTES)


class SourceRejected(ValueError):
    """Missing/foreign/replayed/tampered source; no engineering verdict."""


def require(ok: bool, why: str) -> None:
    if not ok:
        raise SourceRejected(why)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_original(path: Path, *, limit: int) -> bytes:
    require(isinstance(path, Path) and path.is_absolute()
            and path.is_file() and not path.is_symlink()
            and all(not parent.is_symlink() for parent in path.parents),
            "missing/relative/aliased original")
    require(0 < path.stat().st_size <= limit, "empty/oversized original")
    raw = path.read_bytes()
    require(0 < len(raw) <= limit, "original size changed")
    return raw


def review_source(
    base: bytes, candidate: bytes, paper_raw: bytes,
    *, arm: str, action_marker: str, expected_paper_sha256: str,
    plugin_sha256: str, paper_binary_sha256: str,
    server_properties_sha256: str,
) -> dict[str, Any]:
    """Recalculate sources; a caller-matching digest is NOT provenance proof."""
    admitted = profile.review_config(
        base, candidate, arm=arm,
        plugin_sha256=plugin_sha256,
        paper_sha256=paper_binary_sha256,
        server_properties_sha256=server_properties_sha256,
    )
    require(type(paper_raw) is bytes and 0 < len(paper_raw) <= MAX_PAPER,
            "absent/unbounded Paper original")
    require(type(expected_paper_sha256) is str
            and re.fullmatch(r"[0-9a-f]{64}", expected_paper_sha256) is not None
            and sha(paper_raw) == expected_paper_sha256,
            "missing/changed original Paper SHA256 comparator")
    require(type(action_marker) is str
            and re.fullmatch(r"[A-Za-z0-9_-]{8,256}", action_marker) is not None,
            "missing or unsafe Action/session marker")
    # These are separate R reader implementations, NOT S producer reports.
    chord = motion.review_paper_source(paper_raw, arm, action_marker)
    direct = basal.review_original_server_log(paper_raw, arm)
    expected_basal = admitted["expected_basal_setter_input_per_player_tick"]
    expected_walk = admitted["expected_walk_setter_input_per_observed_tick_chord_block"]
    require(abs(direct["configured_basal_request_per_tick"] - expected_basal) < 1e-10,
            "registered config/BASAL native writer disagreement")
    require(abs(chord["source_walk_exhaustion_per_chord_block"] - expected_walk) < 1e-10,
            "registered config/WALK native writer disagreement")
    require(direct["first200_source_player_callbacks"] == 200
            and chord["bounded_quiet_window_observed"] is True
            and chord["event_native_double_billing"] is False
            and chord["source_tick_chord_blocks_lower_bound"] > 0,
            "missing bounded native motion or BASAL source")
    return {
        "classification": CLASS,
        "arm": arm,
        "candidate_config_sha256": admitted["candidate_config_sha256"],
        "plugin_sha256_reference": plugin_sha256,
        "paper_binary_sha256_reference": paper_binary_sha256,
        "paper_log_sha256_comparator": expected_paper_sha256,
        "action_marker": action_marker,
        "paper_world_uuid_as_logged": chord["world"],
        "source_native_tick_chord_rows": chord["native_tick_rows"],
        "observed_tick_chord_lower_bound_blocks":
            chord["source_tick_chord_blocks_lower_bound"],
        "observed_walk_native_setter_input":
            chord["walk_native_exhaustion_setter_input"],
        "expected_walk_setter_input_per_chord_block": expected_walk,
        "source_player_basal_write_rows": direct["source_writes_recorded"],
        "source_basal_requested_first200":
            direct["direct_source_requested_basal_cumulative_first200"],
        "expected_basal_setter_input_per_player_tick": expected_basal,
        "event_double_billed": False,
        "bounded_quiet_window": True,
        "zero_rate_legitimate_if_observed_distance_positive": expected_walk == 0,
        "producer_authenticated_by_this_review": False,
        "paper_world_tick_shared_action_bracket_attested": False,
        "native_terminal_action_or_eat_attested": False,
        "native_pid_or_port_stop_attested": False,
        "continuous_subtick_path_attested": False,
        "net_native_hunger_debit_attested": False,
        "fresh_qualification_grant_issued": False,
        "physical_world_launch_authorized": False,
        "candidate_arm_engineering_qualified": False,
        "other_arms_engineering_qualified": False,
        "v7_science_trials_credited": 0,
        "science_go": False,
        "production_go": False,
    }


def review_paths(
    base_path: Path, candidate_path: Path, paper_path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    original = (
        read_original(base_path, limit=8192),
        read_original(candidate_path, limit=8192),
        read_original(paper_path, limit=MAX_PAPER),
    )
    result = review_source(
        *original, **kwargs,
    )
    require(all(read_original(path, limit=cap) == original[idx]
                for idx, (path, cap) in enumerate((
                    (base_path, 8192), (candidate_path, 8192),
                    (paper_path, MAX_PAPER),
                ))), "original bytes changed during read-only R inspection")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-config-original", type=Path, required=True)
    p.add_argument("--candidate-config", type=Path, required=True)
    p.add_argument("--paper-original", type=Path, required=True)
    p.add_argument("--paper-original-sha256", required=True)
    p.add_argument("--arm", required=True)
    p.add_argument("--action-marker", required=True)
    p.add_argument("--plugin-sha256", required=True)
    p.add_argument("--paper-binary-sha256", required=True)
    p.add_argument("--server-properties-sha256", required=True)
    a = p.parse_args()
    try:
        result = review_paths(
            a.base_config_original, a.candidate_config, a.paper_original,
            arm=a.arm, action_marker=a.action_marker,
            expected_paper_sha256=a.paper_original_sha256,
            plugin_sha256=a.plugin_sha256, paper_binary_sha256=a.paper_binary_sha256,
            server_properties_sha256=a.server_properties_sha256,
        )
        status = 0
    except (SourceRejected, profile.ProfileRejected, motion.InvalidSource,
            basal.SourceRejected, ValueError, TypeError, OSError, KeyError) as exc:
        result = {
            "classification": FAIL,
            "reason": f"{type(exc).__name__}: {exc}",
            "candidate_arm_engineering_qualified": False,
            "physical_world_launch_authorized": False,
            "science_go": False,
            "production_go": False,
        }
        status = 2
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
