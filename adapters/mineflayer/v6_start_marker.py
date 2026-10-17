"""S #537 prospective one-shot server World-time trial-start marker.

Separate from the already R-pinned V6 atomic FOOD V2 bytes. This pure
producer never writes a pack or launches Minecraft. Caller-owned scoreboard
claims are not original command/readback evidence. R/V qualify any future
loaded producer, start-to-food elapsed ticks and first native L0 binding.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from adapters.mineflayer.python_protocol import MineflayerObservation

SOURCE_SCHEMA = "S_V6_TRIAL_START_SOURCE_V1"
NAMESPACE = "relayself_v6_start"
FUNCTION_ID = f"{NAMESPACE}:start_trial"
INSTALL_ID = f"{NAMESPACE}:install"
OBJECTIVE = "rs_v6_tick"  # same score objective as the independently frozen food V2
STARTS = ("WORLD_START_A", "WORLD_START_B", "WORLD_START_C", "WORLD_START_D")
MAX_SCORE = 2**31 - 1
START_FUNCTION_PATH = f"data/{NAMESPACE}/function/start_trial.mcfunction"
PACK_FOLDER = "relayself_v6_start_v1"

# Food V2 must install/create OBJECTIVE first, before this separate start pack.
INSTALL_LINES = (
    f"scoreboard players add #start_attempt {OBJECTIVE} 0",
    f"scoreboard players add #start_gametime {OBJECTIVE} 0",
)
GUARD = f"execute if score #start_attempt {OBJECTIVE} matches 1 run "
READBACK_LINES = (
    f"scoreboard players get #start_attempt {OBJECTIVE}",
    f"scoreboard players get #start_gametime {OBJECTIVE}",
)


class V6StartRejected(ValueError):
    """Unregistered marker, replay/overflow or false time/source binding."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise V6StartRejected(reason)


def _identity(slot: str, nonce: str) -> None:
    _require(type(slot) is str and slot in STARTS, "unknown V6 World-start slot")
    _require(
        type(nonce) is str and re.fullmatch(r"[0-9a-f]{32}", nonce) is not None,
        "trial nonce must be exactly 32 lower-case hex characters",
    )


def start_function_lines(slot: str, nonce: str) -> tuple[str, ...]:
    """A nonce distinguishes sessions but is NOT authentication or admission."""
    _identity(slot, nonce)
    return (
        f"scoreboard players add #start_attempt {OBJECTIVE} 1",
        GUARD + f"scoreboard players set #start_gametime {OBJECTIVE} -1",
        GUARD + "execute store result score #start_gametime "
        f"{OBJECTIVE} run time query gametime",
        GUARD + f"say RELAYSELF_V6_TRIAL_START_{slot}_{nonce}_NOT_ADMITTED",
        f"execute if score #start_attempt {OBJECTIVE} matches 2.. "
        f"run say RELAYSELF_V6_TRIAL_START_REPLAY_BLOCKED_{slot}_{nonce}",
    )


