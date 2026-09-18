from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_MODEL_ID = "google/diffusiongemma-26B-A4B-it"
DEFAULT_TRACE_STEPS = 8
DEFAULT_CHECKPOINTS = (1, 2, 4, 8)


@dataclass(frozen=True, slots=True)
class Candidate:
    label: str
    semantic: str


@dataclass(frozen=True, slots=True)
class ProbeCase:
    case_id: str
    description: str
    prompt: str
    expected_label: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True, slots=True)
class CandidateSummary:
    winner: str
    winner_probability: float
    margin: float
    entropy: float
    probabilities: dict[str, float]


def build_probe_cases() -> tuple[ProbeCase, ...]:
    candidates = (
        Candidate("A", "FLEE(destination=cave)"),
        Candidate("B", "FLEE(destination=ridge)"),
        Candidate("C", "DEFER"),
    )
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
            description="One destination is explicitly open and the other is explicitly blocked.",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 8
Cave route open: true
Ridge route open: false
Decision label:""",
            expected_label="A",
            candidates=candidates,
        ),
        ProbeCase(
            case_id="coupled_constraints",
            description="Both routes are open, but only one satisfies the energy requirement.",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 4
Energy available: 3
Cave route open: true
Cave energy required: 7
Ridge route open: true
Ridge energy required: 2
A route is feasible only when it is open and its energy requirement does not exceed energy available.
Decision label:""",
            expected_label="B",
            candidates=candidates,
        ),
        ProbeCase(
            case_id="incomplete_focus",
            description="The decisive cave route fact is unknown, so omission must not become falsehood.",
            prompt=common
            + """Current Intent: reach safety
Threat nearby: true
Health: 8
Cave route open: UNKNOWN
Ridge route open: false
If no destination is grounded as feasible from the supplied evidence, choose DEFER.
Decision label:""",
            expected_label="C",
            candidates=candidates,
        ),
    )


def _softmax(values: Sequence[float]) -> tuple[float, ...]:
    if not values:
        raise ValueError("candidate logits must not be empty")
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    denominator = sum(weights)
    return tuple(weight / denominator for weight in weights)


