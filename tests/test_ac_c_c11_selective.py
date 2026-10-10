"""C11 model-free selective-compute preregistered and fail-closed tests."""
from dataclasses import replace

import pytest

from experiments.ac_c_c11_selective import (
    ARMS,
    MANIFEST_SHA,
    Evidence,
    HiddenCase,
    Learned,
    World,
    config,
    deep_bit,
    expected_deep_accuracy,
    generate,
    hash_obj,
    report,
    select,
    trajectory,
    value_of_compute,
    viable,
)


def example(
    session: str, *, z: int = 1, bits: tuple[int, int, int] = (1, 0, 1),
    exact: bool = True, blocked: bool = False,
    health: int = 8, deadline: int = 5,
) -> HiddenCase:
    return HiddenCase(
        session, "shift", 0, 0, bits, z, blocked, exact,
        deadline, health, 12, False,
    )


def verified(w: World, mode="L1_GROUP", zguess=0):
    e = w.e0()
    return e, w.consume(e, mode, w.issue(e, mode, zguess))


def test_protocol_identity_and_new_seed_sets():
    m = config()
    assert hash_obj(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [431, 433, 439]
    assert m["seeds"]["heldout"] == [443, 449, 457, 461, 463]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["public_cue_reliability"]["sensor_drift"] == 0.55


def test_source_visible_e0_has_no_future_or_hidden_truth():
    c = example("same", z=0, blocked=True, exact=False)
    other = replace(c, z=1, blocked=False, exact=True)
    assert World(c).e0() == World(other).e0()
    e = World(c).e0()
    assert isinstance(e, Evidence)
    for attr in ("hidden_z", "z", "epoch", "exact_available", "obstructed",
                 "blocked", "correct", "target", "moved", "label_z"):
        assert not hasattr(e, attr)


def test_reproducible_exogenous_cases_and_holdout_length():
    assert generate(443) == generate(443)
    assert generate(443) != generate(449)
    assert len(generate(443)) == 5*120
    assert all(len(x.public_cues) == 3 for x in generate(443))


def test_l2_compute_is_only_public_e0_math():
    e = World(example("public", bits=(1, 1, 0))).e0()
    state = Learned()
    mode, decision = select(e, state, "ALWAYS_L2", warmup=False)
    assert (mode, decision) == ("L2_BAYES", deep_bit(.5, e.public_cues))
    assert decision == 1
    assert deep_bit(.5, (0, 0, 1)) == 0
    assert expected_deep_accuracy(.5) > .85
    assert value_of_compute(.5) > 0
    # No receipt, hidden z, World method, or inspection is read by select.


def test_nominal_sensor_drift_is_not_passed_as_phase_information():
    assert not hasattr(World(example("source")).e0(), "public_cue_reliability")
    assert config()["compute"]["nominal_public_cue_reliability"] == .78
    assert deep_bit(.5, (1, 1, 0)) == 1


def test_unsafe_L2_falls_back_to_source_cheap_or_abstains():
    e = World(example("short", deadline=1)).e0()
    assert viable(e, "L1_GROUP")
    assert not viable(e, "L2_BAYES")
    assert select(e, Learned(), "ALWAYS_L2", warmup=False)[0] == "L1_GROUP"
    exhausted = replace(e, health=2)
    assert not viable(exhausted, "L1_GROUP")
    assert select(exhausted, Learned(), "VALUE_GATE", warmup=False)[0] == "ABSTAIN"
    hungry = replace(e, deadline=5, hunger=2)
    assert not viable(hungry, "L2_BAYES")


def test_source_world_issue_receipt_identity_prohibits_forgery_and_replay():
    w = World(example("source"))
    e = w.e0()
    r = w.issue(e, "L1_GROUP", 0)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(e, "L1_GROUP", replace(r))
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(replace(e, session="other"), "L1_GROUP", r)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(replace(e, revision=2), "L1_GROUP", r)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume(e, "L2_BAYES", r)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, "L1_GROUP", 0)
    assert w.consume(e, "L1_GROUP", r) is r
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume(e, "L1_GROUP", r)


