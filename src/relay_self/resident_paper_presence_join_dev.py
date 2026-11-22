"""#860 Stage22: read-only join of independently owned Paper player presence.

A Paper MOVE is movement in World, not proof of one specific native Action.
B still online after A quit is separate from B performing a canonical
PhysicalActionJournal EAT/ATTACK. No Action issuer, WAL writer or native
sender exists here. Paper main-thread tick and native day-clock are NOT
numerically comparable: use each stream's source ordering independently.
"""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from enum import Enum

from relay_self.world_resident_lifecycle_dev import (
    LogoutFenceEvidence,
    NativeLoginEvidence,
    WorldLifetime,
)


class ResidentPaperJoinError(ValueError):
    """Foreign Paper session, actor UUID, boot, World or impossible ordering."""


class ResidentPaperVerdict(str, Enum):
    PRESENCE_CORRELATED = "DEV_B_PAPER_PRESENCE_AFTER_A_LOGOUT"
    MOVEMENT_CORRELATED = "DEV_B_PAPER_MOVED_AFTER_A_LOGOUT"
    HOLD = "HOLD"


_EVENTS = frozenset({"JOIN", "QUIT", "PRESENT", "MOVE"})
_READY = re.compile(r"P0D_RESIDENT_READY boot=([0-9a-f-]{36}) source=PAPER_MAIN_THREAD version=1")
_EVENT = re.compile(r"P0D_RESIDENT event=([A-Z]+) ")
_NAME = re.compile(r"[A-Za-z0-9_]{3,16}")
_FIELDS = {"event", "boot", "tick", "world", "actor", "name", "x", "y", "z", "source"}


def _uuid(name: str, value: object) -> str:
    if type(value) is not str:
        raise ResidentPaperJoinError(f"{name} not string")
    try:
        u = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ResidentPaperJoinError(f"{name} invalid UUID") from exc
    if str(u) != value:
        raise ResidentPaperJoinError(f"{name} not canonical UUID")
    return value


def _finite(value: str) -> float:
    try:
        v = float(value)
    except (ValueError, OverflowError) as exc:
        raise ResidentPaperJoinError("position not numeric") from exc
    if not math.isfinite(v):
        raise ResidentPaperJoinError("position nonfinite")
    return v


@dataclass(frozen=True, slots=True)
class PaperResidentEvent:
    event: str
    boot_id: str
    tick: int
    world_uuid: str
    actor_uuid: str
    name: str
    x: float
    y: float
    z: float
    line: int
    source: str = "PAPER_MAIN_THREAD"

    def __post_init__(self) -> None:
        if (
            self.event not in _EVENTS
            or self.source != "PAPER_MAIN_THREAD"
            or type(self.tick) is not int or self.tick < 0
            or type(self.line) is not int or self.line < 1
            or not _NAME.fullmatch(self.name)
        ):
            raise ResidentPaperJoinError("Paper resident event schema invalid")
        _uuid("boot", self.boot_id)
        _uuid("world", self.world_uuid)
        _uuid("actor", self.actor_uuid)
        if not all(math.isfinite(v) for v in (self.x, self.y, self.z)):
            raise ResidentPaperJoinError("Paper event coordinates invalid")


@dataclass(frozen=True, slots=True)
class OwnedPaperResidentTrace:
    paper_session_id: str
    boot_id: str
    world_uuid: str
    lines_sha256: str
    events: tuple[PaperResidentEvent, ...]
    log_ref: str

    def __post_init__(self) -> None:
        _uuid("boot", self.boot_id)
        _uuid("world", self.world_uuid)
        if (
            not self.paper_session_id.startswith("paper-owned-")
            or type(self.log_ref) is not str or not self.log_ref
            or type(self.lines_sha256) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", self.lines_sha256)
            or not self.events
            or any(
                x.boot_id != self.boot_id or x.world_uuid != self.world_uuid
                for x in self.events
            )
            or any(
                later.tick < before.tick or later.line <= before.line
                for before, later in zip(self.events, self.events[1:])
            )
        ):
            raise ResidentPaperJoinError("owned Paper presence stream inconsistent")


