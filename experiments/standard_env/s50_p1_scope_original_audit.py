"""Independent R audit of S post-S50 loaded-chunk and native activity samples.

Extends R's original-byte native Action/STOP/WAIT reviewer, NOT S's parser.
Neither sample census nor no observed event proves full World tick or SOLO.
"""
from __future__ import annotations

import re
from pathlib import Path

from experiments.standard_env import s50_p1_wait_original_audit as prior

SOURCE_RUN = 38976662458
SOURCE_ARTIFACT = 12079520551
SOURCE_HEAD = "3f9e79bfb00f171672c661b024b27a0c18729154"
JAR = "36640f5ff0684bbf361e5f6a2885547dfd5e0d500e78091bb6d8216c2aa932ae"
COUNTERS = (
    "movement_events", "teleport_events", "velocity_events", "damage_events",
    "interact_events", "combat_events", "swing_events",
)
LIMITS = {
    "loaded_worlds": 16, "loaded_chunks": 4096,
    "loaded_entities": 32768, "other_loaded_entities": 32768,
    "other_online_players": 2048,
}
CLASS = "R_P1_LOADED_CHUNK_AND_ACTIVITY_SAMPLED_ONLY_NOT_SOLO"


def review(root: Path) -> dict:
    base = prior.review(root, source_run=SOURCE_RUN, source_head=SOURCE_HEAD,
                        source_artifact=SOURCE_ARTIFACT, expected_jar=JAR)
    report = prior.obj(prior.original(root, "m02_report.json"))
    claimed = report.get("movement", {}).get("p1_wait_candidate", {})
    paper = prior.original(root, "paper_server.log")
    scopes = prior.paper_rows(paper, "S50_DEV_WAIT_SCOPE ")
    snapshot = prior.paper_rows(paper, "S50_DEV_WAIT_TICK ")
    prior.need(len(scopes) == len(snapshot) == 8,
               "scope source missing or duplicated")
    begin, end = base["observed_world_ticks"]
    cumulative = []
    other_entities = []
    other_players = []
    changing = []
    previous = None
    for index, (row, tickrow) in enumerate(zip(scopes, snapshot), 1):
        now = begin + index - 1
        prior.need(
            row.get("marker_id") == base["source_action"] + "-"
            + base["native_session"]
            and row.get("world") == base["original_world_uuid"]
            and prior.integer(row, "tick") == now
            and prior.integer(row, "index") == index
            and row.get("coverage") == "LOADED_CHUNK_SAMPLER_ONLY"
            and row.get("client_held_controls") == "NOT_OBSERVED"
            and row.get("entity_lifecycle") == "NOT_ATTESTED"
            and tickrow.get("marker_id") == base["source_action"]
            + "-" + base["native_session"]
            and tickrow.get("world") == base["original_world_uuid"]
            and prior.integer(tickrow, "tick") == now
            and prior.integer(tickrow, "index") == index,
            "foreign scope/World/Action or claimed unsupported source coverage"
        )
        digest = row.get("census_sha256", "")
        prior.need(re.fullmatch("[a-f0-9]{64}", digest) is not None,
                   "native census digest malformed")
        profile = {k: prior.integer(row, k) for k in LIMITS}
        prior.need(
            all(profile[k] <= v for k, v in LIMITS.items())
            and profile["loaded_worlds"] >= 1
            and profile["loaded_chunks"] >= 1
            and profile["other_loaded_entities"] <= profile["loaded_entities"]
            and profile["other_online_players"] <= profile["loaded_entities"],
            "impossible sampled World census"
        )
        numbers = tuple(prior.integer(row, k) for k in COUNTERS)
        prior.need(numbers[1] <= numbers[0]
                   and numbers[5] == prior.integer(tickrow, "combat_events")
                   and numbers[6] == prior.integer(tickrow, "swing_events"),
                   "invalid native motor/attack source correspondence")
        if previous is not None:
            prior.need(all(a >= b for a, b in zip(numbers, previous)),
                       "regressing event counter")
            if numbers != previous:
                changing.append(now)
        previous = numbers
        cumulative.append(profile)
        if profile["other_loaded_entities"] > 0:
            other_entities.append(now)
        if profile["other_online_players"] > 0:
            other_players.append(now)
    # The R parser recalculates from all original rows; producer summary cannot
    # replace originals nor grant WAIT with a forged positive source receipt.
    producer = claimed.get("source_scope") or {}
    prior.need(producer.get("classification")
               == "S_P1_LOADED_CHUNK_CENSUS_AND_EVENTS_SAMPLE_ONLY"
               and producer.get("source_scope_rows") == 8
               and producer.get("first_world_tick") == begin
               and producer.get("last_world_tick") == end
               and producer.get("activity_counter_changed_after_first_sampler")
               == changing
               and producer.get("other_loaded_entities_seen_ticks")
               == other_entities
               and producer.get("other_online_players_seen_ticks")
               == other_players
               and producer.get("wait_ticks_admitted") == 0
               and producer.get("p1_fatigue_recovered") == 0
               and producer.get("independent_R_qualification") is False,
               "original producer scope summary contradicts native rows")
    return {
        "classification": CLASS,
        "source_run": SOURCE_RUN,
        "source_artifact": SOURCE_ARTIFACT,
        "original_paper_sha256": base["original_paper_sha256"],
        "source_original_world": base["original_world_uuid"],
        "first_tick": begin,
        "last_tick": end,
        "independently_checked_scope_rows": 8,
        "observed_stationary_samples": base["sampled_stationary_count"],
        "other_loaded_entities_seen_ticks": other_entities,
        "other_online_players_seen_ticks": other_players,
        "activity_counters_changed_ticks": changing,
        "scope_limited_to_loaded_chunks_per_sampler": True,
        "global_world_lifecycle": "NOT_ATTESTED",
        "held_controls_between_samples": "NOT_ATTESTED",
        "unobserved_tick_activity": "NOT_ATTESTED",
        "true_full_tick_wait_proven": False,
        "global_solo_proven": False,
        "p1_wait_interval_ref_valid": False,
        "p1_wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "engineering_qualification": False,
        "science_go": False,
    }
