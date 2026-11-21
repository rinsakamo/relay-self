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
DEFAULT_MAX_NEW_TOKENS = 32


@dataclass(frozen=True, slots=True)
class LexicalFamily:
    family_id: str
    entity1: str
    entity2: str


@dataclass(frozen=True, slots=True)
class LexicalCase:
    case_id: str
    family_id: str
    prompt: str
    expected_label: str
    label_to_destination: dict[str, str]
    entity1: str
    entity2: str
    entity1_open: bool
    entity2_open: bool
    feasible_destination: str


FAMILIES = (
    LexicalFamily("route", "cave", "ridge"),
    LexicalFamily("color", "amber", "cobalt"),
    LexicalFamily("code", "item-17", "item-42"),
)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _build_case(
    *,
    family: LexicalFamily,
    a_destination: str,
    b_destination: str,
    entity1_open: bool,
    entity2_open: bool,
) -> LexicalCase:
    open_destinations = [
        destination
        for destination, is_open in (
            (family.entity1, entity1_open),
            (family.entity2, entity2_open),
        )
        if is_open
    ]
    if len(open_destinations) != 1:
        raise ValueError("exactly one route must be open")

    feasible = open_destinations[0]
    mapping = {
        "A": a_destination,
        "B": b_destination,
        "C": "DEFER",
    }
    expected = [
        label
        for label, destination in mapping.items()
        if destination == feasible
    ]
    if len(expected) != 1:
        raise ValueError("feasible destination must map to one label")

    case_id = (
        f"{family.family_id}__"
        f"{'entity1' if entity1_open else 'entity2'}_open__"
        f"a_{'entity1' if a_destination == family.entity1 else 'entity2'}"
    )
    prompt = f"""You are resolving one bounded control decision.
Choose only among labels A, B, and C.
Use only the supplied route evidence.
The candidate meanings are:
A = FLEE(destination={a_destination})
B = FLEE(destination={b_destination})
C = DEFER

Current Intent: reach safety
Threat nearby: true
Health: 8
{family.entity1} route open: {_bool_text(entity1_open)}
{family.entity2} route open: {_bool_text(entity2_open)}
A destination is feasible only when its route is explicitly open.
Decision label:"""

    return LexicalCase(
        case_id=case_id,
        family_id=family.family_id,
        prompt=prompt,
        expected_label=expected[0],
        label_to_destination=mapping,
        entity1=family.entity1,
        entity2=family.entity2,
        entity1_open=entity1_open,
        entity2_open=entity2_open,
        feasible_destination=feasible,
    )


def build_cases() -> tuple[LexicalCase, ...]:
    cases: list[LexicalCase] = []
    for family in FAMILIES:
        cases.extend(
            [
                _build_case(
                    family=family,
                    a_destination=family.entity1,
                    b_destination=family.entity2,
                    entity1_open=True,
                    entity2_open=False,
                ),
                _build_case(
                    family=family,
                    a_destination=family.entity2,
                    b_destination=family.entity1,
                    entity1_open=True,
                    entity2_open=False,
                ),
                _build_case(
                    family=family,
                    a_destination=family.entity1,
                    b_destination=family.entity2,
                    entity1_open=False,
                    entity2_open=True,
                ),
                _build_case(
                    family=family,
                    a_destination=family.entity2,
                    b_destination=family.entity1,
                    entity1_open=False,
                    entity2_open=True,
                ),
            ]
        )
    return tuple(cases)


def build_schedule() -> list[dict[str, object]]:
    schedule: list[dict[str, object]] = []
    index = 0
    for case in build_cases():
        for permutation_index, order in enumerate(MODE_PERMUTATIONS):
            for ordinal_position, mode in enumerate(order, start=1):
                schedule.append(
                    {
                        "observation_index": index,
                        "case_id": case.case_id,
                        "family_id": case.family_id,
                        "expected_label": case.expected_label,
                        "feasible_destination": case.feasible_destination,
                        "permutation_index": permutation_index,
                        "order": list(order),
                        "ordinal_position": ordinal_position,
                        "mode": mode,
                    }
                )
                index += 1
    return schedule


