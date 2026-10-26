"""DEV-only moving-geometry corroboration between two untrusted local clocks."""
from __future__ import annotations

from copy import deepcopy

import pytest

from adapters.mineflayer.s49_node_physics_postclear_dev import (
    NativePhysicsTraceRejected,
    audit_node_paper_motion_fingerprint_dev,
)
from test_s49_paper_action_bracket_dev import ACTION, SESSION


def records():
    node = {
        "classification": "NODE_LOCAL_PHYSICS_AFTER_CONTROL_CLEAR_DEV_ONLY",
        "action_id": ACTION,
        "session_id": SESSION,
        "node_postclear_horizontal_deltas_m": [
            .21214275185564663, .11582994251318313, .06324314861219793,
            .034530759142260115, .018853794491674014,
        ],
        "node_postclear_forward_sprint_all_false": True,
        "node_postclear_physics_ticks": 5,
        "node_paper_tick_join_attested": False,
        "WAIT_sourcebound_admitted": False,
        "P1_posted": False,
        "M0_posted": False,
    }
    paper = {
        "classification": "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY",
        "action_id": ACTION,
        "session_id": SESSION,
        "post_release_deltas_m": [
            .06324314861219793, .034530759142260115,
            .018853794491674014, 0.0,
        ],
        "paper_callbacks": 5,
        "speed_modifier_present": False,
        "WAIT_sourcebound_admitted": False,
        "P1_posted": False,
        "M0_posted": False,
    }
    return node, paper


def review(node, paper):
    return audit_node_paper_motion_fingerprint_dev(
        node, paper, action_id=ACTION, session_id=SESSION,
    )


def test_actual_source_style_three_consecutive_moving_deltas_are_consistent():
    node, paper = records()
    r = review(node, paper)
    assert r["matched_consecutive_nonzero_deltas"] == 3
    assert r["node_relative_start_index"] == 3
    assert r["paper_relative_start_index_excluding_mixed"] == 1
    assert r["node_matched_deltas_m"] == r["paper_matched_deltas_m"]
    assert r["native_Paper_tick_correspondence_attested"] is False
    assert r["independent_source_trust_attested"] is False
    assert r["physical_WAIT_qualified"] is False


def test_two_adjacent_moving_samples_count_without_fabricating_missing_third():
    node, paper = records()
    paper["post_release_deltas_m"] = [
        .034530759142260115, .018853794491674014, 0, .0159,
    ]
    r = review(node, paper)
    assert r["matched_consecutive_nonzero_deltas"] == 2
    assert r["node_relative_start_index"] == 4


@pytest.mark.parametrize("fault", [
    "foreign_node_action", "foreign_paper_action", "foreign_node_session",
    "foreign_paper_session", "fake_node_scope", "fake_paper_scope",
    "node_controls_on", "paper_modifier_present", "node_sync_claim",
    "paper_wait_minted", "node_wait_minted", "node_m0_minted",
    "paper_p1_minted", "node_short", "paper_short", "nan",
    "negative", "teleport", "displaced_sequence", "one_coincidence",
    "zero_zero", "fabricated_tolerance", "not_actual_moving",
])
def test_forged_stale_or_unaligned_motion_fingerprints_fail_closed(fault):
    node, paper = records()
    node, paper = deepcopy(node), deepcopy(paper)
    n, p = node["node_postclear_horizontal_deltas_m"], paper["post_release_deltas_m"]
    if fault == "foreign_node_action":
        node["action_id"] = "alien"
    elif fault == "foreign_paper_action":
        paper["action_id"] = "alien"
    elif fault == "foreign_node_session":
        node["session_id"] = "alien"
    elif fault == "foreign_paper_session":
        paper["session_id"] = "alien"
    elif fault == "fake_node_scope":
        node["classification"] = "R_QUALIFIED"
    elif fault == "fake_paper_scope":
        paper["classification"] = "R_QUALIFIED"
    elif fault == "node_controls_on":
        node["node_postclear_forward_sprint_all_false"] = False
    elif fault == "paper_modifier_present":
        paper["speed_modifier_present"] = True
    elif fault == "node_sync_claim":
        node["node_paper_tick_join_attested"] = True
    elif fault == "paper_wait_minted":
        paper["WAIT_sourcebound_admitted"] = True
    elif fault == "node_wait_minted":
        node["WAIT_sourcebound_admitted"] = True
    elif fault == "node_m0_minted":
        node["M0_posted"] = True
    elif fault == "paper_p1_minted":
        paper["P1_posted"] = True
    elif fault == "node_short":
        n.pop()
    elif fault == "paper_short":
        p.pop()
    elif fault == "nan":
        n[2] = float("nan")
    elif fault == "negative":
        p[1] = -.03
    elif fault == "teleport":
        n[3] = 9
    elif fault == "displaced_sequence":
        p[:] = [n[2], 0, n[3], 0]
    elif fault == "one_coincidence":
        p[:] = [n[2], .001, .0005, .003]
    elif fault == "zero_zero":
        n[:] = [0] * 5
        p[:] = [0] * 4
    elif fault == "fabricated_tolerance":
        p[:] = [n[2] + .002, n[3] + .002, n[4] + .002, 0]
    else:
        p[:] = [.35, .27, .19, .11]
    with pytest.raises(NativePhysicsTraceRejected):
        review(node, paper)
