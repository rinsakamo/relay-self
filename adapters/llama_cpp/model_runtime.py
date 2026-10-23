"""Product/S-owned model-only scope over the S57 primitives, never an engine.

RSEE supplies files/interpreter only. Callers retain their own RelayEngine and
requests. A cooperative host lock is not global GPU or backend STOP proof.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.request
from builtins import BaseExceptionGroup
from contextlib import contextmanager
from pathlib import Path

from adapters.llama_cpp.owned_backend import (
    OwnedBackendRejected,
    OwnedBackendSpec,
    _NoHealthRedirect,
    backend_environment,
    backend_ready,
    preflight_available_port,
    terminate_owned_process,
)
from adapters.llama_cpp.runtime_identity import attest_runtime


def _json_get(port: int, route: str, target: Path) -> object:
    url = f"http://127.0.0.1:{port}{route}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoHealthRedirect(),
    )
    with opener.open(url, timeout=20) as response:
        raw = response.read(1048577)
        if response.status != 200 or response.geturl() != url or len(raw) > 1048576:
            raise OwnedBackendRejected("invalid or unbounded runtime identity response")
    with target.open("xb") as sink:
        sink.write(raw)
    return json.loads(raw)


def _starttime(pid: int) -> str:
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def _wait_for_port(port: int, record, *, timeout_s: float = 75) -> None:
    """Observe TIME_WAIT settlement only; never launch or signal a process."""
    start = time.monotonic()
    pending = False
    while True:
        try:
            preflight_available_port(port)
            record("PORT_RELEASED", port=port, bindable=True,
                   elapsed_s=time.monotonic() - start)
            return
        except OwnedBackendRejected:
            if not pending:
                record("PORT_BIND_PENDING", port=port,
                       reason="BIND_UNAVAILABLE_NOT_PROOF_OF_LISTENER")
                pending = True
            if time.monotonic() - start >= timeout_s:
                raise
            time.sleep(0.25)


@contextmanager
def owned_model(spec: OwnedBackendSpec, *, evidence: Path,
                confirm: str, ready_timeout: float = 120):
    """One synchronous owned model lifetime; no arbitrary command or retry.

    Evidence parent must already exist. Target must be exclusive-new. Every
    post-spawn failure, including BaseException, runs the original S57 cleanup.
    Caller exceptions survive cleanup faults as a BaseExceptionGroup.
    """
    if (confirm != "PRODUCT_MODEL_DEV_ONLY" or not isinstance(spec, OwnedBackendSpec)
            or os.environ.get("GITHUB_ACTIONS") == "true"
            or not 1 <= ready_timeout <= 180):
        raise OwnedBackendRejected("explicit local product model admission required")
    if (not evidence.is_absolute() or evidence.is_symlink()
            or any(p.is_symlink() for p in evidence.parents)
            or not evidence.parent.is_dir()):
        raise OwnedBackendRejected("physical external evidence path required")
    if evidence.is_relative_to(Path(__file__).resolve().parents[2]):
        raise OwnedBackendRejected("evidence must be outside source checkout")
    if spec.binary.is_symlink() or spec.gguf.is_symlink():
        raise OwnedBackendRejected("artifact symlinks rejected")
    evidence.mkdir(mode=0o700)
    proc = None
    primary = None
    cleanup_errors = []
    lease = None
    old_handler = None
    journal = (evidence / "lifecycle.jsonl").open("x")

    def record(event, **facts):
        journal.write(json.dumps({"event": event, **facts}, sort_keys=True) + "\n")
        journal.flush()
        os.fsync(journal.fileno())

    def interrupted(signum, frame):
        raise InterruptedError(f"model owner received signal {signum}")

    try:
        lease_path = Path(f"/tmp/relay-self-llama-cpp-local-gpu-{os.getuid()}.lock")
        lease = os.open(lease_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record("LEASE_ACQUIRED", resource_key="llama-cpp:local-gpu",
               scope="COOPERATIVE_S_HOST_LOCK_ONLY", path=str(lease_path))
        binary_sha, gguf_sha = spec.validate_files()
        preflight_available_port(spec.port)
        record("FILES_VERIFIED", binary_sha256=binary_sha, gguf_sha256=gguf_sha,
               argv=[*spec.argv(), "--no-context-shift", "--slots"])
        if threading.current_thread() is threading.main_thread():
            old_handler = signal.signal(signal.SIGTERM, interrupted)
        with (evidence / "server.log").open("xb") as sink:
            proc = subprocess.Popen(
                (*spec.argv(), "--no-context-shift", "--slots"),
                stdin=subprocess.DEVNULL, stdout=sink, stderr=subprocess.STDOUT,
                env=backend_environment(), start_new_session=True,
            )
        record("SPAWNED", pid=proc.pid, pgid=os.getpgid(proc.pid),
               starttime=_starttime(proc.pid))
        backend_ready(spec.port, proc, timeout_s=ready_timeout)
        probes = {name: _json_get(spec.port, route, evidence / (name + ".json"))
                  for route, name in (("/health", "health"), ("/v1/models", "models"),
                                      ("/props", "props"), ("/slots", "slots"))}
        if proc.poll() is not None or os.getpgid(proc.pid) != proc.pid:
            raise OwnedBackendRejected("owned server exited during identity reads")
        version = subprocess.run([str(spec.binary), "--version"],
                                 capture_output=True, text=True, check=True, timeout=10,
                                 env=backend_environment())
        version_text = version.stdout + version.stderr
        match = re.search(r"build\s+(\d+), commit ([a-f0-9]+)", version_text)
        if match is None:
            raise OwnedBackendRejected("unrecognized binary runtime version")
        identity = attest_runtime(
            **{k: probes[k] for k in ("health", "models", "props", "slots")},
            artifact_path=spec.gguf.resolve(), artifact_sha256=gguf_sha,
            llama_identity={"buildNumber": int(match[1]), "revision": match[2]},
        )
        if identity["modelAlias"] != spec.alias or spec.ctx_size != 8192:
            raise OwnedBackendRejected("caller spec and live model differ")
        if any(slot.get("is_processing") is True for slot in probes["slots"]):
            raise OwnedBackendRejected("single model slot is occupied")
        record("API_READY", pid=proc.pid, identity=identity)
        probes["identity"] = identity
        yield probes
    except BaseException as exc:
        primary = exc
    finally:
        if proc is not None:
            try:
                code = terminate_owned_process(proc)
                waited = proc.wait(timeout=6)
                absent = not Path(f"/proc/{proc.pid}").exists()
                record("REAPED", pid=proc.pid, returncode=code, wait_result=waited,
                       proc_absent=absent,
                       backend_stop_ack=None, gpu_vram_released=None)
                if code != waited or not absent:
                    raise OwnedBackendRejected("owned child reap unconfirmed")
                _wait_for_port(spec.port, record)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if old_handler is not None:
            signal.signal(signal.SIGTERM, old_handler)
        if lease is not None:
            os.close(lease)
        try:
            record("TERMINAL", error=None if primary is None else repr(primary),
                   cleanup_errors=[repr(e) for e in cleanup_errors],
                   classification="DEV_ONLY", qualification="NO_GO", science="NOT_RUN")
        except BaseException as exc:
            cleanup_errors.append(exc)
        finally:
            journal.close()
    if primary is not None and cleanup_errors:
        raise BaseExceptionGroup("model body and cleanup failed", [primary, *cleanup_errors])
    if primary is not None:
        raise primary
    if cleanup_errors:
        raise BaseExceptionGroup("model cleanup failed", cleanup_errors)
