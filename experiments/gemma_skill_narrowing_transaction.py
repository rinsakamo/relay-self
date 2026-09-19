from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from experiments.mineflayer_cognition_llama_cpp_transaction import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    EXPECTED_GGUF_SHA256,
    PhysicalTransactionError,
    _collect_gpu_identity,
    _collect_llama_revision,
    _collect_server_version,
    _port_is_free,
    _probe_and_attest,
    _require_clean_repo,
    _require_llama_cpp_paths,
    _server_command,
    _start_server,
    _terminate_owned_process,
    _verify_artifact,
    _wait_until_ready,
)
from experiments.nld_gemma_cross_substrate_transaction import (
    _gpu_memory_used_mib,
)
from experiments.nld_tri_mode_transaction import (
    DEFAULT_TIMEOUT_SECONDS,
    _load_json,
    _prepare_evidence_root,
    _run_probe_command,
    _write_json,
)

FORMAT_VERSION = 1


def _experiment_command(
    *,
    endpoint: str,
    model: str,
    timeout: float,
    output_path: Path,
    run: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.gemma_skill_narrowing",
    ]
    if run:
        command.append("--run")
    command.extend(
        [
            "--endpoint",
            endpoint,
            "--model",
            model,
            "--timeout",
            str(timeout),
            "--output",
            str(output_path),
        ]
    )
    return command


def validate_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise PhysicalTransactionError(
            "Gemma narrowing evidence must be a JSON object"
        )
    if payload.get("evidence_class") != (
        "actual-model gemma skill narrowing"
    ):
        raise PhysicalTransactionError(
            "Gemma narrowing evidence class is incorrect"
        )

    observations = payload.get("observations")
    if not isinstance(observations, list) or len(observations) != 48:
        count = len(observations) if isinstance(observations, list) else "non-list"
        raise PhysicalTransactionError(
            f"expected 48 measured episodes; found {count}"
        )

    expected_cases = {
        "cave_only",
        "ridge_only",
        "both_cave_shelter",
        "both_ridge_shelter",
    }
    expected_conditions = {"broad", "narrow"}
    cell_counts: dict[tuple[str, str], int] = {}

    for row in observations:
        if not isinstance(row, dict):
            raise PhysicalTransactionError(
                "measured episode must be a JSON object"
            )
        case_id = row.get("case_id")
        condition = row.get("condition")
        if case_id not in expected_cases:
            raise PhysicalTransactionError(
                f"unexpected case_id: {case_id!r}"
            )
        if condition not in expected_conditions:
            raise PhysicalTransactionError(
                f"unexpected condition: {condition!r}"
            )
        key = (str(case_id), str(condition))
        cell_counts[key] = cell_counts.get(key, 0) + 1

        calls = row.get("provider_calls")
        if not isinstance(calls, list) or len(calls) not in {1, 2}:
            raise PhysicalTransactionError(
                f"{key!r} episode must contain one or two provider calls"
            )
        for call in calls:
            if not isinstance(call, dict):
                raise PhysicalTransactionError(
                    "provider call record must be an object"
                )
            if not isinstance(call.get("prompt_tokens"), int):
                raise PhysicalTransactionError(
                    "provider call is missing prompt_tokens"
                )
            if not isinstance(call.get("completion_tokens"), int):
                raise PhysicalTransactionError(
                    "provider call is missing completion_tokens"
                )
            if not isinstance(call.get("elapsed_seconds"), (int, float)):
                raise PhysicalTransactionError(
                    "provider call is missing elapsed_seconds"
                )

    if len(cell_counts) != 8:
        raise PhysicalTransactionError(
            f"expected 8 case/condition cells; found {len(cell_counts)}"
        )
    for key, count in cell_counts.items():
        if count != 6:
            raise PhysicalTransactionError(
                f"{key!r} expected 6 episodes; found {count}"
            )

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PhysicalTransactionError("summary is missing")
    by_condition = summary.get("by_condition")
    if not isinstance(by_condition, dict):
        raise PhysicalTransactionError(
            "by_condition summary is missing"
        )
    for condition in expected_conditions:
        subject = by_condition.get(condition)
        if not isinstance(subject, dict) or subject.get("count") != 24:
            raise PhysicalTransactionError(
                f"{condition} summary must contain 24 episodes"
            )

    return {
        "measured_episode_count": len(observations),
        "cost_comparison_eligible": summary.get(
            "cost_comparison_eligible"
        ),
        "by_condition": by_condition,
        "by_case_condition": summary.get("by_case_condition"),
    }


def _initial_summary(
    *,
    repo_root: Path,
    evidence_root: Path,
    llama_cpp_root: Path,
    artifact_path: Path,
) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "status": "STARTED",
        "current_stage": None,
        "completed_stages": [],
        "repo_root": str(repo_root),
        "evidence_root": str(evidence_root),
        "llama_cpp_root": str(llama_cpp_root),
        "artifact_path": str(artifact_path),
        "qualification_scope": "gemma_skill_narrowing",
        "canonical_runtime": {
            "conditions": ["broad", "narrow"],
            "cases": 4,
            "observations_per_case_condition": 6,
            "measured_episode_count": 48,
            "bounded_warmup_count": 1,
            "think_warmup_count": 1,
            "context": 8192,
            "slots": 1,
            "quantization": "Q4_K_M",
            "cache_prompt": False,
            "reasoning_effort": "none",
        },
    }