def test_source_learning_requires_consumed_verified_receipt():
    w = World(example("label", z=1, exact=True))
    e = w.e0()
    issued = w.issue(e, "L1_GROUP", 0)
    state = Learned()
    with pytest.raises(ValueError, match="UNCONSUMED"):
        w.retain(e, issued, state, enabled=True)
    terminal = w.consume(e, "L1_GROUP", issued)
    assert terminal.label_kind == "EXACT"
    assert w.retain(e, terminal, state, enabled=True)
    assert state.posterior(0)[1] == 1
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.retain(e, terminal, state, enabled=True)
    assert len(state.history[0]) == 1


def test_missing_label_does_not_turn_world_failure_into_exact_z():
    w = World(example("missing", z=1, exact=False))
    e, r = verified(w, zguess=0)
    assert r.label_kind == "MISSING" and r.label_z is None
    s = Learned()
    assert not w.retain(e, r, s, enabled=True)
    assert not s.history
    assert w.evaluate()["correct"] is False
    assert not hasattr(r, "correct") and not hasattr(r, "hidden_z")


def test_weak_and_missing_spoofs_cannot_enter_by_issued_receipt_identity():
    w = World(example("forged", z=0, exact=False))
    e = w.e0()
    issued = w.issue(e, "L1_GROUP", 0)
    for change in (
        replace(issued, label_kind="EXACT", label_z=1),
        replace(issued, label_kind="MISSING", label_z=1),
        replace(issued, label_kind="WEAK", label_z=0),
    ):
        with pytest.raises(ValueError, match="FORGED"):
            w.consume(e, "L1_GROUP", change)
    w.consume(e, "L1_GROUP", issued)
    assert not w.retain(e, issued, Learned(), enabled=True)


def test_same_warmup_source_label_history_and_actions_across_all_policies():
    rows = {arm: trajectory(443, arm) for arm in ARMS}
    base = rows["FROZEN_GROUP"]
    warmup = [
        (x["session"], x["mode"], x["prediction"], x["retained_exact"])
        for x in base["trace"] if x["epoch"] == "warmup"
    ]
    for arm in ARMS:
        r = rows[arm]
        assert r["warmup_state"] == base["warmup_state"]
        assert [
            (x["session"], x["mode"], x["prediction"], x["retained_exact"])
            for x in r["trace"] if x["epoch"] == "warmup"
        ] == warmup


def test_frozen_group_equals_no_feedback_group_exactly():
    f, n = trajectory(443, "FROZEN_GROUP"), trajectory(443, "NO_FEEDBACK_GROUP")
    assert f["warmup_state"] == n["warmup_state"]
    assert f["phases"] == n["phases"]
    assert [
        (x["session"], x["prediction"], x["mode"], x["correct"])
        for x in f["trace"]
    ] == [
        (x["session"], x["prediction"], x["mode"], x["correct"])
        for x in n["trace"]
    ]


def test_all_arms_share_denominator_and_utility_determinism():
    n = config()["episodes_per_epoch"]
    for arm in ARMS:
        t = trajectory(443, arm)
        assert len(t["trace"]) == 5*n
        assert len({x["session"] for x in t["trace"]}) == 5*n
        for epoch in config()["epochs"]:
            p = t["phases"][epoch]
            assert p["correct"]+p["wrong"]+p["abstain"] == n
            assert p["exact_admissions"] <= n
            assert p["deep_count"] <= n
    a = report()
    assert report() == a
    assert hash_obj({k: v for k, v in a.items() if k != "result_sha256"}) == a["result_sha256"]
    assert set(a["paired"]) == {"443", "449", "457", "461", "463"}
    for arm in ARMS:
        p = a["summaries"]["heldout"][arm]
        assert p["correct"]+p["wrong"]+p["abstain"] == 2400


def test_emit_final_machine_readable_ci_result():
    import json
    import warnings

    r = report()
    warnings.warn("C11_RESULT_JSON " + json.dumps({
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summaries"]["heldout"],
        "paired": r["paired"],
    }, sort_keys=True), UserWarning)
