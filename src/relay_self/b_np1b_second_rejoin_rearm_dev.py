"""Second A logout/reJOIN: original-owner generation boundary and CPU rearm.

A new proof is needed after the *second* original A retirement: the first
reJOIN verifier is intentionally single-cycle and MUST NOT be reused.
Original B stays on the same Native session; Native/Paper clocks remain
independent. This grants no GPU, physical Action or memory adoption.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import asdict, dataclass

from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeSourceReceipt
from relay_self.b_np1b_current_composite_source_dev import CompositeSourceReceipt
from relay_self.b_np1b_fresh_native_update_dev import (
    read_continuing_b_native_revision,
    read_rejoined_native_revision,
)
from relay_self.b_np1b_initial_source_dev import _revision
from relay_self.b_np1b_normal_present_poll_dev import NormalPresentCpuPoll
from relay_self.b_np1b_normal_present_scheduler_dev import (
    NormalResidentPresentCpuScheduler,
    ScheduledPresentCpu,
    start_normal_resident_present_cpu,
)
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinedCompositeSourceReceipt,
    old_session_active,
)
from relay_self.b_np1b_rejoin_present_dev import RejoinedOwnerSource
from relay_self.bd1b_owner_present_dev import _build_present
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.resident_paper_presence_join_dev import parse_owned_paper_resident_trace
from relay_self.stage28c2b_native_paper_body_link_dev import paper_tick_ack_matches
from relay_self.world_resident_lifecycle_dev import Presence


class SecondRejoinHold(RuntimeError):
    """Second generation Native/Paper/Owner/task source is unqualified."""


@dataclass(frozen=True, slots=True)
class FirstRejoinAnchor:
    """Internal original-resident cut captured while A1 and B are ONLINE."""

    bridge: OwnedResidentPhysicalBridge
    a: RejoinedCompositeSourceReceipt
    b: ContinuingCompositeSourceReceipt
    pair_revision: str
    a_task: ScheduledPresentCpu
    b_task: ScheduledPresentCpu
    a_scope: tuple[int, str, int]
    b_scope: tuple[int, str, int]
    a_owner: object
    b_owner: object
    a_login: object
    a_probe: object


@dataclass(frozen=True, slots=True)
class SecondRejoinCut:
    bridge: OwnedResidentPhysicalBridge
    first: FirstRejoinAnchor


@dataclass(frozen=True, slots=True)
class SecondRejoinRearm:
    first_pair_revision: str
    second_pair_revision: str
    first_a_native: str
    second_a_native: str
    continuous_b_native: str
    old_a_task_epoch: int
    new_a_task_epoch: int
    old_b_task_epoch: int
    new_b_task_epoch: int
    retired_a_cpu_task: bool
    retired_b_cpu_task: bool
    generation: int = 2


def capture_first_rejoin_cpu_anchor(*, bridge: OwnedResidentPhysicalBridge) -> FirstRejoinAnchor:
    """Pin a CURRENT first-reJOIN source from both existing scheduled tasks.

    Caller cannot pass a fabricated receipt or previous-loop source; the
    original Owner's live tasks and current Paper log are read back here.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise SecondRejoinHold("original cognitive Bridge required")
    resident = bridge.cognitive_work
    try:
        with resident.lock:
            if (
                getattr(resident, "_normal_second_rejoin_anchor", None) is not None
                or getattr(resident, "_normal_second_rejoin_cut", None) is not None
            ):
                raise SecondRejoinHold("first reJOIN anchor already captured")
            first_cut = getattr(resident, "_normal_rejoin_source_cut", None)
            if first_cut is None or first_cut.bridge is not bridge:
                raise SecondRejoinHold("original first reJOIN source not bound")
            a_task = bridge.require_scheduled_present_cpu("A")
            b_task = bridge.require_scheduled_present_cpu("B")
            a, b = a_task.poll.a_present, a_task.poll.b_present
            ar, br = a.source.composite_receipt, b.source.composite_receipt
            if (
                type(ar) is not RejoinedCompositeSourceReceipt
                or type(br) is not ContinuingCompositeSourceReceipt
                or a_task.poll != b_task.poll
                or a_task.source_pair_revision != b_task.source_pair_revision
                or br.a_rejoin_composite_ref != _revision(asdict(ar))
                or br.b_continuity_revision != ar.b_continuity_revision
                or ar.paper_log_sha256 != br.paper_log_sha256
                or ar.paper_tick_ref != br.paper_tick_ref
            ):
                raise SecondRejoinHold("first original paired scheduled source diverged")
            anchor = FirstRejoinAnchor(
                bridge, ar, br, a_task.source_pair_revision, a_task, b_task,
                resident.current_scope("A"), resident.current_scope("B"),
                bridge.owners["A"], bridge.owners["B"],
                bridge.last_login_evidence["A"],
                bridge.last_login_observations["A"],
            )
            if (
                anchor.a_scope != (ar.resident_epoch, ar.native_session_id, ar.world_epoch)
                or anchor.b_scope != (br.resident_epoch, br.native_session_id, br.world_epoch)
                or anchor.a_probe.request_id != ar.native_request_id
                or anchor.a_login.observation_ref != ar.native_request_id
                or anchor.a_task.token.epoch != ar.resident_epoch
                or anchor.b_task.token.epoch != br.resident_epoch
            ):
                raise SecondRejoinHold("first original CPU task/Native epoch inconsistent")
            resident._normal_second_rejoin_anchor = anchor
            return anchor
    except SecondRejoinHold:
        raise
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        raise SecondRejoinHold("first original Owner cut unavailable") from exc


