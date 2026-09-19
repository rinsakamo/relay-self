from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

from adapters.llama_cpp.qualify_relay_engine import (
    inspect_llama_cpp_runtime,
    inspect_repository,
)
from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerConnectionEnd,
    MineflayerDecodedMessage,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from adapters.mineflayer.runtime_admission import (
    mineflayer_message_requires_epoch,
)
from experiments.cognition_consequence_loop import (
    ExpectedEvidence,
    ObservedEvidence,
    compare_consequence,
)
from experiments.controlled_minecraft_restart import (
    choose_memory_matching_destination,
    retain_successful_flee_memory,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
    ControlledSkill,
    ScenarioDecision,
    SkillRunResult,
    build_flee_destination_request,
    decide_skill,
    execute_decision,
)
from experiments.present_skill_epoch import (
    PresentFact,
    bind_flee_destination,
    build_present,
    narrow_for_flee,
    projection_is_current,
)
from experiments.reconsideration_admission import (
    ReconsiderationAdmissionKind,
    admit_reach_safety_reconsideration,
)
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    RelayEngine,
    RelayEngineResult,
)
from relay_self.skill import SkillState

QUALIFICATION_NAME = "relay-self-141-terminal-minecraft"
EXPECTED_MINECRAFT_SHA256 = (
    "98ab064389a8b34d48ac3d4c5ed858dd9433d0dfd1a12e1cbbda916448d92994"
)
EXPECTED_MODEL_SHA256 = (
    "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
)
EXPECTED_LLAMA_BUILD = "b10874-e2d2c0d6a"
EXPECTED_MINEFLAYER_VERSION = "4.39.0"
EXPECTED_JAVA_VERSION = "25.0.4.1"


class TerminalQualificationError(RuntimeError):
    """Raised when the bounded live composition cannot be qualified."""


@dataclass(slots=True)
class StageTracker:
    phase: str
    stage: str = "initializing"

    def set(self, stage: str) -> None:
        self.stage = stage


@dataclass(slots=True)
class MonotonicClock:
    last: int = 0

    def now_ns(self) -> int:
        current = time.monotonic_ns()
        if current <= self.last:
            current = self.last + 1
        self.last = current
        return current


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TerminalQualificationError(
            f"could not read JSON evidence {path}: {exc}"
        ) from exc


def jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: jsonable(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [jsonable(item) for item in value]
    return value


def provenance_json(value: Provenance) -> dict[str, str]:
    return {"source": value.source, "reference": value.reference}


def message_json(message: MineflayerDecodedMessage) -> dict[str, object]:
    return jsonable(message)  # type: ignore[return-value]


def require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TerminalQualificationError(f"{name} must be non-empty text")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise TerminalQualificationError(f"could not hash {path}: {exc}") from exc
    return digest.hexdigest()


def command_output(command: list[str], *, env: dict[str, str] | None = None) -> str:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
    except OSError as exc:
        raise TerminalQualificationError(
            f"could not start {' '.join(command)}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise TerminalQualificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}: {detail}"
        )
    return (completed.stdout + completed.stderr).strip()


def _node_env(node: Path, base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    node_dir = str(node.parent)
    env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    return env


def server_properties_text(port: int) -> str:
    """Return the small controlled-world server configuration."""

    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise TerminalQualificationError("Minecraft port must be an integer in 1..65535")
    values = (
        ("allow-flight", "true"),
        ("difficulty", "normal"),
        ("gamemode", "survival"),
        ("level-name", "world"),
        ("level-type", "minecraft:flat"),
        ("motd", "RelaySelf #141 controlled terminal"),
        ("online-mode", "false"),
        ("pvp", "false"),
        ("server-port", str(port)),
        ("spawn-monsters", "false"),
        ("spawn-npcs", "false"),
        ("spawn-protection", "0"),
        ("simulation-distance", "6"),
        ("view-distance", "8"),
    )
    return "\n".join(f"{key}={value}" for key, value in values) + "\n"


def prepare_server_root(
    *,
    server_root: Path,
    minecraft_jar: Path,
    source_root: Path | None,
    port: int,
) -> dict[str, object]:
    if server_root.exists() and any(server_root.iterdir()):
        raise TerminalQualificationError(
            f"server root must be a new empty directory: {server_root}"
        )
    server_root.mkdir(parents=True, exist_ok=True)
    if not minecraft_jar.is_file():
        raise TerminalQualificationError(f"Minecraft jar does not exist: {minecraft_jar}")
    shutil.copy2(minecraft_jar, server_root / "server.jar")
    copied: list[str] = []
    if source_root is not None:
        for name in ("libraries", "versions"):
            source = source_root / name
            target = server_root / name
            if source.is_dir():
                shutil.copytree(source, target)
                copied.append(name)
    (server_root / "eula.txt").write_text(
        "# EULA accepted by the operator for the controlled qualification runtime.\n"
        "eula=true\n",
        encoding="utf-8",
    )
    (server_root / "server.properties").write_text(
        server_properties_text(port),
        encoding="utf-8",
    )
    return {
        "server_root": str(server_root),
        "server_jar": str(server_root / "server.jar"),
        "server_jar_sha256": sha256_file(server_root / "server.jar"),
        "server_properties": str(server_root / "server.properties"),
        "eula": str(server_root / "eula.txt"),
        "copied_runtime_directories": copied,
        "configuration": {
            "server-port": str(port),
            "online-mode": "false",
            "level-type": "minecraft:flat",
            "spawn-protection": "0",
            "difficulty": "normal",
            "gamemode": "survival",
            "pvp": "false",
            "spawn-monsters": "false",
        },
    }


def parse_properties(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise TerminalQualificationError(f"could not read server config: {exc}") from exc
    result: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.replace("\\:", ":")
    return result


def assert_port_listener(host: str, port: int) -> None:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return
    except OSError as exc:
        raise TerminalQualificationError(
            f"no listener at {host}:{port}: {exc}"
        ) from exc


def assert_process_alive(pid: int, name: str) -> None:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        raise TerminalQualificationError(f"{name} process is not alive: pid={pid}") from exc


def _server_log_tail(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TerminalQualificationError(f"could not read Minecraft log: {exc}") from exc
    return raw[-128 * 1024 :].decode("utf-8", errors="replace")


def run_preflight(args: argparse.Namespace) -> dict[str, object]:
    evidence_root = Path(args.evidence_root).resolve()
    repo_root = Path(args.repo_root).resolve()
    server_root = Path(args.server_root).resolve()
    server_log = Path(args.server_log).resolve()
    java = Path(args.java).resolve()
    node = Path(args.node).resolve()
    npm = Path(args.npm).resolve()
    llama = Path(args.llama).resolve()
    model = Path(args.model).resolve()
    runtime_artifacts = (
        read_json(Path(args.runtime_artifacts_path))
        if args.runtime_artifacts_path
        else None
    )
    if not java.is_file() or not node.is_file() or not npm.is_file() or not llama.is_file():
        raise TerminalQualificationError("runtime identity path is missing")

    repository = inspect_repository(repo_root)
    java_version = command_output([str(java), "-version"])
    node_version = command_output([str(node), "--version"])
    npm_version = command_output([str(npm), "--version"], env=_node_env(node))
    llama_version = command_output([str(llama), "--version"])
    if EXPECTED_JAVA_VERSION not in java_version:
        raise TerminalQualificationError(
            f"unexpected Java identity; expected {EXPECTED_JAVA_VERSION}: {java_version}"
        )
    node_match = re.fullmatch(r"v(\d+)(?:\.\d+){1,2}", node_version.strip())
    if node_match is None or int(node_match.group(1)) < 22:
        raise TerminalQualificationError(f"Node >=22 is required: {node_version}")
    if "0.4.0-dev" not in llama_version or "build 10874" not in llama_version:
        raise TerminalQualificationError(f"unexpected llama.cpp identity: {llama_version}")
    if not model.is_file():
        raise TerminalQualificationError(f"GGUF does not exist: {model}")
    model_sha256 = sha256_file(model)
    if model_sha256 != EXPECTED_MODEL_SHA256:
        raise TerminalQualificationError(
            f"unexpected GGUF SHA256: {model_sha256}; expected {EXPECTED_MODEL_SHA256}"
        )
    minecraft_sha256 = sha256_file(server_root / "server.jar")
    if minecraft_sha256 != EXPECTED_MINECRAFT_SHA256:
        raise TerminalQualificationError(
            f"unexpected Minecraft server SHA256: {minecraft_sha256}; "
            f"expected {EXPECTED_MINECRAFT_SHA256}"
        )
    properties = parse_properties(server_root / "server.properties")
    expected_properties = {
        "server-port": str(args.minecraft_port),
        "online-mode": "false",
        "level-type": "minecraft:flat",
        "spawn-protection": "0",
    }
    if any(properties.get(key) != value for key, value in expected_properties.items()):
        raise TerminalQualificationError(
            f"controlled Minecraft configuration mismatch: {properties}"
        )
    eula = (server_root / "eula.txt").read_text(encoding="utf-8")
    if not re.search(r"(?m)^eula=true\s*$", eula):
        raise TerminalQualificationError("operator EULA acceptance is not recorded")
    assert_process_alive(args.minecraft_pid, "Minecraft")
    assert_process_alive(args.llama_pid, "llama.cpp")
    assert_port_listener("127.0.0.1", args.minecraft_port)
    runtime = inspect_llama_cpp_runtime(origin=args.llama_origin, timeout=args.llama_timeout)
    if runtime.model != str(model):
        raise TerminalQualificationError(
            f"served model identity mismatch: {runtime.model} != {model}"
        )
    if runtime.build_info != EXPECTED_LLAMA_BUILD:
        raise TerminalQualificationError(
            f"llama.cpp /props build mismatch: {runtime.build_info} != {EXPECTED_LLAMA_BUILD}"
        )
    package_path = repo_root / "adapters" / "mineflayer" / "node_modules" / "mineflayer" / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TerminalQualificationError(
            f"Mineflayer dependency is not prepared: {package_path}: {exc}"
        ) from exc
    if package.get("version") != EXPECTED_MINEFLAYER_VERSION:
        raise TerminalQualificationError(
            f"unexpected Mineflayer version: {package.get('version')}"
        )
    log_tail = _server_log_tail(server_log)
    if "Done (" not in log_tail:
        raise TerminalQualificationError("Minecraft server has not reported Done")

    preflight = {
        "transaction_started": False,
        "qualification": QUALIFICATION_NAME,
        "timestamp": utc_now(),
        "repository": jsonable(repository),
        "authority": (
            read_json(Path(args.authority_path))
            if args.authority_path
            else None
        ),
        "working_tree": "clean",
        "generated_runtime_artifacts": runtime_artifacts,
        "runtime": {
            "java": str(java),
            "java_version": java_version,
            "minecraft_version": args.minecraft_version,
            "minecraft_jar": str(server_root / "server.jar"),
            "minecraft_jar_sha256": minecraft_sha256,
            "minecraft_server_pid": args.minecraft_pid,
            "minecraft_listener": f"127.0.0.1:{args.minecraft_port}",
            "server_properties": properties,
            "node": str(node),
            "node_version": node_version,
            "npm": str(npm),
            "npm_version": npm_version,
            "mineflayer_version": package.get("version"),
            "llama": str(llama),
            "llama_version": llama_version,
            "llama_pid": args.llama_pid,
            "llama_runtime": jsonable(runtime),
            "gguf": str(model),
            "gguf_sha256": model_sha256,
        },
        "self": {
            "self_id": args.self_id,
            "persistent_path": str(Path(args.persistent_path).resolve()),
        },
        "scenario": {
            "ordinary": "no configured hazard and food above threshold",
            "resource": "food <= 10 with server-given bread",
            "threat": "server-summoned nearby zombie with two destinations",
            "mismatch": "one server-side teleport after FLEE forward issuance",
            "restart": "second OS Self process and second Mineflayer session",
        },
    }
    write_json(evidence_root / "preflight.json", preflight)
    return preflight


async def write_server_command(
    *,
    control_path: Path,
    evidence_path: Path,
    command: str,
    reason: str,
    settle_s: float = 0.25,
) -> None:
    record = {
        "timestamp": utc_now(),
        "command": command,
        "reason": reason,
        "actor": "controlled-world-intervention",
        "not_self_action": True,
    }
    with evidence_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    try:
        await asyncio.to_thread(_write_fifo, control_path, command)
    except OSError as exc:
        raise TerminalQualificationError(
            f"could not deliver server command {command!r}: {exc}"
        ) from exc
    await asyncio.sleep(settle_s)


def _write_fifo(path: Path, command: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(command + "\n")
        handle.flush()


class RecordedMineflayerSession:
    """Evidence wrapper around the existing target-local process session."""

    def __init__(
        self,
        session: MineflayerProcessSession,
        evidence_path: Path,
        *,
        forward_intervention: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._session = session
        self._evidence = evidence_path
        self._forward_intervention = forward_intervention
        self._intervention_task: asyncio.Task[None] | None = None
        self.raw_received_events = 0
        self.admitted_decision_epochs = 0
        self.received_by_type: dict[str, int] = {}
        self._record_message(session.started, admitted=False, startup=True)

    @property
    def started(self):
        return self._session.started

    @property
    def process_pid(self) -> int:
        process = getattr(self._session, "_process", None)
        pid = getattr(process, "pid", None)
        if not isinstance(pid, int):
            raise TerminalQualificationError("Mineflayer process PID is unavailable")
        return pid

    @property
    def process_returncode(self) -> int | None:
        return self._session.process_returncode

    def set_forward_intervention(
        self,
        callback: Callable[[], Awaitable[None]] | None,
    ) -> None:
        self._forward_intervention = callback

    async def receive(self) -> MineflayerDecodedMessage:
        message = await self._session.receive()
        self._record_message(
            message,
            admitted=mineflayer_message_requires_epoch(message),
            startup=False,
        )
        return message

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        if (
            control == "forward"
            and state
            and self._forward_intervention is not None
            and self._intervention_task is None
        ):
            self._intervention_task = asyncio.create_task(
                self._forward_intervention()
            )
        await self._session.send_set_control(
            action_id,
            control=control,
            state=state,
        )

    async def send_clear_controls(self, action_id: str) -> None:
        await self._session.send_clear_controls(action_id)

    async def send_equip_item(self, action_id: str, *, item_name: str) -> None:
        await self._session.send_equip_item(action_id, item_name=item_name)

    async def send_consume_held(self, action_id: str) -> None:
        await self._session.send_consume_held(action_id)

    async def send_look(self, action_id: str, *, yaw: float, pitch: float) -> None:
        await self._session.send_look(action_id, yaw=yaw, pitch=pitch)

    async def wait_forward_intervention(self) -> None:
        if self._intervention_task is not None:
            await self._intervention_task

    async def shutdown(self) -> int:
        self._append({"event": "shutdown_requested", "timestamp": utc_now()})
        return await self._session.shutdown()

    async def terminate(self) -> int:
        return await self._session.terminate()

    def _append(self, value: object) -> None:
        with self._evidence.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")

    def _record_message(
        self,
        message: MineflayerDecodedMessage,
        *,
        admitted: bool,
        startup: bool,
    ) -> None:
        if not startup:
            self.raw_received_events += 1
            if admitted:
                self.admitted_decision_epochs += 1
        kind = type(message).__name__
        if isinstance(message, MineflayerObservation):
            kind = f"observation:{message.kind}"
        self.received_by_type[kind] = self.received_by_type.get(kind, 0) + 1
        self._append(
            {
                "event": "received",
                "timestamp": utc_now(),
                "startup": startup,
                "requires_admitted_epoch": admitted,
                "message": message_json(message),
            }
        )


def _assert_no_terminal_adapter_message(message: object) -> None:
    if isinstance(message, MineflayerConnectionEnd):
        raise TerminalQualificationError(
            f"Mineflayer connection ended: {message.reason}"
        )
    if isinstance(message, MineflayerAdapterErrorMessage):
        raise TerminalQualificationError(
            f"Mineflayer adapter error: {message.message}"
        )


async def receive_until(
    session: RecordedMineflayerSession,
    predicate: Callable[[MineflayerObservation], bool],
    *,
    timeout_s: float,
) -> MineflayerObservation:
    while True:
        try:
            message = await asyncio.wait_for(session.receive(), timeout=timeout_s)
        except TimeoutError as exc:
            raise TerminalQualificationError(
                "timed out waiting for required Mineflayer observation"
            ) from exc
        _assert_no_terminal_adapter_message(message)
        if isinstance(message, MineflayerObservation) and predicate(message):
            return message


def observation_has_item(observation: MineflayerObservation, name: str) -> bool:
    return any(item.name == name and item.count > 0 for item in observation.snapshot.inventory)


def nearby_entity_names(observation: MineflayerObservation) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                entity.name
                for entity in observation.snapshot.nearby_entities
                if entity.name is not None
            }
        )
    )


def _distance(a: object, b: object) -> float:
    return math.hypot(a.x - b.x, a.z - b.z)  # type: ignore[attr-defined]


def destination(
    destination_id: str,
    *,
    position: object,
    description: str,
    reference: str,
) -> ControlledDestination:
    from adapters.mineflayer.python_protocol import MineflayerPosition

    if not isinstance(position, MineflayerPosition):
        raise TerminalQualificationError("destination position must be MineflayerPosition")
    return ControlledDestination(
        destination_id=destination_id,
        position=position,
        description=description,
        provenance=Provenance(
            source="controlled-minecraft-terminal-scenario",
            reference=reference,
        ),
    )


def scenario(
    *,
    hazard_names: frozenset[str],
    destinations: tuple[ControlledDestination, ...],
    evidence_timeout_s: float = 3.0,
    max_evidence_messages: int = 48,
) -> ControlledScenario:
    return ControlledScenario(
        hazard_entity_names=hazard_names,
        food_threshold=10,
        edible_item_names=("bread",),
        destinations=destinations,
        flee_min_progress=0.25,
        evidence_timeout_s=evidence_timeout_s,
        max_evidence_messages=max_evidence_messages,
        cognition_soft_wall_time_budget_s=60.0,
        cognition_think_allowed=True,
    )


def commit_intent() -> IntentCommitment:
    commitment = IntentCommitment()
    commitment.commit(
        "intent-terminal-reach-safety",
        objective="reach safety",
        at_ns=time.monotonic_ns(),
        provenance=Provenance(
            source=QUALIFICATION_NAME,
            reference="current-intent:reach-safety",
        ),
    )
    return commitment


def identity_for(args: argparse.Namespace) -> PersistentCognition:
    return PersistentCognition(
        identity=IdentitySpecification(
            self_id=args.self_id,
            directives=(
                "observe current World evidence before acting",
                "keep Memory distinct from fresh World evidence",
                "close Actions from external consequences",
            ),
            provenance=Provenance(
                source=QUALIFICATION_NAME,
                reference="initial-self-identity",
            ),
        )
    )


def cognition_result_json(result: RelayEngineResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "status": result.status.value,
        "choice_id": result.choice_id,
        "escalated": result.escalated,
        "provider_call_count": result.provider_call_count,
        "elapsed_ns": result.elapsed_ns,
        "elapsed_seconds": result.elapsed_s,
        "soft_wall_time_budget_s": result.soft_wall_time_budget_s,
        "soft_wall_time_budget_exceeded": result.soft_wall_time_budget_exceeded,
        "observed_prompt_tokens": result.observed_prompt_tokens,
        "observed_completion_tokens": result.observed_completion_tokens,
        "attempts": [
            {
                "mode": attempt.mode.value,
                "status": attempt.status.value,
                "choice_id": attempt.choice_id,
                "reason": attempt.reason,
                "elapsed_ns": attempt.elapsed_ns,
                "elapsed_seconds": attempt.elapsed_s,
                "requested_max_output_tokens": attempt.call_facts.requested_max_output_tokens,
                "prompt_tokens": attempt.call_facts.prompt_tokens,
                "completion_tokens": attempt.call_facts.completion_tokens,
                "total_tokens": attempt.call_facts.total_tokens,
                "finish_reason": attempt.call_facts.finish_reason,
            }
            for attempt in result.attempts
        ],
    }


def request_json(
    request: object,
    *,
    model: str = "<served-model-recorded-in-runtime>",
) -> dict[str, object]:
    from adapters.llama_cpp.relay_engine import render_llama_cpp_request

    if not hasattr(request, "choices"):
        raise TerminalQualificationError("request is not a bounded RelayEngine request")
    # This is a content/provenance trace of the exact request shape; it does not
    # send a second provider call.
    rendered = render_llama_cpp_request(
        request,  # type: ignore[arg-type]
        mode=CognitionMode.BOUNDED,
        model=model,
    )
    return jsonable(rendered)  # type: ignore[return-value]


def decision_json(
    decision: ScenarioDecision,
    *,
    request: object | None = None,
    model: str = "<served-model-recorded-in-runtime>",
) -> dict[str, object]:
    result = decision.cognition_result
    return {
        "skill": decision.skill.value,
        "reason": decision.reason,
        "item_name": decision.item_name,
        "destination": (
            decision.destination.destination_id
            if decision.destination is not None
            else None
        ),
        "resolved": decision.resolved,
        "cognition": cognition_result_json(result),
        "request": request_json(request, model=model) if request is not None else None,
    }


def action_json(action: ActionLifecycle) -> dict[str, object]:
    return {
        "action_id": action.action_id,
        "states": [event.state.value for event in action.events],
        "events": [
            {
                "state": event.state.value,
                "at_ns": event.at_ns,
                "provenance": provenance_json(event.provenance),
                "authority": event.authority,
                "deadline_ns": event.deadline_ns,
            }
            for event in action.events
        ],
    }


def skill_run_json(run: SkillRunResult) -> dict[str, object]:
    return {
        "decision": decision_json(run.decision),
        "skill_execution": {
            "execution_id": run.skill_execution.execution_id,
            "skill_id": run.skill_execution.skill_id,
            "intent_id": run.skill_execution.intent_id,
            "state": run.skill_execution.state.value,
            "events": [
                {
                    "state": event.state.value,
                    "at_ns": event.at_ns,
                    "reason": event.reason,
                    "provenance": provenance_json(event.provenance),
                }
                for event in run.skill_execution.events
            ],
        },
        "actions": [action_json(action) for action in run.actions],
        "message_count": len(run.messages),
        "message_types": [type(message).__name__ for message in run.messages],
    }


def make_recovery_present(
    *,
    commitment: IntentCommitment,
    observation: MineflayerObservation,
    blocked_destination: str,
    recovery_destination: str,
) -> object:
    current = observation.provenance
    safe_provenance = Provenance(
        source="controlled-minecraft-terminal-scenario",
        reference="recovery:candidate-destinations",
    )
    blocked_provenance = Provenance(
        source="minecraft-server-intervention",
        reference="recovery:teleport-invalidated-original-progress",
    )
    recovery_provenance = Provenance(
        source=current.source,
        reference=current.reference,
    )
    return build_present(
        intent_commitment=commitment,
        source_revision=observation.seq,
        facts=(
            PresentFact("threat_nearby", True, current),
            PresentFact("health", observation.snapshot.health, current),
            PresentFact(
                "safe_destinations",
                (blocked_destination, recovery_destination),
                safe_provenance,
            ),
            PresentFact(
                "current_destination",
                blocked_destination,
                blocked_provenance,
            ),
            PresentFact("route_catalog_complete", True, safe_provenance),
            PresentFact("viability_acceptable", True, current),
            PresentFact(
                f"route_open:{blocked_destination}",
                False,
                blocked_provenance,
            ),
            PresentFact(
                f"route_open:{recovery_destination}",
                True,
                recovery_provenance,
            ),
        ),
    )


def _last_observation(messages: tuple[MineflayerDecodedMessage, ...]) -> MineflayerObservation:
    observations = [message for message in messages if isinstance(message, MineflayerObservation)]
    if not observations:
        raise TerminalQualificationError("Skill run contained no Mineflayer consequence observation")
    return observations[-1]


async def launch_recorded_session(
    args: argparse.Namespace,
    *,
    phase: str,
) -> RecordedMineflayerSession:
    session = await MineflayerProcessSession.launch(
        MineflayerLaunchConfig(
            host=args.minecraft_host,
            port=args.minecraft_port,
            username=args.username,
            version=args.minecraft_protocol_version,
        ),
        bridge_path=Path(args.repo_root) / "adapters" / "mineflayer" / "bridge.mjs",
        node_executable=args.node,
        startup_timeout_s=args.startup_timeout_s,
    )
    return RecordedMineflayerSession(
        session,
        Path(args.evidence_root) / f"mineflayer-{phase}.jsonl",
    )


def provider_engine(args: argparse.Namespace) -> RelayEngine:
    return RelayEngine(
        LlamaCppRelayProvider(
            endpoint=args.llama_origin.rstrip("/") + "/v1/chat/completions",
            model=args.served_model,
            timeout=args.llama_timeout,
        )
    )


async def run_first_phase(args: argparse.Namespace, tracker: StageTracker) -> dict[str, object]:
    evidence_root = Path(args.evidence_root).resolve()
    persistent_path = Path(args.persistent_path).resolve()
    tracker.set("initialize_persistent_cognition")
    cognition = identity_for(args)
    save_persistent_cognition(persistent_path, cognition)
    initial_bytes = persistent_path.read_bytes()
    commitment = commit_intent()
    engine = provider_engine(args)
    session: RecordedMineflayerSession | None = None
    clock = MonotonicClock()
    try:
        tracker.set("launch_first_mineflayer_session")
        session = await launch_recorded_session(args, phase="first")
        first_session_id = session.started.session_id
        first_bridge_pid = session.process_pid
        tracker.set("ordinary_wait_decision")
        ordinary = await receive_until(
            session,
            lambda observation: observation.kind == "spawn",
            timeout_s=args.evidence_timeout_s,
        )
        ordinary_scenario = scenario(hazard_names=frozenset({"zombie"}), destinations=())
        ordinary_decision = decide_skill(
            ordinary,
            ordinary_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
        )
        if ordinary_decision.skill is not ControlledSkill.WAIT:
            raise TerminalQualificationError("ordinary condition did not select WAIT")

        tracker.set("resource_intervention_and_eat")
        commands_path = evidence_root / "server-commands.jsonl"
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=commands_path,
            command=f"give {args.username} minecraft:bread 2",
            reason="controlled resource intervention: edible inventory",
        )
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=commands_path,
            command=f"data modify entity {args.username} foodLevel set value 7",
            reason="controlled resource intervention: low food",
        )
        resource_observation = await receive_until(
            session,
            lambda observation: (
                observation.snapshot.food <= 10
                and observation_has_item(observation, "bread")
            ),
            timeout_s=args.evidence_timeout_s,
        )
        resource_scenario = scenario(
            hazard_names=frozenset({"zombie"}),
            destinations=(),
        )
        resource_decision = decide_skill(
            resource_observation,
            resource_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
        )
        if resource_decision.skill is not ControlledSkill.EAT:
            raise TerminalQualificationError("resource condition did not select EAT")
        supervisor = ActionSupervisor()
        eat_run = await execute_decision(
            session,
            resource_observation,
            resource_scenario,
            resource_decision,
            intent_commitment=commitment,
            supervisor=supervisor,
            authorization=QUALIFICATION_NAME,
        )
        if eat_run is None or eat_run.skill_execution.state is not SkillState.SUCCEEDED:
            raise TerminalQualificationError("EAT did not close from later food evidence")

        tracker.set("threat_observation_and_model_cognition")
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=commands_path,
            command=(
                f"execute at {args.username} run summon minecraft:zombie "
                "~3 ~ ~ {PersistenceRequired:1b}"
            ),
            reason="controlled threat intervention: nearby persistent zombie",
        )
        threat_observation = await receive_until(
            session,
            lambda observation: any(
                entity.name == "zombie"
                for entity in observation.snapshot.nearby_entities
            ),
            timeout_s=args.evidence_timeout_s,
        )
        hazard_names = frozenset(
            entity.name
            for entity in threat_observation.snapshot.nearby_entities
            if entity.name == "zombie"
        )
        if not hazard_names:
            raise TerminalQualificationError("controlled threat was not present in fresh evidence")
        start = threat_observation.snapshot.position
        from adapters.mineflayer.python_protocol import MineflayerPosition

        first_destinations = (
            destination(
                "cave",
                position=MineflayerPosition(x=start.x + 10, y=start.y, z=start.z),
                description="Reachable cave with explicit shelter evidence.",
                reference="scenario:first:cave",
            ),
            destination(
                "ridge",
                position=MineflayerPosition(x=start.x, y=start.y, z=start.z - 10),
                description="Reachable exposed ridge with no shelter evidence.",
                reference="scenario:first:ridge",
            ),
        )
        threat_scenario = scenario(
            hazard_names=hazard_names,
            destinations=first_destinations,
        )
        first_request = build_flee_destination_request(
            threat_observation,
            threat_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
            retained_memories=(),
        )
        first_decision = decide_skill(
            threat_observation,
            threat_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
            relay_engine=engine,
        )
        if first_decision.skill is not ControlledSkill.FLEE or not first_decision.resolved:
            raise TerminalQualificationError("real RelayEngine did not resolve first FLEE destination")
        if first_decision.cognition_result is None:
            raise TerminalQualificationError("first FLEE did not record a RelayEngine result")

        selected = first_decision.destination
        if selected is None:
            raise TerminalQualificationError("first FLEE has no selected destination")
        selected_dx = selected.position.x - start.x
        selected_dz = selected.position.z - start.z
        beyond_x = selected.position.x + (10 if selected_dx >= 0 else -10)
        beyond_z = selected.position.z + (10 if selected_dz >= 0 else -10)

        async def falsify_expected_progress() -> None:
            await write_server_command(
                control_path=Path(args.server_control),
                evidence_path=commands_path,
                command=(
                    f"tp {args.username} {beyond_x:.3f} "
                    f"{selected.position.y:.3f} {beyond_z:.3f}"
                ),
                reason=(
                    "controlled mismatch intervention after FLEE forward "
                    "issuance: teleport beyond selected destination"
                ),
                settle_s=0.1,
            )

        session.set_forward_intervention(falsify_expected_progress)
        tracker.set("first_flee_mismatch_execution")
        first_flee_run = await execute_decision(
            session,
            threat_observation,
            threat_scenario,
            first_decision,
            intent_commitment=commitment,
            supervisor=supervisor,
            authorization=QUALIFICATION_NAME,
        )
        await session.wait_forward_intervention()
        if first_flee_run is None or first_flee_run.skill_execution.state is not SkillState.FAILED:
            raise TerminalQualificationError(
                "first FLEE did not fail on the contradictory external consequence"
            )
        failure_observation = _last_observation(first_flee_run.messages)
        initial_distance = _distance(start, selected.position)
        actual_distance = _distance(
            failure_observation.snapshot.position,
            selected.position,
        )
        observed_progress = initial_distance - actual_distance >= threat_scenario.flee_min_progress
        comparison = compare_consequence(
            ExpectedEvidence("movement_progress", True),
            ObservedEvidence(
                "movement_progress",
                observed_progress,
                failure_observation.provenance,
            ),
        )
        if comparison.kind.value != "mismatch":
            raise TerminalQualificationError(
                "the actual Mineflayer consequence did not contradict expected progress"
            )

        tracker.set("fresh_reprojection_and_local_recovery")
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=commands_path,
            command=(
                f"execute at {args.username} run summon minecraft:zombie "
                "~3 ~ ~ {PersistenceRequired:1b}"
            ),
            reason="controlled recovery intervention: restore nearby threat at new position",
        )
        recovery_observation = await receive_until(
            session,
            lambda observation: any(
                entity.name == "zombie"
                for entity in observation.snapshot.nearby_entities
            ),
            timeout_s=args.evidence_timeout_s,
        )
        recovery_id = "ridge" if selected.destination_id == "cave" else "cave"
        present = make_recovery_present(
            commitment=commitment,
            observation=recovery_observation,
            blocked_destination=selected.destination_id,
            recovery_destination=recovery_id,
        )
        admission, reconsideration_request = admit_reach_safety_reconsideration(
            present=present,  # type: ignore[arg-type]
            commitment=commitment,
            material_change_key=f"route_open:{selected.destination_id}",
            at_ns=clock.now_ns(),
        )
        if admission.kind is not ReconsiderationAdmissionKind.LOCAL_RECOVERY:
            raise TerminalQualificationError(
                f"mismatch did not enter local recovery: {admission.kind.value}"
            )
        if reconsideration_request is not None or commitment.current_intent is None:
            raise TerminalQualificationError("local recovery changed Current Intent unexpectedly")
        narrowed = narrow_for_flee(present)  # type: ignore[arg-type]
        recovered_binding = bind_flee_destination(narrowed)
        if recovered_binding.destination != recovery_id:
            raise TerminalQualificationError("reprojected FLEE did not select the open recovery route")
        recovery_position = recovery_observation.snapshot.position
        recovery_destination = destination(
            recovery_id,
            position=MineflayerPosition(
                x=(
                    recovery_position.x + 10
                    if recovery_id == "cave"
                    else recovery_position.x
                ),
                y=recovery_position.y,
                z=(
                    recovery_position.z - 10
                    if recovery_id == "ridge"
                    else recovery_position.z
                ),
            ),
            description="Open recovery route with fresh consequence evidence and prior route experience.",
            reference="scenario:recovery:open-route",
        )
        recovery_scenario = scenario(
            hazard_names=hazard_names,
            destinations=(recovery_destination,),
        )
        recovery_decision = decide_skill(
            recovery_observation,
            recovery_scenario,
            intent_id=commitment.current_intent.intent_id,
        )
        if recovery_decision.skill is not ControlledSkill.FLEE:
            raise TerminalQualificationError("fresh recovery observation did not select FLEE")
        session.set_forward_intervention(None)
        recovery_run = await execute_decision(
            session,
            recovery_observation,
            recovery_scenario,
            recovery_decision,
            intent_commitment=commitment,
            supervisor=supervisor,
            authorization=QUALIFICATION_NAME,
        )
        if recovery_run is None or recovery_run.skill_execution.state is not SkillState.SUCCEEDED:
            raise TerminalQualificationError("local recovery FLEE did not close from movement evidence")

        tracker.set("governed_memory_write")
        integrated = retain_successful_flee_memory(
            cognition,
            recovery_run,
            integration_provenance=Provenance(
                source=QUALIFICATION_NAME,
                reference="explicit-memory-integration:successful-recovery-flee",
            ),
        )
        if len(integrated.memories) != 1:
            raise TerminalQualificationError("terminal transaction retained more than one Memory")
        save_persistent_cognition(persistent_path, integrated)
        durable_bytes = persistent_path.read_bytes()
        if durable_bytes == initial_bytes:
            raise TerminalQualificationError("governed Memory write did not change durable bytes")
        memory = integrated.memories[0]
        phase_report = {
            "phase": "first",
            "self_process": {
                "pid": os.getpid(),
                "started_at": utc_now(),
                "mineflayer_pid": first_bridge_pid,
                "mineflayer_session_id": first_session_id,
            },
            "identity": {
                "self_id": cognition.identity.self_id,
                "directives": list(cognition.identity.directives),
                "provenance": provenance_json(cognition.identity.provenance),
            },
            "persistent_cognition": {
                "path": str(persistent_path),
                "initial_memory_count": 0,
                "after_memory_count": len(integrated.memories),
                "durable_sha256": hashlib.sha256(durable_bytes).hexdigest(),
                "durable_bytes": len(durable_bytes),
                "memory": {
                    "memory_id": memory.memory_id,
                    "content": memory.content,
                    "source_provenance": provenance_json(memory.source_provenance),
                    "integration_provenance": provenance_json(memory.integration_provenance),
                    "semantic_type": "Memory",
                },
            },
            "ordinary": {
                "observation": message_json(ordinary),
                "decision": decision_json(ordinary_decision),
                "model_called": False,
            },
            "resource": {
                "observation": message_json(resource_observation),
                "decision": decision_json(resource_decision),
                "skill_run": skill_run_json(eat_run),
                "later_food": [
                    message_json(message)
                    for message in eat_run.messages
                    if isinstance(message, MineflayerObservation)
                    and message.snapshot.food > resource_observation.snapshot.food
                ],
            },
            "threat": {
                "observation": message_json(threat_observation),
                "candidate_destinations": [
                    {
                        "destination_id": item.destination_id,
                        "position": jsonable(item.position),
                        "description": item.description,
                        "provenance": provenance_json(item.provenance),
                    }
                    for item in first_destinations
                ],
                "request": request_json(first_request, model=args.served_model),
                "decision": decision_json(
                    first_decision,
                    request=first_request,
                    model=args.served_model,
                ),
                "cognition_escalation": {
                    "reason": "multiple candidate destinations were not locally resolvable",
                    "relay_engine_invoked": True,
                    "bounded_calls": sum(
                        attempt.mode is CognitionMode.BOUNDED
                        for attempt in first_decision.cognition_result.attempts  # type: ignore[union-attr]
                    ),
                    "think_calls": sum(
                        attempt.mode is CognitionMode.THINK
                        for attempt in first_decision.cognition_result.attempts  # type: ignore[union-attr]
                    ),
                },
            },
            "mismatch_reprojection_recovery": {
                "expected": jsonable(comparison.expected),
                "observed": jsonable(comparison.observed),
                "comparison": comparison.kind.value,
                "first_flee_skill_state": first_flee_run.skill_execution.state.value,
                "first_flee_actions": [action_json(action) for action in first_flee_run.actions],
                "recovery_observation": message_json(recovery_observation),
                "present_source_revision": present.source_revision,  # type: ignore[union-attr]
                "old_observation_projection_current_after_recovery": projection_is_current(
                    present,  # type: ignore[arg-type]
                    current_source_revision=recovery_observation.seq - 1,
                ),
                "reconsideration_admission": admission.kind.value,
                "reconsideration_request_created": reconsideration_request is not None,
                "current_intent_preserved": commitment.current_intent.intent_id,
                "reprojected_destination": recovered_binding.destination,
                "recovery_skill_run": skill_run_json(recovery_run),
            },
            "event_driven": {
                "raw_received_events": session.raw_received_events,
                "admitted_decision_epochs": session.admitted_decision_epochs,
                "received_by_type": dict(session.received_by_type),
            },
            "process_exit_intent_at": utc_now(),
        }
        write_json(evidence_root / "phase-first.json", phase_report)
        return phase_report
    finally:
        if session is not None:
            try:
                await session.shutdown()
            except Exception:
                try:
                    await session.terminate()
                except Exception:
                    pass


