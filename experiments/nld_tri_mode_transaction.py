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
DEFAULT_MODEL_ID = "nvidia/Nemotron-Labs-Diffusion-3B"
DEFAULT_TIMEOUT_SECONDS = 1800
REQUIRED_PACKAGES = ("torch", "transformers")


class PhysicalTransactionError(RuntimeError):
    """Raised when the NLD physical transaction cannot complete truthfully."""


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
            f"command could not complete: {shlex.join(command)}: "
            f"{type(exc).__name__}: {exc}"
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


def _collect_python_environment() -> dict[str, object]:
    packages = {name: _package_version(name) for name in REQUIRED_PACKAGES}
    missing = [name for name, version in packages.items() if version is None]
    if missing:
        raise PhysicalTransactionError(
            "required Python packages are not installed: " + ", ".join(missing)
        )

    transformers_version = packages["transformers"]
    assert transformers_version is not None
    major_text = transformers_version.split(".", 1)[0]
    try:
        transformers_major = int(major_text)
    except ValueError as exc:
        raise PhysicalTransactionError(
            f"could not parse transformers version: {transformers_version}"
        ) from exc

    if transformers_major < 5:
        raise PhysicalTransactionError(
            "official NLD direct runtime currently requires transformers>=5.0; "
            f"found {transformers_version}"
        )

    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
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


def build_probe_command(
    *,
    model_id: str,
    output_path: Path,
    run: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.nld_tri_mode",
    ]
    if run:
        command.append("--run")

    command.extend(
        [
            "--model",
            model_id,
            "--modes",
            "all",
            "--dtype",
            "bf16",
            "--max-new-tokens",
            "32",
            "--max-thinking-tokens",
            "32",
            "--seed",
            "1",
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


def validate_actual_payload(
    payload: object,
    *,
    model_id: str,
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError("actual NLD evidence must be a JSON object")

    if payload.get("evidence_class") != "actual-model experiment":
        raise PhysicalTransactionError(
            "actual NLD payload is not classified as actual-model experiment"
        )

    if payload.get("model_id") != model_id:
        raise PhysicalTransactionError(
            "actual NLD payload model id does not match requested model"
        )

    if payload.get("dtype") != "bf16":
        raise PhysicalTransactionError(
            "actual NLD payload did not use the canonical first-gate bf16 dtype"
        )

    methods = payload.get("method_availability")
    if not isinstance(methods, dict):
        raise PhysicalTransactionError("method_availability is missing")

    required_modes = ("ar", "dlm", "linear_spec")
    unavailable = [mode for mode in required_modes if methods.get(mode) is not True]
    if unavailable:
        raise PhysicalTransactionError(
            "native NLD methods unavailable: " + ", ".join(unavailable)
        )

    results = payload.get("results")
    if not isinstance(results, list):
        raise PhysicalTransactionError("results must be a list")

    by_mode: dict[str, dict[str, object]] = {}
    for item in results:
        if not isinstance(item, dict):
            raise PhysicalTransactionError("result entry must be a JSON object")
        mode = item.get("mode")
        if isinstance(mode, str):
            by_mode[mode] = item

    missing_results = [mode for mode in required_modes if mode not in by_mode]
    if missing_results:
        raise PhysicalTransactionError(
            "actual NLD payload is missing mode results: "
            + ", ".join(missing_results)
        )

    return {
        "model_id": model_id,
        "dtype": payload.get("dtype"),
        "gpu_name": payload.get("gpu_name"),
        "torch_version": payload.get("torch_version"),
        "transformers_version": payload.get("transformers_version"),
        "load_elapsed_seconds": payload.get("load_elapsed_seconds"),
        "cuda_before_load": payload.get("cuda_before_load"),
        "cuda_after_load": payload.get("cuda_after_load"),
        "modes": {
            mode: {
                "elapsed_seconds": by_mode[mode].get("elapsed_seconds"),
                "nfe": by_mode[mode].get("nfe"),
                "tokens_per_forward": by_mode[mode].get("tokens_per_forward"),
                "generated_token_count": by_mode[mode].get(
                    "generated_token_count"
                ),
                "parsed_label": by_mode[mode].get("parsed_label"),
                "expected_label": by_mode[mode].get("expected_label"),
                "decision_correct": by_mode[mode].get("decision_correct"),
                "cuda_peak_allocated_bytes": by_mode[mode].get(
                    "cuda_peak_allocated_bytes"
                ),
            }
            for mode in required_modes
        },
    }


def _initial_summary(
    *,
    repo_root: Path,
    evidence_root: Path,
    model_id: str,
) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "status": "STARTED",
        "current_stage": None,
        "completed_stages": [],
        "repo_root": str(repo_root),
        "evidence_root": str(evidence_root),
        "model_id": model_id,
        "qualification_scope": "nld_3b_tri_mode_first_gate",
        "canonical_runtime": {
            "engine": "pytorch_transformers_direct",
            "dtype": "bf16",
            "modes": ["ar", "dlm", "linear_spec"],
            "lora": False,
            "quantization": None,
            "serving_framework": None,
        },
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
    timeout_seconds: float,
) -> int:
    if timeout_seconds <= 0:
        raise PhysicalTransactionError("timeout_seconds must be positive")

    evidence_root = _prepare_evidence_root(evidence_root)
    summary_path = evidence_root / "summary.json"

    summary = _initial_summary(
        repo_root=repo_root,
        evidence_root=evidence_root,
        model_id=model_id,
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
        summary["python_environment"] = _collect_python_environment()
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "dry_run"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        dry_output = evidence_root / "dry-run.json"
        dry_command = build_probe_command(
            model_id=model_id,
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
            model_id=model_id,
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
        summary["observation"] = validate_actual_payload(
            actual_payload,
            model_id=model_id,
        )
        _complete_stage(summary, stage)

        summary["status"] = "TRI_MODE_PASS"
        summary["non_claims"] = [
            "TRI_MODE_PASS is one bounded prompt, not a benchmark.",
            "No decoding mode is promoted to RelayEngine policy by this result.",
            "Linear Self-Speculation internal AR verification is not World verification.",
            "Model output is not Action authorization or World truth.",
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
        description="Run the fresh NLD-3B tri-mode physical qualification."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root,
    )
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
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
            timeout_seconds=args.timeout_seconds,
        )
    except PhysicalTransactionError as exc:
        parser.error(str(exc))

    raise SystemExit(result)


if __name__ == "__main__":
    main()