def _second_pair_locked(bridge: OwnedResidentPhysicalBridge):
    """Build second A/B receipts from original resident, retirement and owned Paper."""
    resident = bridge.cognitive_work
    if resident is None:
        raise SecondRejoinHold("original Owner missing")
    anchor = getattr(resident, "_normal_second_rejoin_anchor", None)
    first_cut = getattr(resident, "_normal_rejoin_source_cut", None)
    if (
        type(anchor) is not FirstRejoinAnchor or anchor.bridge is not bridge
        or first_cut is None or first_cut.bridge is not bridge
        or getattr(resident, "_normal_second_rejoin_cut", None) not in (
            None, SecondRejoinCut(bridge, anchor),
        )
        or not bridge.adopt_login_worldbody_dev
        or bridge.lifecycle.self_roster != ("A", "B")
        or set(bridge.sessions) != {"A", "B"}
        or any(bridge.lifecycle.view(s).status is not Presence.ONLINE for s in ("A", "B"))
        or bridge.physical.active_action_ids
        or any(s in bridge._pending_login or s in bridge.retired
               or s in getattr(bridge, "_fresh_native_pending", {})
               for s in ("A", "B"))
    ):
        raise SecondRejoinHold("second-generation original Owner admission unavailable")
    bridge._check_world()
    world = bridge.lifecycle.world
    oa, ob = bridge.owners["A"], bridge.owners["B"]
    if (
        resident.owners["A"] is not oa or resident.owners["B"] is not ob
        or oa is not anchor.a_owner or ob is not anchor.b_owner
        or oa.cohort is not resident or ob.cohort is not resident
        or str(oa.files.self_root) != anchor.a.owner_identity
        or str(ob.files.self_root) != anchor.b.owner_identity
        or (world.world_id, world.branch_id, world.epoch, world.paper_session_id)
        != (anchor.a.world_id, anchor.a.branch_id, anchor.a.world_epoch,
            anchor.a.paper_session_id)
    ):
        raise SecondRejoinHold("original World or Owner has changed")
    scope_a = resident.current_scope("A")
    scope_b = resident.current_scope("B")
    sa, sb = bridge.sessions["A"], bridge.sessions["B"]
    login_a, login_b = bridge.last_login_evidence["A"], bridge.last_login_evidence["B"]
    probe_a, probe_b = (
        bridge.last_login_observations["A"], bridge.last_login_observations["B"],
    )
    retired = bridge._b_np1b_retired_login.get("A")
    if type(retired) is not tuple or len(retired) != 5:
        raise SecondRejoinHold("second original A retirement missing")
    logout, old_scope, old_owner, old_login, old_probe = retired
    if (
        old_owner is not oa or old_scope != anchor.a_scope
        or old_login != anchor.a_login or old_probe is not anchor.a_probe
        or logout.native_session_id != anchor.a.native_session_id
        or logout.world_epoch != world.epoch
        or logout.persisted_cognition_ref != f"cognition-file:{oa.files.cognition_file}"
        or not logout.source_ref.startswith("original-issuer:")
        or not all((
            logout.physical_issuer_revoked, logout.no_physical_inflight,
            logout.physical_wal_clear, logout.native_terminated,
            logout.stale_gpu_fenced, logout.peer_transport_drained,
        ))
        or logout.action_issue_authorized
        or scope_a[0] != anchor.a_scope[0] + 2
        or scope_a[1] in (anchor.a.native_session_id, anchor.a.old_native_session_id)
        or scope_a[2] != anchor.a_scope[2]
        or scope_b != anchor.b_scope
        or old_session_active(bridge, anchor.a.native_session_id)
        or old_session_active(bridge, anchor.a.old_native_session_id)
        or sa.started.session_id != scope_a[1] or sb.started.session_id != scope_b[1]
        or bridge.physical.current_native_sessions["A"] != scope_a[1]
        or bridge.physical.current_native_sessions["B"] != scope_b[1]
        or sa.process_returncode is not None or sb.process_returncode is not None
        or type(sa.owned_child_pid) is not int or sa.owned_child_pid <= 0
        or type(sb.owned_child_pid) is not int or sb.owned_child_pid <= 0
        or login_a.native_session_id != scope_a[1]
        or login_a.observation_ref != probe_a.request_id
        or probe_a is not oa.current_worldbody_observation
        or probe_a.session_id != scope_a[1]
        or login_b.native_session_id != anchor.b.native_session_id
        or login_b.observation_ref != first_cut.initial_receipts[1].native_request_id
        or probe_b is not bridge.last_login_observations["B"]
        or probe_b.session_id != scope_b[1]
    ):
        raise SecondRejoinHold("second A retirement/reJOIN or continuous B Native invalid")
    native_a = read_rejoined_native_revision(bridge=bridge, self_id="A")
    native_b = read_continuing_b_native_revision(
        bridge=bridge, initial_receipt=first_cut.initial_receipts[1],
    )
    if (
        native_a.native_session_id != scope_a[1]
        or native_a.native_request_id != probe_a.request_id
        or native_b.native_session_id != scope_b[1]
        or native_b.native_sequence < anchor.b.native_sequence
    ):
        raise SecondRejoinHold("second current Native source was not adopted")
    paper = bridge.paper
    process = paper._assert_owned()
    if (
        paper.owned_session_id != world.paper_session_id
        or paper.world_id != world.world_id or paper.branch_id != world.branch_id
        or process.pid != anchor.a.paper_pid
    ):
        raise SecondRejoinHold("owned Paper process changed")
    tick = paper.tick_readback(world.paper_session_id)
    log = paper.read_owned_log(world.paper_session_id)
    match = re.fullmatch(
        r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
        tick.source_ref,
    ) if type(tick) is PaperTickReceipt else None
    if (
        match is None or match.group(1) != anchor.a.paper_boot_id
        or tick.server_session_id != world.paper_session_id
        or tick.tick <= anchor.a.paper_tick
        or not paper_tick_ack_matches(
            source_ref=tick.source_ref, boot_id=anchor.a.paper_boot_id,
            session_id=world.paper_session_id, world_id=world.world_id,
            tick=tick.tick, log=log,
        )
    ):
        raise SecondRejoinHold("fresh second main-thread Paper ACK unavailable")
    lines = log.splitlines(keepends=True)
    prefixes = [
        i for i in range(1, len(lines) + 1)
        if hashlib.sha256(b"".join(lines[:i])).hexdigest() == anchor.a.paper_log_sha256
    ]
    ack = (
        f"P0D_TICK_ACK nonce={match.group(2)} boot={match.group(1)} "
        f"session={world.paper_session_id} world={world.world_id} "
        f"tick={tick.tick} source=PAPER_MAIN_THREAD"
    ).encode()
    if (
        len(prefixes) != 1 or prefixes[0] >= len(lines)
        or ack not in lines[-1]
        or not paper_tick_ack_matches(
            source_ref=anchor.a.paper_tick_ref, boot_id=anchor.a.paper_boot_id,
            session_id=world.paper_session_id, world_id=world.world_id,
            tick=anchor.a.paper_tick, log=b"".join(lines[:prefixes[0]]),
        )
    ):
        raise SecondRejoinHold("first qualified Paper prefix not present or second ACK not latest")
    trace = parse_owned_paper_resident_trace(
        owned_paper_session_id=world.paper_session_id,
        expected_world_uuid=world.world_id, owned_paper_log=log,
        log_ref="owned-paper-sha256:" + hashlib.sha256(log).hexdigest(),
    )
    aev = [e for e in trace.events if e.name == bridge.configs["A"].username]
    bev = [e for e in trace.events if e.name == bridge.configs["B"].username]
    joins = [e for e in aev if e.event == "JOIN"]
    quits = [e for e in aev if e.event == "QUIT"]
    b_present = [e for e in bev if e.event in ("PRESENT", "MOVE")]
    if (
        trace.boot_id != first_cut.initial_receipts[0].presence_boot_id
        or len(joins) != 3 or len(quits) != 2
        or joins[1].line != anchor.a.paper_rejoin_line
        or quits[0].line != anchor.a.paper_quit_line
        or len([e for e in bev if e.event == "JOIN"]) != 1
        or any(e.event == "QUIT" for e in bev)
        or any(e.actor_uuid != anchor.a.paper_actor_uuid for e in aev)
        or any(e.actor_uuid != anchor.b.paper_actor_uuid for e in bev)
        or joins[0].line >= quits[0].line
        or quits[0].line >= joins[1].line
        or joins[1].line >= prefixes[0]
        or quits[1].line <= prefixes[0]
        or quits[1].line >= joins[2].line
        or joins[2].tick > tick.tick
        or not any(quits[1].line < e.line < joins[2].line for e in b_present)
        or not any(e.line > joins[2].line and e.tick <= tick.tick for e in b_present)
        or not any(e.line > joins[2].line and e.event in ("PRESENT", "MOVE")
                   and e.tick <= tick.tick for e in aev)
        or any(quits[1].line < e.line < joins[2].line
               and e.event in ("PRESENT", "MOVE") for e in aev)
        or any(e.line > len(lines) or e.tick > tick.tick for e in trace.events)
    ):
        raise SecondRejoinHold("second original A QUIT/B continued/A JOIN/B PRESENT unverified")
    second_b_gap = [e for e in b_present if quits[1].line < e.line < joins[2].line][-1]
    second_b_post = [e for e in b_present if joins[2].line < e.line and e.tick <= tick.tick][-1]
    second_a_post = [
        e for e in aev if e.line > joins[2].line and e.event in ("PRESENT", "MOVE")
        and e.tick <= tick.tick
    ][-1]
    digest = hashlib.sha256(log).hexdigest()
    paper_data_a = dict(
        paper_session_id=world.paper_session_id,
        paper_boot_id=anchor.a.paper_boot_id, paper_pid=process.pid,
        paper_actor_uuid=anchor.a.paper_actor_uuid,
        paper_tick=tick.tick, paper_tick_ref=tick.source_ref,
        paper_log_sha256=digest,
    )
    paper_revision_a = _revision(paper_data_a)
    proof_ref = _revision(dict(
        generation=2, first_pair=anchor.pair_revision,
        second_logout=logout.source_ref, second_a_native=native_a.native_revision,
        second_b_native=native_b.native_revision,
        second_a_quit_line=quits[1].line, second_a_join_line=joins[2].line,
        second_a_present_line=second_a_post.line,
        second_b_gap_line=second_b_gap.line,
        second_b_post_line=second_b_post.line,
        owned_paper_sha256=digest, tick_ref=tick.source_ref,
    ))
    b_continuity = _revision(dict(
        generation=2, first_b_ref=_revision(asdict(anchor.b)),
        first_pair_revision=anchor.pair_revision,
        native_revision=native_b.native_revision,
        b_native_session=scope_b[1], paper_gap_line=second_b_gap.line,
        paper_post_line=second_b_post.line, paper_sha256=digest,
        second_logout_source_ref=logout.source_ref,
    ))
    historical_ref = _revision(asdict(anchor.a))
    a_revision = _revision(dict(
        native_revision=native_a.native_revision,
        paper_revision=paper_revision_a,
        initial_receipt_ref=anchor.a.initial_receipt_ref,
        historical_composite_ref=historical_ref,
        old_resident_epoch=anchor.a_scope[0],
        old_native_session_id=anchor.a.native_session_id,
        old_logout_source_ref=logout.source_ref,
        rejoin_paper_revision=proof_ref, b_continuity_revision=b_continuity,
    ))
    a = RejoinedCompositeSourceReceipt(
        self_id="A", world_id=world.world_id, branch_id=world.branch_id,
        world_epoch=world.epoch, owner_identity=native_a.owner_identity,
        resident_epoch=scope_a[0], native_session_id=scope_a[1],
        native_request_id=native_a.native_request_id,
        native_sequence=native_a.native_sequence,
        native_source_ref=native_a.native_source_ref,
        native_world_time=native_a.native_world_time,
        native_revision=native_a.native_revision,
        **paper_data_a, paper_revision=paper_revision_a,
        composite_revision=a_revision, initial_receipt_ref=anchor.a.initial_receipt_ref,
        old_resident_epoch=anchor.a_scope[0],
        old_native_session_id=anchor.a.native_session_id,
        old_logout_source_ref=logout.source_ref,
        historical_composite_ref=historical_ref,
        rejoin_paper_revision=proof_ref,
        b_continuity_revision=b_continuity,
        paper_quit_line=quits[1].line,
        paper_rejoin_line=joins[2].line,
        paper_present_line=second_a_post.line,
        b_present_line=second_b_gap.line,
    )
    paper_data_b = dict(paper_data_a, paper_actor_uuid=anchor.b.paper_actor_uuid)
    paper_revision_b = _revision(paper_data_b)
    a_ref = _revision(asdict(a))
    b_revision = _revision(dict(
        native_revision=native_b.native_revision,
        paper_revision=paper_revision_b,
        initial_receipt_ref=anchor.b.initial_receipt_ref,
        a_rejoin_composite_ref=a_ref,
        b_continuity_revision=b_continuity,
        b_post_rejoin_present_line=second_b_post.line,
        b_post_rejoin_present_tick=second_b_post.tick,
    ))
    b = ContinuingCompositeSourceReceipt(
        self_id="B", world_id=world.world_id, branch_id=world.branch_id,
        world_epoch=world.epoch, owner_identity=native_b.owner_identity,
        resident_epoch=scope_b[0], native_session_id=scope_b[1],
        native_request_id=native_b.native_request_id,
        native_sequence=native_b.native_sequence,
        native_source_ref=native_b.native_source_ref,
        native_world_time=native_b.native_world_time,
        native_revision=native_b.native_revision,
        **paper_data_b, paper_revision=paper_revision_b,
        composite_revision=b_revision, initial_receipt_ref=anchor.b.initial_receipt_ref,
        a_rejoin_composite_ref=a_ref, b_continuity_revision=b_continuity,
        b_post_rejoin_present_line=second_b_post.line,
        b_post_rejoin_present_tick=second_b_post.tick,
    )
    if (
        read_rejoined_native_revision(bridge=bridge, self_id="A") != native_a
        or read_continuing_b_native_revision(
            bridge=bridge, initial_receipt=first_cut.initial_receipts[1],
        ) != native_b
        or paper._assert_owned() is not process
        or paper.read_owned_log(world.paper_session_id) != log
        or resident.current_scope("A") != scope_a
        or resident.current_scope("B") != scope_b
        or bridge._b_np1b_retired_login.get("A") != retired
        or bridge.last_login_evidence["A"] is not login_a
        or bridge.last_login_evidence["B"] is not login_b
        or bridge.last_login_observations["A"] is not probe_a
        or bridge.last_login_observations["B"] is not probe_b
        or bridge.sessions["A"] is not sa or bridge.sessions["B"] is not sb
        or bridge.owners["A"] is not oa or bridge.owners["B"] is not ob
    ):
        raise SecondRejoinHold("original Native/Paper/Owner changed before return")
    return a, b


