"""C3 causal-attribution probes; synthetic and non-generative only."""

from dataclasses import replace

import pytest

from experiments.ac_c_allocation import (
    Evidence,
    SyntheticWorld,
    evaluate,
)
from experiments.ac_c_c3_audit import (
    MANIFEST_SHA256,
    WorldReceiptLedger,
    evidence_hash,
    frozen_config,
    paired_report,
    trajectory,
)


def _subject():
    from experiments.ac_c_allocation import cases_for
    world = SyntheticWorld(cases_for(53, 64)[0])
    return world, world.evidence(fatigue=0)


def test_exact_manifest_and_fresh_confirmation_seeds():
    cfg = frozen_config()
    assert cfg["confirmation_seeds"] == [53, 59, 61, 67, 71]
    assert not set(cfg["confirmation_seeds"]) & {11, 13, 17, 31, 37, 41, 43, 47}
    assert len(MANIFEST_SHA256) == 64
    assert cfg["frozen_parent_head"] == "c2c4b2b6e1fcf245f7c85eb4bc3caac46404a13f"


def test_receipt_is_world_minted_source_bound_and_once_only():
    world, evidence = _subject()
    ledger = WorldReceiptLedger()
    receipt = ledger.issue(world, evidence, "FAST")
    assert receipt.decision_revision == 0
    assert receipt.outcome_revision == 1
    assert receipt.evidence_digest == evidence_hash(evidence)
    with pytest.raises(ValueError, match="FOREIGN"):
        ledger.consume(replace(evidence, session="wrong"), "FAST", receipt)
    with pytest.raises(ValueError, match="FOREIGN"):
        ledger.consume(replace(evidence, revision=1), "FAST", receipt)
    with pytest.raises(ValueError, match="FOREIGN"):
        ledger.consume(evidence, "MEDIUM", receipt)
    with pytest.raises(ValueError, match="FOREIGN"):
        ledger.consume(evidence, "FAST", replace(receipt, observed_success=not receipt.observed_success))
    assert ledger.consume(evidence, "FAST", receipt) is receipt.observed_success
    with pytest.raises(ValueError, match="DUPLICATE"):
        ledger.consume(evidence, "FAST", receipt)
    with pytest.raises(ValueError, match="DUPLICATE"):
        ledger.issue(world, evidence, "FAST")


def test_foreign_world_and_invalid_mechanism_rejected():
    world, e = _subject()
    ledger = WorldReceiptLedger()
    with pytest.raises(ValueError):
        ledger.issue(world, replace(e, session="invalid"), "CHEAP_EXACT")
    with pytest.raises(ValueError, match="UNKNOWN_MECHANISM"):
        ledger.issue(world, e, "FAKE")
    assert ledger.issue(world, e, "CHEAP_EXACT").observed_success


def test_world_truth_not_in_selector_evidence():
    world, e = _subject()
    assert isinstance(e, Evidence)
    assert not hasattr(e, "target")
    assert not hasattr(e, "phase")
    assert world.case.target == e.glyph.bit_count() % 2


def test_original_fixed_and_learned_frozen_results_reproduced():
    for arm in ("FIXED", "LEARNED"):
        new = trajectory(53, arm)
        orig = evaluate(53, arm, "BODY_AWARE")
        for phase in frozen_config()["phase_schedule"]:
            for key in ("success", "failure", "abstain", "counts", "work_units", "selector_ops"):
                assert new["phases"][phase][key] == orig["phases"][phase][key]


def test_receipt_and_trace_one_world_outcome_each():
    for arm in frozen_config()["arms"]:
        rec = trajectory(53, arm)
        assert len(rec["frames"]) == 256
        for phase in frozen_config()["phase_schedule"]:
            rows = [f for f in rec["frames"] if f["phase"] == phase]
            assert len(rows) == 64
            assert len({f["session"] for f in rows}) == 64
            assert all(
                f["outcome_revision"] == 1 if f["success"] is not None
                else f["outcome_revision"] is None
                for f in rows
            )
        for cue, witness in rec["shift_witness"].items():
            assert cue in ("0", "1")
            if witness["lag"] is not None:
                assert witness["failed_fast"]
                assert witness["lag"] > 0
                assert not witness["censored"]


def test_paired_fresh_seed_comparators_and_determinism():
    a, b = paired_report(), paired_report()
    assert a["manifest_sha256"] == MANIFEST_SHA256
    assert a["records_sha256"] == b["records_sha256"]
    assert a["feedback_ablation_pairs"] == b["feedback_ablation_pairs"]
    assert a["summaries"]["CHEAP_EXACT"]["success"] == 1280
    assert a["summaries"]["CHEAP_EXACT"]["abstain"] == 0
    assert a["cheap_exact_provisional_work_costs"] == {
        "1": 1280, "2": 2560, "3": 3840
    }


def test_all_phase_outcome_buckets_partition_and_selection_cost():
    report = paired_report()
    for arm, s in report["summaries"].items():
        assert s["success"] + s["failure"] + s["abstain"] == 1280
        assert s["selector_ops"] == (
            7680 if arm in ("LEARNED", "LEARNED_NO_FEEDBACK") else
            1280 if arm == "FIXED" else 0
        )


def test_receipt_identity_required_even_equal_data():
    world, e = _subject()
    ledger = WorldReceiptLedger()
    receipt = ledger.issue(world, e, "FAST")
    twin = replace(receipt)
    # dataclasses.replace manufactures an equal-but-not-issued object.
    assert twin == receipt and twin is not receipt
    with pytest.raises(ValueError, match="FOREIGN"):
        ledger.consume(e, "FAST", twin)
