"""C12 prospective public-cue reliability, source provenance, and Grand Null."""
from dataclasses import replace

import pytest

from experiments.ac_c_c12_reliability import (
    ARMS,
    E0,
    MANIFEST_SHA,
    HiddenCase,
    Retention,
    World,
    accuracy_majority,
    canonical_hash,
    config,
    fusion,
    generate,
    report,
    select,
    trajectory,
    viable,
)


def case(session, *, z=0, blocked=False, exact=True,
         cues=(1, 0, 1), health=8, deadline=3):
    return HiddenCase(
        session, "sensor_drift", 0, 0, cues, z,
        blocked, exact, health, deadline, 12, False,
    )


def issued(w, guess=0, mode="L1_GROUP"):
    e = w.e0()
    r = w.consume(e, mode, w.issue(e, mode, guess))
    return e, r


def test_frozen_identity_and_independent_heldout_seeds():
    m = config()
    assert canonical_hash(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [467, 479, 487]
    assert m["seeds"]["heldout"] == [491, 499, 503, 509, 521]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["adoption_gate"]["learned_vs_majority_correct_at_least"] == 40
    assert m["learning"]["source_label_only"]


def test_hidden_world_state_and_epoch_are_not_public_evidence():
    c = case("opaque", z=0, blocked=True, exact=False)
    other = replace(c, z=1, blocked=False, exact_available=True)
    e = World(c).e0()
    assert isinstance(e, E0)
    assert World(other).e0() == e
    for name in ("epoch", "z", "blocked", "exact_available", "target",
                 "correct", "label_z", "feedback_type", "obstruction"):
        assert not hasattr(e, name)
    # Generated session IDs must not visibly encode the epoch.
    assert "sensor_drift" not in generate(491)[300].session
    assert "491" not in generate(491)[300].session


def test_reproducible_paired_world_and_drift_manifest():
    assert generate(491) == generate(491)
    assert generate(491) != generate(499)
    assert len(generate(491)) == 600
    assert config()["cue_reliability"]["sensor_drift"] == 0.52
    assert config()["cue_reliability"]["rule_shift"] == 0.82


def test_ambiguous_movement_has_distinct_hidden_causes_same_receipt():
    a = World(case("same", z=0, blocked=True, exact=False))
    b = World(case("same", z=1, blocked=False, exact=False))
    e0a, ra = issued(a, guess=0)
    e0b, rb = issued(b, guess=0)
    assert e0a == e0b
    assert ra == rb
    assert ra.moved is False and ra.feedback_type == "MISSING"
    assert ra.label_z is None
    assert a.retain(e0a, ra, Retention(), enabled=True) is False
    assert b.retain(e0b, rb, Retention(), enabled=True) is False
    assert a.evaluate()[0] is True
    assert b.evaluate()[0] is False


def test_receipts_are_mode_evidence_session_and_identity_bound():
    w = World(case("source", z=1, exact=True))
    e = w.e0()
    raw = w.issue(e, "L1_GROUP", 0)
    state = Retention()
    with pytest.raises(ValueError, match="PREMATURE"):
        w.retain(e, raw, state, enabled=True)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(e, "L1_GROUP", replace(raw))
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(replace(e, session="foreign"), "L1_GROUP", raw)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(replace(e, revision=1), "L1_GROUP", raw)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(e, "L1_MAJORITY", raw)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, "L1_GROUP", 0)
    assert w.consume(e, "L1_GROUP", raw) is raw
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume(e, "L1_GROUP", raw)
    assert w.retain(e, raw, state, enabled=True) is True
    assert state.group_bit(0) == 1
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.retain(e, raw, state, enabled=True)


def test_missing_never_updates_and_exact_source_alone_updates():
    no = World(case("missing", z=1, exact=False))
    e, r = issued(no)
    s = Retention()
    assert not no.retain(e, r, s, enabled=True)
    assert s.signature() == ((), ()) or s.signature() == (((), ()), ())
    assert r.label_z is None
    assert no.evaluate()[0] is False
    yes = World(case("exact", z=0, blocked=False, exact=True, cues=(1, 0, 0)))
    e2, r2 = issued(yes)
    assert yes.retain(e2, r2, s, enabled=True)
    assert list(s.group_labels[0]) == [0]
    assert list(s.cue_matches) == [2]


def test_label_spoof_and_unknown_quality_fail_closed():
    w = World(case("truth", z=0, exact=False))
    e = w.e0()
    issued_receipt = w.issue(e, "L1_GROUP", 0)
    for fake in (
        replace(issued_receipt, feedback_type="EXACT", label_z=1),
        replace(issued_receipt, feedback_type="MISSING", label_z=1),
        replace(issued_receipt, feedback_type="WEAK", label_z=0),
    ):
        with pytest.raises(ValueError, match="FORGED"):
            w.consume(e, "L1_GROUP", fake)


