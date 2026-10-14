"""S #537 / V6: immutable *source-only* server-atomic food fixture proposal.

Prospective 1.21.8 datapack source. No installation, process launch,
Golden copy, /summon execution, packet interpolation, approval or science.
Server-side /function runs ordered commands in one function invocation;
the pre/post gametime scoreboard can be *claimed* later from original logs.
Only R independent original evidence can review that claim.
"""
from __future__ import annotations

import json
from typing import Any

SCHEMA = "S_V6_ATOMIC_FOOD_FUNCTION_SOURCE_V1"
NAMESPACE = "relayself_v6"
OBJECTIVE = "rs_v6_tick"
FUNCTION_ID = f"{NAMESPACE}:atomic_food"
INSTALL_ID = f"{NAMESPACE}:install"
MAX_SCORE = 2**31 - 1

INSTALL_LINES = (
    f"scoreboard objectives add {OBJECTIVE} dummy",
    f"scoreboard players set #before {OBJECTIVE} -1",
    f"scoreboard players set #after {OBJECTIVE} -1",
    f"scoreboard players set #ok {OBJECTIVE} 0",
)
ATOMIC_LINES = (
    f"scoreboard players set #before {OBJECTIVE} -1",
    f"scoreboard players set #after {OBJECTIVE} -1",
    f"scoreboard players set #ok {OBJECTIVE} 0",
    f"execute store result score #before {OBJECTIVE} run time query gametime",
    f'execute store success score #ok {OBJECTIVE} run summon minecraft:item ~2.5 ~0.2 ~ '
    '{Item:{id:"minecraft:rotten_flesh",count:1}}',
    f"execute store result score #after {OBJECTIVE} run time query gametime",
    "say RELAYSELF_V6_ATOMIC_SOURCE_CANDIDATE_NOT_ADMITTED",
)
READBACK_LINES = (
    f"scoreboard players get #before {OBJECTIVE}",
    f"scoreboard players get #after {OBJECTIVE}",
    f"scoreboard players get #ok {OBJECTIVE}",
)
PROPOSED_OPERATOR_INVOKE = f"execute at RelaySelf run function {FUNCTION_ID}"


class AtomicV6Rejected(ValueError):
    """Never permit an internally contradictory or forged time witness."""


def _need(condition: bool, msg: str) -> None:
    if not condition:
        raise AtomicV6Rejected(msg)


def proposed_datapack_files() -> dict[str, bytes]:
    """Construct deterministic bytes in memory, never mutate a World."""
    metadata = {
        "pack": {
            "pack_format": 81,  # Minecraft Java Edition 1.21.7/1.21.8
            "description": "RelaySelf V6 atomic food age PRE-ADMISSION; NO LIVE GRANT",
        },
    }
    return {
        "pack.mcmeta": (
            json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"),
        f"data/{NAMESPACE}/function/install.mcfunction": (
            "\n".join(INSTALL_LINES) + "\n"
        ).encode("utf-8"),
        f"data/{NAMESPACE}/function/atomic_food.mcfunction": (
            "\n".join(ATOMIC_LINES) + "\n"
        ).encode("utf-8"),
    }


def plan() -> dict[str, Any]:
    """Pure source handoff. Nothing is installed on a server."""
    import hashlib

    files = proposed_datapack_files()
    return {
        "classification": "S_V6_ATOMIC_FOOD_SOURCE_DESIGN_ONLY",
        "schema": SCHEMA,
        "target_minecraft_version": "1.21.8",
        "datapack_format": 81,
        "datapack_files_sha256": {
            path: hashlib.sha256(data).hexdigest() for path, data in files.items()
        },
        "datapack_files_installed": False,
        "preregistered_operator_command": PROPOSED_OPERATOR_INVOKE,
        "preload_install_command": f"function {INSTALL_ID}",
        "server_scoreboard_readback_commands": list(READBACK_LINES),
        "claimed_age_precision": "ATOMIC_FUNCTION_SAME_SERVER_TICK_IF_EXECUTED",
        "score_int32_overflow_risk": "REJECT_WITHOUT_QUALIFIED_BOUND",
        "exact_command_effect_tick_originals_attested": False,
        "server_command_originals_attested": False,
        "matched_world_start_attested": False,
        "minecraft_or_node_started": False,
        "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


def review_reported_scores(
    *, before: int, after: int, summon_succeeded: int,
    source_function_sha256: str, expected_function_sha256: str,
) -> dict[str, Any]:
    """Only compare independently presented *claims*, never parse fake originals.

    Original stdout, function-loading, scoreboard commands, server-side effect,
    no duplicate invocations and packet age lineage ALL remain R-owned.
    """
    from hashlib import sha256

    canonical = sha256(proposed_datapack_files()[
        f"data/{NAMESPACE}/function/atomic_food.mcfunction"
    ]).hexdigest()
    _need(
        type(source_function_sha256) is str
        and type(expected_function_sha256) is str
        and source_function_sha256 == expected_function_sha256 == canonical,
        "source function differs from prospective exact byte plan",
    )
    _need(type(before) is int and type(after) is int
          and 0 <= before <= MAX_SCORE and 0 <= after <= MAX_SCORE,
          "gametime scoreboard must be safe signed 32-bit nonnegative integer")
    _need(type(summon_succeeded) is int and summon_succeeded == 1,
          "server scoreboard summon success not recorded")
    _need(before == after, "pre/post gametime straddled Minecraft ticks")
    return {
        "classification": "S_V6_ATOMIC_SERVER_SCORE_CLAIM_REVIEW_ONLY",
        "claimed_server_gametime": before,
        "claimed_summon_success": 1,
        "mcfunction_sha256": canonical,
        "original_server_console_bytes_attested": False,
        "real_server_function_loaded_attested": False,
        "server_effect_age_authenticity_attested": False,
        "world_start_matched_attested": False,
        "native_packet_time_correlated": False,
        "m0_tick_matched": False,
        "physical_execution_authorized": False,
        "science_g3": "NO_GO",
    }


if __name__ == "__main__":
    print(json.dumps(plan(), sort_keys=True, indent=2))
