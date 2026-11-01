"""MP12 local run: source-qualified G3 replay to actual llama.cpp L2 OPEN.

Offline historical data only. Model response cannot authorize movement or L1
learning. The operator must provide a RUNNING local llama.cpp server to call.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.self_body_mp12_capability_shadow import (
    MP12ShadowRejected,
    build_l2_request,
    load_original_experiences,
    render_shadow_result,
    validate_l2_response,
)
from relay_self.relay_engine import RelayEngine


def run(
    root: Path, destination: Path, *, endpoint: str | None,
    model: str | None, count: int = 3, preflight_only: bool = False,
) -> dict:
    if (not isinstance(count,int) or isinstance(count,bool) or not 1<=count<=3
            or not destination.is_absolute() or destination.exists()
            or destination.is_symlink()):
        raise MP12ShadowRejected("fresh absolute output and 1..3 original trials required")
    originals=load_original_experiences(root)
    if len(originals)!=3:
        raise MP12ShadowRejected("exactly three original G3 Paper source windows required")
    if preflight_only:
        if endpoint is not None or model is not None:
            raise MP12ShadowRejected("preflight does not accept an LLM endpoint")
        result=render_shadow_result(originals[:count],None)
        with destination.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        return result
    if not isinstance(endpoint,str) or not isinstance(model,str) or not model.strip():
        raise MP12ShadowRejected("explicit actual llama.cpp endpoint and model required")
    parsed=urlsplit(endpoint)
    if (parsed.scheme!="http" or parsed.hostname not in ("localhost","127.0.0.1","::1")
            or parsed.path!="/v1/chat/completions" or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise MP12ShadowRejected("only exact local llama.cpp chat-completions endpoint permitted")
    provider=LlamaCppRelayProvider(endpoint=endpoint,model=model,timeout=90.0)
    engine=RelayEngine(provider)
    rounds=[]
    try:
        for n in range(1,count+1):
            visible=originals[:n]
            request=build_l2_request(visible)
            result=engine.open(request)
            proposal=validate_l2_response(result,request,visible)
            rounds.append(render_shadow_result(
                visible,proposal,model=model,elapsed_ns=result.elapsed_ns,
                provider_call_count=result.provider_call_count,
            ))
        output={
            "classification":"MP12_HISTORICAL_SOURCE_PREFIX_ACTUAL_LLAMA_CPP_RESPONSES",
            "model_requested_not_weights_attested":model,
            "actual_relay_engine_open_calls":len(rounds),
            "rounds":rounds,
            "provider_model_identity":"NOT_INDEPENDENTLY_ATTESTED",
            "model_outputs_changed_after_evidence":"NOT_A_PROOF_OF_LEARNING",
            "original_G3_historical_trials_influenced_by_these_proposals":False,
            "physical_experiments_issued":0,
            "ability_limits_physically_proven":False,
            "learning_admissions":0,
            "qualification":"NO_GO","science":"NOT_RUN",
        }
    except Exception as exc:
        # Failure retains the already validated prior responses. Never retry or
        # manufacture another L2 answer. Keep new output exclusively local.
        output={
            "classification":"MP12_L2_PROVIDER_OR_SCHEMA_FAILED_CLOSED",
            "model_requested_not_weights_attested":model,
            "validated_rounds_before_failure":rounds,
            "failure":f"{type(exc).__name__}: {exc}",
            "physical_experiments_issued":0,
            "learning_admissions":0,
            "qualification":"NO_GO","science":"NOT_RUN",
        }
        with destination.open("x",encoding="utf-8") as f:
            json.dump(output,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        raise
    with destination.open("x",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    return output


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--g3-originals",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--endpoint")
    p.add_argument("--model")
    p.add_argument("--rounds",type=int,default=3)
    p.add_argument("--preflight-only",action="store_true")
    args=p.parse_args()
    result=run(
        args.g3_originals,args.output,
        endpoint=args.endpoint,model=args.model,count=args.rounds,
        preflight_only=args.preflight_only,
    )
    print("MP12_RESULT="+json.dumps({
        "classification":result["classification"],
        "actual_llama_cpp_calls":result.get("actual_relay_engine_open_calls",0),
        "qualification":result["qualification"],
        "science":result["science"],
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
