"""Read-only current source projection across independent Native and Paper clocks."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from relay_self.b_np1b_fresh_native_update_dev import NativeRevision, _snapshot
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28c2b_native_paper_body_link_dev import (
    paper_tick_ack_matches,
    verify_paper_a_b_presence,
)


class CompositeSourceHold(RuntimeError):
    """A current source cannot be qualified without changing cognition."""


@dataclass(frozen=True, slots=True)
class CompositeSourceReceipt:
    self_id: str
    world_id: str
    branch_id: str
    world_epoch: int
    resident_epoch: int
    native_session_id: str
    native_request_id: str
    native_sequence: int
    native_source_ref: str
    native_world_time: int
    native_revision: str
    paper_session_id: str
    paper_boot_id: str
    paper_pid: int
    paper_actor_uuid: str
    paper_tick: int
    paper_tick_ref: str
    paper_log_sha256: str
    paper_revision: str
    composite_revision: str
    initial_receipt_ref: str


def _native(bridge, sid, revision, initial):
    snap = _snapshot(bridge, sid)
    owner, world, _, evidence, probe_initial, scope, probe, _, _ = snap
    if (sid in getattr(bridge, '_fresh_native_pending', set())
            or type(revision) is not NativeRevision
            or type(initial) is not InitialSourceReceipt
            or getattr(bridge, '_fresh_native_initial', {}).get(sid) != initial
            or getattr(bridge, '_fresh_native_current', {}).get(sid) != (probe, revision)
            or probe is not bridge._fresh_native_current[sid][0]):
        raise CompositeSourceHold('native revision is stale or receiving')
    data = dict(self_id=sid, owner_identity=str(owner.files.self_root), resident_epoch=scope[0],
                world_id=world.world_id, branch_id=world.branch_id, world_epoch=world.epoch,
                native_session_id=scope[1], native_request_id=probe.request_id,
                native_sequence=probe.seq, native_source_ref=probe.provenance.reference,
                native_world_time=owner.last_observed_tick)
    if (revision != NativeRevision(**data, native_revision=_revision(data))
            or (initial.self_id, initial.owner_identity, initial.resident_epoch,
                initial.world_id, initial.branch_id, initial.world_epoch, initial.native_session_id,
                initial.native_request_id, initial.native_sequence, initial.native_source_ref, initial.native_world_time)
            != (sid, data['owner_identity'], scope[0], world.world_id, world.branch_id,
                world.epoch, scope[1], probe_initial.request_id, probe_initial.seq,
                probe_initial.provenance.reference, evidence.observed_world_tick)):
        raise CompositeSourceHold('native or initial source mismatch')
    return snap


def build_current_composite_source(*, bridge: OwnedResidentPhysicalBridge, self_id: str,
                                   native_revision: NativeRevision,
                                   initial_receipts: tuple[InitialSourceReceipt, ...]) -> CompositeSourceReceipt:
    """Read a new owned tick; only same-series association, not simultaneity or causation."""
    try:
        if (not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None
                or self_id not in ('A', 'B') or len(initial_receipts) != 2):
            raise CompositeSourceHold('original A/B bridge and receipts required')
        initials = {r.self_id: r for r in initial_receipts if type(r) is InitialSourceReceipt}
        if set(initials) != {'A', 'B'}:
            raise CompositeSourceHold('initial A/B receipts required')
        for receipt in initials.values():
            fields = asdict(receipt)
            native_fields = {k: fields[k] for k in ('self_id', 'owner_identity', 'resident_epoch',
                'world_id', 'branch_id', 'world_epoch', 'native_session_id', 'native_request_id',
                'native_sequence', 'native_source_ref', 'native_world_time')}
            paper_fields = {k: fields[k] for k in ('paper_session_id', 'paper_pid', 'paper_boot_id',
                'presence_boot_id', 'paper_tick', 'paper_tick_ref', 'paper_actor_uuid', 'paper_log_sha256')}
            if receipt.native_revision != _revision(native_fields) or receipt.paper_revision != _revision(paper_fields):
                raise CompositeSourceHold('initial receipt revision mismatch')
        resident = bridge.cognitive_work
        with resident.lock:
            snap = _native(bridge, self_id, native_revision, initials[self_id])
            world = bridge.lifecycle.world
            owners = tuple(bridge.owners[s] for s in ('A', 'B'))
            scopes = tuple(resident.current_scope(s) for s in ('A', 'B'))
            if (any(resident.owners[s] is not bridge.owners[s] for s in ('A', 'B'))
                    or any(s in getattr(bridge, '_fresh_native_pending', set()) for s in ('A', 'B'))):
                raise CompositeSourceHold('owner or native update changed')
            paper = bridge.paper
            process = paper._assert_owned()
            pid = process.pid
            if (paper.owned_session_id != world.paper_session_id or paper.world_id != world.world_id
                    or paper.branch_id != world.branch_id or type(pid) is not int or pid <= 0
                    or any((r.world_id, r.branch_id, r.world_epoch, r.paper_session_id, r.paper_pid)
                           != (world.world_id, world.branch_id, world.epoch, world.paper_session_id, pid)
                           for r in initials.values())):
                raise CompositeSourceHold('Paper scope mismatch')
        tick = paper.tick_readback(world.paper_session_id)
        log = paper.read_owned_log(world.paper_session_id)
        initial = initials[self_id]
        match = re.fullmatch(r'paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}', tick.source_ref)
        if (type(tick) is not PaperTickReceipt or match is None
                or tick.server_session_id != world.paper_session_id or type(tick.tick) is not int
                or tick.tick <= initial.paper_tick or match.group(1) != initial.paper_boot_id
                or not paper_tick_ack_matches(source_ref=tick.source_ref, boot_id=initial.paper_boot_id,
                    session_id=world.paper_session_id, world_id=world.world_id, tick=tick.tick, log=log)):
            raise CompositeSourceHold('fresh Paper tick unavailable')
        digest, trace, events = verify_paper_a_b_presence(
            bridge=bridge, paper_session_id=world.paper_session_id, world_id=world.world_id,
            tick=tick, log=log)
        lines = log.splitlines(keepends=True)
        # The historic receipt hashes the entire original log, including its final newline.
        prefixes = [i for i in range(1, len(lines) + 1)
                    if hashlib.sha256(b''.join(lines[:i])).hexdigest() == initial.paper_log_sha256]
        ack = f'P0D_TICK_ACK nonce={match.group(2)} boot={match.group(1)} session={world.paper_session_id} world={world.world_id} tick={tick.tick} source=PAPER_MAIN_THREAD'.encode()
        ack_lines = [i for i, line in enumerate(lines) if ack in line]
        if (len(prefixes) != 1 or len(ack_lines) != 1 or ack_lines[0] < prefixes[0]
                or trace.boot_id != initial.presence_boot_id
                or any(events[s][0].actor_uuid != initials[s].paper_actor_uuid
                       or initials[s].paper_log_sha256 != initial.paper_log_sha256
                       or initials[s].paper_boot_id != initial.paper_boot_id
                       or initials[s].presence_boot_id != trace.boot_id
                       or events[s][-1].line > ack_lines[0] for s in ('A', 'B'))
                or not any(e.event in ('PRESENT', 'MOVE') and e.line > prefixes[0]
                           and e.line <= ack_lines[0] and e.tick > initial.paper_tick
                           for e in events[self_id])):
            raise CompositeSourceHold('Paper history or fresh observation mismatch')
        paper_data = dict(paper_session_id=world.paper_session_id, paper_boot_id=initial.paper_boot_id,
                          paper_pid=pid, paper_actor_uuid=events[self_id][0].actor_uuid,
                          paper_tick=tick.tick, paper_tick_ref=tick.source_ref, paper_log_sha256=digest)
        paper_revision = _revision(paper_data)
        initial_ref = _revision(asdict(initial))
        composite = _revision(dict(native_revision=native_revision.native_revision,
                                   paper_revision=paper_revision, initial_receipt_ref=initial_ref))
        with resident.lock:
            after = _native(bridge, self_id, native_revision, initial)
            if (bridge.lifecycle.world != world or tuple(bridge.owners[s] for s in ('A', 'B')) != owners
                    or any(resident.owners[s] is not owners[i] for i, s in enumerate(('A', 'B')))
                    or tuple(resident.current_scope(s) for s in ('A', 'B')) != scopes
                    or any(s in getattr(bridge, '_fresh_native_pending', set()) for s in ('A', 'B'))
                    or any(after[i] is not snap[i] for i in (0, 2, 3, 4, 6))
                    or after[1] != snap[1] or after[5:] != snap[5:]
                    or bridge.paper is not paper or paper._assert_owned() is not process
                    or process.pid != pid or paper.owned_session_id != world.paper_session_id
                    or paper.world_id != world.world_id or paper.branch_id != world.branch_id
                    or paper.read_owned_log(world.paper_session_id) != log):
                raise CompositeSourceHold('source changed during verification')
            final = _native(bridge, self_id, native_revision, initial)
            if (any(final[i] is not snap[i] for i in (0, 2, 3, 4, 6))
                    or final[1] != world or final[5:] != snap[5:]
                    or tuple(resident.current_scope(s) for s in ('A', 'B')) != scopes
                    or any(resident.owners[s] is not owners[i] or bridge.owners[s] is not owners[i]
                           or s in getattr(bridge, '_fresh_native_pending', set())
                           for i, s in enumerate(('A', 'B')))):
                raise CompositeSourceHold('native changed during final Paper read')
        return CompositeSourceReceipt(self_id=self_id, world_id=world.world_id,
            branch_id=world.branch_id, world_epoch=world.epoch, resident_epoch=native_revision.resident_epoch,
            native_session_id=native_revision.native_session_id, native_request_id=native_revision.native_request_id,
            native_sequence=native_revision.native_sequence, native_source_ref=native_revision.native_source_ref,
            native_world_time=native_revision.native_world_time, native_revision=native_revision.native_revision,
            **paper_data, paper_revision=paper_revision, composite_revision=composite, initial_receipt_ref=initial_ref)
    except CompositeSourceHold:
        raise
    except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise CompositeSourceHold('current source unavailable') from exc
