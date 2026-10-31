"""S50 prospective Paper callbacks are auditable, never full-tick P1 WAIT."""
from __future__ import annotations

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_lifecycle import review_lifecycle

SELF_WORLD = "00000000-0000-0000-0000-000000000001"
OTHER_WORLD = "00000000-0000-0000-0000-000000000004"
SELF = "00000000-0000-0000-0000-000000000002"
MOB = "00000000-0000-0000-0000-000000000003"
MARKER = "owned-session"


def source(*, event_kind: str = "ENTITY_ADD", event_world: str = OTHER_WORLD,
           event_tick: int = 44, event_seq: int = 1,
           event_uuid: str = MOB, event_type: str = "STRIDER",
           reported_count: int | None = None,
           overflow: str = "false", async_seen: str = "false") -> str:
    begin = (
        f"S50_DEV_WAIT_LIFECYCLE_BEGIN marker_id={MARKER} world=world "
        f"tick=40 subject_uuid={SELF} event_count=0 "
        "coverage=CALLBACK_PREFIX_TO_SAMPLE_ONLY"
    )
    lines = [begin]
    if event_kind.startswith("CHUNK_"):
        event_uuid, event_type = "NONE", "CHUNK"
    emitted = False
    for index in range(1, 9):
        tick = 40 + index
        if not emitted and tick >= event_tick:
            lines.append(
                f"S50_DEV_WAIT_LIFECYCLE_EVENT marker_id={MARKER} world=world "
                f"tick={event_tick} seq={event_seq} kind={event_kind} "
                f"entity_world={event_world} entity_tick={event_tick} "
                f"uuid={event_uuid} type={event_type} chunk_x=-1 chunk_z=0 "
                "coverage=PAPER_CALLBACK_ONLY"
            )
            emitted = True
        count = (int(emitted) if reported_count is None else reported_count)
        lines.append(
            f"S50_DEV_WAIT_LIFECYCLE_SAMPLE marker_id={MARKER} world=world "
            f"tick={tick} index={index} event_count={count} "
            f"overflow={overflow} async_seen={async_seen} "
            "coverage=CALLBACK_PREFIX_TO_SAMPLE_ONLY"
        )
    return "\n".join(lines)


def check(original: str) -> dict:
    return review_lifecycle(
        original, marker=MARKER, world="world", self_uuid=SELF,
        self_entity_world_uuid=SELF_WORLD,
        wait_first_tick=41, wait_last_tick=48,
    )


def test_other_world_strider_callback_not_same_world_agent():
    out = check(source())
    assert out["event_count"] == 1
    assert out["same_world_entity_lifecycle_ticks"] == []
    assert out["other_world_event_ticks"] == [44]
    assert out["whole_tick_entity_lifecycle"] == "NOT_ATTESTED"
    assert out["wait_ticks_admitted"] == 0
    assert out["p1_fatigue_recovered"] == 0
    assert not out["science_go"]


def test_same_world_transient_mob_cannot_hide_between_two_clean_snapshots():
    out = check(source(event_world=SELF_WORLD))
    assert out["same_world_entity_lifecycle_ticks"] == [44]
    assert out["wait_ticks_admitted"] == 0


def test_same_world_chunk_unload_is_distinguished_from_entity():
    out = check(source(event_kind="CHUNK_UNLOAD", event_world=SELF_WORLD))
    assert out["same_world_chunk_change_ticks"] == [44]
    assert out["same_world_entity_lifecycle_ticks"] == []


def test_no_event_source_still_never_grants_wait():
    value = source()
    lines = [
        line.replace("event_count=1", "event_count=0")
        for line in value.splitlines()
        if "S50_DEV_WAIT_LIFECYCLE_EVENT " not in line
    ]
    out = check("\n".join(lines))
    assert out["event_count"] == 0
    assert out["wait_ticks_admitted"] == 0
    assert out["action_free_interval"] == "NOT_ATTESTED"


@pytest.mark.parametrize("before,after", [
    ("tick=40 subject_uuid", "tick=41 subject_uuid"),
    ("subject_uuid=" + SELF, "subject_uuid=" + MOB),
    ("seq=1 kind=", "seq=2 kind="),
    ("kind=ENTITY_ADD", "kind=IMPOSSIBLE"),
    ("type=STRIDER", "type=CHUNK"),
    ("entity_world=" + OTHER_WORLD, "entity_world=foreign"),
    ("chunk_x=-1", "chunk_x=-01"),
    ("coverage=PAPER_CALLBACK_ONLY", "coverage=FULL_TICK"),
    ("overflow=false", "overflow=true"),
    ("async_seen=false", "async_seen=true"),
    ("index=4 event_count=1", "index=4 event_count=0"),
    ("tick=44 seq=1", "tick=39 seq=1"),
    ("world=world", "world=foreign"),
])
def test_forged_event_source_rejected(before: str, after: str):
    original = source()
    assert before in original
    with pytest.raises(BoundaryRejected):
        check(original.replace(before, after, 1))


def test_lost_and_duplicate_event_rows_are_not_clean():
    original = source()
    events = [line for line in original.splitlines()
              if "S50_DEV_WAIT_LIFECYCLE_EVENT " in line]
    assert len(events) == 1
    with pytest.raises(BoundaryRejected):
        check(original.replace(events[0] + "\n", ""))
    with pytest.raises(BoundaryRejected):
        check(original.replace(events[0], events[0] + "\n" + events[0]))


def test_missing_one_sampler_rejected():
    original = source()
    lines = [x for x in original.splitlines()
             if "index=8 " not in x]
    with pytest.raises(BoundaryRejected):
        check("\n".join(lines))


def test_event_after_last_sample_rejected():
    original = source()
    event = next(x for x in original.splitlines()
                 if "S50_DEV_WAIT_LIFECYCLE_EVENT " in x)
    with pytest.raises(BoundaryRejected):
        check(original.replace(event + "\n", "") + "\n" + event)


def test_missing_begin_and_cross_session_cannot_borrow_source():
    original = source()
    with pytest.raises(BoundaryRejected):
        check("\n".join(x for x in original.splitlines()
                        if "S50_DEV_WAIT_LIFECYCLE_BEGIN " not in x))
    with pytest.raises(BoundaryRejected):
        check(original.replace("marker_id=" + MARKER, "marker_id=foreign", 1))