def build_second_rejoin_cpu_pair(*, bridge: OwnedResidentPhysicalBridge):
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise SecondRejoinHold("original Bridge required")
    try:
        with bridge.cognitive_work.lock:
            return _second_pair_locked(bridge)
    except SecondRejoinHold:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise SecondRejoinHold("second independent source cut unavailable") from exc


def build_second_rejoin_owner_present(
    *, bridge: OwnedResidentPhysicalBridge, self_id: str,
    initial_receipts, historical_composite,
):
    """Use the unchanged original ThreeSelf/Schema/Inquiry projector."""
    if self_id not in ("A", "B") or bridge.cognitive_work is None:
        raise SecondRejoinHold("second A/B original Owner only")
    resident = bridge.cognitive_work
    with resident.lock:
        first = getattr(resident, "_normal_rejoin_source_cut", None)
        second = getattr(resident, "_normal_second_rejoin_cut", None)
        if (
            first is None or type(second) is not SecondRejoinCut
            or first.bridge is not bridge or second.bridge is not bridge
            or first.initial_receipts != initial_receipts
            or first.historical_composite != historical_composite
        ):
            raise SecondRejoinHold("second source selector differs from original binding")

        def source_reader(*, bridge, boot, world, links, self_id):
            a, b = build_second_rejoin_cpu_pair(bridge=bridge)
            receipt = a if self_id == "A" else b
            initial = first.initial_receipts[0 if self_id == "A" else 1]
            return RejoinedOwnerSource(
                self_id=receipt.self_id, world_id=receipt.world_id,
                branch_id=receipt.branch_id, world_epoch=receipt.world_epoch,
                paper_session_id=receipt.paper_session_id,
                paper_boot_id=receipt.paper_boot_id,
                presence_boot_id=initial.presence_boot_id,
                paper_tick_source_ref=receipt.paper_tick_ref,
                paper_log_sha256=receipt.paper_log_sha256,
                paper_actor_uuid=receipt.paper_actor_uuid,
                resident_epoch=receipt.resident_epoch,
                native_session_id=receipt.native_session_id,
                native_probe_ref=receipt.native_request_id,
                native_probe_seq=receipt.native_sequence,
                native_probe_source_ref=receipt.native_source_ref,
                native_world_time_tick=receipt.native_world_time,
                composite_receipt=receipt,
            )

        return _build_present(
            bridge=bridge, boot=None, world=None, links=None,
            self_id=self_id, source_reader=source_reader,
        )


