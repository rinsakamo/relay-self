"""Reject grant replay / profile substitution before any physical M0.2 QUAL."""
import copy

import pytest

from experiments.standard_env import m02_v7_new_plugin_admission as gate


def candidate():
    return {
        "s_exact_head":"2d62b057605c3aaf9bca770b851680302b3e2d56",
        "r_exact_head":"c4b8ddb5df8285cf7850bfd4055f0055359f369a",
        "plugin_sha256":"3260cbf5cad1f91d5fa67d2101a059260c580298d38845f063f7575837cfc23f",
        "paper_sha256":gate.PAPER_SHA,
        "config_sha256":gate.BASE_CONFIG_SHA,
        "arm":"BASE_ON",
        "grant_id":"NEW_USER_20261016_M02_BASE_ON_ONCE",
        "qualification_run_id":"new-base-on-once",
        "source_evidence_root":"/tmp/fresh-one-shot-m02-original",
        "source_ci_run_id":38877646701,
        "independent_r_receipt":None,
        "previous_grants_reused":False,
        "new_java_starts":0,
        "new_node_sessions":0,
        "scientific_trials":0,
    }


def test_shape_only_never_authorizes_or_attests_real_source():
    result=gate.review_candidate(candidate())
    assert result["classification"]==gate.CLASS
    assert result["candidate_arm"]=="BASE_ON"
    assert not result["new_jar_engineering_qualified"]
    assert not result["one_shot_authorization_consumed"]
    assert not result["physical_launch_permission_issued_by_this_module"]
    assert not result["qualification_run_executed"]
    assert result["independent_ci_source_authentication"]=="NOT_PERFORMED_BY_THIS_MODULE"
    assert not result["science_go"]


@pytest.mark.parametrize(("field", "bad"), [
    ("grant_id",gate.OLD_SPENT_GRANT),
    ("grant_id",""),
    ("previous_grants_reused",True),
    ("plugin_sha256",gate.OLD_PLUGIN_SHA),
    ("plugin_sha256","0"*30),
    ("config_sha256","f"*64),
    ("paper_sha256","f"*64),
    ("arm","WALK_ZERO"),
    ("qualification_run_id",""),
    ("source_evidence_root","../old/qual"),
    ("source_ci_run_id",0),
    ("independent_r_receipt",{"classification":"QUALIFIED"}),
    ("new_java_starts",1),
    ("new_node_sessions",1),
    ("scientific_trials",1),
    ("s_exact_head","f"*39),
])
def test_invalid_or_spent_preworld_proposal_fails_closed(field,bad):
    x=copy.deepcopy(candidate())
    x[field]=bad
    with pytest.raises(gate.PreworldRejected):
        gate.review_candidate(x)


def test_no_unregistered_input_fields_promoted():
    x=candidate()
    x["self_reported_qualified"]=True
    with pytest.raises(gate.PreworldRejected):
        gate.review_candidate(x)
