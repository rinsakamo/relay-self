"""AC-C C16: explicitly operator-gated, single-lifetime Mineflayer endpoint test.

No default live action. No Minecraft server start, world file modification,
new protocol message, cognitive signed label, LLM or production Habit update.

C15 static regions are reused; a C16 physical endpoint remains a POSITION
observation, not a proof of selected Action correctness or exclusive task goal.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from adapters.mineflayer.goal_witness import Region, SpatialContract
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerPosition,
)
from adapters.mineflayer.runtime_admission import coordinate_mineflayer_message
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "experiments" / "ac_c_c16_manifest.json"
MANIFEST_SHA = "a4cd1607d9dc6d552b4ed3a1cc217a9a087cd48e20a5b15f074e115d4f204c0b"
CONFIRM = "C16-I-OWN-LOCAL-TEST-WORLD"
MAX_EVENTS = 80


class C16Blocked(RuntimeError):
    """Source, operator, task, safety, or evidence precondition did not hold."""


class OwnedSession(Protocol):
    @property
    def started(self): ...

    async def receive(self): ...

    async def send_observe(self) -> None: ...

    async def send_set_control(self, action_id: str, *,
                               control: str, state: bool) -> None: ...

    async def send_clear_controls(self, action_id: str) -> None: ...


@dataclass(frozen=True)
class C16Result:
    classification: str
    reason: str
    source_session: str | None
    evidence: tuple[str, ...]
    start_action_state: str
    stop_action_state: str
    movement_horizontal: float | None
    world_file_verified: bool
    physical_world_server_association_verified: bool = False
    signed_negative_label: str = "BLOCKED_UNDETERMINED"
    automatic_learning_updates: int = 0


def manifest() -> dict:
    doc = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if hashlib.sha256(raw.encode()).hexdigest() != MANIFEST_SHA:
        raise C16Blocked("FROZEN_MANIFEST_DRIFT")
    return doc


def read_spatial_spec(path: Path) -> tuple[Region, Region]:
    if path.is_symlink() or not path.is_file():
        raise C16Blocked("SPEC_NOT_A_REGULAR_FILE")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise C16Blocked("INVALID_SPEC_JSON") from exc
    if not isinstance(doc, dict) or set(doc) != {"goal", "alternative"}:
        raise C16Blocked("INVALID_SPEC_FIELDS")
    regions = []
    for key in ("goal", "alternative"):
        value = doc[key]
        if (not isinstance(value, dict) or set(value) != {"low", "high"}
                or not all(isinstance(value[k], list) and len(value[k]) == 3
                           for k in ("low", "high"))):
            raise C16Blocked("INVALID_REGION_FIELDS")
        try:
            regions.append(Region(tuple(value["low"]), tuple(value["high"])))
        except ValueError as exc:
            raise C16Blocked("INVALID_REGION_GEOMETRY") from exc
    # Region separation is checked with the existing C15 spatial contract.
    SpatialContract("preflight-session", "preflight-start", "preflight-stop",
                    regions[0], regions[1])
    return regions[0], regions[1]


def preflight(*, execute: bool, confirmation: str | None,
              world_dir: Path | None, expected_level_sha256: str | None,
              spatial_spec_path: Path | None, host: str, port: int,
              check_tcp: bool = True) -> tuple[Region, Region] | C16Result:
    """Default is NEVER to inspect a server or launch a process."""
    manifest()
    def blocked(why: str) -> C16Result:
        return C16Result(
            "BLOCKED_WORLD_OR_AUTHORITY_UNVERIFIED", why, None, (),
            "NOT_RUN", "NOT_RUN", None, False,
        )
    if not execute:
        return blocked("DRY_BLOCKED_NO_PROCESS")
    if confirmation != CONFIRM:
        return blocked("MISSING_EXPLICIT_OPERATOR_CONFIRMATION")
    if host != "127.0.0.1" or type(port) is not int or not 1 <= port <= 65535:
        return blocked("LOOPBACK_SERVER_ONLY")
    if (world_dir is None or expected_level_sha256 is None
            or spatial_spec_path is None):
        return blocked("MISSING_WORLD_OR_GOAL_SOURCE")
    if (len(expected_level_sha256) != 64
            or any(x not in "0123456789abcdef"
                   for x in expected_level_sha256)):
        return blocked("INVALID_LEVEL_DAT_HASH")
    if world_dir.is_symlink() or not world_dir.is_dir():
        return blocked("UNVERIFIED_WORLD_DIR")
    level = world_dir / "level.dat"
    if level.is_symlink() or not level.is_file():
        return blocked("UNVERIFIED_WORLD_FILE")
    try:
        current = hashlib.sha256(level.read_bytes()).hexdigest()
    except OSError:
        return blocked("UNREADABLE_WORLD_FILE")
    if current != expected_level_sha256:
        return blocked("LEVEL_DAT_IDENTITY_MISMATCH")
    try:
        regions = read_spatial_spec(spatial_spec_path)
    except (OSError, ValueError):
        return blocked("INVALID_PREAUTHORIZED_SPATIAL_SPEC")
    if check_tcp:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except OSError:
            return blocked("NO_EXISTING_LOOPBACK_SERVER")
    # A level.dat digest and a TCP port DO NOT attest their mutual association.
    return regions


def _horizontal(a: MineflayerPosition, b: MineflayerPosition) -> float:
    return math.hypot(a.x-b.x, a.z-b.z)


def _status(p: MineflayerPosition, goal: Region, alternative: Region) -> str:
    if goal.contains_strict(p):
        return "GOAL_REGION_OBSERVED"
    if alternative.contains_strict(p):
        return "ALTERNATIVE_REGION_OBSERVED"
    return "UNDETERMINED"


def _position_decision(
    baseline: MineflayerPosition,
    forward: MineflayerPosition,
    posts: tuple[MineflayerPosition, MineflayerPosition],
    goal: Region,
    alternative: Region,
) -> tuple[str, str, float]:
    spec = SpatialContract("internal", "start", "stop", goal, alternative)
    distance = _horizontal(baseline, forward)
    limit = manifest()["protocol"]["maximum_movement_horizontal_m"]
    minimum = manifest()["protocol"]["first_movement_required_horizontal_m"]
    if distance < minimum or distance > limit:
        return "UNDETERMINED", "MOVEMENT_OUTSIDE_ADMISSION_BOUND", distance
    if (spec.goal.contains_closed(baseline)
            or spec.alternative.contains_closed(baseline)):
        return "UNDETERMINED", "PREEXISTING_REGION", distance
    if any(_horizontal(baseline, p) > limit for p in posts):
        return "UNDETERMINED", "POSTSTOP_EXCEEDS_MOVEMENT_BOUND", distance
    tol = manifest()["protocol"]["stable_poststop_xyz_tolerance_m"]
    if any(abs(a-b) > tol for a, b in zip(
        (posts[0].x, posts[0].y, posts[0].z),
        (posts[1].x, posts[1].y, posts[1].z),
    )):
        return "UNDETERMINED", "UNSTABLE_TERMINAL_POSITION", distance
    a, b = _status(posts[0], goal, alternative), _status(posts[1], goal, alternative)
    if a != b or a == "UNDETERMINED":
        return "UNDETERMINED", "NO_STABLE_EXCLUSIVE_REGION", distance
    return a, "SPATIAL_ENDPOINT_ONLY_NOT_GOAL_OR_CAUSAL_PROOF", distance


class OneShotQualification:
    def __init__(self) -> None:
        self._used = False

    async def run(self, session: OwnedSession, *,
                  goal: Region, alternative: Region,
                  world_file_verified: bool = False,
                  timeout_s: float = 5.0) -> C16Result:
        """One bounded admitted control transaction on an already owned session."""
        if self._used:
            return C16Result("UNDETERMINED", "ONE_SHOT_REPLAY_DENIED",
                             None, (), "NOT_RUN", "NOT_RUN", None,
                             world_file_verified)
        self._used = True
        if timeout_s <= 0 or not math.isfinite(timeout_s):
            raise C16Blocked("INVALID_TIMEOUT")
        source = session.started.session_id
        SpatialContract(source, "start", "stop", goal, alternative)
        refs: list[str] = [session.started.provenance.reference]
        next_seq = session.started.seq + 1
        source_events = 0
        start_state = "NOT_RUN"
        stop_state = "NOT_RUN"
        issued_start = False
        forward_pos: MineflayerPosition | None = None
        baseline: MineflayerPosition | None = None
        posts: list[MineflayerPosition] = []
        supervisor = ActionSupervisor()
        clock_value = -1

        def now() -> int:
            nonlocal clock_value
            clock_value = max(time.monotonic_ns(), clock_value + 1)
            return clock_value

        def prov(stage: str) -> Provenance:
            return Provenance(source="mineflayer-c16-owner", reference=f"{source}:{stage}")

        async def receive():
            nonlocal next_seq, source_events
            if source_events >= MAX_EVENTS:
                raise C16Blocked("EVENT_LIMIT_REACHED")
            try:
                msg = await asyncio.wait_for(session.receive(), timeout_s)
            except TimeoutError as exc:
                raise C16Blocked("SOURCE_WAIT_TIMED_OUT") from exc
            source_events += 1
            if msg.session_id != source or msg.seq != next_seq:
                raise C16Blocked("SESSION_OR_SEQUENCE_NOT_CONTIGUOUS")
            next_seq += 1
            refs.append(msg.provenance.reference)
            if isinstance(msg, (MineflayerConnectionEnd, MineflayerAdapterErrorMessage)):
                raise C16Blocked("BRIDGE_TERMINATED_OR_ERROR")
            if isinstance(msg, MineflayerObservation):
                if msg.kind in ("forcedMove", "death", "respawn"):
                    raise C16Blocked("EXTERNAL_MOTION_OR_BODY_TERMINAL")
            elif not isinstance(msg, MineflayerEffectResult):
                raise C16Blocked("UNKNOWN_ADAPTER_EVENT")
            return msg

        async def expect_probe() -> MineflayerPosition:
            while True:
                msg = await receive()
                if isinstance(msg, MineflayerEffectResult):
                    raise C16Blocked("UNEXPECTED_ACTION_EFFECT_RESULT")
                if isinstance(msg, MineflayerObservation) and msg.kind == "probe":
                    return msg.snapshot.position

        def issue_action(action_id: str) -> None:
            proposal = ActionLifecycle.propose(
                action_id, skill_execution=skill, intent_commitment=intent,
                at_ns=now(), provenance=prov(action_id+":proposal"),
            )
            auth = proposal.authorize(
                at_ns=now(), provenance=prov(action_id+":authorize"),
                authority="c16-local-operator-test-only",
            )
            t = now()
            supervisor.issue(
                auth, at_ns=t, deadline_ns=t+int(timeout_s*1_000_000_000),
                provenance=prov(action_id+":issue"),
            )

        async def wait_ack(action_id: str, effect: str) -> None:
            while True:
                msg = await receive()
                if not isinstance(msg, MineflayerEffectResult):
                    continue
                if (msg.action_id != action_id or msg.effect != effect
                        or msg.result != "applied"):
                    raise C16Blocked("UNEXPECTED_OR_REJECTED_ACTION_ACK")
                result = coordinate_mineflayer_message(
                    msg, supervisor, at_ns=now()
                )
                if result is None or result.action_closure is None:
                    raise C16Blocked("ACTION_NOT_CLOSED_BY_OWNER")
                if supervisor.get(action_id).state is not ActionState.OUTCOME:
                    raise C16Blocked("ACTION_NOT_TERMINAL_OUTCOME")
                return

        start_id = f"c16-forward-{source}"
        stop_id = f"c16-stop-{source}"
        try:
            # Spawn must be observed before the controlled transaction.
            for _ in range(MAX_EVENTS):
                msg = await receive()
                if isinstance(msg, MineflayerObservation) and msg.kind == "spawn":
                    if msg.snapshot.health <= 2 or msg.snapshot.food <= 2:
                        raise C16Blocked("UNSAFE_SPAWN_BODY")
                    break
                if isinstance(msg, MineflayerEffectResult):
                    raise C16Blocked("UNEXPECTED_EARLY_ACTION_ACK")
            else:
                raise C16Blocked("SPAWN_NOT_CONFIRMED")
            await session.send_observe()
            baseline = await expect_probe()

            intent = IntentCommitment()
            intent.commit("c16-spatial-intent", objective="observe spatial terminal only",
                          at_ns=now(), provenance=prov("intent"))
            skill = SkillExecution.start(
                "c16-spatial-skill", skill_id="FLEE",
                intent_commitment=intent, at_ns=now(), provenance=prov("skill"),
            )
            issue_action(start_id)
            await session.send_set_control(start_id, control="forward", state=True)
            issued_start = True
            await wait_ack(start_id, "set_control")
            start_state = "OUTCOME"

            while forward_pos is None:
                msg = await receive()
                if isinstance(msg, MineflayerEffectResult):
                    raise C16Blocked("UNEXPECTED_MID_ACTION_ACK")
                if isinstance(msg, MineflayerObservation) and msg.kind == "move":
                    candidate = msg.snapshot.position
                    delta = _horizontal(baseline, candidate)
                    if delta > manifest()["protocol"]["maximum_movement_horizontal_m"]:
                        raise C16Blocked("MOTION_EXCEEDED_BOUND_BEFORE_STOP")
                    if delta >= manifest()["protocol"]["first_movement_required_horizontal_m"]:
                        forward_pos = candidate

            issue_action(stop_id)
            await session.send_clear_controls(stop_id)
            await wait_ack(stop_id, "clear_controls")
            stop_state = "OUTCOME"

            for _ in range(2):
                await session.send_observe()
                posts.append(await expect_probe())
            if skill.state is not SkillState.STARTED or intent.current_intent is None:
                raise C16Blocked("EXISTING_AUTHORITY_WAS_MUTATED")
            status, reason, delta = _position_decision(
                baseline, forward_pos, (posts[0], posts[1]), goal, alternative
            )
            return C16Result(status, reason, source, tuple(refs),
                             start_state, stop_state, delta, world_file_verified)
        except (C16Blocked, ValueError, RuntimeError, KeyError) as exc:
            return C16Result("UNDETERMINED", f"FAIL_CLOSED:{type(exc).__name__}:{exc}",
                             source, tuple(refs), start_state, stop_state,
                             _horizontal(baseline,forward_pos)
                             if baseline is not None and forward_pos is not None else None,
                             world_file_verified)
        finally:
            if issued_start and stop_state != "OUTCOME":
                # Emergency cleanup is NOT a supervised qualified Action.
                # Exactly one bounded stop attempt; no retry or automatic replacement.
                try:
                    await session.send_clear_controls(f"c16-emergency-{source}")
                except (OSError, RuntimeError, ValueError):
                    pass


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="C16 one-shot owned physical spatial qualification")
    p.add_argument("--run", action="store_true")
    p.add_argument("--confirmation")
    p.add_argument("--world-dir", type=Path)
    p.add_argument("--expected-level-sha256")
    p.add_argument("--regions", type=Path)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=25565)
    p.add_argument("--username", default="RelaySelfC16")
    p.add_argument("--version")
    p.add_argument("--evidence-timeout-s", type=float, default=5.0)
    return p


async def _main_async(args: argparse.Namespace) -> C16Result:
    pre = preflight(
        execute=args.run, confirmation=args.confirmation,
        world_dir=args.world_dir, expected_level_sha256=args.expected_level_sha256,
        spatial_spec_path=args.regions, host=args.host, port=args.port,
    )
    if isinstance(pre, C16Result):
        return pre
    goal, alt = pre
    owned: MineflayerProcessSession | None = None
    try:
        owned = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=args.host, port=args.port,
                username=args.username, version=args.version,
            ),
            startup_timeout_s=args.evidence_timeout_s,
        )
        return await OneShotQualification().run(
            owned, goal=goal, alternative=alt,
            world_file_verified=True, timeout_s=args.evidence_timeout_s,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        return C16Result(
            "UNDETERMINED", f"PHYSICAL_SESSION_FAILED:{type(exc).__name__}",
            owned.started.session_id if owned is not None else None,
            (), "UNKNOWN", "UNKNOWN", None, True,
        )
    finally:
        if owned is not None:
            try:
                await owned.shutdown(timeout_s=5.0)
            except (RuntimeError, OSError):
                await owned.terminate()


def main() -> int:
    args = _parser().parse_args()
    result = asyncio.run(_main_async(args))
    print(json.dumps(asdict(result), sort_keys=True, ensure_ascii=False))
    return 0 if result.classification in (
        "GOAL_REGION_OBSERVED", "ALTERNATIVE_REGION_OBSERVED"
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
