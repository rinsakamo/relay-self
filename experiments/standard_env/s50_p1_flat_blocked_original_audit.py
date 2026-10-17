"""R read-only audit profile for S50/P1 FLAT physical-run-001 BLOCKED source.

Does NOT import S readers, rewrite S report, run Paper/Mineflayer, certify a
server-effective input tick, approve P1 WAIT, or change old V7 PASS admissions.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

CLASS = "R_S50_P1_FLAT_BLOCKED_ORIGINAL_SOURCE_REVIEW_DEV_ONLY"
SOURCE_SESSION = "be9aa263-afac-4b17-945b-09eef6c47126"
SOURCE_SHA256 = {
    "original_native.jsonl": "28c79c4cf2d16bd52f787568c9f2f2a22ed8633627485a509dcc66c9d5e78ad4",
    "owner_commands.jsonl": "37e56e56b775cb433bf7ee5a77c3ca9524f85f6929677a5b1bbd01d606b72c56",
    "paper_server.log": "01db9aeb30ecba5e4009f07a19f0c490f3d21500735d9a85b3e6cecaa192620e",
    "s50_action_original.jsonl": "e116e936e7e007f70695aab135c83d9b8d36c75197da89b95d785c9f2bf6cdeb",
    "s50_p1_native_controls_original.jsonl": "d86f08cca11fc399d37b1b6d66d9ce682f3386947579247babc4138da643d3a6",
}
CONTROLS = ("forward", "back", "left", "right", "jump", "sprint", "sneak")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def no_duplicate_fields(pairs):
    value = {}
    for key, data in pairs:
        require(key not in value, "duplicate original JSON key")
        value[key] = data
    return value


def jsonl(raw: bytes) -> list[dict]:
    try:
        values = [json.loads(line, object_pairs_hook=no_duplicate_fields)
                  for line in raw.decode("utf-8").splitlines()]
    except (ValueError, UnicodeError) as exc:
        raise ValueError("undecodable original source JSONL") from exc
    require(values and all(isinstance(row, dict) for row in values),
            "empty/non-object original source")
    return values


def originals(root: Path, expected: dict[str, str]) -> dict[str, bytes]:
    require(root.is_absolute() and root.is_dir()
            and not root.is_symlink()
            and not any(part.is_symlink() for part in root.parents),
            "unsafe physical original root")
    require(set(expected) == set(SOURCE_SHA256), "incomplete R frozen source manifest")
    data = {}
    for name, digest in expected.items():
        file = root / name
        require(file.is_file() and not file.is_symlink()
                and 0 < file.stat().st_size <= 32_000_000,
                "missing/unbounded original file: " + name)
        raw = file.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == digest,
                "frozen original source SHA256 mismatch: " + name)
        data[name] = raw
    return data


def fields(line: str, prefix: str) -> dict[str, str]:
    require(line.count(prefix) == 1, "malformed Paper prefix")
    pairs = [token.split("=", 1) for token in line.split(prefix, 1)[1].split()]
    require(pairs and all(len(p) == 2 for p in pairs)
            and len({p[0] for p in pairs}) == len(pairs),
            "malformed/duplicate Paper key")
    return dict(pairs)


def review(root: Path, *, expected_sha: dict[str, str] | None = None,
           expected_session: str = SOURCE_SESSION) -> dict:
    """Reject foreign bytes and falsified PASS; preserve BLOCKED interpretation."""
    raw = originals(root, SOURCE_SHA256 if expected_sha is None else expected_sha)
    native = jsonl(raw["original_native.jsonl"])
    action = jsonl(raw["s50_action_original.jsonl"])
    controls = jsonl(raw["s50_p1_native_controls_original.jsonl"])
    commands = jsonl(raw["owner_commands.jsonl"])
    require(len(native) == 28
            and all(row.get("seq") == i and row.get("session_id") == expected_session
                    for i, row in enumerate(native))
            and native[0].get("type") == "adapter_started"
            and native[26].get("type") == "shutdown_ack"
            and native[27].get("type") == "connection_end",
            "new FLAT BLOCKED session/source chronology incorrect")
    for seq, effect, result in (
        (7, "look", "applied"), (8, "set_control", "applied"),
        (17, "clear_controls", "applied"),
    ):
        require(native[seq].get("type") == "effect_result"
                and native[seq].get("effect") == effect
                and native[seq].get("result") == result,
                "real native motor ACK is missing/changed")
    require(len([row for row in commands if row.get("type") == "shutdown"]) == 1,
            "shutdown command omitted/duplicated")
    issued = [row for row in action if row.get("state") == "issued"]
    outcomes = [row for row in action if row.get("state") == "outcome"]
    require(len(issued) == len(outcomes) == 1
            and issued[0].get("action_id") == outcomes[0].get("action_id")
            and issued[0].get("session_id") == expected_session
            and outcomes[0].get("session_id") == expected_session,
            "S Action ISSUED/OUTCOME originals incomplete")
    consequence = outcomes[0].get("consequence")
    require(type(consequence) is dict
            and consequence.get("kind") == "BLOCKED"
            and consequence.get("action_id") == issued[0]["action_id"]
            and consequence.get("session_id") == expected_session
            and type(consequence.get("progress_m")) in (float, int)
            and math.isclose(consequence["progress_m"], -0.3363737550662047,
                             abs_tol=1e-8, rel_tol=0),
            "S source BLOCKED consequence was changed/promoted")
    require(not any(row.get("status") == "PASS"
                    or row.get("physical_outcome") == "PASS" for row in action),
            "retroactive PASS promotion of source BLOCKED")

    require(5 <= len(controls) <= 8192
            and controls[0].get("kind") == "SESSION_START"
            and controls[-1].get("kind") == "SHUTDOWN_ACK",
            "client native direct-control boundary incomplete")
    client_tick = 0
    count_after = 0
    clear_seen = False
    forward_seen = False
    for ordinal, row in enumerate(controls, 1):
        require(row.get("source") == "S50_DEV_NATIVE_READBACK_V1"
                and row.get("session_id") == expected_session
                and row.get("ordinal") == ordinal,
                "readback foreign/duplicate source order")
        if row.get("kind") == "PHYSICS_TICK":
            client_tick += 1
        require(row.get("client_physics_tick") == client_tick,
                "original client physicsTick gap/nonsequenced callback")
        if row["kind"] == "SESSION_START":
            require(ordinal == 1, "repeated native session start")
            continue
        state = row.get("controls")
        require(isinstance(state, dict) and set(state) == set(CONTROLS)
                and all(type(v) is bool for v in state.values()),
                "incomplete or nonboolean native control state")
        if row.get("kind") == "EFFECT_ACK":
            if row.get("native_seq") == 8:
                require(state["forward"], "forward not directly observed ON")
                forward_seen = True
            if row.get("native_seq") == 17:
                require(not any(state.values()), "clear failed to release input")
                clear_seen = True
        if clear_seen and row.get("kind") == "PHYSICS_TICK":
            require(not any(state.values()), "client controls reactivated")
            count_after += 1
    require(forward_seen and clear_seen and client_tick == 30
            and count_after >= 23, "missing physical callback continuity")

    paper = raw["paper_server.log"].decode("utf-8")
    starts = [fields(x, "S50_DEV_WAIT_BEGIN ") for x in paper.splitlines()
              if "S50_DEV_WAIT_BEGIN " in x]
    samples = [fields(x, "S50_DEV_WAIT_TICK ") for x in paper.splitlines()
               if "S50_DEV_WAIT_TICK " in x]
    require(len(starts) == 1 and len(samples) == 8
            and int(starts[0]["tick"]) == 43
            and [int(x["tick"]) for x in samples] == list(range(44, 52)),
            "Paper WAIT candidate samples invalid")
    marker, world = starts[0]["marker_id"], starts[0]["world"]
    require(all(row.get("marker_id") == marker and row.get("world") == world
                and float(row["x"]) == 0.5
                and float(row["z"]) == 1.707742656099451
                and math.isfinite(float(row["y"])) for row in samples),
            "foreign or altered Paper native body snapshots")
    return {
        "classification": CLASS,
        "source_session": expected_session,
        "sha256_originals_checked": len(raw),
        "native_frames_checked": len(native),
        "client_physics_ticks": client_tick,
        "post_clear_client_callbacks": count_after,
        "paper_candidate_tick_start": 44,
        "paper_candidate_tick_end": 51,
        "s50_consequence": "BLOCKED_RETAINED_NO_PASS_PROMOTION",
        "server_effective_input_release_tick": "NOT_ATTESTED",
        "paper_whole_tick_activity_absence": "NOT_ATTESTED",
        "all_action_issuers_absent": "NOT_ATTESTED",
        "independent_R_qualification": False,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "science_go": False,
    }
