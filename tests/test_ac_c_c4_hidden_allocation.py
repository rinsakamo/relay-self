"""C4 strict non-generative hidden-information and adaptation controls."""

from dataclasses import replace

import pytest

from experiments.ac_c_c4_hidden_allocation import (
    ARMS,
    MANIFEST_SHA256,
    Evidence,
    SourceWorld,
    State,
    admissible,
    decide,
    digest,
    frozen_manifest,
    generate,
    report,
    trajectory,
)


def test_frozen_manifest_and_seed_holdout():
    m = frozen_manifest()
    assert digest(m) == MANIFEST_SHA256
    assert m["seeds"]["heldout"] == [101, 103, 107, 109, 113]
    assert set(m["seeds"]["heldout"]).isdisjoint(m["seeds"]["calibration"])
    assert len(generate(101)) == 4 * 80
    assert generate(101) == generate(101)
    assert generate(101) != generate(103)


def test_e0_excludes_hidden_truth_regime_hint_and_oracle():
    w = SourceWorld(generate(101)[0])
    e = w.e0()
    assert isinstance(e, Evidence)
    for k in ("target", "latent_z", "medium_hint", "phase", "seed"):
        assert not hasattr(e, k)
    with pytest.raises(ValueError, match="ORACLE"):
        decide(e, "EVALUATOR_ORACLE", State())


def test_same_initial_evidence_cannot_determine_both_hidden_targets():
    a = generate(101)[0]
    b = replace(a, latent_z=1 - a.latent_z)
    assert SourceWorld(a).e0() == SourceWorld(b).e0()
    assert a.target != b.target


def test_source_fenced_result_once_no_forgery_or_wrong_mode():
    w = SourceWorld(generate(101)[0])
    e = w.e0()
    mode = "FAST" if admissible(e, "FAST") else "SLOW"
    if not admissible(e, mode):
        pytest.skip("frozen case has no feasible mode")
    receipt = w.issue(e, mode)
    with pytest.raises(ValueError, match="INVALID_OR_REPLAYED"):
        w.consume(replace(e, session="alien"), receipt, mode)
    with pytest.raises(ValueError, match="INVALID_OR_REPLAYED"):
        w.consume(e, replace(receipt, success=not receipt.success), mode)
    with pytest.raises(ValueError, match="INVALID_OR_REPLAYED"):
        w.consume(e, receipt, "MEDIUM" if mode == "FAST" else "FAST")
    assert w.consume(e, receipt, mode) is receipt
    with pytest.raises(ValueError, match="INVALID_OR_REPLAYED"):
        w.consume(e, receipt, mode)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, mode)


def test_unpaid_information_and_stale_e0_rejected():
    w = SourceWorld(generate(103)[0])
    e = w.e0()
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue(e, "SLOW", cheap_z=1)
    with pytest.raises(ValueError, match="STALE"):
        w.issue(replace(e, revision=1), "FAST")
    with pytest.raises(ValueError, match="STALE"):
        w.issue(replace(e, group=1 - e.group), "FAST")


def test_hard_health_deadline_hunger_scan_gates():
    e = Evidence("s", 0, 0, 1, 1, 2, 2, True, False)
    assert not any(admissible(e, mode) for mode in ("FAST", "MEDIUM", "SLOW", "OBSERVE"))
    assert decide(e, "LEARNED_ALLOC", State())[0] == "ABSTAIN"
    normal = replace(e, deadline=7, health=10)
    assert not admissible(normal, "SLOW")
    assert not admissible(normal, "OBSERVE")
    assert admissible(normal, "FAST")


def test_paid_medium_and_exact_diagnostics_revision_and_cost():
    from experiments.ac_c_c4_hidden_allocation import COST
    cases = generate(101)
    good = next(c for c in cases if (
        c.deadline >= 5 and c.health >= 6 and c.hunger >= 5 and c.scan_available
    ))
    for mode in ("FAST", "MEDIUM", "OBSERVE", "SLOW"):
        w = SourceWorld(good)
        e = w.e0()
        assert admissible(e, mode)
        r = w.consume(e, w.issue(e, mode), mode)
        assert r.terminal_revision == (1 if mode == "FAST" else 2)
        assert COST[mode][0] <= e.deadline
        assert r.success == (r.selected_action == r.observed_target)
        if mode in ("SLOW", "OBSERVE"):
            assert r.success


def test_feedback_applies_to_own_completed_receipt_only():
    good = next(c for c in generate(107) if c.health > 2)
    w = SourceWorld(good)
    e = w.e0()
    mode = "FAST"
    r = w.consume(e, w.issue(e, mode), mode)
    state = State()
    assert not state.fast_result
    w.apply_feedback(e, r, "LEARNED_NO_FEEDBACK", state)
    assert not state.fast_result
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.apply_feedback(e, r, "LEARNED_ALLOC", state)
    assert not state.fast_result
    for arm, attribute in (("LEARNED_ALLOC", "fast_result"), ("CHEAP_HISTORY", "z_history")):
        fresh = SourceWorld(good)
        e2 = fresh.e0()
        receipt = fresh.consume(e2, fresh.issue(e2, "FAST"), "FAST")
        s = State()
        with pytest.raises(ValueError, match="UNATTESTED"):
            fresh.apply_feedback(e2, replace(receipt), arm, s)
        fresh.apply_feedback(e2, receipt, arm, s)
        assert s.__getattribute__(attribute)[e2.group]


def test_simple_switch_is_cheap_source_matched_competitor():
    from collections import deque
    s = State()
    e = Evidence("s", 0, 0, 1, 7, 6, 10, False, True)
    mode, _ = decide(e, "SIMPLE_SWITCH", s)
    assert mode == "FAST"
    s.fast_result[0] = deque([False, False, True, False], maxlen=8)
    assert decide(e, "SIMPLE_SWITCH", s)[0] in ("SLOW", "OBSERVE")
    s.fast_result[0] = deque([True] * 8, maxlen=8)
    assert decide(e, "SIMPLE_SWITCH", s)[0] == "FAST"


def test_all_arms_own_heldout_actions_and_no_fabricated_success():
    for arm in ARMS:
        x = trajectory(101, arm)
        assert len(x["trace"]) == 320
        for phase in frozen_manifest()["phases"]:
            p = x["phases"][phase]
            assert p["success"] + p["wrong"] + p["abstain"] == 80
        assert len({row["session"] for row in x["trace"]}) == 320
        assert all(row["world_revision"] in (None, 1, 2) for row in x["trace"])


def test_reproducible_disjoint_reporting_and_feedback_ablation():
    a, b = report(), report()
    assert a == b
    assert a["manifest_sha256"] == MANIFEST_SHA256
    assert len(a["feedback_pairs"]) == 5
    for seed, row in a["feedback_pairs"].items():
        assert seed in ("101", "103", "107", "109", "113")
        assert 0 <= row["selection_divergences"] <= 320
    assert set(a["summaries"]) == {"calibration", "heldout"}
