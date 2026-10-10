"""C13: outcome-grounded goal witness cannot be replaced by movement or guesses."""
from dataclasses import replace

import pytest

from experiments.ac_c_c13_goal import (
    ARMS,
    MANIFEST_SHA,
    E0,
    Hidden,
    Retention,
    World,
    admissible_detour,
    admissible_first,
    checksum,
    choose,
    generate,
    manifest,
    report,
    trajectory,
)


def case(session: str, *, z: int = 0, normal_block: bool = False,
         detour_block: bool = False, cues=(1, 0, 1),
         health: int = 8, deadline: int = 7,
         hunger: int = 12, threat: bool = False) -> Hidden:
    return Hidden(
        session, "sensor_drift", 0, 0, cues, z, normal_block,
        detour_block, health, deadline, hunger, threat,
    )


def started(world: World, z: int = 0):
    e = world.e0()
    r = world.consume_first(e, world.issue_first(e, z))
    return e, r


def test_frozen_manifest_and_distinct_seed_families():
    m = manifest()
    assert checksum(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [523, 541, 547]
    assert m["seeds"]["heldout"] == [557, 563, 569, 571, 577]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["world"]["direct_exact_z_labels_never"]
    assert m["retention"]["no_negative_labels"]
    assert m["retention"]["no_raw_moved_label"]


def test_case_pairing_public_observation_and_opaque_session():
    a = case("same", z=0, normal_block=True, detour_block=False)
    b = case("same", z=1, normal_block=False, detour_block=True)
    assert World(a).e0() == World(b).e0()
    e = World(a).e0()
    assert isinstance(e, E0)
    for hidden in ("hidden_z", "blocked_normal", "blocked_detour",
                   "epoch", "truth", "goal", "goal_reached", "correct"):
        assert not hasattr(e, hidden)
    assert generate(557) == generate(557)
    assert generate(557) != generate(563)
    assert len(generate(557)) == 600
    assert "557" not in generate(557)[241].session
    assert "sensor_drift" not in generate(557)[241].session


def test_moved_without_goal_never_certifies_z():
    w = World(case("wrong_goal", z=1, normal_block=False))
    e, first = started(w, z=0)
    assert first.moved
    assert not first.goal_reached
    assert not hasattr(first, "label_z")
    assert not hasattr(first, "correct")
    w.stop(e, first)
    state = Retention()
    assert w.retain(e, first, None, state, enabled=True) == (False, "UNIDENTIFIED")
    assert state.fingerprint() == (((), ()), ())
    assert w.evaluate()["first_decision_correct"] is False


def test_same_failed_world_receipt_can_have_different_hidden_rule():
    records = []
    for hidden_z in (0, 1):
        w = World(case("equivalent", z=hidden_z, normal_block=True))
        e, first = started(w, z=0)
        assert first.moved is False and first.goal_reached is False
        records.append(first)
        w.stop(e, first)
        assert w.retain(e, first, None, Retention(), enabled=True)[0] is False
    assert records[0] == records[1]


def test_positive_source_goal_witness_certifies_only_executed_z():
    w = World(case("goal", z=0, normal_block=False, cues=(1, 0, 0)))
    e, first = started(w, z=0)
    assert first.goal_reached and first.moved
    s = Retention()
    verified, kind = w.retain(e, first, None, s, enabled=True)
    assert (verified, kind) == (True, "FIRST_GOAL")
    assert list(s.group_z[0]) == [0]
    assert list(s.cue_matches) == [2]
    assert s.sensor_r() > 0.5
    assert w.evaluate()["hidden_z"] == 0


def test_detour_success_certifies_source_without_hidden_z_label():
    w = World(case("detour", z=0, normal_block=True, detour_block=False))
    e, first = started(w, z=0)
    second = w.consume_second(e, first, w.issue_second(e, first, "DETOUR_SAME"))
    assert not first.goal_reached
    assert second.moved and second.goal_reached
    assert second.action_type == "DETOUR_SAME"
    assert second.parent_hash == checksum({
        "action_bit": first.action_bit,
        "action_type": first.action_type,
        "e0_hash": first.e0_hash,
        "goal_reached": first.goal_reached,
        "moved": first.moved,
        "parent_hash": first.parent_hash,
        "revision": first.revision,
        "session": first.session,
    })
    s = Retention()
    assert w.retain(e, first, second, s, enabled=True) == (True, "SECOND_GOAL")
    assert list(s.group_z[0]) == [0]
    assert w.evaluate()["final_goal"] is True


def test_failed_detour_is_nonidentifying_even_if_first_direction_correct():
    w = World(case("blocked_detour", z=0, normal_block=True, detour_block=True))
    e, first = started(w, z=0)
    second = w.consume_second(e, first, w.issue_second(e, first, "DETOUR_SAME"))
    assert not second.moved and not second.goal_reached
    s = Retention()
    assert w.retain(e, first, second, s, enabled=True) == (False, "UNIDENTIFIED")
    assert s.fingerprint() == (((), ()), ())
    assert w.evaluate()["first_decision_correct"] is True
    assert w.evaluate()["blocked_detour"] is True


def test_moved_detour_without_goal_is_also_nonidentifying():
    w = World(case("wrong_detour", z=1, normal_block=True, detour_block=False))
    e, first = started(w, z=0)
    second = w.consume_second(e, first, w.issue_second(e, first, "DETOUR_SAME"))
    assert second.moved and not second.goal_reached
    s = Retention()
    assert w.retain(e, first, second, s, enabled=True)[0] is False
    assert s.fingerprint() == (((), ()), ())


def test_first_receipt_identity_session_revision_and_replay_fences():
    w = World(case("source"))
    e = w.e0()
    r = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume_first(e, replace(r))
    with pytest.raises(ValueError, match="FORGED"):
        w.consume_first(replace(e, session="other"), r)
    with pytest.raises(ValueError, match="FORGED"):
        w.consume_first(replace(e, revision=1), r)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue_first(e, 0)
    assert w.consume_first(e, r) is r
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_first(e, r)


def test_second_only_after_failed_consumed_first():
    w = World(case("late", z=0, normal_block=True))
    e = w.e0()
    r = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="AUTHORIZED"):
        w.issue_second(e, r, "DETOUR_SAME")
    w.consume_first(e, r)
    second = w.issue_second(e, r, "DETOUR_SAME")
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(e, r, replace(second))
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(replace(e, session="wrong"), r, second)
    w.consume_second(e, r, second)
    with pytest.raises(ValueError, match="REPLAYED"):
        w.consume_second(e, r, second)
    with pytest.raises(ValueError, match="AUTHORIZED"):
        w.issue_second(e, r, "DETOUR_SAME")


