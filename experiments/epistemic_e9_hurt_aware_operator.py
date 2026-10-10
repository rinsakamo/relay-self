"""Lane A E9: next operator-owned one-shot, old-zombie hurt aware.

NO server install/start/stop, EULA action, World mutation, Self Action, LLM or
autonomous repeat. The owned LOCAL operator, not this tool or GitHub Actions,
must separately opt into --run against their existing disposable Minecraft.
Even a native-looking valid trace is UNATTESTED physical evidence and CLI
exits 3; E5's 36-run science stays NOT_RUN / NOT_AUTHORIZED.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerConnectionEnd,
    MineflayerEntityHurt,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerShutdownAck,
    MineflayerStreamDecoder,
    encode_observe,
    encode_shutdown,
)
from experiments import epistemic_e7_native_trace_gate as e7
from experiments import epistemic_e8_operator_calibration as e8
from experiments import epistemic_e9_native_hurt_gate as e9gate

# The parent E8 manifest is frozen; E9 authority is Issue #549 and this
# successor source commit. Never reinterpret E8's manifest/result.
VERSION = "AC-A-E9-NATIVE-ZOMBIE-HURT-SUCCESSOR-v1"
MANIFEST = e8.MANIFEST
MANIFEST_SHA256 = e8.MANIFEST_SHA256

CONFIRMATION = "E9-I-OWN-LOCAL-TEST-WORLD"
MAX_BYTES = e7.MAX_BYTES
MAX_FRAMES = e7.MAX_FRAMES
PROMPT_FAR = (
    "SERVER CONSOLE (manual, after checking no other zombies): "
    "execute at RelaySelf run summon minecraft:zombie ~1.8 ~ ~ "
    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}"
)
PROMPT_GONE = "SERVER CONSOLE (manual, disposable world ONLY): kill @e[type=minecraft:zombie]"
PROMPT_NEAR = (
    "SERVER CONSOLE (manual, NEW zombie; if collision displaces bot, FAIL): "
    "execute at RelaySelf run summon minecraft:zombie ~0.2 ~ ~ "
    "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}"
)


class E9Blocked(ValueError):
    """No physical calibration qualification from this input."""


class ProcessLike(Protocol):
    stdin: object
    stdout: object
    returncode: int | None

    async def wait(self) -> int: ...


@dataclass(frozen=True, slots=True)
class CandidateReceipt:
    classification: str
    physically_authenticated: bool
    e5_physical_study_authorized: bool
    action_issued: bool
    world_server_started_by_e8: bool
    minecraft_world_mutation_sent_by_e8: bool
    source_sha256: str
    source_bytes: int
    audited_prefix_bytes: int
    frames: int
    hurt_event_count: int
    observed_close_suffix: str
    session_id: str
    first_probe_seq: int
    second_probe_seq: int
    far_entity_id: int
    near_entity_id: int
    bridge_exit_code: int
    physical_geometry: str


def digest(obj: object = MANIFEST) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _frozen() -> None:
    e8._frozen()
    if digest() != MANIFEST_SHA256 or e7.digest() != MANIFEST["e7_manifest_sha256"]:
        raise E9Blocked("E7/E8 prospective source identity drift")


def validate_run_gate(
    run: bool,
    confirmation: str | None,
    raw_path: Path | None,
    report_path: Path | None,
    *,
    environ: dict[str, str] | None = None,
) -> None:
    """No subprocess can be attempted from the default or CI CLI."""
    _frozen()
    env = dict(os.environ if environ is None else environ)
    if run is not True or confirmation != CONFIRMATION:
        raise E9Blocked("new explicit local operator --run/--confirmation required")
    if env.get("CI") or env.get("GITHUB_ACTIONS") or env.get("NODE_OPTIONS"):
        raise E9Blocked("CI and NODE_OPTIONS/test preloads are forbidden for physical E8")
    if raw_path is None or report_path is None:
        raise E9Blocked("new distinct --raw and --report evidence outputs required")
    if raw_path == report_path or raw_path.exists() or report_path.exists():
        raise E9Blocked("evidence destination already exists or paths overlap")
    if raw_path.suffix != ".jsonl" or report_path.suffix != ".json":
        raise E9Blocked("raw JSONL and report JSON output suffix required")
    if not raw_path.parent.is_dir() or not report_path.parent.is_dir():
        raise E9Blocked("evidence directories must exist; never provision or overwrite")


async def capture_one(
    process: ProcessLike,
    raw_writer: BinaryIO,
    *,
    message_timeout_s: float = 90.0,
    prompts: list[str] | None = None,
) -> CandidateReceipt:
    """One source-native session, exactly two read-only requests, no retry.

    This function does NOT start a process and can be tested with a fake
    pre-scripted pipe. Only the separate, CLI-guarded run path may launch.
    """
    _frozen()
    if (
        type(message_timeout_s) not in (int, float)
        or not 0 < message_timeout_s <= 120
        or process.stdin is None or process.stdout is None
    ):
        raise E9Blocked("invalid bounded process transport")
    prompts = prompts if prompts is not None else []
    decoder = MineflayerStreamDecoder()
    source = bytearray()
    frames = 0
    hurt_event_count = 0

    async def next_frame():
        nonlocal frames
        try:
            line = await asyncio.wait_for(
                process.stdout.readline(), timeout=message_timeout_s
            )
        except TimeoutError as exc:
            raise E9Blocked("bounded native event/probe deadline expired") from exc
        if type(line) is not bytes or not line.endswith(b"\n") or not line:
            raise E9Blocked("owned Mineflayer stdout ended or malformed")
        if b"\r" in line or len(source) + len(line) > MAX_BYTES or frames >= MAX_FRAMES:
            raise E9Blocked("native source exceeds immutable 1MB/256-frame bound")
        source.extend(line)
        raw_writer.write(line)
        raw_writer.flush()
        frames += 1
        try:
            return decoder.decode(line.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise E9Blocked("existing MineflayerStreamDecoder rejected raw source") from exc

    async def send_nonaction(command: str) -> None:
        if not (
            command.startswith('{"request_id":"e7:') and '"type":"observe"' in command
            or command == encode_shutdown()
        ):
            raise E9Blocked("physical E8 transport can send ONLY 2 observes or shutdown")
        process.stdin.write(command.encode("utf-8"))
        await process.stdin.drain()

    def manual(message: str) -> None:
        prompts.append(message)
        print(message, flush=True)

    async def until(kind: str, *, target_cm: int | None = None,
                    expected_id: int | None = None, absence: bool = False):
        nonlocal hurt_event_count
        for _ in range(MAX_FRAMES):
            frame = await next_frame()
            if isinstance(frame, MineflayerEntityHurt):
                # Only the old zombie may emit hurt when operator kills it.
                # Hurt alone is NEVER proof of entityGone/absence.
                if not (
                    kind == "gone" and expected_id is not None
                    and frame.entity_id == expected_id
                    and frame.source_entity_id is None
                    and frame.actor_entity_id != expected_id
                    and hurt_event_count == 0
                ):
                    raise E9Blocked("unqualified native hurt phase/id/duplicate")
                hurt_event_count += 1
                continue
            if not isinstance(frame, MineflayerObservation):
                raise E9Blocked("unexpected native command/error/terminal frame")
            if kind == "spawn" and frame.kind == "spawn":
                return frame, None
            if kind != "spawn" and frame.kind == "probe":
                if frame.request_id != (
                    e7.MANIFEST["first_request_id"] if kind == "far_probe"
                    else e7.MANIFEST["second_request_id"] if kind == "near_probe"
                    else None
                ):
                    raise E9Blocked("unexpected/early/mismatched correlated probe")
            if kind != "spawn" and frame.kind in ("death", "respawn", "forcedMove"):
                raise E9Blocked("native physics disrupted by death/respawn/forced move")
            if kind == "spawn" and frame.kind != "spawn":
                raise E9Blocked("bridge did not provide immediate native spawn")
            if kind in ("far_event", "gone", "near_event") and frame.kind != "entities":
                if frame.kind in ("health", "time", "inventory", "move"):
                    continue
                raise E9Blocked("native unsolicited entity-change event missing")
            if (
                kind in ("far_probe", "near_probe") and frame.kind != "probe"
            ):
                if frame.kind in ("entities", "health", "time", "inventory", "move"):
                    continue
                raise E9Blocked("correlated probe source missing")
            if frame.kind not in ("entities", "probe"):
                continue
            try:
                fact = e7._zombie(frame.snapshot, allow_absent=absence)
            except e7.E7Rejected as exc:
                raise E9Blocked("typed zombie geometry/coverage invalid") from exc
            if absence:
                if fact is None:
                    return frame, None
                if fact[0].entity_id != expected_id:
                    raise E9Blocked("source entity was replaced without witnessed disappearance")
                continue
            if fact is None:
                raise E9Blocked("expected exact target missing")
            entity, cm = fact
            if target_cm is not None and cm != target_cm:
                raise E9Blocked("observed actual geometry differs from requested centimeters")
            if expected_id is not None:
                if kind == "near_event" and entity.entity_id == expected_id:
                    raise E9Blocked("near target must be NEW entity")
                if kind != "near_event" and entity.entity_id != expected_id:
                    raise E9Blocked("correlated probe targeted different entity")
            return frame, entity.entity_id
        raise E9Blocked("native frame budget exhausted")

    started = await next_frame()
    if (
        not isinstance(started, MineflayerAdapterStarted)
        or started.seq != 0 or started.config.host != "127.0.0.1"
        or started.config.version != "1.21.8"
        or started.config.username != "RelaySelf"
    ):
        raise E9Blocked("local genuine 1.21.8 bridge session not established")
    spawn, _ = await until("spawn")
    manual(PROMPT_FAR)
    far_event, far_id = await until("far_event", target_cm=180)
    e7._stationary(far_event, spawn)
    await send_nonaction(encode_observe(e7.MANIFEST["first_request_id"]))
    far_probe, _ = await until("far_probe", target_cm=180, expected_id=far_id)
    e7._stationary(far_probe, spawn)

    manual(PROMPT_GONE)
    gone_event, _ = await until("gone", absence=True, expected_id=far_id)
    e7._stationary(gone_event, spawn)
    manual(PROMPT_NEAR)
    near_event, near_id = await until("near_event", target_cm=20, expected_id=far_id)
    e7._stationary(near_event, spawn)
    await send_nonaction(encode_observe(e7.MANIFEST["second_request_id"]))
    near_probe, _ = await until("near_probe", target_cm=20, expected_id=near_id)
    e7._stationary(near_probe, spawn)

    await send_nonaction(encode_shutdown())
    ack = await next_frame()
    if not isinstance(ack, MineflayerShutdownAck):
        raise E9Blocked("actual bridge did not give exact shutdown ACK")
    ack_prefix_length = len(source)
    try:
        tail = await asyncio.wait_for(process.stdout.readline(), timeout=10)
    except TimeoutError as exc:
        raise E9Blocked("no clean native bridge EOF after shutdown ACK") from exc
    close_suffix = "NONE"
    if tail:
        # Original complete stdout is preserved and independently typed;
        # E7's strict final-ACK qualified prefix is never spliced silently.
        if type(tail) is not bytes or not tail.endswith(b"\n"):
            raise E9Blocked("noncanonical trailing native close event")
        source.extend(tail)
        raw_writer.write(tail)
        raw_writer.flush()
        frames += 1
        try:
            ending = decoder.decode(tail.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise E9Blocked("native close source invalid") from exc
        if not isinstance(ending, MineflayerConnectionEnd):
            raise E9Blocked("unexpected message after native shutdown ACK")
        close_suffix = "connection_end"
        try:
            final = await asyncio.wait_for(process.stdout.readline(), timeout=10)
        except TimeoutError as exc:
            raise E9Blocked("bridge emitted close but did not finish stdout") from exc
        if final:
            source.extend(final)
            raw_writer.write(final)
            raw_writer.flush()
            raise E9Blocked("unqualified additional native output after close")
    try:
        code = await asyncio.wait_for(process.wait(), timeout=10)
    except TimeoutError as exc:
        raise E9Blocked("native bridge did not exit after ACK/close") from exc
    if code != 0:
        raise E9Blocked("native bridge shutdown exit was nonzero")
    try:
        audited = e9gate.audit_jsonl(bytes(source[:ack_prefix_length]))
    except e7.E7Rejected as exc:
        raise E9Blocked("full ACK-terminated prefix failed E7 exact typed gate") from exc
    if audited.classification != "UNATTESTED_NATIVE_TRACE" or audited.hurt_event_count != hurt_event_count:
        raise E9Blocked("E7 native source trust ceiling was violated")
    return CandidateReceipt(
        classification="LOCAL_E9_OPERATOR_TRACE_CANDIDATE_UNATTESTED",
        physically_authenticated=False, e5_physical_study_authorized=False,
        action_issued=False, world_server_started_by_e8=False,
        minecraft_world_mutation_sent_by_e8=False,
        source_sha256=hashlib.sha256(source).hexdigest(),
        source_bytes=len(source), audited_prefix_bytes=ack_prefix_length,
        frames=frames, hurt_event_count=hurt_event_count,
        observed_close_suffix=close_suffix,
        session_id=audited.session_id, first_probe_seq=audited.first_probe_seq,
        second_probe_seq=audited.second_probe_seq,
        far_entity_id=audited.far_entity_id,
        near_entity_id=audited.near_entity_id, bridge_exit_code=code,
        physical_geometry="UNATTESTED_SOURCE_REQUIRES_INDEPENDENT_WORLD_REVIEW",
    )


def _data(r: CandidateReceipt) -> dict[str, object]:
    return {name: getattr(r, name) for name in r.__dataclass_fields__}


async def run_once(raw: Path, report: Path, *, port: int = 25565) -> int:
    """Potentially launch only the Mineflayer *client*, after explicit CLI gate.

    Does NOT own or start a Minecraft server. Both original bytes and an
    independent report persist even if calibration fails.
    """
    _frozen()
    if type(port) is not int or not 1 <= port <= 65535:
        raise E9Blocked("local loopback port invalid")
    bridge = Path(__file__).resolve().parents[1] / "adapters" / "mineflayer" / "bridge.mjs"
    module = bridge.parent / "node_modules" / "mineflayer"
    if not bridge.is_file() or not module.is_dir():
        raise E9Blocked("original bridge and locked npm ci Mineflayer are required")
    config = MineflayerLaunchConfig(
        host="127.0.0.1", port=port, username="RelaySelf", version="1.21.8"
    )
    proc = None
    outcome: dict[str, object] = {
        "classification": "E9_LOCAL_ATTEMPT_BLOCKED_OR_FAILED",
        "physically_authenticated": False,
        "e5_physical_study_authorized": False,
        "world_server_started_by_e8": False,
    }
    code = 2
    try:
        # Create evidence files with exclusive create, never clobber.
        with raw.open("xb") as writer:
            proc = await asyncio.create_subprocess_exec(
                *config.argv(bridge), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=None,
            )
            try:
                # Bound the entire manual one-shot calibration, not just each
                # native frame; no idle event stream may hold a process forever.
                candidate = await asyncio.wait_for(
                    capture_one(proc, writer), timeout=300
                )
                outcome = _data(candidate)
                code = 3  # structurally valid locally acquired trace is NOT attested
            finally:
                if proc.returncode is None:
                    try:
                        proc.stdin.write(encode_shutdown().encode("utf-8"))
                        await proc.stdin.drain()
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except (TimeoutError, OSError, ValueError, ConnectionError):
                        if proc.returncode is None:
                            proc.kill()
                        await proc.wait()
    except (E9Blocked, OSError, ValueError, asyncio.TimeoutError) as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
        outcome["classification"] = "E9_LOCAL_ATTEMPT_BLOCKED_OR_FAILED"
        code = 2
    # Report is always fail-closed. NO SUCCESSES labelled physical qualification.
    try:
        with report.open("x", encoding="utf-8") as output:
            json.dump(outcome, output, indent=2, sort_keys=True)
            output.write("\n")
    except FileExistsError:
        return 2
    print(json.dumps(outcome, sort_keys=True))
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E9 local operator-owned zombie-hurt-aware one-shot")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--plan", action="store_true")
    actions.add_argument("--run", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--port", type=int, default=25565)
    args = parser.parse_args(argv)
    if args.plan:
        _frozen()
        print(json.dumps({
            "classification": "E9_PLAN_ONLY_NO_WORLD_ATTEMPT",
            "version": VERSION, "parent_e8_manifest_sha256": MANIFEST_SHA256,
            "world_launched_by_e8": False,
            "manual_operator_console_protocol": [PROMPT_FAR, PROMPT_GONE, PROMPT_NEAR],
            "physical_execution_authorized": False,
            "local_operator_confirmation_required": CONFIRMATION,
        }, sort_keys=True))
        return 0
    try:
        validate_run_gate(args.run, args.confirmation, args.raw, args.report)
    except E9Blocked as exc:
        print(json.dumps({
            "classification": "E9_NOT_AUTHORIZED_TO_LAUNCH",
            "reason": str(exc), "world_launched_by_e8": False,
        }, sort_keys=True))
        return 2
    return asyncio.run(run_once(args.raw, args.report, port=args.port))


if __name__ == "__main__":
    sys.exit(main())
