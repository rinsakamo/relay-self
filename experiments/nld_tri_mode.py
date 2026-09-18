from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_MODEL_ID = "nvidia/Nemotron-Labs-Diffusion-3B"
DEFAULT_MODES = ("ar", "dlm", "linear_spec")
DEFAULT_MAX_NEW_TOKENS = 32
DEFAULT_MAX_THINKING_TOKENS = 32
DEFAULT_SEED = 1

# Mirror the current public NVIDIA evaluate.py defaults.
MODE_DEFAULTS: dict[str, dict[str, float | int | None]] = {
    "ar": {"block_length": 1, "threshold": None},
    "dlm": {"block_length": 8, "threshold": 0.9},
    "linear_spec": {"block_length": 32, "threshold": 0.0},
}

_LABEL_RE = re.compile(r"(?<![A-Z0-9_])([ABC])(?![A-Z0-9_])")
_EXPLICIT_LABEL_RE = re.compile(
    r"\b(?:decision\s+label|feasible\s+decision|decision|answer)"
    r"\s*(?:is\s*)?(?:[:=]\s*)?\*{0,2}\s*([ABC])\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ProbeCase:
    case_id: str
    prompt: str
    expected_label: str


def build_probe_case() -> ProbeCase:
    return ProbeCase(
        case_id="easy_separable",
        expected_label="A",
        prompt="""You are resolving one bounded control decision.

Current Intent: reach safety
Threat nearby: true
Cave route open: true
Ridge route open: false

Candidates:
A = FLEE(destination=cave)
B = FLEE(destination=ridge)
C = DEFER

Return exactly one decision label: A, B, or C. Do not explain your answer.""",
    )


def round_to_block(max_new_tokens: int, block_length: int) -> int:
    if max_new_tokens < 1:
        raise ValueError("max_new_tokens must be positive")
    if block_length < 1:
        raise ValueError("block_length must be positive")
    return max(block_length, (max_new_tokens // block_length) * block_length)


def parse_decision_label(text: str) -> str | None:
    explicit_match = _EXPLICIT_LABEL_RE.search(text)
    if explicit_match is not None:
        return explicit_match.group(1).upper()

    matches = _LABEL_RE.findall(text.upper())
    if not matches:
        return None
    return matches[-1]


def resolve_modes(raw: Iterable[str] | None) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_MODES

    modes = tuple(raw)
    if not modes:
        raise ValueError("at least one mode is required")

    unknown = sorted(set(modes) - set(MODE_DEFAULTS))
    if unknown:
        raise ValueError(f"unknown modes: {', '.join(unknown)}")

    if len(set(modes)) != len(modes):
        raise ValueError("modes must not contain duplicates")

    return modes


def mode_arguments(
    mode: str,
    *,
    max_new_tokens: int,
    max_thinking_tokens: int,
) -> dict[str, object]:
    if mode not in MODE_DEFAULTS:
        raise ValueError(f"unknown mode: {mode}")

    defaults = MODE_DEFAULTS[mode]
    block_length = int(defaults["block_length"])
    threshold = defaults["threshold"]

    if mode == "ar":
        return {
            "max_new_tokens": max_new_tokens,
            "block_length": block_length,
            "threshold": threshold,
            "max_thinking_tokens": None,
        }

    return {
        "max_new_tokens": round_to_block(max_new_tokens, block_length),
        "block_length": block_length,
        "threshold": threshold,
        "max_thinking_tokens": max_thinking_tokens,
    }


def dispatch_generation(
    model: object,
    tokenizer: object,
    prompt_ids: object,
    *,
    mode: str,
    max_new_tokens: int,
    max_thinking_tokens: int,
):
    args = mode_arguments(
        mode,
        max_new_tokens=max_new_tokens,
        max_thinking_tokens=max_thinking_tokens,
    )
    eos = tokenizer.eos_token_id

    if mode == "ar":
        method = getattr(model, "ar_generate", None)
        if method is None:
            raise RuntimeError("model does not expose ar_generate")
        return method(
            prompt_ids=prompt_ids,
            max_new_tokens=args["max_new_tokens"],
            eos_token_id=eos,
        )

    if mode == "dlm":
        method = getattr(model, "generate", None)
        if method is None:
            raise RuntimeError("model does not expose generate")
        return method(
            prompt_ids,
            max_new_tokens=args["max_new_tokens"],
            block_length=args["block_length"],
            threshold=args["threshold"],
            eos_token_id=eos,
            max_thinking_tokens=args["max_thinking_tokens"],
        )

    if mode == "linear_spec":
        method = getattr(model, "linear_spec_generate", None)
        if method is None:
            raise RuntimeError("model does not expose linear_spec_generate")
        return method(
            prompt_ids,
            max_new_tokens=args["max_new_tokens"],
            block_length=args["block_length"],
            eos_token_id=eos,
            max_thinking_tokens=args["max_thinking_tokens"],
        )

    raise ValueError(f"unknown mode: {mode}")


def dry_run_payload(
    *,
    model_id: str,
    modes: Iterable[str] | None,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    selected_modes = resolve_modes(modes)
    case = build_probe_case()
    return {
        "evidence_class": "experiment plan only",
        "model_id": model_id,
        "case": asdict(case),
        "modes": [
            {
                "mode": mode,
                "arguments": mode_arguments(
                    mode,
                    max_new_tokens=max_new_tokens,
                    max_thinking_tokens=max_thinking_tokens,
                ),
            }
            for mode in selected_modes
        ],
        "seed": seed,
        "dtype": dtype,
        "device": "cuda",
        "runtime": {
            "loader": "transformers.AutoModel/AutoTokenizer",
            "trust_remote_code": True,
            "lora": False,
            "serving_framework": None,
        },
        "non_claims": [
            "dry-run output is not model evidence",
            "tri-mode availability is not established until actual execution",
            "AR verification is not World verification",
            "no mode is promoted to RelayEngine policy by this probe",
        ],
    }


def _import_runtime():
    try:
        import torch
        import transformers
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "actual model execution requires torch and transformers"
        ) from exc

    major_text = transformers.__version__.split(".", 1)[0]
    try:
        major = int(major_text)
    except ValueError as exc:
        raise RuntimeError(
            f"could not parse transformers major version: {transformers.__version__}"
        ) from exc

    if major < 5:
        raise RuntimeError(
            f"official NLD runtime currently requires transformers>=5.0; "
            f"found {transformers.__version__}"
        )

    return torch, transformers, AutoModel, AutoTokenizer


def _torch_dtype(torch, dtype: str):
    mapping = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }
    try:
        return mapping[dtype]
    except KeyError as exc:
        raise ValueError(f"unsupported dtype: {dtype}") from exc


def _cuda_memory_snapshot(torch) -> dict[str, int] | None:
    if not torch.cuda.is_available():
        return None
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    return {
        "allocated_bytes": int(torch.cuda.memory_allocated()),
        "reserved_bytes": int(torch.cuda.memory_reserved()),
        "free_bytes": int(free_bytes),
        "total_bytes": int(total_bytes),
    }


def _nfe_value(nfe: object) -> float | int | None:
    if isinstance(nfe, bool):
        return int(nfe)
    if isinstance(nfe, (int, float)):
        return nfe
    if hasattr(nfe, "item"):
        value = nfe.item()
        if isinstance(value, (int, float)):
            return value
    return None


def _prepare_prompt(tokenizer: object, model: object, case: ProbeCase):
    messages = [{"role": "user", "content": case.prompt}]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = tokenizer(prompt, return_tensors="pt")
    input_ids = encoded.input_ids.to(model.device)
    return prompt, input_ids


def _reset_seed(torch, seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _run_mode(
    *,
    torch,
    model: object,
    tokenizer: object,
    prompt_ids: object,
    mode: str,
    case: ProbeCase,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
) -> dict[str, object]:
    _reset_seed(torch, seed)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

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
    elapsed_seconds = time.perf_counter() - started

    new_ids = out_ids[0, prompt_ids.shape[1] :]
    generated_text = tokenizer.decode(new_ids, skip_special_tokens=True)
    generated_token_count = int(new_ids.numel())
    nfe_value = _nfe_value(nfe)
    tpf = None
    if (
        nfe_value is not None
        and isinstance(nfe_value, (int, float))
        and nfe_value > 0
    ):
        tpf = generated_token_count / float(nfe_value)

    parsed_label = parse_decision_label(generated_text)
    peak_bytes = None
    if torch.cuda.is_available():
        peak_bytes = int(torch.cuda.max_memory_allocated())

    return {
        "mode": mode,
        "arguments": arguments,
        "elapsed_seconds": elapsed_seconds,
        "nfe": nfe_value,
        "tokens_per_forward": tpf,
        "generated_token_count": generated_token_count,
        "generated_text": generated_text,
        "parsed_label": parsed_label,
        "expected_label": case.expected_label,
        "decision_correct": parsed_label == case.expected_label,
        "cuda_peak_allocated_bytes": peak_bytes,
    }


def run_actual_probe(
    *,
    model_id: str,
    modes: Iterable[str] | None,
    max_new_tokens: int,
    max_thinking_tokens: int,
    seed: int,
    dtype: str,
) -> dict[str, object]:
    torch, transformers, AutoModel, AutoTokenizer = _import_runtime()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; first NLD physical gate requires CUDA")

    selected_modes = resolve_modes(modes)
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
        mode for mode in selected_modes if not method_availability.get(mode, False)
    ]
    if missing:
        raise RuntimeError(
            "loaded model is missing required mode methods: " + ", ".join(missing)
        )

    case = build_probe_case()
    prompt_text, prompt_ids = _prepare_prompt(tokenizer, model, case)

    results = [
        _run_mode(
            torch=torch,
            model=model,
            tokenizer=tokenizer,
            prompt_ids=prompt_ids,
            mode=mode,
            case=case,
            max_new_tokens=max_new_tokens,
            max_thinking_tokens=max_thinking_tokens,
            seed=seed,
        )
        for mode in selected_modes
    ]

    return {
        "evidence_class": "actual-model experiment",
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
        "results": results,
        "non_claims": [
            "this is one bounded prompt, not a benchmark",
            "mode correctness differences do not yet justify an adaptive selector",
            "Linear Self-Speculation internal AR verification is not World verification",
            "model output is not Action authorization or World truth",
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


def _parse_modes(raw: str) -> tuple[str, ...] | None:
    if raw == "all":
        return None
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("--modes must be 'all' or a comma-separated list")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the first NLD-3B matched tri-mode bounded-decision probe."
    )
    parser.add_argument("--run", action="store_true", help="execute the actual model")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--modes",
        default="all",
        help="all or comma-separated: ar,dlm,linear_spec",
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
        default="bf16",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    if args.max_thinking_tokens < 0:
        parser.error("--max-thinking-tokens must be non-negative")

    try:
        modes = _parse_modes(args.modes)
        if args.run:
            payload = run_actual_probe(
                model_id=args.model,
                modes=modes,
                max_new_tokens=args.max_new_tokens,
                max_thinking_tokens=args.max_thinking_tokens,
                seed=args.seed,
                dtype=args.dtype,
            )
        else:
            payload = dry_run_payload(
                model_id=args.model,
                modes=modes,
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
