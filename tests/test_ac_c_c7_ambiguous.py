"""C7 prospective ambiguous evidence test suite (no models/physical World)."""
from collections import deque
from dataclasses import replace

import pytest

from experiments.ac_c_c7_ambiguous import (
    ARMS,
    MANIFEST_SHA,
    Capsule,
    Case,
    Evidence,
    PolicyState,
    World,
    cases,
    choose,
    digest,
    frozen_manifest,
    report,
    trajectory,
    viable,
)


def subject(name: str, kind: str, *, z: int = 1, vote=None, scan=True) -> Case:
    return Case(
        session=name, epoch="shift", group=0, prefix=0, hidden_z=z,
        feedback_kind=kind, feedback_vote=vote,
        deadline=5, health=8, hunger=12, threat=False, scan_available=scan,
    )


def verified(state: PolicyState, case: Case, arm: str,
             index: int, from_capsule=True, mode="CHEAP") -> dict:
    w = World(case)
    e = w.evidence()
    r = w.consume(e, w.issue(e, mode, predicted_z=0), mode)
    return w.retain(e, r, state, arm, warmup=False,
                    from_capsule=from_capsule, index=index)


def trained() -> PolicyState:
    s = PolicyState()
    s.history[0] = deque(
        [(0, 1., "EXACT", f"warm:{i}") for i in range(10)], maxlen=12
    )
    s.last_source[0] = "warm:9"
    assert s.certify_warmup()["0"]
    assert s.capsules[0] == Capsule(0, 0, 1, "warm:9")
    return s


def test_manifest_identity_and_disjoint_seeds():
    cfg = frozen_manifest()
    assert digest(cfg) == MANIFEST_SHA
    assert cfg["seeds"]["calibration"] == [211, 223, 227]
    assert cfg["seeds"]["heldout"] == [229, 233, 239, 241, 251]
    assert set(cfg["seeds"]["calibration"]).isdisjoint(cfg["seeds"]["heldout"])
    assert cfg["retention"]["weak_weight"] == .25


def test_paired_world_and_unseen_hidden_target_quality():
    assert cases(229) == cases(229)
    assert cases(229) != cases(233)
    assert len(cases(229)) == 336
    e = World(cases(229)[0]).evidence()
    assert isinstance(e, Evidence)
    for hidden in ("hidden_z", "epoch", "target", "feedback_kind", "feedback_vote", "seed"):
        assert not hasattr(e, hidden)
    c = subject("a", "MISSING")
    alt = replace(c, hidden_z=1-c.hidden_z)
    assert World(c).evidence() == World(alt).evidence()
    assert c.target != alt.target


def test_world_feedback_is_ambiguous_without_success_truth():
    case = subject("weak", "WEAK", vote=1)
    w = World(case)
    e = w.evidence()
    receipt = w.consume(e, w.issue(e, "CHEAP"), "CHEAP")
    assert receipt.feedback_kind == "WEAK"
    assert receipt.feedback_vote == 1
    assert not hasattr(receipt, "success")
    assert not hasattr(receipt, "observed_target")
    assert w.evaluate()[0] is False


def test_missing_has_no_label_and_cannot_certificate():
    s = PolicyState()
    for i in range(8):
        verified(s, subject(f"missing:{i}", "MISSING"), "WEIGHTED_GUARD", i, False)
    assert 0 not in s.history
    assert not s.certify_warmup()["0"]


def test_weak_only_cannot_make_qualified_capsule():
    s = PolicyState()
    for i in range(12):
        verified(s, subject(f"weak:{i}", "WEAK", vote=0),
                 "WEIGHTED_GUARD", i, False)
    assert s.exact_in_recent(0) == 0
    assert not s.certify_warmup()["0"]


def test_paid_diagnostic_is_exact_despite_missing_terminal_feedback():
    s = PolicyState()
    w = World(subject("paid", "MISSING", scan=True))
    e = w.evidence()
    r = w.consume(e, w.issue(e, "DIAGNOSTIC"), "DIAGNOSTIC")
    assert r.paid_diagnostic_z == 1
    assert r.feedback_kind == "MISSING"
    change = w.retain(e, r, s, "WEIGHTED_GUARD",
                      warmup=True, from_capsule=False, index=0)
    assert change["quality"] == "EXACT"
    assert s.history[0][-1][0:3] == (1, 1., "EXACT")