def parse_owned_paper_resident_trace(
    *, owned_paper_session_id: str, expected_world_uuid: str,
    owned_paper_log: bytes, log_ref: str,
) -> OwnedPaperResidentTrace:
    """Use ONLY bytes read through OwnedPaperWorld.read_owned_log(session).

    Never point this parser at an arbitrary global latest.log and call the
    result authenticated. The actual owned-Paper parent must bind the source.
    """
    import hashlib

    _uuid("world", expected_world_uuid)
    if (
        type(owned_paper_log) is not bytes
        or not owned_paper_session_id.startswith("paper-owned-")
    ):
        raise ResidentPaperJoinError("owned Paper process log required")
    try:
        text = owned_paper_log.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ResidentPaperJoinError("Paper log not UTF-8") from exc
    ready: list[str] = []
    events: list[PaperResidentEvent] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _READY.search(line)
        if match:
            ready.append(_uuid("boot", match.group(1)))
        found = _EVENT.search(line)
        if found is None:
            continue
        tokenized = line[line.index("P0D_RESIDENT event="):].split()
        try:
            fields = dict(field.split("=", 1) for field in tokenized[1:])
        except ValueError as exc:
            raise ResidentPaperJoinError("malformed Paper event key/value") from exc
        if set(fields) != _FIELDS or fields["event"] != found.group(1):
            raise ResidentPaperJoinError("Paper presence event fields differ")
        try:
            tick = int(fields["tick"])
        except ValueError as exc:
            raise ResidentPaperJoinError("noninteger Paper tick") from exc
        # Reject noncanonical numeric and boolean tick representations.
        if str(tick) != fields["tick"]:
            raise ResidentPaperJoinError("Paper tick is not canonical")
        events.append(PaperResidentEvent(
            event=fields["event"], boot_id=fields["boot"],
            tick=tick, world_uuid=fields["world"],
            actor_uuid=fields["actor"], name=fields["name"],
            x=_finite(fields["x"]), y=_finite(fields["y"]),
            z=_finite(fields["z"]), line=lineno,
            source=fields["source"],
        ))
    if len(ready) != 1 or not events:
        raise ResidentPaperJoinError("one Paper boot marker and player events required")
    if any(x.boot_id != ready[0] for x in events):
        raise ResidentPaperJoinError("foreign Paper boot marker in resident stream")
    return OwnedPaperResidentTrace(
        owned_paper_session_id, ready[0], expected_world_uuid,
        hashlib.sha256(owned_paper_log).hexdigest(), tuple(events), log_ref,
    )


@dataclass(frozen=True, slots=True)
class ResidentPresenceDecision:
    status: ResidentPaperVerdict
    a_actor_uuid: str
    b_actor_uuid: str
    a_quit_tick: int
    b_later_tick: int
    a_rejoin_tick: int
    b_movement_m: float
    paper_source_ref: str
    prior_native_a: str
    new_native_a: str
    continuous_native_b: str
    native_action_caused_b_move: bool = False
    physical_wal_action_attested: bool = False
    actual_paper_source_authenticated_by_parser: bool = False


