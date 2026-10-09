"""S57: opt-in owned llama-server process lifecycle around S56 physical gate.

No inherited local service, fake responder, implicit GGUF selection or remote
fallback. This instrument records process/command provenance; an owned launch
and healthy HTTP alone cannot prove hardware placement or GPU memory release.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.s55_local_model_probe import hash_gguf
from adapters.mineflayer.s56_real_model_world_ci import qualify as qualify_world


class OwnedBackendRejected(ValueError):
    """Fail closed when exact local process admission is not established."""


def sha256_file(path: Path) -> str:
    if not isinstance(path, Path) or not path.is_file():
        raise OwnedBackendRejected("readable local binary required")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class OwnedBackendSpec:
    binary: Path
    gguf: Path
    binary_sha256: str
    gguf_sha256: str
    alias: str
    port: int = 12345
    gpu_layers: int = 0
    ctx_size: int = 4352
    inference_parallel: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.binary, Path)
            or not isinstance(self.gguf, Path)
            or not self.binary.is_file()
            or not os.access(self.binary, os.X_OK)
            or not self.gguf.is_file()
            or self.gguf.suffix.lower() != ".gguf"
            or not isinstance(self.alias, str)
            or not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,160}", self.alias)
            or type(self.port) is not int or not 1025 <= self.port <= 65535
            or type(self.gpu_layers) is not int or not 0 <= self.gpu_layers <= 120
            or type(self.ctx_size) is not int or not 512 <= self.ctx_size <= 32768
            or type(self.inference_parallel) is not int
            or self.inference_parallel != 1
            or not isinstance(self.binary_sha256, str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", self.binary_sha256)
            or not isinstance(self.gguf_sha256, str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", self.gguf_sha256)
        ):
            raise OwnedBackendRejected("exact single-model localhost server spec required")

    def validate_files(self) -> tuple[str, str]:
        binary_digest = sha256_file(self.binary)
        model_receipt = hash_gguf(self.gguf, self.gguf_sha256)
        if binary_digest != self.binary_sha256.lower():
            raise OwnedBackendRejected("llama-server binary SHA256 mismatch")
        model_digest = model_receipt["file_sha256"]
        if not isinstance(model_digest, str):
            raise OwnedBackendRejected("GGUF bytes not independently hashed")
        return binary_digest, model_digest

    def argv(self) -> tuple[str, ...]:
        return (
            str(self.binary.resolve()),
            "--model", str(self.gguf.resolve()),
            "--alias", self.alias,
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--ctx-size", str(self.ctx_size),
            "--parallel", str(self.inference_parallel),
            "--n-gpu-layers", str(self.gpu_layers),
        )

    def public_config(self) -> dict[str, object]:
        return {
            "backend_type": "llama.cpp llama-server",
            "alias": self.alias,
            "bound_host": "127.0.0.1",
            "bound_port": self.port,
            "gpu_layers_requested": self.gpu_layers,
            "ctx_size": self.ctx_size,
            "parallel_slots": 1,
            "model_file_path_published": False,
            "binary_file_path_published": False,
        }


def preflight_available_port(port: int) -> None:
    if type(port) is not int or not 1025 <= port <= 65535:
        raise OwnedBackendRejected("invalid user-local port")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            sock.bind(("127.0.0.1", port))
    except OSError as exc:
        raise OwnedBackendRejected("owned loopback port unavailable") from exc


def backend_environment() -> dict[str, str]:
    """Minimal process environment; never forward API tokens or model overrides."""
    allowed = {
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ", "LD_LIBRARY_PATH",
        "CUDA_VISIBLE_DEVICES", "CUDA_PATH", "CUDA_HOME",
        "NVIDIA_VISIBLE_DEVICES", "XDG_CACHE_HOME", "OMP_NUM_THREADS",
        "TMPDIR", "TMP", "TEMP",
    }
    return {key: value for key, value in os.environ.items() if key in allowed}


class _NoHealthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def backend_ready(port: int, process: subprocess.Popen[bytes], *,
                  timeout_s: float = 90) -> None:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoHealthRedirect(),
    )
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OwnedBackendRejected("owned llama-server exited before health check")
        try:
            with opener.open(url, timeout=2) as response:
                if response.status != 200 or response.geturl() != url:
                    raise OwnedBackendRejected("health was redirected or unhealthy")
                data = response.read(8193)
                if len(data) > 8192:
                    raise OwnedBackendRejected("unbounded backend health payload")
                try:
                    payload = json.loads(data)
                except (ValueError, TypeError) as exc:
                    raise OwnedBackendRejected("invalid backend health body") from exc
                if isinstance(payload, dict) and payload.get("status") == "ok":
                    return
        except urllib.error.HTTPError as exc:
            if exc.code not in (503, 404):
                raise OwnedBackendRejected("backend health returned failure") from exc
        except urllib.error.URLError:
            pass
        time.sleep(0.25)
    raise OwnedBackendRejected("owned backend never became healthy")


def terminate_owned_process(process: subprocess.Popen[bytes]) -> int | None:
    if process.poll() is not None:
        return process.returncode
    try:
        # Never send a signal to an unowned PID. Process group was created
        # by our own Popen(start_new_session=True).
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return process.poll()
    try:
        return process.wait(timeout=12)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        return process.wait(timeout=6)


async def run_owned_world(spec: OwnedBackendSpec, *,
                          report_file: Path, server_log: Path,
                          backend_log: Path,
                          timeout_s: float = 100) -> int:
    receipt: dict[str, object] = {
        "milestone": "S57", "status": "BLOCKED",
        "classification": "OWNED_LOCAL_BACKEND_PHYSICAL_QUALIFICATION_PENDING",
        "owned_backend_started": False,
        "owned_backend_healthy": False,
        "backend_model_loaded_independently_attested": False,
        "gpu_actual_placement_measured": False,
        "gpu_vram_release_measured": False,
        "native_world_actual_model_overlap_pass": False,
    }
    proc: subprocess.Popen[bytes] | None = None
    code = 2
    try:
        if os.environ.get("S57_ALLOW_OWNED_BACKEND") != "1":
            raise OwnedBackendRejected("explicit S57_ALLOW_OWNED_BACKEND=1 required")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise OwnedBackendRejected("GitHub Actions has no user-local model authority")
        if not isinstance(spec, OwnedBackendSpec):
            raise OwnedBackendRejected("explicit immutable spec required")
        binary_sha, model_sha = await asyncio.to_thread(spec.validate_files)
        receipt["binary_sha256"] = binary_sha
        receipt["gguf_sha256"] = model_sha
        receipt["configuration"] = spec.public_config()
        preflight_available_port(spec.port)
        backend_log.parent.mkdir(parents=True, exist_ok=True)
        with backend_log.open("wb") as sink:
            proc = subprocess.Popen(
                spec.argv(), stdin=subprocess.DEVNULL, stdout=sink,
                stderr=subprocess.STDOUT, env=backend_environment(),
                start_new_session=True,
            )
        receipt["backend_pid"] = proc.pid
        receipt["owned_backend_started"] = True
        await asyncio.to_thread(backend_ready, spec.port, proc)
        if proc.poll() is not None:
            raise OwnedBackendRejected("backend exited after health preflight")
        receipt["owned_backend_healthy"] = True
        # S56 owns ALL native World, supervisor, strict physical OUTCOME and
        # stale L2 fencing semantics. No fake provider is installed.
        previous = os.environ.get("S56_LOCAL_REAL_MODEL")
        os.environ["S56_LOCAL_REAL_MODEL"] = "1"
        try:
            inner_report = report_file.with_name("s56-physical-same-run.json")
            result_code = await qualify_world(
                inner_report, server_log, model=spec.alias,
                endpoint=f"http://127.0.0.1:{spec.port}/v1/chat/completions",
                gguf=spec.gguf, expected_sha256=spec.gguf_sha256,
                timeout_s=timeout_s, max_tokens=768,
            )
        finally:
            if previous is None:
                os.environ.pop("S56_LOCAL_REAL_MODEL", None)
            else:
                os.environ["S56_LOCAL_REAL_MODEL"] = previous
        receipt["s56_report_generated"] = inner_report.is_file()
        receipt["s56_exit_code"] = result_code
        receipt["native_world_actual_model_overlap_pass"] = result_code == 0
        if result_code != 0:
            receipt["classification"] = "OWNED_BACKEND_WORLD_MODEL_GATE_NOT_QUALIFIED"
            code = result_code
        else:
            receipt["status"] = "PASS"
            receipt["classification"] = (
                "OWNED_LLAMA_SERVER_AND_REAL_MINECRAFT_OVERLAP_"
                "BACKEND_LOAD_AND_GPU_UNVERIFIED"
            )
            code = 0
    except (OSError, ValueError) as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["status"] = "BLOCKED" if isinstance(exc, OwnedBackendRejected) else "FAIL"
        code = 2 if isinstance(exc, OwnedBackendRejected) else 1
    finally:
        if proc is not None:
            receipt["backend_process_exit_code"] = await asyncio.to_thread(
                terminate_owned_process, proc,
            )
            receipt["backend_process_terminated"] = proc.poll() is not None
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        print("S57_REPORT=" + json.dumps(receipt, sort_keys=True))
    return code


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--llama-server", type=Path, required=True)
    p.add_argument("--binary-sha256", required=True)
    p.add_argument("--gguf", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--model-alias", required=True)
    p.add_argument("--port", type=int, default=12345)
    p.add_argument("--gpu-layers", type=int, default=0)
    p.add_argument("--ctx-size", type=int, default=4352)
    p.add_argument("--timeout-s", type=float, default=100)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--backend-log", type=Path, required=True)
    args = p.parse_args()
    try:
        spec = OwnedBackendSpec(
            args.llama_server, args.gguf, args.binary_sha256,
            args.expected_sha256, args.model_alias,
            port=args.port, gpu_layers=args.gpu_layers, ctx_size=args.ctx_size,
        )
    except (ValueError, OSError) as exc:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({
            "milestone": "S57", "status": "BLOCKED",
            "classification": "INVALID_OWNED_BACKEND_SPEC",
            "error_type": type(exc).__name__,
        }, sort_keys=True, indent=2) + "\n")
        return 2
    return asyncio.run(run_owned_world(
        spec, report_file=args.report, server_log=args.server_log,
        backend_log=args.backend_log, timeout_s=args.timeout_s,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
