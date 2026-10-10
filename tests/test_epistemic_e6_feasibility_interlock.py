"""Lane A E6: no-live-launch source feasibility interlock + falsification.

Fixtures are *self-reported*, not trusted real Minecraft observations.
Even a consistent complete self-report can never pass physical qualification.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from experiments import epistemic_e5_prospective_gate as e5
from experiments import epistemic_e6_feasibility_interlock as e6


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def all_claims():
    detail = [
        {
            "distance_cm": 20, "entity_name": "zombie",
            "coverage_complete": True, "source_policy": "S24_THRESHOLD_100CM",
        },
        {
            "first_distance_cm": 180, "second_distance_cm": 20,
            "first_request_id": "e6:source:first", "second_request_id": "e6:source:second",
            "first_seq": 8, "second_seq": 10, "same_session": True,
        },
        {"action3_id": "Action3", "action3_state": "OUTCOME",
         "world3_status": "EXECUTED"},
        {"action3_id": "Action3", "action4_id": "Action4",
         "action4_state": "OUTCOME", "world4_status": "EXECUTED",
         "independently_authorized": True},
        {"game_mode": "survival", "mob_ai_enabled": True, "damage_recorded": True},
        {"policy_probe_count": 0, "evaluator_probe_count": 1,
         "evaluator_after_decision": True},
        {"health_measured": True, "movement_measured": True,
         "damage_measured": True, "evaluator_after_decision": True},
        {"trial_count": 36, "distinct_sessions": 36, "distinct_reset_ids": 36,
         "matched_blocks": 12, "same_initial_health": True,
         "equal_followup_horizon": True},
        {"actual_elapsed_ms": 120, "actual_probe_ms": 25,
         "actual_damage_points": 0, "actual_movement_m": 0.3},
        {"new_permission_ref": "e6:fresh-human-approval", "user_owned": True,
         "independent_of_415": True, "explicit_for_e5": True},
    ]
    claims = []
    for i, name in enumerate(e6.REQUIRED):
        claims.append({
            "capability": name, "state": "CLAIMED",
            "source_commit": f"{1000+i:040x}",
            "world_session": (
                "s29-real-parent" if i in (0, 1, 2)
                else "s15-next-action4" if i == 3
                else f"e6:calibration{i}"
            ),
            "witness_sha256": h(f"SELF_REPORTED_E6_NOT_REAL:{i}"),
            "details": detail[i],
        })
    return {
        "manifest_sha256": e6.MANIFEST_SHA256,
        "e5_manifest_sha256": e5.MANIFEST_SHA256,
        "source_kind": "SELF_REPORTED",
        "claims": claims,
    }


def absent_claims():
    report = all_claims()
    for c in report["claims"]:
        c.update({"state": "MISSING", "source_commit": None,
                  "world_session": None, "witness_sha256": None,
                  "details": None})
    return report


def mutate(i: int, name: str, value: object, *, at: str = "details"):
    report = all_claims()
    if at == "details":
        report["claims"][i]["details"][name] = value
    else:
        report["claims"][i][name] = value
    with pytest.raises(e6.E6Rejected):
        e6.check_claims(report)


def test_immutable_prospective_contract_exact_history_and_e5_schedule():
    assert e6.digest() == e6.MANIFEST_SHA256
    assert e6.MANIFEST["base_e5"] == "640d9df6fdc0310ab6189a05084bd13993864a75"
    assert e6.MANIFEST["source_e5"] == e5.MANIFEST_SHA256
    assert e6.MANIFEST["historical_s31a_gamemode"] == "creative"
    assert e6.MANIFEST["historical_s42_threshold_m"] == 4
    assert e6.MANIFEST["e5_s24_threshold_m"] == 1
    assert e6.MANIFEST["e5_distances_m"] == [0.2, 1.8]
    assert e5.MANIFEST["distances_cm"] == [20, 180]
    assert len(e6.REQUIRED) == len(e6.DETAIL_KEYS) == 10
    assert len(e5.planned_trials()) == 36
    assert len({s.block_id for s in e5.planned_trials()}) == 12
    assert "S31B" in {s["owner"] for s in e6.MANIFEST["historical_qualifications"]}


def test_historical_success_cannot_be_promoted_to_e5_physical_evidence():
    v = all_claims()
    v["claims"][0]["source_commit"] = (
        e6.MANIFEST["historical_qualifications"][0]["head"]
    )
    with pytest.raises(e6.E6Rejected, match="old S31-B/S43"):
        e6.check_claims(v)
    v = all_claims()
    v["claims"][1]["source_commit"] = (
        e6.MANIFEST["historical_qualifications"][1]["head"]
    )
    with pytest.raises(e6.E6Rejected, match="old S31-B/S43"):
        e6.check_claims(v)


def test_plan_reports_hard_blockers_without_world_launch():
    receipt = e6.plan()
    assert receipt["classification"] == "E6_PHYSICAL_START_BLOCKED"
    assert receipt["world_launched"] is False
    assert receipt["physical_effect"] == "UNDETERMINED"
    assert len(receipt["trial_ids"]) == 36
    assert len(set(receipt["trial_ids"])) == 36
    assert receipt["incompatible_thresholds_m"] == {"S42": 4, "E5_S24": 1}
    assert receipt["historical_gamemode"] == "creative"
    assert receipt["blocked_capabilities"] == list(e6.REQUIRED)


def test_missing_all_and_partial_remains_blocked():
    report = e6.check_claims(absent_claims())
    assert report.classification == "E6_PHYSICAL_START_BLOCKED"
    assert report.claimed_capabilities == 0
    assert report.missing_capabilities == e6.REQUIRED
    assert report.execution_authorized is False
    assert report.world_launched is False
    assert not report.physically_authenticated
    v = all_claims()
    v["claims"][-1].update({
        "state": "DENIED", "source_commit": None, "world_session": None,
        "witness_sha256": None, "details": None,
    })
    partial = e6.check_claims(v)
    assert partial.classification == "E6_PHYSICAL_START_BLOCKED"
    assert partial.claimed_capabilities == 9
    assert partial.missing_capabilities == (e6.REQUIRED[-1],)
    assert not partial.execution_authorized


def test_all_ten_claims_still_not_real_physical_proof_or_spend():
    outcome = e6.check_claims(all_claims())
    assert outcome.classification == "CLAIMED_CAPABILITIES_UNATTESTED"
    assert outcome.claimed_capabilities == 10
    assert outcome.missing_capabilities == ()
    assert outcome.e5_trial_count == 36 and outcome.e5_block_count == 12
    assert outcome.physically_authenticated is False
    assert outcome.execution_authorized is False
    assert outcome.world_launched is False
    assert outcome.physical_effect == "UNDETERMINED"
    with pytest.raises(FrozenInstanceError):
        outcome.execution_authorized = True


@pytest.mark.parametrize("index,key,value", [
    (0, "distance_cm", 200),
    (0, "distance_cm", 180),
    (0, "distance_cm", True),
    (0, "entity_name", "creeper"),
    (0, "coverage_complete", False),
    (0, "source_policy", "S42_THRESHOLD_4M"),
    (1, "first_distance_cm", 1000),
    (1, "second_distance_cm", 200),
    (1, "first_request_id", "e6:source:second"),
    (1, "second_request_id", "e6:source:first"),
    (1, "second_seq", 8),
    (1, "first_seq", 11),
    (1, "same_session", False),
    (2, "action3_state", "ISSUED"),
    (2, "action3_state", "UNKNOWN"),
    (2, "world3_status", "UNDETERMINED"),
    (3, "action4_id", "Action3"),
    (3, "action4_state", "PROPOSED"),
    (3, "action4_state", "UNKNOWN"),
    (3, "world4_status", "FAILED"),
    (3, "independently_authorized", False),
    (4, "game_mode", "creative"),
    (4, "mob_ai_enabled", False),
    (4, "damage_recorded", False),
    (5, "policy_probe_count", 1),
    (5, "evaluator_probe_count", 0),
    (5, "evaluator_after_decision", False),
    (6, "health_measured", False),
    (6, "movement_measured", False),
    (6, "damage_measured", False),
    (6, "evaluator_after_decision", False),
    (7, "trial_count", 35),
    (7, "distinct_sessions", 35),
    (7, "distinct_reset_ids", 35),
    (7, "matched_blocks", 11),
    (7, "same_initial_health", False),
    (7, "equal_followup_horizon", False),
    (8, "actual_elapsed_ms", 0),
    (8, "actual_probe_ms", 0),
    (8, "actual_damage_points", float("nan")),
    (8, "actual_movement_m", float("inf")),
    (8, "actual_elapsed_ms", True),
    (9, "user_owned", False),
    (9, "independent_of_415", False),
    (9, "explicit_for_e5", False),
    (9, "new_permission_ref", ""),
])
def test_e6_exact_capability_witness_content_fails_closed(index, key, value):
    mutate(index, key, value)


@pytest.mark.parametrize("mode", [
    "two_probe_wrong_session", "action3_world_session", "action4_same_session",
    "action3_cross_id", "duplicate_hash", "reuse_s31b_head", "wrong_sha_size",
    "duplicate_capability", "incomplete_claims", "unsupported_source",
    "wrong_e5_manifest", "wrong_e6_manifest", "undocumented_extra_field",
    "missing_kind_evidence", "missing_claim_value", "false_pass_state",
])
def test_source_lineage_or_claim_forgery_rejected(mode):
    data = all_claims()
    claims = data["claims"]
    if mode == "two_probe_wrong_session":
        claims[1]["world_session"] = "s29:alien"
    elif mode == "action3_world_session":
        claims[2]["world_session"] = "s29:other-action3"
    elif mode == "action4_same_session":
        claims[3]["world_session"] = claims[2]["world_session"]
    elif mode == "action3_cross_id":
        claims[3]["details"]["action3_id"] = "other-parent"
    elif mode == "duplicate_hash":
        claims[1]["witness_sha256"] = claims[0]["witness_sha256"]
    elif mode == "reuse_s31b_head":
        claims[2]["source_commit"] = e6.MANIFEST["historical_qualifications"][0]["head"]
    elif mode == "wrong_sha_size":
        claims[0]["source_commit"] = "a" * 39
    elif mode == "duplicate_capability":
        claims[1]["capability"] = claims[0]["capability"]
    elif mode == "incomplete_claims":
        data["claims"].pop()
    elif mode == "unsupported_source":
        data["source_kind"] = "LIVE_AUTHENTICATED"
    elif mode == "wrong_e5_manifest":
        data["e5_manifest_sha256"] = "a" * 64
    elif mode == "wrong_e6_manifest":
        data["manifest_sha256"] = "b" * 64
    elif mode == "undocumented_extra_field":
        claims[0]["physical_pass"] = True
    elif mode == "missing_kind_evidence":
        claims[0]["state"] = "MISSING"
    elif mode == "missing_claim_value":
        claims[0]["details"] = None
    elif mode == "false_pass_state":
        claims[0]["state"] = "PASS"
    with pytest.raises(e6.E6Rejected):
        e6.check_claims(data)


@pytest.mark.parametrize("mode", [
    "non_dictionary", "empty", "extra", "missing_key", "not_array", "float_bool",
])
def test_bad_schema_denied(mode):
    payload = all_claims()
    if mode == "non_dictionary":
        payload = "historical E6 is fine"
    elif mode == "empty":
        payload = {}
    elif mode == "extra":
        payload["approved"] = True
    elif mode == "missing_key":
        payload.pop("claims")
    elif mode == "not_array":
        payload["claims"] = {}
    elif mode == "float_bool":
        payload["claims"][7]["details"]["trial_count"] = True
    with pytest.raises(e6.E6Rejected):
        e6.check_claims(payload)


def test_e6_read_only_cli_does_not_infer_execution_or_allow_success_exit(tmp_path, capsys):
    assert e6.main(["--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["classification"] == "E6_PHYSICAL_START_BLOCKED"
    assert plan["world_launched"] is False
    path = tmp_path / "untrusted-self-report.json"
    path.write_text(json.dumps(all_claims()), encoding="utf-8")
    assert e6.main(["--check", str(path)]) == 3
    self_report = json.loads(capsys.readouterr().out)
    assert self_report["classification"] == "CLAIMED_CAPABILITIES_UNATTESTED"
    assert self_report["world_launched"] is False
    assert self_report["execution_authorized"] is False
    path.write_text(json.dumps(absent_claims()), encoding="utf-8")
    assert e6.main(["--check", str(path)]) == 4
    no_evidence = json.loads(capsys.readouterr().out)
    assert no_evidence["classification"] == "E6_PHYSICAL_START_BLOCKED"
    path.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    assert e6.main(["--check", str(path)]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["classification"] == "REJECTED"


def test_historic_physical_evidence_not_cross_imported_as_e5_authority():
    old = copy.deepcopy(e6.MANIFEST["historical_qualifications"])
    assert {v["owner"] for v in old} == {"S31B", "S43"}
    assert e6.MANIFEST["historical_s31a_gamemode"] == "creative"
    assert 2.0 not in e6.MANIFEST["e5_distances_m"]
    assert 10.0 not in e6.MANIFEST["e5_distances_m"]
    assert e6.MANIFEST["historical_s42_threshold_m"] != 1
    fake = all_claims()
    fake["claims"][4]["details"]["game_mode"] = "creative"
    with pytest.raises(e6.E6Rejected, match="creative mode"):
        e6.check_claims(fake)
