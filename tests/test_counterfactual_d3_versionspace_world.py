"""Pure #427 D3 compositional version-space regressions, no model calls."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from experiments import counterfactual_d3_versionspace_world as d3


def by_id() -> dict[str, d3.Case]:
    return {case.case_id: case for case in d3.all_cases()}


EXPECTED = {
    "I_AND": ("AND",), "I_NAND": ("NAND",),
    "O_OR": ("OR", "XOR"), "O_NOR": ("NOR", "XNOR"),
    "D_AND": ("AND", "OR", "XOR"),
    "D_NAND": ("XOR", "NAND"),
    "A_AND": ("AND", "XNOR"), "A_XNOR": ("AND", "XNOR"),
}

EXPECTED_CHOICES = {
    "I_AND": "DIRECT", "I_NAND": "DETOUR",
    "O_OR": "DIRECT", "O_NOR": "DETOUR",
    "D_AND": "DETOUR", "D_NAND": "DETOUR",
    "A_AND": "SCOUT", "A_XNOR": "SCOUT",
}


def test_exact_frozen_manifest_sha_and_strict_defensive_copy():
    assert d3.VERSION == "CF-D3-COMPOSITIONAL-VERSIONSPACE-v1"
    assert d3.EXPECTED_MANIFEST_SHA256 == (
        "1390326e9dc2ea753d33291e62e076249309ce2d60204608d3d911b16e246eb3"
    )
    assert d3.manifest_sha256() == d3.EXPECTED_MANIFEST_SHA256
    d3.assert_manifest()
    changed = d3.frozen_manifest()
    changed["actions"][0] = "ATTACK"
    with pytest.raises(d3.D3ContractError, match="drift"):
        d3.assert_manifest(changed)
    assert d3.frozen_manifest()["actions"][0] == "DIRECT"


def test_all_eight_cases_and_exact_version_space_strata():
    cases = d3.all_cases()
    assert len(cases) == 8
    assert len(set(c.case_id for c in cases)) == 8
    assert set(EXPECTED) == {c.case_id for c in cases}
    tally = {key: 0 for key in d3.STRATA}
    for case in cases:
        assert case.expected_stratum in d3.STRATA
        evidence = d3.predictor_evidence(case)
        d3.assert_source_bound(case, evidence)
        assert d3.version_space(evidence) == EXPECTED[case.case_id]
        assert d3.identifiability_stratum(evidence) == case.expected_stratum
        assert d3.bayes_choice(evidence) == EXPECTED_CHOICES[case.case_id]
        assert case.true_rule in d3.version_space(evidence)
        assert case.test_cues not in tuple(x[:3] for x in case.history)
        tally[case.expected_stratum] += 1
    assert tally == {
        "IDENTIFIED": 2, "OUTCOME_EQUIVALENT": 2,
        "DECISION_EQUIVALENT": 2, "DECISION_AMBIGUOUS": 2,
        "INCONSISTENT": 0,
    }


def test_exactly_24_independent_three_action_outcomes_replay_in_six_orders():
    total = 0
    orders = d3.ordered_action_permutations()
    assert len(orders) == 6
    assert len(set(orders)) == 6
    for case in d3.all_cases():
        baseline = d3.independent_interventions(case)
        before = deepcopy(case)
        assert set(baseline) == set(d3.ACTIONS)
        for order in orders:
            assert d3.independent_interventions(case, order) == baseline
        assert case == before
        for a, result in baseline.items():
            assert result.action == a
            assert result == d3.intervene(case, a)
            assert result.utility == 20 - result.ticks - result.health_loss
            assert result.ticks in (2, 3, 5, 6)
            assert result.health_loss in (0, 8, 16)
            total += 1
    assert total == 24


@pytest.mark.parametrize(("case_id", "truth_hazards", "oracle"), [
    ("I_AND", (0, 0), "DIRECT"),
    ("I_NAND", (1, 1), "DETOUR"),
    ("O_OR", (0, 0), "DIRECT"),
    ("O_NOR", (1, 1), "DETOUR"),
    ("D_AND", (0, 1), "DETOUR"),
    ("D_NAND", (1, 1), "DETOUR"),
    ("A_AND", (0, 0), "DIRECT"),
    ("A_XNOR", (1, 1), "DETOUR"),
])
def test_heldout_truth_and_full_information_oracle(case_id, truth_hazards, oracle):
    case = by_id()[case_id]
    assert d3.future_hazards(case.true_rule, case.test_cues) == truth_hazards
    assert d3.full_information_choice(case.true_rule, case.test_cues) == oracle
    assert d3.intervene(case, oracle).utility == max(
        d3.independent_interventions(case)[a].utility for a in d3.ACTIONS
    )


def test_identifiability_does_not_require_unique_rule_when_outcomes_match():
    for name in ("O_OR", "O_NOR"):
        case = by_id()[name]
        evidence = d3.predictor_evidence(case)
        assert len(d3.version_space(evidence)) == 2
        assert d3.identifiability_stratum(evidence) == "OUTCOME_EQUIVALENT"
        # Model-facing evidence cannot reveal which latent candidate is truth.
        assert case.true_rule not in evidence.values()


def test_different_future_outcomes_can_have_same_optimal_action():
    for name in ("D_AND", "D_NAND"):
        case = by_id()[name]
        evidence = d3.predictor_evidence(case)
        compatible = d3.version_space(evidence)
        assert len(compatible) >= 2
        assert d3.identifiability_stratum(evidence) == "DECISION_EQUIVALENT"
        assert all(
            d3.full_information_choice(rule, case.test_cues) == "DETOUR"
            for rule in compatible
        )
        assert len({
            d3.future_hazards(rule, case.test_cues) for rule in compatible
        }) > 1


def test_same_source_evidence_different_hidden_world_choice_is_underdetermined():
    a = by_id()["A_AND"]
    b = by_id()["A_XNOR"]
    payload_a = d3.predictor_evidence(a)
    payload_b = d3.predictor_evidence(b)
    assert payload_a == payload_b
    assert d3.version_space(payload_a) == ("AND", "XNOR")
    assert d3.identifiability_stratum(payload_a) == "DECISION_AMBIGUOUS"
    assert d3.full_information_choice(a.true_rule, a.test_cues) == "DIRECT"
    assert d3.full_information_choice(b.true_rule, b.test_cues) == "DETOUR"
    assert d3.bayes_choice(payload_a) == d3.bayes_choice(payload_b) == "SCOUT"
    assert d3.bayes_utilities(payload_a) == {
        "DIRECT": Fraction(10),
        "DETOUR": Fraction(15),
        "SCOUT": Fraction(31, 2),
    }
    assert d3.predictive_hazard_probabilities(payload_a) == (
        Fraction(1, 2), Fraction(1, 2)
    )


def test_corrupt_source_history_is_not_a_valid_world_episode():
    negative = d3.negative_case()
    assert negative.expected_stratum == "INCONSISTENT"
    assert negative not in d3.all_cases()
    with pytest.raises(d3.D3ContractError):
        d3.predictor_evidence(negative)
    valid = d3.predictor_evidence(by_id()["I_AND"])
    bad = deepcopy(valid)
    bad["presentCues"] = "001"  # frozen negative case, distinct from prior 000
    bad["pastDirectEpisodes"] = [
        {"cues": "000", "observedHazards": "00"},
        {"cues": "000", "observedHazards": "11"},
    ]
    assert d3.version_space(bad) == ()
    assert d3.identifiability_stratum(bad) == "INCONSISTENT"
    with pytest.raises(d3.D3ContractError, match="INCONSISTENT"):
        d3.bayes_choice(bad)
    with pytest.raises(d3.D3ContractError):
        d3.assert_source_bound(by_id()["I_AND"], bad)


def test_past_episode_authenticity_is_separate_from_json_shape():
    case = by_id()["A_AND"]
    swapped = d3.trusted_episodes(by_id()["A_XNOR"])
    assert swapped[0].cues == d3.trusted_episodes(case)[0].cues
    assert swapped[0].observed == d3.trusted_episodes(case)[0].observed
    with pytest.raises(d3.D3ContractError, match="lineage"):
        d3.predictor_evidence(case, swapped)
    forged = d3.Episode(
        case.case_id, d3.trusted_episodes(case)[0].cues, "11"
    )
    with pytest.raises(d3.D3ContractError):
        d3.predictor_evidence(case, (forged,))
    assert d3.predictor_evidence(case) == d3.predictor_evidence(case)


@pytest.mark.parametrize("field", [
    "trueRule", "sourceSession", "case ID", "heldout h1/h2",
    "future consequence vector", "goldAction", "outcome",
    "executionIndex", "model", "arm", "mapping", "seed",
])
def test_gold_and_control_metadata_injection_fail_closed(field):
    case = by_id()["I_AND"]
    evidence = d3.predictor_evidence(case)
    evidence[field] = "leaked"
    with pytest.raises(d3.D3ContractError):
        d3.version_space(evidence)
    with pytest.raises(d3.D3ContractError):
        d3.assert_source_bound(case, evidence)


def test_nested_source_mutation_and_future_result_leakage_fail_closed():
    case = by_id()["D_NAND"]
    for field, content in [
        ("hypothesisFamily", ["NAND"]),
        ("pastDirectEpisodes", [{"cues": "011", "observedHazards": "11"}]),
        ("actionContract", {"DIRECT": {"ticks": 1}}),
        ("terminalUtility", "free reward"),
    ]:
        p = d3.predictor_evidence(case)
        p[field] = content
        with pytest.raises(d3.D3ContractError):
            d3.assert_source_bound(case, p)
        if field != "pastDirectEpisodes":
            with pytest.raises(d3.D3ContractError):
                d3.version_space(p)
        else:
            # A structurally valid but forged past record is rejected
            # by the independent source owner, not by pure shape parsing.
            assert d3.version_space(p) != d3.version_space(
                d3.predictor_evidence(case)
            )


def test_forecast_shape_rejects_bool_or_nonbinary_cues_and_observations():
    case = by_id()["O_OR"]
    for tamper in (
        {"cues": "002", "observedHazards": "01"},
        {"cues": "001", "observedHazards": "02"},
        {"cues": "001", "observedHazards": [0, 1]},
    ):
        p = d3.predictor_evidence(case)
        p["pastDirectEpisodes"] = [tamper]
        with pytest.raises(d3.D3ContractError):
            d3.version_space(p)
    p = d3.predictor_evidence(case)
    p["presentCues"] = [0, True, 0]
    with pytest.raises(d3.D3ContractError):
        d3.version_space(p)


def test_only_matching_three_action_permutation_is_admissible():
    case = by_id()["A_AND"]
    for bad in (
        ("DIRECT", "DIRECT", "SCOUT"),
        ("DETOUR", "SCOUT"),
        ("DIRECT", "DETOUR", "FLY"),
        ["DIRECT", "DETOUR", "SCOUT"],
    ):
        with pytest.raises(d3.D3ContractError):
            d3.independent_interventions(case, bad)
    for action in ("FLY", "direct", True, None):
        with pytest.raises(d3.D3ContractError):
            d3.intervene(case, action)


def test_world_subject_is_immutable_and_no_model_transport_exists():
    case = by_id()["I_AND"]
    with pytest.raises(FrozenInstanceError):
        case.true_rule = "NAND"
    assert d3.VERSION.endswith("-v1")
    assert d3.frozen_manifest()["future_science_calls"] == 0
    assert d3.intervene(case, "DIRECT") == d3.intervene(case, "DIRECT")
