"""L-BCG H7: source-timed S49 PRE-action cues from already archived H5.

Read-only and provisional. Does not create a Goal, gait, P1/M state, obstacle
fact, PHYSICAL_POST_CLEAR_VERIFIED, an actionable L1 hint, or World truth.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from relay_self.l_bcg_dev_proxy import (
    DevProxyEpisode,
    DevProxyRejected,
    _source_rows,
    read_h6_provisional_world,
    summarize_h6_provisional_worlds,
)

_MISSING = (
    "goal_remaining_m", "goal_tolerance_m", "selected_gait",
    "p1_fatigue_high", "m_energy_low", "verified_obstacle",
    "world_revision", "verified_post_clear_training",
)


@dataclass(frozen=True, slots=True)
class H7ObservedCue:
    name: str
    value: float
    native_seq: int
    native_source_ref: str
    phase: str = "ORIGINAL_S49_PRE_ACTION"


@dataclass(frozen=True, slots=True)
class H7PreActionAudit:
    episode: DevProxyEpisode
    original_choice_event_seq: int
    original_choice_probe_seq: int
    original_action_before_probe_seq: int
    original_next_epoch_probe_seq: int
    pre_action_observed: tuple[H7ObservedCue, ...]
    missing_bcg_conditions: tuple[str, ...]
    cheap_native_food_low: bool
    cheap_native_threat_near: bool
    provenance_status: str = "HOST_S7_DIGEST_MATCH_NOT_INDEPENDENT_WIRE_ATTESTATION"
    physical_training_worlds: int = 0
    learned_l1_attention: str = "DEFER_UNKNOWN"
    extra_action_issues: int = 0
    learning_updates: int = 0
    qualifies_goal: bool = False
    qualifies_p1_m: bool = False
    qualifies_post_clear: bool = False


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise DevProxyRejected(label)


def audit_h7_pre_action(
    *, host_report_original: bytes, independent_audit_original: bytes,
    s16_original: bytes, s7_received_prefix_original: bytes,
    paper_server_original: bytes,
) -> H7PreActionAudit:
    """Retain PRE-action event-20 and S15-before identity, not future epoch-55.

    H6 first verifies all original digest and source-bound ceilings. H7 only
    extracts existing measured native values, never fills absent Goal or Body.
    """
    episode = read_h6_provisional_world(
        host_report_original=host_report_original,
        independent_audit_original=independent_audit_original,
        s16_original=s16_original,
        s7_received_prefix_original=s7_received_prefix_original,
        paper_server_original=paper_server_original,
    )
    report = json.loads(host_report_original)
    _require(
        hashlib.sha256(s7_received_prefix_original).hexdigest()
        == episode.s7_prefix_sha256,
        "wrong pre-action S7 digest",
    )
    rows = _source_rows(s7_received_prefix_original, session=episode.session_id)
    try:
        choice = report["decisions"][1]
        before = report["actual_native_actions"][0]["execution_evidence"]["before_observation"]
        next_epoch = report["live_next_epoch"]["current_body"]["observation"]
        choice_row = rows[choice["probe_seq"]]
        before_row = rows[before["seq"]]
        snapshot = choice_row["snapshot"]
        before_snapshot = before_row["snapshot"]
    except (KeyError, TypeError, IndexError) as exc:
        raise DevProxyRejected("missing original before-Action native cue") from exc
    choice_seq = choice["probe_seq"]
    before_seq = before["seq"]
    _require(
        type(choice_seq) is int
        and type(before_seq) is int
        and type(choice["event_seq"]) is int
        and choice["issued"] is True
        and choice["selected"] == "MOVE_AWAY"
        and choice_seq < before_seq == episode.action_before_native_seq
        and before_seq < episode.action_after_native_seq < episode.next_native_seq
        and next_epoch.get("native_seq") == episode.next_native_seq
        and next_epoch.get("session_id") == episode.session_id
        and choice_row.get("kind") == before_row.get("kind") == "probe"
        and choice_row.get("request_id") == (
            f"s49-actual:{episode.session_id}:event-{choice['event_seq']}"
        )
        and before_row.get("request_id") == before.get("request_id")
        and before_row.get("snapshot") == before.get("snapshot"),
        "S49 pre-action epoch misbound or next-epoch leakage",
    )
    source = (
        f"native-probe:{episode.session_id}:{choice_seq}:"
        f"{choice_row['request_id']}"
    )
    before_source = (
        f"native-probe:{episode.session_id}:{before_seq}:"
        f"{before_row['request_id']}"
    )
    items: list[H7ObservedCue] = []
    for key in ("health", "food", "food_saturation"):
        val = snapshot.get(key)
        _require(type(val) in (int, float) and -1e100 < val < 1e100,
                 "invalid native pre-action body scalar")
        items.append(H7ObservedCue("minecraft_" + key, float(val), choice_seq, source))
    position = snapshot.get("position")
    _require(isinstance(position, dict), "missing pre-action native position")
    for axis in ("x", "y", "z"):
        val = position.get(axis)
        _require(type(val) in (int, float) and -1e100 < val < 1e100,
                 "invalid original native coordinate")
        items.append(H7ObservedCue("position_" + axis, float(val), choice_seq, source))
    entities = snapshot.get("nearby_entities")
    coverage = snapshot.get("nearby_entities_coverage")
    _require(isinstance(entities, list) and isinstance(coverage, dict),
             "missing S49 entity coverage")
    _require(
        coverage.get("truncated") is False
        and coverage.get("source_scope") == "mineflayer_entity_registry"
        and type(coverage.get("candidate_count")) is int
        and coverage["candidate_count"] >= len(entities),
        "original native threat coverage not admitted",
    )
    matches = [
        e for e in entities if isinstance(e, dict)
        and e.get("id") == choice["entity_id"]
        and e.get("name") == "zombie" and e.get("type") == "hostile"
    ]
    _require(len(matches) == 1, "original chosen hostile not observed")
    dist = matches[0].get("distance")
    _require(
        type(dist) in (int, float) and 0 <= dist < 1e100
        and type(choice.get("distance_m")) in (int, float)
        and dist == choice["distance_m"]
        and dist == episode.before_s42_threat_distance_m,
        "S42 pre-action target distance mismatch",
    )
    items.append(H7ObservedCue("s42_hostile_distance_m", float(dist), choice_seq, source))
    # S15 pre-action probe is a distinct later native observation.
    # It must not be relabelled as the S42 decision-time source.
    val = before_snapshot.get("food")
    _require(
        type(val) in (int, float) and val == episode.before_minecraft_food,
        "S15-before food differs from original episode",
    )
    items.append(H7ObservedCue("s15_before_minecraft_food", float(val), before_seq, before_source))
    _require(
        not any(x.native_seq >= episode.action_after_native_seq for x in items),
        "post-outcome feature leakage",
    )
    return H7PreActionAudit(
        episode=episode,
        original_choice_event_seq=choice["event_seq"],
        original_choice_probe_seq=choice_seq,
        original_action_before_probe_seq=before_seq,
        original_next_epoch_probe_seq=episode.next_native_seq,
        pre_action_observed=tuple(items),
        missing_bcg_conditions=_MISSING,
        cheap_native_food_low=float(snapshot["food"]) <= 10.0,
        cheap_native_threat_near=float(dist) <= 4.0,
    )


def compare_h7_cheap_pre_action(
    audits: tuple[H7PreActionAudit, ...],
) -> dict[str, object]:
    """Observational cheap controls; NEVER score a learned L1 policy."""
    _require(type(audits) is tuple, "bounded H7 typed audit tuple needed")
    _require(all(type(a) is H7PreActionAudit for a in audits), "typed audit only")
    base = summarize_h6_provisional_worlds(tuple(a.episode for a in audits))
    _require(
        all(a.physical_training_worlds == a.extra_action_issues == a.learning_updates == 0
            and not (a.qualifies_goal or a.qualifies_p1_m or a.qualifies_post_clear)
            and a.learned_l1_attention == "DEFER_UNKNOWN" for a in audits),
        "provisional H7 promoted into learning authority",
    )
    return {
        "observed_worlds": base.distinct_provisional_worlds,
        "cheap_food_low_worlds": sum(a.cheap_native_food_low for a in audits),
        "cheap_threat_near_worlds": sum(a.cheap_native_threat_near for a in audits),
        "cheap_sampled_motion_worlds": sum(a.episode.sampled_any_motion for a in audits),
        "source_ceiling": "DEV_ARCHIVED_H5_PRE_ACTION_NATIVE_NOT_GOAL_OR_P1_M",
        "learned_l1_attention": "DEFER_UNKNOWN",
        "physical_training_worlds": 0,
        "action_issues": 0,
        "learning_updates": 0,
    }