def test_sensor_rate_derived_from_labelled_public_bits_only():
    s = Retention()
    assert s.reliability() == pytest.approx(.78)
    w = World(case("cal", z=1, exact=True, cues=(1, 1, 1)))
    e, r = issued(w)
    assert w.retain(e, r, s, enabled=True)
    expect = (3+4*.78)/(3+4)
    assert s.reliability() == pytest.approx(expect)
    assert len(s.cue_matches) == 1


def test_strong_simple_majority_and_fusion_controls():
    s = Retention()
    e = World(case("majority", cues=(0, 1, 1))).e0()
    assert select(e, s, "L1_MAJORITY", warmup=False) == ("L1_MAJORITY", 1)
    assert select(e, s, "FROZEN_MAJORITY", warmup=False) == ("L1_MAJORITY", 1)
    assert fusion(.5, .78, (0, 1, 1)) == 1
    assert fusion(.5, .78, (0, 0, 1)) == 0
    assert accuracy_majority(.82) > accuracy_majority(.52)
    assert 0 < s.group_p1(0) < 1


def test_safe_first_viability_and_denial():
    e = World(case("safe")).e0()
    assert viable(e, "FIXED_FUSION")
    assert select(e, Retention(), "LEARNED_RELIABILITY_GATE", warmup=False)[0] != "ABSTAIN"
    unsafe = replace(e, health=2)
    assert not viable(unsafe, "L1_GROUP")
    assert select(unsafe, Retention(), "LEARNED_RELIABILITY_GATE", warmup=False) == ("ABSTAIN", 0)
    late = replace(e, deadline=0)
    assert not viable(late, "LEARNED_FUSION")
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        World(case("unsafe", health=2)).issue(
            World(case("unsafe", health=2)).e0(), "L1_GROUP", 0
        )


def test_all_arms_identical_warmup_before_any_evaluation():
    trials = {a: trajectory(491, a) for a in ARMS}
    origin = trials[ARMS[0]]
    baseline = [(r["session"], r["mode"], r["guess"], r["admitted_exact"])
                for r in origin["trace"] if r["epoch"] == "warmup"]
    for arm, t in trials.items():
        assert t["warmup_signature"] == origin["warmup_signature"]
        assert [(r["session"], r["mode"], r["guess"], r["admitted_exact"])
                for r in t["trace"] if r["epoch"] == "warmup"] == baseline, arm


def test_frozen_negative_and_unlearning_majority_baselines():
    f = trajectory(491, "FROZEN_GROUP")
    n = trajectory(491, "NO_FEEDBACK_GROUP")
    assert f["phases"] == n["phases"]
    assert [(x["session"], x["guess"], x["mode"])
            for x in f["trace"]] == [(x["session"], x["guess"], x["mode"])
                                    for x in n["trace"]]
    frozen = trajectory(491, "FROZEN_MAJORITY")
    adapt = trajectory(491, "L1_MAJORITY")
    assert [(x["session"], x["guess"], x["mode"])
            for x in frozen["trace"]] == [(x["session"], x["guess"], x["mode"])
                                         for x in adapt["trace"]]


def test_source_history_identical_between_online_policy_arms():
    left = trajectory(491, "ADAPT_GROUP")
    right = trajectory(491, "LEARNED_RELIABILITY_GATE")
    assert [r["source_sig_after"] for r in left["trace"]] == [
        r["source_sig_after"] for r in right["trace"]
    ]


def test_exact_head_ci_report_reproducible_and_preregistered_denominator():
    r = report()
    assert r == report()
    assert r["result_sha256"] == canonical_hash({
        key: val for key, val in r.items() if key != "result_sha256"
    })
    assert set(r["paired"]) == {"491", "499", "503", "509", "521"}
    for a in ARMS:
        h = r["summary"]["heldout"][a]
        assert h["correct"]+h["wrong"]+h["abstain"] == 2400
        assert set(h["mean_end_cue_reliability"]) == set(config()["epochs"])
        assert h["work"]+h["selector_work"] >= h["work"]


def test_machine_readable_frozen_result_in_exact_head_ci():
    import json
    import warnings

    data = report()
    warnings.warn("C12_RESULT_JSON " + json.dumps({
        "manifest_sha256": data["manifest_sha256"],
        "result_sha256": data["result_sha256"],
        "heldout": data["summary"]["heldout"],
        "paired": data["paired"],
    }, sort_keys=True), UserWarning)