def join_resident_paper_presence(
    *,
    trace: OwnedPaperResidentTrace, world: WorldLifetime,
    a_name: str, b_name: str,
    a_logout: LogoutFenceEvidence, a_relogin: NativeLoginEvidence,
    original_b_native: str, surviving_b_native: str,
    minimum_b_movement_m: float = 0.3,
) -> ResidentPresenceDecision:
    """Require A's Paper logout→B present/move→A Paper rejoin, B no quit.

    Preserves original issuer and new native session evidence, but does
    NOT assert cross-clock equality, action ticket, or World Action
    causation from a proximity/time-only comparison.
    """
    if (
        not isinstance(trace, OwnedPaperResidentTrace)
        or not isinstance(world, WorldLifetime)
        or not isinstance(a_logout, LogoutFenceEvidence)
        or not isinstance(a_relogin, NativeLoginEvidence)
        or a_name == b_name
        or not all(_NAME.fullmatch(x) for x in (a_name, b_name))
        or trace.paper_session_id != world.paper_session_id
        or trace.world_uuid != world.world_id
        or not a_logout.native_terminated
        or not a_logout.physical_issuer_revoked
        or not a_logout.no_physical_inflight
        or not a_logout.physical_wal_clear
        or not a_logout.stale_gpu_fenced
        or not a_logout.peer_transport_drained
        or a_logout.world_epoch != world.epoch
        or a_relogin.world_id != world.world_id
        or a_relogin.branch_id != world.branch_id
        or a_relogin.paper_session_id != world.paper_session_id
        or a_relogin.world_epoch != world.epoch
        or not a_relogin.new_native_source_verified
        or not a_relogin.old_native_invalidated
        or a_relogin.native_session_id == a_logout.native_session_id
        or a_relogin.action_issue_authorized
        or original_b_native != surviving_b_native
        or original_b_native in (a_logout.native_session_id, a_relogin.native_session_id)
        or type(minimum_b_movement_m) not in (int, float)
        or not 0.2 <= minimum_b_movement_m <= 4.0
    ):
        raise ResidentPaperJoinError("World/native/issuer/scope source mismatch")
    a = [x for x in trace.events if x.name == a_name]
    b = [x for x in trace.events if x.name == b_name]
    if not a or not b:
        raise ResidentPaperJoinError("both actors missing in Paper presence log")
    uuid_a = a[0].actor_uuid
    uuid_b = b[0].actor_uuid
    if uuid_a == uuid_b or any(x.actor_uuid != uuid_a for x in a) or any(
        x.actor_uuid != uuid_b for x in b
    ):
        raise ResidentPaperJoinError("Paper native player identity collision")
    if a[0].event != "JOIN" or b[0].event != "JOIN":
        raise ResidentPaperJoinError("both original Paper JOIN events required")
    quits = [x for x in a if x.event == "QUIT"]
    joins = [x for x in a[1:] if x.event == "JOIN"]
    if len(quits) != 1 or len(joins) != 1:
        raise ResidentPaperJoinError("one verified Paper A quit/rejoin epoch required")
    old_a_quit = quits[0]
    new_a_join = joins[0]
    if not a[0].line < old_a_quit.line < new_a_join.line:
        raise ResidentPaperJoinError("A's Paper stream not a logout/relogin")
    if any(x.event == "QUIT" for x in b) or len(
        [x for x in b if x.event == "JOIN"]
    ) != 1:
        raise ResidentPaperJoinError("B not continuously present")
    b_after = [
        x for x in b
        if old_a_quit.line < x.line < new_a_join.line
        and x.event in ("PRESENT", "MOVE")
    ]
    b_before = [
        x for x in b
        if x.line < old_a_quit.line and x.event in ("JOIN", "PRESENT", "MOVE")
    ]
    if not b_after or not b_before:
        raise ResidentPaperJoinError("no independent B Paper presence after A quit")
    reference = b_before[-1]
    maximum = max(
        math.dist((reference.x, reference.y, reference.z), (x.x, x.y, x.z))
        for x in b_after
    )
    witnessed_move = any(x.event == "MOVE" for x in b_after)
    moved = witnessed_move and maximum >= minimum_b_movement_m
    return ResidentPresenceDecision(
        ResidentPaperVerdict.MOVEMENT_CORRELATED if moved
        else ResidentPaperVerdict.PRESENCE_CORRELATED,
        uuid_a, uuid_b, old_a_quit.tick,
        b_after[-1].tick, new_a_join.tick, maximum,
        trace.log_ref, a_logout.native_session_id,
        a_relogin.native_session_id, surviving_b_native,
    )
