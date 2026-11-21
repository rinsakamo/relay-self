"""Read-only original-owner source reconciliation; not an authority receipt.

The Stage28 producer and the owned Paper process remain the trust boundary.
This readout neither attests a real trial nor authorizes subsequent work.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from relay_self import stage28c2b_native_paper_body_link_dev as paper_link
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28NativePaperBodyLink,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import _require_live_original
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
                            self_id: str,
                            i1_complete_paper_prefix: bool = False,
                            i2b_read_attached_lane: bool = False) -> BD1bOwnerSource:
    """Reconcile both sources under the existing resident lock, without writes.

    Normal B requires the full owned log's SHA, unchanged. Explicit I1-only
    readback requires the current owned stream's LAST exact LF-terminated
    prefix SHA to equal the freshly linked producer SHA; a trailing partial
    Paper console prompt is not an ACK or evidence. Later *complete* lines
    force a new producer link. Paper/native clocks remain independent.
    """
    if (not isinstance(bridge, OwnedResidentPhysicalBridge)
            or bridge.cognitive_work is None
            or type(i1_complete_paper_prefix) is not bool):
        raise BD1bSourceHold("original resident bridge required")
    with bridge.cognitive_work.lock:
        try:
            scope, probe = _require_live_original(
                bridge=bridge, sid=self_id, boot=boot, world=world,
                i2b_read_attached_lane=i2b_read_attached_lane,
            )
            if (type(links) is not tuple or len(links) != 2
                or any(type(link) is not Stage28NativePaperBodyLink for link in links)
                or {link.self_id for link in links} != {"A", "B"}
                or bridge.lifecycle.self_roster != ("A", "B")):
                raise BD1bSourceHold("exact A/B links and roster required")
            by_self = {link.self_id: link for link in links}
            process = bridge.paper._assert_owned()
            raw_log = bridge.paper.read_owned_log(boot.paper_session_id)
            first = by_self["A"]
            match = re.fullmatch(
                r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
                first.paper_tick_source_ref,
            )
            if (process.pid != boot.paper_pid or match is None
                    or match.group(1) != boot.paper_boot_id):
                raise BD1bSourceHold("owned Paper source or ACK mismatch")
            marker = (
                f"P0D_TICK_ACK nonce={match.group(2)} boot={boot.paper_boot_id} "
                f"session={boot.paper_session_id} world={boot.source_world_id} "
                f"tick={world.world_tick} source=PAPER_MAIN_THREAD"
            )
            # The exact same trusted original Paper Popen is read back.
            # I1 projects only its last completed original line, requiring
            # the fresh ACK within that original prefix. Normal B continues
            # to check the entire raw log byte-for-byte, as before.
            log = (
                paper_link.i1_complete_owned_paper_prefix(
                    raw_log, ack_marker=marker.encode("utf-8"),
                ) if i1_complete_paper_prefix else raw_log
            )
            digest = hashlib.sha256(log).hexdigest()
            trace = paper_link.parse_owned_paper_resident_trace(
                owned_paper_session_id=boot.paper_session_id,
                expected_world_uuid=boot.source_world_id,
                owned_paper_log=log,
                log_ref="paper-owned-log:" + boot.paper_session_id + ":sha256:" + digest,
            )
            if (not trace.boot_id or trace.paper_session_id != boot.paper_session_id
                    or marker not in log.decode("utf-8", errors="replace")):
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
            link = by_self[self_id]
            return BD1bOwnerSource(
                self_id, world.world_id, world.branch_id, world.epoch,
                world.paper_session_id, boot.paper_boot_id, link.presence_boot_id,
                link.paper_tick_source_ref, digest, link.paper_actor_uuid,
                scope[0], scope[1], probe.request_id, probe.seq,
                probe.provenance.reference, link.native_world_time_tick,
            )
        except BD1bSourceHold as exc:
            # On the explicit I1 DEV path, retain the *actual read() bytes* in
            # the escaping exception for the original Runner to freeze on
            # failure. Merely rereading the growing Paper log in the Runner
            # cannot reconstruct these failure-time bytes. Do not write here:
            # this source reconciliation remains strictly read-only.
            if i1_complete_paper_prefix and "raw_log" in locals():
                exc.i1_original_paper_readback = raw_log
                exc.i1_source_debug = {
                    "phase": "bd1b_source_hold",
                    "self_id": self_id,
                    "raw_sha256": hashlib.sha256(raw_log).hexdigest(),
                    "raw_size": len(raw_log),
                    "projection_sha256": (
                        hashlib.sha256(log).hexdigest()
                        if "log" in locals() else None
                    ),
                    "projection_size": len(log) if "log" in locals() else None,
                    "link_sha256_A": by_self["A"].paper_log_sha256,
                    "link_sha256_B": by_self["B"].paper_log_sha256,
                    "paper_session_id": boot.paper_session_id,
                }
            raise
        except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
            failure = BD1bSourceHold("original source unavailable or stale")
            if i1_complete_paper_prefix and "raw_log" in locals():
                failure.i1_original_paper_readback = raw_log
                failure.i1_source_debug = {
                    "phase": "bd1b_source_exception",
                    "self_id": self_id,
                    "source_type": type(exc).__name__,
                    "raw_sha256": hashlib.sha256(raw_log).hexdigest(),
                    "raw_size": len(raw_log),
                    "projection_sha256": (
                        hashlib.sha256(log).hexdigest()
                        if "log" in locals() else None
                    ),
                    "projection_size": len(log) if "log" in locals() else None,
                    "link_sha256_A": by_self["A"].paper_log_sha256,
                    "link_sha256_B": by_self["B"].paper_log_sha256,
                    "paper_session_id": boot.paper_session_id,
                }
            raise failure from exc
