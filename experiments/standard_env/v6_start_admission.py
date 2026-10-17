"""R #575 independent two-pack V6 trial-start/atomic-food SOURCE-only admission.

Pins an immutable S start producer separately from frozen S atomic V2,
checks exactly six candidate staged datapack files, and refuses to
convert arithmetic claims into server-origin World-time evidence.
No server, Java, Node, GPU, network, World write or grant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.v6_atomic_admission import (
    MAX_SCORE,
    S_ATOMIC_SOURCE_HEAD,
    _git_blob,
    expected_pack_bytes,
    review_s_atomic_source,
)
from experiments.standard_env.v6_packet_provenance import _safe
from experiments.standard_env.world_binding import _world_files

S_START_SOURCE_HEAD = "2aaff0b921bcbd47a61d563b52d502596f896924"
S_START_SOURCE_BLOB = "d1510006dc370d217afe6d4988662ca0f36c5522"
START_PACK_DIR = "datapacks/relayself_v6_start_v1"
START_OBJECTIVE = "rs_v6_tick"
START_SLOTS = ("WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D")
START_INSTALL = (
    f"scoreboard players add #start_attempt {START_OBJECTIVE} 0",
    f"scoreboard players add #start_gametime {START_OBJECTIVE} 0",
)
START_ONCE = (
    f"execute if score #start_attempt {START_OBJECTIVE} matches 1 run "
)


class StartReviewRejected(ValueError):
    """Unqualified source, clone, or source-shaped temporal claim."""


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise StartReviewRejected(reason)


def _identity(slot: str, nonce: str) -> None:
    _need(type(slot) is str and slot in START_SLOTS, "unregistered World-start slot")
    _need(type(nonce) is str and re.fullmatch(r"[0-9a-f]{32}", nonce) is not None,
          "invalid/noncanonical session correlation nonce")


def expected_start_pack_bytes(slot: str, nonce: str) -> dict[str, bytes]:
    """Independently express frozen S source; nonce only correlates, never authenticates."""
    _identity(slot, nonce)
    meta = {"pack": {
        "pack_format": 81,
        "description": "RelaySelf V6 server trial-start clock source; NO LIVE GRANT",
    }}
    function = (
        f"scoreboard players add #start_attempt {START_OBJECTIVE} 1",
        START_ONCE + f"scoreboard players set #start_gametime {START_OBJECTIVE} -1",
        START_ONCE + "execute store result score #start_gametime "
        f"{START_OBJECTIVE} run time query gametime",
        START_ONCE + f"say RELAYSELF_V6_TRIAL_START_{slot}_{nonce}_NOT_ADMITTED",
        f"execute if score #start_attempt {START_OBJECTIVE} matches 2.. "
        f"run say RELAYSELF_V6_TRIAL_START_REPLAY_BLOCKED_{slot}_{nonce}",
    )
    return {
        f"{START_PACK_DIR}/pack.mcmeta": (
            json.dumps(meta, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
        f"{START_PACK_DIR}/data/relayself_v6_start/function/install.mcfunction": (
            "\n".join(START_INSTALL) + "\n"
        ).encode("utf-8"),
        f"{START_PACK_DIR}/data/relayself_v6_start/function/start_trial.mcfunction": (
            "\n".join(function) + "\n"
        ).encode("utf-8"),
    }


def expected_combined_pack_bytes(slot: str, nonce: str) -> dict[str, bytes]:
    """Food V2 and start V1 are separate immutable 3-file packs, not Golden."""
    food = expected_pack_bytes()
    start = expected_start_pack_bytes(slot, nonce)
    _need(len(food) == len(start) == 3 and not set(food).intersection(start),
          "expected pack path collision/invalid cardinality")
    return {**food, **start}


def review_s_start_source(checkout: Path, *, slot: str, nonce: str) -> dict[str, Any]:
    """Read-only Git HEAD/blob pin and independently constructed byte manifest."""
    _identity(slot, nonce)
    root = _safe(checkout, directory=True)
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise StartReviewRejected("S start checkout HEAD/cleanliness unavailable") from exc
    _need(head == S_START_SOURCE_HEAD and not dirty,
          "S start checkout does not match exact clean producer")
    f = _safe(root / "adapters/mineflayer/v6_start_marker.py", directory=False)
    raw = f.read_bytes()
    _need(len(raw) <= 200_000 and _git_blob(raw) == S_START_SOURCE_BLOB,
          "S start producer blob mismatch")
    pack = expected_combined_pack_bytes(slot, nonce)
    return {
        "classification": "RSEE_V6_START_S_SOURCE_PINNED_REVIEW_ONLY",
        "start_source_head": head, "start_source_git_blob": _git_blob(raw),
        "food_source_head": S_ATOMIC_SOURCE_HEAD,
        "world_start_slot": slot, "session_correlation_nonce": nonce,
        "nonce_authenticates_origin": False,
        "expected_staged_pack_files": {
            p: hashlib.sha256(b).hexdigest() for p, b in sorted(pack.items())
        },
        "source_guard_only": True, "actual_loaded_functions_attested": False,
        "actual_world_start_attested": False,
        "original_server_console_bytes_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def review_staged_index(
    original: tuple[tuple[str, int, str], ...],
    staged: tuple[tuple[str, int, str], ...],
    *, slot: str, nonce: str,
) -> dict[str, Any]:
    """Synthetic index agreement proves shape only; host originals still required."""
    pack = expected_combined_pack_bytes(slot, nonce)
    _need(type(original) is tuple and type(staged) is tuple and bool(original),
          "missing or invalid original/staged World index")
    for index in (original, staged):
        _need(all(
            type(row) is tuple and len(row) == 3
            and type(row[0]) is str and bool(row[0])
            and type(row[1]) is int and row[1] >= 0
            and type(row[2]) is str and re.fullmatch(r"[0-9a-f]{64}", row[2]) is not None
            for row in index
        ), "malformed index row")
        _need(len({r[0] for r in index}) == len(index), "duplicate World file path")
    gold = {r[0]: r for r in original}
    candidate = {r[0]: r for r in staged}
    _need(all(candidate.get(k) == v for k, v in gold.items()),
          "Golden file missing/changed in staged clone")
    _need(set(candidate) - set(gold) == set(pack),
          "candidate must add exactly both versioned datapacks")
    for path, raw in pack.items():
        _need(candidate[path] == (path, len(raw), hashlib.sha256(raw).hexdigest()),
              "staged datapack bytes differ from immutable source")
    return {
        "classification": "RSEE_V6_TWO_PACK_STAGED_DELTA_REVIEW_ONLY",
        "original_file_count": len(gold),
        "added_pack_file_count": 6,
        "world_start_slot": slot, "session_correlation_nonce": nonce,
        "changed_original_bytes": False,
        "candidate_pack_sha256": {
            p: candidate[p][2] for p in sorted(pack)
        },
        "original_world_bytes_independently_read": False,
        "server_function_loaded": False,
        "first_l0_probe_bound_to_server_start": False,
        "native_elapsed_world_ticks_attested": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def review_staged_clone(
    *, jar: Path, golden: Path, manifest: Path, initial_evidence: Path,
    staged_clone: Path, s_start_checkout: Path, s_food_checkout: Path,
    slot: str, nonce: str,
) -> dict[str, Any]:
    """On-host read-only stopped-byte gate, never an actual World launch."""
    review_s_start_source(s_start_checkout, slot=slot, nonce=nonce)
    review_s_atomic_source(s_food_checkout)
    for p in (jar, golden, manifest, initial_evidence, staged_clone):
        _safe(p, directory=p in (golden, staged_clone))
    _need(staged_clone != golden, "candidate clone aliases stopped Golden")
    binding = verify_qualified_world(jar, golden, manifest, initial_evidence)
    checked = review_staged_index(
        binding.files, _world_files(staged_clone), slot=slot, nonce=nonce,
    )
    return {
        **checked, "classification": "RSEE_V6_TWO_PACK_STOPPED_BYTES_REVIEW_ONLY",
        "golden_manifest_sha256": binding.manifest_sha256,
        "original_world_bytes_independently_read": True,
        "candidate_clone_bytes_read": True,
        "live_server_started": False,
        "real_world_elapsed_parity_verified": False,
    }


def review_elapsed_claim(
    *, slot: str, nonce: str, session_id: str,
    first_probe_seq: int, first_probe_request_id: str,
    reported_start_attempt: int, reported_start_gametime: int,
    reported_food_attempt: int, reported_food_before: int,
    reported_food_after: int, reported_summon_success: int,
    m0_tick_at_food: int,
) -> dict[str, Any]:
    """Arithmetic on caller reports ONLY; not server stdout or start/L0 simultaneity."""
    _identity(slot, nonce)
    _need(type(session_id) is str and bool(session_id)
          and type(first_probe_seq) is int and first_probe_seq >= 0
          and type(first_probe_request_id) is str and bool(first_probe_request_id),
          "no correlation identity or source-shaped first L0 reference")
    _need(type(reported_start_attempt) is int and reported_start_attempt == 1
          and type(reported_food_attempt) is int and reported_food_attempt == 1,
          "start/food attempts must both be one")
    _need(type(reported_start_gametime) is int
          and type(reported_food_before) is int
          and type(reported_food_after) is int
          and 0 <= reported_start_gametime <= reported_food_before
          == reported_food_after <= MAX_SCORE,
          "invalid/overflow/reversed reported server gametime")
    _need(type(reported_summon_success) is int and reported_summon_success == 1
          and type(m0_tick_at_food) is int and m0_tick_at_food == 11,
          "incorrect source-shaped food success or M0 decision clock")
    return {
        "classification": "RSEE_V6_ELAPSED_SERVER_TIME_CLAIM_REVIEW_ONLY",
        "world_start_slot": slot, "session_correlation_nonce": nonce,
        "session_id_claim": session_id,
        "first_l0_probe_seq_claim": first_probe_seq,
        "first_l0_request_id_claim": first_probe_request_id,
        "claimed_elapsed_world_ticks": reported_food_before - reported_start_gametime,
        "first_l0_and_server_start_same_tick": "NOT_ATTESTED",
        "source_originals_independently_verified": False,
        "server_command_effect_time_attested": False,
        "matched_12_arm_world_time_attested": False,
        "m0_tick_not_minecraft_tick": True,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def plan() -> dict[str, Any]:
    return {
        "classification": "RSEE_V6_TWO_PACK_START_SOURCE_ONLY_PLAN",
        "s_start_source_head": S_START_SOURCE_HEAD,
        "s_food_source_head": S_ATOMIC_SOURCE_HEAD,
        "expected_added_pack_files": 6,
        "staged_clone_read": False,
        "server_originals_read": False,
        "server_function_loaded": False,
        "native_world_start_and_food_effect_attested": False,
        "matched_12_arm_world_elapsed_ticks": False,
        "physical_execution_authorized": False, "science_g3": "NO_GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s-start-checkout", type=Path)
    parser.add_argument("--s-food-checkout", type=Path)
    parser.add_argument("--slot")
    parser.add_argument("--nonce")
    parser.add_argument("--jar", type=Path)
    parser.add_argument("--golden", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--initial-evidence", type=Path)
    parser.add_argument("--staged-clone", type=Path)
    args = parser.parse_args(argv)
    try:
        sources = (args.s_start_checkout, args.s_food_checkout)
        worlds = (args.jar, args.golden, args.manifest,
                  args.initial_evidence, args.staged_clone)
        if any(x is not None for x in (*sources, *worlds, args.slot, args.nonce)):
            _need(all(x is not None for x in (*sources, args.slot, args.nonce)),
                  "both exact S checkouts, slot and nonce required")
            if any(x is not None for x in worlds):
                _need(all(x is not None for x in worlds),
                      "all five World/clone original paths required")
                result = review_staged_clone(
                    s_start_checkout=args.s_start_checkout,
                    s_food_checkout=args.s_food_checkout,
                    slot=args.slot, nonce=args.nonce,
                    jar=args.jar, golden=args.golden, manifest=args.manifest,
                    initial_evidence=args.initial_evidence,
                    staged_clone=args.staged_clone,
                )
            else:
                result = review_s_start_source(
                    args.s_start_checkout, slot=args.slot, nonce=args.nonce,
                )
                review_s_atomic_source(args.s_food_checkout)
        else:
            result = plan()
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        print(json.dumps({
            "classification": "RSEE_V6_TWO_PACK_START_SOURCE_BLOCKED",
            "reason": type(exc).__name__ + ": " + str(exc),
            "physical_execution_authorized": False, "science_g3": "NO_GO",
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
