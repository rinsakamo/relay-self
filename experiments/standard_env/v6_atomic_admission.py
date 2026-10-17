"""R #575: immutable V6 atomic-food source and staged-World delta review.

Only read stopped candidate bytes and evaluate reported values. No datapack
installation, Minecraft process, command invocation, original runtime receipt,
World-time parity, independently authenticated single use or authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.v6_packet_provenance import _safe
from experiments.standard_env.world_binding import _world_files

S_ATOMIC_SOURCE_HEAD = "37f9365d3d16c9bda440ca9a9c8a10be6a32f1fc"
S_ATOMIC_SOURCE_BLOB = "ea4f4123e9d43a774f736b519743616115b78ea2"
PACK_DIR = "datapacks/relayself_v6_atomic"
OBJECTIVE = "rs_v6_tick"
MAX_SCORE = 2**31 - 1

SOURCE_INSTALL = (
    f"scoreboard objectives add {OBJECTIVE} dummy",
    f"scoreboard players add #attempt {OBJECTIVE} 0",
    f"scoreboard players add #before {OBJECTIVE} 0",
    f"scoreboard players add #after {OBJECTIVE} 0",
    f"scoreboard players add #ok {OBJECTIVE} 0",
)
ONCE = f"execute if score #attempt {OBJECTIVE} matches 1 run "
SOURCE_FUNCTION = (
    f"scoreboard players add #attempt {OBJECTIVE} 1",
    ONCE + f"scoreboard players set #before {OBJECTIVE} -1",
    ONCE + f"scoreboard players set #after {OBJECTIVE} -1",
    ONCE + f"scoreboard players set #ok {OBJECTIVE} 0",
    ONCE + f"execute store result score #before {OBJECTIVE} run time query gametime",
    ONCE + "execute store success score #ok "
    f'{OBJECTIVE} run summon minecraft:item ~2.5 ~0.2 ~ '
    '{Item:{id:"minecraft:rotten_flesh",count:1}}',
    ONCE + f"execute store result score #after {OBJECTIVE} run time query gametime",
    ONCE + "say RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED",
    f"execute if score #attempt {OBJECTIVE} matches 2.. "
    "run say RELAYSELF_V6_REPEAT_BLOCKED_SOURCE_NOT_ADMITTED",
)


class AtomicReviewRejected(ValueError):
    """Exact source identity or proposed run evidence fails closed."""


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise AtomicReviewRejected(reason)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def expected_pack_bytes() -> dict[str, bytes]:
    """R-owned independent re-expression of the frozen S candidate source."""
    meta = {"pack": {
        "pack_format": 81,
        "description": "RelaySelf V6 atomic food age PRE-ADMISSION; NO LIVE GRANT",
    }}
    return {
        f"{PACK_DIR}/pack.mcmeta": (
            json.dumps(meta, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
        f"{PACK_DIR}/data/relayself_v6/function/install.mcfunction": (
            "\n".join(SOURCE_INSTALL) + "\n"
        ).encode("utf-8"),
        f"{PACK_DIR}/data/relayself_v6/function/atomic_food.mcfunction": (
            "\n".join(SOURCE_FUNCTION) + "\n"
        ).encode("utf-8"),
    }


def review_s_atomic_source(checkout: Path) -> dict[str, Any]:
    """Require a clean immutable S candidate, rather than a mutable S branch."""
    root = _safe(checkout, directory=True)
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=8, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=8, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AtomicReviewRejected("S source checkout cannot be bound") from exc
    _need(head == S_ATOMIC_SOURCE_HEAD and not status,
          "candidate S atomic source is dirty or not at pinned HEAD")
    f = _safe(root / "adapters/mineflayer/v6_atomic_fixture.py", directory=False)
    raw = f.read_bytes()
    _need(len(raw) <= 200_000 and _git_blob(raw) == S_ATOMIC_SOURCE_BLOB,
          "S candidate generator source bytes differ")
    pack = expected_pack_bytes()
    _need(len(pack) == 3 and len(set(pack)) == 3,
          "R frozen expected function manifest malformed")
    return {
        "classification": "RSEE_V6_ATOMIC_S_SOURCE_PINNED_REVIEW_ONLY",
        "source_head": head,
        "source_git_blob": _git_blob(raw),
        "expected_staged_pack_files": {
            path: hashlib.sha256(content).hexdigest()
            for path, content in sorted(pack.items())
        },
        "installed_or_loaded": False,
        "server_function_executed": False,
        "single_use_guard_present_source_only": True,
        "independent_single_use_verified": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def review_staged_index(
    original_index: tuple[tuple[str, int, str], ...],
    candidate_index: tuple[tuple[str, int, str], ...],
) -> dict[str, Any]:
    """Exact addition of three staged pack files, no Golden changes allowed.

    Indices here may be synthetic. Only review_staged_clone separately binds
    original actual bytes against a qualified Golden #588 owner.
    """
    _need(type(original_index) is tuple and type(candidate_index) is tuple
          and bool(original_index), "invalid World file index types")
    gold = {x[0]: x for x in original_index}
    staged = {x[0]: x for x in candidate_index}
    _need(len(gold) == len(original_index)
          and len(staged) == len(candidate_index),
          "duplicate indexed World path")
    _need(set(gold) <= set(staged), "original stopped World file removed")
    _need(all(staged[k] == row for k, row in gold.items()),
          "qualified stopped World file altered")
    pack = expected_pack_bytes()
    _need(set(staged) - set(gold) == set(pack),
          "unexpected missing/extra staged World path")
    for rel, expected in pack.items():
        _need(
            staged[rel] == (rel, len(expected), hashlib.sha256(expected).hexdigest()),
            "added data pack differs from frozen candidate",
        )
    return {
        "classification": "RSEE_V6_ATOMIC_STAGED_DELTA_SHAPE_REVIEW_ONLY",
        "original_file_count": len(gold),
        "added_pack_file_count": len(pack),
        "changed_original_bytes": False,
        "candidate_pack_file_sha256": {
            k: staged[k][2] for k in sorted(pack)
        },
        "staged_clone_world_started": "NOT_ATTESTED",
        "server_function_loaded": False,
        "single_use_guard_present_source_only": True,
        "independent_single_use_verified": False,
        "exact_summon_effect_tick_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def review_staged_clone(
    *, jar: Path, golden: Path, manifest: Path, initial_evidence: Path,
    staged_clone: Path, pinned_s_checkout: Path,
) -> dict[str, Any]:
    """Independent at-read-time Golden + instrumented clone source gate."""
    review_s_atomic_source(pinned_s_checkout)
    for source in (jar, golden, manifest, initial_evidence, staged_clone):
        _safe(source, directory=source in (golden, staged_clone))
    _need(staged_clone != golden, "staged clone aliases Golden")
    qualified = verify_qualified_world(jar, golden, manifest, initial_evidence)
    result = review_staged_index(qualified.files, _world_files(staged_clone))
    return {
        **result,
        "classification": "RSEE_V6_ATOMIC_STAGED_STOPPED_BYTES_REVIEW_ONLY",
        "qualified_original_world_manifest_sha256": qualified.manifest_sha256,
        "s_fixture_source_head": S_ATOMIC_SOURCE_HEAD,
        "actual_staged_clone_bytes_read": True,
        "live_world_start_matched": False,
        "prelaunch_stopped_state_attested": False,
        "server_function_loaded": False,
        "exact_summon_effect_tick_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def review_score_claim(
    value: dict[str, Any], *, expected_function_sha256: str,
) -> dict[str, Any]:
    """Not an original server receipt. Never promote caller-supplied values."""
    _need(type(value) is dict and set(value) == {
        "source_function_sha256", "before_gametime", "after_gametime",
        "summon_success", "claimed_invocations", "m0_tick_at_opportunity",
    }, "reported scoreboard fields incomplete or ambiguous")
    func = expected_pack_bytes()[
        f"{PACK_DIR}/data/relayself_v6/function/atomic_food.mcfunction"
    ]
    sha = hashlib.sha256(func).hexdigest()
    _need(
        type(expected_function_sha256) is str
        and expected_function_sha256 == sha
        and type(value["source_function_sha256"]) is str
        and value["source_function_sha256"] == sha,
        "scoreboard source not the pinned exact function",
    )
    before, after, success = (
        value["before_gametime"], value["after_gametime"],
        value["summon_success"],
    )
    _need(type(before) is int and type(after) is int
          and 0 <= before == after <= MAX_SCORE,
          "World gametime unequal/out of safe scoreboard int32 range")
    _need(type(success) is int and success == 1,
          "unearned/ambiguous item-summon command success")
    _need(type(value["claimed_invocations"]) is int
          and value["claimed_invocations"] == 1,
          "repeated function overwrote the scoreboard")
    _need(type(value["m0_tick_at_opportunity"]) is int
          and value["m0_tick_at_opportunity"] == 11,
          "M0 decision clock differs from preregistered opportunity")
    return {
        "classification": "RSEE_V6_ATOMIC_REPORTED_SCORE_CLAIM_REVIEW_ONLY",
        "claimed_gametime_tick": before,
        "m0_decision_tick": 11,
        "function_sha256": sha,
        "claimed_invocations": 1,
        "single_use_guard_present_source_only": True,
        "original_server_command_bytes_verified": False,
        "function_loaded_by_server_attested": False,
        "independent_single_use_verified": False,
        "true_world_effect_tick_attested": False,
        "world_start_matched": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_V6_ATOMIC_SOURCE_ONLY_PLAN",
        "s_fixture_pinned_head": S_ATOMIC_SOURCE_HEAD,
        "golden_checked": False,
        "staged_clone_checked": False,
        "actual_server_originals_read": False,
        "server_function_single_use": "GUARDED_IN_SOURCE_ONLY_UNVERIFIED_RUNTIME",
        "server_function_parse_verified_1_21_8": False,
        "matched_elapsed_world_time": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s-checkout", type=Path)
    parser.add_argument("--jar", type=Path)
    parser.add_argument("--golden", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--initial-evidence", type=Path)
    parser.add_argument("--staged-clone", type=Path)
    args = parser.parse_args(argv)
    try:
        world_args = (args.jar, args.golden, args.manifest,
                      args.initial_evidence, args.staged_clone)
        if any(x is not None for x in world_args):
            _need(args.s_checkout is not None
                  and all(x is not None for x in world_args),
                  "source and all five Golden+clone paths required")
            result = review_staged_clone(
                pinned_s_checkout=args.s_checkout, jar=args.jar,
                golden=args.golden, manifest=args.manifest,
                initial_evidence=args.initial_evidence,
                staged_clone=args.staged_clone,
            )
        elif args.s_checkout is not None:
            result = review_s_atomic_source(args.s_checkout)
        else:
            result = plan()
    except (OSError, TypeError, ValueError, UnicodeError) as exc:
        print(json.dumps({
            "classification": "RSEE_V6_ATOMIC_SOURCE_REVIEW_BLOCKED",
            "reason": type(exc).__name__ + ": " + str(exc),
            "physical_execution_authorized": False, "science_g3": "NO_GO",
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
