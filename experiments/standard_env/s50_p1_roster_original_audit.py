"""R independent original-byte S/P1 entity roster review.

Reconstruct *every sampled loaded entity* using UUID/type/chunk originals.
This is independent of S validators and never authorizes whole-tick WAIT,
full entity lifecycle, or physical Fatigue recovery.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from pathlib import Path

from experiments.standard_env import s50_p1_wait_original_audit as old

ENTITY_CAP = 512
CLASS = "R_P1_ENTITY_UUID_TYPE_ROSTER_ORIGINAL_REVIEW_ONLY_NOT_SOLO"


def canonical_uuid(raw: str) -> str:
    try:
        candidate = str(uuid.UUID(raw))
    except (TypeError, ValueError, AttributeError) as exc:
        raise old.WaitOriginalRejected("bad native UUID") from exc
    old.need(candidate == raw, "noncanonical native UUID")
    return candidate


def review(root: Path, *, run: int, head: str, artifact: int, jar: str) -> dict:
    """A new-World source pin is always required; old historical default excluded."""
    old.need(type(run) is int and run > 0
             and type(artifact) is int and artifact > 0
             and re.fullmatch("[a-f0-9]{40}", head) is not None
             and re.fullmatch("[a-f0-9]{64}", jar) is not None,
             "missing fixed original source/run/JAR identity")
    receipt = old.review(
        root, source_run=run, source_head=head,
        source_artifact=artifact, expected_jar=jar,
    )
    report = old.obj(old.original(root, "m02_report.json"))
    candidate = report.get("movement", {}).get("p1_wait_candidate", {})
    source = old.original(root, "paper_server.log")
    scopes = old.paper_rows(source, "S50_DEV_WAIT_SCOPE ")
    entity_lines = old.paper_rows(source, "S50_DEV_WAIT_ENTITY ")
    snapshot = old.paper_rows(source, "S50_DEV_WAIT_TICK ")
    old.need(len(scopes) == len(snapshot) == 8,
             "source scope missing/duplicated")
    start, end = receipt["observed_world_ticks"]
    old.need(end == start + 7, "unbounded tick sampling")
    marker = receipt["source_action"] + "-" + receipt["native_session"]
    world = receipt["original_world_uuid"]
    cursor = 0
    all_types = []
    native_hashes = []
    fingerprints = []
    other_agent_ticks = []
    same_world_other_ticks = []
    world_type_snapshots = []
    for ix, (scope, tick) in enumerate(zip(scopes, snapshot), 1):
        clock = start + ix - 1
        old.need(scope.get("marker_id") == marker
                 and scope.get("world") == world
                 and old.integer(scope, "tick") == clock
                 and old.integer(scope, "index") == ix
                 and tick.get("marker_id") == marker
                 and tick.get("world") == world
                 and old.integer(tick, "tick") == clock
                 and old.integer(tick, "index") == ix
                 and scope.get("coverage") == "LOADED_CHUNK_SAMPLER_ONLY"
                 and scope.get("client_held_controls") == "NOT_OBSERVED"
                 and scope.get("entity_lifecycle") == "NOT_ATTESTED",
                 "source scope contradicts original Action/World/tick")
        subject = canonical_uuid(scope.get("subject_uuid"))
        count = old.integer(scope, "loaded_entities")
        other_count = old.integer(scope, "other_loaded_entities")
        other_players = old.integer(scope, "other_online_players")
        old.need(1 <= count <= ENTITY_CAP and other_count + 1 == count
                 and other_players <= other_count,
                 "unexpected source entity/subject census")
        roster = []
        seen = set()
        types = Counter()
        world_types = Counter()
        local_others = 0
        for number in range(1, count + 1):
            old.need(cursor < len(entity_lines), "truncated source entity list")
            row = entity_lines[cursor]
            cursor += 1
            old.need(row.get("marker_id") == marker
                     and row.get("world") == world
                     and old.integer(row, "tick") == clock
                     and old.integer(row, "index") == ix
                     and old.integer(row, "roster_index") == number,
                     "reordered or foreign entity original")
            entity_world = canonical_uuid(row.get("entity_world"))
            entity_uuid = canonical_uuid(row.get("uuid"))
            category = row.get("type", "")
            old.need(re.fullmatch("[A-Z0-9_]{2,80}", category) is not None,
                     "invalid original Bukkit entity type")
            try:
                chunk_x = int(row["chunk_x"])
                chunk_z = int(row["chunk_z"])
            except (KeyError, ValueError, TypeError) as exc:
                raise old.WaitOriginalRejected("bad entity chunk coordinate") from exc
            old.need(entity_uuid not in seen and abs(chunk_x) < 30_000_000
                     and abs(chunk_z) < 30_000_000,
                     "duplicated entity UUID or unbounded World locator")
            seen.add(entity_uuid)
            if entity_uuid == subject:
                old.need(category == "PLAYER", "source Self mapped to non-player")
            roster.append(
                f"{entity_world}:{chunk_x}:{chunk_z}:{entity_uuid}:{category}"
            )
            types[category] += 1
            world_types[(entity_world, category)] += 1
            if entity_world == world and entity_uuid != subject:
                local_others += 1
        old.need(subject in seen and len(seen) == count
                 and roster == sorted(roster),
                 "original roster count/order/subject not established")
        digest = hashlib.sha256(
            "".join(item + "\n" for item in roster).encode("utf-8")
        ).hexdigest()
        old.need(digest == scope.get("census_sha256"),
                 "independent native entity digest mismatch")
        native_hashes.append(digest)
        all_types.append(dict(sorted(types.items())))
        fingerprints.append(tuple(roster))
        if other_count:
            other_agent_ticks.append(clock)
    old.need(cursor == len(entity_lines), "extra source entity rows")
    saved = candidate.get("source_scope") or {}
    old.need(saved.get("source_entity_rows") == len(entity_lines)
             and saved.get("native_roster_digests") == native_hashes
             and saved.get("first_sample_entity_types") == all_types[0]
             and saved.get("wait_ticks_admitted") == 0
             and saved.get("p1_fatigue_recovered") == 0
             and saved.get("independent_R_qualification") is False,
             "producer source tally diverges from original roster")
    return {
        "classification": CLASS,
        "source_run": run,
        "source_head": head,
        "source_artifact": artifact,
        "jar_sha256": jar,
        "world": world,
        "action": receipt["source_action"],
        "first_tick": start,
        "last_tick": end,
        "native_roster_rows": len(entity_lines),
        "sampled_type_histogram_per_tick": all_types,
        "native_roster_digest_per_tick": native_hashes,
        "roster_same_across_8_samples": all(x == fingerprints[0] for x in fingerprints),
        "other_loaded_entity_presence_ticks": other_agent_ticks,
        "individual_lifecycle_events": "NOT_ATTESTED",
        "unloaded_chunk_lifecycle": "NOT_ATTESTED",
        "full_tick_input_absence": "NOT_ATTESTED",
        "native_held_motor_controls": "NOT_ATTESTED",
        "full_server_actor_solo": "NOT_ATTESTED",
        "s_true_wait_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "r_engineering_qualified": False,
        "science_go": False,
    }
