from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import experiments.mineflayer_cognition_ab as cognition

FORMAT_VERSION = 1
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 1234
DEFAULT_CONTEXT = 8192
DEFAULT_SLOTS = 1
DEFAULT_REPEATS = 20
DEFAULT_REQUEST_TIMEOUT = 600.0
READY_TIMEOUT_SECONDS = 120.0
READY_POLL_SECONDS = 0.5
EXPECTED_GGUF_SHA256 = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_TARGET_QUANTIZATION = "Q4_K_M"
_MODEL_FTYPE_TARGET_QUANTIZATION_EQUIVALENCE = {
    "Q4_K - Medium": "Q4_K_M",
}


class PhysicalTransactionError(RuntimeError):
    """The bounded llama.cpp cognition transaction cannot proceed truthfully."""


def _begin_stage(summary: dict[str, object], stage: str) -> None:
    summary["currentStage"] = stage


def _complete_stage(summary: dict[str, object], stage: str) -> None:
    completed = summary.get("completedStages")
    if not isinstance(completed, list):
        raise AssertionError("completedStages must be a list")
    completed.append(stage)
    summary["currentStage"] = None


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise PhysicalTransactionError(
            f"command could not start: {shlex.join(command)}: {type(exc).__name__}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PhysicalTransactionError(
            f"command failed ({completed.returncode}): {shlex.join(command)}: {detail}"
        )
    return completed.stdout or completed.stderr


