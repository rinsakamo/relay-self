from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_tri_mode import (
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_MAX_THINKING_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_MODES,
    DEFAULT_SEED,
    ProbeCase,
    _cuda_memory_snapshot,
    _import_runtime,
    _nfe_value,
    _prepare_prompt,
    _reset_seed,
    _torch_dtype,
    dispatch_generation,
    mode_arguments,
    parse_decision_label,
)
from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _numeric_summary,
)

DEFAULT_DTYPE = "bf16"


def build_matrix_cases() -> tuple[ProbeCase, ...]:
    common = """You are resolving one bounded control decision.
Choose only among labels A, B, and C.
Treat unknown information as unknown. Do not invent missing World facts.
The candidate meanings are:
A = FLEE(destination=cave)
B = FLEE(destination=ridge)
C = DEFER

"""
    return (
        ProbeCase(
            case_id="easy_separable",
            expected_label="A",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 8
Cave route open: true
Ridge route open: false
Decision label:""",
        ),
        ProbeCase(
            case_id="coupled_constraints",
            expected_label="B",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 4
Energy available: 3
Cave route open: true
Cave energy required: 7
Ridge route open: true
Ridge energy required: 2
A route is feasible only when it is open and its energy requirement does not
exceed energy available.
Decision label:""",
        ),
        ProbeCase(
            case_id="incomplete_focus",
            expected_label="C",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 8
Cave route open: UNKNOWN
Ridge route open: false
If no destination is grounded as feasible from the supplied evidence,
choose DEFER.
Decision label:""",
        ),
    )


def build_matrix_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    observation_index = 0

    for case in build_matrix_cases():
        for permutation_index, order in enumerate(MODE_PERMUTATIONS):
            for ordinal_position, mode in enumerate(order, start=1):
                schedule.append(
                    {
                        "observation_index": observation_index,
                        "case_id": case.case_id,
                        "expected_label": case.expected_label,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": ordinal_position,
                        "mode": mode,
                    }
                )
                observation_index += 1

    return schedule


def _label_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        label = row.get("parsed_label")
        if isinstance(label, str):
            counts[label] += 1
        else:
            counts["INVALID"] += 1
    return dict(sorted(counts.items()))


def summarize_matrix(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    cases = build_matrix_cases()
    summary: dict[str, object] = {}

    for case in cases:
        case_rows = [
            row
            for row in observations
            if row.get("case_id") == case.case_id
        ]
        mode_summary: dict[str, object] = {}

        for mode in DEFAULT_MODES:
            rows = [
                row for row in case_rows if row.get("mode") == mode
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
                    row.get("decision_correct") is True
                    for row in rows
                ),
                "invalid_output_count": sum(
                    row.get("parsed_label") is None for row in rows
                ),
                "observed_labels": _label_counts(rows),
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

        summary[case.case_id] = {
            "expected_label": case.expected_label,
            "observation_count": len(case_rows),
            "modes": mode_summary,
        }

    return summary


def dry_run_payload(
    *,
    model_id: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    schedule = build_matrix_schedule()
    return {
        "evidence_class": "bounded difficulty matrix plan only",
        "model_id": model_id,
        "cases": [asdict(case) for case in build_matrix_cases()],
        "dtype": dtype,
        "seed": seed,
        "warmup_modes": list(DEFAULT_MODES),
        "measured_schedule": schedule,
        "measured_observation_count": len(schedule),
        "observations_per_case_mode_cell": len(MODE_PERMUTATIONS),
        "mode_arguments": {
            mode: mode_arguments(
                mode,
                max_new_tokens=max_new_tokens,
                max_thinking_tokens=max_thinking_tokens,
            )
            for mode in DEFAULT_MODES
        },
        "timing_protocol": [
            "reset configured seed",
            "reset CUDA peak-memory stats",
            "torch.cuda.synchronize() before monotonic timer",
            "run native generation including full output path",
            "torch.cuda.synchronize() before stopping monotonic timer",
        ],
        "runtime": {
            "loader": "transformers.AutoModel/AutoTokenizer",
            "trust_remote_code": True,
            "same_loaded_model": True,
            "lora": False,
            "quantization": None,
            "serving_framework": None,
        },
        "non_claims": [
            "this is a bounded A/B/C decision matrix",
            "max_thinking_tokens is not treated as a validated cognition-depth budget",
            "this is not a long-form throughput benchmark",
            "no adaptive mode selector is established",
        ],
    }


def _run_case_mode_observation(
    *,
    torch,
    model: object,
    tokenizer: object,
    prompt_ids: object,
    case: ProbeCase,
    mode: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
) -> dict[str, object]:
    _reset_seed(torch, seed)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

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
    generated_text = tokenizer.decode(
        new_ids,
        skip_special_tokens=True,
    )
    generated_token_count = int(new_ids.numel())
    nfe_value = _nfe_value(nfe)
    tokens_per_forward = None
    if isinstance(nfe_value, (int, float)) and nfe_value > 0:
        tokens_per_forward = generated_token_count / float(nfe_value)

    parsed_label = parse_decision_label(generated_text)

    return {
        "case_id": case.case_id,
        "expected_label": case.expected_label,
        "mode": mode,
        "arguments": mode_arguments(
            mode,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
        ),
        "elapsed_seconds": elapsed_seconds,
        "nfe": nfe_value,
        "tokens_per_forward": tokens_per_forward,
        "generated_token_count": generated_token_count,
        "generated_text": generated_text,
        "parsed_label": parsed_label,
        "decision_correct": parsed_label == case.expected_label,
        "cuda_peak_allocated_bytes": int(
            torch.cuda.max_memory_allocated()
        ),
    }


def run_actual_matrix(
    *,
    model_id: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    torch, transformers, AutoModel, AutoTokenizer = _import_runtime()
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required for the NLD bounded difficulty matrix"
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
        case.case_id: case for case in build_matrix_cases()
    }
    prepared: dict[str, tuple[str, object]] = {}
    for case in cases.values():
        prepared[case.case_id] = _prepare_prompt(
            tokenizer,
            model,
            case,
        )

    warmup: list[dict[str, object]] = []
    warmup_case = cases["easy_separable"]
    _, warmup_ids = prepared[warmup_case.case_id]
    for mode in DEFAULT_MODES:
        observation = _run_case_mode_observation(
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
    for schedule_entry in build_matrix_schedule():
        case_id = str(schedule_entry["case_id"])
        mode = str(schedule_entry["mode"])
        case = cases[case_id]
        _, prompt_ids = prepared[case_id]

        observation = _run_case_mode_observation(
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
        "evidence_class": "actual-model bounded difficulty matrix",
        "model_id": model_id,
        "cases": [asdict(case) for case in cases.values()],
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
        "summary_by_case": summarize_matrix(observations),
        "non_claims": [
            "this is a bounded A/B/C decision matrix",
            "case structure is not a validated scalar difficulty scale",
            "max_thinking_tokens is not treated as a validated cognition-depth budget",
            "no adaptive mode selector is justified by this experiment alone",
            "internal AR verification is not World verification",
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
            "Run the first NLD-3B bounded problem-structure "
            "by native-mode matrix."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MAX_NEW_TOKENS,
    )
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

    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    if args.max_thinking_tokens < 0:
        parser.error("--max-thinking-tokens must be non-negative")

    try:
        if args.run:
            payload = run_actual_matrix(
                model_id=args.model,
                max_new_tokens=args.max_new_tokens,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
        else:
            payload = dry_run_payload(
                model_id=args.model,
                max_new_tokens=args.max_new_tokens,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    _write_payload(payload, args.output)


if __name__ == "__main__":
    main()