async def run_restart_phase(args: argparse.Namespace, tracker: StageTracker) -> dict[str, object]:
    evidence_root = Path(args.evidence_root).resolve()
    persistent_path = Path(args.persistent_path).resolve()
    first_report = read_json(evidence_root / "phase-first.json")
    first_pid = first_report["self_process"]["pid"]
    if not isinstance(first_pid, int):
        raise TerminalQualificationError("first Self PID is missing from phase report")
    try:
        os.kill(first_pid, 0)
    except ProcessLookupError:
        first_process_alive = False
    except PermissionError:
        first_process_alive = True
    else:
        first_process_alive = True
    if first_process_alive:
        raise TerminalQualificationError("first Self process did not terminate before restart")

    tracker.set("reload_durable_cognition")
    reloaded = load_persistent_cognition(persistent_path)
    if reloaded.identity.self_id != args.self_id or len(reloaded.memories) != 1:
        raise TerminalQualificationError("restart did not recover the same identity and one Memory")
    memory = reloaded.memories[0]
    before_sha256 = sha256_file(persistent_path)
    commitment = commit_intent()
    engine = provider_engine(args)
    session: RecordedMineflayerSession | None = None
    try:
        tracker.set("launch_second_mineflayer_session")
        session = await launch_recorded_session(args, phase="restart")
        second_session_id = session.started.session_id
        second_bridge_pid = session.process_pid
        if second_session_id == first_report["self_process"]["mineflayer_session_id"]:
            raise TerminalQualificationError("restart reused the first Mineflayer session id")
        tracker.set("fresh_post_restart_observation")
        await receive_until(
            session,
            lambda observation: observation.kind == "spawn",
            timeout_s=args.evidence_timeout_s,
        )
        commands_path = evidence_root / "server-commands.jsonl"
        await write_server_command(
            control_path=Path(args.server_control),
            evidence_path=commands_path,
            command=(
                f"execute at {args.username} run summon minecraft:zombie "
                "~3 ~ ~ {PersistenceRequired:1b}"
            ),
            reason="post-restart controlled threat intervention for fresh decision",
        )
        later_observation = await receive_until(
            session,
            lambda observation: any(
                entity.name == "zombie"
                for entity in observation.snapshot.nearby_entities
            ),
            timeout_s=args.evidence_timeout_s,
        )
        from adapters.mineflayer.python_protocol import MineflayerPosition

        current = later_observation.snapshot.position
        memory_destination_id = memory_destination_id_from_content(memory)
        if memory_destination_id not in {"cave", "ridge"}:
            raise TerminalQualificationError(
                "reloaded Memory has no controlled destination identity"
            )
        prior_description = (
            "Open protected route matching a prior observed successful recovery destination."
        )
        unremembered_description = "Unverified route with no current shelter evidence."
        later_destinations = (
            destination(
                "ridge",
                position=MineflayerPosition(x=current.x, y=current.y, z=current.z - 10),
                description=(
                    prior_description
                    if memory_destination_id == "ridge"
                    else unremembered_description
                ),
                reference="scenario:restart:ridge",
            ),
            destination(
                "cave",
                position=MineflayerPosition(x=current.x + 10, y=current.y, z=current.z),
                description=(
                    prior_description
                    if memory_destination_id == "cave"
                    else unremembered_description
                ),
                reference="scenario:restart:cave",
            ),
        )
        later_scenario = scenario(
            hazard_names=frozenset({"zombie"}),
            destinations=later_destinations,
        )
        later_request = build_flee_destination_request(
            later_observation,
            later_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
            retained_memories=reloaded.memories,
        )
        memory_choice = choose_memory_matching_destination(later_request)
        if memory_choice != memory_destination_id:
            raise TerminalQualificationError("reloaded Memory did not identify a later admissible destination")
        tracker.set("post_restart_model_decision_and_action")
        later_decision = decide_skill(
            later_observation,
            later_scenario,
            intent_id=commitment.current_intent.intent_id,  # type: ignore[union-attr]
            relay_engine=engine,
            retained_memories=reloaded.memories,
        )
        if later_decision.skill is not ControlledSkill.FLEE or not later_decision.resolved:
            raise TerminalQualificationError("post-restart decision did not resolve FLEE")
        if later_decision.destination is None or later_decision.destination.destination_id != memory_choice:
            raise TerminalQualificationError(
                "post-restart RelayEngine decision did not use retained destination experience"
            )
        supervisor = ActionSupervisor()
        later_run = await execute_decision(
            session,
            later_observation,
            later_scenario,
            later_decision,
            intent_commitment=commitment,
            supervisor=supervisor,
            authorization=QUALIFICATION_NAME,
        )
        if later_run is None or later_run.skill_execution.state is not SkillState.SUCCEEDED:
            raise TerminalQualificationError("post-restart FLEE did not close from fresh movement evidence")
        after_sha256 = sha256_file(persistent_path)
        if after_sha256 != before_sha256:
            raise TerminalQualificationError("post-restart decision changed durable Memory without explicit integration")
        phase_report = {
            "qualification": "TERMINAL PASS / LIVE QUALIFIED",
            "qualified": True,
            "phase": "restart",
            "self_process": {
                "first_pid": first_pid,
                "first_process_alive_at_restart_check": first_process_alive,
                "second_pid": os.getpid(),
                "second_started_at": utc_now(),
                "first_mineflayer_pid": first_report["self_process"]["mineflayer_pid"],
                "second_mineflayer_pid": second_bridge_pid,
                "first_mineflayer_session_id": first_report["self_process"]["mineflayer_session_id"],
                "second_mineflayer_session_id": second_session_id,
                "self_id_same": reloaded.identity.self_id == args.self_id,
                "mineflayer_session_changed": (
                    second_session_id != first_report["self_process"]["mineflayer_session_id"]
                ),
                "process_changed": first_pid != os.getpid(),
            },
            "persistent_cognition": {
                "path": str(persistent_path),
                "reloaded_self_id": reloaded.identity.self_id,
                "reloaded_memory_count": len(reloaded.memories),
                "memory": {
                    "memory_id": memory.memory_id,
                    "content": memory.content,
                    "source_provenance": provenance_json(memory.source_provenance),
                    "integration_provenance": provenance_json(memory.integration_provenance),
                    "semantic_type": "Memory",
                },
                "durable_sha256_before": before_sha256,
                "durable_sha256_after": after_sha256,
            },
            "later_decision": {
                "fresh_observation": message_json(later_observation),
                "fresh_observation_provenance": provenance_json(later_observation.provenance),
                "retained_memory_provenance": {
                    "source": memory.source_provenance.source,
                    "reference": memory.source_provenance.reference,
                    "integration": provenance_json(memory.integration_provenance),
                },
                "memory_choice": memory_choice,
                "request": request_json(later_request, model=args.served_model),
                "decision": decision_json(
                    later_decision,
                    request=later_request,
                    model=args.served_model,
                ),
                "skill_run": skill_run_json(later_run),
                "memory_and_world_are_separate": True,
            },
            "event_driven": {
                "raw_received_events": session.raw_received_events,
                "admitted_decision_epochs": session.admitted_decision_epochs,
                "received_by_type": dict(session.received_by_type),
            },
            "canonical_terminal_invocation_count": 1,
            "retry_count": 0,
            "replay_count": 0,
            "evidence_root": str(evidence_root),
            "terminal_emitted_report": str(evidence_root / "terminal-report.json"),
        }
        first = read_json(evidence_root / "phase-first.json")
        preflight = read_json(evidence_root / "preflight.json")
        report = {
            "qualification": "TERMINAL PASS / LIVE QUALIFIED",
            "qualified": True,
            "repository": preflight["repository"],
            "working_tree": preflight["working_tree"],
            "runtime": preflight["runtime"],
            "self": {
                "self_id": reloaded.identity.self_id,
                "identity": reloaded.identity.directives,
                "persistent_path": str(persistent_path),
                "first_process_pid": first_pid,
                "second_process_pid": os.getpid(),
            },
            "scenario": preflight["scenario"],
            "skills": ["WAIT", "EAT", "FLEE"],
            "phases": {
                "ordinary": first["ordinary"],
                "resource": first["resource"],
                "threat": first["threat"],
                "mismatch_reprojection_recovery": first["mismatch_reprojection_recovery"],
                "restart": phase_report,
            },
            "memory": {
                "retained_experience": first["persistent_cognition"]["memory"],
                "explicit_integration": True,
                "automatic_skill_to_memory": False,
            },
            "event_driven_counts": {
                "first": first["event_driven"],
                "restart": phase_report["event_driven"],
                "relay_engine_calls": sum(
                    len(item["attempts"])
                    for item in (
                        first["threat"]["decision"]["cognition"],
                        phase_report["later_decision"]["decision"]["cognition"],
                    )
                    if item is not None
                ),
                "bounded_calls": sum(
                    sum(attempt["mode"] == "bounded" for attempt in item["attempts"])
                    for item in (
                        first["threat"]["decision"]["cognition"],
                        phase_report["later_decision"]["decision"]["cognition"],
                    )
                    if item is not None
                ),
                "think_calls": sum(
                    sum(attempt["mode"] == "think" for attempt in item["attempts"])
                    for item in (
                        first["threat"]["decision"]["cognition"],
                        phase_report["later_decision"]["decision"]["cognition"],
                    )
                    if item is not None
                ),
            },
            "evidence_classes": {
                "deterministic_invariant_evidence": [
                    "raw event admission is distinct from decision epochs",
                    "Action lifecycle closes from Mineflayer effect results",
                    "Persistent Cognition identity and Memory schema reload",
                ],
                "model_system_quality_observations": [
                    "actual llama.cpp RelayEngine bounded/THINK attempt facts",
                    "candidate request, selected destination, token and finish facts",
                ],
                "dynamic_simulation_behavior": [
                    "WAIT/EAT/FLEE situation-dependent selection",
                    "teleport mismatch, Present reprojection, local recovery",
                ],
                "live_minecraft_external_qualification": [
                    "Minecraft 26.1 server and Mineflayer sessions",
                    "food increase and movement consequences from fresh observations",
                ],
            },
            "canonical_terminal_invocation_count": 1,
            "retry_count": 0,
            "replay_count": 0,
            "evidence_root": str(evidence_root),
            "terminal_emitted_report": str(evidence_root / "terminal-report.json"),
            "server_commands": str(evidence_root / "server-commands.jsonl"),
        }
        write_json(evidence_root / "terminal-report.json", report)
        return report
    finally:
        if session is not None:
            try:
                await session.shutdown()
            except Exception:
                try:
                    await session.terminate()
                except Exception:
                    pass