def _require_clean_repo(repo_root: Path) -> tuple[str, str]:
    if not (repo_root / ".git").exists():
        raise PhysicalTransactionError(f"repo-root is not a git checkout: {repo_root}")
    status = _run_text(["git", "status", "--porcelain"], cwd=repo_root)
    if status.strip():
        raise PhysicalTransactionError("physical transaction requires a clean RelaySelf checkout")
    head = _run_text(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    tree = _run_text(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root).strip()
    return head, tree


def _port_is_free(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _require_llama_cpp_paths(llama_cpp_root: Path, server_binary: Path) -> None:
    if not server_binary.is_file() or not os.access(server_binary, os.X_OK):
        raise PhysicalTransactionError(f"llama-server is not executable: {server_binary}")
    if not (llama_cpp_root / ".git").exists():
        raise PhysicalTransactionError(f"llama.cpp root is not a git checkout: {llama_cpp_root}")


def _collect_llama_revision(llama_cpp_root: Path) -> str:
    revision = _run_text(["git", "rev-parse", "HEAD"], cwd=llama_cpp_root).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise PhysicalTransactionError("llama.cpp revision is not a lowercase 40-hex commit")
    return revision


def _collect_server_version(server_binary: Path) -> dict[str, object]:
    version = _run_text([str(server_binary), "--version"]).strip()
    match = re.search(r"\bbuild\s+(\d+)\b", version)
    if match is None:
        raise PhysicalTransactionError("could not parse llama-server build number from --version")
    return {"version": version, "buildNumber": int(match.group(1))}


def _verify_artifact(artifact_path: Path) -> str:
    if not artifact_path.is_file():
        raise PhysicalTransactionError(f"pinned GGUF is not a file: {artifact_path}")
    artifact_sha256 = _sha256_file(artifact_path)
    if artifact_sha256 != EXPECTED_GGUF_SHA256:
        raise PhysicalTransactionError("GGUF sha256 does not match the pinned v1 target")
    return artifact_sha256


def _collect_gpu_identity() -> str:
    output = _run_text(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader",
        ]
    ).strip()
    if not output:
        raise PhysicalTransactionError("nvidia-smi returned no GPU identity")
    return output


def _server_command(
    *, server_binary: Path, artifact_path: Path, port: int, log_path: Path
) -> list[str]:
    return [
        str(server_binary),
        "-m",
        str(artifact_path),
        "--host",
        DEFAULT_HOST,
        "--port",
        str(port),
        "-ngl",
        "999",
        "-c",
        str(DEFAULT_CONTEXT),
        "-np",
        str(DEFAULT_SLOTS),
        "--no-context-shift",
        "-lv",
        "4",
        "--log-timestamps",
        "--log-file",
        str(log_path),
    ]


def _start_server(command: list[str]) -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError as exc:
        raise PhysicalTransactionError(f"failed to launch transaction-owned llama-server: {exc}") from exc


def _get_json(url: str, *, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PhysicalTransactionError(f"GET {url} failed: {exc}") from exc


def _wait_until_ready(process: subprocess.Popen[str], origin: str) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise PhysicalTransactionError(
                f"transaction-owned llama-server exited before readiness: {process.returncode}"
            )
        try:
            health = _get_json(f"{origin}/health", timeout=5.0)
            if isinstance(health, dict) and health.get("status") == "ok":
                return
        except PhysicalTransactionError as exc:
            last_error = exc
        time.sleep(READY_POLL_SECONDS)
    detail = f": {last_error}" if last_error else ""
    raise PhysicalTransactionError(f"transaction-owned llama-server did not become ready{detail}")


def _model_ids(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise PhysicalTransactionError("llama-server /v1/models response is invalid")
    result: list[str] = []
    for item in payload["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]:
            result.append(item["id"])
    return result


def _model_ftype_matches_target_quantization(
    *, model_ftype: object, target_quantization: str
) -> bool:
    if model_ftype == target_quantization:
        return True
    if not isinstance(model_ftype, str):
        return False
    return (
        _MODEL_FTYPE_TARGET_QUANTIZATION_EQUIVALENCE.get(model_ftype)
        == target_quantization
    )


def attest_runtime(
    *,
    health: object,
    models: object,
    props: object,
    slots: object,
    artifact_path: Path,
    artifact_sha256: str,
    llama_identity: dict[str, object],
) -> dict[str, object]:
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise PhysicalTransactionError("llama-server /health is not ready")
    model_ids = _model_ids(models)
    if len(model_ids) != 1:
        raise PhysicalTransactionError("single-model transaction requires exactly one /v1/models id")
    if not isinstance(props, dict):
        raise PhysicalTransactionError("llama-server /props must return an object")
    if not isinstance(slots, list) or len(slots) != DEFAULT_SLOTS:
        raise PhysicalTransactionError("llama-server must expose exactly one /slots entry")

    build_number = llama_identity.get("buildNumber")
    revision = llama_identity.get("revision")
    build_info = props.get("build_info")
    if not isinstance(build_info, str):
        raise PhysicalTransactionError("props.build_info must be a string")
    if str(build_number) not in build_info:
        raise PhysicalTransactionError("llama-server --version build does not match /props build_info")
    if not isinstance(revision, str) or (
        revision not in build_info and revision[:7] not in build_info
    ):
        raise PhysicalTransactionError("llama.cpp git revision does not match /props build_info")

    model_alias = props.get("model_alias")
    if model_alias != model_ids[0]:
        raise PhysicalTransactionError("/props model_alias does not match /v1/models id")
    model_path = props.get("model_path")
    if not isinstance(model_path, str) or Path(model_path).resolve() != artifact_path:
        raise PhysicalTransactionError("/props model_path does not match the pinned GGUF")
    settings = props.get("default_generation_settings")
    if not isinstance(settings, dict) or settings.get("n_ctx") != DEFAULT_CONTEXT:
        raise PhysicalTransactionError("/props context does not equal 8192")
    if props.get("total_slots") != DEFAULT_SLOTS:
        raise PhysicalTransactionError("/props total_slots does not equal 1")
    slot = slots[0]
    if not isinstance(slot, dict) or slot.get("n_ctx") != DEFAULT_CONTEXT:
        raise PhysicalTransactionError("/slots context does not equal 8192")
    if slot.get("id") != 0:
        raise PhysicalTransactionError("single /slots entry must have id 0")
    model_ftype = props.get("model_ftype")
    if not _model_ftype_matches_target_quantization(
        model_ftype=model_ftype,
        target_quantization=EXPECTED_TARGET_QUANTIZATION,
    ):
        raise PhysicalTransactionError(
            "props.model_ftype does not match target quantization Q4_K_M"
        )
    chat_template = props.get("chat_template")
    if not isinstance(chat_template, str) or not chat_template:
        raise PhysicalTransactionError("props.chat_template must be a non-empty string")

    return {
        "requestModel": model_ids[0],
        "buildInfo": build_info,
        "modelAlias": model_alias,
        "modelPath": str(artifact_path),
        "modelFtype": model_ftype,
        "targetQuantization": EXPECTED_TARGET_QUANTIZATION,
        "artifactSha256": artifact_sha256,
        "chatTemplateSha256": _sha256_bytes(chat_template.encode("utf-8")),
        "context": DEFAULT_CONTEXT,
        "slots": DEFAULT_SLOTS,
        "contextShiftEnabled": False,
        "reasoningEffort": "none",
        "cachePrompt": False,
    }


def _probe_and_attest(
    *, origin: str, artifact_path: Path, artifact_sha256: str, llama_identity: dict[str, object]
) -> dict[str, object]:
    health = _get_json(f"{origin}/health", timeout=20.0)
    models = _get_json(f"{origin}/v1/models", timeout=20.0)
    props = _get_json(f"{origin}/props", timeout=20.0)
    slots = _get_json(f"{origin}/slots", timeout=20.0)
    attested = attest_runtime(
        health=health,
        models=models,
        props=props,
        slots=slots,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        llama_identity=llama_identity,
    )
    return {
        "health": health,
        "models": models,
        "props": props,
        "slots": slots,
        "attested": attested,
        "nonGenerativeRequestCount": 4,
    }


def physical_requests(model: str) -> dict[str, dict[str, object]]:
    rendered = cognition.render_ab_requests(model)
    output: dict[str, dict[str, object]] = {}
    for condition in cognition.CONDITIONS:
        request_body = copy.deepcopy(rendered[condition]["request"])
        if not isinstance(request_body, dict):
            raise AssertionError("rendered request must be an object")
        request_body["reasoning_effort"] = "none"
        request_body["cache_prompt"] = False
        output[condition] = {
            "request": request_body,
            "requestHash": _sha256_bytes(_canonical_json(request_body).encode("utf-8")),
        }
    return output


def planned_request_ledger(model: str, repeats: int) -> list[dict[str, object]]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    rendered = physical_requests(model)
    rows: list[dict[str, object]] = []
    conditions = tuple(cognition.CONDITIONS)
    for trial in range(repeats):
        ordered = conditions if trial % 2 == 0 else tuple(reversed(conditions))
        for order_index, condition in enumerate(ordered):
            bundle = rendered[condition]
            rows.append(
                {
                    "trial": trial,
                    "orderIndex": order_index,
                    "condition": condition,
                    "requestHash": bundle["requestHash"],
                    "request": bundle["request"],
                }
            )
    return rows


def execute_cognition(
    *, endpoint: str, model: str, repeats: int, timeout: float
) -> dict[str, object]:
    planned = planned_request_ledger(model, repeats)
    records: list[dict[str, object]] = []
    for item in planned:
        request_body = item["request"]
        assert isinstance(request_body, dict)
        try:
            raw_text = cognition.call_openai_compatible(
                endpoint=endpoint,
                request_body=request_body,
                api_key=None,
                timeout=timeout,
            )
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            raise PhysicalTransactionError(
                f"model call failed without retry at trial {item['trial']} "
                f"condition {item['condition']}: {type(exc).__name__}: {exc}"
            ) from exc
        parsed = cognition.parse_choice(raw_text)
        records.append(
            {
                "trial": item["trial"],
                "orderIndex": item["orderIndex"],
                "condition": item["condition"],
                "model": model,
                "endpoint": cognition.endpoint_metadata(endpoint),
                "requestHash": item["requestHash"],
                "rawText": raw_text,
                "planId": parsed.plan_id,
                "parseError": parsed.error,
                "transportError": None,
            }
        )
    return {"records": records, "summary": cognition._summary(records)}


def _terminate_owned_process(process: subprocess.Popen[str]) -> int | None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)
    return process.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Own one v1-style llama.cpp lifetime for the Mineflayer cognition probe."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--llama-cpp-root", default=str(Path.home() / "src" / "llama.cpp"))
    parser.add_argument(
        "--artifact-path",
        default=str(Path.home() / "models" / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"),
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--evidence-root")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    evidence_root = (
        Path(args.evidence_root).expanduser().resolve()
        if args.evidence_root
        else Path(tempfile.mkdtemp(prefix="relay-self-mineflayer-llama-cpp-"))
    )
    if args.evidence_root:
        evidence_root.mkdir(parents=True, exist_ok=False)

    summary: dict[str, object] = {
        "formatVersion": FORMAT_VERSION,
        "disposition": None,
        "serverLaunchCount": 0,
        "modelCallCount": 0,
        "retryCount": 0,
        "replayCount": 0,
        "fallbackCount": 0,
        "repositoryMutationCount": 0,
        "evidenceRoot": str(evidence_root),
        "currentStage": "initialization",
        "completedStages": [],
    }
    process: subprocess.Popen[str] | None = None
    log_path = evidence_root / "llama-server.log"
    cleanup: dict[str, object] = {"ownedProcess": False, "terminated": False, "exitCode": None}
    exit_code = 2

    try:
        if args.repeats <= 0:
            raise PhysicalTransactionError("repeats must be positive")

        _begin_stage(summary, "clean_repo")
        head, tree = _require_clean_repo(repo_root)
        summary["relaySelf"] = {"head": head, "tree": tree}
        _complete_stage(summary, "clean_repo")

        _begin_stage(summary, "port_free")
        if args.port != DEFAULT_PORT:
            raise PhysicalTransactionError("current physical condition requires port 1234")
        if not _port_is_free(DEFAULT_HOST, args.port):
            raise PhysicalTransactionError("127.0.0.1:1234 is already occupied")
        _complete_stage(summary, "port_free")

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        _require_llama_cpp_paths(llama_cpp_root, server_binary)

        _begin_stage(summary, "llama_cpp_revision")
        revision = _collect_llama_revision(llama_cpp_root)
        _complete_stage(summary, "llama_cpp_revision")

        _begin_stage(summary, "llama_server_version")
        version_identity = _collect_server_version(server_binary)
        _complete_stage(summary, "llama_server_version")
        llama_identity = {"revision": revision, **version_identity}

        _begin_stage(summary, "gguf_verify")
        artifact_sha256 = _verify_artifact(artifact_path)
        _complete_stage(summary, "gguf_verify")

        _begin_stage(summary, "gpu_identity")
        gpu_identity = _collect_gpu_identity()
        _complete_stage(summary, "gpu_identity")

        command = _server_command(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.port,
            log_path=log_path,
        )
        binding = {
            "relaySelf": {"head": head, "tree": tree},
            "llamaCpp": llama_identity,
            "artifactPath": str(artifact_path),
            "artifactSha256": artifact_sha256,
            "launchCommand": shlex.join(command),
            "gpuIdentity": gpu_identity,
            "context": DEFAULT_CONTEXT,
            "slots": DEFAULT_SLOTS,
            "contextShiftEnabled": False,
        }

        _begin_stage(summary, "binding_write")
        _write_json(evidence_root / "binding.json", binding)
        _complete_stage(summary, "binding_write")

        _begin_stage(summary, "server_launch")
        process = _start_server(command)
        cleanup["ownedProcess"] = True
        summary["serverLaunchCount"] = 1
        summary["serverPid"] = process.pid
        _complete_stage(summary, "server_launch")

        origin = f"http://{DEFAULT_HOST}:{args.port}"
        _begin_stage(summary, "readiness")
        _wait_until_ready(process, origin)
        _complete_stage(summary, "readiness")

        _begin_stage(summary, "runtime_attestation")
        runtime = _probe_and_attest(
            origin=origin,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            llama_identity=llama_identity,
        )
        _write_json(evidence_root / "runtime-attestation.json", runtime)
        _complete_stage(summary, "runtime_attestation")

        attested = runtime["attested"]
        assert isinstance(attested, dict)
        model = attested["requestModel"]
        assert isinstance(model, str)

        _begin_stage(summary, "request_ledger")
        ledger = planned_request_ledger(model, args.repeats)
        _write_json(evidence_root / "request-ledger.json", ledger)
        summary["plannedModelCallCount"] = len(ledger)
        _complete_stage(summary, "request_ledger")

        _begin_stage(summary, "model_generation")
        result = execute_cognition(
            endpoint=f"{origin}/v1/chat/completions",
            model=model,
            repeats=args.repeats,
            timeout=args.timeout,
        )
        _complete_stage(summary, "model_generation")

        _begin_stage(summary, "result_write")
        _write_json(evidence_root / "cognition-result.json", result)
        summary["modelCallCount"] = len(result["records"])
        summary["resultSummary"] = result["summary"]
        summary["disposition"] = "COMPLETED"
        _complete_stage(summary, "result_write")
        exit_code = 0
        return exit_code
    except PhysicalTransactionError as exc:
        summary["disposition"] = "BLOCKED_OR_INVALID"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3
        return exit_code
    except Exception as exc:  # pragma: no cover - final fail-closed boundary
        summary["disposition"] = "HARNESS_INVALID"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 2
        return exit_code
    finally:
        if process is not None:
            cleanup["exitCode"] = _terminate_owned_process(process)
            cleanup["terminated"] = process.poll() is not None
        if log_path.is_file():
            cleanup["logSha256"] = _sha256_file(log_path)
        _write_json(evidence_root / "cleanup.json", cleanup)
        completed = summary.get("completedStages")
        if isinstance(completed, list):
            completed.append("cleanup")
        summary["transactionExitCode"] = exit_code
        summary["cleanup"] = cleanup
        _write_json(evidence_root / "transaction-summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
