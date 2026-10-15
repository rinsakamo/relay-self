"""Independent R Paper B1 ON/OFF *historical DEV* original-byte audit.

No new World/Java/Node, physical qualification, R grant, V science, or proof
of Memory content bytes. The known original Archive is SHA-pinned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import zipfile
from pathlib import Path
from typing import Any

from experiments.standard_env.m02_paper_dev_audit import (
    BODY,
    EVENT,
    MOVEMENT,
    Rejected,
    decode,
    finite,
    require,
    rows,
)

S_PRODUCER_HEAD = "8611a4cafef1e1acce4309359e429c8188f103ec"
PAPER_ARTIFACT_RUN = 38738039907
PAPER_ARTIFACT_ID = 11974134396
PAPER_ARTIFACT_ZIP_SHA256 = (
    "3707510b36ae6b2c3f9cc8f65f0435f65e0f98e4ec5148ed3a91d4ee13de2891"
)
ORIGINAL_SHA = {
    "on": {
        "original_native.jsonl": "e5dfc2816021fdcc5104878b27bcd681bebe08d6aa12183d3077a1e21262f518",
        "owner_commands.jsonl": "18d510dda058d48365b092ab6f62296812f4341b89d4ae1992779d239debb0f4",
        "paper_server.log": "c9daabb24c9f9961875bd2ca13f555c8ded93655a6ae7d7897d1cd8d29321ff7",
        "initial_world_level.dat": "6372725c580ffaba82139fe3cd004b28472585e0710b985bc0ea52dd0b3b7137",
        "m02_report.json": "4a716c9837d90c38b681265c60fa7e19c68d9f670174d3881f2cadd41dd7c3f1",
    },
    "off": {
        "original_native.jsonl": "49ef53a7dfa5180ed08ce115e1666fbc1dc9b810c90db577184ad35a897b7f0d",
        "owner_commands.jsonl": "7ede0aee5f865e922645347fd566c2fe89598e0e073265da71e433d750f5b517",
        "paper_server.log": "49df0b07c77a86458005051481eade89d87e28a7ab5e4129637afa4a34a98478",
        "initial_world_level.dat": "9ed57c685f93432b7b68570670fa5514354b091c7f1a9fcc19e52f05c4dca82e",
        "m02_report.json": "4b5ae84c42450fcc6a64cb506cc9375264ac270181bf27f7b6339fdf867f2f9c",
    },
}
PARTS = frozenset(("original_native.jsonl", "owner_commands.jsonl", "paper_server.log",
                   "initial_world_level.dat", "m02_report.json"))


def original_prefix(arm: str) -> str:
    return f"m02-paper-b1-{arm}-{PAPER_ARTIFACT_RUN}-1/"


def _read_zip(p: Path) -> dict[str, bytes]:
    require(p.is_absolute() and p.is_file() and not p.is_symlink()
            and stat.S_ISREG(p.lstat().st_mode), "nonregular/relative archive")
    before = p.stat()
    require(0 < before.st_size < 16 * 1024 * 1024, "archive oversized")
    raw = p.read_bytes()
    after = p.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "archive changed during read")
    require(hashlib.sha256(raw).hexdigest() == PAPER_ARTIFACT_ZIP_SHA256,
            "historical B1 ZIP pin mismatch")
    with zipfile.ZipFile(p) as z:
        names = [x.filename for x in z.infolist()]
        required = {original_prefix(arm) + name for arm in ("on", "off") for name in PARTS}
        require(len(names) == 10 and set(names) == required,
                "duplicate/foreign/missing historical B1 ZIP entries")
        require(all((info.external_attr >> 16) & 0o170000 != 0o120000
                    and 0 < info.file_size < 4 * 1024 * 1024
                    and info.compress_size < 4 * 1024 * 1024
                    for info in z.infolist()), "unsafe/bounded original entry")
        return {name: z.read(name) for name in names}


def probe(n: list[dict[str, Any]], seq: Any) -> dict[str, Any]:
    require(type(seq) is int and 0 < seq < len(n) - 2, "nonexistent native probe seq")
    v = n[seq]
    require(v.get("type") == "observation" and v.get("kind") == "probe"
            and type(v.get("snapshot")) is dict, "not native probe")
    return v["snapshot"]


def count_food(s: dict[str, Any]) -> int:
    inv = s.get("inventory")
    require(type(inv) is list, "missing native food inventory")
    total = 0
    for x in inv:
        require(type(x) is dict, "invalid native inventory row")
        if x.get("name") == "cooked_beef":
            n = x.get("count")
            require(type(n) is int and n >= 0, "invalid native steak count")
            total += n
    return total


def point(s: dict[str, Any]) -> tuple[float, float]:
    p = s.get("position")
    require(type(p) is dict, "missing original World position")
    return finite_signed(p.get("x")), finite_signed(p.get("z"))


def finite_signed(x: Any) -> float:
    require(type(x) in (int, float) and math.isfinite(x), "nonfinite original coordinate")
    return float(x)


def _one_effect(n: list[dict[str, Any]], cmds: list[dict[str, Any]],
                seq: int, name: str, action: str) -> None:
    row = n[seq]
    require(row.get("type") == "effect_result" and row.get("effect") == name
            and row.get("action_id") == action and row.get("result") == "applied",
            "S50/S51 effect not native applied")
    require(sum(x.get("type") == "effect" and x.get("effect") == name
                and x.get("action_id") == action for x in cmds) == 1,
            "missing or replayed original command")


def physics(log: bytes, expected: dict[str, Any]) -> dict[str, float | int]:
    content = log.decode("utf-8")
    require(content.count("M02_DEV_ONLY: candidate physics") == 1, "Paper plugin not sourced")
    mot = []
    bodies = []
    walked = []
    for line in content.splitlines():
        m = MOVEMENT.search(line)
        if m and m.group(2) == "WALK":
            values = (int(m.group(1)), *(float(m.group(i)) for i in range(3, 7)))
            require(all(math.isfinite(v) and v >= 0 for v in values[1:]),
                    "invalid motion telemetry")
            mot.append(values)
            require(math.isclose(sum(q[1] for q in mot), values[3], abs_tol=1e-7)
                    and math.isclose(sum(q[2] for q in mot), values[4], abs_tol=1e-7),
                    "inconsistent cumulative physical motion")
        b = BODY.search(line)
        if b:
            bodies.append(int(b.group(1)))
        e = EVENT.search(line)
        if e and e.group(2) == "WALK":
            walked.append((float(e.group(3)), float(e.group(4))))
    require(mot and bodies and 1 in bodies and 20 in bodies,
            "native coordinate movement or basal World source missing")
    require([x[0] for x in mot] == list(range(1, len(mot) + 1)),
            "missing/duplicate native movement packet")
    require(all(0 < m[1] <= 1 for m in mot), "unbounded native displacement")
    require(all(bodies[i] < bodies[i + 1] for i in range(len(bodies) - 1)),
            "not monotone real World tick samples")
    require(all(v == (0.0, 0.0) for v in walked),
            "native walk event extra charged")
    blocks = sum(x[1] for x in mot)
    debit = sum(x[2] for x in mot)
    require(1 < blocks < 16 and math.isclose(debit, 0.01 * blocks, abs_tol=1e-7),
            "native distance/physical WALK debit mismatch")
    require(type(expected) is dict and expected.get("count_walk_motion_packets") == len(mot)
            and expected.get("count_walk_native_events") == len(walked)
            and math.isclose(finite(expected.get("world_measured_walk_blocks")),
                             blocks, abs_tol=1e-7)
            and math.isclose(finite(expected.get("world_billed_walk_exhaustion")),
                             debit, abs_tol=1e-7), "Paper owner's physical diagnostics conflict")
    return {"native_motion_packets": len(mot), "native_path_blocks": blocks,
            "native_walk_exhaustion": debit, "native_walk_event_count": len(walked)}


def review_arm(arm: str, files: dict[str, bytes]) -> dict[str, Any]:
    pinned = ORIGINAL_SHA[arm]
    for name, digest in pinned.items():
        require(hashlib.sha256(files[name]).hexdigest() == digest,
                "independent historical original SHA256 mismatch: " + name)
    r = decode(files["m02_report.json"])
    require(type(r) is dict and r.get("classification") == "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED"
            and r.get("scenario") == "PAPER_B1_" + arm.upper() + "_DEV"
            and r.get("status") == "PASS" and r.get("owner_status") == "PASS"
            and r.get("qualified") is False and r.get("science_go") is False
            and r.get("production_go") is False and r.get("m0_virtual_ledger_used") is False
            and r.get("java_exit") == 0 and r.get("node_exit") == 0
            and r.get("port_released_after_shutdown") is True,
            "Paper historical B1 DEV not safely closed")
    require(r.get("evidence_hashes") == {
        k: pinned[k] for k in ("original_native.jsonl", "owner_commands.jsonl", "paper_server.log")},
        "producer source hash report disagrees")
    world = r.get("initial_world_receipt")
    require(type(world) is dict and world.get("sha256") == pinned["initial_world_level.dat"]
            and world.get("size_bytes") == len(files["initial_world_level.dat"])
            and world.get("snapshot_phase") == "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION",
            "missing source original World before first Action")
    native, commands = rows(files["original_native.jsonl"]), rows(files["owner_commands.jsonl"])
    session = r.get("source_session_id")
    require(type(session) is str and session
            and all(x.get("seq") == i and x.get("session_id") == session
                    for i, x in enumerate(native)), "native source seq/session drift")
    require(native[0].get("type") == "adapter_started"
            and native[-2].get("type") == "shutdown_ack"
            and native[-1].get("type") == "connection_end",
            "missing true native STOP ACK")
    require(commands[-1].get("type") == "shutdown"
            and sum(c.get("type") == "shutdown" for c in commands) == 1,
            "missing unique outbound STOP")
    require(native[0].get("mineflayer_version") == "4.39.0"
            and native[0].get("config", {}).get("version") == "1.21.8",
            "wrong original Mineflayer source")
    ground = r.get("ground_foraging")
    require(type(ground) is dict and ground.get("source_session") == session
            and ground.get("status") == "PICKUP_SOURCE_CONSISTENT"
            and ground.get("strict_pickup_causality") == "UNKNOWN"
            and ground.get("virtual_energy_ledger_used") is False,
            "invalid Paper B1 original forage summary")
    moves = ground.get("movement_outcomes")
    require(type(moves) is list and len(moves) == 6
            and [x.get("kind") for x in moves][:4]
            == ["PROGRESSED", "BLOCKED", "PROGRESSED", "ARRIVED"]
            and sum(x.get("kind") == "BLOCKED" for x in moves) == 1,
            "no authentic bounded first BLOCKED then lateral MOVE")
    lateral = []
    for i, move in enumerate(moves):
        require(move.get("action_id") == f"m02-paper-forage-move-{i}"
                and move.get("terminal") == "outcome", "source Action closed incorrectly")
        s1, s2 = probe(native, move.get("before_seq")), probe(native, move.get("after_seq"))
        before, after = point(s1), point(s2)
        distance = math.dist(before, after)
        require(distance + 0.05 >= finite(move.get("progress_blocks"))
                and distance - finite(move.get("progress_blocks")) <= 0.2,
                "native physical movement incompatible with reported goal progress")
        if move["kind"] == "BLOCKED":
            require(distance < 0.05, "BLOCKED original made progress")
        else:
            require(distance > 0.05, "PROGRESSED/ARRIVED original has no movement")
        look, forward, clear = (move.get(name) for name in
                                ("look_seq", "forward_seq", "clear_seq"))
        require(type(look) is int and type(forward) is int and type(clear) is int
                and move["before_seq"] < look < forward < clear < move["after_seq"],
                "missing source-ordered physical S50 effect")
        action = move["action_id"]
        for seq, effect, eid in (
            (look, "look", action + "-look"),
            (forward, "set_control", action),
            (clear, "clear_controls", action + "-clear"),
        ):
            _one_effect(native, commands, seq, effect, eid)
        if i in (2, 3):
            lateral.append(after[1] - before[1])
    require(sum(lateral) < -0.5 if arm == "on" else sum(lateral) > 0.5,
            "native World did not use reported ON/OFF lateral direction")
    # Native can attest different paths, not serialized retained Memory content.
    reported_memory = ground.get("b1_evidence")
    require(type(reported_memory) is dict and reported_memory.get("session_id") == session
            and reported_memory.get("retention_enabled") is (arm == "on")
            and reported_memory.get("blocked_action_count") == 1
            and reported_memory.get("retained_observations") == (1 if arm == "on" else 0)
            and reported_memory.get("reused_for_lateral_choice") == (1 if arm == "on" else 0)
            and reported_memory.get("lateral_choice_count") == 1
            and reported_memory.get("alternative_progressed") == 2
            and reported_memory.get("learning_qualified") is False
            and reported_memory.get("habit_created") is False,
            "missing expected unqualified S-reported B1 retention trace")
    choice = ground.get("b1_decisions")
    require(type(choice) is list and len(choice) == 6
            and [x.get("waypoint_id") for x in choice][2:4]
            == ["b1-local-lateral", "b1-local-lateral"]
            and choice[2].get("retained_memory_count") == (1 if arm == "on" else 0)
            and choice[2].get("source_seq") > moves[1]["after_seq"],
            "no reported source-ordered lateral choice after BLOCKED")
    pickup = ground.get("pickup")
    require(type(pickup) is dict and pickup.get("source_session_id") == session
            and pickup.get("cooked_beef_inventory_delta") == 1
            and pickup.get("item_entity_id") == ground.get("item_entity_id")
            and pickup.get("strict_player_collect_causality") == "UNKNOWN",
            "no honest source-consistent pickup limitation")
    start, picked = (probe(native, pickup[key]) for key in
                     ("source_before_seq", "source_after_seq"))
    item = pickup["item_entity_id"]
    require(count_food(start) == 0 and count_food(picked) == 1
            and any(v.get("id") == item and v.get("name") == "item"
                    for v in start.get("nearby_entities", []))
            and not any(v.get("id") == item for v in picked.get("nearby_entities", [])),
            "native item disappearance and inventory rise not correlated")
    eating = r.get("eating")
    require(type(eating) is dict and eating.get("action_state") == "outcome"
            and eating.get("source_session") == session
            and eating.get("virtual_energy_credit") == 0,
            "S51 EAT not an uncredited original")
    native_eat = eating.get("native_outcome")
    require(type(native_eat) is dict and native_eat.get("session_id") == session
            and native_eat.get("count_before") == 1 and native_eat.get("count_after") == 0
            and native_eat.get("food_before") == 12 and native_eat.get("food_after") == 20,
            "EAT report inconsistent")
    appetizer = eating.get("appetite_trace")
    require(type(appetizer) is list and appetizer and appetizer[-1].get("paper_native_l0_kind") == "EAT",
            "missing native-source L0 EAT candidate")
    first_eat = probe(native, appetizer[-1].get("source_seq"))
    after_eat = probe(native, native_eat.get("after_probe_seq"))
    require(count_food(first_eat) == 1 and first_eat.get("food") == 12
            and count_food(after_eat) == 0 and after_eat.get("food") == 20,
            "native after EAT observation not observed")
    for effect, suffix in (("equip_item", "-equip"), ("consume_held", "-consume")):
        action = eating["action_id"] + suffix
        seqs = [v["seq"] for v in native if v.get("type") == "effect_result"
                and v.get("effect") == effect and v.get("action_id") == action]
        require(len(seqs) == 1 and first_eat != after_eat, "missing native EAT child")
        _one_effect(native, commands, seqs[0], effect, action)
        require(appetizer[-1]["source_seq"] < seqs[0] < native_eat["after_probe_seq"],
                "nonsequential governed S51 effect")
    meters = physics(files["paper_server.log"], r.get("paper_native_diagnostics"))
    spawn = native[1].get("snapshot", {}).get("position")
    require(type(spawn) is dict, "missing original initial spawn")
    return {
        "arm": arm.upper(), "source_session": session, "source_head_pin": S_PRODUCER_HEAD,
        "world_snapshot_sha256": pinned["initial_world_level.dat"],
        "original_spawn": spawn, "native_rows": len(native),
        "native_stop_ack_seq": native[-2]["seq"],
        "native_connection_end_seq": native[-1]["seq"],
        "governed_s50_move_count": len(moves), "native_blocked_count": 1,
        "native_lateral_direction": "MINUS_Z" if arm == "on" else "PLUS_Z",
        "source_consistent_steak_pickup": True,
        "strict_pickup_causality": "UNKNOWN",
        "native_governed_eat": True,
        "reported_retained_memory_count": reported_memory["retained_observations"],
        "retained_memory_original_bytes_present": False,
        **meters,
    }


def audit_zip(path: Path) -> dict[str, Any]:
    blobs = _read_zip(path)
    reports = {}
    for arm in ("on", "off"):
        p = original_prefix(arm)
        reports[arm] = review_arm(arm, {name: blobs[p + name] for name in PARTS})
    require(reports["on"]["source_session"] != reports["off"]["source_session"],
            "two arms reused a session")
    # The actual historical physical starting coordinates and World originals differ.
    identical = (reports["on"]["world_snapshot_sha256"]
                 == reports["off"]["world_snapshot_sha256"]
                 and reports["on"]["original_spawn"] == reports["off"]["original_spawn"])
    return {
        "classification": "RSEE_PAPER_B1_HISTORICAL_DEV_ORIGINAL_REVIEW_ONLY",
        "s_pinned_producer_head": S_PRODUCER_HEAD,
        "historical_action_run": PAPER_ARTIFACT_RUN,
        "historical_artifact_id": PAPER_ARTIFACT_ID,
        "zip_sha256": PAPER_ARTIFACT_ZIP_SHA256,
        "arms": reports,
        "world_and_spawn_matched": identical,
        "comparative_memory_causal_effect_qualified": False,
        "original_retained_memory_bytes_qualified": False,
        "strict_item_pickup_causality_qualified": False,
        "historical_physical_host_independently_attested_here": False,
        "new_source_r_engineering_qualified": False,
        "v_science_admitted": False,
        "production_go": False,
        "physical_world_launches_by_reviewer": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-zip", type=Path)
    args = parser.parse_args(argv)
    if args.original_zip is None:
        print(json.dumps({"classification": "PAPER_B1_R_REVIEW_NOT_RUN_NO_ORIGINAL_ZIP",
                          "physical_world_launches_by_reviewer": 0,
                          "new_source_r_engineering_qualified": False}))
        return 0
    try:
        result = audit_zip(args.original_zip)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        result = {"classification": "PAPER_B1_R_HISTORICAL_ORIGINAL_REVIEW_BLOCKED",
                  "reason": f"{type(exc).__name__}: {exc}",
                  "physical_world_launches_by_reviewer": 0,
                  "new_source_r_engineering_qualified": False, "v_science_admitted": False}
    print(json.dumps(result, sort_keys=True))
    return 2 if result["classification"].endswith("BLOCKED") else 0


if __name__ == "__main__":
    raise SystemExit(main())