def _complete_stage(
    summary: dict[str, object],
    stage: str,
) -> None:
    completed = summary.get("completed_stages")
    if not isinstance(completed, list):
        raise AssertionError("completed_stages must be a list")
    completed.append(stage)
    summary["current_stage"] = None


def run_transaction(
    *,
    repo_root: Path,
    evidence_root: Path,
    llama_cpp_root: Path,
    artifact_path: Path,
    timeout_seconds: float,
) -> int:
    if timeout_seconds <= 0:
        raise PhysicalTransactionError(
            "timeout_seconds must be positive"
        )

    evidence_root = _prepare_evidence_root(evidence_root)
    summary_path = evidence_root / "summary.json"
    summary = _initial_summary(
        repo_root=repo_root,
        evidence_root=evidence_root,
        llama_cpp_root=llama_cpp_root,
        artifact_path=artifact_path,
    )
    _write_json(summary_path, summary)

    process = None
    log_path = evidence_root / "llama-server.log"

    try:
        stage = "repo_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        head, tree = _require_clean_repo(repo_root)
        summary["git"] = {"head": head, "tree": tree}
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "llama_preflight"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        _require_llama_cpp_paths(llama_cpp_root, server_binary)
        if not _port_is_free(DEFAULT_HOST, DEFAULT_PORT):
            raise PhysicalTransactionError(
                "127.0.0.1:1234 is already occupied"
            )
        revision = _collect_llama_revision(llama_cpp_root)
        version_identity = _collect_server_version(server_binary)
        artifact_sha256 = _verify_artifact(artifact_path)
        summary["gpu_identity"] = _collect_gpu_identity()
        summary["llama_cpp"] = {
            **version_identity,
            "revision": revision,
            "artifact_sha256": artifact_sha256,
            "expected_artifact_sha256": EXPECTED_GGUF_SHA256,
        }
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "dry_run"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        dry_output = evidence_root / "dry-run.json"
        dry_command = _experiment_command(
            endpoint=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/v1/chat/completions",
            model="dry-run",
            timeout=timeout_seconds,
            output_path=dry_output,
            run=False,
        )
        returncode = _run_probe_command(
            dry_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "dry-run.stdout.txt",
            stderr_path=evidence_root / "dry-run.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        if returncode != 0:
            raise PhysicalTransactionError(
                f"dry run exited with code {returncode}"
            )
        dry_payload = _load_json(dry_output)
        if (
            not isinstance(dry_payload, dict)
            or dry_payload.get("measured_episode_count") != 48
        ):
            raise PhysicalTransactionError(
                "dry-run schedule is invalid"
            )
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "server"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        command = _server_command(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=DEFAULT_PORT,
            log_path=log_path,
        )
        summary["server_command"] = command
        origin = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
        ready_started = time.perf_counter()
        process = _start_server(command)
        _wait_until_ready(process, origin)
        ready_elapsed_seconds = time.perf_counter() - ready_started
        attestation = _probe_and_attest(
            origin=origin,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            llama_identity={
                **version_identity,
                "revision": revision,
            },
        )
        attested = attestation.get("attested")
        if not isinstance(attested, dict):
            raise PhysicalTransactionError(
                "llama.cpp attestation is missing"
            )
        request_model = attested.get("requestModel")
        if not isinstance(request_model, str) or not request_model:
            raise PhysicalTransactionError(
                "attested request model is missing"
            )
        summary["server"] = {
            "ready_elapsed_seconds": ready_elapsed_seconds,
            "gpu_memory_used_mib_ready": _gpu_memory_used_mib(),
            "attestation": attestation,
        }
        _complete_stage(summary, stage)
        _write_json(summary_path, summary)

        stage = "actual_model"
        summary["current_stage"] = stage
        _write_json(summary_path, summary)
        actual_output = evidence_root / "actual-model.json"
        actual_command = _experiment_command(
            endpoint=f"{origin}/v1/chat/completions",
            model=request_model,
            timeout=timeout_seconds,
            output_path=actual_output,
            run=True,
        )
        summary["actual_command"] = actual_command
        returncode = _run_probe_command(
            actual_command,
            repo_root=repo_root,
            stdout_path=evidence_root / "actual-model.stdout.txt",
            stderr_path=evidence_root / "actual-model.stderr.txt",
            timeout_seconds=timeout_seconds,
        )
        summary["actual_returncode"] = returncode
        if returncode != 0:
            raise PhysicalTransactionError(
                f"actual model run exited with code {returncode}"
            )
        payload = _load_json(actual_output)
        summary["observation"] = validate_payload(payload)
        summary["server"]["gpu_memory_used_mib_after_calls"] = (
            _gpu_memory_used_mib()
        )
        _complete_stage(summary, stage)

        summary["status"] = "GEMMA_SKILL_NARROWING_PASS"
        summary["non_claims"] = [
            "PASS means a structurally valid matched physical trace was recorded.",
            "Cost interpretation remains conditional on preserved useful outcome.",
            "Pretrained narrowing evidence is not experience-dependent crystallization.",
            "No Action authorization or World truth follows from model output.",
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

    finally:
        if process is not None:
            exit_code = _terminate_owned_process(process)
            summary["server_cleanup"] = {
                "terminated": True,
                "exit_code": exit_code,
            }
            _write_json(summary_path, summary)