def proposed_start_pack(slot: str, nonce: str) -> dict[str, bytes]:
    """Pure generated pack in memory; never mutate Golden or its clone."""
    lines = start_function_lines(slot, nonce)
    meta = {
        "pack": {
            "pack_format": 81,
            "description": "RelaySelf V6 server trial-start clock source; NO LIVE GRANT",
        },
    }
    return {
        "pack.mcmeta": (
            json.dumps(meta, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode(),
        f"data/{NAMESPACE}/function/install.mcfunction": (
            "\n".join(INSTALL_LINES) + "\n"
        ).encode(),
        START_FUNCTION_PATH: ("\n".join(lines) + "\n").encode(),
    }


def source_plan(slot: str, nonce: str) -> dict[str, Any]:
    """For R's future independently pinned *separate* staged-clone delta."""
    blobs = proposed_start_pack(slot, nonce)
    return {
        "schema": SOURCE_SCHEMA,
        "classification": "S_V6_START_PACK_SOURCE_ONLY",
        "slot": slot, "trial_nonce": nonce,
        "version": "1.21.8", "pack_format": 81,
        "pack_folder": PACK_FOLDER,
        "required_prior_setup": "FOOD_V2_OBJECTIVE_INSTALL_FIRST",
        "start_invocation": f"function {FUNCTION_ID}",
        "staging_requires_new_r_v_profile": True,
        "sha256": {k: hashlib.sha256(v).hexdigest() for k, v in blobs.items()},
        "original_stopped_golden_mutated": False,
        "instrumented_live_start_attested": False,
        "first_native_l0_binding_attested": False,
        "command_originals_attested": False,
        "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


def review_claimed_start(
    *, slot: str, nonce: str,
    first_l0: MineflayerObservation,
    expected_session_id: str, expected_first_probe_seq: int,
    attempt_count: int, reported_gametime: int,
    source_function_sha256: str,
) -> dict[str, Any]:
    """Source-shape association only, never a server or packet attestation.

    The first L0 probe provides an unambiguous prospective association, not
    proof that the server function ran at the same tick as that probe.
    """
    blob = proposed_start_pack(slot, nonce)[START_FUNCTION_PATH]
    expected_sha = hashlib.sha256(blob).hexdigest()
    _require(
        isinstance(first_l0, MineflayerObservation)
        and first_l0.kind == "probe"
        and first_l0.provenance.source == "mineflayer"
        and type(expected_session_id) is str and bool(expected_session_id)
        and first_l0.session_id == expected_session_id
        and type(expected_first_probe_seq) is int
        and first_l0.seq == expected_first_probe_seq
        and first_l0.request_id != ""
        and first_l0.snapshot.nearby_entities_coverage.truncated is False
        and first_l0.snapshot.nearby_entities_coverage.candidate_count
        == len(first_l0.snapshot.nearby_entities)
        and not first_l0.snapshot.inventory
        and not any(e.name == "item" for e in first_l0.snapshot.nearby_entities),
        "first same-session item-free L0 probe not source-shaped",
    )
    _require(
        type(attempt_count) is int and attempt_count == 1,
        "replayed or forged trial start count",
    )
    _require(
        type(reported_gametime) is int
        and 0 <= reported_gametime <= MAX_SCORE,
        "invalid signed-int32 server-start time claim",
    )
    _require(
        type(source_function_sha256) is str
        and source_function_sha256 == expected_sha,
        "unrecognized start function source SHA",
    )
    return {
        "classification": "S_V6_START_SCORE_AND_L0_CLAIM_REVIEW_ONLY",
        "world_start_slot": slot,
        "trial_nonce": nonce,
        "claimed_start_gametime": reported_gametime,
        "claimed_start_attempts": attempt_count,
        "native_session_id": first_l0.session_id,
        "first_l0_probe_seq": first_l0.seq,
        "first_l0_request_id": first_l0.request_id,
        "start_function_sha256": expected_sha,
        "first_l0_to_server_effect_same_tick_attested": False,
        "server_original_console_bytes_attested": False,
        "loaded_start_function_attested": False,
        "live_golden_start_identity_attested": False,
        "physical_execution_authorized": False,
    }


def review_claimed_elapsed(
    start_claim: dict[str, Any], food_claim: dict[str, Any],
    *, expected_slot: str, expected_session_id: str,
) -> dict[str, Any]:
    """A bounded arithmetic *claim*; R must separately source-qualify both."""
    _require(
        type(start_claim) is dict and type(food_claim) is dict
        and start_claim.get("classification")
        == "S_V6_START_SCORE_AND_L0_CLAIM_REVIEW_ONLY"
        and start_claim.get("world_start_slot") == expected_slot
        and start_claim.get("native_session_id") == expected_session_id
        and start_claim.get("physical_execution_authorized") is False
        and food_claim.get("classification")
        == "S_V6_ATOMIC_SERVER_SCORE_CLAIM_REVIEW_ONLY"
        and food_claim.get("claimed_atomic_function_attempt_count") == 1
        and food_claim.get("original_server_console_bytes_attested") is False
        and food_claim.get("physical_execution_authorized") is False,
        "start/food source-claim identity mismatch",
    )
    start_tick = start_claim.get("claimed_start_gametime")
    food_tick = food_claim.get("claimed_server_gametime")
    _require(
        type(start_tick) is int and type(food_tick) is int
        and 0 <= start_tick <= food_tick <= MAX_SCORE,
        "negative, inverted or overflowing reported elapsed World time",
    )
    return {
        "classification": "S_V6_CLAIMED_ELAPSED_WORLD_TICKS_REVIEW_ONLY",
        "world_start_slot": expected_slot,
        "session_id": expected_session_id,
        "claimed_start_tick": start_tick,
        "claimed_food_tick": food_tick,
        "claimed_elapsed_world_ticks": food_tick - start_tick,
        "m0_decision_tick_equated_to_world_time": False,
        "host_clock_equated_to_world_time": False,
        "r_independent_originals_attested": False,
        "paired_12_arm_world_time_matched": False,
        "physical_execution_authorized": False,
        "v_science_g3": "NO_GO",
    }
