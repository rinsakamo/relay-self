"""S50 joint original evidence: correlation is not full-tick WAIT proof."""
from __future__ import annotations

import re
from copy import deepcopy

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_wait_joint_dev import (
    MISSING_R_PROOFS,
    review_joint_wait_sources,
)
from test_s50_p1_control_action import MARKER, WORLD
from test_s50_p1_control_action import fixture as control_fixture
from test_s50_p1_lifecycle import source as lifecycle_source
from test_s50_p1_scope import original_source as scope_source
from test_s50_p1_wait import fixture as wait_source


def _bind(source: str) -> list[str]:
    source = source.replace("marker_id=action-session", "marker_id=" + MARKER)
    source = source.replace("marker_id=owned-session", "marker_id=" + MARKER)
    source = source.replace("world=world", "world=" + WORLD)
    # S50 command source has post-clear tick 58; the WAIT candidate begins 60.
    return [
        re.sub(r"\btick=(\d+)\b",
               lambda m: "tick=" + str(int(m.group(1)) + 20), line)
        for line in source.splitlines()
    ]


def originals(*, mob_elsewhere: bool = True,
              event_world: str = "00000000-0000-0000-0000-000000000004"):
    paper, native, commands, journal, movement = control_fixture()
    lines = [line for line in paper.splitlines()
             if not line.startswith("S50_DEV_WAIT_")]
    lines.extend(_bind(wait_source()))
    lines.extend(line for line in _bind(scope_source(mob_elsewhere=mob_elsewhere))
                 if not line.startswith("S50_DEV_WAIT_TICK "))
    lines.extend(_bind(lifecycle_source(event_world=event_world)))
    return ("\n".join(lines), native, commands, journal, movement)


def test_four_original_streams_cross_join_but_cannot_authorize_p1_recovery():
    result = review_joint_wait_sources(*originals())
    assert result["first_world_tick"] == 61
    assert result["last_world_tick"] == 68
    assert len(result["source_streams_screened"]) == 4
    assert result["sample_screen_clear"] is True
    assert result["observed_conflicts"] == []
    assert result["missing_independent_r_proofs"] == MISSING_R_PROOFS
    assert result["complete_world_tick_inactivity_proven"] is False
    assert result["all_action_issuers_proven_idle"] is False
    assert result["r_original_source_authenticated"] is False
    assert result["source_bound_tick"] is None
    assert result["wait_interval_ref"] is None
    assert result["wait_ticks_admitted"] == 0
    assert result["p1_fatigue_recovered"] == 0
    assert not result["qualification_go"]
    assert not result["science_go"]


def test_other_same_world_entity_never_qualifies_as_solo_wait():
    r = review_joint_wait_sources(*originals(mob_elsewhere=False))
    assert r["observed_conflicts"] == ["OTHER_LOADED_ENTITY_IN_SELF_WORLD"]
    assert not r["sample_screen_clear"]
    assert r["p1_fatigue_recovered"] == 0


def test_transient_entity_event_between_samplers_is_not_invisible():
    r = review_joint_wait_sources(*originals(
        event_world="00000000-0000-0000-0000-000000000001",
    ))
    assert "TRANSIENT_ENTITY_LIFECYCLE_IN_SELF_WORLD" in r["observed_conflicts"]
    assert r["wait_interval_ref"] is None


def test_native_counter_change_blocks_even_when_positions_are_static():
    data = list(originals())
    lines = data[0].splitlines()
    for index, line in enumerate(lines):
        if line.startswith("S50_DEV_WAIT_SCOPE ") and "index=8 " in line:
            lines[index] = line.replace("movement_events=10", "movement_events=11")
    data[0] = "\n".join(lines)
    r = review_joint_wait_sources(*data)
    assert "NATIVE_EVENT_COUNTER_CHANGED" in r["observed_conflicts"]
    assert r["wait_ticks_admitted"] == 0


@pytest.mark.parametrize("original_to_remove", [
    "S50_DEV_WAIT_LIFECYCLE_BEGIN ",
    "S50_DEV_WAIT_LIFECYCLE_SAMPLE ",
    "S50_DEV_WAIT_SCOPE ",
    "S50_DEV_WAIT_ENTITY ",
    "S50_DEV_WAIT_TICK ",
])
def test_missing_original_cannot_cross_join(original_to_remove):
    data = list(originals())
    data[0] = "\n".join(
        line for line in data[0].splitlines()
        if original_to_remove not in line
    )
    with pytest.raises(BoundaryRejected):
        review_joint_wait_sources(*data)


@pytest.mark.parametrize("old,new", [
    ("marker_id=" + MARKER + " world=" + WORLD + " tick=61 index=1",
     "marker_id=foreign world=" + WORLD + " tick=61 index=1"),
    ("census_sha256=", "census_sha256=BAD"),
    ("tick=64 index=4", "tick=65 index=4"),
    ("coverage=CALLBACK_PREFIX_TO_SAMPLE_ONLY",
     "coverage=WHOLE_TICK_ATTESTED"),
])
def test_cross_stream_splice_and_fabricated_coverage_fail(old, new):
    data = list(originals())
    assert old in data[0]
    data[0] = data[0].replace(old, new, 1)
    with pytest.raises(BoundaryRejected):
        review_joint_wait_sources(*data)


def test_open_or_second_action_cannot_be_smuggled_into_wait():
    data = list(originals())
    data[3] = deepcopy(data[3])
    data[3].append(deepcopy(data[3][-1]))
    with pytest.raises(BoundaryRejected):
        review_joint_wait_sources(*data)
