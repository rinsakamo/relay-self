"""T1w: packet/geometry matches are NOT source-bound WorldTick authority."""
from __future__ import annotations

import copy
import json

import pytest

from adapters.mineflayer.t1w_motion_correspondence_dev import (
    T1wMotionRejected,
    review_motion_correspondence_dev,
)


def event(index, kind, clock, **kwargs):
    return dict(
        revision=1, kind=kind, index=index, node_ns=str(clock),
        clock_scope="NODE_ONLY", source_authority="PASSIVE_LOCAL_DIAGNOSTIC",
        **kwargs,
    )


def node(*, duplicate=False, wrong_pose=False, footer=True):
    rows = [
        event(1, "PHYSICS_EVENT_SAMPLE", 100, physics_event_index=1,
              applied_controls_sample={"back": True},
              client_pose_sample={"x": 0., "y": 64., "z": 0.}),
        event(2, "MOVEMENT_WRITE_RETURNED", 120, packet_index=1,
              packet_name="position", last_physics_event_index=1,
              packet_pose={"x": .2 if wrong_pose else .098, "y": 64., "z": 0.},
              packet_pose_valid=True, network_delivered=False, paper_accepted=False),
    ]
    if duplicate:
        rows.append(event(3, "MOVEMENT_WRITE_RETURNED", 130, packet_index=2,
                          packet_name="position", last_physics_event_index=1,
                          packet_pose={"x": .098, "y": 64., "z": 0.},
                          packet_pose_valid=True,
                          network_delivered=False, paper_accepted=False))
    if footer:
        rows.append(dict(revision=1, kind="TRACE_END", complete=True, lost=False,
                         recorded_rows=len(rows), motion_authority=False))
    return [json.dumps(row) for row in rows]


def paper(*, movement=.098, event_id=1, world="evidence-world"):
    return [
        "[21:34:00] [Server thread/INFO]: M02_DEV_MOTION "
        f"id={event_id} reason=WALK blocks={movement} billed=0 "
        "cumulative_blocks=0.098 cumulative_billed=0 "
        "from_x=0 from_y=64 from_z=0 "
        f"to_x={movement} to_y=64 to_z=0 world_full_time=1033 "
        f"world={world} marker_id=none"
    ]


def test_even_exact_unique_packet_pose_does_not_admit_p1():
    result = review_motion_correspondence_dev(node(), paper())
    assert result["node_physics_samples"] == 1
    assert result["paper_move_events"] == 1
    assert result["paper_candidates"][0]["candidate_status"] == (
        "GEOMETRY_SINGLE_UNATTESTED")
    assert result["paper_candidates"][0]["matching_packet_indices"] == [1]
    assert result["p1_transitions_admitted"] == 0
    assert result["m0_debits_posted"] == 0
    assert result["exact_client_step_to_paper_tick_proven"] is False
    assert result["network_acceptance_proven"] is False
    assert result["cross_process_packet_id_present"] is False


def test_duplicate_packet_geometry_is_ambiguous():
    result = review_motion_correspondence_dev(node(duplicate=True), paper())
    assert result["paper_candidates"][0]["candidate_status"] == "GEOMETRY_AMBIGUOUS"
    assert result["paper_candidates"][0]["matching_packet_indices"] == [1, 2]
    assert result["p1_transitions_admitted"] == 0


def test_no_pose_match_is_not_filled_from_nearest_clock():
    result = review_motion_correspondence_dev(node(wrong_pose=True), paper())
    assert result["paper_candidates"][0]["candidate_status"] == "NO_GEOMETRY_MATCH"
    assert result["paper_candidates"][0]["matching_packet_indices"] == []
    assert result["p1_transitions_admitted"] == 0


@pytest.mark.parametrize("mutate", [
    lambda rows: rows.pop(),
    lambda rows: rows[2].update(complete=False, lost=True),
    lambda rows: rows[1].update(node_ns="50"),
    lambda rows: rows[1].update(network_delivered=True),
    lambda rows: rows[1].update(index=4),
    lambda rows: rows[1].update(packet_index=4),
    lambda rows: rows[1].update(clock_scope="PAPER"),
    lambda rows: rows.append(event(4, "PHYSICS_EVENT_SAMPLE", 150)),
])
def test_corrupt_partial_backpressured_or_forged_node_trace_rejected(mutate):
    lines = [json.loads(line) for line in node()]
    mutate(lines)
    with pytest.raises(T1wMotionRejected):
        review_motion_correspondence_dev([json.dumps(x) for x in lines], paper())


def test_duplicate_paper_motion_events_rejected():
    with pytest.raises(T1wMotionRejected, match="duplicate Paper"):
        review_motion_correspondence_dev(node(), paper() + paper())


def test_distinct_paper_worlds_refused():
    with pytest.raises(T1wMotionRejected, match="Paper event order or world changed"):
        review_motion_correspondence_dev(node(), paper(world="one") + paper(
            event_id=2, world="two"))


def test_paper_motion_bad_numeric_rejected_not_rounded_to_zero():
    with pytest.raises(T1wMotionRejected, match="invalid Paper movement geometry"):
        review_motion_correspondence_dev(node(), paper(movement=float("nan")))


def test_complete_zero_motion_trace_remains_unqualified():
    zero = [event(1, "PHYSICS_EVENT_SAMPLE", 100)]
    zero.append(dict(revision=1, kind="TRACE_END", complete=True,
                     lost=False, recorded_rows=1, motion_authority=False))
    r = review_motion_correspondence_dev([json.dumps(x) for x in zero], [])
    assert r["paper_move_events"] == 0
    assert r["p1_transitions_admitted"] == 0
