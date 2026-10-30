"""G4.11: original Paper pair opportunity, not fictitious cadence proof."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g410_in_action_evidence_quality_dev import (
    join_g410_in_action_evidence_dev,
)
from adapters.mineflayer.g411_g1_unstable_pair_census_dev import (
    _reason,
    join_g411_g1_unstable_pair_census_dev,
)
from test_s49_g410_in_action_evidence_quality_dev import _source


def _args():
    original = _source()
    g410 = [asdict(row) for row in join_g410_in_action_evidence_dev(
        **original,
    )]
    return {**original, "g410_rows": g410}


def test_g411_readonly_adjacency_and_original_evidence_sha():
    a = _args()
    before = deepcopy(a)
    out = join_g411_g1_unstable_pair_census_dev(**a)
    assert a == before
    assert [r.source_seq for r in out] == [12, 20, 26, 32]
    assert len(out) == len([
        r for r in a["g410_rows"]
        if "G1_TWO_SAMPLE_STABLE_KIND" in r["missing_evidence_axes"]
    ])
    assert all(r.evidence_class == "ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS"
               for r in out)
    assert all(r.adjacent_original_paper_worldtick
               and r.original_world_tick_gap == 1
               and r.original_paper_seq_gap > 0
               and len(r.original_g410_row_sha256) == 64
               and not r.physical_cadence_causality_proven
               and not r.blocked_collision_proven
               and not r.packet_to_physics_tick_attested
               and not r.inferred_wait_or_recovery
               and not r.unknown_reclassified
               and not r.p1_or_m0_reposted
               and not r.second_reader_or_owner_created
               for r in out)


@pytest.mark.parametrize(("kind", "same_gen", "same_phase", "same_controls",
                          "same_gait", "reason"), [
    ("BLOCKED_OR_STALLED_CONTROL_UNDETERMINED", True, True, True, True,
     "G1_NEAR_ZERO_MOTION_WITH_CONTROL_NOT_CAUSAL_BLOCK_PROOF"),
    ("MOVING_MODE_UNDETERMINED", True, True, True, True,
     "G1_MOVING_MODE_UNDETERMINED"),
    ("STABLE_PHYSICAL_IDLE_CANDIDATE", True, True, True, True,
     "G1_IDLE_CANDIDATE_INSIDE_ACTION_NOT_WAIT"),
    ("TRANSITION_OR_UNDETERMINED", False, True, True, True,
     "ADJACENT_NODE_CONTROL_BOUNDARY_DIFFERS"),
    ("TRANSITION_OR_UNDETERMINED", True, True, False, True,
     "ADJACENT_NODE_CONTROLS_DIFFER"),
    ("TRANSITION_OR_UNDETERMINED", True, True, True, False,
     "ADJACENT_PAPER_GAIT_FACTS_DIFFER"),
    ("TRANSITION_OR_UNDETERMINED", True, True, True, True,
     "ADJACENT_PAIR_PRESENT_CAUSE_UNDETERMINED"),
]):
def test_g411_observational_reason_categories(
    kind, same_gen, same_phase, same_controls, same_gait, reason,
):
    assert _reason(
        kind, adjacent=True, has_previous=True,
        same_generation=same_gen, same_phase=same_phase,
        same_controls=same_controls, same_paper_gait=same_gait,
    ) == reason


def test_g411_frame_absence_is_not_claimed_as_physical_sampling_cause():
    assert _reason(
        "TRANSITION_OR_UNDETERMINED", adjacent=False,
        has_previous=True, same_generation=False, same_phase=False,
        same_controls=False, same_paper_gait=False,
    ) == "NO_ADJACENT_ORIGINAL_PAPER_WORLDTICK"
    assert _reason(
        "TRANSITION_OR_UNDETERMINED", adjacent=False,
        has_previous=False, same_generation=False, same_phase=False,
        same_controls=False, same_paper_gait=False,
    ) == "NO_PREVIOUS_ORIGINAL_PAPER_FRAME"


@pytest.mark.parametrize("mutate", [
    "change_g410", "omit_g410", "forge_t2", "replace_paper_tick",
    "duplicate_paper", "nonmonotone_source", "negative_motion",
    "foreign_session", "g1_kind_changed",
])
def test_g411_fails_closed_on_mixed_original_receipts(mutate):
    a = _args()
    if mutate == "change_g410":
        a["g410_rows"][0]["original_g1_kind"] = "STABLE_SPRINT_FORWARD_CANDIDATE"
    elif mutate == "omit_g410":
        a["g410_rows"].pop()
    elif mutate == "forge_t2":
        a["t2_rows"][1]["p1"] = {"forged": True}
    elif mutate == "replace_paper_tick":
        a["paper_rows"][1]["world_tick"] += 1000
    elif mutate == "duplicate_paper":
        a["paper_rows"].append(dict(a["paper_rows"][-1]))
    elif mutate == "nonmonotone_source":
        a["paper_rows"][1]["source_seq"] = a["paper_rows"][0]["source_seq"]
    elif mutate == "negative_motion":
        a["paper_rows"][1]["dxz_m"] = -1.0
    elif mutate == "foreign_session":
        a["paper_rows"][1]["session_id"] = "foreign"
    else:
        a["paper_rows"][1]["kind"] = "STABLE_SPRINT_FORWARD_CANDIDATE"
    with pytest.raises(ValueError, match="G4.1[01]"):
        join_g411_g1_unstable_pair_census_dev(**a)


def test_g411_keeps_all_original_g49_unbound_outside_this_diagnostic():
    a = _args()
    a["g410_rows"] = [asdict(row) for row in
                       join_g410_in_action_evidence_dev(**_source())]
    rows = join_g411_g1_unstable_pair_census_dev(**a)
    assert all(r.original_action_id.startswith("goal-") for r in rows)
    assert len(rows) <= sum(row["still_unknown"] for row in a["g49_rows"])