def test_source_receipt_fences_and_double_learning():
    w = World(subject("x", "EXACT", vote=1))
    e = w.evidence()
    issued = w.issue(e, "CHEAP")
    with pytest.raises(ValueError, match="UNCONSUMED"):
        w.retain(e, issued, PolicyState(), "WEIGHTED_GUARD",
                 warmup=True, from_capsule=False, index=0)
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(e, replace(issued), "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(replace(e, session="foreign"), issued, "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(replace(e, revision=1), issued, "CHEAP")
    with pytest.raises(ValueError, match="INVALID"):
        w.consume(e, issued, "DIAGNOSTIC")
    assert w.consume(e, issued, "CHEAP") is issued
    w.retain(e, issued, PolicyState(), "WEIGHTED_GUARD",
             warmup=True, from_capsule=False, index=0)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.retain(e, issued, PolicyState(), "WEIGHTED_GUARD",
                 warmup=True, from_capsule=False, index=0)
    with pytest.raises(ValueError, match="DUPLICATE"):
        w.issue(e, "CHEAP")


def test_spoof_missing_and_corrupt_weak_type_not_accepted():
    # Source receipt is an immutable issued object, not a user-produced value.
    w = World(subject("m", "MISSING"))
    e = w.evidence()
    r = w.issue(e, "CHEAP")
    for forged in (
        replace(r, feedback_kind="EXACT", feedback_vote=1),
        replace(r, feedback_kind="MISSING", feedback_vote=1),
        replace(r, feedback_kind="WEAK", feedback_vote=1),
    ):
        with pytest.raises(ValueError, match="INVALID"):
            w.consume(e, forged, "CHEAP")


def test_budget_and_unpaid_diagnostic_fail_closed():
    e = Evidence("s", 0, 0, 0, 1, 2, 2, True, False)
    assert not any(viable(e, m) for m in ("CHEAP", "DIAGNOSTIC"))
    assert choose(e, "WEIGHTED_GUARD", PolicyState(), warmup=False)[0] == "ABSTAIN"
    w = World(subject("unpaid", "EXACT", vote=1))
    with pytest.raises(ValueError, match="UNPAID"):
        w.issue(w.evidence(), "DIAGNOSTIC", predicted_z=1)


def test_unsafe_naive_promotes_two_weak_to_revocation():
    naive, strict, weighted = trained(), trained(), trained()
    for i in range(2):
        c = subject(f"n{i}", "WEAK", z=1, vote=1)
        out_naive = verified(naive, c, "NAIVE_WEAK_AS_EXACT", i)
        out_strict = verified(strict, c, "STRICT_EXACT_ONLY", i)
        out_weighted = verified(weighted, c, "WEIGHTED_GUARD", i)
    assert out_naive["revoked"]
    assert not out_strict["revoked"]
    assert not out_weighted["revoked"]
    assert 0 not in naive.capsules
    assert 0 in strict.capsules and 0 in weighted.capsules


def test_guard_can_revoke_from_exact_and_weak_combination():
    weighted = trained()
    for i, kind in enumerate(("EXACT", "WEAK", "WEAK")):
        change = verified(weighted, subject(f"w{i}", kind, vote=1),
                          "WEIGHTED_GUARD", i)
    assert change["revoked"]
    assert change["lag"] == 2
    assert 0 not in weighted.capsules


def test_exact_guard_does_not_accept_weak_substitution():
    strict = trained()
    for i, kind in enumerate(("WEAK", "EXACT", "WEAK", "EXACT")):
        result = verified(strict, subject(f"s{i}", kind, vote=1),
                          "STRICT_EXACT_ONLY", i)
    assert result["revoked"]
    assert 0 not in strict.capsules


def test_recompile_only_after_four_new_valid_exact_labels():
    s = trained()
    for i, kind in enumerate(("EXACT", "WEAK", "WEAK")):
        verified(s, subject(f"x{i}", kind, vote=1), "WEIGHTED_GUARD", i)
    assert 0 not in s.capsules
    recompiled = False
    for i in range(20):
        change = verified(s, subject(f"new{i}", "MISSING", z=1),
                          "WEIGHTED_GUARD", i+3, False, mode="DIAGNOSTIC")
        if i < 3:
            assert not change["recompiled"]  # >=4 new exact receipts required
        if change["recompiled"]:
            assert i >= 3  # posterior confidence is a separate requirement
            recompiled = True
            break
    assert recompiled
    assert s.capsules[0].predicted_z == 1
    assert s.capsules[0].revision == 2


def test_all_arms_partition_and_reuse_only_certified_capsule():
    cfg = frozen_manifest()
    for arm in ARMS:
        result = trajectory(229, arm)
        assert len(result["trace"]) == 336
        assert len({x["session"] for x in result["trace"]}) == 336
        for epoch in cfg["epochs"]:
            p = result["phases"][epoch]
            assert p["correct"] + p["wrong"] + p["abstain"] == cfg["episodes_per_epoch"][epoch]
        assert all(x["revision"] in (None, 1, 2) for x in result["trace"])


def test_matched_heldout_metrics_and_frozen_determinism():
    a, b = report(), report()
    assert a == b
    assert a["result_sha256"] == digest({
        k: v for k, v in a.items() if k != "result_sha256"
    })
    for arm in ARMS:
        q = a["summaries"]["heldout"][arm]
        assert q["correct"] + q["wrong"] + q["abstain"] == 1200
    assert set(a["paired"]) == {"229", "233", "239", "241", "251"}


def test_qualified_result_receipt_in_exact_head_ci_log():
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
    warnings.warn("C7_RESULT_JSON " + json.dumps(payload, sort_keys=True), UserWarning)
