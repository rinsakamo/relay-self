"""MP12 fake tests: typed historical source prefixes, NO llama model or World."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.self_body_mp12_capability_shadow import (
    MP12ShadowRejected,
    OriginalExperience,
    build_l2_request,
    render_shadow_result,
    validate_l2_response,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionResult,
    ProviderExpression,
    RelayEngine,
)
from tools.mp12_l2_source_shadow import run


def samples():
    """Synthetic typed shape inspired by G3, not original Paper qualification."""
    motions=(
        (.049492188301323625,.009543604920852156,.005210808286785218,0.,0.,0.,0.,0.),
        (.09064503351890774,.017479129891670553,.009543604920852156,.005210808286785218,0.,0.,0.,0.),
        (.09064503351890818,.017479129891670553,.009543604920851934,.00521080828678544,0.,0.,0.,0.),
    )
    return tuple(OriginalExperience(
        ordinal=i+1,action_id=f"s49-native-move-{i}",world_uuid="real-paper-uuid-shape",
        subject_uuid="subject-shape",session_id="native-shape",
        paper_wait_ticks=tuple(range(100+i*100,108+i*100)),
        paper_wait_motion_m=x,
        actual_wait_total_m=sum(x),
        frozen_slope_065_mae_m=sum(abs(.65*a-b) for a,b in zip(x,x[1:]))/7,
        cheap_zero_mae_m=sum(x[1:])/7,
        original_paper_prefix_sha256=f"{i+1:064x}",
        original_paper_prefix_lines=100*(i+1),
    ) for i,x in enumerate(motions))


def answer(request,*,kind="UNKNOWN",experiment="ICE_SHORT"):
    return OpenCognitionResult(
        request_id=request.request_id,
        text=json.dumps({
            "experiment_id":experiment,
            "model_family":"INITIAL_SPEED_DEPENDENT",
            "explanation":"The first WAIT displacement varies despite identical material.",
            "falsification_test":"Repeat from a verified matched initial speed and compare coast.",
            "predicted_wait_total_m":.11,
            "capability_assessment":kind,
            "ability_boundary_reason":"Available trials do not establish reliable stopping control.",
        }),
        provenance=Provenance("llama.cpp","simulated-test-only-not-real-model"),
    )


def test_prefix_excludes_future_experiences_at_each_historical_round():
    obs=samples()
    for n in (1,2,3):
        req=build_l2_request(obs[:n])
        assert req.focus=="MODEL_ERROR_AND_CURRENT_SELF_CAPABILITY_UNKNOWN"
        history=json.loads(req.context[1].value_json)
        assert len(history)==n
        assert [x["ordinal"] for x in history]==list(range(1,n+1))
        assert json.loads(req.context[0].value_json)["future_history_hidden"] is True
        assert req.request_id.endswith(f"after-{n}-real-trials")
        assert "ability" in req.instruction.lower()
        p=validate_l2_response(answer(req),req,obs[:n])
        assert p.source_round==n
        assert p.capability_assessment=="UNKNOWN"
        assert p.learning_admissions==0
        assert p.action_authority is False
        assert p.classification=="RETROSPECTIVE_L2_SHADOW_PROPOSAL_NOT_EXECUTED"
        out=render_shadow_result(obs[:n],p,model="synthetic-shape",provider_call_count=1)
        assert out["future_physical_actions_executed"]==0
        assert out["ability_infeasibility_established"] is False


def test_three_historical_rounds_can_call_relayengine_open_mock_but_not_model():
    calls=[]
    def mock_provider(request,*,mode):
        assert mode is CognitionMode.OPEN
        calls.append(request.request_id)
        x=answer(request)
        return ProviderExpression(text=x.text,provenance=x.provenance)
    engine=RelayEngine(mock_provider)
    obs=samples()
    proposals=[]
    for n in (1,2,3):
        req=build_l2_request(obs[:n])
        proposals.append(validate_l2_response(engine.open(req),req,obs[:n]))
    assert len(calls)==3
    assert [x.source_evidence_count for x in proposals]==[1,2,3]
    assert len({x.proposal_sha256 for x in proposals})==3


@pytest.mark.parametrize("attack",[
    "future_history","foreign_world","bad_order","bad_type",
    "raw_action","unbounded_capability","wrong_provider","bad_prediction",
    "missing_json_field","extra_command","invalid_reason","stale_request",
])
def test_fail_closed_wrong_prefix_or_unauthorized_provider(attack):
    obs=samples()
    if attack in {"future_history","foreign_world","bad_order","bad_type"}:
        bad={
            "future_history":(obs[0],obs[2]),
            "foreign_world":(obs[0],replace(obs[1],world_uuid="bad")),
            "bad_order":(obs[1],obs[0]),
            "bad_type":(dict(),),
        }[attack]
        with pytest.raises(MP12ShadowRejected):
            build_l2_request(bad)
        return
    req=build_l2_request(obs[:1])
    reply=answer(req)
    data=json.loads(reply.text)
    if attack=="raw_action":
        data["experiment_id"]="TELEPORT_AND_ISSUE_ACTION"
    elif attack=="unbounded_capability":
        data["capability_assessment"]="IMPOSSIBLE_FOREVER"
    elif attack=="bad_prediction":
        data["predicted_wait_total_m"]=float("nan")
    elif attack=="missing_json_field":
        del data["ability_boundary_reason"]
    elif attack=="extra_command":
        data["minecraft_command"]="teleport player"
    elif attack=="invalid_reason":
        data["ability_boundary_reason"]="no"
    elif attack=="wrong_provider":
        reply=replace(reply,provenance=Provenance("fixture.provider","fake"))
    elif attack=="stale_request":
        reply=replace(reply,request_id="other-request")
    if attack not in ("wrong_provider","stale_request"):
        reply=replace(reply,text=json.dumps(data))
    with pytest.raises(MP12ShadowRejected):
        validate_l2_response(reply,req,obs[:1])


def test_preflight_does_not_call_provider_or_pretend_world_or_model(tmp_path:Path,monkeypatch):
    def fake(root):
        assert root==tmp_path
        return samples()
    monkeypatch.setattr("tools.mp12_l2_source_shadow.load_original_experiences",fake)
    out=tmp_path/"preflight.json"
    report=run(tmp_path,out,endpoint=None,model=None,count=2,preflight_only=True)
    assert json.loads(out.read_text())["classification"]==(
        "MP12_ORIGINAL_SOURCE_PREFIX_PREFLIGHT_NO_MODEL")
    assert report["actual_open_calls_observed_in_this_run"]==0
    assert report["learning_admissions"]==0
    with pytest.raises(MP12ShadowRejected):
        run(tmp_path,out,endpoint=None,model=None,preflight_only=True)


def test_no_network_before_strict_loopback_model_preflight(tmp_path,monkeypatch):
    monkeypatch.setattr(
        "tools.mp12_l2_source_shadow.load_original_experiences",lambda root:samples())
    for endpoint in (
        None,"https://127.0.0.1:8080/v1/chat/completions",
        "http://external.example/v1/chat/completions",
        "http://127.0.0.1:8080/other",
    ):
        with pytest.raises(MP12ShadowRejected):
            run(tmp_path,tmp_path/("not-created.json"),endpoint=endpoint,model="m")
    assert not (tmp_path/"not-created.json").exists()