async def rearm_second_rejoin_normal_cpu(
    *, bridge: OwnedResidentPhysicalBridge, interval_s: float = 0.05,
) -> tuple[NormalResidentPresentCpuScheduler, SecondRejoinRearm]:
    """One-shot rearm after genuine second reJOIN; never adopt old tasks/results.

    Must run in the original event loop. A's old Owner task was cancelled by
    original logout. B's old task is stopped here and removed ONLY after
    exact task-identity verification. A/B new tasks use the original Owner.
    """
    if (
        not isinstance(bridge, OwnedResidentPhysicalBridge)
        or bridge.cognitive_work is None
        or type(interval_s) not in (int, float) or not 0.01 <= interval_s <= 30
    ):
        raise SecondRejoinHold("original bounded CPU rearm required")
    resident = bridge.cognitive_work
    with resident.lock:
        if getattr(resident, "_normal_second_rejoin_cut", None) is not None:
            raise SecondRejoinHold("second reJOIN task rearm already completed")
        anchor = getattr(resident, "_normal_second_rejoin_anchor", None)
        old = getattr(resident, "_normal_present_scheduler", None)
        if (
            type(anchor) is not FirstRejoinAnchor
            or type(old) is not NormalResidentPresentCpuScheduler
            or old.bridge is not bridge or old.resident is not resident
            or old._tokens.get("A") != anchor.a_task.token
            or old._tokens.get("B") != anchor.b_task.token
            or not old._tasks["A"].done()
            or not resident._state("A").mode == "ONLINE"
            or resident.current_scope("A")[0] != anchor.a_scope[0] + 2
            or resident.current_scope("B") != anchor.b_scope
        ):
            raise SecondRejoinHold("old original CPU work was not retired with A")
        verified_a, verified_b = _second_pair_locked(bridge)
    await old.stop()
    with resident.lock:
        if (
            getattr(resident, "_normal_present_scheduler", None) is not old
            or getattr(resident, "_normal_second_rejoin_cut", None) is not None
            or not all(t.done() for t in old._tasks.values())
            or not old._stopped
            or resident._state("A").tasks is None
            or "normal-present-cpu:A" in resident._state("A").tasks
            or resident._state("B").tasks is None
            or resident._state("B").tasks.get("normal-present-cpu:B") is not old._tasks["B"]
            or _second_pair_locked(bridge) != (verified_a, verified_b)
        ):
            raise SecondRejoinHold("original CPU task/source changed during rearm fence")
        del resident._state("B").tasks["normal-present-cpu:B"]
        resident._normal_present_scheduler = None
        resident._normal_second_rejoin_cut = SecondRejoinCut(bridge, anchor)
        try:
            new = start_normal_resident_present_cpu(
                bridge=bridge, interval_s=interval_s,
            )
        except BaseException as exc:
            # Old tasks are already stopped and cannot regain authority.
            raise SecondRejoinHold("second original CPU tasks did not rearm") from exc
        if (
            new._tokens["A"].epoch != verified_a.resident_epoch
            or new._tokens["B"].epoch != verified_b.resident_epoch
            or new._tasks["A"] is old._tasks["A"]
            or new._tasks["B"] is old._tasks["B"]
        ):
            new._stopped = True
            new._current.clear()
            for task in new._tasks.values():
                task.cancel()
            raise SecondRejoinHold("rearmed original CPU epochs disagree")
        proof = SecondRejoinRearm(
            first_pair_revision=anchor.pair_revision,
            second_pair_revision=_revision(dict(
                a_composite=verified_a.composite_revision,
                b_composite=verified_b.composite_revision,
                a_native=verified_a.native_revision,
                b_native=verified_b.native_revision,
                paper_sha256=verified_a.paper_log_sha256,
            )),
            first_a_native=anchor.a.native_session_id,
            second_a_native=verified_a.native_session_id,
            continuous_b_native=verified_b.native_session_id,
            old_a_task_epoch=anchor.a_task.token.epoch,
            new_a_task_epoch=new._tokens["A"].epoch,
            old_b_task_epoch=anchor.b_task.token.epoch,
            new_b_task_epoch=new._tokens["B"].epoch,
            retired_a_cpu_task=old._tasks["A"].done(),
            retired_b_cpu_task=old._tasks["B"].done(),
        )
        resident._normal_second_rejoin_rearm = proof
        return new, proof
