"""C6 frozen revocable-capsule toy: source, reliability, shift and null checks."""
from collections import deque
from dataclasses import replace

import pytest

from experiments.ac_c_c6_capsule import (
    ARMS,
    MANIFEST_SHA,
    Capsule,
    Evidence,
    HiddenCase,
    PolicyState,
    World,
    canonical_hash,
    decide,
    frozen_manifest,
    generate,
    report,
    trajectory,
    viable,
)


def _case(session: str, z: int = 1) -> HiddenCase:
    return HiddenCase(
        session=session, epoch="shift", group=0, prefix=0,
        hidden_z=z, deadline=6, health=8, hunger=12,
        threat=False, scan_available=True,
    )


def _verified(world: World, state: PolicyState, arm: str, from_capsule: bool,
              opportunity: int, mode: str = "CHEAP", bit: int = 0) -> dict:
    e = world.evidence()
    r = world.consume(e, world.issue(e, mode, predicted_z=bit), mode)
    return world.retain(
        e, r, state, arm, warmup=False,
        from_capsule=from_capsule, opportunity=opportunity,
    )


def _trained_capsule() -> PolicyState:
    s = PolicyState()
    s.history[0] = deque([0] * 10, maxlen=12)
    s.label_count[0] = 10
    s.last_verified_session[0] = "warmup-terminal"
    assert s.certify_warmup()["0"]
    assert s.capsule[0].predicted_z == 0
    assert s.capsule[0].source_session == "warmup-terminal"
    return s


def test_manifest_sha_and_new_disjoint_seeds():
    m = frozen_manifest()
    assert canonical_hash(m) == MANIFEST_SHA
    assert m["seeds"]["calibration"] == [167, 173, 179]
    assert m["seeds"]["heldout"] == [181, 191, 193, 197, 199]
    assert set(m["seeds"]["calibration"]).isdisjoint(m["seeds"]["heldout"])
    assert m["positive_gate"]["heldout_posttraining_cases"] == 1000


def test_cases_are_paired_and_E0_cannot_expose_hidden_z_or_regime():
    assert generate(181) == generate(181)
    assert generate(181) != generate(191)
    assert len(generate(181)) == 280
    w = World(generate(181)[0])
    e = w.evidence()
    assert isinstance(e, Evidence)
    for hidden in ("hidden_z", "target", "epoch", "seed"):
        assert not hasattr(e, hidden)
    c = _case("same")
    reverse = replace(c, hidden_z=1 - c.hidden_z)
    assert World(c).evidence() == World(reverse).evidence()
    assert c.target != reverse.target


def test_protect_World_receipt_identity_revision_and_feedback_one_shot():
    w = World(_case("origin"))
    e = w.evidence()
    r = w.issue(e, "CHEAP")
    with pytest.raises(ValueError, match="FORGED"):
        w.retain(e, r, PolicyState(), "GUARDED_CAPSULE", warmup=False,
                 from_capsule=False, opportunity=0)
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        w.consume(e, replace(r), "CHEAP")
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        w.consume(replace(e, session="other"), r, "CHEAP")
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        w.consume(e, r, "DIAGNOSTIC")
    assert w.consume(e, r, "CHEAP") == r
    with pytest.raises(ValueError, match="UNAUTHORIZED"):
        w.consume(e, r, "CHEAP")
    w.retain(e, r, PolicyState(), "GUARDED_CAPSULE", warmup=False,
             from_capsule=False, opportunity=0)
    with pytest.raises(ValueError, match="FORGED"):
        w.retain(e, r, PolicyState(), "GUARDED_CAPSULE", warmup=False,
                 from_capsule=False, opportunity=0)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, "CHEAP")


def test_paid_world_information_requires_mode_and_fresh_evidence():
    w = World(_case("s"))
    e = w.evidence()
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue(e, "DIAGNOSTIC", predicted_z=1)
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue(replace(e, revision=1), "CHEAP")
    with pytest.raises(ValueError, match="FOREIGN"):
        w.issue(replace(e, group=1), "CHEAP")
    assert w.issue(e, "DIAGNOSTIC").success
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, "CHEAP")


def test_hard_world_viability_never_optimized_away():
    e = Evidence("s", 0, 0, 0, 1, 2, 2, True, False)
    assert not any(viable(e, mode) for mode in ("CHEAP", "DIAGNOSTIC", "DEEP"))
    assert decide(e, "GUARDED_CAPSULE", PolicyState(), warmup=False)[0] == "ABSTAIN"
    assert not viable(replace(e, health=8, deadline=6), "DEEP")
    healthy = replace(e, health=8, deadline=6, hunger=12, scan_available=True)
    assert viable(healthy, "DIAGNOSTIC")


