"""Opt-in real llama.cpp SystemOne benchmark for #828 §27 minimal DEV.

No Minecraft or Action issuance. Requires explicit local real-LLM grant.
Run from repo root with PYTHONPATH=src:. python -m experiments.cognitive_minimal_l1_benchmark ...
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.cognitive_minimal_dev import (
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import RelayEngine

SKILLS = frozenset({("EAT", 1), ("ATTACK", 1), ("MOVE", 1), ("REST", 1)})


def _p95(values: list[int]) -> int:
    return sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)]


def _summary(values: list[int]) -> dict[str, int | float]:
    return {"n": len(values), "p50_ns": statistics.median(values),
            "p95_ns": _p95(values), "max_ns": max(values)}


def _percept(case: str, seq: int) -> WorldPercept:
    provenance = Provenance("benchmark-synthetic", f"case:{case}:seq:{seq}")
    session = "benchmark-world-1"
    targets = []
    if case in ("D1", "D2"):
        targets.append(Target("synthetic-apple-1", "FOOD", provenance, session, seq))
    if case == "D2":
        targets.append(Target("synthetic-zombie-1", "ZOMBIE", provenance, session, seq))
    return WorldPercept(ScopeRef("benchmark-self-1", session), provenance,
                        seq, 10, False, tuple(targets))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant-real-llm", action="store_true",
                        help="explicit operator approval for live model calls")
    parser.add_argument("--endpoint", required=True, help="local chat completions endpoint")
    parser.add_argument("--systemone-endpoint", default=None,
                        help="explicit Jev /v1/systemone endpoint (optional)")
    parser.add_argument("--model", required=True, help="served llama.cpp model name")
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=2)
    args = parser.parse_args()
    if not args.grant_real_llm:
        parser.error("--grant-real-llm is required; no implicit local model access")
    if args.repeats < 1 or args.warmup < 0:
        parser.error("--repeats must be positive and --warmup nonnegative")

    provider = LlamaCppRelayProvider(
        endpoint=args.endpoint,
        systemone_endpoint=args.systemone_endpoint,
        model=args.model,
    )
    engine = RelayEngine(provider)
    registry = initial_patterns()
    report: dict[str, object] = {
        "evidence_class": "REAL_LLM_SYNTHETIC_WORLD_DEV_ONLY",
        "backend": "JEV" if args.systemone_endpoint else "GENERATED_BOUNDED",
        "model": args.model,
        "endpoint": args.endpoint,
        "server_model_load_included": False,
        "world_body_outcome": "NOT_RUN",
        "cases": {},
    }
    for case in ("D1", "D2", "D3"):
        elapsed_ns: list[int] = []
        cpu_ns: list[int] = []
        prompt_tokens: list[int] = []
        completions: list[int] = []
        accepted = 0
        chosen_ids: list[str | None] = []
        errors: list[str] = []
        for i in range(args.warmup + args.repeats):
            p = _percept(case, i)
            owner = IntentCommitment()
            epoch = cpu_schema_epoch(p, registry, allowed_skills=SKILLS, epoch=i)
            round_ = assemble_l1_select(epoch, intent_owner=owner)
            started = time.perf_counter_ns()
            try:
                result = engine(round_.request)
                duration = time.perf_counter_ns() - started
                receipt = resolve_l1_choice(
                    round_, result, current_frame=epoch,
                    intent_owner=owner, available_skills=SKILLS,
                )
                choice = None if result.choice_id is None else dict(round_.numbered).get(
                    result.choice_id
                )
                correct = (
                    case == "D1" and receipt.status == "READY"
                    and receipt.option is not None and receipt.option.skill_id == "EAT"
                ) or (
                    case == "D2" and receipt.status == "READY"
                    and receipt.option is not None
                    and receipt.option.skill_id in ("ATTACK", "EAT")
                ) or (
                    case == "D3" and receipt.status == "ESCALATE_L2"
                )
                if i >= args.warmup:
                    elapsed_ns.append(duration)
                    cpu_ns.append(epoch.elapsed_ns)
                    accepted += int(correct)
                    chosen_ids.append(result.choice_id)
                    if result.observed_prompt_tokens is not None:
                        prompt_tokens.append(result.observed_prompt_tokens)
                    if result.observed_completion_tokens is not None:
                        completions.append(result.observed_completion_tokens)
            except Exception as exc:
                if i >= args.warmup:
                    errors.append(f"{type(exc).__name__}:{str(exc)[:180]}")
                    chosen_ids.append(None)
            # Never issue native Action; model output remains a candidate only.
        if not elapsed_ns:
            report["cases"][case] = {
                "status": "NO_VALID_CALL", "errors": errors,
            }
        else:
            report["cases"][case] = {
                "selection_accepted_rate": accepted / args.repeats,
                "successful_provider_calls": len(elapsed_ns),
                "failed_provider_calls": len(errors),
                "elapsed": _summary(elapsed_ns),
                "schema_cpu": _summary(cpu_ns),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completions,
                "choice_ids": chosen_ids,
                "errors": errors,
            }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
