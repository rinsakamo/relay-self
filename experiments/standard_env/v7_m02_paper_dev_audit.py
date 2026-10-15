"""R independent V7 M0.2 Paper source-byte DEV reviewer, NEVER QUAL/SCIENCE.

Checks new disposable five-arm native originals against frozen source profiles,
not claims of ecological calibration, controlled experimental ticks or paired
world equivalence. No Minecraft process starts and no file modifications.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from experiments.standard_env import m02_paper_dev_audit as source

CLASSIFICATION = "RSEE_V7_M02_CHANGED_CONFIG_DEV_ORIGINAL_REVIEW_ONLY"
S_SOURCE_HEAD = "944a68ca36f90380ffa5481ba85a6f95ed08ba18"
PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
PLUGIN_SHA = "0ed8a00a7ebf577bdbea361e2c6facf7ed4b24001c017d362823da5cb60398e5"
ARMS = {
    "BASE_ON": (1, 1, "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e"),
    "SHAM_ON": (1, 1, "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e"),
    "BASAL_ZERO": (0, 1, "260e3b14e7f536ff7416dffc8ed713397e6f324af1074e80af296856a84cd2c0"),
    "WALK_ZERO": (1, 0, "f7d7c5ec9c94d95bbaf13af07ac25c518c3fe71e74216df2bfd2600c15b4bb40"),
    "BOTH_ZERO": (0, 0, "b8c5991f4e1c5b60e487747696b329e8d7d079c7d1090baccda99566410103cb"),
}
ORIGINALS = ("paper_server.log", "original_native.jsonl",
             "owner_commands.jsonl", "initial_world_level.dat", "m02_report.json")


class Rejected(ValueError):
    pass


def need(value: bool, message: str) -> None:
    if not value:
        raise Rejected(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def number(v: Any) -> float:
    need(type(v) in (float, int) and math.isfinite(v), "invalid reported number")
    return float(v)


def read_json_lines(raw: bytes) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    except (ValueError, UnicodeError) as exc:
        raise Rejected("invalid original native/command stream") from exc
    need(bool(rows) and all(type(x) is dict for x in rows), "empty/foreign original stream")
    return rows


def read_source(root: Path, name: str) -> bytes:
    need(root.is_absolute() and root.is_dir() and not root.is_symlink()
         and all(not p.is_symlink() for p in root.parents), "unsafe original root")
    try:
        raw = source.read_original(root / name)
    except (OSError, ValueError) as exc:
        raise Rejected("original missing/unsafe: " + name) from exc
    return raw


def parse_logs(raw: bytes, arm: str) -> dict[str, Any]:
    baseline, walk_rate, _ = ARMS[arm]
    lines = raw.decode("utf-8").splitlines()
    need(any("M02_DEV_ONLY: candidate physics" in x for x in lines),
         "missing genuine Paper candidate plugin enablement")
    need(not any("M02_DEV_DISABLED:" in x for x in lines),
         "Paper physics plugin disabled")
    body = []
    motion = []
    native_walk = []
    for line in lines:
        if "M02_DEV_BODY sampled_tick=" in line:
            m = re.search(r"sampled_tick=(\d+).*?exhaustion=([0-9.eE+\-]+).*?motion_blocks=([0-9.eE+\-]+)", line)
            need(m is not None, "unparseable actual player World tick receipt")
            body.append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
        if "M02_DEV_MOTION " in line and " reason=WALK " in line:
            m = re.search(r"\bblocks=([0-9.eE+\-]+).*?\bbilled=([0-9.eE+\-]+)", line)
            need(m is not None, "missing actual packet displacement/billed source")
            motion.append((float(m.group(1)), float(m.group(2))))
        if "M02_DEV_EVENT " in line and " reason=WALK " in line:
            native_walk.append(line)
    need(body and body[0][0] == 1 and body[-1][0] >= 200
         and all(x[0] < y[0] for x, y in zip(body, body[1:])),
         "not at least 200 monotone actual Paper player ticks")
    need(motion and all(math.isfinite(a) and math.isfinite(b)
                        and a > 0 and b >= 0 for a, b in motion),
         "no valid actual packet movement source")
    blocks = sum(x for x, _ in motion)
    charge = sum(y for _, y in motion)
    need(0.5 < blocks < 2.0 and
         abs(charge - blocks * 0.01 * walk_rate) < 1e-7,
         "observed Paper path/WALK billed mismatch")
    need(all("original=0.0 " in line and "replaced=0.0" in line
             for line in native_walk), "original vanilla event double billed")
    need(not any("M02_DEV_MOTION_UNCLASSIFIED" in x for x in lines),
         "unknown unbilled physical movement")
    return {
        "min_player_ticks_reached": body[-1][0],
        "body_source_samples": len(body), "real_motion_packets": len(motion),
        "real_motion_path_blocks": blocks, "observed_walk_debit": charge,
        "inferred_basal_debit_at_200_ticks": 0.2 * baseline,
        "basal_debit_independently_attested": False,
        "native_walk_event_count": len(native_walk),
    }


def review(root: Path, arm: str) -> dict[str, Any]:
    need(arm in ARMS, "unknown prospective arm")
    raw = {name: read_source(root, name) for name in ORIGINALS}
    try:
        r = json.loads(raw["m02_report.json"].decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Rejected("original S DEV report invalid") from exc
    need(type(r) is dict and r.get("classification") == "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
         and r.get("status") == "PASS" and r.get("owner_status") == "PASS"
         and r.get("scenario") == f"V7_{arm}_PHYSICS_DEV"
         and r.get("v7_arm") == arm and r.get("v7_seed") == 61021
         and r.get("v7_real_science_trials") == 0
         and r.get("v7_food_introduced_by_runner") is False
         and r.get("qualified") is False and r.get("science_go") is False
         and r.get("production_go") is False
         and r.get("m0_virtual_ledger_used") is False
         and r.get("java_exit") == 0 and r.get("node_exit") == 0
         and r.get("port_released_after_shutdown") is True,
         "source owner is not safe 1-World V7 DEV")
    need(r.get("paper_sha256") == PAPER_SHA and r.get("plugin_sha256") == PLUGIN_SHA
         and r.get("plugin_config_sha256") == ARMS[arm][2],
         "wrong binary or changed factor profile identity")
    reported_hashes = r.get("evidence_hashes")
    need(type(reported_hashes) is dict and
         all(reported_hashes.get(n) == sha(raw[n]) for n in (
             "original_native.jsonl", "owner_commands.jsonl", "paper_server.log")),
         "original bytes disagree with S source digest")
    snap = r.get("initial_world_receipt")
    need(type(snap) is dict and snap.get("sha256") == sha(raw["initial_world_level.dat"])
         and snap.get("size_bytes") == len(raw["initial_world_level.dat"])
         and snap.get("snapshot_phase") ==
         "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION",
         "first World original not pre-Action witnessed")
    try:
        world = gzip.decompress(raw["initial_world_level.dat"])
    except (OSError, EOFError) as exc:
        raise Rejected("not true World gzip original") from exc
    need(len(world) >= 4 and len(world) <= 16 * 1024 * 1024
         and world[0] == 10, "not valid World NBT compound")
    native = read_json_lines(raw["original_native.jsonl"])
    cmds = read_json_lines(raw["owner_commands.jsonl"])
    session = r.get("source_session_id")
    need(isinstance(session, str) and session
         and all(row.get("session_id") == session and row.get("seq") == i
                 for i, row in enumerate(native))
         and native[0].get("type") == "adapter_started"
         and native[-2].get("type") == "shutdown_ack"
         and native[-1].get("type") == "connection_end",
         "native session, original sequence or shutdown ACK absent")
    need(sum(x.get("type") == "shutdown" for x in cmds) == 1
         and cmds[-1].get("type") == "shutdown",
         "original owner STOP absent/multiple")
    need(not any(x.get("effect") in ("equip_item", "consume_held") for x in native),
         "food consumption contaminates V7 no-food condition")
    move = r.get("movement")
    need(type(move) is dict and move.get("source_session") == session
         and move.get("action_state") == "outcome"
         and move.get("requested_max_step_blocks") == 1.0
         and 0.5 <= number(move.get("observed_progress_blocks")) <= 1.5
         and type(move.get("look_seq")) is int
         and type(move.get("forward_seq")) is int
         and type(move.get("clear_seq")) is int
         and move["look_seq"] < move["forward_seq"] < move["clear_seq"],
         "governed one-block original S50 MOVE source absent")
    for key, effect in (("look_seq", "look"), ("forward_seq", "set_control"),
                        ("clear_seq", "clear_controls")):
        row = native[move[key]]
        need(row.get("type") == "effect_result" and row.get("effect") == effect,
             "native child effect absent/source seq wrong")
    cost = parse_logs(raw["paper_server.log"], arm)
    physics = r.get("v7_source")
    need(type(physics) is dict
         and physics.get("classification") == "S_V7_PAPER_DEV_OBSERVED_SOURCE_SHAPE_ONLY"
         and physics.get("arm") == arm
         and physics.get("basal_source_charge_inferred_not_independently_attested") is True
         and number(physics.get("observed_motion_path_blocks")) ==
         cost["real_motion_path_blocks"]
         and abs(number(physics.get("observed_motion_debit")) -
                 cost["observed_walk_debit"]) <= 1e-8
         and physics.get("science_go") is False, "S physical source diagnostics not reproducible")
    for name, expected in raw.items():
        need(sha(read_source(root, name)) == sha(expected),
             "original changed during independent readback")
    return {
        "classification": CLASSIFICATION,
        "arm": arm, "owner_run_source": S_SOURCE_HEAD,
        "source_session": session,
        "source_world_level_sha256": sha(raw["initial_world_level.dat"]),
        "source_original_sha256": {n: sha(x) for n, x in raw.items()},
        "paper_candidate_profile_sha256": ARMS[arm][2],
        **cost,
        "real_s50_move_attested": True, "real_s51_eat_tested": False,
        "strict_world_seed_authenticated": False,
        "source_basal_physical_debit_independently_attested": False,
        "all_paired_paths_matched": False,
        "r_changed_config_physical_qualified": False,
        "actual_v7_science_trials": 0,
        "v_science_go": False, "ecological_calibration_go": False,
        "production_go": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-root", required=True, type=Path)
    parser.add_argument("--arm", required=True)
    args = parser.parse_args()
    try:
        result = review(args.original_root, args.arm)
        code = 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        result = {"classification": "RSEE_V7_M02_DEV_SOURCE_INVALID_OR_UNDETERMINED",
                  "failure": f"{type(exc).__name__}: {exc}",
                  "r_changed_config_physical_qualified": False,
                  "actual_v7_science_trials": 0, "v_science_go": False,
                  "production_go": False}
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