def memory_destination_id_from_content(memory: Memory) -> str | None:
    try:
        payload = json.loads(memory.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    destination_id = payload.get("destination_id")
    return destination_id if isinstance(destination_id, str) else None


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the one-shot RelaySelf #141 live Minecraft terminal composition."
    )
    result.add_argument("--phase", choices=("prepare", "preflight", "first", "restart"), required=True)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--evidence-root", required=True)
    result.add_argument("--server-root")
    result.add_argument("--server-source-root")
    result.add_argument("--minecraft-jar")
    result.add_argument("--minecraft-version", default="26.1")
    result.add_argument("--minecraft-host", default="127.0.0.1")
    result.add_argument("--minecraft-port", type=int, default=25565)
    result.add_argument("--minecraft-protocol-version")
    result.add_argument("--server-control")
    result.add_argument("--server-log")
    result.add_argument("--authority-path")
    result.add_argument("--runtime-artifacts-path")
    result.add_argument("--minecraft-pid", type=int)
    result.add_argument("--node", default="node")
    result.add_argument("--npm", default="npm")
    result.add_argument("--java")
    result.add_argument("--llama")
    result.add_argument("--llama-origin", default="http://127.0.0.1:8080")
    result.add_argument("--llama-port", type=int, default=8080)
    result.add_argument("--llama-pid", type=int)
    result.add_argument("--model", required=True)
    result.add_argument("--served-model")
    result.add_argument("--llama-timeout", type=float, default=60.0)
    result.add_argument("--self-id", default="relay-self-141")
    result.add_argument("--username", default="RelaySelf")
    result.add_argument("--persistent-path")
    result.add_argument("--startup-timeout-s", type=float, default=15.0)
    result.add_argument("--evidence-timeout-s", type=float, default=8.0)
    return result


