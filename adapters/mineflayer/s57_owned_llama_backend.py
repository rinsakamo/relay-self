"""S57: opt-in owned llama-server process lifecycle around S56 physical gate.

No inherited local service, fake responder, implicit GGUF selection or remote
fallback. This instrument records process/command provenance; an owned launch
and healthy HTTP alone cannot prove hardware placement or GPU memory release.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path

from adapters.llama_cpp.owned_backend import (
    OwnedBackendRejected as OwnedBackendRejected,
)
from adapters.llama_cpp.owned_backend import (
    OwnedBackendSpec as OwnedBackendSpec,
)
from adapters.llama_cpp.owned_backend import (
    backend_environment as backend_environment,
)
from adapters.llama_cpp.owned_backend import (
    backend_ready as backend_ready,
)
from adapters.llama_cpp.owned_backend import (
    preflight_available_port as preflight_available_port,
)
from adapters.llama_cpp.owned_backend import (
    sha256_file as sha256_file,
)
from adapters.llama_cpp.owned_backend import (
    terminate_owned_process as terminate_owned_process,
)
from adapters.mineflayer.s56_real_model_world_ci import qualify as qualify_world


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
            try:
                receipt["backend_process_exit_code"] = await asyncio.to_thread(
                    terminate_owned_process, proc,
                )
                receipt["backend_process_terminated"] = proc.poll() is not None
            except (OSError, subprocess.TimeoutExpired) as exc:
                receipt["backend_process_terminated"] = False
                receipt["backend_cleanup_error_type"] = type(exc).__name__
            if not receipt.get("backend_process_terminated", False):
                receipt["status"] = "FAIL"
                receipt["classification"] = "OWNED_BACKEND_TERMINATION_UNVERIFIED"
                code = 1
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
