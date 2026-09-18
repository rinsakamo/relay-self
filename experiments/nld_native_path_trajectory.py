from __future__ import annotations

import argparse
import collections
import hashlib
import inspect
import json
import re
import time
from dataclasses import asdict
from pathlib import Path

from experiments.nld_tri_mode import (
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
    parse_decision,
)
from experiments.nld_tri_mode_repeatability import (
    MODE_PERMUTATIONS,
    _numeric_summary,
)

DEFAULT_DTYPE = "bf16"
DEFAULT_MAX_NEW_TOKENS = 32
DEFAULT_MAX_THINKING_TOKENS = 32
_HEX40_RE = re.compile(r"(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])")


def build_case() -> ProbeCase:
    return ProbeCase(
        case_id="reversed_ridge_open",
        expected_label="A",
        prompt="""You are resolving one bounded control decision.
Choose only among labels A, B, and C.
Use only the supplied route evidence.
The candidate meanings are:
A = FLEE(destination=ridge)
B = FLEE(destination=cave)
C = DEFER

Current Intent: reach safety
Threat nearby: true
Health: 8
Cave route open: false
Ridge route open: true
A destination is feasible only when its route is explicitly open.
Decision label:""",
    )


def build_schedule() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    index = 0
    for permutation_index, order in enumerate(MODE_PERMUTATIONS):
        for ordinal_position, mode in enumerate(order, start=1):
            rows.append(
                {
                    "observation_index": index,
                    "permutation_index": permutation_index,
                    "order": list(order),
                    "ordinal_position": ordinal_position,
                    "mode": mode,
                }
            )
            index += 1
    return rows


def resolve_candidate_forms(
    tokenizer: object,
) -> dict[str, list[dict[str, object]]]:
    forms: dict[str, list[dict[str, object]]] = {}
    for label in ("A", "B", "C"):
        entries: list[dict[str, object]] = []
        seen: set[int] = set()
        for text in (label, f" {label}", f"\n{label}"):
            token_ids = tokenizer.encode(text, add_special_tokens=False)
            if len(token_ids) != 1:
                continue
            token_id = int(token_ids[0])
            if token_id in seen:
                continue
            seen.add(token_id)
            entries.append({"text": text, "token_id": token_id})
        if not entries:
            raise RuntimeError(
                f"no tested single-token form for label {label}"
            )
        forms[label] = entries
    return forms


def source_metadata(model: object) -> dict[str, object]:
    class_file = Path(inspect.getfile(model.__class__))
    revision = _HEX40_RE.search(str(class_file))
    methods: dict[str, object] = {}
    for mode, method_name in {
        "ar": "ar_generate",
        "dlm": "generate",
        "linear_spec": "linear_spec_generate",
    }.items():
        source = inspect.getsource(getattr(model, method_name))
        methods[mode] = {
            "method_name": method_name,
            "sha256": hashlib.sha256(
                source.encode("utf-8")
            ).hexdigest(),
            "line_count": len(source.splitlines()),
        }
    return {
        "class_file": str(class_file),
        "class_file_sha256": hashlib.sha256(
            class_file.read_bytes()
        ).hexdigest(),
        "loaded_revision_from_path": (
            revision.group(1) if revision else None
        ),
        "methods": methods,
    }



def candidate_scores(
    logits,
    forms: dict[str, list[dict[str, object]]],
) -> dict[str, list[float]]:
    scores: dict[str, list[float]] = {}
    for label in ("A", "B", "C"):
        token_ids = [
            int(item["token_id"]) for item in forms[label]
        ]
        selected = logits[..., token_ids].max(dim=-1).values
        scores[label] = [
            float(value)
            for value in selected[0].detach().float().cpu().tolist()
        ]
    return scores


def token_diagnostic(
    *,
    tokenizer: object,
    logits,
    forms: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    scores = candidate_scores(logits, forms)
    argmax_ids = [
        int(value)
        for value in logits.argmax(dim=-1)[0].detach().cpu().tolist()
    ]
    winners = [
        max(
            ("A", "B", "C"),
            key=lambda label: scores[label][position],
        )
        for position in range(len(argmax_ids))
    ]
    return {
        "argmax_token_ids": argmax_ids,
        "candidate_scores": scores,
        "candidate_winners": winners,
    }




def decision_events(
    tokenizer: object,
    token_ids: list[int],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(1, len(token_ids) + 1):
        decoded = tokenizer.decode(
            token_ids[:index],
            skip_special_tokens=True,
        )
        parsed = parse_decision(decoded)
        rows.append(
            {
                "index": index,
                "label": parsed.label,
                "source": parsed.source,
            }
        )
    return rows



def sequence_sha256(token_ids: list[int]) -> str:
    payload = ",".join(str(value) for value in token_ids)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def dry_run_payload() -> dict[str, object]:
    schedule = build_schedule()
    return {
        "evidence_class": "native path trajectory plan only",
        "model_id": DEFAULT_MODEL_ID,
        "case": asdict(build_case()),
        "modes": list(DEFAULT_MODES),
        "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "max_thinking_tokens": DEFAULT_MAX_THINKING_TOKENS,
        "measured_schedule": schedule,
        "measured_calls": len(schedule),
        "warmup_calls": len(DEFAULT_MODES),
        "required_native_match": {
            "generated_token_ids": True,
            "nfe": True,
        },
        "non_claims": [
            "diagnostic path must match the native result before interpretation",
            "candidate scores are diagnostic only",
            "algorithmic verification is not World verification",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = dry_run_payload()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(path)
    else:
        print(text)


if __name__ == "__main__":
    main()
