"""C9: frozen source-bound epistemic Action intervention and Grand Null."""
from dataclasses import replace

import pytest

from experiments.ac_c_c9_epistemic import (
    ARMS,
    MANIFEST_SHA,
    CalibrationWorld,
    Case,
    E0,
    World,
    cfg,
    cheap_heuristic,
    first_viable,
    generate,
    group_prediction,
    inspect_viable,
    posterior,
    report,
    run_arm,
    second_viable,
    sha,
    train,
    voi_decision,
)


def case(
    session: str, *, hidden_z: int = 0, blocked: bool = True,
    weak: bool | None = None, inspect_hint: bool = True,
    deadline: int = 7, health: int = 10,
) -> Case:
    return Case(
        session, "block_shift", 0, 0, hidden_z, blocked, weak,
        inspect_hint, True, deadline, health, 12, False,
    )


def first_done(world: World, initial_z: int = 0):
    e = world.e0()
    return e, world.consume_first(e, world.issue_first(e, initial_z))


def test_immutable_protocol_and_seed_separation():
    m = cfg()
    assert sha(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [307, 311, 313]
    assert m["seeds"]["heldout"] == [317, 331, 337, 347, 349]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["adoption_gate"]["voi_more_successes_than_cheap_hint_at_least"] == 25


def test_independent_cases_and_no_hidden_e0_content():
    assert generate(317) == generate(317)
    assert generate(317) != generate(331)
    assert len(generate(317)) == 400
    c = case("same", blocked=True, hidden_z=0)
    a = World(c).e0()
    b = World(replace(c, hidden_z=1, blocked=False)).e0()
    assert a == b
    assert isinstance(a, E0)
    for hidden in ("blocked", "hidden_z", "target", "cheap_hint",
                   "inspect_hint", "epoch", "success", "second_result"):
        assert not hasattr(a, hidden)


def test_single_source_calibration_and_common_prior():
    world = CalibrationWorld(317)
    records = world.issued()
    assert len(records) == 48
    assert len({x.session for x in records}) == 48
    with pytest.raises(ValueError, match="UNSOURCED"):
        world.consume(replace(records[0]))
    world.consume(records[0])
    with pytest.raises(ValueError, match="REPLAYED"):
        world.consume(records[0])
    counts = train(317)
    assert counts == train(317)
    for group in (0, 1):
        bit, confidence = group_prediction(counts, group)
        assert bit in (0, 1) and .5 <= confidence <= 1
        assert counts[group][1] == 24


def test_observational_equivalence_and_postfailure_probe_value():
    correct_blocked = World(case("same", hidden_z=0, blocked=True, weak=None))
    wrong_unblocked = World(case("same", hidden_z=1, blocked=False, weak=None))
    outputs = []
    for world in (correct_blocked, wrong_unblocked):
        e, first = first_done(world)
        assert not first.moved
        outputs.append(first)
        assert world.e0() == e
    assert outputs[0] == outputs[1]
    # Inspection can disambiguate probabilistically, not reveal ground truth.
    e1, f1 = correct_blocked.e0(), outputs[0]
    inspected = correct_blocked.consume_inspect(
        e1, f1, correct_blocked.issue_inspect(e1, f1)
    )
    assert inspected.hinted_obstruction is True
    assert not hasattr(inspected, "hidden_z")
    assert not hasattr(inspected, "correct")


def test_wrong_stale_foreign_and_duplicate_first_receipts_are_rejected():
    world = World(case("origin"))
    e = world.e0()
    first = world.issue_first(e, 0)
    with pytest.raises(ValueError, match="INVALID"):
        world.consume_first(e, replace(first))
    with pytest.raises(ValueError, match="INVALID"):
        world.consume_first(replace(e, session="different"), first)
    with pytest.raises(ValueError, match="INVALID"):
        world.consume_first(replace(e, revision=1), first)
    with pytest.raises(ValueError, match="DUPLICATE"):
        world.issue_first(e, 0)
    world.consume_first(e, first)
    with pytest.raises(ValueError, match="REPLAYED"):
        world.consume_first(e, first)


def test_inspection_needs_paid_admission_and_only_once():
    world = World(case("probe"))
    e = world.e0()
    with pytest.raises(ValueError, match="NOT_ADMITTED"):
        world.issue_inspect(e, world.issue_first(e, 0))
    e, first = world.e0(), world._first
    world.consume_first(e, first)
    inspection = world.issue_inspect(e, first)
    with pytest.raises(ValueError, match="NOT_ADMITTED"):
        world.issue_inspect(e, first)
    with pytest.raises(ValueError, match="INVALID"):
        world.consume_inspect(e, first, replace(inspection))
    assert world.consume_inspect(e, first, inspection) is inspection
    with pytest.raises(ValueError, match="REPLAYED"):
        world.consume_inspect(e, first, inspection)
    assert inspect_viable(e)


def test_paid_receipt_is_required_before_second_action():
    w = World(case("inspect"))
    e, first = first_done(w)
    ins = w.issue_inspect(e, first)
    with pytest.raises(ValueError, match="UNCONSUMED"):
        w.issue_second(e, first, "DETOUR_SAME", inspect=ins)
    w.consume_inspect(e, first, ins)
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue_second(e, first, "DETOUR_SAME", inspect=replace(ins))
    second = w.issue_second(e, first, "DETOUR_SAME", inspect=ins)
    with pytest.raises(ValueError, match="INVALID"):
        w.consume_second(e, first, replace(second))
    assert w.consume_second(e, first, second) is second
    assert second.moved
    assert w.evaluate()["success"] is True
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(e, first, second)


def test_failure_second_action_cannot_be_issued_before_first_consumption():
    w = World(case("first"))
    e = w.e0()
    first = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="NOT_AUTHORIZED"):
        w.issue_second(e, first, "NORMAL_FLIP")
    w.consume_first(e, first)
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue_second(e, first, "NORMAL_FLIP", inspect=World(case("other"))._inspect)