def parsed_destination(
    case: LexicalCase,
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
        counts[str(value) if value is not None else "INVALID"] += 1
    return dict(sorted(counts.items()))


def summarize(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    by_case: dict[str, object] = {}
    cases = {case.case_id: case for case in build_cases()}

    for case_id, case in cases.items():
        case_rows = [
            row for row in observations if row.get("case_id") == case_id
        ]
        mode_summaries: dict[str, object] = {}
        for mode in DEFAULT_MODES:
            rows = [row for row in case_rows if row.get("mode") == mode]
            mode_summaries[mode] = {
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
            }
        by_case[case_id] = {
            "family_id": case.family_id,
            "expected_label": case.expected_label,
            "feasible_destination": case.feasible_destination,
            "label_to_destination": case.label_to_destination,
            "observation_count": len(case_rows),
            "modes": mode_summaries,
        }

    by_family: dict[str, object] = {}
    for family in FAMILIES:
        rows = [
            row
            for row in observations
            if row.get("family_id") == family.family_id
        ]
        by_family[family.family_id] = {
            mode: {
                "count": len(
                    mode_rows := [
                        row for row in rows if row.get("mode") == mode
                    ]
                ),
                "correct_count": sum(
                    row.get("decision_correct") is True
                    for row in mode_rows
                ),
                "invalid_output_count": sum(
                    row.get("parsed_label") is None for row in mode_rows
                ),
            }
            for mode in DEFAULT_MODES
        }

    overall = {}
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
        }

    return {
        "by_case": by_case,
        "by_family": by_family,
        "overall_by_mode": overall,
    }


def entity_tokenization(
    tokenizer: object,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for family in FAMILIES:
        result[family.family_id] = {
            family.entity1: tokenizer.encode(
                family.entity1,
                add_special_tokens=False,
            ),
            family.entity2: tokenizer.encode(
                family.entity2,
                add_special_tokens=False,
            ),
        }
    return result


def dry_run_payload(
    *,
    model_id: str,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    schedule = build_schedule()
    return {
        "evidence_class": "lexical remapping generalization plan only",
        "model_id": model_id,
        "families": [asdict(family) for family in FAMILIES],
        "cases": [asdict(case) for case in build_cases()],
        "seed": seed,
        "dtype": dtype,
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "max_thinking_tokens": DEFAULT_MAX_THINKING_TOKENS,
        "warmup_modes": list(DEFAULT_MODES),
        "measured_schedule": schedule,
        "measured_observation_count": len(schedule),
        "observations_per_case_mode_cell": len(MODE_PERMUTATIONS),
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
    elapsed = time.perf_counter() - started

    new_ids = out_ids[0, prompt_ids.shape[1] :]
    generated_ids = [
        int(token_id)
        for token_id in new_ids.detach().cpu().tolist()
    ]
    generated_text = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    )
    parsed = parse_decision(generated_text)
    nfe_value = _nfe_value(nfe)
    token_count = len(generated_ids)
    tokens_per_forward = None
    if isinstance(nfe_value, (int, float)) and nfe_value > 0:
        tokens_per_forward = token_count / float(nfe_value)

    return {
        "case_id": case.case_id,
        "family_id": case.family_id,
        "expected_label": case.expected_label,
        "feasible_destination": case.feasible_destination,
        "label_to_destination": case.label_to_destination,
        "entity1": case.entity1,
        "entity2": case.entity2,
        "entity1_open": case.entity1_open,
        "entity2_open": case.entity2_open,
        "mode": mode,
        "arguments": mode_arguments(
            mode,
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
            max_thinking_tokens=DEFAULT_MAX_THINKING_TOKENS,
        ),
        "elapsed_seconds": elapsed,
        "nfe": nfe_value,
        "generated_token_count": token_count,
        "generated_token_ids": generated_ids,
        "generated_text": generated_text,
        "tokens_per_forward": tokens_per_forward,
        "parsed_label": parsed.label,
        "parse_source": parsed.source,
        "parsed_destination": parsed_destination(case, parsed.label),
        "decision_correct": parsed.label == case.expected_label,
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
            "CUDA is required for NLD lexical generalization"
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
    load_elapsed = time.perf_counter() - load_started
    after_load = _cuda_memory_snapshot(torch)

    required_methods = {
        "ar": "ar_generate",
        "dlm": "generate",
        "linear_spec": "linear_spec_generate",
    }
    availability = {
        mode: callable(getattr(model, name, None))
        for mode, name in required_methods.items()
    }
    missing = [
        mode for mode, available in availability.items() if not available
    ]
    if missing:
        raise RuntimeError(
            "missing native methods: " + ", ".join(missing)
        )

    cases = {case.case_id: case for case in build_cases()}
    prepared = {
        case_id: _prepare_prompt(tokenizer, model, case)
        for case_id, case in cases.items()
    }

    warmup = []
    warmup_case = cases["route__entity1_open__a_entity1"]
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
    for schedule in build_schedule():
        case = cases[str(schedule["case_id"])]
        _, prompt_ids = prepared[case.case_id]
        row = _run_observation(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            case=case,
            mode=str(schedule["mode"]),
            seed=seed,
        )
        row.update(schedule)
        row["warmup"] = False
        observations.append(row)

    return {
        "evidence_class": "actual-model lexical remapping generalization",
        "model_id": model_id,
        "families": [asdict(family) for family in FAMILIES],
        "cases": [asdict(case) for case in cases.values()],
        "seed": seed,
        "dtype": dtype,
        "device": "cuda",
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "gpu_name": torch.cuda.get_device_name(0),
        "method_availability": availability,
        "entity_tokenization": entity_tokenization(tokenizer),
        "load_elapsed_seconds": load_elapsed,
        "cuda_before_load": before_load,
        "cuda_after_load": after_load,
        "warmup": warmup,
        "observations": observations,
        "summary": summarize(observations),
        "non_claims": [
            "this tests lexical generalization within one checkpoint",
            "aggregate correctness is not a product ranking",
            "this does not establish hidden causal mechanism",
            "this does not establish cross-model generalization",
        ],
    }


def write_payload(
    payload: dict[str, object],
    output: str | None,
) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output is None:
        print(text)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run NLD lexical remapping generalization."
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
