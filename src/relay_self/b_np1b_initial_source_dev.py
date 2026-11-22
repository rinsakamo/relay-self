"""Fresh original-owner Native/Paper initial source, CPU/offline DEV."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28c2b_native_paper_body_link_dev import (
    paper_tick_ack_matches,
    verify_paper_a_b_presence,
)
from relay_self.world_resident_lifecycle_dev import Presence


class InitialSourceHold(RuntimeError):
    """The original sources changed or cannot be independently qualified."""


@dataclass(frozen=True, slots=True)
class InitialSourceReceipt:
    self_id: str
    owner_identity: str
    resident_epoch: int
    world_id: str
    branch_id: str
    world_epoch: int
    native_session_id: str
    native_request_id: str
    native_sequence: int
    native_source_ref: str
    native_world_time: int
    paper_session_id: str
    paper_pid: int
    paper_boot_id: str
    presence_boot_id: str
    paper_tick: int
    paper_tick_ref: str
    paper_actor_uuid: str
    paper_log_sha256: str
    native_revision: str
    paper_revision: str


def _revision(value):
    return 'sha256:' + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':')
    ).encode()).hexdigest()


def _native_snapshot(bridge):
    resident = bridge.cognitive_work
    world = bridge.lifecycle.world
    if (resident is None or not bridge.adopt_login_worldbody_dev
            or bridge.lifecycle.self_roster != ('A', 'B')
            or set(bridge.sessions) != {'A', 'B'}
            or bridge.paper.owned_session_id != world.paper_session_id
            or bridge.paper.world_id != world.world_id
            or bridge.paper.branch_id != world.branch_id):
        raise InitialSourceHold('original fresh A/B scope unavailable')
    result = {}
    for sid in ('A', 'B'):
        owner = bridge.owners[sid]
        probe = bridge.last_login_observations[sid]
        evidence = bridge.last_login_evidence[sid]
        session = bridge.sessions[sid]
        scope = resident.current_scope(sid)
        if (resident.owners[sid] is not owner or owner.cohort is not resident
                or owner.retained.identity.self_id != sid
                or owner.current_worldbody_observation is not probe
                or bridge.lifecycle.view(sid).status is not Presence.ONLINE
                or session.process_returncode is not None
                or type(session.owned_child_pid) is not int or session.owned_child_pid <= 0
                or scope[0] != 1 or world.epoch != 0
                or scope[1:] != (probe.session_id, world.epoch)
                or session.started.session_id != scope[1]
                or bridge.physical.current_native_sessions[sid] != scope[1]
                or owner.native_session_id != scope[1]
                or evidence.self_id != sid or evidence.native_session_id != scope[1]
                or (evidence.world_id, evidence.branch_id, evidence.paper_session_id,
                    evidence.world_epoch) != (world.world_id, world.branch_id,
                                              world.paper_session_id, world.epoch)
                or probe.kind != 'probe' or not probe.request_id
                or probe.request_id != evidence.observation_ref
                or probe.snapshot.time is None
                or probe.snapshot.time.day * 24000 + probe.snapshot.time.time_of_day
                != evidence.observed_world_tick
                or owner.last_observed_tick != evidence.observed_world_tick
                or not evidence.new_native_source_verified
                or not evidence.physical_wal_clear or evidence.action_issue_authorized):
            raise InitialSourceHold('original native owner, scope or adopted probe mismatch')
        result[sid] = (owner, probe, evidence, session, scope,
                       (session.started.session_id, session.process_returncode,
                        session.owned_child_pid, owner.native_session_id,
                        owner.last_observed_tick, probe.seq, probe.request_id,
                        probe.provenance.reference))
    if result['A'][4][1] == result['B'][4][1]:
        raise InitialSourceHold('native session collision')
    return world, result


def build_initial_source_receipts(*, bridge: OwnedResidentPhysicalBridge,
                                  tick: PaperTickReceipt) -> tuple[InitialSourceReceipt, ...]:
    """Reconcile an already obtained main-thread receipt without modifying either owner."""
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise InitialSourceHold('original bridge required')
    try:
        with bridge.cognitive_work.lock:
            world, native = _native_snapshot(bridge)
            process = bridge.paper._assert_owned()
            pid = process.pid
            if (type(pid) is not int or pid <= 0 or type(tick) is not PaperTickReceipt
                    or tick.server_session_id != world.paper_session_id
                    or type(tick.tick) is not int or tick.tick < 0):
                raise InitialSourceHold('Paper process or tick session mismatch')
            match = re.fullmatch(r'paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}', tick.source_ref)
            if match is None:
                raise InitialSourceHold('Paper tick boot missing')
            boot = match.group(1)
            log = bridge.paper.read_owned_log(world.paper_session_id)
            if not paper_tick_ack_matches(source_ref=tick.source_ref, boot_id=boot,
                                          session_id=world.paper_session_id,
                                          world_id=world.world_id, tick=tick.tick, log=log):
                raise InitialSourceHold('Paper nonce ACK mismatch')
            digest, trace, events = verify_paper_a_b_presence(
                bridge=bridge, paper_session_id=world.paper_session_id,
                world_id=world.world_id, tick=tick, log=log,
            )
            lines = log.decode('utf-8').splitlines()
            ready = f'P0D_TICK_READY boot={boot} source=PAPER_MAIN_THREAD'
            ack = f'P0D_TICK_ACK nonce={match.group(2)} boot={boot} session={world.paper_session_id} world={world.world_id} tick={tick.tick} source=PAPER_MAIN_THREAD'
            ready_lines = [i for i, line in enumerate(lines) if ready in line]
            ack_lines = [i for i, line in enumerate(lines) if ack in line]
            if (len(ready_lines) != 1 or len(ack_lines) != 1
                    or ready_lines[0] >= ack_lines[0]
                    or any(events[sid][-1].line > ack_lines[0] for sid in ('A', 'B'))):
                raise InitialSourceHold('Paper boot/ACK ordering mismatch')
            receipts = []
            for sid in ('A', 'B'):
                owner, probe, evidence, session, scope, _ = native[sid]
                native_data = dict(self_id=sid, owner_identity=str(owner.files.self_root),
                    resident_epoch=scope[0], world_id=world.world_id, branch_id=world.branch_id,
                    world_epoch=world.epoch, native_session_id=scope[1],
                    native_request_id=probe.request_id, native_sequence=probe.seq,
                    native_source_ref=probe.provenance.reference,
                    native_world_time=evidence.observed_world_tick)
                paper_data = dict(paper_session_id=world.paper_session_id, paper_pid=pid,
                    paper_boot_id=boot, presence_boot_id=trace.boot_id, paper_tick=tick.tick,
                    paper_tick_ref=tick.source_ref, paper_actor_uuid=events[sid][0].actor_uuid,
                    paper_log_sha256=digest)
                receipts.append(InitialSourceReceipt(**native_data, **paper_data,
                    native_revision=_revision(native_data), paper_revision=_revision(paper_data)))
            if (bridge.paper._assert_owned() is not process
                    or process.pid != pid
                    or bridge.paper.read_owned_log(world.paper_session_id) != log):
                raise InitialSourceHold('Paper source changed during verification')
            world_after, native_after = _native_snapshot(bridge)
            if (world_after != world or any(
                    native_after[sid][0] is not native[sid][0]
                    or native_after[sid][1] is not native[sid][1]
                    or native_after[sid][2:] != native[sid][2:]
                    for sid in ('A', 'B'))):
                raise InitialSourceHold('Native source changed during verification')
            return tuple(receipts)
    except InitialSourceHold:
        raise
    except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise InitialSourceHold('original source unavailable or invalid') from exc
