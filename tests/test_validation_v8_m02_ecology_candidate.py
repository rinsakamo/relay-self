"""V8 draft: keep realized random-terrain movement as ecological outcome."""
from __future__ import annotations

import copy

import pytest

from experiments.validation import v8_m02_ecology_candidate as v8


def test_real_world_behavior_not_mistaken_for_v7_matched_path_arithmetic():
    p=v8.candidate()
    x=v8.review_plan(p)
    assert x["classification"]==v8.CLASS
    assert x["draft_arm_count"]==5
    assert x["draft_seed_count"]==8
    assert x["draft_future_science_slots"]==40
    assert x["all_new_science_trials_unexecuted"]
    assert x["minimum_control_required"]["world_clone_bytes"]
    assert x["minimum_control_required"]["native_pose"]
    assert x["minimum_control_required"]["actual_walk_path_can_differ"]
    assert x["minimum_control_required"]["obstacles_not_excluded_after_outcome"]
    assert not x["science_go"]
    assert not x["production_go"]
    assert p["predecessor_v7"]["science_trials_executed"]==0
    assert p["predecessor_v7"]["retroactive_path_gate_change"] is False
    assert p["design"]["policy"].endswith("L1_L2_OFF")
    assert "HARD" in p["design"]["world"]


@pytest.mark.parametrize(("field", "bad"),[
    ("distance_policy","FORCE_EQUAL_DISTANCE"),
    ("start_pose","SEED_ONLY_WITH_RANDOM_RESPAWN"),
    ("pre_action_snapshot","SAME_SEED_WITHOUT_CLONED_CHUNKS"),
    ("host_abort_handling","COUNT_HOST_CRASH_AS_DEATH"),
    ("stopping","DROP_BLOCKED_OR_DEAD"),
    ("science_power_claim",True),
    ("primary",["SOURCE_WALK_EXHAUSTION_ONLY"]),
])
def test_mutating_precaution_or_primary_fail_closed(field,bad):
    p=copy.deepcopy(v8.candidate())
    p["design"][field]=bad
    with pytest.raises(v8.NotAdmitted):
        v8.review_plan(p)


def test_fake_science_or_frozen_v7_retroactive_promotion_is_refused():
    p=v8.candidate()
    p["boundaries"]["v8_science_go"]=True
    with pytest.raises(v8.NotAdmitted):
        v8.review_plan(p)
    p=v8.candidate()
    p["predecessor_v7"]["retroactive_path_gate_change"]=True
    with pytest.raises(v8.NotAdmitted):
        v8.review_plan(p)
    p=v8.candidate()
    p["design"]["seeds"]=[62101] * 8
    with pytest.raises(v8.NotAdmitted):
        v8.review_plan(p)
