"""Product/S model-only process primitives, extracted from S57. No World imports."""
from __future__ import annotations

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

from adapters.llama_cpp.owned_artifacts import hash_gguf


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
    if os.getpgid(process.pid) != process.pid:
        raise OwnedBackendRejected("owned process-group identity mismatch")
    try:
        # Never send a signal to an unowned PID. Process group was created
        # by our own Popen(start_new_session=True).
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return process.wait(timeout=6)
    try:
        return process.wait(timeout=12)
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            if os.getpgid(process.pid) != process.pid:
                raise OwnedBackendRejected("owned process-group identity mismatch")
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return process.wait(timeout=6)

