"""Read-only original-owner source reconciliation; not an authority receipt.

The Stage28 producer and the owned Paper process remain the trust boundary.
This readout neither attests a real trial nor authorizes subsequent work.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from relay_self import stage28c2b_native_paper_body_link_dev as paper_link
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28NativePaperBodyLink,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import (
    _require_live_original,
)
from relay_self.world_resident_lifecycle_dev import WorldLifetime


class BD1bSourceHold(RuntimeError):
    """The original sources cannot be reconciled."""


@dataclass(frozen=True, slots=True)
class BD1bOwnerSource:
    self_id: str
    world_id: str
    branch_id: str
    world_epoch: int
    paper_session_id: str
    paper_boot_id: str
    presence_boot_id: str
    paper_tick_source_ref: str
    paper_log_sha256: str
    paper_actor_uuid: str
    resident_epoch: int
    native_session_id: str
    native_probe_ref: str
    native_probe_seq: int
    native_probe_source_ref: str
    native_world_time_tick: int


def build_bd1b_owner_source(*, bridge: OwnedResidentPhysicalBridge,
                            boot: Stage28ForkPaperEpoch, world: WorldLifetime,
                            links: tuple[Stage28NativePaperBodyLink, ...],
                            self_id: str) -> BD1bOwnerSource:
    """Reconcile both sources under the existing resident lock, without writes.

    The owned log must still match the producer's snapshot; later log growth
    conservatively requires a new producer receipt. Paper and native clocks
    are never compared to each other.
    """
    return _build_source(bridge=bridge, boot=boot, world=world, links=links,
                         self_id=self_id, require_original=_require_live_original)


def _build_source(*, bridge, boot, world, links, self_id, require_original):
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise BD1bSourceHold("original resident bridge required")
    with bridge.cognitive_work.lock:
        try:
            scope, probe = require_original(
                bridge=bridge, sid=self_id, boot=boot, world=world,
            )
            if (type(links) is not tuple or len(links) != 2
                or any(type(link) is not Stage28NativePaperBodyLink for link in links)
                or {link.self_id for link in links} != {"A", "B"}
                or bridge.lifecycle.self_roster != ("A", "B")):
                raise BD1bSourceHold("exact A/B links and roster required")
            by_self = {link.self_id: link for link in links}
            process = bridge.paper._assert_owned()
            log = bridge.paper.read_owned_log(boot.paper_session_id)
            digest = hashlib.sha256(log).hexdigest()
            trace = paper_link.parse_owned_paper_resident_trace(
                owned_paper_session_id=boot.paper_session_id,
                expected_world_uuid=boot.source_world_id,
                owned_paper_log=log,
                log_ref="paper-owned-log:" + boot.paper_session_id + ":sha256:" + digest,
            )
            first = by_self["A"]
            if (process.pid != boot.paper_pid
                or not trace.boot_id or trace.paper_session_id != boot.paper_session_id
                or not paper_link.paper_tick_ack_matches(
                    source_ref=first.paper_tick_source_ref, boot_id=boot.paper_boot_id,
                    session_id=boot.paper_session_id, world_id=boot.source_world_id,
                    tick=world.world_tick, log=log)):
                raise BD1bSourceHold("owned Paper source or ACK mismatch")
            actors = set()
            sessions = set()
            for sid in ("A", "B"):
                link = by_self[sid]
                owner = bridge.owners[sid]
                native = bridge.last_login_evidence[sid]
                body = bridge.last_login_observations[sid]
                current = bridge.cognitive_work.current_scope(sid)
                session = bridge.sessions[sid]
                events = [e for e in trace.events if e.name == bridge.configs[sid].username]
                if (current[1:] != (body.session_id, world.epoch)
                    or native.self_id != sid or native.world_id != world.world_id
                    or native.branch_id != world.branch_id
                    or native.paper_session_id != world.paper_session_id
                    or native.world_epoch != world.epoch
                    or native.observed_world_tick != owner.last_observed_tick
                    or not all((native.old_native_invalidated, native.physical_wal_clear,
                                native.stale_gpu_fenced, native.stale_transport_fenced,
                                native.new_native_source_verified))
                    or session.started.session_id != body.session_id
                    or type(session.owned_child_pid) is not int or session.owned_child_pid <= 0
                    or body.session_id in bridge.forbidden_native_sessions
                    or link.native_session_id != body.session_id
                    or link.native_probe_ref != body.request_id
                    or link.native_world_time_tick != native.observed_world_tick
                    or link.paper_session_id != world.paper_session_id
                    or link.tick_boot_id != boot.paper_boot_id
                    or link.presence_boot_id != trace.boot_id
                    or link.paper_tick_source_ref != first.paper_tick_source_ref
                    or link.paper_log_sha256 != digest
                    or link.clocks_numerically_comparable is not False
                    or link.physical_action_issue_authorized is not False
                    or not events or events[0].event != "JOIN"
                    or sum(e.event == "JOIN" for e in events) != 1
                    or any(e.event == "QUIT" for e in events)
                    or not any(e.event in ("PRESENT", "MOVE") and e.line > events[0].line for e in events)
                    or len({e.actor_uuid for e in events}) != 1
                    or events[0].actor_uuid != link.paper_actor_uuid
                    or events[0].tick < boot.boot_tick
                    or events[-1].tick > world.world_tick
                    or events[-1].tick != link.paper_observed_tick):
                    raise BD1bSourceHold("original A/B native or Paper link mismatch")
                actors.add(link.paper_actor_uuid)
                sessions.add(body.session_id)
            if len(actors) != 2 or len(sessions) != 2:
                raise BD1bSourceHold("A/B actor or native collision")
            # The resident lock does not lock the external Paper process.  A
            # changed log invalidates the snapshot, even when all earlier
            # checks succeeded against its former bytes.
            if (bridge.paper._assert_owned().pid != process.pid
                    or bridge.paper.read_owned_log(boot.paper_session_id) != log):
                raise BD1bSourceHold("owned Paper log changed during verification")
            link = by_self[self_id]
            return BD1bOwnerSource(
                self_id, world.world_id, world.branch_id, world.epoch,
                world.paper_session_id, boot.paper_boot_id, link.presence_boot_id,
                link.paper_tick_source_ref, digest, link.paper_actor_uuid,
                scope[0], scope[1], probe.request_id, probe.seq,
                probe.provenance.reference, link.native_world_time_tick,
            )
        except BD1bSourceHold:
            raise
        except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
            raise BD1bSourceHold("original source unavailable or stale") from exc
