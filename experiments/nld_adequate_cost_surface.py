from __future__ import annotations

import argparse
import collections
import json
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_lexical_remapping_generalization import (
    LexicalCase,
    build_cases,
    parsed_destination,
)
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
DEFAULT_MAX_NEW_TOKENS = 32


def build_cost_cases() -> tuple[LexicalCase, ...]:
    return tuple(
        case for case in build_cases() if case.family_id == "color"
    )


def build_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    observation_index = 0
    for case in build_cost_cases():
        for permutation_index, order in enumerate(MODE_PERMUTATIONS):
            for ordinal_position, mode in enumerate(order, start=1):
                schedule.append(
                    {
                        "observation_index": observation_index,
                        "case_id": case.case_id,
                        "expected_label": case.expected_label,
                        "feasible_destination": case.feasible_destination,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": ordinal_position,
                        "mode": mode,
                    }
                )
                observation_index += 1
    return schedule


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


def first_event_index(
    events: list[dict[str, object]],
    *,
    source: str | None = None,
    require_label: bool = False,
) -> int | None:
    for event in events:
        if source is not None and event.get("parse_source") != source:
            continue
        if require_label and event.get("parsed_label") is None:
            continue
        value = event.get("token_index_1based")
        if isinstance(value, int):
            return value
    return None