def test_health_time_and_inspector_budget_is_hard_viability():
    bad = replace(World(case("low", health=2, deadline=2)).e0(), health=2)
    assert not first_viable(bad)
    assert not second_viable(bad, "DETOUR_SAME", False)
    e = World(case("short", deadline=2, health=4)).e0()
    assert first_viable(e)
    assert second_viable(e, "NORMAL_FLIP", False)
    assert not inspect_viable(e)
    assert not second_viable(e, "NORMAL_FLIP", True)
    w = World(case("short", deadline=2, health=4))
    x, first = first_done(w)
    with pytest.raises(ValueError, match="NOT_ADMITTED"):
        w.issue_inspect(x, first)


def test_no_costless_information_or_inadmissible_second():
    w = World(case("x", deadline=4))
    e, first = first_done(w)
    assert inspect_viable(e)  # one normal action remains
    ins = w.consume_inspect(e, first, w.issue_inspect(e, first))
    assert not second_viable(e, "DETOUR_SAME", True)
    with pytest.raises(ValueError, match="UNSAFE"):
        w.issue_second(e, first, "DETOUR_SAME", inspect=ins)
    assert second_viable(e, "NORMAL_FLIP", True)


def test_posterior_conditions_on_movement_failure_and_sensor_quality():
    belief = posterior(.8, None)
    assert belief == pytest.approx({
        (True, True): .24/.44,
        (False, True): .06/.44,
        (False, False): .14/.44,
    })
    assert sum(posterior(.8, True).values()) == pytest.approx(1)
    assert sum(posterior(.8, False, True).values()) == pytest.approx(1)
    e = World(case("belief")).e0()
    inspected, current_choice, voi = voi_decision(e, .8, None)
    assert isinstance(inspected, bool)
    assert current_choice in ("STOP", "NORMAL_FLIP", "DETOUR_SAME", "DETOUR_FLIP")
    assert isinstance(voi, float)
    assert cheap_heuristic(e, True, inspected=False) == "DETOUR_SAME"


def test_each_arm_completes_exact_same_world_episode_base():
    for arm in ARMS:
        r = run_arm(317, arm)
        assert len(r["trace"]) == 400
        assert len({x["session"] for x in r["trace"]}) == 400
        for ep in cfg()["epochs"]:
            p = r["phases"][ep]
            assert p["success"] + p["initial_abstain"] + p["stop"] + p["failed_second"] == 100
            assert p["inspected"] <= p["first_failure"]
            assert p["changed_from_noinspect"] <= p["inspected"]
            assert p["first_success"] <= p["success"]
            assert p["ticks"] >= 0 and p["work"] >= 0
        assert all(
            x["terminal"] in ("SUCCESS", "INITIAL_ABSTAIN", "STOP", "FAILED_SECOND")
            for x in r["trace"]
        )


def test_report_determinism_and_frozen_heldout_pairing():
    a = report()
    assert report() == a
    assert a["result_sha256"] == sha({
        k: v for k, v in a.items() if k != "result_sha256"
    })
    assert set(a["paired"]) == {"317", "331", "337", "347", "349"}
    for arm in ARMS:
        q = a["summary"]["heldout"][arm]
        assert q["success"] + q["initial_abstain"] + q["stop"] + q["failed_second"] == 2000


def test_exact_head_ci_machine_readable_provenance():
    import json
    import warnings

    r = report()
    payload = {
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summary"]["heldout"],
        "heldout_phases": r["heldout_phases"],
        "paired": r["paired"],
    }
    warnings.warn("C9_RESULT_JSON " + json.dumps(payload, sort_keys=True), UserWarning)