def test_capsule_qualification_is_receipt_sourced_and_unqualified_cannot_be_used():
    s = PolicyState()
    s.history[0] = deque([0] * 7, maxlen=12)
    s.label_count[0] = 7
    s.last_verified_session[0] = "observed"
    assert not s.certify_warmup()["0"]
    e = World(_case("now")).evidence()
    assert decide(e, "GUARDED_CAPSULE", s, warmup=False)[0] == "DIAGNOSTIC"
    s.capsule[0] = Capsule(0, 0, 1, "source", 7, certified=False)
    assert decide(e, "GUARDED_CAPSULE", s, warmup=False)[0] == "DIAGNOSTIC"


def test_guard_revokes_only_after_two_consumed_capsule_contradictions():
    s = _trained_capsule()
    for i in (0, 1):
        w = World(_case(f"shift:{i}", z=1))
        e = w.evidence()
        mode, bit, cached = decide(e, "GUARDED_CAPSULE", s, warmup=False)
        assert (mode, bit, cached) == ("CHEAP", 0, True)
        change = _verified(w, s, "GUARDED_CAPSULE", cached, i, mode=mode, bit=bit)
        assert change["revoked"] == (i == 1)
        if i == 1:
            assert change["revocation_lag"] == 1
    assert 0 not in s.capsule
    assert decide(World(_case("next")).evidence(),
                  "GUARDED_CAPSULE", s, warmup=False)[0] == "DIAGNOSTIC"


def test_recompile_needs_eight_new_verified_world_outcomes_after_revocation():
    s = _trained_capsule()
    for i in range(2):
        _verified(World(_case(f"bad:{i}")), s, "GUARDED_CAPSULE",
                  True, i, mode="CHEAP", bit=0)
    assert 0 not in s.capsule
    for i in range(8):
        world = World(_case(f"repair:{i}", z=1))
        outcome = _verified(
            world, s, "GUARDED_CAPSULE", False, i + 2, mode="DIAGNOSTIC",
        )
        assert outcome["recompiled"] == (i == 7)
    assert s.capsule[0].predicted_z == 1
    assert s.capsule[0].revision == 2
    assert s.capsule[0].source_session == "repair:7"


def test_unchecked_cache_cannot_revoke_from_world_feedback():
    s = _trained_capsule()
    for i in range(4):
        w = World(_case(f"stale:{i}"))
        e = w.evidence()
        mode, bit, cached = decide(e, "STATIC_CAPSULE", s, warmup=False)
        assert (mode, bit, cached) == ("CHEAP", 0, True)
        outcome = _verified(w, s, "STATIC_CAPSULE", True, i, mode, bit)
        assert not outcome["revoked"]
    assert s.capsule[0].predicted_z == 0


def test_all_frozen_arms_have_paired_outcomes_and_partition():
    m = frozen_manifest()
    for arm in ARMS:
        record = trajectory(181, arm)
        assert len(record["trace"]) == 280
        assert len({row["session"] for row in record["trace"]}) == 280
        for ep in m["epochs"]:
            p = record["phases"][ep]
            assert p["correct"] + p["wrong"] + p["abstain"] == m["opportunities"][ep]
        assert all(row["receipt_revision"] in (None, 1, 2)
                   for row in record["trace"])


def test_heldout_report_is_deterministic_and_metric_boundaries_explicit():
    x, y = report(), report()
    assert x == y
    assert x["result_sha256"] == canonical_hash({
        k: v for k, v in x.items() if k != "result_sha256"
    })
    for arm in ARMS:
        item = x["summaries"]["heldout"][arm]
        assert item["correct"] + item["wrong"] + item["abstain"] == 1000
    assert set(x["paired"]) == {"181", "191", "193", "197", "199"}


def test_c6_results_provenance_in_exact_head_ci_log():
    import json
    import warnings

    r = report()
    published = {
        "manifest_sha256": r["manifest_sha256"],
        "result_sha256": r["result_sha256"],
        "heldout": r["summaries"]["heldout"],
        "heldout_phases": r["heldout_phases"],
        "paired": r["paired"],
    }
    warnings.warn("C6_RESULT_JSON " + json.dumps(published, sort_keys=True), UserWarning)
