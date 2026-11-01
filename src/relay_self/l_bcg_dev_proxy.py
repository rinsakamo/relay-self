"""H6 isolated DEV proxy readback: provisional Paper samples are NOT training.

No MotorOutcome, MotorSourceAdmission, real Goal, Action or L1 authority here.
Original digest checks are report/audit consistency, not independent TCP,
physical effective clear, or scientific validation.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from relay_self.habit_shadow import MAX_SAMPLES


class DevProxyRejected(ValueError):
    """Original readback missing, inconsistent, aliased or over-qualified."""


@dataclass(frozen=True, slots=True)
class DevProxyEpisode:
    session_id: str
    paper_world_id: str
    action_id: str
    action_before_native_seq: int
    action_after_native_seq: int
    next_native_seq: int
    before_minecraft_food: float
    before_s42_threat_distance_m: float
    sampled_input_off_ticks: tuple[int, ...]
    sampled_input_off_motion_m: float
    sampled_any_motion: bool
    s16_original_sha256: str
    s7_prefix_sha256: str
    paper_original_sha256: str
    classification: str = "DEV_SAMPLED_LAST_REPORTED_INPUT_OFF_PROXY_ONLY"
    physical_effective_clear_attested: bool = False
    goal_attested: bool = False
    physical_training_eligible: bool = False
    learning_commits: int = 0
    extra_actions: int = 0


@dataclass(frozen=True, slots=True)
class DevProxyComparison:
    distinct_provisional_worlds: int
    cheap_last_world_motion: str
    cheap_any_world_motion: str
    learned_l1_attention: str = "DEFER_UNKNOWN"
    learned_policy_qualified: bool = False
    admitted_training_worlds: int = 0
    action_issues: int = 0
    learning_commits: int = 0
    reason: str = "FULL_CONDITION_AND_PHYSICAL_CLEAR_NOT_ATTESTED"


def _require(condition: bool, why: str) -> None:
    if not condition:
        raise DevProxyRejected(why)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _num(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _source_rows(raw: bytes, *, session: str) -> dict[int, dict[str, object]]:
    _require(type(raw) is bytes and 0 < len(raw) <= 2_000_000, "S7 prefix byte limit")
    rows: dict[int, dict[str, object]] = {}
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise DevProxyRejected("invalid S7 source row") from exc
        _require(isinstance(item, dict) and item.get("session_id") == session, "foreign S7 session")
        seq = item.get("seq")
        _require(type(seq) is int and seq >= 0 and seq not in rows, "duplicate or invalid S7 sequence")
        rows[seq] = item
    return rows


def _read_json(raw: bytes, name: str) -> dict[str, object]:
    _require(type(raw) is bytes and 0 < len(raw) <= 2_000_000, name + " byte bound")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise DevProxyRejected(name + " malformed") from exc
    _require(isinstance(value, dict), name + " object required")
    return value


def read_h6_provisional_world(
    *, host_report_original: bytes, independent_audit_original: bytes,
    s16_original: bytes, s7_received_prefix_original: bytes,
    paper_server_original: bytes,
    audit_classification: str = "DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
) -> DevProxyEpisode:
    """Join ORIGINAL bytes and preserved audit, without minting physical admission.

    The pre-action food and threat are kept distinct from the NEXT epoch cues.
    The Paper label is sampled motion with *last reported* input off, not
    motion after independently attested effective input clear.
    """
    report = _read_json(host_report_original, "host report")
    audit = _read_json(independent_audit_original, "independent audit")
    try:
        hashes = audit["original_sha256"]
        l22 = audit["original"]["route_b"]["l22"]
        l23 = audit["original"]["route_b"]["l23"]
        audit_window = audit["original"]["route_b"]["live_window"]
        action = report["actual_native_actions"][0]
        evidence = action["execution_evidence"]
        before = evidence["before_observation"]
        after = evidence["after_observation"]
        s16 = _read_json(s16_original, "S16 original")
        decisions = report["decisions"]
        window = report["live_next_epoch"]["window"]
        shadow = report["l_bcg_shadow"]
        session = report["session_id"]
        world = window["paper_world_uuid"]
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        raise DevProxyRejected("missing typed original host/audit fields") from exc
    _require(type(session) is str and bool(session) and type(world) is str and bool(world),
             "missing native/World identity")
    expected = {
        "s49-report.json": (host_report_original, hashes.get("s49-report.json")),
        "capture/l18_s16_terminal_original.jsonl": (
            s16_original, hashes.get("capture/l18_s16_terminal_original.jsonl")
        ),
        "capture/pre-next-l0-prefix/native_bridge_received_original.jsonl": (
            s7_received_prefix_original,
            hashes.get("capture/pre-next-l0-prefix/native_bridge_received_original.jsonl"),
        ),
        "server.log": (paper_server_original, hashes.get("server.log")),
    }
    _require(all(type(v) is str and _sha(raw) == v for raw, v in expected.values()),
             "original byte digest mismatch")
    _require(
        audit_classification in (
            "DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
            "DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
        )
        and audit.get("classification") == audit_classification
        and audit.get("qualified_training_worlds") == 0
        and audit.get("effective_clear") == "NOT_ATTESTED"
        and audit.get("goal") == "UNDETERMINED"
        and audit.get("qualification") == "NO_GO"
        and audit.get("science") == "NOT_RUN"
        and audit.get("worlds") == 1 and audit.get("actions") == 1
        and audit.get("retries") == 0 and audit.get("model_calls") == 0,
        "missing per-World DEV audit ceiling",
    )
    _require(
        report.get("status") == "PASS" and report.get("stage") == "CLOSED"
        and report.get("node_exit") == report.get("server_exit") == 0
        and report.get("real_model_calls") == 0
        and report.get("learning_in_world") is False
        and len(report["actual_native_actions"]) == 1
        and len(decisions) == 3
        and [d["selected"] for d in decisions] == ["WAIT", "MOVE_AWAY", "WAIT"]
        and [d["issued"] for d in decisions] == [False, True, False]
        and shadow.get("advice") == "DEFER_UNKNOWN"
        and shadow.get("conditional") is None
        and shadow.get("used_physical_training_worlds") == 0
        and shadow.get("action_authority") is False
        and shadow.get("goal_success_attested") is False
        and not any(shadow.get(k) != 0 for k in (
            "action_issues", "extra_native_reads", "learning_updates", "habit_grants"
        )),
        "S49 original or shadow ceiling changed",
    )
    move = decisions[1]
    _require(
        evidence.get("action_id") == action.get("action") == s16.get("action_id")
        == l22.get("action_id") == l23.get("action_id") == window.get("action_id")
        and action.get("terminal") == "outcome"
        and evidence.get("status") == "executed"
        and s16.get("session_id") == l22.get("session_id") == l23.get("session_id")
        == session == window.get("session_id")
        and s16.get("disposition") == "outcome"
        and s16.get("source_status") == "executed"
        and s16.get("source_revision") == 0
        and before.get("seq") == s16.get("before_seq")
        and after.get("seq") == s16.get("after_seq")
        == l22.get("after_seq")
        and before.get("seq") > move["probe_seq"]
        and decisions[2]["probe_seq"] > after.get("seq")
        and l23.get("paper_world") == world
        and window.get("marker_id") == l23.get("marker_id")
        and window.get("provisional") is True
        and window.get("final_source_verified") is False
        and window.get("physical_stability_attested") is False
        and window.get("effective_clear_tick") == "NOT_ATTESTED"
        and window.get("full_tick_input_idle") is False
        and window.get("goal_admitted") is False,
        "foreign or promoted Action/Paper source",
    )
    _require(
        _sha(s16_original) == l22.get("s16_original_sha256") == l23.get("s16_original_sha256")
        and _sha(s7_received_prefix_original) == l22.get("received_sha256")
        == l23.get("s7_received_sha256")
        and _sha(paper_server_original) == l23.get("paper_original_sha256")
        and window == audit_window,
        "Paper/S7/S16 original lineage mismatch",
    )
    rows = _source_rows(s7_received_prefix_original, session=session)
    for observation in (before, after):
        seq = observation["seq"]
        src = rows.get(seq, {})
        _require(
            src.get("type") == "observation"
            and src.get("kind") == "probe"
            and src.get("request_id") == observation.get("request_id")
            and src.get("snapshot", {}).get("food")
               == observation.get("snapshot", {}).get("food")
            and src.get("snapshot", {}).get("position")
               == observation.get("snapshot", {}).get("position"),
            "pre/post action native evidence not present in S7 prefix",
        )
    prior = rows.get(move["probe_seq"], {})
    _require(
        prior.get("type") == "observation"
        and prior.get("request_id") == f"s49-actual:{session}:event-{move['event_seq']}",
        "pre-decision source missing from original S7",
    )
    pre_entities = before["snapshot"]["nearby_entities"]
    matched = [e for e in pre_entities if e.get("entity_id") == move.get("entity_id")]
    prior_entities = prior.get("snapshot", {}).get("nearby_entities", [])
    _require(
        len(matched) == 1
        and matched[0].get("name") == "zombie"
        and any(e.get("id") == move["entity_id"] for e in prior_entities)
        and _num(matched[0].get("distance"))
        and _num(move.get("distance_m"))
        and abs(matched[0]["distance"] - move["distance_m"]) <= 1e-9
        and _num(before["snapshot"].get("food")),
        "original pre-action observed threat/food missing",
    )
    ticks = window["ticks"]
    _require(
        isinstance(ticks, list) and len(ticks) == l23["paper_sample_count"] == 8
        and ticks[0]["world_tick"] == l23["paper_first_tick"]
        and ticks[-1]["world_tick"] == l23["paper_last_tick"],
        "incomplete Paper callback window",
    )
    off_motion = 0.0
    off_ticks: list[int] = []
    active_ticks: list[int] = []
    for i, tick in enumerate(ticks):
        _require(
            type(tick.get("world_tick")) is int
            and tick["world_tick"] == ticks[0]["world_tick"] + i
            and type(tick.get("last_reported_input_active")) is bool
            and _num(tick.get("displacement_m"))
            and tick["displacement_m"] >= 0,
            "invalid sampled Paper tick",
        )
        if not tick["last_reported_input_active"]:
            off_ticks.append(tick["world_tick"])
            off_motion += tick["displacement_m"]
        if tick["displacement_m"] > 0:
            active_ticks.append(tick["world_tick"])
    _require(
        active_ticks == l23["paper_activity_ticks"]
        and len(off_ticks) > 0 and math.isfinite(off_motion),
        "sampled motion labels disagree with Paper readback",
    )
    return DevProxyEpisode(
        session_id=session,
        paper_world_id=world,
        action_id=action["action"],
        action_before_native_seq=before["seq"],
        action_after_native_seq=after["seq"],
        next_native_seq=decisions[2]["probe_seq"],
        before_minecraft_food=float(before["snapshot"]["food"]),
        before_s42_threat_distance_m=float(move["distance_m"]),
        sampled_input_off_ticks=tuple(off_ticks),
        sampled_input_off_motion_m=off_motion,
        sampled_any_motion=off_motion > 0.0,
        s16_original_sha256=_sha(s16_original),
        s7_prefix_sha256=_sha(s7_received_prefix_original),
        paper_original_sha256=_sha(paper_server_original),
    )


def summarize_h6_provisional_worlds(
    episodes: tuple[DevProxyEpisode, ...],
) -> DevProxyComparison:
    """Only cheap DEV observational comparisons; NEVER call formal BCG trainer."""
    _require(type(episodes) is tuple and len(episodes) <= MAX_SAMPLES, "bounded episodes")
    worlds: set[str] = set()
    sessions: set[str] = set()
    receipts: set[tuple[str, str]] = set()
    for row in episodes:
        _require(type(row) is DevProxyEpisode, "typed DEV proxy required")
        _require(
            row.paper_world_id not in worlds and row.session_id not in sessions
            and (row.session_id, row.action_id) not in receipts
            and row.classification == "DEV_SAMPLED_LAST_REPORTED_INPUT_OFF_PROXY_ONLY"
            and not row.physical_training_eligible and not row.physical_effective_clear_attested
            and not row.goal_attested and row.learning_commits == row.extra_actions == 0,
            "duplicate or over-qualified provisional World",
        )
        worlds.add(row.paper_world_id)
        sessions.add(row.session_id)
        receipts.add((row.session_id, row.action_id))
    flags = [x.sampled_any_motion for x in episodes]
    return DevProxyComparison(
        distinct_provisional_worlds=len(episodes),
        cheap_last_world_motion=(
            "SAMPLED_MOTION" if flags[-1] else "NO_SAMPLED_MOTION"
        ) if flags else "UNKNOWN",
        cheap_any_world_motion=(
            "SAMPLED_MOTION" if any(flags) else "NO_SAMPLED_MOTION"
        ) if flags else "UNKNOWN",
    )
