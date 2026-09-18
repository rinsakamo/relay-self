from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1
DEFAULT_MODEL_ID = "google/diffusiongemma-26B-A4B-it"
DEFAULT_CASE = "easy_separable"
DEFAULT_STEPS = 1
DEFAULT_QUANTIZATION = "bnb4"
DEFAULT_TIMEOUT_SECONDS = 1800
REQUIRED_PACKAGES = ("torch", "transformers", "accelerate")


class PhysicalTransactionError(RuntimeError):
    """Raised when the bounded physical transaction cannot complete truthfully."""


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_capture(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PhysicalTransactionError(
            f"command could not complete: {shlex.join(command)}: {type(exc).__name__}: {exc}"
        ) from exc


def _require_success(
    completed: subprocess.CompletedProcess[str],
    *,
    description: str,
) -> str:
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PhysicalTransactionError(
            f"{description} failed with exit {completed.returncode}: {detail}"
        )
    return completed.stdout.strip()


def _require_clean_repo(repo_root: Path) -> tuple[str, str, str]:
    if not (repo_root / ".git").exists():
        raise PhysicalTransactionError(f"repo-root is not a git checkout: {repo_root}")

    status = _require_success(
        _run_capture(["git", "status", "--porcelain"], cwd=repo_root),
        description="git status",
    )
    if status:
        raise PhysicalTransactionError(
            "physical transaction requires a clean RelaySelf checkout"
        )

    head = _require_success(
        _run_capture(["git", "rev-parse", "HEAD"], cwd=repo_root),
        description="git head",
    )
    tree = _require_success(
        _run_capture(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root),
        description="git tree",
    )
    branch = _require_success(
        _run_capture(["git", "branch", "--show-current"], cwd=repo_root),
        description="git branch",
    )
    if not branch:
        raise PhysicalTransactionError(
            "physical transaction requires an attached RelaySelf branch"
        )
    return head, tree, branch


def _find_nvidia_smi() -> str:
    executable = shutil.which("nvidia-smi")
    if executable is not None:
        return executable

    wsl_path = Path("/usr/lib/wsl/lib/nvidia-smi")
    if wsl_path.is_file():
        return str(wsl_path)

    raise PhysicalTransactionError(
        "nvidia-smi is unavailable on PATH and /usr/lib/wsl/lib/nvidia-smi is absent"
    )


def _collect_gpu_identity() -> dict[str, object]:
    executable = _find_nvidia_smi()
    completed = _run_capture(
        [
            executable,
            "--query-gpu=name,driver_version,memory.total,memory.free",
            "--format=csv,noheader,nounits",
        ]
    )
    output = _require_success(completed, description="nvidia-smi identity query")
    rows: list[dict[str, object]] = []
    for index, line in enumerate(output.splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            raise PhysicalTransactionError(
                f"unexpected nvidia-smi row: {line!r}"
            )
        name, driver, total_mib, free_mib = parts
        try:
            total = int(total_mib)
            free = int(free_mib)
        except ValueError as exc:
            raise PhysicalTransactionError(
                f"nvidia-smi memory fields are not integers: {line!r}"
            ) from exc
        rows.append(
            {
                "index": index,
                "name": name,
                "driver_version": driver,
                "memory_total_mib": total,
                "memory_free_mib": free,
            }
        )

    if not rows:
        raise PhysicalTransactionError("nvidia-smi returned no GPU rows")
    return {"executable": executable, "gpus": rows}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _collect_python_environment(*, quantization: str) -> dict[str, object]:
    packages = {
        name: _package_version(name)
        for name in (*REQUIRED_PACKAGES, "bitsandbytes")
    }
    missing = [name for name in REQUIRED_PACKAGES if packages[name] is None]
    if missing:
        raise PhysicalTransactionError(
            "required Python packages are not installed: " + ", ".join(missing)
        )
    if quantization == "bnb4" and packages["bitsandbytes"] is None:
        raise PhysicalTransactionError(
            "bitsandbytes is required for --quantization bnb4"
        )

    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
    }


def build_probe_command(
    *,
    repo_root: Path,
    model_id: str,
    case_id: str,
    steps: int,
    quantization: str,
    output_path: Path,
    run: bool,
) -> list[str]:
    del repo_root
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.diffusiongemma_bounded_decision",
    ]
    if run:
        command.append("--run")
    command.extend(
        [
            "--model",
            model_id,
            "--cases",
            case_id,
            "--steps",
            str(steps),
            "--seed",
            "1",
            "--quantization",
            quantization,
            "--output",
            str(output_path),
        ]
    )
    return command


