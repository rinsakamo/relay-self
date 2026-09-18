from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from experiments.nld_tri_mode import DEFAULT_MODES
from experiments.nld_tri_mode_repeatability import _numeric_summary

FOCUS_CASE_ID = "reversed_ridge_open"
FOCUS_MAX_NEW_TOKENS = 32


def sequence_sha256(token_ids: list[int]) -> str:
    payload = ",".join(str(value) for value in token_ids)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def first_matching_event(
    events: list[dict[str, object]],
    *,
    source: str | None = None,
    require_label: bool = False,
) -> dict[str, object] | None:
    for event in events:
        if source is not None and event.get("parse_source") != source:
            continue
        if require_label and event.get("parsed_label") is None:
            continue
        return dict(event)
    return None


def common_token_count(first: list[int], second: list[int]) -> int:
    limit = min(len(first), len(second))
    index = 0
    while index < limit and first[index] == second[index]:
        index += 1
    return index


def pairwise_divergence(
    first: dict[str, object],
    second: dict[str, object],
) -> dict[str, object]:
    first_ids = first["generated_token_ids"]
    second_ids = second["generated_token_ids"]
    count = common_token_count(first_ids, second_ids)
    return {
        "common_token_count": count,
        "first_divergence_token_index_1based": (
            count + 1
            if count < min(len(first_ids), len(second_ids))
            else None
        ),
        "first_next_token_id": (
            first_ids[count] if count < len(first_ids) else None
        ),
        "second_next_token_id": (
            second_ids[count] if count < len(second_ids) else None
        ),
        "first_next_token_text": (
            first["generated_token_texts"][count]
            if count < len(first["generated_token_texts"])
            else None
        ),
        "second_next_token_text": (
            second["generated_token_texts"][count]
            if count < len(second["generated_token_texts"])
            else None
        ),
    }


def analyze_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("input evidence must be a JSON object")
    if payload.get("evidence_class") != (
        "actual-model reversed mapping token-budget isolation"
    ):
        raise ValueError("input evidence has the wrong evidence class")

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("input observations are missing")

    focus = [
        row
        for row in observations
        if isinstance(row, dict)
        and row.get("case_id") == FOCUS_CASE_ID
        and row.get("max_new_tokens") == FOCUS_MAX_NEW_TOKENS
    ]
    if len(focus) != 18:
        raise ValueError(
            f"expected 18 focus observations; found {len(focus)}"
        )

    summary_by_mode: dict[str, object] = {}
    representative: dict[str, dict[str, object]] = {}
    for mode in DEFAULT_MODES:
        rows = [row for row in focus if row.get("mode") == mode]
        if len(rows) != 6:
            raise ValueError(
                f"expected 6 focus observations for {mode}; "
                f"found {len(rows)}"
            )

        sequence_hashes = collections.Counter()
        labels = collections.Counter()
        destinations = collections.Counter()
        first_any_indices: list[int] = []
        first_explicit_indices: list[int] = []

        for row in rows:
            token_ids = row.get("generated_token_ids")
            token_texts = row.get("generated_token_texts")
            events = row.get("decision_prefix_events")
            if not isinstance(token_ids, list):
                raise ValueError("generated_token_ids are missing")
            if not isinstance(token_texts, list):
                raise ValueError("generated_token_texts are missing")
            if not isinstance(events, list):
                raise ValueError("decision_prefix_events are missing")

            row["sequence_sha256"] = sequence_sha256(token_ids)
            first_any = first_matching_event(
                events,
                require_label=True,
            )
            first_explicit = first_matching_event(
                events,
                source="explicit",
            )
            row["first_any_decision_event"] = first_any
            row["first_explicit_decision_event"] = first_explicit

            sequence_hashes[row["sequence_sha256"]] += 1
            labels[str(row.get("parsed_label"))] += 1
            destinations[str(row.get("parsed_destination"))] += 1

            if isinstance(first_any, dict):
                first_any_indices.append(
                    int(first_any["token_index_1based"])
                )
            if isinstance(first_explicit, dict):
                first_explicit_indices.append(
                    int(first_explicit["token_index_1based"])
                )

        representative[mode] = rows[0]
        summary_by_mode[mode] = {
            "count": len(rows),
            "correct_count": sum(
                row.get("decision_correct") is True for row in rows
            ),
            "labels": dict(sorted(labels.items())),
            "destinations": dict(sorted(destinations.items())),
            "sequence_hashes": dict(sorted(sequence_hashes.items())),
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
            "first_any_decision_token_index": _numeric_summary(
                first_any_indices
            ),
            "first_explicit_decision_token_index": _numeric_summary(
                first_explicit_indices
            ),
        }

    pairwise = {}
    for first_mode, second_mode in (
        ("ar", "dlm"),
        ("ar", "linear_spec"),
        ("dlm", "linear_spec"),
    ):
        pairwise[f"{first_mode}__{second_mode}"] = pairwise_divergence(
            representative[first_mode],
            representative[second_mode],
        )

    return {
        "evidence_class": "native output-token trajectory analysis",
        "source_evidence_class": payload.get("evidence_class"),
        "model_id": payload.get("model_id"),
        "dtype": payload.get("dtype"),
        "seed": payload.get("seed"),
        "gpu_name": payload.get("gpu_name"),
        "torch_version": payload.get("torch_version"),
        "transformers_version": payload.get("transformers_version"),
        "load_elapsed_seconds": payload.get("load_elapsed_seconds"),
        "focus_case_id": FOCUS_CASE_ID,
        "focus_max_new_tokens": FOCUS_MAX_NEW_TOKENS,
        "focus_observation_count": len(focus),
        "summary_by_mode": summary_by_mode,
        "pairwise_output_divergence": pairwise,
        "representative_outputs": {
            mode: {
                "generated_token_ids": representative[mode][
                    "generated_token_ids"
                ],
                "generated_token_texts": representative[mode][
                    "generated_token_texts"
                ],
                "generated_text": representative[mode]["generated_text"],
                "decision_prefix_events": representative[mode][
                    "decision_prefix_events"
                ],
                "parsed_label": representative[mode]["parsed_label"],
                "parsed_destination": representative[mode][
                    "parsed_destination"
                ],
            }
            for mode in DEFAULT_MODES
        },
        "non_claims": [
            "this analyzes native output-token trajectories, not hidden states",
            "first textual divergence does not identify a hidden causal mechanism",
            "the full physical run retains the other case and budget controls",
            "model output is not World truth or Action authorization",
        ],
    }


def dry_run_payload() -> dict[str, object]:
    return {
        "evidence_class": "native output-token trajectory plan only",
        "source_physical_gate": (
            "reversed mapping token-budget apparatus with added "
            "token-prefix observability"
        ),
        "physical_measured_calls": 72,
        "focus_observations": 18,
        "focus_case_id": FOCUS_CASE_ID,
        "focus_max_new_tokens": FOCUS_MAX_NEW_TOKENS,
        "modes": list(DEFAULT_MODES),
        "observables": [
            "native generated token ids and per-token decoded text",
            "decision parser state after every generated-token prefix",
            "first label-bearing prefix",
            "first explicit decision prefix",
            "pairwise first output-token divergence",
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
        description=(
            "Analyze native output-token trajectories from a fresh "
            "NLD reversed-mapping physical trace."
        )
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.input is None:
        payload = dry_run_payload()
    else:
        payload = analyze_payload(
            json.loads(args.input.read_text(encoding="utf-8"))
        )
    write_payload(payload, args.output)


if __name__ == "__main__":
    main()
