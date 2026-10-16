"""Source adversaries: all loaded chunks per sampler are not whole-tick WAIT."""
from __future__ import annotations

import hashlib

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_scope import review_scope


def original_source() -> str:
    world_uuid = "00000000-0000-0000-0000-000000000001"
    self_uuid = "00000000-0000-0000-0000-000000000002"
    mob_uuid = "00000000-0000-0000-0000-000000000003"
    roster = [
        f"{world_uuid}:0:0:{self_uuid}:PLAYER",
        f"{world_uuid}:0:0:{mob_uuid}:ZOMBIE",
    ]
    fingerprint = hashlib.sha256(
        "".join(record + "\\n" for record in roster).encode("utf-8")
    ).hexdigest()
    lines = []
    for i in range(1, 9):
        stamp = 40 + i
        lines.append(
            f"S50_DEV_WAIT_TICK marker_id=action-session world=world "
            f"tick={stamp} index={i} combat_events=0 swing_events=0"
        )
        for order, record in enumerate(roster, 1):
            euuid, cx, cz, eid, kind = record.split(":")
            lines.append(
                f"S50_DEV_WAIT_ENTITY marker_id=action-session world=world "
                f"tick={stamp} index={i} roster_index={order} "
                f"entity_world={euuid} chunk_x={cx} chunk_z={cz} "
                f"uuid={eid} type={kind}"
            )
        lines.append(
            f"S50_DEV_WAIT_SCOPE marker_id=action-session world=world "
            f"tick={stamp} index={i} loaded_worlds=3 loaded_chunks=250 "
            f"loaded_entities=2 subject_uuid={self_uuid} "
            "other_loaded_entities=1 other_online_players=0 "
            f"census_sha256={fingerprint} movement_events=10 teleport_events=0 "
            "velocity_events=0 damage_events=0 interact_events=0 "
            "combat_events=0 swing_events=0 coverage=LOADED_CHUNK_SAMPLER_ONLY "
            "client_held_controls=NOT_OBSERVED entity_lifecycle=NOT_ATTESTED"
        )
    return "\\n".join(lines)


def review(content: str):
    return review_scope(content, marker="action-session", world="world",
                        wait_first_tick=41, wait_last_tick=48,
                        original_outcome="outcome")


def test_scope_candidate_cannot_certify_world_or_wait():
    r = review(original_source())
    assert r["source_scope_rows"] == 8
    assert r["wait_ticks_admitted"] == 0
    assert r["p1_fatigue_recovered"] == 0
    assert r["other_loaded_entities_seen_ticks"] == list(range(41, 49))
    assert r["source_entity_rows"] == 16
    assert r["first_sample_entity_types"] == {"PLAYER": 1, "ZOMBIE": 1}
    assert r["unloaded_entity_lifecycle"] == "NOT_ATTESTED"
    assert r["held_motor_control_absence"] == "NOT_ATTESTED"


@pytest.mark.parametrize("start,end", [
    ("loaded_worlds=3", "loaded_worlds=0"),
    ("loaded_chunks=250", "loaded_chunks=0"),
    ("loaded_entities=2", "loaded_entities=1"),
    ("census_sha256=", "census_sha256=FAKE"),
    ("coverage=LOADED_CHUNK_SAMPLER_ONLY", "coverage=WHOLE_WORLD"),
    ("client_held_controls=NOT_OBSERVED", "client_held_controls=FALSE"),
    ("entity_lifecycle=NOT_ATTESTED", "entity_lifecycle=COMPLETE"),
    ("tick=42 index=2", "tick=41 index=2"),
    ("world=world", "world=foreign"),
    ("marker_id=action-session", "marker_id=other"),
    ("swing_events=0", "swing_events=1"),
    ("teleport_events=0", "teleport_events=11"),
    ("type=ZOMBIE", "type=CHICKEN"),
    ("roster_index=2", "roster_index=1"),
    ("subject_uuid=00000000-0000-0000-0000-000000000002",
     "subject_uuid=00000000-0000-0000-0000-000000000003"),
])
def test_forged_or_missing_scope_fails_closed(start, end):
    content = original_source()
    assert start in content
    with pytest.raises(BoundaryRejected):
        review(content.replace(start, end, 1))


@pytest.mark.parametrize("remove", ["S50_DEV_WAIT_SCOPE", "S50_DEV_WAIT_TICK", "S50_DEV_WAIT_ENTITY"])
def test_truncated_or_absent_scope_fails_closed(remove):
    content = original_source()
    with pytest.raises(BoundaryRejected):
        review("\n".join(x for x in content.splitlines() if remove not in x))


def test_native_activity_delta_is_not_wait():
    content = original_source().splitlines()
    # This changes a legitimate event counter monotonically; never implies WAIT.
    for i, line in enumerate(content):
        if line.startswith("S50_DEV_WAIT_SCOPE ") and "index=8 " in line:
            content[i] = line.replace("movement_events=10", "movement_events=11")
    receipt = review("\n".join(content))
    assert receipt["activity_counter_changed_after_first_sampler"] == [48]
    assert receipt["wait_ticks_admitted"] == 0


def test_false_terminal_outcome_rejected():
    with pytest.raises(BoundaryRejected):
        review_scope(original_source(), marker="action-session", world="world",
                     wait_first_tick=41, wait_last_tick=48,
                     original_outcome="unknown")


def test_negative_controls_cannot_upgrade_to_p1():
    receipt = review(original_source())
    assert not receipt["independent_R_qualification"]
    assert receipt["whole_tick_all_activity_absence"] == "NOT_ATTESTED"
    assert receipt["science_go"] is False
