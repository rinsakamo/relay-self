"""V8 structural-only admission / five-profile R engineering handoff regressions."""
from __future__ import annotations

import copy

import pytest

from experiments.validation import v8_m02_admission_bridge as bridge


def test_proposed_slots_cannot_be_read_as_science_trials():
    roster = bridge.draft_roster()
    got = bridge.review_roster(roster)
    assert got["classification"] == bridge.CLASS
    assert got["proposed_slots"] == 40
    assert got["executed_trials"] == 0
    assert got["science_go"] is False
    assert got["randomization_status"] == "DRAFT_ORDER_NOT_APPROVED"
    assert roster["science_admission"] is False
    assert roster["grant_issued"] is False
    assert all(s["state"] == "NOT_RUN" for s in roster["all_slots"])
    assert all(s["source_world_uuid"] is None for s in roster["all_slots"])
    assert len({s["slot_id"] for s in roster["all_slots"]}) == 40


def test_draft_order_reproducible_and_seed_blocked():
    assert bridge.draft_roster() == bridge.draft_roster()
    r = bridge.draft_roster()
    for seed in range(62101, 62109):
        group = [s for s in r["all_slots"] if s["seed"] == seed]
        assert len(group) == 5
        assert {s["arm"] for s in group} == set(bridge.v8.ARMS)
        assert {s["draft_order"] for s in group} == set(range(5))


@pytest.mark.parametrize("mutation", [
    lambda r: r["all_slots"].pop(),
    lambda r: r["all_slots"].append(copy.deepcopy(r["all_slots"][0])),
    lambda r: r["all_slots"][0].__setitem__("state", "SCIENCE_PASS"),
    lambda r: r["all_slots"][0].__setitem__("science_grant", "CONSUMED_OLD_GRANT"),
    lambda r: r["all_slots"][0].__setitem__("source_world_uuid", "looks-authentic"),
    lambda r: r["all_slots"][0].__setitem__("initial_terrain_snapshot_digest", "a" * 64),
    lambda r: r["all_slots"][0].__setitem__("seed", 61021),
    lambda r: r["all_slots"][0].__setitem__("draft_order", 1 - r["all_slots"][0]["draft_order"] % 2),
    lambda r: r.__setitem__("science_admission", True),
    lambda r: r.__setitem__("grant_issued", True),
    lambda r: r.__setitem__("v7_science_executed", 20),
])
def test_roster_tampering_or_grant_claim_fails_closed(mutation):
    r = bridge.draft_roster()
    mutation(r)
    with pytest.raises(bridge.NotAdmitted):
        bridge.review_roster(r)


def test_four_new_originals_are_distinct_and_stay_engineering_only():
    handoff = copy.deepcopy(bridge.R_FOUR_ARM_HANDOFF)
    got = bridge.review_r_handoff(handoff)
    assert got["mechanism_engineering_profiles_total"] == 5
    assert got["qualified_by_r_engineering_only"] == 4
    assert got["previous_base_on_qualified_separately"] is True
    assert got["four_arm_tick_chord_spread_blocks"] > 0.215
    assert got["v7_frozen_matched_path_gate"] == "FAIL"
    assert got["continuous_subtick_path_attested"] is False
    assert got["net_hunger_effect_attested"] is False
    assert got["v8_science_go"] is False
    assert got["v7_science_executed"] == 0
    assert len({v["grant"] for v in handoff.values()}) == 4
    assert len({v["source_artifact_id"] for v in handoff.values()}) == 4


@pytest.mark.parametrize("mutation", [
    lambda h: h.pop("BOTH_ZERO"),
    lambda h: h["BASAL_ZERO"].__setitem__("tick_chord_lower_bound_blocks", 1.9389928412050272),
    lambda h: h["WALK_ZERO"].__setitem__("walk_setter_input", 0.01),
    lambda h: h["BOTH_ZERO"].__setitem__("basal_requested_first_200", 0.2),
    lambda h: h["SHAM_ON"].__setitem__("source_artifact_id", 12056065364),
    lambda h: h["BOTH_ZERO"].__setitem__("grant", "USER_M02_V7_SHAM_ON_20261017_ONCE"),
    lambda h: h["SHAM_ON"].__setitem__("source_artifact_sha256", "a" * 64),
])
def test_forged_changed_or_aliased_r_handoff_fails_closed(mutation):
    h = copy.deepcopy(bridge.R_FOUR_ARM_HANDOFF)
    mutation(h)
    with pytest.raises(bridge.NotAdmitted):
        bridge.review_r_handoff(h)


def test_no_physical_authorization_from_structural_review():
    r = bridge.review_roster(bridge.draft_roster())
    h = bridge.review_r_handoff(copy.deepcopy(bridge.R_FOUR_ARM_HANDOFF))
    assert not r["science_go"]
    assert not h["v8_science_go"]
