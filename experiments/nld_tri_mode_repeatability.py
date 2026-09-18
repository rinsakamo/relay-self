from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from experiments.nld_tri_mode import (
    DEFAULT_MAX_NEW_TOKENS,
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
    build_probe_case,
    dispatch_generation,
    mode_arguments,
    parse_decision_label,
)

DEFAULT_PERMUTATION_REPEATS = 2
DEFAULT_DTYPE = "bf16"
MODE_PERMUTATIONS = tuple(itertools.permutations(DEFAULT_MODES))


def build_measured_schedule(
    *,
    permutation_repeats: int = DEFAULT_PERMUTATION_REPEATS,
) -> list[dict[str, object]]:
    if permutation_repeats < 1:
        raise ValueError("permutation_repeats must be positive")

    schedule: list[dict[str, object]] = []
    observation_index = 0
    for repeat_index in range(permutation_repeats):
        for permutation_index, order in enumerate(MODE_PERMUTATIONS):
            for ordinal_position, mode in enumerate(order, start=1):
                schedule.append(
                    {
                        "observation_index": observation_index,
                        "repeat_index": repeat_index,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": ordinal_position,
                        "mode": mode,
                    }
                )
                observation_index += 1
    return schedule


def _nearest_rank_percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")

    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def _numeric_summary(values: Iterable[float | int]) -> dict[str, float | int] | None:
    materialized = [value for value in values if isinstance(value, (int, float))]
    if not materialized:
        return None
    return {
        "count": len(materialized),
        "min": min(materialized),
        "median": statistics.median(materialized),
        "p95_nearest_rank": _nearest_rank_percentile(materialized, 0.95),
        "max": max(materialized),
    }


def summarize_observations(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    by_mode: dict[str, list[dict[str, object]]] = {
        mode: [] for mode in DEFAULT_MODES
    }
    for observation in observations:
        mode = observation.get("mode")
        if mode in by_mode:
            by_mode[mode].append(observation)

    summaries: dict[str, object] = {}
    for mode in DEFAULT_MODES:
        rows = by_mode[mode]
        by_position: dict[str, object] = {}
        for position in (1, 2, 3):
            position_rows = [
                row for row in rows if row.get("ordinal_position") == position
            ]
            by_position[str(position)] = {
                "count": len(position_rows),
                "latency_seconds": _numeric_summary(
                    row["elapsed_seconds"]
                    for row in position_rows
                    if isinstance(row.get("elapsed_seconds"), (int, float))
                ),
            }

        summaries[mode] = {
            "count": len(rows),
            "correct_count": sum(
                row.get("decision_correct") is True for row in rows
            ),
            "invalid_output_count": sum(
                row.get("parsed_label") is None for row in rows
            ),
            "latency_seconds": _numeric_summary(
                row["elapsed_seconds"]
                for row in rows
                if isinstance(row.get("elapsed_seconds"), (int, float))
            ),
            "nfe": _numeric_summary(
                row["nfe"]
                for row in rows
                if isinstance(row.get("nfe"), (int, float))
            ),
            "generated_token_count": _numeric_summary(
                row["generated_token_count"]
                for row in rows
                if isinstance(row.get("generated_token_count"), (int, float))
            ),
            "tokens_per_forward": _numeric_summary(
                row["tokens_per_forward"]
                for row in rows
                if isinstance(row.get("tokens_per_forward"), (int, float))
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

    return summaries


def dry_run_payload(
    *,
    model_id: str,
    permutation_repeats: int,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    schedule = build_measured_schedule(
        permutation_repeats=permutation_repeats
    )
    return {
        "evidence_class": "repeatability experiment plan only",
        "model_id": model_id,
        "case": asdict(build_probe_case()),
        "dtype": dtype,
        "seed": seed,
        "warmup_modes": list(DEFAULT_MODES),
        "permutation_repeats": permutation_repeats,
        "measured_schedule": schedule,
        "measured_observation_count": len(schedule),
        "observations_per_mode": len(schedule) // len(DEFAULT_MODES),
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
            "this plan does not establish any measured latency",
            "repeatability on one prompt is not a general model-quality ranking",
            "no adaptive RelayEngine mode policy is established",
        ],
    }


def _run_synchronized_observation(
    *,
    torch,
    model: object,
    tokenizer: object,
    prompt_ids: object,
    mode: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
) -> dict[str, object]:
    case = build_probe_case()
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
    generated_text = tokenizer.decode(new_ids, skip_special_tokens=True)
    generated_token_count = int(new_ids.numel())
    nfe_value = _nfe_value(nfe)
    tokens_per_forward = None
    if (
        isinstance(nfe_value, (int, float))
        and nfe_value > 0
    ):
        tokens_per_forward = generated_token_count / float(nfe_value)

    parsed_label = parse_decision_label(generated_text)

    return {
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
        "expected_label": case.expected_label,
        "decision_correct": parsed_label == case.expected_label,
        "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
    }


def run_actual_repeatability(
    *,
    model_id: str,
    permutation_repeats: int,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    torch, transformers, AutoModel, AutoTokenizer = _import_runtime()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the NLD repeatability gate")

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
        mode for mode, available in method_availability.items() if not available
    ]
    if missing:
        raise RuntimeError(
            "loaded model is missing required mode methods: " + ", ".join(missing)
        )

    case = build_probe_case()
    prompt_text, prompt_ids = _prepare_prompt(tokenizer, model, case)

    warmup: list[dict[str, object]] = []
    for mode in DEFAULT_MODES:
        observation = _run_synchronized_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            mode=mode,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
            seed=seed,
        )
        observation["warmup"] = True
        warmup.append(observation)

    measured_schedule = build_measured_schedule(
        permutation_repeats=permutation_repeats
    )
    observations: list[dict[str, object]] = []
    for schedule_entry in measured_schedule:
        mode = str(schedule_entry["mode"])
        observation = _run_synchronized_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            mode=mode,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
            seed=seed,
        )
        observation.update(schedule_entry)
        observation["warmup"] = False
        observations.append(observation)

    return {
        "evidence_class": "actual-model repeatability experiment",
        "model_id": model_id,
        "case": asdict(case),
        "prompt_text": prompt_text,
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
        "permutation_repeats": permutation_repeats,
        "warmup": warmup,
        "observations": observations,
        "summary_by_mode": summarize_observations(observations),
        "percentile_definition": "nearest-rank",
        "non_claims": [
            "this is one prompt with repeated physical measurements",
            "latency ordering is not a general model-quality ranking",
            "no adaptive mode selector is justified by this experiment alone",
            "internal AR verification is not World verification",
        ],
    }


def _write_payload(payload: dict[str, object], output: str | None) -> None:
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
            "Measure NLD-3B tri-mode repeatability with warm-up, "
            "CUDA synchronization, and counterbalanced execution order."
        )
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--permutation-repeats",
        type=int,
        default=DEFAULT_PERMUTATION_REPEATS,
    )
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

    if args.permutation_repeats < 1:
        parser.error("--permutation-repeats must be positive")
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    if args.max_thinking_tokens < 0:
        parser.error("--max-thinking-tokens must be non-negative")

    try:
        if args.run:
            payload = run_actual_repeatability(
                model_id=args.model,
                permutation_repeats=args.permutation_repeats,
                max_new_tokens=args.max_new_tokens,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
        else:
            payload = dry_run_payload(
                model_id=args.model,
                permutation_repeats=args.permutation_repeats,
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
