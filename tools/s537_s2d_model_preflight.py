"""S2-D model identity preflight for an already-running user-owned llama-server.

This read-only guard runs BEFORE any World/model call. It proves an explicit
PID, executable, GGUF bytes on disk, and startup arguments agree, not that
the backend has finished loading the weights, GPU mapped them, or stopped.
No process launch, socket request or process termination.
"""
from __future__ import annotations

import os
from pathlib import Path

from adapters.mineflayer.s57_owned_llama_backend import (
    OwnedBackendRejected,
    OwnedBackendSpec,
)


class S2DPreflightRejected(ValueError):
    """Local model source was not established from independent OS evidence."""


def _flag_value(argv: tuple[str, ...], flag: str) -> str:
    occurrences = [
        argv[i + 1] for i in range(len(argv) - 1) if argv[i] == flag
    ]
    if len(occurrences) != 1:
        raise S2DPreflightRejected(f"exactly one {flag} argument required")
    return occurrences[0]


def verify_owned_argv(
    argv: tuple[str, ...], spec: OwnedBackendSpec, *,
    running_exe: Path, same_user: bool,
) -> None:
    """Fail closed on duplicate/missing backend flags or fake reasoning-off."""
    if (
        not isinstance(spec, OwnedBackendSpec)
        or not argv or len(argv) > 256
        or not same_user
        or not isinstance(running_exe, Path)
        or running_exe.resolve() != spec.binary.resolve()
        or Path(argv[0]).resolve() != spec.binary.resolve()
    ):
        raise S2DPreflightRejected("actual executable/UID source mismatch")
    try:
        required = {
            "--model": str(spec.gguf.resolve()),
            "--alias": spec.alias,
            "--host": "127.0.0.1",
            "--port": str(spec.port),
            "--ctx-size": "8192",
            "--parallel": "1",
        }
        for flag, expected in required.items():
            actual = _flag_value(argv, flag)
            if flag == "--model":
                if Path(actual).resolve() != spec.gguf.resolve():
                    raise S2DPreflightRejected("GGUF process argument mismatch")
            elif actual != expected:
                raise S2DPreflightRejected(f"{flag} argument mismatch")
        # --reasoning-format none is NOT reasoning off.
        if "--reasoning" in argv and "-rea" in argv:
            raise S2DPreflightRejected("duplicate reasoning controls")
        flag = "--reasoning" if "--reasoning" in argv else "-rea"
        if _flag_value(argv, flag) != "off":
            raise S2DPreflightRejected("explicit --reasoning off required")
        if "--reasoning-format" in argv and (
            _flag_value(argv, "--reasoning-format") not in
            ("none", "auto", "deepseek", "deepseek-legacy")
        ):
            raise S2DPreflightRejected("unsupported reasoning format")
        if _flag_value(argv, "--n-gpu-layers") != str(spec.gpu_layers):
            raise S2DPreflightRejected("GPU layer config mismatch")
    except (ValueError, OSError) as exc:
        raise S2DPreflightRejected("exact running backend arguments rejected") from exc


def verify_running_backend(
    spec: OwnedBackendSpec, *, pid: int,
) -> dict[str, object]:
    """Read/prove current same-user /proc process, then hash both files."""
    if (
        type(pid) is not int or pid <= 1
        or not isinstance(spec, OwnedBackendSpec)
        or spec.ctx_size != 8192
        or spec.inference_parallel != 1
    ):
        raise S2DPreflightRejected("backend PID or context budget invalid")
    root = Path("/proc") / str(pid)
    try:
        if not root.is_dir():
            raise S2DPreflightRejected("backend PID not running")
        raw = (root / "cmdline").read_bytes()
        if not raw or len(raw) > 16384 or not raw.endswith(b"\0"):
            raise S2DPreflightRejected("owned process argv unavailable")
        argv = tuple(part.decode("utf-8") for part in raw[:-1].split(b"\0"))
        status = (root / "status").read_text(encoding="utf-8")
        uids = [
            line.split()[1:] for line in status.splitlines()
            if line.startswith("Uid:")
        ]
        if len(uids) != 1 or not uids[0]:
            raise S2DPreflightRejected("backend UID unavailable")
        uid = int(uids[0][0])
        running_exe = (root / "exe").resolve(strict=True)
        verify_owned_argv(
            argv, spec, running_exe=running_exe,
            same_user=(uid == os.geteuid()),
        )
        binary_sha, gguf_sha = spec.validate_files()
        if not root.is_dir() or (root / "exe").resolve(strict=True) != running_exe:
            raise S2DPreflightRejected("backend PID/source advanced")
        if (root / "cmdline").read_bytes() != raw:
            raise S2DPreflightRejected("backend argv changed during preflight")
    except (OSError, UnicodeError, OwnedBackendRejected, ValueError) as exc:
        raise S2DPreflightRejected("backend process identity not verified") from exc
    return {
        "schema": "S537_S2D_OWNED_MODEL_ARGV_PREWORLD_DEV_V1",
        "status": "ARGUMENTS_AND_ARTIFACT_BYTES_VERIFIED",
        "model_pid": pid,
        "binary_sha256": binary_sha,
        "gguf_sha256": gguf_sha,
        "alias": spec.alias,
        "port": spec.port,
        "context_size": 8192,
        "slot_count": 1,
        "reasoning_off_argv_verified": True,
        "model_process_argv_verified": True,
        "strict_json_requested": True,
        "actual_model_completion_verified": False,
        "model_gpu_mapping_attested": False,
        "backend_stop_ack": False,
    }
