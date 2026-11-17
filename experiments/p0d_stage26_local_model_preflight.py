"""Stage26 original llama-server pre-World read-only owner source audit.

Never starts/stops model processes, sends inference, starts Paper or asserts
GPU-wide exclusivity. It proves only a bounded process/model/port/slot source.
Windows WDDM desktop activity is informational, not a compute-conflict proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit


class Stage26ModelPreflightHold(RuntimeError):
    """A dedicated model-server source is not independently attributable."""


@dataclass(frozen=True, slots=True)
class Stage26OwnedModelSource:
    classification: str
    linux_pid: int
    executable_realpath: str
    executable_sha256: str
    gguf_realpath: str
    gguf_sha256: str
    argv: tuple[str, ...]
    context_size: int
    n_parallel: int
    gpu_layers: int
    endpoint: str
    owned_listener_inode: str
    slots_raw_sha256: str
    slots_id: int
    slots_processing: bool
    windows_gpu_snapshot_sha256: str | None
    gpu_wide_exclusivity_attested: bool = False
    gpu_capacity_attested: bool = False
    external_client_absence_attested: bool = False
    physical_action_authorized: bool = False
    world_trial_consumed: bool = False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for part in iter(lambda: src.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _argv_value(argv: tuple[str, ...], *flags: str) -> str:
    """Support spaced, --flag=value and compact -np1/-c8192 forms."""
    values: list[str] = []
    for idx, word in enumerate(argv):
        for flag in flags:
            if word == flag:
                if idx + 1 >= len(argv):
                    raise Stage26ModelPreflightHold(f"model argv flag {flag} has no value")
                values.append(argv[idx + 1])
            elif word.startswith(flag + "="):
                values.append(word[len(flag) + 1:])
            elif flag in ("-np", "-c", "-ngl") and word.startswith(flag):
                raw = word[len(flag):]
                if raw and raw.isdecimal():
                    values.append(raw)
    if len(values) != 1 or not values[0]:
        raise Stage26ModelPreflightHold(
            "exactly one unambiguous required llama-server argv flag missing"
        )
    return values[0]


def _owned_loopback_socket_inode(
    pid: int, port: int, *, proc_root: Path,
) -> str:
    # /proc/net/tcp uses little-endian IPv4: 0100007F == 127.0.0.1.
    rows = (proc_root / "net" / "tcp").read_text().splitlines()[1:]
    listeners = set()
    for row in rows:
        fields = row.split()
        if len(fields) < 10 or fields[3] != "0A":
            continue
        host, sep, port_hex = fields[1].partition(":")
        if sep and host == "0100007F" and int(port_hex, 16) == port:
            listeners.add(fields[9])
    if len(listeners) != 1:
        raise Stage26ModelPreflightHold(
            "exactly one IPv4 127.0.0.1 LISTEN socket not independently established"
        )
    inode = next(iter(listeners))
    handles = (proc_root / str(pid) / "fd").iterdir()
    matched = 0
    for handle in handles:
        try:
            if os.readlink(handle) == f"socket:[{inode}]":
                matched += 1
        except (OSError, ValueError):
            pass
    if matched < 1:
        raise Stage26ModelPreflightHold(
            "server PID does not own exact TCP loopback listener inode"
        )
    return inode


def inspect_stage26_model_source(
    *, pid: int, endpoint: str, executable: Path,
    executable_sha256: str, gguf: Path, gguf_sha256: str,
    proc_root: Path = Path("/proc"),
    windows_gpu_snapshot: Path | None = None,
) -> Stage26OwnedModelSource:
    """Read only source evidence; no claims about other WDDM GUI processes."""
    if type(pid) is not int or pid < 1:
        raise Stage26ModelPreflightHold("positive owned linux PID required")
    url = urlsplit(endpoint)
    if (
        url.scheme != "http" or url.hostname != "127.0.0.1"
        or url.port is None or url.port < 1024
        or url.path != "/v1/chat/completions"
        or url.username is not None or url.password is not None
        or url.query or url.fragment
    ):
        raise Stage26ModelPreflightHold(
            "explicit 127.0.0.1:port/v1/chat/completions endpoint required"
        )
    if (
        len(executable_sha256) != 64 or len(gguf_sha256) != 64
        or not all(c in "0123456789abcdef" for c in executable_sha256)
        or not all(c in "0123456789abcdef" for c in gguf_sha256)
    ):
        raise Stage26ModelPreflightHold("exact expected binary/model SHA256 required")
    try:
        owned_exe = (proc_root / str(pid) / "exe").resolve(strict=True)
        expected_exe = executable.resolve(strict=True)
        model_file = gguf.resolve(strict=True)
        argv_bytes = (proc_root / str(pid) / "cmdline").read_bytes()
        if not argv_bytes.endswith(b"\x00"):
            raise Stage26ModelPreflightHold("process argv not a full NUL-terminated source")
        argv = tuple(
            piece.decode("utf-8", errors="strict")
            for piece in argv_bytes.split(b"\x00") if piece
        )
        if (
            len(argv) < 3 or owned_exe != expected_exe
            or _sha256(owned_exe) != executable_sha256
            or _sha256(model_file) != gguf_sha256
        ):
            raise Stage26ModelPreflightHold(
                "actual owner executable/model bytes differ from expected SHA/path"
            )
        named_model = Path(_argv_value(argv, "-m", "--model")).resolve(strict=True)
        if named_model != model_file:
            raise Stage26ModelPreflightHold("owned PID points to a different GGUF")
        n_parallel = int(_argv_value(argv, "-np", "--parallel"))
        context = int(_argv_value(argv, "-c", "--ctx-size"))
        layers = int(_argv_value(argv, "-ngl", "--n-gpu-layers"))
        if n_parallel != 1 or context != 8192 or layers <= 0:
            raise Stage26ModelPreflightHold(
                "original single-slot context/offload model configuration changed"
            )
        inode = _owned_loopback_socket_inode(pid, url.port, proc_root=proc_root)
        request = urllib.request.Request(
            f"http://127.0.0.1:{url.port}/slots",
            method="GET", headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=2.0) as reply:
            if reply.status != 200:
                raise Stage26ModelPreflightHold("model /slots not HTTP 200")
            slots_raw = reply.read(1048577)
        if len(slots_raw) > 1048576:
            raise Stage26ModelPreflightHold("model /slots response over 1MiB")
        slots = json.loads(slots_raw)
        if not (
            type(slots) is list and len(slots) == 1
            and type(slots[0]) is dict
            and type(slots[0].get("id")) is int
            and slots[0]["id"] == 0
            and slots[0].get("is_processing") is False
        ):
            raise Stage26ModelPreflightHold(
                "original llama-server n_parallel=1 idle slot unverified"
            )
        desktop_digest = (
            _sha256(windows_gpu_snapshot)
            if windows_gpu_snapshot is not None else None
        )
        return Stage26OwnedModelSource(
            classification="OWNED_MODEL_SLOT_IDLE_DEV_NOT_FULL_GPU_ATTESTATION",
            linux_pid=pid,
            executable_realpath=str(owned_exe),
            executable_sha256=executable_sha256,
            gguf_realpath=str(model_file),
            gguf_sha256=gguf_sha256,
            argv=argv,
            context_size=context,
            n_parallel=n_parallel,
            gpu_layers=layers,
            endpoint=endpoint,
            owned_listener_inode=inode,
            slots_raw_sha256=hashlib.sha256(slots_raw).hexdigest(),
            slots_id=0, slots_processing=False,
            windows_gpu_snapshot_sha256=desktop_digest,
        )
    except Stage26ModelPreflightHold:
        raise
    except (
        OSError, ValueError, UnicodeError, json.JSONDecodeError,
    ) as exc:
        raise Stage26ModelPreflightHold(
            f"original owned model source could not be verified: {type(exc).__name__}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--executable-sha256", required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--gguf-sha256", required=True)
    parser.add_argument("--windows-gpu-snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = asdict(inspect_stage26_model_source(
            pid=args.pid, endpoint=args.endpoint,
            executable=args.executable,
            executable_sha256=args.executable_sha256,
            gguf=args.gguf, gguf_sha256=args.gguf_sha256,
            windows_gpu_snapshot=args.windows_gpu_snapshot,
        ))
        status = 0
    except Stage26ModelPreflightHold as exc:
        result = {
            "classification": "PRE_WORLD_HOLD",
            "reason": str(exc),
            "world_trial_consumed": False,
        }
        status = 2
    path = args.output
    if not path.parent.is_dir():
        parser.error("existing evidence parent directory required")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
                   + "\n").encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
