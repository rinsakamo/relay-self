from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.nld_tri_mode import (
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_MODES,
    DEFAULT_SEED,
    _cuda_memory_snapshot,
    _import_runtime,
    _nfe_value,
    _prepare_prompt,
    _reset_seed,
    _torch_dtype,
    dispatch_generation,
    mode_arguments,
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _numeric_summary,
)

DEFAULT_DTYPE = "bf16"
TOKEN_BUDGETS = (32, 64)


@dataclass(frozen=True, slots=True)
class BudgetCase:
    case_id: str
    prompt: str
    expected_label: str
    feasible_destination: str
    label_to_destination: dict[str, str]
    cave_open: bool
    ridge_open: bool


def build_budget_cases() -> tuple[BudgetCase, ...]:
    mapping = {
        "A": "ridge",
        "B": "cave",
        "C": "DEFER",
    }
    common = """You are resolving one bounded control decision.
Choose only among labels A, B, and C.
Use only the supplied route evidence.
The candidate meanings are:
A = FLEE(destination=ridge)
B = FLEE(destination=cave)
C = DEFER

Current Intent: reach safety
Threat nearby: true
Health: 8
"""

    return (
        BudgetCase(
            case_id="reversed_cave_open",
            expected_label="B",
            feasible_destination="cave",
            label_to_destination=mapping,
            cave_open=True,
            ridge_open=False,
            prompt=common
            + """Cave route open: true
Ridge route open: false
A destination is feasible only when its route is explicitly open.
Decision label:""",
        ),
        BudgetCase(
            case_id="reversed_ridge_open",
            expected_label="A",
            feasible_destination="ridge",
            label_to_destination=mapping,
            cave_open=False,
            ridge_open=True,
            prompt=common
            + """Cave route open: false
Ridge route open: true
A destination is feasible only when its route is explicitly open.
Decision label:""",
        ),
    )


def build_budget_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    observation_index = 0

    for case in build_budget_cases():
        for max_new_tokens in TOKEN_BUDGETS:
            for permutation_index, order in enumerate(MODE_PERMUTATIONS):
                for ordinal_position, mode in enumerate(order, start=1):
                    schedule.append(
                        {
                            "observation_index": observation_index,
                            "case_id": case.case_id,
                            "expected_label": case.expected_label,
                            "feasible_destination": case.feasible_destination,
                            "max_new_tokens": max_new_tokens,
                            "permutation_index": permutation_index,
                            "order": list(order),
                            "ordinal_position": ordinal_position,
                            "mode": mode,
                        }
                    )
                    observation_index += 1

    return schedule


def parsed_destination(
    case: BudgetCase,
    label: str | None,
) -> str:
    if label is None:
        return "INVALID"
    return case.label_to_destination.get(label, "INVALID")


