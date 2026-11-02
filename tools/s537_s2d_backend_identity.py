"""DEV-only local owned llama-server identity preflight, without model calls.

Verifies the same-user live Linux process, exact executable/model file
hashes and a bounded request-compatible command line. This does not certify
model load, CUDA placement, backend STOP, or independent process custody.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


class BackendIdentityRejected(ValueError):
    """Original process identity or runtime arguments cannot be established."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(buf)
    return digest.hexdigest()


def verify_local_backend(
    *, pid: int, binary: Path, gguf: Path, binary_sha256: str,
    gguf_sha256: str, alias: str, port: int,
) -> dict[str, object]:
    if (
        type(pid) is not int or pid <= 1
        or type(port) is not int or not 1025 <= port <= 65535
        or not isinstance(binary, Path) or not isinstance(gguf, Path)
        or not binary.is_file() or not gguf.is_file()
        or binary.is_symlink() or gguf.is_symlink()
        or not isinstance(alias, str) or not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,160}", alias)
        or not isinstance(binary_sha256, str)
        or not isinstance(gguf_sha256, str)
        or not re.fullmatch("[a-fA-F0-9]{64}", binary_sha256)
        or not re.fullmatch("[a-fA-F0-9]{64}", gguf_sha256)
    ):
        raise BackendIdentityRejected("exact local backend arguments required")
    proc = Path("/proc") / str(pid)
    try:
        status = (proc / "status").read_text(encoding="utf-8")
        uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
        uids = [int(x) for x in uid_line.split()[1:]]
        raw = (proc / "cmdline").read_bytes()
        argv = [token.decode("utf-8", errors="strict") for token in raw.split(b"\x00") if token]
        exe = (proc / "exe").resolve(strict=True)
    except (OSError, ValueError, StopIteration, UnicodeError) as exc:
        raise BackendIdentityRejected("live Linux process source unavailable") from exc
    if (
        len(uids) != 4 or uids[0] != os.getuid()
        or exe != binary.resolve(strict=True)
        or len(argv) < 9
        or Path(argv[0]).resolve() != exe
    ):
        raise BackendIdentityRejected("owner or binary executable not verified")

    def opt(*names: str) -> str:
        values = [argv[i + 1] for i, key in enumerate(argv[:-1]) if key in names]
        if len(values) != 1:
            raise BackendIdentityRejected("missing/duplicate owned runtime argument")
        return values[0]

    if (
        Path(opt("--model", "-m")).resolve(strict=True) != gguf.resolve(strict=True)
        or opt("--alias") != alias
        or opt("--host") != "127.0.0.1"
        or int(opt("--port")) != port
        or int(opt("--ctx-size", "-c")) != 8192
        or int(opt("--parallel", "-np")) != 1
        or opt("--reasoning", "-rea") != "off"
    ):
        raise BackendIdentityRejected("wrong model mapping, slot or reasoning setting")
    if _sha256(binary) != binary_sha256.lower() or _sha256(gguf) != gguf_sha256.lower():
        raise BackendIdentityRejected("live binary/GGUF hash mismatch")
    # Re-check PID/executable after expensive hashing; does not grant ownership
    # over external provider/model lifecycle or claim a live GPU allocation.
    try:
        if (proc / "exe").resolve(strict=True) != exe or (proc / "cmdline").read_bytes() != raw:
            raise BackendIdentityRejected("backend PID reused or arguments changed")
    except OSError as exc:
        raise BackendIdentityRejected("backend exited during preflight") from exc
    return {
        "schema": "S537_S2D_LOCAL_BACKEND_IDENTITY_DEV_V1",
        "status": "PROCESS_FILE_HASH_AND_ARGUMENTS_MATCH",
        "pid": pid,
        "binary_sha256": binary_sha256.lower(),
        "gguf_sha256": gguf_sha256.lower(),
        "alias": alias,
        "port": port,
        "context": 8192,
        "slots": 1,
        "reasoning_off_runtime_argument_observed": True,
        "request_schema_validation_proven": False,
        "loaded_model_mapping_independently_attested": False,
        "gpu_placement_attested": False,
        "backend_stop_ack": False,
    }
