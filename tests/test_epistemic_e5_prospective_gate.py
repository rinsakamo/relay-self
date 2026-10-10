"""AC Lane A E5: offline-only future physical experiment admission (NO World)."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from experiments import epistemic_e3_s29_integration as e3
from experiments import epistemic_e5_prospective_gate as e5


def source_digest(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def fake_trial(spec: e5.TrialSpec, *, source_kind: str = "SYNTHETIC") -> dict:
    """Fully disclosed synthetic *schema* fixture, never physical World evidence."""
    is_observe = spec.arm == "OBSERVE" or (
        spec.arm == "CHEAP_EXACT" and spec.price_quarters == 1
    )
    selected = "MOVE_AWAY" if is_observe and spec.distance_cm == 20 else "WAIT"
    issue = selected == "MOVE_AWAY"
    return {
        "trial_id": spec.trial_id,
        "block_id": spec.block_id,
        "arm": spec.arm,
        "world_seed": spec.world_seed,
        "session_id": f"native:{spec.trial_id}",
        "action_session_id": f"action:{spec.trial_id}" if issue else None,
        "reset_id": f"reset:{spec.trial_id}",
        "source_kind": source_kind,
        "policy_inputs": {
            "price_quarters": spec.price_quarters,
            "prior_ref": "uniform-nearfar-v1",
        },
        "decision_source": "S29_CORRELATED" if is_observe else "PRIOR_ONLY",
        "first_distance_cm": 180 if is_observe else None,
        "second_distance_cm": spec.distance_cm if is_observe else None,
        "policy_request_ids": [
            f"e5:{spec.trial_id}:p1", f"e5:{spec.trial_id}:p2",
        ] if is_observe else [],
        "policy_probe_seqs": [5, 6] if is_observe else [],
        "evaluator_request_id": f"e5:{spec.trial_id}:eval",
        "start_ns": 1_000_000_000,
        "first_probe_ns": 1_010_000_000 if is_observe else None,
        "second_probe_ns": 1_020_000_000 if is_observe else None,
        "decision_ns": 1_030_000_000,
        "action_issue_ns": 1_050_000_000 if issue else None,
        "action_terminal_ns": 1_075_000_000 if issue else None,
        "evaluator_ns": 1_100_000_000,
        "selected_candidate": selected,
        "action_owner_state": "OUTCOME" if issue else "NONE",
        "world_result": "EXECUTED" if issue else "NONE",
        "reason_code": "observed_execution" if issue else "NONE",
        "elapsed_ms": 100,
        "probe_ms": 20 if is_observe else 0,
        "evaluator_ms": 5,
        "health_before": 20,
        "health_after": 20 if issue or spec.distance_cm == 180 else 18,
        "damage_points": 0 if issue or spec.distance_cm == 180 else 2,
        "movement_m": 0.25 if issue else 0,
        "hunger_delta": None,
        "energy_joules": None,
        "server_log_sha256": source_digest("server:" + spec.trial_id),
        "adapter_log_sha256": source_digest("adapter:" + spec.trial_id),
        "receipt_sha256": source_digest("receipt:" + spec.trial_id),
    }


def fake_bundle(source_kind: str = "SYNTHETIC") -> dict:
    return {
        "manifest_sha256": e5.MANIFEST_SHA256,
        "source_kind": source_kind,
        "trials": [
            fake_trial(spec, source_kind=source_kind)
            for spec in e5.planned_trials()
        ],
    }


def fail_mutated(trial_index: int, field: str, value: object, *, message: str | None = None):
    bundle = fake_bundle()
    bundle["trials"][trial_index][field] = value
    with pytest.raises(e5.E5Rejected, match=message):
        e5.audit_bundle(bundle)


def _first_trial_with(*, arm: str, distance: int, price: int) -> int:
    return next(i for i, spec in enumerate(e5.planned_trials())
                if spec.arm == arm and spec.distance_cm == distance
                and spec.price_quarters == price)


NEAR_OBSERVE = _first_trial_with(arm="OBSERVE", distance=20, price=1)
FAR_OBSERVE = _first_trial_with(arm="OBSERVE", distance=180, price=1)
NEAR_NO_OBS = _first_trial_with(arm="NO_OBSERVE", distance=20, price=1)
DEAR_CHEAP = _first_trial_with(arm="CHEAP_EXACT", distance=20, price=4)


def test_manifest_identity_exact_36_and_predeclared_arm_position_balance():
    assert e5.digest() == e5.MANIFEST_SHA256
    specs = e5.planned_trials()
    assert len(specs) == 36
    assert len({v.trial_id for v in specs}) == 36
    assert len({v.block_id for v in specs}) == 12
    assert Counter(v.arm for v in specs) == {
        "NO_OBSERVE": 12, "CHEAP_EXACT": 12, "OBSERVE": 12,
    }
    assert Counter((v.arm, v.order_index) for v in specs) == {
        (arm, p): 4
        for arm in e5.MANIFEST["arms"] for p in (0, 1, 2)
    }
    for block in {s.block_id for s in specs}:
        matching = [s for s in specs if s.block_id == block]
        assert len(matching) == 3
        assert len({s.world_seed for s in matching}) == 1
        assert len({s.distance_cm for s in matching}) == 1
        assert len({s.price_quarters for s in matching}) == 1
    mutant = dict(e5.MANIFEST)
    mutant["expected_trials"] = 35
    assert e5.digest(mutant) != e5.MANIFEST_SHA256
    with pytest.raises(FrozenInstanceError):
        specs[0].arm = "OBSERVE"


def test_explicit_grand_null_matches_e3_prospective_cheap_price_gate():
    cheap = e3.plan_epistemic(1)
    dear = e3.plan_epistemic(4)
    assert cheap.no_observe_expected_score == dear.no_observe_expected_score == 6
    assert cheap.net_information_value == Fraction(1, 4)
    assert dear.net_information_value == -Fraction(1, 2)
    assert cheap.first == "OBSERVE" and dear.first == "WAIT"
    plans = e5.planned_trials()
    for spec in plans:
        f = fake_trial(spec)
        observed = len(f["policy_request_ids"]) == 2
        assert observed == (spec.arm == "OBSERVE" or (
            spec.arm == "CHEAP_EXACT" and spec.price_quarters == 1
        ))
        assert (f["second_distance_cm"] is None) == (not observed)
        assert f["policy_inputs"] == {
            "price_quarters": spec.price_quarters,
            "prior_ref": "uniform-nearfar-v1",
        }
        if not observed:
            assert f["selected_candidate"] == "WAIT"
    # Exact source-matched cheap comparator uses the same cheap rule;
    # neither of these policies calls an LLM.
    assert all(s.arm != "LLM" for s in plans)


def test_full_synthetic_36_trial_schema_and_distinct_denominators():
    report = e5.audit_bundle(fake_bundle())
    assert report.classification == "OFFLINE_SYNTHETIC_STRUCTURE_VALID"
    assert report.physically_authenticated is False
    assert report.physical_effect == "UNDETERMINED"
    assert report.checked_trials == report.expected_trials == 36
    assert report.checked_blocks == 12
    assert report.observed_policy_probes == 36  # 18 observing runs × 2
    assert report.simulated_actions == 9  # near + read, not WAIT or far
    assert report.unresolved_actions == 0
    assert report.no_observation_comparator_present
    assert report.cheap_exact_comparator_present


def test_live_claim_even_with_all_plausible_sha256_is_never_authenticated():
    live = fake_bundle("CLAIMED_LIVE")
    report = e5.audit_bundle(live)
    assert report.classification == "UNATTESTED_PHYSICAL_CLAIM"
    assert report.physical_effect == "UNDETERMINED"
    assert not report.physically_authenticated
    assert report.checked_trials == 36
    # Hashes of caller-controlled files are not real physical authentication.


@pytest.mark.parametrize("field,value", [
    ("arm", "OBSERVE"),
    ("trial_id", "forged"),
    ("world_seed", 5),
    ("source_kind", "CLAIMED_LIVE"),
    ("decision_source", "PRIOR_ONLY"),
    ("second_distance_cm", 180),
    ("first_distance_cm", 20),
    ("policy_probe_seqs", [6, 5]),
    ("policy_probe_seqs", [5, 5]),
    ("policy_request_ids", ["duplicate", "duplicate"]),
    ("action_session_id", None),
    ("selected_candidate", "WAIT"),
    ("reason_code", "known_adapter_rejection"),
    ("action_owner_state", "UNKNOWN"),
    ("world_result", "FAILED"),
    ("action_issue_ns", 1_020_000_000),
    ("action_terminal_ns", 1_120_000_000),
    ("evaluator_ns", 1_030_000_000),
    ("elapsed_ms", 99),
    ("health_before", 21),
    ("probe_ms", 0),
    ("server_log_sha256", "0" * 63),
])
def test_near_observed_action_receipt_mutations_fail_closed(field, value):
    fail_mutated(NEAR_OBSERVE, field, value)


@pytest.mark.parametrize("field,value", [
    ("decision_source", "S29_CORRELATED"),
    ("first_distance_cm", 180),
    ("second_distance_cm", 20),
    ("policy_probe_seqs", [5, 6]),
    ("policy_request_ids", ["fake0", "fake1"]),
    ("first_probe_ns", 1_010_000_000),
    ("second_probe_ns", 1_020_000_000),
    ("probe_ms", 10),
    ("selected_candidate", "MOVE_AWAY"),
    ("action_session_id", "foreign-action"),
    ("action_issue_ns", 1_050_000_000),
    ("action_owner_state", "OUTCOME"),
])
def test_no_observation_cannot_obtain_future_source_or_issue_action(field, value):
    fail_mutated(NEAR_NO_OBS, field, value)


@pytest.mark.parametrize("field,value", [
    ("decision_source", "S29_CORRELATED"),
    ("second_distance_cm", 20),
    ("selected_candidate", "MOVE_AWAY"),
    ("probe_ms", 20),
    ("policy_request_ids", ["forged1", "forged2"]),
])
def test_expensive_cheap_exact_preserves_no_observation(field, value):
    fail_mutated(DEAR_CHEAP, field, value)


@pytest.mark.parametrize("field,value", [
    ("action_owner_state", "OUTCOME"),
    ("action_session_id", "foreign-action"),
    ("action_issue_ns", 1_050_000_000),
    ("world_result", "EXECUTED"),
    ("reason_code", "observed_execution"),
])
def test_observed_far_wait_has_no_action_even_with_valid_source(field, value):
    fail_mutated(FAR_OBSERVE, field, value)


@pytest.mark.parametrize("field,value", [
    ("session_id", "native:alien"),
    ("reset_id", "reset:alien"),
])
def test_duplicate_session_and_reset_are_prohibited_across_three_arms(field, value):
    bundle = fake_bundle()
    bundle["trials"][1][field] = bundle["trials"][0][field]
    with pytest.raises(e5.E5Rejected):
        e5.audit_bundle(bundle)


def test_duplicate_evaluator_and_policy_ids_or_receipt_hash_fail():
    for field in ("evaluator_request_id", "receipt_sha256"):
        bundle = fake_bundle()
        bundle["trials"][1][field] = bundle["trials"][0][field]
        with pytest.raises(e5.E5Rejected):
            e5.audit_bundle(bundle)
    bundle = fake_bundle()
    bundle["trials"][NEAR_OBSERVE]["evaluator_request_id"] = (
        bundle["trials"][NEAR_OBSERVE]["policy_request_ids"][0]
    )
    with pytest.raises(e5.E5Rejected):
        e5.audit_bundle(bundle)


def test_cross_trial_reordering_and_partial_denominator_never_pass():
    bundle = fake_bundle()
    bundle["trials"][0], bundle["trials"][1] = (
        bundle["trials"][1], bundle["trials"][0],
    )
    with pytest.raises(e5.E5Rejected):
        e5.audit_bundle(bundle)
    b = fake_bundle()
    b["trials"].pop()
    with pytest.raises(e5.E5Rejected, match="36"):
        e5.audit_bundle(b)


def test_policy_only_gets_price_prior_no_scene_and_evaluator_after_decision():
    for kind in ("SYNTHETIC", "CLAIMED_LIVE"):
        bundle = fake_bundle(kind)
        item = bundle["trials"][NEAR_NO_OBS]
        item["policy_inputs"]["future_distance_cm"] = 20
        with pytest.raises(e5.E5Rejected, match="E0 policy inputs"):
            e5.audit_bundle(bundle)
        b = fake_bundle(kind)
        b["trials"][NEAR_NO_OBS]["evaluator_ns"] = 1_020_000_000
        with pytest.raises(e5.E5Rejected):
            e5.audit_bundle(b)


def test_unknown_and_unavailable_are_counted_without_success_inference():
    for state, world, reason, term in (
        ("UNKNOWN", "FAILED", "adapter_failure_consequence_unknown", 1_075_000_000),
        ("ISSUED", "UNDETERMINED", "world_consequence_undetermined", None),
    ):
        bundle = fake_bundle()
        item = bundle["trials"][NEAR_OBSERVE]
        item["action_owner_state"] = state
        item["world_result"] = world
        item["reason_code"] = reason
        item["action_terminal_ns"] = term
        item["health_after"] = None
        item["movement_m"] = None
        item["damage_points"] = None
        report = e5.audit_bundle(bundle)
        assert report.unresolved_actions == 1
        assert report.physical_effect == "UNDETERMINED"
        # Never misclassify unknown/missing physical outcomes as zero damage.
        altered = copy.deepcopy(bundle)
        altered["trials"][NEAR_OBSERVE]["action_owner_state"] = "OUTCOME"
        with pytest.raises(e5.E5Rejected):
            e5.audit_bundle(altered)


@pytest.mark.parametrize("invalid", [
    None, {}, [], "fixture", True, {"manifest_sha256": "f" * 64},
])
def test_invalid_bundle_shape_rejected(invalid):
    with pytest.raises(e5.E5Rejected):
        e5.audit_bundle(invalid)


def test_strict_integer_float_and_bool_spoof_denial():
    for field in ("world_seed", "start_ns", "elapsed_ms"):
        fail_mutated(NEAR_NO_OBS, field, True)
    for field in ("health_before", "damage_points", "probe_ms"):
        fail_mutated(NEAR_NO_OBS, field, float("nan"))
        fail_mutated(NEAR_NO_OBS, field, float("inf"))
        fail_mutated(NEAR_NO_OBS, field, True)


def test_cli_plan_and_read_only_audit(tmp_path, capsys):
    assert e5._main(["--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert len(plan["trials"]) == 36
    assert plan["physical_run"] == "NOT_AUTHORIZED_OR_LAUNCHED"
    file = tmp_path / "synthetic-e5-receipt.json"
    file.write_text(json.dumps(fake_bundle()), encoding="utf-8")
    assert e5._main(["--audit", str(file)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "OFFLINE_SYNTHETIC_STRUCTURE_VALID"
    assert result["physically_authenticated"] is False
    modified = fake_bundle()
    modified["source_kind"] = "CLAIMED_LIVE"
    file.write_text(json.dumps(modified), encoding="utf-8")
    assert e5._main(["--audit", str(file)]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "REJECTED"


def test_bogus_live_text_is_not_a_real_qualifying_receipt(tmp_path, capsys):
    file = tmp_path / "claimed-live.json"
    file.write_text(json.dumps(fake_bundle("CLAIMED_LIVE")), encoding="utf-8")
    assert e5._main(["--audit", str(file)]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["classification"] == "UNATTESTED_PHYSICAL_CLAIM"
    assert response["physical_effect"] == "UNDETERMINED"
    assert response["physically_authenticated"] is False
