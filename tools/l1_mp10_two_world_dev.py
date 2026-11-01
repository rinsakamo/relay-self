"""MP10 native next-epoch typed SelfBody correction, real Paper source DEV audit.

No new action owner, no model admission, no live policy changes. Candidate is
produced only AFTER original L0 choice and scored IN SAMPLE until a future World.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_mp9_selector import train_mp8_only
from tools.l1_mp9_two_world_dev import (
    PAPER_SHA,
    PAPER_SIZE,
    _must,
    compare_original_states,
    original_json,
    port_free,
    review_world,
    run_one,
    sha,
    timestamp,
)

CONFIRM = "MP10-TYPED-NEXT-EPOCH-REVISION-TWO-WORLDS-DEV-20261101"
SURFACES = ("NORMAL", "ICE")
TRIGGER_M = 0.002


def review_revision(root: Path, condition: str, paper: dict, prior) -> dict:
    """Recompute proposal from sealed original Paper; not a future score."""
    report = json.loads((root / "s49-report.json").read_text())
    mp10 = report.get("mp10_l1_revision", {})
    proposal = mp10.get("candidate", {})
    _must(mp10.get("status") == "NEXT_NATIVE_EPOCH_REVISION_PROPOSED_AFTER_L0",
          "no post-L0 typed native revision")
    _must(mp10.get("durable_learning_admissions") == 0
          and mp10.get("no_l0_actions_modified") is True
          and mp10.get("heldout_after_revision") == "NOT_RUN",
          "MP10 owner permission escalation")
    native = report.get("live_next_epoch", {})
    readback = native.get("readback", {})
    _must(proposal.get("native_observation_ref") == readback.get("current_native_ref")
          and proposal.get("native_epoch_id") == readback.get("current_epoch_id")
          and proposal.get("world_uuid") == paper["world_uuid"]
          and proposal.get("action_id") in
              {x.get("action") for x in report.get("actual_native_actions", [])}
          and proposal.get("subject_uuid") == paper["subject_uuid"]
          and proposal.get("session_id") == report.get("session_id")
          and proposal.get("paper_prefix_sha256")
              == readback.get("previous_paper_sha256"),
          "candidate not bound to original Body/World/Paper source")
    old = prior.normal_slope if condition == "NORMAL" else prior.ice_slope
    motions = paper["motions_m"]
    xs, ys = motions[:-1], motions[1:]
    _must(len(xs) == 7 and all(math.isfinite(x) and x >= 0 for x in motions),
          "not seven authentic finite original Paper motion transitions")
    mae = sum(abs(old*x-y) for x,y in zip(xs,ys))/7
    denominator = sum(x*x for x in xs)
    status = (
        "ABSTAIN_INSUFFICIENT_MOTION" if denominator <= 1e-10
        else "KEEP_NO_MATERIAL_ERROR" if mae < TRIGGER_M
        else "REVISE_CANDIDATE_IN_SAMPLE_ONLY"
    )
    fitted = (old if status != "REVISE_CANDIDATE_IN_SAMPLE_ONLY"
              else sum(x*y for x,y in zip(xs,ys))/denominator)
    if not math.isfinite(fitted) or fitted < 0 or fitted > 2:
        status = "ABSTAIN_OUT_OF_MODEL_DOMAIN"
        fitted = old
    insample = sum(abs(fitted*x-y) for x,y in zip(xs,ys))/7
    expected = {
        "world_uuid": paper["world_uuid"],
        "subject_uuid": paper["subject_uuid"],
        "surface": "GRASS_BLOCK" if condition == "NORMAL" else "PACKED_ICE",
        "previous_slope": old,
        "proposed_slope": fitted,
        "old_mae_m": mae,
        "proposed_in_sample_mae_m": insample,
        "observed_pair_count": 7,
        "trigger_threshold_m": TRIGGER_M,
        "status": status,
    }
    for k, value in expected.items():
        v = proposal.get(k)
        if type(value) is float:
            _must(type(v) is float and math.isclose(v, value, abs_tol=1e-12),
                  "MP10 original proposal value mismatch " + k)
        else:
            _must(v == value, "MP10 original proposal status mismatch " + k)
    fields = {
        k: proposal[k] for k in (
            "session_id", "native_epoch_id", "native_observation_ref",
            "world_uuid", "action_id", "subject_uuid",
            "paper_prefix_sha256", "prior_ticket_sha256",
            "surface", "previous_slope", "proposed_slope",
            "observed_pair_count", "old_mae_m", "proposed_in_sample_mae_m",
            "trigger_threshold_m", "status",
        )
    }
    digest = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode()
    ).hexdigest()
    _must(proposal.get("revision_sha256") == digest,
          "MP10 revision ticket digest mismatch")
    _must(proposal.get("current_l0_action_modified") is False
          and proposal.get("durable_learning_admissions") == 0
          and proposal.get("future_heldout_mae_m") == "NOT_OBSERVED",
          "no post-observation learning authority permitted")

    journal = [
        json.loads(line) for line in (root / "prediction-original.jsonl").read_text().splitlines()
    ]
    frozen = [j for j in journal if j.get("kind") == "MP9_SHADOW_SELECTION_FIXED"]
    revisions = [j for j in journal if j.get("kind") == "MP10_L1_REVISION_NEXT_EPOCH"]
    observed = [j for j in journal if j.get("kind") == "OBSERVED"]
    _must(len(frozen) == len(revisions) == 1 and len(observed) == 8
          and frozen[0]["host_monotonic_ns"] < observed[0]["host_monotonic_ns"]
          and observed[-1]["host_monotonic_ns"] < revisions[0]["host_monotonic_ns"]
          and revisions[0]["proposal"] == proposal
          and revisions[0].get("no_owner_or_policy_mutation") is True
          and revisions[0].get("prior_ticket_sha256")
              == proposal["prior_ticket_sha256"],
          "MP10 revision not recorded only after complete Paper observations")
    return {
        "condition": condition,
        "native_previous_action_id": proposal["action_id"],
        "native_read_source": proposal["native_observation_ref"],
        "world_uuid": paper["world_uuid"],
        "paper_original_sha256": paper["source_sha256"],
        "source_prefix_sha256": proposal["paper_prefix_sha256"],
        "original_s49_actions": 1,
        "original_paper_eight_wait_ticks": 8,
        "original_paper_seven_old_model_scores": 7,
        "revision_status": proposal["status"],
        "previous_slope": old,
        "proposed_slope": fitted,
        "old_mae_m": mae,
        "new_in_sample_mae_m": insample,
        "revision_sha256": digest,
        "original_l0_unchanged": True,
        "durable_learning_admission": 0,
        "future_heldout_generalization": "NOT_TESTED",
        "paper_source_authority": "DEV_ORIGINAL_AFTER_COMPLETE_SHUTDOWN",
        "current_model_deployment": "NOT_ADMITTED",
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    p=argparse.ArgumentParser()
    for name in ("output","paper-jar","plugin-jar","config-default","node-runtime"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--confirm",required=True)
    p.add_argument("--preflight-only",action="store_true")
    a=p.parse_args()
    if (a.confirm != CONFIRM or not a.output.is_absolute() or a.output.exists()
            or a.output.is_symlink()):
        p.error("fresh absolute MP10 root and explicit DEV 2-World scope needed")
    a.output.mkdir(parents=True)
    try:
        _must(port_free(),"original World port already occupied")
        _must(a.paper_jar.is_file() and sha(a.paper_jar)==PAPER_SHA
              and a.paper_jar.stat().st_size==PAPER_SIZE,"original Paper mismatch")
        _must(a.plugin_jar.is_file() and a.config_default.is_file(),
              "missing original Paper plugin/config")
        _must(a.node_runtime.is_absolute() and not a.node_runtime.is_symlink(),
              "original Node runtime not owned")
        pkg=json.loads((a.node_runtime/"node_modules/mineflayer/package.json").read_text())
        _must(pkg.get("version")=="4.39.0","wrong Mineflayer runtime")
        prior=train_mp8_only()
        original_json(a.output/"MP10_PREWORLD_FROZEN_PLAN.json",{
            "run_head":os.environ.get("GITHUB_SHA"),
            "time":timestamp(),
            "training_source_sha1":prior.source_sha1,
            "frozen_normal_ice_priors":asdict(prior),
            "new_seed":"RelaySelf-MP10-Typed-Correction-20261101",
            "surface_order":["NORMAL","ICE"],
            "trigger_mae_m":TRIGGER_M,
            "max_worlds":2,"max_original_s49_actions":2,
            "proposal_after_original_next_L0":True,
            "future_heldout_not_run":True,
            "cheap_same_information_ols_equivalent":True,
            "qualification":"NO_GO","science":"NOT_RUN",
        })
        if a.preflight_only:
            print("MP10_TYPED_REVISION_PREFLIGHT_OK worlds_started=0",flush=True)
            return 0
        worlds={}
        diagnostics={}
        for mode in SURFACES:
            _must(port_free(),"port still bound from prior World")
            rc,expired=run_one(
                a.output,mode,paper=a.paper_jar,plugin=a.plugin_jar,
                config_default=a.config_default,node=a.node_runtime,
                prior_sha=prior.source_sha1,mp10_revision_dev=True,
            )
            _must(port_free(),"Paper World process or port unclean")
            original=review_world(a.output/mode.lower(),mode,rc,expired)
            original_json(a.output/mode.lower()/"mp10-paper-source-audit.json",original)
            review=review_revision(a.output/mode.lower(),mode,original,prior)
            original_json(a.output/mode.lower()/"mp10-typed-revision-audit.json",review)
            worlds[mode]=original
            diagnostics[mode]=review
        match=compare_original_states(worlds["NORMAL"],worlds["ICE"])
        original_json(a.output/"MP10_PHYSICAL_PAIR_AUDIT.json",match)
        _must(match["matched"],"two new Worlds initial sampled states unmatched")
        result={
            "classification":"DEV_ORIGINAL_PAPER_TWO_WORLD_TYPED_L1_REVISION",
            "real_worlds":2,"original_s49_actions":2,
            "original_l0_unchanged":True,"learning_updates":0,
            "source_original_paper_pair_sampled_match":True,
            "model_frozen_prior_mp8":prior.source_sha1,
            "normal_revision":diagnostics["NORMAL"],
            "ice_revision":diagnostics["ICE"],
            "future_world_out_of_sample_transfer":"NOT_TESTED",
            "cheap_same_information_ols":"MATHEMATICALLY_EQUIVALENT",
            "in_sample_improvement_not_generalization":True,
            "goal":"UNDETERMINED","qualification":"NO_GO","science":"NOT_RUN",
        }
        original_json(a.output/"MP10_TWO_WORLD_DEV_RESULT.json",result)
        print("MP10_TWO_WORLD_DEV_RESULT="+json.dumps(result,sort_keys=True),flush=True)
        return 0
    except Exception as exc:
        original_json(a.output/"MP10_FAILURE_ORIGINAL.json",{
            "time":timestamp(),"error":f"{type(exc).__name__}: {exc}",
            "classification":"DEV_FAILED_NO_REVISION_QUALIFIED",
            "qualification":"NO_GO","science":"NOT_RUN",
        })
        print("MP10_DEV_FAILED="+str(exc),file=sys.stderr,flush=True)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
