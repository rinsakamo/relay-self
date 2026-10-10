"""S60-B2 one-shot stock probe. Default plan has no external side effects.

P0 authority never authorizes run(). P1 needs a separately reviewed local grant.
No World driver, native stop, idle reconciliation, shell or inference retries.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import signal
import socket
import subprocess
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from relay_self.best_effort_displacement import BestEffortDisplacement
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance

BASE = "66b8045fd2b47d9c35febb12c495379d1248bb4e"
MANIFEST = "1ce5eefa1125d9701f0987cf2ea14489a6c978720f06d89bb3f5a1522560e07d"
SOURCE = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
BINARY = "ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536"
FINGERPRINT = "b10874-e2d2c0d6a"
MODEL = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
SOURCE_FILES = {
    "tools/server/server.cpp": "a0b400372a697182fb552c946579f74e81a845aa6d37e4b40b978ff4be5e016c",
    "tools/server/server-context.cpp": "6abaa516f75cc284503f1d694603eb350696b50054e5512f852e9295e8b172bd",
    "tools/server/server-task.cpp": "0fd5c8df2525e61214986e8abe3fc4edbb92f5dd652c9c2bfd1bc2712218a585",
    "tools/server/server-http.cpp": "fc9d307525d7db13fcee3d32e0d4587cbd2f3d93bcc70a86b2cedc16b336ce11",
    "tools/server/server-queue.cpp": "0e196113d16f130230d2cc0b232915e1f5b4f1dda184790afbfdc4986dd1fd58",
    "common/arg.cpp": "bab0fa0fe008c964a8fcc8e91b5f08ad88f0aa454934c7eebbe1646bb1898471",
}
ROOT = Path(__file__).resolve().parents[2]
CEILING = ["PHYSICAL_RUN_NOT_AUTHORIZED", "BACKEND_STOP_UNCONFIRMED",
           "NO_SAME_PROCESS_SLOT_REUSE_PROOF", "NO_GPU_PREEMPTION_CLAIM", "NO_PRODUCTION_GO"]


class ProbeRejected(ValueError):
    """Sanitized admission/evidence failure; never include private data."""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bounded_read(path: Path, limit: int = 8192) -> bytes:
    with path.open("rb") as f:
        value = f.read(limit + 1)
    if len(value) > limit:
        raise ProbeRejected("input bound exceeded")
    return value


def parse_json(data: bytes):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ProbeRejected("duplicate JSON key")
            value[key] = item
        return value
    try:
        return json.loads(data, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProbeRejected("JSON unconfirmed") from exc


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], timeout=5, stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise ProbeRejected("repository identity unconfirmed") from exc


@dataclass(frozen=True)
class Config:
    binary: Path
    gguf: Path
    source: Path
    binary_sha256: str
    model_sha256: str
    source_commit: str
    alias: str
    port: int
    ctx_size: int
    gpu_layers: int
    arm: str
    prompt: str

    def __post_init__(self):
        if (any(not isinstance(p, Path) or not p.is_absolute()
                for p in (self.binary, self.gguf, self.source))
            or self.binary_sha256 != BINARY or self.model_sha256 != MODEL
            or self.source_commit != SOURCE or self.arm not in ("A", "B", "C")
            or not isinstance(self.alias, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", self.alias)
            or type(self.port) is not int or not 1025 <= self.port <= 65535
            or type(self.ctx_size) is not int or not 512 <= self.ctx_size <= 32768
            or type(self.gpu_layers) is not int or not 0 <= self.gpu_layers <= 120
            or not isinstance(self.prompt, str) or not 1 <= len(self.prompt) <= 4096):
            raise ProbeRejected("exact source/model/loopback config required")

    @classmethod
    def read(cls, data: bytes):
        obj = parse_json(data)
        if not isinstance(obj, dict) or set(obj) != set(cls.__dataclass_fields__):
            raise ProbeRejected("strict config required")
        for key in ("binary", "gguf", "source"):
            if not isinstance(obj[key], str):
                raise ProbeRejected("absolute private paths required")
            obj[key] = Path(obj[key])
        return cls(**obj)

    def argv(self) -> tuple[str, ...]:
        return (str(self.binary), "--model", str(self.gguf), "--alias", self.alias,
                "--host", "127.0.0.1", "--port", str(self.port), "--ctx-size",
                str(self.ctx_size), "--parallel", "1", "--n-gpu-layers",
                str(self.gpu_layers), "--slots")

    def public(self):
        return dict(binary_sha256=self.binary_sha256, model_sha256=self.model_sha256,
                    source_commit=self.source_commit, arm=self.arm, alias=self.alias,
                    host="127.0.0.1", port=self.port, ctx_size=self.ctx_size,
                    gpu_layers=self.gpu_layers, parallel=1, slots=True,
                    private_paths_and_prompt_published=False)


def authorize(config_bytes: bytes, approval_bytes: bytes, evidence: Path) -> Config:
    # Direct API calls must pass exactly the same gates as CLI calls.
    if any(os.environ.get(k) for k in ("CI", "GITHUB_ACTIONS", "GITLAB_CI")):
        raise ProbeRejected("physical run forbidden in CI")
    if len(config_bytes) > 8192 or len(approval_bytes) > 8192:
        raise ProbeRejected("input bound exceeded")
    config = Config.read(config_bytes)
    approval = parse_json(approval_bytes)
    if (not isinstance(approval, dict) or set(approval) != {
        "runner_head", "manifest_sha256", "config_sha256", "arm", "operator_token",
        "allow_model_gpu_launch", "source_binary_mapping_reviewed",
        "prior_cleanup_confirmed", "evidence_root",
    } or approval.get("allow_model_gpu_launch") is not True
        or approval.get("source_binary_mapping_reviewed") is not True
        or approval.get("prior_cleanup_confirmed") is not True
        or approval.get("evidence_root") != str(evidence.resolve())
        or approval.get("arm") != config.arm
        or approval.get("manifest_sha256") != MANIFEST
        or approval.get("config_sha256") != hashlib.sha256(config_bytes).hexdigest()
        or not isinstance(approval.get("operator_token"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", approval["operator_token"])
        or approval.get("runner_head") != git(ROOT, "rev-parse", "HEAD")
        or git(ROOT, "status", "--porcelain")
        or digest(ROOT / "docs/s60b2/manifest.md") != MANIFEST):
        raise ProbeRejected("separate exact local operator approval required")
    return config


class Journal:
    """Exclusive durable reservation + bounded sanitized append-only events."""
    def __init__(self, root: Path):
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.root = root
        self.start = time.monotonic()
        self.last = 0.0
        self.count = 0
        self.accounting = {}
        self.file = (root / "events.jsonl").open("x", encoding="utf-8")
        os.chmod(root / "events.jsonl", 0o600)
        self.emit("RESERVED")
        # Directory entries must survive a crash before invocation.
        for directory in (root, root.parent):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def emit(self, phase: str, **facts):
        allowed = {"generation", "pid", "busy", "task", "decoded", "prompt_processed",
                   "elapsed_s", "returncode", "forced", "arm", "runner_head", "admissions",
                   "transport_starts", "tcp_posts", "complete_responses", "slot_samples",
                   "observed_elapsed_s"}
        elapsed = time.monotonic() - self.start
        if (self.count >= 256 or elapsed < self.last or not math.isfinite(elapsed)
            or not re.fullmatch(r"[A-Z0-9_]{1,80}", phase) or set(facts) - allowed
            or any(type(x) not in (int, float, bool, str) for x in facts.values())
            or any(isinstance(x, str) and not re.fullmatch(r"[a-f0-9ABC]{1,64}", x)
                   for x in facts.values())
            or any(type(x) is float and not math.isfinite(x) for x in facts.values())):
            raise ProbeRejected("receipt bounds or sanitization unconfirmed")
        data = json.dumps(dict(phase=phase, monotonic_elapsed_s=elapsed, **facts),
                          sort_keys=True, allow_nan=False)
        if len(data.encode()) > 2048:
            raise ProbeRejected("receipt bound exceeded")
        self.file.write(data + "\n")
        self.file.flush()
        os.fsync(self.file.fileno())
        self.count += 1
        self.last = elapsed
        if phase == "ARM_ACCOUNTING":
            self.accounting = facts.copy()

    def close(self):
        self.file.close()


def fingerprint(path: Path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def available_port(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", port))


def preflight(config: Config):
    pins = fingerprint(config.binary), fingerprint(config.gguf)
    if (not os.access(config.binary, os.X_OK) or config.gguf.suffix.lower() != ".gguf"
        or digest(config.binary) != config.binary_sha256
        or digest(config.gguf) != config.model_sha256):
        raise ProbeRejected("pinned file identity unconfirmed")
    with config.gguf.open("rb") as f:
        if f.read(4) != b"GGUF":
            raise ProbeRejected("model source unconfirmed")
    if (git(config.source, "rev-parse", "HEAD") != SOURCE
        or git(config.source, "status", "--porcelain", "--untracked-files=no")
        or any(digest(config.source / p) != sha for p, sha in SOURCE_FILES.items())):
        raise ProbeRejected("SLOT_IDLE_ATTESTATION_UNAVAILABLE")
    available_port(config.port)
    if pins != (fingerprint(config.binary), fingerprint(config.gguf)):
        raise ProbeRejected("pinned bytes changed during preflight")
    return pins


class ProcessWitness:
    """Local /proc provenance; server snapshots still are not hardware facts."""
    def __init__(self, config: Config, pid: int, pins, proc: Path = Path("/proc")):
        self.config, self.pid, self.pins, self.proc = config, pid, pins, proc
        self.starttime = self._starttime()

    def _starttime(self):
        # comm may contain spaces or parentheses. Field 22 follows final ')'.
        stat = bounded_read(self.proc / str(self.pid) / "stat").decode()
        return int(stat.rsplit(")", 1)[1].split()[19])

    def verify(self, *, model: bool = True):
        base = self.proc / str(self.pid)
        cfg = self.config
        if (self._starttime() != self.starttime
            or fingerprint(base / "exe") != self.pins[0]
            or fingerprint(cfg.binary) != self.pins[0]
            or fingerprint(cfg.gguf) != self.pins[1]
            or bounded_read(base / "cmdline") != b"\0".join(
                x.encode() for x in cfg.argv()) + b"\0"):
            raise ProbeRejected("owned process identity changed")
        own = set()
        for entry in (base / "fd").iterdir():
            try:
                target = os.readlink(entry)
            except FileNotFoundError:
                continue  # unrelated connection fd may close concurrently
            if target.startswith("socket:["):
                own.add(target[8:-1])
        port = f"{cfg.port:04X}"
        lines = bounded_read(base / "net/tcp", 131072).decode().splitlines()[1:]
        listeners = [line.split() for line in lines
                     if len(line.split()) >= 10 and line.split()[3] == "0A"
                     and line.split()[1].endswith(":" + port)]
        if (len(listeners) != 1 or listeners[0][1] != "0100007F:" + port
            or listeners[0][9] not in own):
            raise ProbeRejected("exclusive owned loopback listener unconfirmed")
        if model:
            stat = cfg.gguf.stat()
            device = f"{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}"
            maps = bounded_read(base / "maps", 2 * 1024 * 1024).decode().splitlines()
            if not any(len(row.split()) >= 5 and row.split()[3] == device
                       and row.split()[4] == str(stat.st_ino) for row in maps):
                raise ProbeRejected("model mapping unconfirmed")


@dataclass(frozen=True)
class Slot:
    busy: bool
    task: int | None
    decoded: int
    prompt_processed: int


def slot_snapshot(data: bytes, config: Config) -> Slot:
    if config.source_commit != SOURCE or config.binary_sha256 != BINARY or len(data) > 131072:
        raise ProbeRejected("SLOT_IDLE_ATTESTATION_UNAVAILABLE")
    value = parse_json(data)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise ProbeRejected("single stock slot unconfirmed")
    slot = value[0]
    if (type(slot.get("id")) is not int or slot["id"] != 0
        or type(slot.get("is_processing")) is not bool
        or type(slot.get("n_ctx")) is not int or slot["n_ctx"] != config.ctx_size):
        raise ProbeRejected("stock slot schema unconfirmed")
    if not slot["is_processing"]:
        return Slot(False, None, 0, 0)
    nxt = slot.get("next_token")
    if (type(slot.get("id_task")) is not int or slot["id_task"] < 0
        or type(slot.get("n_prompt_tokens_processed")) is not int
        or slot["n_prompt_tokens_processed"] < 0
        or not isinstance(nxt, list) or len(nxt) != 1 or not isinstance(nxt[0], dict)
        or type(nxt[0].get("n_decoded")) is not int or nxt[0]["n_decoded"] < 0):
        raise ProbeRejected("stock progress schema unconfirmed")
    return Slot(True, slot["id_task"], nxt[0]["n_decoded"],
                slot["n_prompt_tokens_processed"])


async def get_json(config: Config, endpoint: str) -> bytes:
    if endpoint not in ("/health", "/slots"):
        raise ProbeRejected("fixed read-only endpoint required")
    parser = LoopbackDisplacementAdapter(
        LoopbackTransportConfig(config.alias, config.port, read_s=2, whole_s=2), lambda _: {},
    )
    writer = None
    try:
        async with asyncio.timeout(2):
            reader, writer = await asyncio.open_connection("127.0.0.1", config.port,
                                                          family=socket.AF_INET, limit=8192)
            writer.write((f"GET {endpoint} HTTP/1.1\r\nHost: 127.0.0.1:{config.port}\r\n"
                          "Connection: close\r\n\r\n").encode())
            await writer.drain()
            return await parser._response(reader)  # frozen B1 framing, no Future fabrication
    finally:
        if writer:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 2)
            except (OSError, TimeoutError):
                pass
        await parser.aclose()


async def ready(config: Config, process, witness):
    deadline = time.monotonic() + 90
    for _ in range(180):
        if process.returncode is not None or time.monotonic() >= deadline:
            break
        try:
            witness.verify(model=False)
            async with asyncio.timeout_at(deadline):
                value = parse_json(await get_json(config, "/health"))
            if value == {"status": "ok"}:
                witness.verify()
                return
        except (OSError, ProbeRejected, TransportUnconfirmed, TimeoutError,
                asyncio.IncompleteReadError):
            pass  # bounded startup readiness only, never inference retry
        await asyncio.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise ProbeRejected("startup unconfirmed")


async def durable_write(journal, phase, **facts):
    pending = asyncio.create_task(asyncio.to_thread(journal.emit, phase, **facts))
    try:
        await asyncio.shield(pending)
    except asyncio.CancelledError:
        await pending  # do not close the journal underneath an in-flight fsync
        raise


class MeasuredTransport(LoopbackDisplacementAdapter):
    """Durable content-free B1 transport facts, independent of server slot facts."""
    def __init__(self, config, payload, journal):
        super().__init__(config, payload)
        self.journal = journal
        self.starts = self.posts = self.completions = 0
        self.events = deque()

    def _validate_response(self, body, max_tokens):
        value = parse_json(body)
        if (not isinstance(value, dict) or value.get("model") != self.config.model
            or value.get("system_fingerprint") != FINGERPRINT
            or not isinstance(value.get("usage"), dict)):
            raise TransportUnconfirmed("exact stock response source unconfirmed")
        return super()._validate_response(body, max_tokens)

    def _record(self, event, attempt):
        super()._record(event, attempt)
        phases = {"START_INVOKED": "TRANSPORT_START_INVOKED",
                  "SOCKET_POST_SENT": "TCP_POST_SENT",
                  "HTTP_COMPLETION_OBSERVED": "HTTP_RESPONSE_OBSERVED",
                  "TRANSPORT_UNCONFIRMED": "TRANSPORT_UNCONFIRMED",
                  "CLIENT_CANCEL_UNCONFIRMED": "CLIENT_CANCEL_UNCONFIRMED"}
        self.starts += event == "START_INVOKED"
        self.posts += event == "SOCKET_POST_SENT"
        self.completions += event == "HTTP_COMPLETION_OBSERVED"
        if len(self.events) >= 64:
            raise ProbeRejected("transport observation buffer exhausted")
        self.events.append((phases[event], attempt.request.generation,
                            time.monotonic() - self.journal.start))

    async def drain(self):
        # File I/O is outside frozen nonblocking start/cancel/transport callbacks.
        while self.events:
            phase, generation, observed = self.events.popleft()
            await durable_write(self.journal, phase, generation=generation,
                                observed_elapsed_s=observed)


class KeepStream(MeasuredTransport):
    """Arm B explicitly non-terminating client intervention, no STOP assertion."""
    def cancel(self, request):
        if self._attempt is None or self._attempt.request is not request:
            raise ProbeRejected("exact ignored-cancel ticket required")


async def measure(config: Config, witness, journal: Journal, *,
                  diagnostic_adapter: type[MeasuredTransport] | None = None):
    # Prospective R3 offline seam; run()/CLI never select diagnostic mode.
    if diagnostic_adapter is not None:
        from adapters.mineflayer.s60b2_r3_diagnostic import R3DiagnosticTransport
        if config.arm != "A" or diagnostic_adapter is not R3DiagnosticTransport:
            raise ProbeRejected("R3 offline Arm A diagnostic adapter required")
    deadline = time.monotonic() + 60
    context = CognitionContext("s60b2-callback", 1, 1, 1)
    provenance = Provenance("s60b2", "operator-approved-probe")
    adapter_type = KeepStream if config.arm == "B" else MeasuredTransport
    if diagnostic_adapter is not None:
        adapter_type = diagnostic_adapter
    adapter = adapter_type(LoopbackTransportConfig(config.alias, config.port), lambda _: dict(
        model=config.alias, messages=[dict(role="user", content=config.prompt)],
        temperature=0, max_tokens=256, stream=False,
    ), journal)
    owner = BestEffortDisplacement(context, "s60b2", adapter.start, adapter.cancel, time.monotonic)
    adapter.bind(owner)
    samples = 0
    last_sample = -math.inf
    inference_count = 0
    terminal_count = 0
    task_ids = set()

    def submit(level, priority):
        nonlocal inference_count
        request = owner.admit(context, level, priority, deadline, 5, provenance)
        owner.submit(request)
        inference_count += 1
        return request

    async def record(phase, **facts):
        await durable_write(journal, phase, **facts)

    async def sample():
        nonlocal samples, last_sample
        await asyncio.sleep(max(0, 0.25 - (time.monotonic() - last_sample)))
        last_sample = time.monotonic()
        if samples >= 120:
            raise ProbeRejected("slot observation budget exhausted")
        samples += 1
        await adapter.drain()
        await asyncio.to_thread(witness.verify)
        value = slot_snapshot(await get_json(config, "/slots"), config)
        await asyncio.to_thread(witness.verify)
        await record("BACKEND_BUSY_OBSERVED" if value.busy else "SAME_PROCESS_SLOT_IDLE_OBSERVED",
                     busy=value.busy, task=value.task if value.task is not None else -1,
                     decoded=value.decoded, prompt_processed=value.prompt_processed)
        return value

    async def busy(request):
        while True:
            value = await sample()
            if value.busy and (value.decoded > 0 or value.prompt_processed > 0):
                if value.task in task_ids:
                    raise ProbeRejected("new inference task identity unconfirmed")
                task_ids.add(value.task)
                await record("NEW_INFERENCE_STARTED", generation=request.generation)
                return
            if adapter._attempt.future.done():
                raise ProbeRejected("progress missed UNDETERMINED")
            await asyncio.sleep(0.25)

    async def complete(request):
        nonlocal terminal_count
        attempt = adapter._attempt
        while not attempt.future.done():
            await asyncio.sleep(0.25)
            await sample()
            if not attempt.future.done():
                owner.tick()  # service pending expiry without consuming completion
        await adapter.drain()
        future = attempt.future
        if future.cancelled() or future.exception() is not None:
            raise ProbeRejected("provider terminal unconfirmed")
        await record("PROVIDER_TERMINAL_OBSERVED", generation=request.generation)
        await record("NEW_INFERENCE_COMPLETED", generation=request.generation)
        terminal_count += 1
        return owner.tick()

    async def l0():
        start = time.monotonic()
        entered = []
        async def callback():
            if config.arm != "C" and adapter._attempt.future.done():
                raise ProbeRejected("L0 overlap not observed")
            entered.append(time.monotonic() - journal.start)
        await owner.run_l0(callback)
        elapsed = time.monotonic() - start
        await record("L0_CALLBACK_ENTER", observed_elapsed_s=entered[0])
        await record("L0_CALLBACK_RETURN", elapsed_s=elapsed,
                     observed_elapsed_s=start + elapsed - journal.start)
        if elapsed > 0.1:
            raise ProbeRejected("L0 callback timing ceiling exceeded")

    try:
        async with asyncio.timeout_at(deadline):
            if (await sample()).busy:
                raise ProbeRejected("initial backend busy")
            old = submit("L2", 1)
            await record("L2_ADMITTED", generation=old.generation)
            await busy(old)
            if config.arm == "A":
                await l0()
                if (await complete(old)) is None:
                    raise ProbeRejected("baseline result unconfirmed")
                fresh = submit("L1", 2)
                await busy(fresh)
                if (await complete(fresh)) is None:
                    raise ProbeRejected("fresh result unconfirmed")
            else:
                submit("L1", 2)
                newest = submit("L1", 3)
                pending_until = min(deadline, time.monotonic() + 5)
                await record("HOST_CANCEL_REQUESTED", generation=old.generation)
                await l0()
                if config.arm == "B":
                    result = await complete(old)
                    if result is not None:
                        raise ProbeRejected("stale result accepted")
                    await record("STALE_REJECTED", generation=old.generation)
                    if owner.active is newest:
                        await busy(newest)
                        if (await complete(newest)) is None:
                            raise ProbeRejected("fresh result unconfirmed")
                    else:
                        await record("CANCEL_UNCONFIRMED_BACKEND_BUSY")
                else:
                    attempt = adapter._attempt
                    if attempt.task:
                        await attempt.task
                    await record("TRANSPORT_DISCONNECTED", generation=old.generation)
                    await sample()  # independent server observation AFTER stream close
                    while owner.pending is not None and time.monotonic() <= pending_until:
                        await asyncio.sleep(0.25)
                        await sample()
                        owner.tick()
                    owner.tick()
                    if owner.pending is not None or owner.active is not old:
                        raise ProbeRejected("unknown lease or expiry violated")
                    if sum(e == "START_INVOKED" for e, _ in adapter.receipts) != 1:
                        raise ProbeRejected("disconnect triggered successor transport")
                    await record("CANCEL_UNCONFIRMED_BACKEND_BUSY")
            # Count actual starts separately from admissions/coalescing.
            starts = sum(e == "START_INVOKED" for e, _ in adapter.receipts)
            return dict(status="P1_RECEIPTS_REVIEW_REQUIRED", arm=config.arm,
                        admissions=inference_count, transport_starts=starts,
                        independently_observed_starts=len(task_ids), complete_responses=terminal_count,
                        slot_samples=samples, hardware_evidence=False, world_actions=0)
    finally:
        await adapter.aclose()
        await adapter.drain()
        await record("ARM_ACCOUNTING", admissions=inference_count,
                     transport_starts=adapter.starts, tcp_posts=adapter.posts,
                     complete_responses=adapter.completions, slot_samples=samples)


async def cleanup(process, journal: Journal):
    if process.returncode is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        journal.emit("OWNED_PROCESS_TERM_REQUESTED")
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            journal.emit("OWNED_PROCESS_FORCED_KILL", forced=True)
            await asyncio.wait_for(process.wait(), 5)
    journal.emit("OWNED_PROCESS_EXIT", returncode=process.returncode)


async def run(config_bytes: bytes, approval_bytes: bytes, evidence: Path):
    config = authorize(config_bytes, approval_bytes, evidence)
    # Never put evidence in checkout; no generated paths in public receipts.
    root = evidence.resolve()
    if ROOT == root or ROOT in root.parents:
        raise ProbeRejected("private external fresh evidence root required")
    journal = Journal(root)
    process = None
    result = dict(status="UNDETERMINED", physical_qualification=False)
    try:
        journal.emit("APPROVAL_BOUND", arm=config.arm, runner_head=git(ROOT, "rev-parse", "HEAD"))
        pins = preflight(config)
        journal.emit("PREFLIGHT_PASS")
        # Atomic once-only invocation follows fsynced reservation, never retried.
        journal.emit("OWNED_PROCESS_START_INVOKED")
        spawn = asyncio.create_task(asyncio.create_subprocess_exec(
            *config.argv(), stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL, start_new_session=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        ))
        try:
            process = await asyncio.shield(spawn)
        except asyncio.CancelledError:
            process = await spawn  # retain ownership even at interrupted creation
            raise
        journal.emit("OWNED_PROCESS_STARTED", pid=process.pid)
        witness = ProcessWitness(config, process.pid, pins)
        await ready(config, process, witness)
        journal.emit("HEALTH_RESPONSE_OBSERVED")
        result = await measure(config, witness, journal)
    except asyncio.CancelledError:
        journal.emit("HOST_ABORTED")
        raise
    except (OSError, ValueError, TimeoutError, asyncio.IncompleteReadError,
            asyncio.LimitOverrunError):
        journal.emit("UNDETERMINED")
    finally:
        try:
            if process:
                await cleanup(process, journal)
        except (OSError, TimeoutError):
            result = dict(status="CLEANUP_UNCONFIRMED", physical_qualification=False)
            journal.emit("CLEANUP_UNCONFIRMED")
        finally:
            journal.close()
            # Summary is secondary to durable failure-inclusive event journal.
            result.update(config=config.public(), manifest_sha256=MANIFEST,
                          accounting=journal.accounting,
                          physical_qualification=False,
                          backend_stop="UNCONFIRMED", gpu_compute_quiesced=False,
                          vram_released=False, production_go=False)
            with (root / "summary.json").open("x", encoding="utf-8") as output:
                os.chmod(root / "summary.json", 0o600)
                json.dump(result, output, sort_keys=True)
                output.flush()
                os.fsync(output.fileno())
    return result


def plan():
    return dict(status="P0_ONLY", default="--plan", base=BASE, source_commit=SOURCE,
                binary_sha256=BINARY, model_sha256=MODEL, manifest_sha256=MANIFEST,
                launch_count=0, inference_count=0, world_actions=0,
                slot_idle_attestation="SLOT_IDLE_ATTESTATION_UNAVAILABLE_UNTIL_LIVE_PROVENANCE",
                required="Separate exact local operator approval; see docs/s60b2/plan.md",
                ceilings=CEILING)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps(plan(), sort_keys=True))
        return 0
    try:
        if any(p is None for p in (args.config, args.approval, args.evidence)):
            raise ProbeRejected("separate local approval/config/evidence required")
        result = asyncio.run(run(bounded_read(args.config), bounded_read(args.approval), args.evidence))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "P1_RECEIPTS_REVIEW_REQUIRED" else 2
    except (OSError, ValueError, TimeoutError):
        print(json.dumps(dict(status="BLOCKED", reason="local admission unconfirmed")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
