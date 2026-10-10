"""C10 freeze and adversarial source-only online calibration tests."""
from dataclasses import replace

import pytest

from experiments.ac_c_c10_online import (
    ARMS,
    MANIFEST_SHA,
    Belief,
    Evidence,
    HiddenCase,
    InspectReceipt,
    World,
    digest,
    expected,
    first_viable,
    generate,
    manifest,
    posterior,
    report,
    run,
    viable_inspect,
    viable_second,
)


def fixture_case(
    session: str, *, z: int = 0, blocked: bool = True,
    hint: bool | None = None, inspect_hint: bool = True,
    health: int = 10, deadline: int = 7,
    hunger: int = 12, threat: bool = False,
) -> HiddenCase:
    return HiddenCase(
        session, "block_shift", 0, 0, z, blocked, hint, inspect_hint,
        True, deadline, health, hunger, threat,
    )


def first_done(world: World, *, guess: int = 0):
    e = world.e0()
    r = world.consume_first(e, world.issue_first(e, guess))
    return e, r


def test_preregistered_manifest_hash_and_new_heldout_seeds():
    m = manifest()
    assert digest(m) == MANIFEST_SHA
    assert m["seeds"]["heldout"] == [389, 397, 401, 409, 419]
    assert m["seeds"]["calibration"] == [359, 367, 373]
    assert set(m["seeds"]["heldout"]).isdisjoint(m["seeds"]["calibration"])
    assert m["n_per_epoch"] == 120
    assert m["learning"]["failed_normal_not_label"] is True
    assert m["learning"]["max_z_updates_per_episode"] == 1


def test_deterministic_paired_episodes_and_no_hidden_world_e0():
    assert generate(389) == generate(389)
    assert len(generate(389)) == 600
    assert generate(389) != generate(397)
    c = fixture_case("same", z=0, blocked=True)
    other = replace(c, z=1, blocked=False)
    assert World(c).e0() == World(other).e0()
    for hidden in (
        "z", "hidden_z", "blocked", "cheap_hint", "inspect_hint",
        "epoch", "target", "first_result", "second_result",
    ):
        assert not hasattr(World(c).e0(), hidden)


def test_identical_first_failed_receipt_from_distinct_latent_causes():
    receipts = []
    for c in (
        fixture_case("same", z=0, blocked=True),
        fixture_case("same", z=1, blocked=False),
    ):
        w = World(c)
        _, r = first_done(w)
        assert r.moved is False
        receipts.append(r)
    assert receipts[0] == receipts[1]


def test_first_movement_success_qualifies_exact_z_without_evaluator():
    w = World(fixture_case("success", z=1, blocked=False))
    e, r = first_done(w, guess=1)
    assert r.moved
    s = Belief()
    labeled, flipped = w.retain(e, r, None, s, enabled=True)
    assert labeled and flipped
    assert list(s.z_evidence[0]) == [1]
    assert w.evaluator()["success"] is True


def test_failed_normal_is_ambiguous_and_cannot_label_preferred_z():
    w = World(fixture_case("blocked", z=0, blocked=True, hint=True))
    e, first = first_done(w)
    assert not first.moved
    w.stop(e, first)
    s = Belief()
    assert w.retain(e, first, None, s, enabled=True) == (False, False)
    assert not s.z_evidence
    assert list(s.block_hints) == [1]


def test_failed_normal_second_is_also_ambiguous():
    # First NORMAL guess=0 fails because blocked; NORMAL_FLIP fails because z=0.
    w = World(fixture_case("two_fail", z=0, blocked=True))
    e, first = first_done(w)
    second = w.consume_second(e, first, w.issue_second(e, first, "NORMAL_FLIP"))
    assert not second.moved
    s = Belief()
    labeled, _ = w.retain(e, first, second, s, enabled=True)
    assert not labeled
    assert not s.z_evidence


def test_detour_failed_identifies_opposite_rule_only_given_bypass_law():
    # Detour is defined to bypass *all* obstruction in this toy.
    w = World(fixture_case("detour_fail", z=1, blocked=True))
    e, first = first_done(w, guess=0)
    second = w.consume_second(e, first, w.issue_second(e, first, "DETOUR_SAME"))
    assert not second.moved
    s = Belief()
    labeled, flipped = w.retain(e, first, second, s, enabled=True)
    assert labeled and flipped
    assert list(s.z_evidence[0]) == [1]


def test_detour_success_identifies_its_executed_rule():
    w = World(fixture_case("detour_win", z=0, blocked=True))
    e, first = first_done(w)
    r = w.consume_second(e, first, w.issue_second(e, first, "DETOUR_SAME"))
    assert r.moved
    s = Belief()
    assert w.retain(e, first, r, s, enabled=True)[0]
    assert list(s.z_evidence[0]) == [0]


def test_obstruction_estimation_uses_sensor_not_hidden_truth():
    s = Belief()
    assert s.obstacle_rate() == pytest.approx(.3)
    for _ in range(24):
        s.block_hints.append(1)
    assert s.obstacle_rate() == pytest.approx(.95)
    s.block_hints.clear()
    for _ in range(24):
        s.block_hints.append(0)
    assert s.obstacle_rate() == pytest.approx(.05)