def _count_values(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        value = row.get(key)
        counts[str(value) if value is not None else "INVALID"] += 1
    return dict(sorted(counts.items()))


def summarize(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    by_case: dict[str, object] = {}
    for case in build_cost_cases():
        case_rows = [
            row for row in observations if row.get("case_id") == case.case_id
        ]
        modes: dict[str, object] = {}
        for mode in DEFAULT_MODES:
            rows = [row for row in case_rows if row.get("mode") == mode]
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
                        if isinstance(row.get("elapsed_seconds"), (int, float))
                    ),
                }
            modes[mode] = {
                "count": len(rows),
                "correct_count": sum(
                    row.get("decision_correct") is True for row in rows
                ),
                "invalid_output_count": sum(
                    row.get("parsed_label") is None for row in rows
                ),
                "parse_sources": _count_values(rows, "parse_source"),
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
                    if isinstance(
                        row.get("generated_token_count"),
                        (int, float),
                    )
                ),
                "tokens_per_forward": _numeric_summary(
                    row["tokens_per_forward"]
                    for row in rows
                    if isinstance(row.get("tokens_per_forward"), (int, float))
                ),
                "first_label_token_index": _numeric_summary(
                    row["first_label_token_index"]
                    for row in rows
                    if isinstance(
                        row.get("first_label_token_index"),
                        (int, float),
                    )
                ),
                "first_explicit_token_index": _numeric_summary(
                    row["first_explicit_token_index"]
                    for row in rows
                    if isinstance(
                        row.get("first_explicit_token_index"),
                        (int, float),
                    )
                ),
                "post_explicit_tail_tokens": _numeric_summary(
                    row["post_explicit_tail_tokens"]
                    for row in rows
                    if isinstance(
                        row.get("post_explicit_tail_tokens"),
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
        by_case[case.case_id] = {
            "expected_label": case.expected_label,
            "feasible_destination": case.feasible_destination,
            "observation_count": len(case_rows),
            "modes": modes,
        }

    overall: dict[str, object] = {}
    for mode in DEFAULT_MODES:
        rows = [row for row in observations if row.get("mode") == mode]
        overall[mode] = {
            "count": len(rows),
            "correct_count": sum(
                row.get("decision_correct") is True for row in rows
            ),
            "invalid_output_count": sum(
                row.get("parsed_label") is None for row in rows
            ),
            "parse_sources": _count_values(rows, "parse_source"),
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
            "first_label_token_index": _numeric_summary(
                row["first_label_token_index"]
                for row in rows
                if isinstance(row.get("first_label_token_index"), (int, float))
            ),
            "first_explicit_token_index": _numeric_summary(
                row["first_explicit_token_index"]
                for row in rows
                if isinstance(
                    row.get("first_explicit_token_index"),
                    (int, float),
                )
            ),
            "post_explicit_tail_tokens": _numeric_summary(
                row["post_explicit_tail_tokens"]
                for row in rows
                if isinstance(
                    row.get("post_explicit_tail_tokens"),
                    (int, float),
                )
            ),
        }

    adequate = all(
        isinstance(overall.get(mode), dict)
        and overall[mode].get("count") == 24
        and overall[mode].get("correct_count") == 24
        and overall[mode].get("invalid_output_count") == 0
        for mode in DEFAULT_MODES
    )
    return {
        "by_case": by_case,
        "overall_by_mode": overall,
        "cost_comparison_eligible": adequate,
    }


def dry_run_payload(
    *,
    model_id: str,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    schedule = build_schedule()
    return {
        "evidence_class": "adequate cost surface plan only",
        "model_id": model_id,
        "cases": [asdict(case) for case in build_cost_cases()],
        "seed": seed,
        "dtype": dtype,
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "max_thinking_tokens": DEFAULT_MAX_THINKING_TOKENS,
        "warmup_modes": list(DEFAULT_MODES),
        "measured_schedule": schedule,
        "measured_observation_count": len(schedule),
        "observations_per_case_mode_cell": len(MODE_PERMUTATIONS),
        "non_claims": [
            "cost comparison is conditional on fresh matched adequacy",
            "cost dimensions remain separate; no weighted score is defined",
        ],
    }


def _run_observation(
    *,
    torch,
    model: object,
    tokenizer: object,
    prompt_ids: object,
    case: LexicalCase,
    mode: str,
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
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
            max_thinking_tokens=DEFAULT_MAX_THINKING_TOKENS,
        )
    torch.cuda.synchronize()
    elapsed_seconds = time.perf_counter() - started

    new_ids = out_ids[0, prompt_ids.shape[1] :]
    token_ids = [
        int(token_id)
        for token_id in new_ids.detach().cpu().tolist()
    ]
    generated_text = tokenizer.decode(
        token_ids,
        skip_special_tokens=True,
    )
    parsed = parse_decision(generated_text)
    events = decision_prefix_events(tokenizer, token_ids)
    first_label = first_event_index(
        events,
        require_label=True,
    )
    first_explicit = first_event_index(
        events,
        source="explicit",
    )
    post_explicit_tail = (
        len(token_ids) - first_explicit
        if first_explicit is not None
        else None
    )

    nfe_value = _nfe_value(nfe)
    tokens_per_forward = None
    if isinstance(nfe_value, (int, float)) and nfe_value > 0:
        tokens_per_forward = len(token_ids) / float(nfe_value)

    return {
        "case_id": case.case_id,
        "expected_label": case.expected_label,
        "feasible_destination": case.feasible_destination,
        "label_to_destination": case.label_to_destination,
        "mode": mode,
        "arguments": mode_arguments(
            mode,
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
            max_thinking_tokens=DEFAULT_MAX_THINKING_TOKENS,
        ),
        "elapsed_seconds": elapsed_seconds,
        "nfe": nfe_value,
        "generated_token_count": len(token_ids),
        "generated_token_ids": token_ids,
        "generated_text": generated_text,
        "tokens_per_forward": tokens_per_forward,
        "parsed_label": parsed.label,
        "parse_source": parsed.source,
        "parsed_destination": parsed_destination(case, parsed.label),
        "decision_correct": parsed.label == case.expected_label,
        "first_label_token_index": first_label,
        "first_explicit_token_index": first_explicit,
        "post_explicit_tail_tokens": post_explicit_tail,
        "cuda_peak_allocated_bytes": int(
            torch.cuda.max_memory_allocated()
        ),
    }


def run_actual(
    *,
    model_id: str,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    torch, transformers, AutoModel, AutoTokenizer = _import_runtime()
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required for NLD adequate cost surface"
        )

    before_load = _cuda_memory_snapshot(torch)
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
    )
    model = AutoModel.from_pretrained(
        model_id,
        trust_remote_code=True,
    ).to("cuda").to(_torch_dtype(torch, dtype))
    model.eval()
    torch.cuda.synchronize()
    load_elapsed_seconds = time.perf_counter() - load_started
    after_load = _cuda_memory_snapshot(torch)

    required_methods = {
        "ar": "ar_generate",
        "dlm": "generate",
        "linear_spec": "linear_spec_generate",
    }
    availability = {
        mode: callable(getattr(model, method_name, None))
        for mode, method_name in required_methods.items()
    }
    missing = [
        mode
        for mode, available in availability.items()
        if not available
    ]
    if missing:
        raise RuntimeError(
            "loaded model is missing native methods: "
            + ", ".join(missing)
        )

    cases = {
        case.case_id: case for case in build_cost_cases()
    }
    prepared = {
        case_id: _prepare_prompt(tokenizer, model, case)
        for case_id, case in cases.items()
    }

    warmup = []
    warmup_case = next(iter(cases.values()))
    _, warmup_ids = prepared[warmup_case.case_id]
    for mode in DEFAULT_MODES:
        row = _run_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=warmup_ids,
            case=warmup_case,
            mode=mode,
            seed=seed,
        )
        row["warmup"] = True
        warmup.append(row)

    observations = []
    for schedule_entry in build_schedule():
        case = cases[str(schedule_entry["case_id"])]
        _, prompt_ids = prepared[case.case_id]
        row = _run_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            case=case,
            mode=str(schedule_entry["mode"]),
            seed=seed,
        )
        row.update(schedule_entry)
        row["warmup"] = False
        observations.append(row)

    return {
        "evidence_class": "actual-model adequate cost surface",
        "model_id": model_id,
        "cases": [asdict(case) for case in cases.values()],
        "seed": seed,
        "dtype": dtype,
        "device": "cuda",
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "gpu_name": torch.cuda.get_device_name(0),
        "method_availability": availability,
        "load_elapsed_seconds": load_elapsed_seconds,
        "cuda_before_load": before_load,
        "cuda_after_load": after_load,
        "warmup": warmup,
        "observations": observations,
        "summary": summarize(observations),
        "non_claims": [
            "cost comparison is conditional on fresh matched adequacy",
            "no weighted total cognition score is defined",
            "explicit textual decisions are not World truth or Action authorization",
            "this does not establish a permanent mode selector",
        ],
    }


def write_payload(
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
        description="Measure NLD cost surface under matched adequacy."
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "fp16", "fp32"),
        default=DEFAULT_DTYPE,
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        payload = (
            run_actual(
                model_id=args.model,
                seed=args.seed,
                dtype=args.dtype,
            )
            if args.run
            else dry_run_payload(
                model_id=args.model,
                seed=args.seed,
                dtype=args.dtype,
            )
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    write_payload(payload, args.output)


if __name__ == "__main__":
    main()