def test_cannot_detour_after_positive_first_goal():
    w = World(case("success"))
    e, first = started(w)
    assert first.goal_reached
    with pytest.raises(ValueError, match="AUTHORIZED"):
        w.issue_second(e, first, "DETOUR_SAME")
    with pytest.raises(ValueError, match="AUTHORIZED"):
        w.stop(e, first)


def test_hard_budget_and_health_reject_unsafe_detour():
    e = World(case("short", deadline=2)).e0()
    assert admissible_first(e)
    assert not admissible_detour(e)
    w = World(case("short", normal_block=True, deadline=2))
    obs, first = started(w)
    with pytest.raises(ValueError, match="UNSAFE"):
        w.issue_second(obs, first, "DETOUR_SAME")
    too_hungry = replace(e, hunger=2)
    assert not admissible_detour(too_hungry)
    bad = replace(e, health=2, deadline=1)
    assert not admissible_first(bad)
    risky = replace(e, threat=True, health=4, deadline=7)
    assert not admissible_detour(risky)


def test_source_receipt_and_retention_nonrepeat_and_proof_only():
    w = World(case("first"))
    e = w.e0()
    r = w.issue_first(e, 0)
    with pytest.raises(ValueError, match="PREMATURE"):
        w.retain(e, r, None, Retention(), enabled=True)
    w.consume_first(e, r)
    assert w.retain(e, r, None, Retention(), enabled=True)[0]
    with pytest.raises(ValueError, match="REPLAYED"):
        w.retain(e, r, None, Retention(), enabled=True)


def test_cheap_route_always_admissible_no_oracle_read():
    e = World(case("choose")).e0()
    for arm in ("ADAPT_GROUP", "FROZEN_MAJORITY", "STATIC_GATE", "LEARNED_GATE",
                "SIMPLE_R_GATE", "CERTIFY_ALWAYS", "CERTIFY_SELECTIVE"):
        mode, z = choose(e, Retention(), arm, warmup=False)
        assert mode in ("GROUP", "MAJORITY")
        assert z in (0, 1)
    with pytest.raises(ValueError, match="ORACLE"):
        choose(e, Retention(), "EVALUATOR_ORACLE", warmup=False)


def test_all_warmups_identical_for_every_policy():
    variants = {a: trajectory(557, a) for a in ARMS}
    origin = variants[ARMS[0]]
    ref = origin["warmup_signature"]
    baseline = [(x["session"], x["first_mode"], x["first_z"], x["certificate"])
                for x in origin["trace"] if x["epoch"] == "warmup"]
    for arm, trial in variants.items():
        assert trial["warmup_signature"] == ref
        assert [
            (x["session"], x["first_mode"], x["first_z"], x["certificate"])
            for x in trial["trace"] if x["epoch"] == "warmup"
        ] == baseline, arm


def test_frozen_negative_baselines_are_output_equivalent():
    f = trajectory(557, "FROZEN_GROUP")
    n = trajectory(557, "NO_FEEDBACK_GROUP")
    assert f["phases"] == n["phases"]
    assert [x["first_z"] for x in f["trace"]] == [
        x["first_z"] for x in n["trace"]
    ]
    a = trajectory(557, "ADAPT_MAJORITY")
    b = trajectory(557, "FROZEN_MAJORITY")
    assert [x["first_z"] for x in a["trace"]] == [
        x["first_z"] for x in b["trace"]
    ]


def test_report_paired_determinism_and_2400_episode_denominator():
    r = report()
    assert r == report()
    assert r["result_sha256"] == checksum({
        key: val for key, val in r.items() if key != "result_sha256"
    })
    assert set(r["paired"]) == {"557", "563", "569", "571", "577"}
    for arm in ARMS:
        q = r["summary"]["heldout"][arm]
        assert q["first_correct"]+q["first_wrong"]+q["initial_abstain"] == 2400
        assert q["certificates"] <= q["final_goal"]
        assert q["first_certificates"]+q["second_certificates"] == q["certificates"]
        assert q["second_certificates"] <= q["detour_count"]
        assert q["ticks"] >= q["first_correct"]+q["first_wrong"]
        assert set(q["phase_r_end_mean"]) == set(manifest()["epochs"])


def test_ci_emit_machine_readable_preregistered_result():
    import json
    import warnings

    answer = report()
    warnings.warn("C13_RESULT_JSON "+json.dumps({
        "manifest_sha256": answer["manifest_sha256"],
        "result_sha256": answer["result_sha256"],
        "heldout": answer["summary"]["heldout"],
        "paired": answer["paired"],
    }, sort_keys=True), UserWarning)
