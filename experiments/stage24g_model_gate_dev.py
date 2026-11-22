"""Stage24g read-only source-qualified model/GPU gate BEFORE owned World creation.

No GPU allocation, no model inference, no process killing, no model loading.
The operator's PID/alias/path are *claims* until independent sources agree.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.resident_llama_inference_lane_dev import LlamaCppSingleSlotWitness

PINNED_STAGE24G_GGUF_SHA256 = (
    "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
)
_PROC_ROOT = Path("/proc")


class Stage24gModelGateError(RuntimeError):
    """Model or GPU provenance incomplete; do not start the trial."""


@dataclass(frozen=True)
class Stage24gModelGateReceipt:
    llama_pid: int
    model_alias: str
    gguf_path: str
    gguf_sha256: str
    gpu_name: str
    native_cmdline_sha256: str
    maps_sha256: str
    slot_id: int
    slot_count: int
    model_catalog_sha256: str


def _digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _read_model_catalog(endpoint: str, model_alias: str) -> str:
    parsed = urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise Stage24gModelGateError("model endpoint not strict loopback HTTP")
    url = f"http://{parsed.hostname}:{parsed.port}/v1/models"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=5.0) as response:
        if response.status != 200:
            raise Stage24gModelGateError("model catalog is not HTTP 200")
        raw = response.read(1024 * 1024)
    obj = json.loads(raw)
    models = obj.get("data") if isinstance(obj, dict) else None
    if (
        type(models) is not list or len(models) != 1
        or not isinstance(models[0], dict)
        or models[0].get("id") != model_alias
    ):
        raise Stage24gModelGateError("model catalog alias differs from loaded GGUF claim")
    return hashlib.sha256(raw).hexdigest()



def _verify_pid_owns_endpoint(pid: int, endpoint: str) -> None:
    """Bind the observed localhost listening TCP socket to the same owned PID.

    Model/PID checks without this allow pointing the client at another server
    sharing the same model alias. Reads only proc kernel records, no packets.
    """
    parsed = urlsplit(endpoint)
    port = parsed.port
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or type(port) is not int
    ):
        raise Stage24gModelGateError("model socket not explicit loopback TCP")
    listening: set[str] = set()
    for table in (_PROC_ROOT / "net/tcp", _PROC_ROOT / "net/tcp6"):
        try:
            rows = table.read_text().splitlines()[1:]
        except OSError:
            continue
        for line in rows:
            fields = line.split()
            if len(fields) >= 10 and fields[3] == "0A":
                try:
                    found_port = int(fields[1].rsplit(":", 1)[1], 16)
                except (ValueError, IndexError):
                    continue
                if found_port == port:
                    listening.add(fields[9])
    if not listening:
        raise Stage24gModelGateError("model listening TCP socket unavailable")
    try:
        targets = {
            os.readlink(fd)
            for fd in (_PROC_ROOT / str(pid) / "fd").iterdir()
        }
    except OSError as exc:
        raise Stage24gModelGateError("model PID socket ownership unreadable") from exc
    if not any(f"socket:[{inode}]" in targets for inode in listening):
        raise Stage24gModelGateError("model endpoint is not owned by mapped GGUF PID")


def verify_stage24g_model_gate(
    *, gguf_path: Path, llama_pid: int, model_alias: str,
    llama_endpoint: str, systemone_endpoint: str,
) -> Stage24gModelGateReceipt:
    """All observations are read-only and checked *before* creating any World."""
    if (
        not isinstance(gguf_path, Path) or gguf_path.is_symlink()
        or not gguf_path.is_file() or gguf_path.suffix.lower() != ".gguf"
        or type(llama_pid) is not int or llama_pid <= 1
        or not isinstance(model_alias, str) or not model_alias.strip()
    ):
        raise Stage24gModelGateError("typed regular GGUF/PID/model alias required")
    resolved = gguf_path.resolve(strict=True)
    if _digest_file(resolved) != PINNED_STAGE24G_GGUF_SHA256:
        raise Stage24gModelGateError("GGUF bytes differ from independently archived pin")
    proc = _PROC_ROOT / str(llama_pid)
    try:
        if proc.is_symlink() or proc.stat().st_uid != os.getuid():
            raise Stage24gModelGateError("llama PID not owned by current operator")
        cmdline_bytes = (proc / "cmdline").read_bytes()
        argv = [x.decode("utf-8") for x in cmdline_bytes.split(b"\x00") if x]
        maps_bytes = (proc / "maps").read_bytes()
        maps = maps_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Stage24gModelGateError("owned llama process source unreadable") from exc
    if (
        not argv or not re.search(r"llama-server(?:$|\b)", Path(argv[0]).name)
        or not any(
            str(resolved) == arg or arg.endswith("=" + str(resolved))
            for arg in argv[1:]
        )
        or not any(line.rsplit(None, 1)[-1] == str(resolved)
                   for line in maps.splitlines() if line.split())
    ):
        raise Stage24gModelGateError("loaded GGUF not mapped by owned llama-server PID")
    try:
        apps = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout
        names = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise Stage24gModelGateError("GPU owner source unavailable") from exc
    if str(llama_pid) not in {line.strip() for line in apps.splitlines()}:
        raise Stage24gModelGateError("owned llama PID absent from active GPU compute apps")
    gpu = next((line.strip() for line in names.splitlines() if "RTX 3060" in line), None)
    if gpu is None:
        raise Stage24gModelGateError("expected RTX 3060 GPU missing")
    provider = LlamaCppRelayProvider(
        endpoint=llama_endpoint, systemone_endpoint=systemone_endpoint,
        model=model_alias,
    )
    witness = LlamaCppSingleSlotWitness(
        provider=provider, backend_ref=f"stage24g-pid-{llama_pid}",
    )
    _verify_pid_owns_endpoint(llama_pid, llama_endpoint)
    slot = witness.require_idle()
    catalog_sha = _read_model_catalog(llama_endpoint, model_alias)
    return Stage24gModelGateReceipt(
        llama_pid, model_alias, str(resolved), PINNED_STAGE24G_GGUF_SHA256,
        gpu, hashlib.sha256(cmdline_bytes).hexdigest(),
        hashlib.sha256(maps_bytes).hexdigest(), slot.slot_id,
        slot.n_slots, catalog_sha,
    )


def receipt_json(receipt: Stage24gModelGateReceipt) -> bytes:
    return (json.dumps(asdict(receipt), sort_keys=True, indent=2) + "\n").encode()
