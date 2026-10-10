"""B20: frozen exact nine-Draft evidence terminal and fail-closed promotion tests."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from experiments.ac_b_b20_synthesis import (
    BOUNDED_TERMINAL,
    EXPECTED,
    MAIN_SHA,
    MISSING_GATES,
    POSITIVE_CHEAP,
    PROMOTIONS,
    SCHEMA,
    InvalidFrozenEvidence,
    check_frozen_evidence,
    promotion_gate,
    read_frozen_manifest,
    synthesize,
)


def test_all_nine_exact_frozen_draft_receipts_and_qualified_null():
    manifest = read_frozen_manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["authority"]["main"] == MAIN_SHA
    assert manifest["authority"]["issue"] == 533
    assert manifest["authority"]["C15_static_endpoint_PR"] == 525
    r = check_frozen_evidence(manifest)
    assert r.terminal == BOUNDED_TERMINAL
    assert r.qualified_offline_draft_count == 9
    assert r.cheap_baseline_tie_count == 9
    assert r.generic_positive_controls == POSITIVE_CHEAP
    assert not r.production_s11_owner_qualified
    assert not r.physical_s17_s11_source_qualified
    assert not r.authentic_l2_gain_qualified
    assert not r.live_body_cost_measurement_qualified
    assert r.source_authority == "FROZEN_EXPERIMENT_METADATA_ONLY_NOT_REAL_WORLD"
    assert [x["step"] for x in manifest["prospective_entries"]] == [
        f"B{i}" for i in range(11, 20)
    ]
    assert tuple(
        (x["issue"], x["pr"], x["head"], x["ci_run"])
        for x in manifest["prospective_entries"]
    ) == tuple((x[1], x[2], x[3], x[4]) for x in EXPECTED)
    assert manifest["prospective_entries"][1]["source_type"] == (
        "DISJOINT_OFFLINE_S17_FAKE_AND_B11_SIM"
    )


def test_adjacency_all_explicit_Drafts_not_main_and_no_sibling_link():
    manifest = read_frozen_manifest()
    records = manifest["prospective_entries"]
    assert records[0]["base"] == manifest["authority"]["S17"]
    for older, newer in zip(records, records[1:]):
        assert newer["base"] == older["head"]
    assert records[-1]["head"] == manifest["authority"]["B19_exact"]
    assert records[-1]["head"] != manifest["authority"]["main"]
    assert manifest["authority"]["read_only_lane_C"] == 432
    assert not any(r["production_authority"] for r in records)
    assert not any(r["actual_llm_l2"] for r in records)


@pytest.mark.parametrize("step", range(9))
def test_missing_or_duplicate_or_reordered_lineage_is_fail_closed(step):
    m = read_frozen_manifest()
    del m["prospective_entries"][step]
    with pytest.raises(InvalidFrozenEvidence, match="nine|9"):
        check_frozen_evidence(m)
    m = read_frozen_manifest()
    m["prospective_entries"][step]["step"] = "B19"
    if step != 8:
        with pytest.raises(InvalidFrozenEvidence, match="receipt"):
            check_frozen_evidence(m)


@pytest.mark.parametrize("field,forge", [
    ("head", "0" * 40),
    ("base", "f" * 40),
    ("ci_run", 0),
    ("classification", "PHYSICAL_L2_QUALIFIED"),
    ("source_type", "AUTHENTICATED_PHYSICAL_MINECRAFT"),
    ("production_authority", True),
    ("actual_llm_l2", True),
    ("cheap_comparator_no_worse", False),
])
def test_tampered_evidence_record_cannot_inflate_claim(field, forge):
    m = read_frozen_manifest()
    m["prospective_entries"][5][field] = forge
    with pytest.raises(InvalidFrozenEvidence, match="receipt"):
        check_frozen_evidence(m)


def test_explicit_positive_results_from_cheapest_methods_are_preserved():
    r = synthesize()
    positives = r["distinct_cheap_positive_controls"]
    assert len(positives) == 5
    assert any("QUORUM_BEATS_FIRST_SHOT" in x for x in positives)
    assert any("DETERMINACY_REDUCES_SOURCE_ACTIONS" in x for x in positives)
    assert any("QUERY_CHOICE" in x for x in positives)
    assert any("REVERSE_SOURCE_ONLY_QUERY_ADVANTAGE" in x for x in positives)
    assert r["cheap_equal_or_better_comparator_count"] == 9
    assert r["offline_experiment_drafts"] == 9
    assert r["no_actual_world_model_gpu_spend"] is True


@pytest.mark.parametrize("claim", PROMOTIONS)
def test_every_production_l2_l1_l0_claim_denied_even_forged_certificates(claim):
    m = read_frozen_manifest()
    proof = tuple(MISSING_GATES) + ("FAKE_SIGNATURE", "FAKE_PHYSICAL_SRC")
    decision = promotion_gate(
        claim, caller_supplied_witnesses=proof, manifest=m,
    )
    assert decision.status == "BLOCKED_NO_INDEPENDENT_SOURCE_AUTHORITY"
    assert decision.missing_witnesses == MISSING_GATES
    assert decision.terminal == BOUNDED_TERMINAL
    assert decision.proposed_claim == claim
    assert asdict(decision)["status"] != "QUALIFIED"


def test_c15_static_mineflayer_endpoint_is_not_signed_goal_truth():
    m = read_frozen_manifest()
    m["authority"]["C15_static_endpoint_PR"] = 525
    m["authority"]["C15_static_head"] = (
        "5e738596b805522d8516b43fa1b7ee001bfc5b2b"
    )
    assert check_frozen_evidence(m).physical_s17_s11_source_qualified is False
    m["authority"]["C15_static_head"] = "c" * 40
    with pytest.raises(InvalidFrozenEvidence, match="authority"):
        check_frozen_evidence(m)


def test_any_new_positive_production_entry_or_deleted_precondition_rejected():
    m = read_frozen_manifest()
    m["disallowed_promotions"].remove("VERIFIED_L2_TO_L1_DISTILLATION")
    with pytest.raises(InvalidFrozenEvidence, match="promotion"):
        check_frozen_evidence(m)
    m = read_frozen_manifest()
    m["pending_physical_prerequisites"].remove(
        "NON_BYPASSABLE_PRODUCTION_S11_OWNER"
    )
    with pytest.raises(InvalidFrozenEvidence, match="conditions"):
        check_frozen_evidence(m)


def test_cannot_erase_cheap_quorum_or_cost_control_positive():
    m = read_frozen_manifest()
    m["bounded_generic_positive"][0] = "S10_ADVANTAGE_OVER_CHEAP"
    with pytest.raises(InvalidFrozenEvidence, match="positive"):
        check_frozen_evidence(m)
    m = read_frozen_manifest()
    m["bounded_generic_positive"].pop()
    with pytest.raises(InvalidFrozenEvidence, match="positive"):
        check_frozen_evidence(m)


def test_no_caller_supplied_admission_authority_and_unknown_promotions():
    with pytest.raises(InvalidFrozenEvidence, match="unknown"):
        promotion_gate("CERTIFY_REAL_MINECRAFT_WORLD")
    with pytest.raises(InvalidFrozenEvidence, match="token shape"):
        promotion_gate(PROMOTIONS[0], caller_supplied_witnesses=["FAKE"])
    with pytest.raises(InvalidFrozenEvidence, match="token shape"):
        promotion_gate(PROMOTIONS[0], caller_supplied_witnesses=(1,))


def test_invalid_manifest_body_main_or_missing_physical_limit_fail():
    with pytest.raises(InvalidFrozenEvidence, match="schema"):
        check_frozen_evidence({"schema": "PROMOTED"})
    m = read_frozen_manifest()
    m["authority"]["main"] = "f" * 40
    with pytest.raises(InvalidFrozenEvidence, match="authority"):
        check_frozen_evidence(m)
    m = read_frozen_manifest()
    m["limits"] = ["Everything is fully proven, no limits"]
    with pytest.raises(InvalidFrozenEvidence, match="Minecraft"):
        check_frozen_evidence(m)


def test_production_gate_does_not_depend_on_user_forged_approval_provenance():
    decision = promotion_gate(
        "PROMOTE_PRODUCTION_HABIT_OWNER",
        caller_supplied_witnesses=(
            "AUTHENTICATED_COMMON_PHYSICAL_ACTION_OUTCOME",
            "NON_BYPASSABLE_PRODUCTION_S11_OWNER",
            "CAUSALLY_DISCRIMINATING_HELDOUT_L2_VS_CHEAP",
            "MEASURED_COMPUTE_AND_CALIBRATED_BODY_COST_FOR_COST_CLAIMS",
        ),
    )
    assert decision.status == "BLOCKED_NO_INDEPENDENT_SOURCE_AUTHORITY"
    assert len(decision.missing_witnesses) == 4


def test_synthesis_is_repeatable_without_any_world_or_model_calls():
    a, b = synthesize(), synthesize()
    assert a == b
    assert len(a["blocked_promotions"]) == len(PROMOTIONS)
    assert not a["physical_s17_s11_bridge"]
    assert not a["native_l2_measured_gain"]
    assert not a["physical_resource_calibration"]


def test_synthesis_result_is_not_mutable_live_qualification():
    base = check_frozen_evidence(read_frozen_manifest())
    cloned = replace(base)
    assert cloned is not base and cloned == base
    assert not cloned.production_s11_owner_qualified
