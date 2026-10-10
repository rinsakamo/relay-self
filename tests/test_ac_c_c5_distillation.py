"""AC-C C5 deterministic policy distillation and World-source safety gates."""
from dataclasses import replace

import pytest

from experiments.ac_c_c5_distillation import (
    ARMS,
    MANIFEST_SHA,
    Evidence,
    State,
    World,
    bayes_decision,
    canonical_hash,
    cases,
    config,
    decide,
    run,
    run_arm,
    viable,
)


def test_manifest_frozen_and_no_shared_seed():
    m = config()
    assert canonical_hash(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [127, 131, 137]
    assert m["seeds"]["heldout"] == [139, 149, 151, 157, 163]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["primary_positive_gate"]["correct_over_simple_gate_at_least"] == 16


def test_cases_paired_deterministic_and_no_hidden_E0_leak():
    assert cases(139) == cases(139)
    assert cases(139) != cases(149)
    assert len(cases(139)) == 288
    a = cases(139)[0]
    e = World(a).evidence()
    for hidden in ("phase", "target", "latent_z", "medium_hint", "seed"):
        assert not hasattr(e, hidden)
    b = replace(a, latent_z=1 - a.latent_z)
    assert World(b).evidence() == e
    assert b.target != a.target


def test_reject_unpaid_knowledge_and_stale_source():
    subject = next(c for c in cases(149) if c.deadline >= 2 and c.health > 2)
    w = World(subject)
    e = w.evidence()
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue(e, "MEDIUM", z_guess=1)
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue(replace(e, revision=1), "CHEAP")
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue(replace(e, session="injected"), "CHEAP")


def test_consumption_feedback_identity_single_use():
    c = next(x for x in cases(151) if x.health > 2)
    w = World(c)
    e = w.evidence()
    r = w.issue(e, "CHEAP", z_guess=0)
    with pytest.raises(ValueError, match="UNCONSUMED"):
        w.retain(e, r, State(), "CHEAP_HISTORY")
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(e, replace(r), "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(e, r, "MEDIUM")
    assert w.consume(e, r, "CHEAP") is r
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(e, r, "CHEAP")
    state = State()
    w.retain(e, r, state, "CHEAP_HISTORY")
    assert state.history[e.group][-1] == (r.observed_target ^ (e.prefix.bit_count() & 1))
    with pytest.raises(ValueError, match="DUPLICATED"):
        w.retain(e, r, state, "CHEAP_HISTORY")
    with pytest.raises(ValueError, match="DUPLICATE_ISSUE"):
        w.issue(e, "CHEAP")


def test_hard_viability_and_ABSTAIN():
    e = Evidence("s", 0, 0, 2, 1, 2, 2, True, False)
    assert not any(viable(e, m) for m in ("CHEAP", "MEDIUM", "SCAN", "DEEP"))
    assert decide(e, "SIMPLE_GATE", State())[0] == "ABSTAIN"
    assert bayes_decision(e, State())[0] == "ABSTAIN"
    healthy = replace(e, health=9, deadline=6, scan_available=True)
    assert viable(healthy, "SCAN")
    assert not viable(healthy, "DEEP")


def test_feedback_prior_and_source_matched_strong_policy():
    from collections import deque
    s = State()
    e = Evidence("s", 0, 0, 2, 6, 9, 12, False, True)
    assert s.posterior(0) == (0.5, 0)
    mode0, *_ = decide(e, "SIMPLE_GATE", s)
    assert mode0 == "SCAN"
    s.history[0] = deque([1] * 12, maxlen=12)
    p, bit = s.posterior(0)
    assert bit == 1 and p > 0.75
    assert decide(e, "CHEAP_HISTORY", s)[0:2] == ("CHEAP", 1)
    assert decide(e, "SIMPLE_GATE", s)[0:2] == ("CHEAP", 1)
    with pytest.raises(ValueError, match="EVALUATOR"):
        decide(e, "EVALUATOR_ORACLE", s)


def test_cache_key_does_not_use_hidden_info_and_returns_identical_decision():
    e = Evidence("s", 0, 1, 2, 6, 9, 12, False, True)
    s = State()
    original = decide(e, "RESOURCE_BAYES", s)[0:2]
    first = decide(e, "CACHE_COMPILED", s)
    second = decide(replace(e, session="different"), "CACHE_COMPILED", s)
    assert first[0:2] == original
    assert second[0:2] == original
    assert first[2] is False
    assert second[2] is True
    assert len(s.cache) == 1


def test_all_frozen_arms_partition_all_opportunities():
    m = config()
    for arm in ARMS:
        a = run_arm(139, arm)
        assert len(a["trace"]) == 288
        assert len({r["session"] for r in a["trace"]}) == 288
        for phase in m["phases"]:
            p = a["phases"][phase]
            assert p["correct"] + p["wrong"] + p["abstain"] == 96
        assert all(r["terminal_revision"] in (None, 1, 2) for r in a["trace"])


def test_resource_vs_cached_source_matched_equivalence_multiple_seeds():
    for seed in [139, 149, 151, 157, 163]:
        res = run_arm(seed, "RESOURCE_BAYES")
        fast = run_arm(seed, "CACHE_COMPILED")
        assert [(r["session"], r["mode"], r["selected_z"], r["success"]) for r in res["trace"]] == [
            (r["session"], r["mode"], r["selected_z"], r["success"]) for r in fast["trace"]
        ]
        assert all(
            res["phases"][phase]["correct"] == fast["phases"][phase]["correct"]
            for phase in config()["phases"]
        )


def test_report_determinism_and_heldout_pairing():
    a, b = run(), run()
    assert a == b
    assert a["result_sha256"] == canonical_hash({
        k: v for k, v in a.items() if k != "result_sha256"
    })
    assert set(a["paired"]) == {"139", "149", "151", "157", "163"}
    for arm in ARMS:
        row = a["summaries"]["heldout"][arm]
        assert row["correct"] + row["wrong"] + row["abstain"] == 1440


def test_report_provenance_to_ci_warning_log():
    """Record frozen exact-head aggregate, not only pass/fail, in CI logs."""
    import json
    import warnings

    r = run()
    payload = {
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summaries"]["heldout"],
        "paired": r["paired"],
    }
    warnings.warn("C5_RESULT_JSON " + json.dumps(payload, sort_keys=True), UserWarning)