def _count_values(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        value = row.get(key)
        if isinstance(value, str):
            counts[value] += 1
        elif isinstance(value, bool):
            counts[str(value).lower()] += 1
        else:
            counts["INVALID"] += 1
    return dict(sorted(counts.items()))


def summarize_budget_isolation(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    summary: dict[str, object] = {}

    for case in build_budget_cases():
        budget_summary: dict[str, object] = {}
        for max_new_tokens in TOKEN_BUDGETS:
            subject_rows = [
                row
                for row in observations
                if row.get("case_id") == case.case_id
                and row.get("max_new_tokens") == max_new_tokens
            ]
            mode_summary: dict[str, object] = {}

            for mode in DEFAULT_MODES:
                rows = [
                    row for row in subject_rows if row.get("mode") == mode
                ]
                by_position: dict[str, object] = {}
                for position in (1, 2, 3):
                    position_rows = [
                        row
                        for row in rows
                        if row.get("ordinal_position") == position
                    ]
                    by_position[str(position)] = {
                        "count": len(position_rows),
                        "latency_seconds": _numeric_summary(
                            row["elapsed_seconds"]
                            for row in position_rows
                            if isinstance(
                                row.get("elapsed_seconds"),
                                (int, float),
                            )
                        ),
                    }

                mode_summary[mode] = {
                    "count": len(rows),
                    "correct_count": sum(
                        row.get("decision_correct") is True for row in rows
                    ),
                    "invalid_output_count": sum(
                        row.get("parsed_label") is None for row in rows
                    ),
                    "observed_labels": _count_values(rows, "parsed_label"),
                    "observed_destinations": _count_values(
                        rows,
                        "parsed_destination",
                    ),
                    "parse_sources": _count_values(rows, "parse_source"),
                    "explicit_labels": _count_values(
                        rows,
                        "explicit_label",
                    ),
                    "fallback_labels": _count_values(
                        rows,
                        "fallback_label",
                    ),
                    "eos_reached": _count_values(rows, "eos_reached"),
                    "token_cap_proxy": _count_values(
                        rows,
                        "reached_or_exceeded_effective_max_new_tokens",
                    ),
                    "latency_seconds": _numeric_summary(
                        row["elapsed_seconds"]
                        for row in rows
                        if isinstance(
                            row.get("elapsed_seconds"),
                            (int, float),
                        )
                    ),
                    "nfe": _numeric_summary(
                        row["nfe"]
                        for row in rows
                        if isinstance(row.get("nfe"), (int, float))
                    ),
                    "generated_token_count": _numeric_summary(
                        row["generated_token_count"]
                        for row in rows
                        if isinstance(
                            row.get("generated_token_count"),
                            (int, float),
                        )
                    ),
                    "tokens_per_forward": _numeric_summary(
                        row["tokens_per_forward"]
                        for row in rows
                        if isinstance(
                            row.get("tokens_per_forward"),
                            (int, float),
                        )
                    ),
                    "cuda_peak_allocated_bytes": _numeric_summary(
                        row["cuda_peak_allocated_bytes"]
                        for row in rows
                        if isinstance(
                            row.get("cuda_peak_allocated_bytes"),
                            (int, float),
                        )
                    ),
                    "latency_by_ordinal_position": by_position,
                }

            budget_summary[str(max_new_tokens)] = {
                "observation_count": len(subject_rows),
                "modes": mode_summary,
            }

        summary[case.case_id] = {
            "expected_label": case.expected_label,
            "feasible_destination": case.feasible_destination,
            "label_to_destination": case.label_to_destination,
            "route_evidence": {
                "cave_open": case.cave_open,
                "ridge_open": case.ridge_open,
            },
            "budgets": budget_summary,
        }

    return summary


def dry_run_payload(
    *,
    model_id: str,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    schedule = build_budget_schedule()
    return {
        "evidence_class": "reversed mapping token-budget plan only",
        "model_id": model_id,
        "cases": [asdict(case) for case in build_budget_cases()],
        "token_budgets": list(TOKEN_BUDGETS),
        "dtype": dtype,
        "seed": seed,
        "warmup_subjects": [
            {
                "mode": mode,
                "max_new_tokens": max_new_tokens,
            }
            for max_new_tokens in TOKEN_BUDGETS
            for mode in DEFAULT_MODES
        ],
        "measured_schedule": schedule,
        "measured_observation_count": len(schedule),
        "observations_per_case_budget_mode_cell": len(MODE_PERMUTATIONS),
        "timing_protocol": [
            "reset configured seed",
            "reset CUDA peak-memory stats",
            "torch.cuda.synchronize() before monotonic timer",
            "run native generation including full output path",
            "torch.cuda.synchronize() before stopping monotonic timer",
        ],
        "non_claims": [
            "max_new_tokens is an output-generation control, not semantic cognition depth",
            "max_thinking_tokens remains an unqualified native call argument",
            "this gate does not measure general long-form throughput",
            "no adaptive mode policy is established",
        ],
    }



def decision_prefix_events(
    tokenizer: object,
    token_ids: list[int],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index in range(1, len(token_ids) + 1):
        text = tokenizer.decode(
            token_ids[:index],
            skip_special_tokens=True,
        )
        parsed = parse_decision(text)
        events.append(
            {
                "token_index_1based": index,
                "parsed_label": parsed.label,
                "parse_source": parsed.source,
                "explicit_label": parsed.explicit_label,
                "fallback_label": parsed.fallback_label,
            }
        )
    return events



def _run_observation(
    *,
    torch,
    model: object,
    tokenizer: object,
    prompt_ids: object,
    case: BudgetCase,
    mode: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
) -> dict[str, object]:
    _reset_seed(torch, seed)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    arguments = mode_arguments(
        mode,
        max_new_tokens=max_new_tokens,
        max_thinking_tokens=max_thinking_tokens,
    )

    started = time.perf_counter()
    with torch.inference_mode():
        out_ids, nfe = dispatch_generation(
            model,
            tokenizer,
            prompt_ids,
            mode=mode,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
        )
    torch.cuda.synchronize()
    elapsed_seconds = time.perf_counter() - started

    new_ids = out_ids[0, prompt_ids.shape[1] :]
    generated_text = tokenizer.decode(new_ids, skip_special_tokens=True)
    generated_token_ids = [
        int(token_id) for token_id in new_ids.detach().cpu().tolist()
    ]
    generated_token_count = len(generated_token_ids)

    nfe_value = _nfe_value(nfe)
    tokens_per_forward = None
    if isinstance(nfe_value, (int, float)) and nfe_value > 0:
        tokens_per_forward = generated_token_count / float(nfe_value)

    parsed = parse_decision(generated_text)
    destination = parsed_destination(case, parsed.label)
    eos_token_id = tokenizer.eos_token_id
    eos_reached = (
        eos_token_id is not None
        and int(eos_token_id) in generated_token_ids
    )
    effective_max_new_tokens = int(arguments["max_new_tokens"])

    return {
        "case_id": case.case_id,
        "expected_label": case.expected_label,
        "feasible_destination": case.feasible_destination,
        "label_to_destination": case.label_to_destination,
        "route_evidence": {
            "cave_open": case.cave_open,
            "ridge_open": case.ridge_open,
        },
        "mode": mode,
        "arguments": arguments,
        "requested_max_new_tokens": max_new_tokens,
        "effective_max_new_tokens": effective_max_new_tokens,
        "elapsed_seconds": elapsed_seconds,
        "nfe": nfe_value,
        "tokens_per_forward": tokens_per_forward,
        "generated_token_count": generated_token_count,
        "generated_text": generated_text,
        "generated_token_ids": generated_token_ids,
        "parsed_label": parsed.label,
        "parse_source": parsed.source,
        "explicit_label": parsed.explicit_label,
        "fallback_label": parsed.fallback_label,
        "parsed_destination": destination,
        "decision_correct": parsed.label == case.expected_label,
        "eos_reached": eos_reached,
        "reached_or_exceeded_effective_max_new_tokens": (
            generated_token_count >= effective_max_new_tokens
        ),
        "cuda_peak_allocated_bytes": int(
            torch.cuda.max_memory_allocated()
        ),
    }


def run_actual_budget_isolation(
    *,
    model_id: str,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    torch, transformers, AutoModel, AutoTokenizer = _import_runtime()
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required for reversed-mapping token-budget isolation"
        )

    torch_dtype = _torch_dtype(torch, dtype)
    before_load = _cuda_memory_snapshot(torch)
    load_started = time.perf_counter()

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
    )
    model = AutoModel.from_pretrained(
        model_id,
        trust_remote_code=True,
    ).to("cuda").to(torch_dtype)
    model.eval()

    torch.cuda.synchronize()
    load_elapsed_seconds = time.perf_counter() - load_started
    after_load = _cuda_memory_snapshot(torch)

    required_methods = {
        "ar": "ar_generate",
        "dlm": "generate",
        "linear_spec": "linear_spec_generate",
    }
    method_availability = {
        mode: callable(getattr(model, method_name, None))
        for mode, method_name in required_methods.items()
    }
    missing = [
        mode
        for mode, available in method_availability.items()
        if not available
    ]
    if missing:
        raise RuntimeError(
            "loaded model is missing required mode methods: "
            + ", ".join(missing)
        )

    cases = {
        case.case_id: case for case in build_budget_cases()
    }
    prepared: dict[str, tuple[str, object]] = {}
    for case in cases.values():
        prepared[case.case_id] = _prepare_prompt(
            tokenizer,
            model,
            case,
        )

    warmup: list[dict[str, object]] = []
    warmup_case = cases["reversed_cave_open"]
    _, warmup_ids = prepared[warmup_case.case_id]
    for max_new_tokens in TOKEN_BUDGETS:
        for mode in DEFAULT_MODES:
            observation = _run_observation(
                torch=torch,
                model=model,
                tokenizer=tokenizer,
                prompt_ids=warmup_ids,
                case=warmup_case,
                mode=mode,
                max_new_tokens=max_new_tokens,
                max_thinking_tokens=max_thinking_tokens,
                seed=seed,
            )
            observation["warmup"] = True
            warmup.append(observation)

    observations: list[dict[str, object]] = []
    for schedule_entry in build_budget_schedule():
        case_id = str(schedule_entry["case_id"])
        mode = str(schedule_entry["mode"])
        max_new_tokens = int(schedule_entry["max_new_tokens"])
        case = cases[case_id]
        _, prompt_ids = prepared[case_id]

        observation = _run_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            case=case,
            mode=mode,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
            seed=seed,
        )
        observation.update(schedule_entry)
        observation["warmup"] = False
        observations.append(observation)

    return {
        "evidence_class": "actual-model reversed mapping token-budget isolation",
        "model_id": model_id,
        "cases": [asdict(case) for case in cases.values()],
        "token_budgets": list(TOKEN_BUDGETS),
        "seed": seed,
        "dtype": dtype,
        "device": "cuda",
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "gpu_name": torch.cuda.get_device_name(0),
        "method_availability": method_availability,
        "load_elapsed_seconds": load_elapsed_seconds,
        "cuda_before_load": before_load,
        "cuda_after_load": after_load,
        "warmup": warmup,
        "observations": observations,
        "summary_by_case": summarize_budget_isolation(observations),
        "non_claims": [
            "this is one bounded reversed-mapping token-budget isolation",
            "max_new_tokens is not semantic cognition depth",
            "diagnostic patterns do not prove hidden internal causality",
            "no adaptive mode selector is justified by this experiment alone",
        ],
    }


def _write_payload(
    payload: dict[str, object],
    output: str | None,
) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if output is None:
        print(serialized)
        return

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run reversed-mapping NLD token-budget / termination isolation."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--max-thinking-tokens",
        type=int,
        default=DEFAULT_MAX_THINKING_TOKENS,
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "fp16", "fp32"),
        default=DEFAULT_DTYPE,
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.max_thinking_tokens < 0:
        parser.error("--max-thinking-tokens must be non-negative")

    try:
        if args.run:
            payload = run_actual_budget_isolation(
                model_id=args.model,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
        else:
            payload = dry_run_payload(
                model_id=args.model,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    _write_payload(payload, args.output)


if __name__ == "__main__":
    main()
