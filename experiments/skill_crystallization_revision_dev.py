"""One-shot revision of a saved DEV mock skill after observed failures."""

import argparse
import json
from pathlib import Path

from experiments.skill_crystallization_dev import (
    ModelCallFailure,
    WorldTrial,
    applicable,
    cue_for,
    gemma_l2,
    make_trials,
    run_baseline,
    run_skill,
    validate_skill,
)


def shifted(seed, surface):
    # Use the existing shifted-motion generator; keep cue and physics separate.
    return [WorldTrial(surface, t.start, t.effects, t.session)
            for t in make_trials(seed, 128, phase=f"revision-{seed}", shift=True)]


def failures(old, trials, prior):
    rows = list(prior)
    seen = {row["source_session"] for row in rows}
    for t in trials:
        if t.session in seen or not applicable(old, cue_for(t), t):
            continue
        result = run_skill(old, t, cue_for(t))
        rows.append({"experience_id": f"shift-experience-{len(rows):03}",
                     "source_session": t.session, "surface_cue": t.surface,
                     "start_distance": round(t.start, 6), "observed_action": "MOVE_AWAY",
                     "observed_trace": result["trace"], "outcome_success": result["success"],
                     "target_distance": old["target_distance"]})
        if len(rows) >= 2 and not any(x["outcome_success"] for x in rows[-2:]):
            break
        if len(rows) >= 16:
            break
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    first = json.loads(args.first.read_text())
    old = validate_skill(first["candidate_raw"], {x["experience_id"] for x in first["training"]})
    prior = json.loads(args.prior.read_text())["shift_observations"]
    observations = failures(old, shifted(20261111, old["surface"]), prior)
    report = {"old_skill": old, "shift_observations": observations, "suspended": False,
              "rollback": "old skill remains suspended; fixed L0 fallback", "provider_record": None,
              "new_skill": None, "validator_error": None, "evaluation": None}
    if len(observations) < 2 or any(x["outcome_success"] for x in observations[-2:]):
        report["validator_error"] = "TWO_CONSECUTIVE_FAILURES_NOT_OBSERVED"
    else:
        report["suspended"] = True
        training = first["training"] + observations
        try:
            candidate, record = gemma_l2(
                training, endpoint=args.endpoint, model=args.model, timeout=300,
                revision_context={"old_skill": old, "failure_reason": (
                    "Two consecutive observed attempts failed to reach target; "
                    "old skill suspended. Propose a revised skill based on the observations.")})
            report["provider_record"] = record
            report["new_skill"] = candidate
            try:
                spec = validate_skill(candidate, {x["experience_id"] for x in training})
                counts = {"n": 0, "selected": 0, "success": 0, "actions": 0,
                          "baseline_success": 0, "baseline_actions": 0}
                for t in shifted(20261112, old["surface"])[:16]:
                    selected = applicable(spec, cue_for(t), t)
                    base = run_baseline(t)
                    out = run_skill(spec, t, cue_for(t)) if selected else base
                    counts["n"] += 1
                    counts["selected"] += int(selected)
                    counts["success"] += int(out["success"])
                    counts["actions"] += out["action_count"]
                    counts["baseline_success"] += int(base["success"])
                    counts["baseline_actions"] += base["action_count"]
                report["evaluation"] = counts
            except ValueError as exc:
                report["validator_error"] = str(exc)
        except ModelCallFailure as exc:
            report["provider_record"] = exc.record
            report["validator_error"] = str(exc)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
