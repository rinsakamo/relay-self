"""Independent R source-byte replay of a past S/P1 Paper WAIT candidate.

Read-only. Eight stationary sampler callbacks cannot attest whole-tick
inactivity, no held motor input, full solo-census, or P1 fatigue recovery.
No S parser import, physical World launch or R qualification grant.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

EXPECTED_JAR = "714052143fb88b10b83d4b9ab72cbe7c5c6b5066c590e330141e6d06f6748922"
EXPECTED_PAPER = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
RUN_ID = 38921173953
ARTIFACT_ID = 12055285327
S_HEAD = "62133211312e85a270294bec6f047e48d80aa680"
CLASS = "R_S50_P1_SAMPLED_STATIONARY_ORIGINAL_REVIEW_ONLY"
ORIGINALS = (
    "paper_server.log", "original_native.jsonl",
    "owner_commands.jsonl", "s50_action_original.jsonl",
)


class WaitOriginalRejected(ValueError):
    """Source loss, mismatch, changed/foreign original, or impossible timeline."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise WaitOriginalRejected(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def original(root: Path, name: str) -> bytes:
    file = root / name
    need(file.is_file() and not file.is_symlink(), "missing/aliased original " + name)
    raw = file.read_bytes()
    need(0 < len(raw) < 20_000_000, "invalid original bytes " + name)
    return raw


def obj(raw: bytes):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, "duplicate original JSON key")
            out[key] = value
        return out

    def invalid_constant(value):
        raise WaitOriginalRejected("nonfinite original JSON: " + value)

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise WaitOriginalRejected("invalid original JSON") from exc


def native_rows(raw: bytes):
    try:
        return [obj(line.encode("utf-8")) for line in
                raw.decode("utf-8").splitlines() if line]
    except UnicodeError as exc:
        raise WaitOriginalRejected("non-UTF8 native original") from exc


def paper_rows(raw: bytes, prefix: str):
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise WaitOriginalRejected("non-UTF8 Paper original") from exc
    results = []
    for line in lines:
        if prefix not in line:
            continue
        tokens = [x.split("=", 1) for x in line.split(prefix, 1)[1].split()]
        need(all(len(x) == 2 and x[0] for x in tokens), "bad Paper source field")
        row = dict(tokens)
        need(len(row) == len(tokens), "duplicate Paper field")
        results.append(row)
    return results


def integer(row, name):
    try:
        value = int(row[name])
    except (KeyError, TypeError, ValueError) as exc:
        raise WaitOriginalRejected("missing native counter " + name) from exc
    need(value >= 0 and str(value) == row[name], "bad native counter " + name)
    return value


def number(row, name):
    try:
        value = float(row[name])
    except (KeyError, TypeError, ValueError) as exc:
        raise WaitOriginalRejected("missing native number " + name) from exc
    need(math.isfinite(value), "nonfinite native number " + name)
    return value


def pos(row, prefix=""):
    return tuple(number(row, prefix + name) for name in ("x", "y", "z"))


