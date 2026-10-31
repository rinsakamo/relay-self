"""Read-only diagnostics of failed L21 DEV originals; never repairs/adopts them.

Run with PYTHONPATH=src:tests:. This is deliberately not an admission path.
Missing closed rows, L16 failures and absent owner indexes remain failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.l16_first_action_goal_originals import (
    L16GoalPlan,
    inspect_l16_first_action_prefix,
    load_original_prefix,
)
from adapters.mineflayer.l21_goal_observer_source import (
    ORIGINAL_NAME,
    _status,
    review_l21_observer_original,
)
from relay_self.l20_external_goal_commitment import review_external_pre_world_criterion


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def diagnose(root: Path, criterion: Path, admitted_sha: str) -> dict:
    capture = root / "capture"
    received, sent, index, plan_raw = load_original_prefix(capture)
    assert sha(received) == index["received_sha256"]
    assert sha(sent) == index["sent_sha256"]
    rows = [json.loads(x) for x in received.splitlines()]
    assert [r["seq"] for r in rows] == list(range(len(rows)))
    pd = json.loads(plan_raw)
    plan = L16GoalPlan(pd["target_x"], pd["target_z"], pd["tolerance_m"],
                       pd["stable_probe_delta_max_m"])
    assert plan.original_bytes() == plan_raw
    pre = review_external_pre_world_criterion(
        original=criterion.read_bytes(), admitted_sha256=admitted_sha,
        operator_plan=plan,
    )
    terminal_raw = (capture / "l18_s16_terminal_original.jsonl").read_bytes()
    terminal = json.loads(terminal_raw)
    sid, aid = terminal["session_id"], terminal["action_id"]
    assert terminal["pre_probe_sha256"] == sha(
        received.splitlines(keepends=True)[terminal["before_seq"]])
    assert all(r["session_id"] == sid for r in rows)
    effects = [r for r in rows if r["type"] == "effect_result"]
    assert len(effects) == 2
    assert [r["action_id"] for r in effects] == [aid, aid + "-s15-clear"]
    assert all(r["result"] == "applied" for r in effects)
    probes = [r for r in rows if r.get("request_id") in
              (f"l16:{sid}:{aid}:goal-1", f"l16:{sid}:{aid}:goal-2")]
    assert len(probes) == 2
    native = [dict(entity_id=-1, **r["snapshot"]["position"]) for r in probes]
    native_status = _status(*native, plan)
    params = dict(
        received_original=received, sent_original=sent, s7_receipt=index,
        plan=plan, plan_original=plan_raw, session_id=sid, action_id=aid,
        before_seq=terminal["before_seq"], dispatch_seq=effects[0]["seq"],
        cleanup_seq=effects[1]["seq"], after_seq=terminal["after_seq"],
        first_probe_seq=probes[0]["seq"], second_probe_seq=probes[1]["seq"],
        first_probe_request_id=probes[0]["request_id"],
        second_probe_request_id=probes[1]["request_id"],
    )
    try:
        formal_l16 = asdict(inspect_l16_first_action_prefix(**params))
    except ValueError as exc:
        formal_l16 = {"rejected": str(exc)}
    raw = (root / "observer" / ORIGINAL_NAME).read_bytes()
    obs = [json.loads(x) for x in raw.splitlines()]
    samples = [r for r in obs if r["kind"] == "sample"]
    assert len(samples) == 2
    assert [r["request_id"] for r in samples] == [r["request_id"] for r in probes]
    observed_status = _status(*(r["position"] for r in samples), plan)
    try:
        formal_l21 = asdict(review_l21_observer_original(
            raw=raw, criterion_original=criterion.read_bytes(),
            criterion_sha256=admitted_sha, plan=plan, session_id=sid,
            action_id=aid, native_goal_status=native_status))
    except ValueError as exc:
        formal_l21 = {"rejected": str(exc)}
    pairs = []
    for sample, probe in zip(samples, probes, strict=True):
        a, b = sample["position"], probe["snapshot"]["position"]
        pairs.append(dict(observer=sample, s7_seq=probe["seq"], s7_position=b,
                          s7_time=probe["snapshot"].get("time"),
                          horizontal_delta_m=math.hypot(a["x"]-b["x"], a["z"]-b["z"])))
    return dict(
        classification="DEV_PARTIAL_PHYSICAL_ORIGINALS_FORMAL_ADMISSION_FAILED",
        preflight=asdict(pre), session_id=sid, action_id=aid,
        s16_original=terminal, s16_original_sha256=sha(terminal_raw),
        received_sha256=sha(received), sent_sha256=sha(sent),
        observer_sha256=sha(raw), observer_closed=obs[-1]["kind"] == "closed",
        formal_l16=formal_l16, formal_l21=formal_l21,
        diagnostic_native_goal=native_status, diagnostic_observer_goal=observed_status,
        paired_positions=pairs, new_worlds=0, new_actions=0,
        qualified_l10_pairs=0, s10_updates=0, s11_grants=0,
        independent_owner_authenticated=False, nonintervention_proven=False,
        s16_index_reconstructed=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--criterion", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(diagnose(args.run_root, args.criterion, args.sha256),
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
