"""C8 source-only action attribution, falsification and Grand Null tests."""
from dataclasses import replace

import pytest

from experiments.ac_c_c8_attribution import (
    ARMS,
    MANIFEST_SHA,
    Case,
    Evidence,
    PolicyState,
    World,
    canonical_hash,
    config,
    generate,
    report,
    select,
    trajectory,
    viable,
)


def case(session: str, *, hidden_z: int, blocked: bool, hint=None) -> Case:
    return Case(
        session, "block_only", 0, 0, hidden_z, blocked, hint,
        5, 8, 12, False, True,
    )


def test_frozen_manifest_and_independent_seed_sets():
    m = config()
    assert canonical_hash(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [257, 263, 269]
    assert m["seeds"]["heldout"] == [271, 277, 281, 283, 293]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["learners"]["assumed_obstruction_prior"] == .3
    assert len(generate(271)) == 480
    assert generate(271) == generate(271)
    assert generate(271) != generate(277)


def test_visible_e0_cannot_reveal_causal_state_phase_or_future_receipt():
    c = case("public", hidden_z=1, blocked=True, hint=True)
    e = World(c).e0()
    assert isinstance(e, Evidence)
    for hidden in ("hidden_z", "target", "obstructed", "obstacle_hint",
                   "epoch", "seed", "movement", "correct"):
        assert not hasattr(e, hidden)
    alt = replace(c, hidden_z=0, obstructed=False)
    assert World(alt).e0() == e
    assert c.target != alt.target


def test_identical_observed_failed_movement_has_distinct_hidden_causes():
    # A=0, z=0, block => decision correct but no movement.
    blocked_correct = World(case("x", hidden_z=0, blocked=True, hint=None))
    # A=0, z=1, no block => bad decision and no movement.
    wrong_unblocked = World(case("x", hidden_z=1, blocked=False, hint=None))
    observations = []
    labels = []
    for w in (blocked_correct, wrong_unblocked):
        e = w.e0()
        receipt = w.consume(e, w.issue(e, "CHEAP", predicted_z=0), "CHEAP")
        observations.append(receipt)
        labels.append(w.evaluate()[:2])
        assert not hasattr(receipt, "decision_correct")
        assert not hasattr(receipt, "obstructed")
        assert not hasattr(receipt, "hidden_z")
    assert observations[0] == observations[1]  # unidentifiable at receipt boundary
    assert labels == [(True, False), (False, False)]


def test_paid_probe_exposes_z_but_block_can_still_prevent_movement():
    world = World(case("paid", hidden_z=1, blocked=True, hint=True))
    e = world.e0()
    r = world.consume(e, world.issue(e, "PROBE"), "PROBE")
    assert r.probe_z == 1
    assert r.moved is False
    assert world.evaluate()[0:2] == (True, False)
    s = PolicyState()
    world.retain(e, r, s, "PROBE_FIRST", warmup=False)
    assert s.z_probability[0][-1] == 1


def test_typed_receipt_session_revision_mode_and_replay_fail_closed():
    world = World(case("origin", hidden_z=0, blocked=False))
    e = world.e0()
    receipt = world.issue(e, "CHEAP")
    with pytest.raises(ValueError, match="UNATTESTED"):
        world.retain(e, receipt, PolicyState(), "NAIVE_BLAME", warmup=False)
    with pytest.raises(ValueError, match="INVALID"):
        world.consume(e, replace(receipt, moved=False), "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        world.consume(replace(e, session="other"), receipt, "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        world.consume(replace(e, revision=1), receipt, "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        world.consume(e, receipt, "PROBE")
    assert world.consume(e, receipt, "CHEAP") is receipt
    with pytest.raises(ValueError, match="INVALID"):
        world.consume(e, receipt, "CHEAP")
    world.retain(e, receipt, PolicyState(), "NAIVE_BLAME", warmup=False)
    with pytest.raises(ValueError, match="UNATTESTED"):
        world.retain(e, receipt, PolicyState(), "NAIVE_BLAME", warmup=False)
    with pytest.raises(ValueError, match="DUPLICATE"):
        world.issue(e, "CHEAP")


def test_unpaid_latent_and_hard_viability_gates():
    w = World(case("unpaid", hidden_z=1, blocked=False))
    e = w.e0()
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue(e, "PROBE", predicted_z=1)
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue(replace(e, revision=1), "CHEAP")
    unsafe = replace(e, health=2, deadline=1, probe_available=False)
    assert not any(viable(unsafe, mode) for mode in ("CHEAP", "PROBE"))
    assert select(unsafe, "CAUSAL_BAYES", PolicyState(), warmup=False)[0] == "ABSTAIN"
    assert viable(e, "PROBE")


def test_movement_positive_confirms_action_but_failure_does_not_by_itself():
    for arm in ("SUCCESS_ONLY", "CAUSAL_BAYES", "NAIVE_BLAME"):
        w = World(case("positive", hidden_z=0, blocked=False))
        e = w.e0()
        r = w.consume(e, w.issue(e, "CHEAP"), "CHEAP")
        s = PolicyState()
        w.retain(e, r, s, arm, warmup=False)
        assert s.z_probability[0][-1] == 0
    w = World(case("negative", hidden_z=0, blocked=True))
    e = w.e0()
    r = w.consume(e, w.issue(e, "CHEAP"), "CHEAP")
    s = PolicyState()
    w.retain(e, r, s, "SUCCESS_ONLY", warmup=False)
    assert not s.z_probability
    naive = PolicyState()
    # Distinct World object: second feedback is never a replay.
    other = World(case("naive", hidden_z=0, blocked=True))
    x = other.e0()
    y = other.consume(x, other.issue(x, "CHEAP"), "CHEAP")
    other.retain(x, y, naive, "NAIVE_BLAME", warmup=False)
    assert naive.z_probability[0][-1] == 1  # deliberately false blame


def test_causal_failure_update_uses_sensor_likelihood_not_truth():
    s = PolicyState()
    w = World(case("weak-block", hidden_z=0, blocked=True, hint=True))
    e = w.e0()
    r = w.consume(e, w.issue(e, "CHEAP"), "CHEAP")
    w.retain(e, r, s, "CAUSAL_BAYES", warmup=False)
    # P(z=0 | moved=false, noisy blocked hint) = 0.12 / (0.12+0.19)
    assert s.z_probability[0][-1] == pytest.approx(1-0.12/0.31)
    plain = PolicyState()
    w2 = World(case("no-hint-model", hidden_z=0, blocked=True, hint=True))
    x = w2.e0()
    y = w2.consume(x, w2.issue(x, "CHEAP"), "CHEAP")
    w2.retain(x, y, plain, "CAUSAL_NO_SENSOR", warmup=False)
    assert plain.z_probability[0][-1] == pytest.approx(1 - 0.15 / 0.65)
    assert s.z_probability[0][-1] < plain.z_probability[0][-1]


def test_sensor_heuristic_can_overtrust_wrong_obstacle_hint():
    s = PolicyState()
    w = World(case("hint", hidden_z=1, blocked=False, hint=True))
    e = w.e0()
    r = w.consume(e, w.issue(e, "CHEAP"), "CHEAP")
    w.retain(e, r, s, "SENSOR_HEURISTIC", warmup=False)
    assert not s.z_probability  # falsely thinks a wrong choice was obstructed
    w2 = World(case("missing", hidden_z=0, blocked=True, hint=None))
    e2 = w2.e0()
    r2 = w2.consume(e2, w2.issue(e2, "CHEAP"), "CHEAP")
    w2.retain(e2, r2, s, "SENSOR_HEURISTIC", warmup=False)
    assert s.z_probability[0][-1] == 1


def test_warmup_identical_across_all_arms_and_allows_only_grounded_updates():
    for seed in (271, 277):
        trials = {arm: trajectory(seed, arm) for arm in ARMS}
        base = [
            (x["session"], x["mode"], x["correct_decision"], x["moved"])
            for x in trials["FROZEN_MAP"]["trace"] if x["epoch"] == "warmup"
        ]
        for t in trials.values():
            actual = [
                (x["session"], x["mode"], x["correct_decision"], x["moved"])
                for x in t["trace"] if x["epoch"] == "warmup"
            ]
            assert actual == base


def test_all_arm_partitions_and_reproducible_frozen_report():
    m = config()
    for arm in ARMS:
        x = trajectory(271, arm)
        assert len(x["trace"]) == 480
        assert len(set(y["session"] for y in x["trace"])) == 480
        for epoch in m["epochs"]:
            row = x["phases"][epoch]
            assert row["correct"] + row["wrong"] + row["abstain"] == m["episode_counts"][epoch]
            assert row["moved"] <= row["correct"]
            assert row["correct_but_blocked"] == row["correct"] - row["moved"]
        assert all(y["receipt_revision"] in (None, 1, 2) for y in x["trace"])
    a, b = report(), report()
    assert a == b
    assert a["result_sha256"] == canonical_hash({
        k: v for k, v in a.items() if k != "result_sha256"
    })
    for arm in ARMS:
        row = a["summaries"]["heldout"][arm]
        assert row["correct"] + row["wrong"] + row["abstain"] == 2000
    assert set(a["paired"]) == {"271", "277", "281", "283", "293"}


def test_exact_head_ci_includes_machine_readable_frozen_outcomes():
    import json
    import warnings

    r = report()
    payload = {
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summaries"]["heldout"],
        "heldout_phases": r["heldout_phases"],
        "paired": r["paired"],
    }
    warnings.warn("C8_RESULT_JSON " + json.dumps(payload, sort_keys=True), UserWarning)
