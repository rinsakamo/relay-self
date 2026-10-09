"""Zero-model D4 Grand-Null/version-space tests; no physical operations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import permutations

import pytest

from experiments import counterfactual_d4_cost_world as d4

COUNTS = {
    "I_AND": (1, "IDENTIFIED", "DIRECT"),
    "I_NAND": (1, "IDENTIFIED", "DETOUR"),
    "O_SAFE": (2, "OUTCOME_EQUIVALENT", "DIRECT"),
    "O_HAZARD": (2, "OUTCOME_EQUIVALENT", "DETOUR"),
    "D_LOW": (18, "DECISION_EQUIVALENT", "DETOUR"),
    "D_HIGH": (18, "DECISION_EQUIVALENT", "DETOUR"),
    "A_SAFE": (9, "DECISION_AMBIGUOUS", "SCOUT"),
    "A_HAZARD": (9, "DECISION_AMBIGUOUS", "SCOUT"),
}


def cases_by_id():
    return {c.case_id: c for c in d4.qualified_cases()}


def test_d4_exact_frozen_manifest_and_216_rules():
    assert d4.MANIFEST_VERSION == "CF-D4-RESOURCE-GATE216-v1"
    assert d4.manifest_sha256() == (
        "2f2f300f43f130ecfb84283fc685775e98a1cf8118209bcd9f4488dfd16173a3"
    )
    d4.assert_manifest()
    clone = d4.manifest()
    clone["actions"].append("FLY")
    with pytest.raises(d4.D4ContractError, match="drift"):
        d4.assert_manifest(clone)
    assert len(d4.HYPOTHESES) == 6 ** 3 == 216
    assert len(set(d4.HYPOTHESES)) == 216
    assert len(d4.GATES) == 6
    assert d4.manifest()["model_calls"] == 0


def test_complete_8_case_strata_and_exact_bayes_cheap_predictions():
    all_cases = d4.qualified_cases()
    assert len(all_cases) == 8
    assert set(c.case_id for c in all_cases) == set(COUNTS)
    measured = set()
    for case in all_cases:
        size, label, action = COUNTS[case.case_id]
        e = d4.evidence(case)
        d4.assert_source(case, e)
        versions, counter = d4.version_space(e)
        assert len(versions) == size
        assert case.truth in versions
        assert d4.stratum(e) == label == case.expected
        assert d4.cheap_choice(e) == action
        assert counter.hypotheses_tested == 216
        assert 216 <= counter.episode_comparisons <= 432
        assert counter.gate_evaluations == 3 * counter.episode_comparisons
        assert case.test not in case.training
        assert len(set(case.training)) == 2
        measured.add(label)
        assert all(len(h) == 3 for h in versions)
    assert measured == {
        "IDENTIFIED", "OUTCOME_EQUIVALENT",
        "DECISION_EQUIVALENT", "DECISION_AMBIGUOUS",
    }


def test_24_action_counterfactual_interventions_and_replay_order():
    subjects, outcomes = 0, 0
    all_orders = tuple(permutations(d4.ACTIONS))
    assert len(all_orders) == 6
    for case in d4.qualified_cases():
        baseline = d4.all_interventions(case)
        before = deepcopy(case)
        subjects += 1
        for order in all_orders:
            assert d4.all_interventions(case, order) == baseline
        assert case == before
        for action, result in baseline.items():
            assert result == d4.intervention(case, action)
            assert result.utility == 20 - result.ticks - result.damage
            assert result.action == action
            outcomes += 1
    assert (subjects, outcomes) == (8, 24)


def test_identical_source_evidence_can_be_decision_ambiguous():
    a, b = cases_by_id()["A_SAFE"], cases_by_id()["A_HAZARD"]
    e_a, e_b = d4.evidence(a), d4.evidence(b)
    assert e_a == e_b
    assert d4.stratum(e_a) == "DECISION_AMBIGUOUS"
    assert d4.cheap_choice(e_a) == "SCOUT" == d4.cheap_choice(e_b)
    full_a = d4.all_interventions(a)
    full_b = d4.all_interventions(b)
    assert full_a["DIRECT"].utility == 17
    assert full_b["DIRECT"].utility == 3
    assert max(full_a, key=lambda action: full_a[action].utility) == "DIRECT"
    assert max(full_b, key=lambda action: full_b[action].utility) == "DETOUR"
    assert d4.cheap_expected_utilities(e_a)["SCOUT"] > Fraction(13)


def test_different_hidden_hazards_same_optimal_action_is_not_identification():
    a, b = cases_by_id()["D_LOW"], cases_by_id()["D_HIGH"]
    assert d4.evidence(a) == d4.evidence(b)
    assert d4.forecast(a.truth, a.test) != d4.forecast(b.truth, b.test)
    assert d4.stratum(d4.evidence(a)) == "DECISION_EQUIVALENT"
    assert d4.cheap_choice(d4.evidence(a)) == "DETOUR"
    assert d4.intervention(a, "DIRECT").utility != d4.intervention(
        b, "DIRECT"
    ).utility


def test_hidden_rule_and_source_id_never_model_facing():
    for case in d4.qualified_cases():
        payload = d4.evidence(case)
        assert set(payload) == {
            "currentCues", "candidateGates", "episodes",
            "actions", "utility",
        }
        assert case.case_id not in d4.canonical(payload)
        assert "trueRule" not in d4.canonical(payload)
        assert "sourceSession" not in d4.canonical(payload)
        assert "oracleAction" not in d4.canonical(payload)
        assert d4.parse_public(payload)[0] == case.test


def test_wrong_source_session_episode_is_not_admissible():
    a, b = cases_by_id()["A_SAFE"], cases_by_id()["A_HAZARD"]
    assert d4.source_episodes(a)[0].observed == d4.source_episodes(b)[0].observed
    assert d4.source_episodes(a)[0].session != d4.source_episodes(b)[0].session
    with pytest.raises(d4.D4ContractError, match="lineage"):
        d4.evidence(a, d4.source_episodes(b))
    forged = d4.SourceEpisode(
        a.case_id, d4.source_episodes(a)[0].cue, "111"
    )
    with pytest.raises(d4.D4ContractError, match="lineage"):
        d4.evidence(a, (forged, d4.source_episodes(a)[1]))


@pytest.mark.parametrize("extra", [
    "sourceSession", "trueRule", "horizonTruth", "future_hazards",
    "case_id", "gold_action", "oracleScore", "arm", "mapping",
    "modelId", "observedFuture", "scientificClassification",
])
def test_evaluator_or_semantic_label_injection_fails_closed(extra):
    c = cases_by_id()["I_AND"]
    e = d4.evidence(c)
    e[extra] = "leak"
    with pytest.raises(d4.D4ContractError):
        d4.parse_public(e)
    with pytest.raises(d4.D4ContractError):
        d4.assert_source(c, e)


def test_nested_source_changes_fail_closed_even_when_shape_valid():
    c = cases_by_id()["I_AND"]
    tamper = []
    fake = d4.evidence(c)
    fake["episodes"][0]["hazards"] = "111"
    tamper.append(fake)
    fake = d4.evidence(c)
    fake["actions"]["DIRECT"]["ticks"] = 1
    tamper.append(fake)
    fake = d4.evidence(c)
    fake["episodes"][0]["cue"] = "0011"
    tamper.append(fake)
    for fake in tamper:
        with pytest.raises(d4.D4ContractError):
            d4.assert_source(c, fake)


def test_contradictory_qualified_shape_has_no_version_space():
    c = cases_by_id()["I_AND"]
    bad = d4.evidence(c)
    # Distinct training cues with identical first gate inputs (00),
    # but contradictory first-site outcomes. This does not leak test.
    bad["episodes"] = [
        {"cue": "0000", "hazards": "000"},
        {"cue": "0010", "hazards": "100"},
    ]
    candidates, counts = d4.version_space(bad)
    assert candidates == ()
    assert counts.hypotheses_tested == 216
    assert d4.stratum(bad) == "INCONSISTENT"
    with pytest.raises(d4.D4ContractError, match="INCONSISTENT"):
        d4.cheap_choice(bad)
    with pytest.raises(d4.D4ContractError):
        d4.assert_source(c, bad)


def test_invalid_episodes_and_training_test_overlap_rejected():
    c = cases_by_id()["I_AND"]
    for bad_cue in ("0001", "0022", [0, 0, 0, 0], True):
        fake = d4.evidence(c)
        fake["episodes"][0]["cue"] = bad_cue
        with pytest.raises(d4.D4ContractError):
            d4.parse_public(fake)
    fake = d4.evidence(c)
    fake["episodes"][0]["hazards"] = "00"
    with pytest.raises(d4.D4ContractError):
        d4.parse_public(fake)


def test_no_action_or_source_mutation_and_no_model_transport():
    c = cases_by_id()["I_AND"]
    with pytest.raises(FrozenInstanceError):
        c.truth = ("NAND", "AND", "AND")
    original = deepcopy(c)
    d4.all_interventions(c)
    assert c == original
    for name in ("FLY", "direct", None, 123):
        with pytest.raises(d4.D4ContractError):
            d4.intervention(c, name)
    for order in (
        ("DIRECT", "DIRECT", "DETOUR"),
        ("DIRECT", "DETOUR"),
        ("DIRECT", "DETOUR", "HIDE"),
    ):
        with pytest.raises(d4.D4ContractError):
            d4.all_interventions(c, order)
