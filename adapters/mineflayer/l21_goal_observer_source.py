"""L21: second physical Mineflayer client read-only protocol and source audit.

The separate Node process owns its original file. Python can trigger snapshots
after existing S16 closure, but cannot write/edit or infer external goal labels.
Different TCP client is not Paper owner, independent chronology or causality.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from relay_self.l14_original_bridge_goal_window import _json
from relay_self.l20_external_goal_commitment import (
    review_external_pre_world_criterion,
)
from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan

SCHEMA = "L21_SEPARATE_CLIENT_GOAL_OBSERVER_V1"
ORIGINAL_NAME = "l21_separate_client_goal_original.jsonl"


class L21ObserverRejected(ValueError):
    """No physical Goal source admitted on missing or inconsistent original."""


@dataclass(frozen=True, slots=True)
class L21OriginalReview:
    schema: str
    observer_session: str
    original_sha256: str
    source_bytes: int
    first_request_id: str
    second_request_id: str
    goal_status: str
    native_goal_status: str
    diagnostic_agreement: bool | None
    physical_second_tcp_client_source_claim: bool = True
    tcp_authenticated_independently: bool = False
    separate_external_goal_owner_authenticated: bool = False
    independently_attested_nonintervention: bool = False
    qualified_real_learning_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0


def _read_lines(raw: bytes) -> list[dict]:
    if (
        not isinstance(raw, bytes) or not 0 < len(raw) <= 8192 * 10
        or not raw.endswith(b"\n")
    ):
        raise L21ObserverRejected("bounded closed observer original required")
    lines = raw.splitlines(keepends=True)
    if len(lines) != 6 or any(not 0 < len(line) <= 8192 for line in lines):
        raise L21ObserverRejected("L21 requires original start/ready/2 samples/result/closed")
    return [_json(line) for line in lines]


def _position(doc: object) -> dict | None:
    if doc is None:
        return None
    if (
        not isinstance(doc, dict)
        or set(doc) != {"entity_id", "x", "y", "z"}
        or type(doc["entity_id"]) is not int
        or doc["entity_id"] < 0
        or any(type(doc[k]) not in (int, float) or not math.isfinite(doc[k])
               for k in ("x", "y", "z"))
    ):
        raise L21ObserverRejected("observer position must be typed native entity coordinates")
    return doc


def _status(a: dict | None, b: dict | None, plan: L16GoalPlan) -> str:
    if a is None or b is None or a["entity_id"] != b["entity_id"]:
        return "UNDETERMINED"
    d1 = math.hypot(a["x"] - plan.target_x, a["z"] - plan.target_z)
    d2 = math.hypot(b["x"] - plan.target_x, b["z"] - plan.target_z)
    drift = math.hypot(a["x"] - b["x"], a["z"] - b["z"])
    if drift > plan.stable_probe_delta_max_m or (d1 <= plan.tolerance_m) != (
        d2 <= plan.tolerance_m
    ):
        return "UNDETERMINED"
    return "REACHED" if d2 <= plan.tolerance_m else "NOT_REACHED"


def review_l21_observer_original(
    *, raw: bytes, criterion_original: bytes, criterion_sha256: str,
    plan: L16GoalPlan, session_id: str, action_id: str,
    native_goal_status: str,
) -> L21OriginalReview:
    """Review actual bytes from second client; never turn into L13 reward."""
    try:
        pre = review_external_pre_world_criterion(
            original=criterion_original, admitted_sha256=criterion_sha256,
            operator_plan=plan,
        )
        lines = _read_lines(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise L21ObserverRejected("external criterion/observer original rejected") from exc
    if (
        not pre.matched_operator_plan
        or not isinstance(session_id, str) or not session_id
        or not isinstance(action_id, str) or not action_id
        or native_goal_status not in ("REACHED", "NOT_REACHED", "UNDETERMINED")
        or [line.get("kind") for line in lines] != [
            "start", "ready", "sample", "sample", "goal_result", "closed",
        ]
    ):
        raise L21ObserverRejected("foreign Goal observer window")
    obsid = lines[0].get("observer_session")
    if not isinstance(obsid, str) or not obsid or any(
        line.get("schema") != SCHEMA
        or line.get("observer_session") != obsid
        or type(line.get("index")) is not int or line["index"] != ix
        for ix, line in enumerate(lines)
    ):
        raise L21ObserverRejected("foreign or reordered observer original")
    start, ready, first, second, result, closed = lines
    if (
        set(start) != {
            "schema", "observer_session", "index", "kind", "criterion_sha256",
            "observer_username", "target_username", "observer_capabilities",
            "goal_observation_authority",
        }
        or start["criterion_sha256"] != criterion_sha256
        or start["observer_username"] != "RelayGoalObserver"
        or start["target_username"] != "RelaySelf"
        or start["observer_capabilities"] != "READ_ONLY_MINEFLAYER_SECOND_TCP_CLIENT"
        or start["goal_observation_authority"] is not False
        or set(ready) != {
            "schema", "observer_session", "index", "kind", "observer_entity_id",
        }
        or type(ready["observer_entity_id"]) is not int
        or ready["observer_entity_id"] < 0
        or any(set(entry) != {
            "schema", "observer_session", "index", "kind", "request_id", "position",
        } for entry in (first, second))
        or set(result) != {
            "schema", "observer_session", "index", "kind",
            "first_request_id", "second_request_id", "goal_status",
        }
        or set(closed) != {
            "schema", "observer_session", "index", "kind", "samples",
        }
        or closed["samples"] != 2
    ):
        raise L21ObserverRejected("observer owner result original malformed")
    ids = (
        f"l16:{session_id}:{action_id}:goal-1",
        f"l16:{session_id}:{action_id}:goal-2",
    )
    if (
        (first["request_id"], second["request_id"]) != ids
        or (result["first_request_id"], result["second_request_id"]) != ids
    ):
        raise L21ObserverRejected("observer requests not bound to first S49 Action")
    a, b = _position(first["position"]), _position(second["position"])
    if (
        (a is not None and a["entity_id"] == ready["observer_entity_id"])
        or (b is not None and b["entity_id"] == ready["observer_entity_id"])
        or result["goal_status"] != _status(a, b, plan)
    ):
        raise L21ObserverRejected("source Goal label does not follow observer positions")
    status = result["goal_status"]
    agreement = (
        status == native_goal_status
        if status != "UNDETERMINED" and native_goal_status != "UNDETERMINED"
        else None
    )
    return L21OriginalReview(
        schema="L21_SEPARATE_CLIENT_FIRST_ACTION_GOAL_SOURCE_REVIEW_V1",
        observer_session=obsid, original_sha256=hashlib.sha256(raw).hexdigest(),
        source_bytes=len(raw), first_request_id=ids[0],
        second_request_id=ids[1], goal_status=status,
        native_goal_status=native_goal_status,
        diagnostic_agreement=agreement,
    )


class L21ObserverSession:
    def __init__(self, process: asyncio.subprocess.Process, source_path: Path):
        self.process = process
        self.source_path = source_path
        self._sampled = 0
        self._closed = False

    async def _recv(self, kind: str, *, request_id: str | None = None) -> dict:
        if self.process.stdout is None:
            raise L21ObserverRejected("observer has no source ACK stream")
        try:
            raw = await asyncio.wait_for(self.process.stdout.readline(), timeout=40)
        except TimeoutError as exc:
            raise L21ObserverRejected("observer physical ACK timed out") from exc
        if not raw or len(raw) > 4096:
            raise L21ObserverRejected("observer exited or emitted oversized ACK")
        try:
            doc = _json(raw)
        except ValueError as exc:
            raise L21ObserverRejected("invalid observer ACK") from exc
        if (
            doc.get("type") != kind
            or (request_id is not None and doc.get("request_id") != request_id)
        ):
            raise L21ObserverRejected("wrong independent observer ACK")
        return doc

    @classmethod
    async def launch(cls, *, source_path: Path, criterion_path: Path,
                     criterion_sha256: str) -> L21ObserverSession:
        if (
            not isinstance(source_path, Path) or not source_path.is_absolute()
            or not source_path.parent.is_dir()
            or source_path.exists() or source_path.is_symlink()
            or not isinstance(criterion_path, Path) or not criterion_path.is_absolute()
            or criterion_path.is_symlink() or not criterion_path.is_file()
            or criterion_path == source_path
        ):
            raise L21ObserverRejected("fresh external observer root required")
        bridge = Path(__file__).with_name("l21_goal_observer.mjs")
        p = await asyncio.create_subprocess_exec(
            "node", str(bridge), "--goal-file", str(criterion_path),
            "--goal-sha256", criterion_sha256, "--output", str(source_path),
            "--observer-username", "RelayGoalObserver",
            "--target-username", "RelaySelf",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        )
        self = cls(p, source_path)
        try:
            await self._recv("ready")
        except Exception:
            await self.terminate()
            raise
        return self

    async def sample(self, request_id: str) -> None:
        if self._closed or self._sampled >= 2 or not isinstance(request_id, str):
            raise L21ObserverRejected("observer only permits two after-S16 samples")
        if self.process.stdin is None:
            raise L21ObserverRejected("observer has no read-only command channel")
        self.process.stdin.write(
            (json.dumps({"type": "sample", "request_id": request_id}) + "\n").encode()
        )
        await self.process.stdin.drain()
        await self._recv("sample", request_id=request_id)
        self._sampled += 1
        if self._sampled == 2:
            await self._recv("goal_result")

    async def close(self) -> bytes:
        if self._closed or self._sampled != 2 or self.process.stdin is None:
            raise L21ObserverRejected("two samples required before sealed source")
        self.process.stdin.write(b'{"type":"shutdown"}\n')
        await self.process.stdin.drain()
        await self._recv("closed")
        self._closed = True
        await asyncio.wait_for(self.process.wait(), timeout=15)
        if self.process.returncode != 0:
            raise L21ObserverRejected("observer exited without clean shutdown")
        if self.source_path.is_symlink() or not self.source_path.is_file():
            raise L21ObserverRejected("independent source lost after close")
        return self.source_path.read_bytes()

    async def terminate(self) -> None:
        self._closed = True
        if self.process.returncode is None:
            self.process.kill()
        await self.process.wait()
