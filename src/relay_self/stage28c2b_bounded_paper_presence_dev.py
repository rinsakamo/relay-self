"""Stage28c2b DEV: source-bound, bounded wait for BOTH Paper A/B presence.

Never turn a fixed wall-clock sleep into a guessed PRESENT. This gate reads
the original owned Paper Popen log until each new native's Paper player has
one JOIN followed by an actual PRESENT/MOVE. The final nonce tick ACK and
actual cognitive WorldBody handoff remain separate, later validations.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
from dataclasses import dataclass

from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.resident_paper_presence_join_dev import (
    ResidentPaperJoinError,
    parse_owned_paper_resident_trace,
)
from relay_self.stage28_cognitive_recovery_gate_dev import Stage28ForkPaperEpoch
from relay_self.world_resident_lifecycle_dev import Presence


class Stage28PresenceWaitHold(RuntimeError):
    """Original A/B live Paper source did not prove both present in time."""


@dataclass(frozen=True, slots=True)
class Stage28PresenceReady:
    paper_session_id: str
    resident_plugin_boot_id: str
    paper_pid: int
    a_join_tick: int
    b_join_tick: int
    a_presence_tick: int
    b_presence_tick: int
    paper_log_sha256: str
    polling_reads: int
    elapsed_seconds: float
    both_present_source_verified: bool = True
    owner_worldbody_accepted: bool = False
    physical_action_issue_authorized: bool = False


def _require_paper_and_native_owners(
    bridge: OwnedResidentPhysicalBridge,
    paper: OwnedPaperWorld,
    boot: Stage28ForkPaperEpoch,
) -> None:
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or not isinstance(paper, OwnedPaperWorld)
        or not isinstance(boot, Stage28ForkPaperEpoch)
        or bridge.paper is not paper
        or bridge.inference_lane is not None
        or not bridge.physical.observation_only
        or bridge.physical.active_action_ids
        or bridge.lifecycle.self_roster != ("A", "B")
        or bridge.lifecycle.world.world_id != boot.source_world_id
        or bridge.lifecycle.world.branch_id != boot.fork_branch_id
        or bridge.lifecycle.world.paper_session_id != boot.paper_session_id
        or bridge.lifecycle.world.epoch != boot.world_epoch
        or paper.world_id != boot.source_world_id
        or paper.branch_id != boot.fork_branch_id
        or paper.owned_session_id != boot.paper_session_id
        or tuple(sorted(bridge.sessions)) != ("A", "B")
        or tuple(sorted(bridge.last_login_evidence)) != ("A", "B")
        or tuple(sorted(bridge.configs)) != ("A", "B")
        or not all(
            bridge.lifecycle.view(sid).status is Presence.ONLINE
            and bridge.sessions[sid].process_returncode is None
            and bridge.sessions[sid].started.session_id
            == bridge.last_login_evidence[sid].native_session_id
            and bridge.last_login_evidence[sid].paper_session_id
            == boot.paper_session_id
            and bridge.last_login_evidence[sid].action_issue_authorized is False
            for sid in ("A", "B")
        )
        or bridge.configs["A"].username == bridge.configs["B"].username
    ):
        raise Stage28PresenceWaitHold(
            "both original observation-only native owners must remain ONLINE"
        )


async def await_both_recovered_paper_present(
    *, bridge: OwnedResidentPhysicalBridge,
    paper: OwnedPaperWorld,
    boot: Stage28ForkPaperEpoch,
    timeout_seconds: float = 12.0,
    poll_seconds: float = 0.10,
    max_ticks_after_latest_join: int = 120,
) -> Stage28PresenceReady:
    """Wait for actual source events, bounded by wall time AND Paper ticks.

    There is no automatic World restart, issued Action, GPU request, or
    native effect. Missing B PRESENT is HOLD, never inferred from 40 ticks.
    After success, callers MUST request a NEW Paper main-thread nonce ACK
    via link_recovered_a_b_native_paper_body and recheck exact source.
    """
    if (
        type(timeout_seconds) not in (int, float)
        or not math.isfinite(timeout_seconds)
        or not 1 <= timeout_seconds <= 30
        or type(poll_seconds) not in (int, float)
        or not math.isfinite(poll_seconds)
        or not 0.02 <= poll_seconds <= 0.5
        or poll_seconds >= timeout_seconds
        or type(max_ticks_after_latest_join) is not int
        or not 40 <= max_ticks_after_latest_join <= 240
    ):
        raise Stage28PresenceWaitHold("finite bounded Paper presence budget required")
    _require_paper_and_native_owners(bridge, paper, boot)
    loop = asyncio.get_running_loop()
    started_at = loop.time()
    deadline = started_at + timeout_seconds
    reads = 0
    seen_resident_boot: str | None = None
    while True:
        _require_paper_and_native_owners(bridge, paper, boot)
        try:
            owned = paper._assert_owned()
            if owned.pid != boot.paper_pid:
                raise Stage28PresenceWaitHold("Paper PID changed during presence wait")
            data = paper.read_owned_log(boot.paper_session_id)
        except Stage28PresenceWaitHold:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise Stage28PresenceWaitHold(
                "original owned Paper stdout no longer available"
            ) from exc
        reads += 1
        # No complete event yet: wait rather than misclassify a still
        # starting plugin. A malformed existing event is an immediate HOLD.
        if b"P0D_RESIDENT event=" in data:
            try:
                trace = parse_owned_paper_resident_trace(
                    owned_paper_session_id=boot.paper_session_id,
                    expected_world_uuid=boot.source_world_id,
                    owned_paper_log=data,
                    log_ref="owned-paper-presence-wait:" + hashlib.sha256(data).hexdigest(),
                )
            except ResidentPaperJoinError as exc:
                raise Stage28PresenceWaitHold(
                    "malformed or foreign Paper presence source"
                ) from exc
            if (
                seen_resident_boot is not None
                and trace.boot_id != seen_resident_boot
            ):
                raise Stage28PresenceWaitHold("Paper resident plugin boot changed")
            seen_resident_boot = trace.boot_id
            joined: dict[str, object] = {}
            present: dict[str, object] = {}
            actors: set[str] = set()
            for sid in ("A", "B"):
                actor_name = bridge.configs[sid].username
                events = [e for e in trace.events if e.name == actor_name]
                if not events:
                    continue
                first = events[0]
                if (
                    first.event != "JOIN" or first.tick < boot.boot_tick
                    or len([e for e in events if e.event == "JOIN"]) != 1
                    or any(e.event == "QUIT" for e in events)
                    or len({e.actor_uuid for e in events}) != 1
                    or first.actor_uuid in actors
                ):
                    raise Stage28PresenceWaitHold(
                        "duplicate, retired or collided original Paper actor"
                    )
                actors.add(first.actor_uuid)
                joined[sid] = first
                observed = [
                    e for e in events
                    if e.event in ("PRESENT", "MOVE")
                    and e.line > first.line and e.tick >= first.tick
                ]
                if observed:
                    present[sid] = observed[0]
            if len(joined) == 2:
                latest_join = max(joined["A"].tick, joined["B"].tick)
                if (
                    trace.events[-1].tick - latest_join
                    > max_ticks_after_latest_join
                ):
                    raise Stage28PresenceWaitHold(
                        "both-PRESENT Paper tick budget exhausted"
                    )
            if len(joined) == 2 and len(present) == 2:
                return Stage28PresenceReady(
                    boot.paper_session_id, trace.boot_id, boot.paper_pid,
                    joined["A"].tick, joined["B"].tick,
                    present["A"].tick, present["B"].tick,
                    hashlib.sha256(data).hexdigest(), reads,
                    max(0.0, loop.time() - started_at),
                )
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise Stage28PresenceWaitHold(
                "bounded actual Paper JOIN/PRESENT wait timed out; HOLD"
            )
        await asyncio.sleep(min(poll_seconds, remaining))