def summarize_candidate_logits(
    labels: Sequence[str],
    logits: Sequence[float],
) -> CandidateSummary:
    if len(labels) != len(logits):
        raise ValueError("labels and logits must have the same length")
    if len(labels) < 2:
        raise ValueError("at least two candidates are required")
    if len(set(labels)) != len(labels):
        raise ValueError("candidate labels must be unique")

    probabilities = _softmax(logits)
    ranked = sorted(
        zip(labels, probabilities, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    winner, winner_probability = ranked[0]
    margin = winner_probability - ranked[1][1]
    entropy = -sum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0.0
    )
    return CandidateSummary(
        winner=winner,
        winner_probability=winner_probability,
        margin=margin,
        entropy=entropy,
        probabilities=dict(zip(labels, probabilities, strict=True)),
    )


def select_cases(case_ids: Iterable[str] | None) -> tuple[ProbeCase, ...]:
    cases = build_probe_cases()
    if case_ids is None:
        return cases
    requested = tuple(case_ids)
    known = {case.case_id: case for case in cases}
    unknown = sorted(set(requested) - set(known))
    if unknown:
        raise ValueError(f"unknown case ids: {', '.join(unknown)}")
    return tuple(known[case_id] for case_id in requested)


def _encode_without_special_tokens(tokenizer: object, text: str) -> tuple[int, ...]:
    encoded = tokenizer.encode(text, add_special_tokens=False)
    return tuple(int(token_id) for token_id in encoded)


def resolve_single_token_candidates(
    tokenizer: object,
    candidates: Sequence[Candidate],
) -> tuple[dict[str, int], dict[str, str]]:
    token_ids: dict[str, int] = {}
    token_texts: dict[str, str] = {}
    for candidate in candidates:
        chosen: tuple[str, int] | None = None
        for token_text in (f" {candidate.label}", candidate.label):
            encoded = _encode_without_special_tokens(tokenizer, token_text)
            if len(encoded) == 1:
                chosen = (token_text, encoded[0])
                break
        if chosen is None:
            raise RuntimeError(
                f"candidate label {candidate.label!r} is not single-token in either tested form"
            )
        token_text, token_id = chosen
        token_ids[candidate.label] = token_id
        token_texts[candidate.label] = token_text

    if len(set(token_ids.values())) != len(token_ids):
        raise RuntimeError("candidate labels resolved to duplicate token ids")
    return token_ids, token_texts


def checkpoint_records(
    records: Sequence[dict[str, object]],
    checkpoints: Sequence[int] = DEFAULT_CHECKPOINTS,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for checkpoint in checkpoints:
        if checkpoint < 1:
            raise ValueError("checkpoints must be positive")
        if checkpoint <= len(records):
            result[str(checkpoint)] = dict(records[checkpoint - 1])
    return result


class CandidateTraceRecorder:
    """Observe candidate logits at one canvas slot without modifying generation logits."""

    def __init__(
        self,
        *,
        labels: Sequence[str],
        token_ids: Sequence[int],
        slot: int = 0,
    ) -> None:
        if len(labels) != len(token_ids):
            raise ValueError("labels and token_ids must have the same length")
        self.labels = tuple(labels)
        self.token_ids = tuple(int(token_id) for token_id in token_ids)
        self.slot = slot
        self.records: list[dict[str, object]] = []

    def __call__(self, input_ids, scores, cur_step=None):
        del input_ids
        if scores.ndim != 3:
            raise RuntimeError(
                f"expected diffusion logits shaped [batch, canvas, vocab], got {tuple(scores.shape)}"
            )
        if not 0 <= self.slot < scores.shape[1]:
            raise RuntimeError(
                f"decision slot {self.slot} is outside canvas length {scores.shape[1]}"
            )

        selected = scores[0, self.slot, list(self.token_ids)]
        raw_logits = tuple(float(value) for value in selected.detach().float().cpu().tolist())
        summary = summarize_candidate_logits(self.labels, raw_logits)
        if cur_step is None:
            remaining_step = None
        elif hasattr(cur_step, "item"):
            remaining_step = int(cur_step.item())
        else:
            remaining_step = int(cur_step)

        self.records.append(
            {
                "ordinal": len(self.records) + 1,
                "remaining_step": remaining_step,
                "raw_logits": dict(zip(self.labels, raw_logits, strict=True)),
                **asdict(summary),
            }
        )
        return scores


def _import_model_runtime():
    try:
        import torch
        import transformers
        from transformers import (
            AutoProcessor,
            BitsAndBytesConfig,
            DiffusionGemmaForBlockDiffusion,
            LogitsProcessorList,
        )
    except ImportError as exc:
        raise RuntimeError(
            "model execution requires torch plus a Transformers build that provides "
            "DiffusionGemmaForBlockDiffusion"
        ) from exc
    return (
        torch,
        transformers,
        AutoProcessor,
        BitsAndBytesConfig,
        DiffusionGemmaForBlockDiffusion,
        LogitsProcessorList,
    )


def _move_inputs_to_model_device(inputs, model):
    device = getattr(model, "device", None)
    if device is None:
        return inputs
    return inputs.to(device)


def _load_model_and_processor(*, model_id: str, quantization: str):
    (
        torch,
        transformers,
        AutoProcessor,
        BitsAndBytesConfig,
        DiffusionGemmaForBlockDiffusion,
        LogitsProcessorList,
    ) = _import_model_runtime()

    load_kwargs: dict[str, object] = {
        "device_map": "auto",
        "low_cpu_mem_usage": True,
    }
    if quantization == "bnb4":
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif quantization != "none":
        raise ValueError(f"unsupported quantization mode: {quantization}")

    processor = AutoProcessor.from_pretrained(model_id)
    model = DiffusionGemmaForBlockDiffusion.from_pretrained(model_id, **load_kwargs)
    model.eval()
    return (
        torch,
        transformers,
        processor,
        model,
        LogitsProcessorList,
    )


def _prepare_inputs(processor, model, case: ProbeCase):
    messages = [{"role": "user", "content": case.prompt}]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    return _move_inputs_to_model_device(inputs, model)


def _reset_seed(torch, seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _cuda_peak_bytes(torch) -> int | None:
    if not torch.cuda.is_available():
        return None
    return int(torch.cuda.max_memory_allocated())


def _run_generation_trace(
    *,
    torch,
    processor,
    model,
    logits_processor_list_cls,
    case: ProbeCase,
    steps: int,
    seed: int,
    adaptive: bool,
) -> dict[str, object]:
    if steps < 1:
        raise ValueError("steps must be positive")

    token_ids_by_label, token_text_by_label = resolve_single_token_candidates(
        processor.tokenizer,
        case.candidates,
    )
    labels = tuple(candidate.label for candidate in case.candidates)
    recorder = CandidateTraceRecorder(
        labels=labels,
        token_ids=tuple(token_ids_by_label[label] for label in labels),
        slot=0,
    )
    inputs = _prepare_inputs(processor, model, case)
    prompt_tokens = int(inputs["input_ids"].shape[-1])

    _reset_seed(torch, seed)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    generation_kwargs: dict[str, object] = {
        "max_new_tokens": 1,
        "max_denoising_steps": steps,
        "return_dict_in_generate": True,
        "logits_processor": logits_processor_list_cls([recorder]),
    }
    if not adaptive:
        generation_kwargs.update(
            stability_threshold=None,
            confidence_threshold=None,
        )

    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(**inputs, **generation_kwargs)
    elapsed_seconds = time.perf_counter() - started

    records = tuple(recorder.records)
    final_record = records[-1] if records else None
    generated = output.sequences[0, prompt_tokens:]
    generated_token_ids = [
        int(token_id) for token_id in generated.detach().cpu().tolist()
    ]
    tokens_per_forward = getattr(output, "tokens_per_forward", None)
    if tokens_per_forward is not None:
        tokens_per_forward = [
            float(value)
            for value in tokens_per_forward.detach().float().cpu().tolist()
        ]

    return {
        "case_id": case.case_id,
        "description": case.description,
        "expected_label": case.expected_label,
        "candidate_semantics": {
            candidate.label: candidate.semantic for candidate in case.candidates
        },
        "candidate_token_ids": token_ids_by_label,
        "candidate_token_texts": token_text_by_label,
        "prompt_tokens": prompt_tokens,
        "requested_max_new_tokens": 1,\n        "decision_slots_observed": 1,
        "canvas_length": int(model.config.canvas_length),
        "configured_max_denoising_steps": steps,
        "adaptive_stopping_enabled": adaptive,
        "actual_denoising_steps": len(records),
        "elapsed_seconds": elapsed_seconds,
        "cuda_peak_bytes": _cuda_peak_bytes(torch),
        "tokens_per_forward": tokens_per_forward,
        "generated_token_count": len(generated_token_ids),\n        "generated_token_ids": generated_token_ids,
        "candidate_trace": list(records),
        "checkpoints": checkpoint_records(records),
        "final_candidate_readout": final_record,
        "final_candidate_correct": (
            final_record is not None and final_record["winner"] == case.expected_label
        ),
    }


def run_model_probe(
    *,
    model_id: str,
    case_ids: Iterable[str] | None,
    steps: int,
    adaptive: bool,
    seed: int,
    quantization: str,
) -> dict[str, object]:
    (
        torch,
        transformers,
        processor,
        model,
        logits_processor_list_cls,
    ) = _load_model_and_processor(model_id=model_id, quantization=quantization)

    cases = select_cases(case_ids)
    fixed_results = [
        _run_generation_trace(
            torch=torch,
            processor=processor,
            model=model,
            logits_processor_list_cls=logits_processor_list_cls,
            case=case,
            steps=steps,
            seed=seed,
            adaptive=False,
        )
        for case in cases
    ]

    adaptive_results: list[dict[str, object]] = []
    if adaptive:
        adaptive_steps = int(getattr(model.generation_config, "max_denoising_steps", 48))
        adaptive_results = [
            _run_generation_trace(
                torch=torch,
                processor=processor,
                model=model,
                logits_processor_list_cls=logits_processor_list_cls,
                case=case,
                steps=adaptive_steps,
                seed=seed,
                adaptive=True,
            )
            for case in cases
        ]

    return {
        "evidence_class": "actual-model experiment",
        "model_id": model_id,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "quantization": quantization,
        "seed": seed,
        "fixed_trace_steps": steps,
        "checkpoint_ordinals": [
            checkpoint for checkpoint in DEFAULT_CHECKPOINTS if checkpoint <= steps
        ],
        "fixed_results": fixed_results,
        "adaptive_results": adaptive_results,
        "notes": [
            "Candidate probabilities are normalized only across the bounded candidate token set.",
            "The recorder observes raw candidate logits before DiffusionGemma's temperature processor and does not modify them.",
            "max_new_tokens=1 selects one canvas here; current DiffusionGemma generation still appends the full model.config.canvas_length canvas before autoregressive stopping.",\n            "The bounded decision reads one diagnostic canvas slot; it is not a one-token physical generation path.",
            "Candidate readout quality is model-quality evidence, not Action authorization or World truth.",
        ],
    }


def dry_run_payload(
    *,
    model_id: str,
    case_ids: Iterable[str] | None,
    steps: int,
    adaptive: bool,
    seed: int,
    quantization: str,
) -> dict[str, object]:
    return {
        "evidence_class": "experiment plan only",
        "model_id": model_id,
        "cases": [asdict(case) for case in select_cases(case_ids)],
        "fixed_trace_steps": steps,
        "adaptive_requested": adaptive,
        "seed": seed,
        "quantization": quantization,
        "checkpoint_ordinals": [
            checkpoint for checkpoint in DEFAULT_CHECKPOINTS if checkpoint <= steps
        ],
        "runtime_requirements": [
            "torch",
            "transformers with DiffusionGemmaForBlockDiffusion",
            "accelerate/device_map support for model execution",
            "bitsandbytes only when --quantization bnb4 is selected",
        ],
        "non_claims": [
            "dry-run output is not a model result",
            "bnb4 compatibility/performance is not established by this plan",
            "one logical decision token does not imply one-token physical decoder compute",
        ],
    }


def _write_or_print(payload: dict[str, object], output: str | None) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if output is None:
        print(serialized)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
    print(path)


def _parse_case_ids(raw: str) -> tuple[str, ...] | None:
    if raw == "all":
        return None
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("--cases must be 'all' or a comma-separated list")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe bounded candidate readout across DiffusionGemma denoising steps."
    )
    parser.add_argument("--run", action="store_true", help="execute the actual model")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--cases",
        default="all",
        help="all or comma-separated case ids",
    )
    parser.add_argument("--steps", type=int, default=DEFAULT_TRACE_STEPS)
    parser.add_argument(
        "--adaptive",
        action="store_true",
        help="also run the checkpoint's adaptive stopping configuration",
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--quantization",
        choices=("none", "bnb4"),
        default="none",
        help="runtime loading mode; bnb4 is experimental and not a RelaySelf dependency",
    )
    parser.add_argument("--output", help="optional JSON result path")
    args = parser.parse_args()

    if args.steps < 1:
        parser.error("--steps must be positive")

    try:
        case_ids = _parse_case_ids(args.cases)
        if args.run:
            payload = run_model_probe(
                model_id=args.model,
                case_ids=case_ids,
                steps=args.steps,
                adaptive=args.adaptive,
                seed=args.seed,
                quantization=args.quantization,
            )
        else:
            payload = dry_run_payload(
                model_id=args.model,
                case_ids=case_ids,
                steps=args.steps,
                adaptive=args.adaptive,
                seed=args.seed,
                quantization=args.quantization,
            )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    _write_or_print(payload, args.output)


if __name__ == "__main__":
    main()