def review(root: Path):
    """Independent original values; no SourceBoundTick(WAIT) is produced."""
    need(root.is_absolute() and root.is_dir() and not root.is_symlink(),
         "untrusted original root")
    report = obj(original(root, "m02_report.json"))
    need(type(report) is dict and report.get("status") == "PASS"
         and report.get("owner_status") == "PASS"
         and report.get("v7_arm") == "BASE_ON"
         and report.get("v7_seed") == 61021
         and report.get("qualified") is False
         and report.get("science_go") is False
         and report.get("v7_tick_meter_dev") is True
         and report.get("v7_server_clock_calibration_dev") is True
         and report.get("plugin_sha256") == EXPECTED_JAR
         and report.get("paper_sha256") == EXPECTED_PAPER
         and report.get("java_exit") == 0
         and report.get("node_exit") == 0
         and report.get("port_released_after_shutdown") is True,
         "not the S/P1 original source run")
    raw = {name: original(root, name) for name in ORIGINALS}
    hashes = report.get("evidence_hashes")
    need(type(hashes) is dict, "no original SHA index")
    for name, data in raw.items():
        need(sha(data) == hashes.get(name), "original source hash changed " + name)
    need(sha(original(root, "relay-metabolism-paper-dev.jar")) == EXPECTED_JAR,
         "wrong WAIT instrumentation JAR bytes")
    world = original(root, "initial_world_level.dat")
    world_ref = report.get("initial_world_receipt") or {}
    need(sha(world) == world_ref.get("sha256")
         and len(world) == world_ref.get("size_bytes"),
         "original World NBT hash/size mismatch")
    move = report.get("movement") or {}
    session = report.get("source_session_id")
    aid = move.get("action_id")
    need(type(aid) is str and type(session) is str
         and move.get("source_session") == session
         and move.get("action_state") == "outcome"
         and move.get("v7_p1_wait_evidence_dev") is True
         and move.get("v7_tick_meter_dev") is True,
         "S50 terminal Action/window not correlated")
    marker = aid + "-" + session
    need(move.get("v7_phase_marker_id") == marker, "foreign session marker")
    journal = native_rows(raw["s50_action_original.jsonl"])
    need(len(journal) == 2 and [r.get("state") for r in journal]
         == ["issued", "outcome"] and all(
             r.get("action_id") == aid and r.get("session_id") == session
             for r in journal), "S50 terminal original absent")
    native = native_rows(raw["original_native.jsonl"])
    commands = native_rows(raw["owner_commands.jsonl"])
    need(len(native) > 5 and [r.get("seq") for r in native]
         == list(range(len(native))) and all(
             r.get("session_id") == session for r in native)
         and len([r for r in native if r.get("type") == "shutdown_ack"]) == 1
         and len([r for r in native if r.get("type") == "connection_end"]) == 1,
         "native stream/STOP incomplete")
    for ref, effect in ((aid + "-look", "look"), (aid, "set_control"),
                        (aid + "-clear", "clear_controls")):
        need(len([r for r in commands if r.get("action_id") == ref
                  and r.get("effect") == effect]) == 1
             and len([r for r in native if r.get("type") == "effect_result"
                      and r.get("action_id") == ref
                      and r.get("effect") == effect
                      and r.get("result") == "applied"]) == 1,
             "original S50 effect/ACK missing")
    paper = raw["paper_server.log"]
    phases = paper_rows(paper, "M02_DEV_S50_PHASE ")
    need(len(phases) == 4 and [r.get("phase") for r in phases]
         == ["PRE_FORWARD", "POST_FORWARD", "PRE_CLEAR", "POST_CLEAR"],
         "source phase order incomplete")
    uuids = {r.get("world") for r in phases}
    need(len(uuids) == 1 and all(r.get("marker_id") == marker for r in phases),
         "foreign source phase World")
    uuid = phases[0]["world"]
    phase_times = [integer(r, "world_full_time") for r in phases]
    need(phase_times == sorted(phase_times), "regressing source phase World tick")
    begin = paper_rows(paper, "S50_DEV_WAIT_BEGIN ")
    samples = paper_rows(paper, "S50_DEV_WAIT_TICK ")
    need(len(begin) == 1 and len(samples) == 8,
         "missing/duplicate/partial WAIT observation")
    start = begin[0]
    t0 = integer(start, "tick")
    need(start.get("marker_id") == marker
         and start.get("world") == uuid and t0 > phase_times[-1],
         "WAIT observation precedes S50 terminal source phase")
    prior = pos(start)
    counters = (integer(start, "packets"), number(start, "blocks"),
                number(start, "tick_meter_blocks"),
                integer(start, "combat_events"),
                integer(start, "swing_events"),
                integer(start, "basal_ticks"))
    active = []
    for i, row in enumerate(samples, 1):
        need(row.get("marker_id") == marker and row.get("world") == uuid
             and integer(row, "index") == i and integer(row, "tick") == t0 + i
             and pos(row, "from_") == prior,
             "foreign/nonconsecutive WAIT sample original")
        current = pos(row)
        counted = (integer(row, "motion_packets"), number(row, "motion_blocks"),
                   number(row, "tick_meter_blocks"),
                   integer(row, "combat_events"), integer(row, "swing_events"),
                   integer(row, "basal_ticks"))
        need(all(x >= y for x, y in zip(counted[:5], counters[:5]))
             and counted[5] == counters[5] + 1,
             "inconsistent native motion/combat/BASAL time")
        still = (current == prior and counted[:5] == counters[:5]
                 and all(row.get(k) == "false" for k in
                         ("sprint", "sneak", "swimming")))
        if not still:
            active.append(t0 + i)
        prior, counters = current, counted
    basal = paper_rows(paper, "M02_DEV_BASAL_WRITE ")
    need(len(basal) >= counters[5] and all(
         integer(r, "id") == i for i, r in enumerate(basal[:counters[5]], 1)),
         "native BASAL source progression missing")
    candidate = move.get("p1_wait_candidate") or {}
    need(candidate.get("first_world_tick") == t0 + 1
         and candidate.get("last_world_tick") == t0 + 8
         and candidate.get("wait_ticks_admitted") == 0
         and candidate.get("p1_fatigue_recovered") == 0,
         "producer asserted unqualified WAIT/recovery")
    return {
        "classification": CLASS,
        "source_run": RUN_ID,
        "source_head": S_HEAD,
        "source_artifact": ARTIFACT_ID,
        "original_paper_sha256": sha(paper),
        "original_world_uuid": uuid,
        "native_session": session,
        "source_action": aid,
        "observed_world_ticks": [t0 + 1, t0 + 8],
        "sampled_stationary_count": 8 - len(active),
        "sampled_active_ticks": active,
        "native_basal_continues": True,
        "independent_r_original_byte_review": True,
        "whole_tick_motor_combat_inactivity": "NOT_ATTESTED",
        "held_client_control_absence": "NOT_ATTESTED",
        "global_solo_entity_census": "NOT_ATTESTED",
        "p1_wait_interval_ref_authoritative": False,
        "p1_wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "new_wait_jar_qualified": False,
        "science_go": False,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="R read-only P1 WAIT source audit")
    parser.add_argument("original_root", type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args.original_root), sort_keys=True))
