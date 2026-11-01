"""MP11 Stage0: fake OPEN provider and fake S49/S16/Paper receipt, NEVER World."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l2_mp11_experiment import (
    EXPERIMENTS,
    L2ExperimentLoop,
    MP11Rejected,
    WorldTrialReceipt,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionRequest,
    OpenCognitionResult,
    ProviderExpression,
    RelayEngine,
)


def fake_open(request: OpenCognitionRequest) -> OpenCognitionResult:
    assert request.focus == "L2_MODEL_STRUCTURE_AND_APPLICABILITY_RECONSIDERATION"
    previous = json.loads(request.context[2].value_json)
    allowed = json.loads(request.context[1].value_json)
    # A fixture provider that *reads* previous outcomes to select next condition.
    if len(previous) == 0:
        experiment, model = "GRASS_SHORT", "SINGLE_DECAY"
    elif len(previous) == 1 and previous[-1]["absolute_error_m"] > 0.01:
        experiment, model = "ICE_SHORT", "SURFACE_DEPENDENT"
    elif len(previous) == 2:
        experiment, model = "ICE_LONG", "INITIAL_SPEED_DEPENDENT"
    else:
        experiment, model = "GRASS_LONG", "PHASE_DEPENDENT"
    assert experiment in allowed
    return OpenCognitionResult(
        request_id=request.request_id,
        text=json.dumps({
            "experiment_id":experiment,
            "model_family":model,
            "explanation":"Past prediction errors suggest the model applicability is uncertain.",
            "falsification_test":"Compare the frozen expected WAIT motion against original Paper movement.",
            "predicted_wait_total_m":0.02,
        }),
        provenance=Provenance(source="fixture.provider",reference=request.request_id),
    )


def owner_fixture(loop, proposal, *, movement=0.02, tick=100):
    return WorldTrialReceipt(
        world_uuid=loop.world_uuid, subject_uuid=loop.subject_uuid,
        session_id=loop.session_id, proposal_sha256=proposal.proposal_sha256,
        experiment_id=proposal.experiment_id, action_id=f"s49-original-{proposal.round}",
        action_outcome="S16_OUTCOME",
        actual_floor_material=EXPERIMENTS[proposal.experiment_id][0],
        actual_input_regime=EXPERIMENTS[proposal.experiment_id][1],
        wait_ticks=tuple(range(tick,tick+8)),
        wait_motion_m=(movement,)*8,
        paper_original_sha256="a"*64,
        native_original_sha256="b"*64,
    )


def new_loop():
    return L2ExperimentLoop("world-uuid-A","subject-id","native-session-01")


def test_four_rounds_one_world_hypothesis_changes_but_no_actual_action_or_learning():
    loop = new_loop()
    seen = []
    for round_num in range(4):
        p=loop.propose(fake_open)
        seen.append((p.experiment_id,p.model_family))
        assert p.round == round_num+1
        assert not p.executable_action
        assert p.learning_admission == 0
        r=owner_fixture(loop,p,movement=.03 if round_num == 0 else .01,
                        tick=100+round_num*10)
        scored=loop.record_owner_result(r)
        assert scored.original_trial_world_uuid == loop.world_uuid
        assert scored.source_status == "UNVERIFIED_OWNER_SUPPLIED_FIXTURE"
        assert scored.hypothesis_supported == "NOT_ESTABLISHED_WITH_ONE_TRIAL"
    assert seen == [
        ("GRASS_SHORT","SINGLE_DECAY"),
        ("ICE_SHORT","SURFACE_DEPENDENT"),
        ("ICE_LONG","INITIAL_SPEED_DEPENDENT"),
        ("GRASS_LONG","PHASE_DEPENDENT"),
    ]
    assert all(r.world_uuid == loop.world_uuid for r in loop.receipts)
    out=loop.summary()
    assert out["rounds_completed"]==4
    assert out["real_world_multi_trial_verified"] is False
    assert out["actual_minecraft_actions_issued_here"]==0
    assert out["learning_admissions"]==0
    with pytest.raises(MP11Rejected):
        loop.propose(fake_open)
    loop.stop()


@pytest.mark.parametrize("case",[
    "forged_world","foreign_session","foreign_subject","wrong_ticket",
    "mismatched_condition","bad_outcome","missing_sample",
    "noncontiguous_ticks","nan_motion","wrong_sha","duplicate_action",
    "nonmonotonic_trial","wrong_floor","wrong_input",
])
def test_fake_original_owner_receipt_fail_closed(case):
    loop=new_loop()
    p=loop.propose(fake_open)
    r=owner_fixture(loop,p)
    if case=="forged_world":
        r=replace(r,world_uuid="other-world")
    elif case=="foreign_session":
        r=replace(r,session_id="other-session")
    elif case=="foreign_subject":
        r=replace(r,subject_uuid="other-subject")
    elif case=="wrong_ticket":
        r=replace(r,proposal_sha256="c"*64)
    elif case=="mismatched_condition":
        r=replace(r,experiment_id="ICE_LONG")
    elif case=="bad_outcome":
        r=replace(r,action_outcome="S16_UNKNOWN")
    elif case=="missing_sample":
        r=replace(r,wait_motion_m=r.wait_motion_m[:-1])
    elif case=="noncontiguous_ticks":
        r=replace(r,wait_ticks=(100,101,102,104,105,106,107,108))
    elif case=="nan_motion":
        r=replace(r,wait_motion_m=(float("nan"),)*8)
    elif case=="wrong_sha":
        r=replace(r,paper_original_sha256="source-not-verified")
    elif case=="wrong_floor":
        r=replace(r,actual_floor_material="LAVA")
    elif case=="wrong_input":
        r=replace(r,actual_input_regime="UNBOUNDED")
    else:
        loop.record_owner_result(r)
        p2=loop.propose(fake_open)
        r=owner_fixture(loop,p2,tick=120)
        if case=="duplicate_action":
            r=replace(r,action_id=loop.receipts[0].action_id)
        else:
            r=replace(r,wait_ticks=tuple(range(101,109)))
    with pytest.raises(MP11Rejected):
        loop.record_owner_result(r)
    assert loop.pending is not None


@pytest.mark.parametrize("invalid",[
    "not-json","not-object","added-command","unknown-experiment",
    "bad-family","nan-prediction","negative-prediction",
    "invalid-falsification",
])
def test_open_llm_schema_or_unsafe_action_fail_closed(invalid):
    loop=new_loop()
    def bad(req):
        obj={
            "experiment_id":"GRASS_SHORT",
            "model_family":"SINGLE_DECAY",
            "explanation":"A bounded body-model structure is being examined.",
            "falsification_test":"Use the original future WAIT displacement to compare.",
            "predicted_wait_total_m":.02,
        }
        if invalid=="added-command":
            obj["minecraft_command"]="op RelaySelf"
        if invalid=="unknown-experiment":
            obj["experiment_id"]="WORLD_RESET_AND_MOVE"
        if invalid=="bad-family":
            obj["model_family"]="EXEC_SHELL"
        if invalid=="nan-prediction":
            obj["predicted_wait_total_m"]=float("nan")
        if invalid=="negative-prediction":
            obj["predicted_wait_total_m"]=-1
        if invalid=="invalid-falsification":
            obj["falsification_test"]="vague"
        if invalid=="not-json":
            body="reasoning without constrained JSON"
        elif invalid=="not-object":
            body="[]"
        else:
            body=json.dumps(obj)
        return OpenCognitionResult(
            request_id=req.request_id,text=body,
            provenance=Provenance("fixture.provider","bad-l2"),
        )
    with pytest.raises(MP11Rejected):
        loop.propose(bad)
    assert len(loop.proposals)==0
    assert loop.pending is None


def test_provider_unavailable_never_executes_or_autofalls_back():
    loop=new_loop()
    with pytest.raises(MP11Rejected):
        loop.propose(None)
    with pytest.raises(MP11Rejected):
        loop.record_owner_result({})
    assert loop.summary()["actual_minecraft_actions_issued_here"]==0


def test_stale_provider_request_and_already_pending_rejected():
    loop=new_loop()
    def stale(req):
        ans=fake_open(req)
        return replace(ans,request_id="stale-request")
    with pytest.raises(MP11Rejected):
        loop.propose(stale)
    p=loop.propose(fake_open)
    with pytest.raises(MP11Rejected):
        loop.propose(fake_open)
    with pytest.raises(MP11Rejected):
        loop.stop()
    assert p.experiment_id=="GRASS_SHORT"


def test_model_input_carries_last_trial_errors_not_assumed_world_truth():
    loop=new_loop()
    p=loop.propose(fake_open)
    loop.record_owner_result(owner_fixture(loop,p,movement=.04))
    r=loop.l2_request()
    limits=json.loads(r.context[0].value_json)
    history=json.loads(r.context[2].value_json)
    assert limits["current_world_observation"]=="HOST_FIXTURE_STAGE0_ONLY"
    assert limits["training_admission"] is False
    assert history[0]["absolute_error_m"]==pytest.approx(.3)
    assert history[0]["source_status"]=="UNVERIFIED_OWNER_SUPPLIED_FIXTURE"


def test_real_relayengine_open_contract_routes_exactly_one_l2_provider_call():
    """Adapter integration only; provider here is synthetic, NOT an LLM."""
    calls=[]
    def provider(request, *, mode):
        assert mode is CognitionMode.OPEN
        assert isinstance(request, OpenCognitionRequest)
        calls.append(request.request_id)
        model_fixture=fake_open(request)
        return ProviderExpression(
            text=model_fixture.text,
            provenance=Provenance("fixture.provider","relay-open-integration"),
        )
    engine=RelayEngine(provider)
    loop=new_loop()
    proposal=loop.propose(engine.open)
    assert calls == [f"mp11:{loop.world_uuid}:round-1"]
    assert proposal.model_family=="SINGLE_DECAY"
    assert proposal.provider_source=="fixture.provider"
    assert proposal.executable_action is False


def test_unhashable_model_fields_cannot_leak_as_unhandled_runtime_errors():
    loop=new_loop()
    def bad(req):
        answer=fake_open(req)
        obj=json.loads(answer.text)
        obj["experiment_id"]=["GRASS_SHORT"]
        return replace(answer,text=json.dumps(obj))
    with pytest.raises(MP11Rejected):
        loop.propose(bad)