def _run_probe_command(
    command: list[str],
    *,
    repo_root: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
) -> int:
    completed = _run_capture(
        command,
        cwd=repo_root,
        timeout=timeout_seconds,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed.returncode


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PhysicalTransactionError(
            f"could not read JSON evidence {path}: {exc}"
        ) from exc


def validate_probe_result(
    payload: object,
    *,
    model_id: str,
    case_id: str,
    steps: int,
    quantization: str,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError("probe result must be a JSON object")
    if payload.get("evidence_class") != "actual-model experiment":
        raise PhysicalTransactionError(
            "probe result is not classified as actual-model experiment evidence"
        )
    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError("probe result model id does not match request")
    if payload.get("quantization") != quantization:
        raise PhysicalTransactionError(
            "probe result quantization does not match request"
        )
    if payload.get("fixed_trace_steps") != steps:
        raise PhysicalTransactionError(
            "probe result fixed_trace_steps does not match request"
        )

    fixed_results = payload.get("fixed_results")
    if not isinstance(fixed_results, list) or len(fixed_results) != 1:
        raise PhysicalTransactionError(
            "probe result must contain exactly one fixed result"
        )
    result = fixed_results[0]
    if not isinstance(result, dict):
        raise PhysicalTransactionError("fixed result must be a JSON object")
    if result.get("case_id") != case_id:
        raise PhysicalTransactionError("fixed result case id does not match request")
    if result.get("actual_denoising_steps") != steps:
        raise PhysicalTransactionError(
            "fixed result did not execute the requested denoising-step count"
        )

    canvas_length = result.get("canvas_length")
    if (
        not isinstance(canvas_length, int)
        or isinstance(canvas_length, bool)
        or canvas_length < 1
    ):
        raise PhysicalTransactionError("fixed result has invalid canvas_length")

    final_readout = result.get("final_candidate_readout")
    if not isinstance(final_readout, dict):
        raise PhysicalTransactionError(
            "fixed result is missing final candidate readout"
        )

    return {
        "case_id": case_id,
        "expected_label": result.get("expected_label"),
        "winner": final_readout.get("winner"),
        "candidate_correct": result.get("final_candidate_correct"),
        "actual_denoising_steps": result.get("actual_denoising_steps"),
        "canvas_length": canvas_length,
        "elapsed_seconds": result.get("elapsed_seconds"),
        "cuda_peak_bytes": result.get("cuda_peak_bytes"),
        "generated_token_count": result.get("generated_token_count"),
        "tokens_per_forward": result.get("tokens_per_forward"),
        "transformers_version": payload.get("transformers_version"),
        "torch_version": payload.get("torch_version"),
    }


def _prepare_evidence_root(path: Path) -> Path:
    if path.exists():
        if not path.is_dir():
            raise PhysicalTransactionError(
                f"evidence-root exists but is not a directory: {path}"
            )
        if any(path.iterdir()):
            raise PhysicalTransactionError(
                f"evidence-root must be new or empty: {path}"
            )
    else:
        path.mkdir(parents=True)
    return path.resolve()


def _initial_summary(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
    case_id: str,
    steps: int,
    quantization: str,
) -> dict[str, object]:
    scope = (
        "unquantized_baseline"
        if quantization == "none"
        else "bnb4_local_feasibility"
    )
    return {
        "format_version": FORMAT_VERSION,
        "status": "STARTED",
        "current_stage": None,
        "completed_stages": [],
        "repo_root": str(repo_root),
        "evidence_root": str(evidence_root),
        "model_id": model_id,
        "case_id": case_id,
        "steps": steps,
        "quantization": quantization,
        "qualification_scope": scope,
        "baseline_equivalent": quantization == "none",
    }


def _complete_stage(summary: dict[str, object], stage: str) -> None:
    completed = summary.get("completed_stages")
    if not isinstance(completed, list):
        raise AssertionError("completed_stages must be a list")
    completed.append(stage)
    summary["current_stage"] = None


def run_transaction(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
    case_id: str,
    steps: int,
    quantization: str,
    timeout_seconds: float,
) -> int:
    if steps < 1:
        raise PhysicalTransactionError("steps must be positive")
    if timeout_seconds <= 0:
        raise PhysicalTransactionError("timeout_seconds must be positive")

    evidence_root = _prepare_evidence_root(evidence_root)
    summary_path = evidence_root / "summary.json"
    summary = _initial_summary(
        repo_root=repo_root,
        evidence_root=evidence_root,
        model_id=model_id,
        case_id=case_id,
        steps=steps,
        quantization=quantization,
    )
    _write_json(summary_path, summary)

    try:
        stage = "repo_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        head, tree, branch = _require_clean_repo(repo_root)
        summary["git"] = {"head": head, "tree": tree, "branch": branch}
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "gpu_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        summary["gpu"] = _collect_gpu_identity()
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "python_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        summary["python_environment"] = _collect_python_environment(
            quantization=quantization
        )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "dry_run"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        dry_output = evidence_root / "dry-run.json"
        dry_command = build_probe_command(
            repo_root=repo_root,
            model_id=model_id,
            case_id=case_id,
            steps=steps,
            quantization=quantization,
            output_path=dry_output,
            run=False,
        )
        summary["dry_run_command"] = dry_command
        dry_returncode = _run_probe_command(
            dry_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "dry-run.stdout.txt",
            stderr_path=evidence_root / "dry-run.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if dry_returncode != 0:
            raise PhysicalTransactionError(
                f"dry-run probe exited with code {dry_returncode}"
            )
        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("evidence_class") != "experiment plan only"
        ):
            raise PhysicalTransactionError(
                "dry-run output is not classified as experiment plan only"
            )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "actual_model"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        actual_output = evidence_root / "actual-model.json"
        actual_command = build_probe_command(
            repo_root=repo_root,
            model_id=model_id,
            case_id=case_id,
            steps=steps,
            quantization=quantization,
            output_path=actual_output,
            run=True,
        )
        summary["actual_model_command"] = actual_command
        actual_returncode = _run_probe_command(
            actual_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "actual-model.stdout.txt",
            stderr_path=evidence_root / "actual-model.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        summary["actual_model_returncode"] = actual_returncode
        if actual_returncode != 0:
            raise PhysicalTransactionError(
                f"actual-model probe exited with code {actual_returncode}"
            )

        actual_payload = _load_json(actual_output)
        summary["observation"] = validate_probe_result(
            actual_payload,
            model_id=model_id,
            case_id=case_id,
            steps=steps,
            quantization=quantization,
        )
        _complete_stage(summary, stage)

        summary["status"] = "PASS"
        summary["non_claims"] = [
            "PASS does not make model output Action authorization or World truth.",
            "bnb4 PASS is local-feasibility evidence, not the unquantized baseline.",
            "one observed decision slot does not imply one-token physical generation.",
            "this one-case one-step transaction does not establish adaptive cognition quality.",
        ]
        _write_json(summary_path, summary)
        return 0
    except PhysicalTransactionError as exc:
        summary["status"] = "FAIL_NOT_QUALIFIED"
        summary["failure_stage"] = summary.get("current_stage")
        summary["failure_reason"] = str(exc)
        summary["current_stage"] = None
        _write_json(summary_path, summary)
        return 2


def main() -> None:
    default_repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Run the smallest fresh physical DiffusionGemma bounded-decision transaction."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root,
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument(
        "--quantization",
        choices=("none", "bnb4"),
        default=DEFAULT_QUANTIZATION,
        help=(
            "bnb4 is local-feasibility evidence for constrained hardware; "
            "none is the unquantized baseline path"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    args = parser.parse_args()

    try:
        result = run_transaction(
            repo_root=args.repo_root.resolve(),
            evidence_root=args.evidence_root,
            model_id=args.model,
            case_id=args.case,
            steps=args.steps,
            quantization=args.quantization,
            timeout_seconds=args.timeout_seconds,
        )
    except PhysicalTransactionError as exc:
        parser.error(str(exc))
    raise SystemExit(result)


if __name__ == "__main__":
    main()