def validate_phase_args(args: argparse.Namespace) -> None:
    args.evidence_root = str(Path(args.evidence_root).resolve())
    Path(args.evidence_root).mkdir(parents=True, exist_ok=True)
    args.repo_root = str(Path(args.repo_root).resolve())
    if args.persistent_path is None:
        args.persistent_path = str(Path(args.evidence_root) / "persistent-cognition.json")
    if args.phase in {"first", "restart"}:
        for name in ("server_control", "served_model"):
            if not getattr(args, name):
                raise TerminalQualificationError(f"--{name.replace('_', '-')} is required")
    if args.phase == "preflight":
        for name in ("server_root", "server_log", "java", "llama", "minecraft_pid", "llama_pid"):
            if not getattr(args, name, None):
                raise TerminalQualificationError(f"preflight requires --{name.replace('_', '-')}")
    if args.phase == "prepare":
        for name in ("server_root", "minecraft_jar"):
            if not getattr(args, name, None):
                raise TerminalQualificationError(f"prepare requires --{name.replace('_', '-')}")


async def async_main(args: argparse.Namespace) -> int:
    validate_phase_args(args)
    if args.phase == "prepare":
        prepared = prepare_server_root(
            server_root=Path(args.server_root).resolve(),
            minecraft_jar=Path(args.minecraft_jar).resolve(),
            source_root=(
                Path(args.server_source_root).resolve()
                if args.server_source_root
                else None
            ),
            port=args.minecraft_port,
        )
        write_json(Path(args.evidence_root) / "server-setup.json", prepared)
        print(json.dumps(prepared, ensure_ascii=False, sort_keys=True))
        return 0
    if args.phase == "preflight":
        preflight = run_preflight(args)
        print(json.dumps(preflight, ensure_ascii=False, sort_keys=True))
        return 0

    tracker = StageTracker(args.phase)
    try:
        if args.phase == "first":
            report = await run_first_phase(args, tracker)
        else:
            report = await run_restart_phase(args, tracker)
    except Exception as exc:
        failure = {
            "qualification": QUALIFICATION_NAME,
            "transaction_started": True,
            "phase": tracker.phase,
            "first_concrete_failure_stage": tracker.stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timestamp": utc_now(),
            "retry_count": 0,
            "replay_count": 0,
        }
        write_json(
            Path(args.evidence_root) / f"failure-{tracker.phase}.json",
            failure,
        )
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    args = parser().parse_args()
    try:
        return asyncio.run(async_main(args))
    except Exception as exc:
        evidence_root = Path(args.evidence_root).resolve()
        evidence_root.mkdir(parents=True, exist_ok=True)
        failure = {
            "qualification": QUALIFICATION_NAME,
            "transaction_started": args.phase in {"first", "restart"},
            "phase": args.phase,
            "first_concrete_failure_stage": "argument_or_preflight",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timestamp": utc_now(),
            "retry_count": 0,
            "replay_count": 0,
        }
        write_json(evidence_root / f"failure-{args.phase}.json", failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