def test_posterior_uses_probability_and_not_only_selected_map_bit():
    joint = posterior(.8, .3, None)
    assert joint == pytest.approx({
        (True, True): .24/.44,
        (False, True): .06/.44,
        (False, False): .14/.44,
    })
    e = World(fixture_case("posterior")).e0()
    act, val = expected(e, joint, False)
    assert act in ("STOP", "NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP")
    assert isinstance(val, float)


def test_first_and_second_receipt_authentication_and_single_use():
    w = World(fixture_case("origin", z=1, blocked=True))
    e = w.e0()
    issued = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_first(e, replace(issued))
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_first(replace(e, session="other"), issued)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_first(replace(e, revision=1), issued)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue_first(e, 0)
    w.consume_first(e, issued)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_first(e, issued)
    second = w.issue_second(e, issued, "DETOUR_SAME")
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(e, issued, replace(second))
    w.consume_second(e, issued, second)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(e, issued, second)
    s = Belief()
    w.retain(e, issued, second, s, enabled=True)
    with pytest.raises(ValueError, match="DUPLICATED"):
        w.retain(e, issued, second, s, enabled=True)


def test_paid_inspection_must_be_source_admitted_consumed_and_fresh():
    w = World(fixture_case("inspected", z=0, blocked=True))
    e = w.e0()
    first = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="UNADMITTED"):
        w.issue_inspect(e, first)
    w.consume_first(e, first)
    inspected = w.issue_inspect(e, first)
    with pytest.raises(ValueError, match="UNADMITTED"):
        w.issue_inspect(e, first)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_inspect(e, first, replace(inspected))
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue_second(e, first, "DETOUR_SAME", inspection=inspected)
    assert w.consume_inspect(e, first, inspected) is inspected
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_inspect(e, first, inspected)
    fake = InspectReceipt("other", "fake", True, 2)
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue_second(e, first, "DETOUR_SAME", inspection=fake)
    second = w.issue_second(e, first, "DETOUR_SAME", inspection=inspected)
    w.consume_second(e, first, second)
    assert w.retain(e, first, second, Belief(), enabled=False) == (False, False)


def test_do_not_run_second_before_first_consumption_and_protect_body():
    w = World(fixture_case("pre", z=0, blocked=True))
    e = w.e0()
    first = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        w.issue_second(e, first, "NORMAL_FLIP")
    unsafe = replace(e, health=2, deadline=2)
    assert not first_viable(unsafe)
    assert not viable_inspect(unsafe)
    assert not viable_second(unsafe, "DETOUR_SAME", False)
    assert viable_second(e, "DETOUR_SAME", False)
    w.consume_first(e, first)
    with pytest.raises(ValueError, match="UNSAFE"):
        w.issue_second(e, first, "INSPECT")


def test_warmup_is_identical_for_all_arms_and_frozen_controls_preserve_state():
    records = {arm: run(389, arm) for arm in ARMS}
    first = records[ARMS[0]]
    baseline = first["warmup_state"]
    assert baseline["hints"]
    for arm, item in records.items():
        assert item["warmup_state"] == baseline
        assert [
            (x["session"], x["success"], x["choice"], x["z_labeled"])
            for x in item["trace"] if x["epoch"] == "warmup"
        ] == [
            (x["session"], x["success"], x["choice"], x["z_labeled"])
            for x in first["trace"] if x["epoch"] == "warmup"
        ], arm


def test_all_arms_complete_same_episodes_and_denominator():
    m = manifest()
    for arm in ARMS:
        item = run(389, arm)
        assert len(item["trace"]) == 5*m["n_per_epoch"]
        assert len({x["session"] for x in item["trace"]}) == 5*m["n_per_epoch"]
        for ep in m["epochs"]:
            row = item["phases"][ep]
            assert (row["success"] + row["initial_abstain"] +
                    row["stopped"] + row["failed_second"] == m["n_per_epoch"])
            assert row["changed_action"] <= row["inspected"]
            assert row["first_success"] <= row["success"]
            assert row["z_labeled"] <= m["n_per_epoch"]


def test_report_is_reproducible_and_paired():
    r = report()
    assert r == report()
    assert r["result_sha256"] == digest({
        key: val for key, val in r.items() if key != "result_sha256"
    })
    assert set(r["paired"]) == {"389", "397", "401", "409", "419"}
    for arm in ARMS:
        item = r["summary"]["heldout"][arm]
        assert item["success"] + item["initial_abstain"] + item["stopped"] + item["failed_second"] == 2400


def test_exact_head_ci_emits_result_with_manifest_sha():
    import json
    import warnings

    r = report()
    warning = {
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summary"]["heldout"],
        "paired": r["paired"],
    }
    warnings.warn("C10_RESULT_JSON " + json.dumps(warning, sort_keys=True), UserWarning)
