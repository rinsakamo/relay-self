"""Owner-bound CPU-only bridge to the existing Paper reJOIN stream verifier.

No current composite source, physical issue, model, or Question adoption is granted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from relay_self.b_np1b_fresh_native_update_dev import (
    NativeRevision,
    read_continuing_b_native_revision,
    read_rejoined_native_revision,
)
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.b_np1b_rejoin_paper_dev import RejoinPaperEvidence, verify_rejoin_paper
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.world_resident_lifecycle_dev import Presence


class OwnerBoundRejoinHold(RuntimeError):
    """Original Owner, Native, retirement or Paper source is not qualified."""


@dataclass(frozen=True, slots=True)
class OwnerBoundRejoinPaperEvidence:
    """Verified sources for later composition, NOT a composite source receipt."""

    self_id: str
    world_id: str
    branch_id: str
    world_epoch: int
    old_resident_epoch: int
    resident_epoch: int
    old_native_session_id: str
    native_session_id: str
    native_revision: str
    b_native_revision: str
    old_logout_source_ref: str
    historical_initial_ref: str
    paper_session_id: str
    paper_pid: int
    paper_boot_id: str
    paper_actor_uuid: str
    paper_tick: int
    paper_tick_ref: str
    paper_log_sha256: str
    paper_evidence: RejoinPaperEvidence


def _initials(receipts):
    if (type(receipts) is not tuple or len(receipts) != 2
            or any(type(r) is not InitialSourceReceipt for r in receipts)):
        raise OwnerBoundRejoinHold("original A/B initial receipts required")
    result = {r.self_id: r for r in receipts}
    if set(result) != {"A", "B"}:
        raise OwnerBoundRejoinHold("distinct A/B initial receipts required")
    for receipt in result.values():
        fields = asdict(receipt)
        native_keys = (
            "self_id", "owner_identity", "resident_epoch", "world_id", "branch_id",
            "world_epoch", "native_session_id", "native_request_id", "native_sequence",
            "native_source_ref", "native_world_time",
        )
        paper_keys = (
            "paper_session_id", "paper_pid", "paper_boot_id", "presence_boot_id",
            "paper_tick", "paper_tick_ref", "paper_actor_uuid", "paper_log_sha256",
        )
        if (receipt.native_revision != _revision({k: fields[k] for k in native_keys})
                or receipt.paper_revision != _revision({k: fields[k] for k in paper_keys})):
            raise OwnerBoundRejoinHold("initial source revision invalid")
    a, b = result["A"], result["B"]
    if ((a.world_id, a.branch_id, a.world_epoch, a.paper_session_id, a.paper_pid,
         a.paper_boot_id, a.presence_boot_id, a.paper_tick, a.paper_log_sha256)
            != (b.world_id, b.branch_id, b.world_epoch, b.paper_session_id, b.paper_pid,
                b.paper_boot_id, b.presence_boot_id, b.paper_tick, b.paper_log_sha256)
            or a.paper_actor_uuid == b.paper_actor_uuid
            or a.native_session_id == b.native_session_id):
        raise OwnerBoundRejoinHold("historical Self/Paper A/B sources disagree")
    return result


def _owner_snapshot(bridge, originals):
    """Called only under the ORIGINAL resident lock."""
    resident = bridge.cognitive_work
    world = bridge.lifecycle.world
    a, b = originals["A"], originals["B"]
    if (resident is None or not bridge.adopt_login_worldbody_dev
            or bridge.lifecycle.self_roster != ("A", "B")
            or set(bridge.owners) != {"A", "B"}
            or any(bridge.lifecycle.view(s).status is not Presence.ONLINE
                   for s in ("A", "B"))
            or any(s in bridge._pending_login or s in bridge.retired
                   or s in getattr(bridge, "_fresh_native_pending", {})
                   for s in ("A", "B"))
            or bridge.physical.active_action_ids
            or (world.world_id, world.branch_id, world.epoch, world.paper_session_id)
            != (a.world_id, a.branch_id, a.world_epoch, a.paper_session_id)
            or bridge.paper.owned_session_id != world.paper_session_id
            or bridge.paper.world_id != world.world_id
            or bridge.paper.branch_id != world.branch_id):
        raise OwnerBoundRejoinHold("original live A/B scope unavailable")
    bridge._check_world()
    oa, ob = bridge.owners["A"], bridge.owners["B"]
    sa, sb = bridge.sessions["A"], bridge.sessions["B"]
    if (resident.owners["A"] is not oa or resident.owners["B"] is not ob
            or oa.cohort is not resident or ob.cohort is not resident
            or str(oa.files.self_root) != a.owner_identity
            or str(ob.files.self_root) != b.owner_identity
            or sa.process_returncode is not None or sb.process_returncode is not None
            or type(sa.owned_child_pid) is not int or sa.owned_child_pid <= 0
            or type(sb.owned_child_pid) is not int or sb.owned_child_pid <= 0):
        raise OwnerBoundRejoinHold("original owner or process changed")
    scope_a = resident.current_scope("A")
    scope_b = resident.current_scope("B")
    login_a = bridge.last_login_evidence["A"]
    login_b = bridge.last_login_evidence["B"]
    probe_a = bridge.last_login_observations["A"]
    probe_b = bridge.last_login_observations["B"]
    retired = bridge._b_np1b_retired_login.get("A")
    if retired is None:
        raise OwnerBoundRejoinHold("original Bridge logout proof unavailable")
    logout, prior_scope, prior_owner, old_login, old_probe = retired
    if (prior_owner is not oa
            or prior_scope != (a.resident_epoch, a.native_session_id, a.world_epoch)
            or old_login.self_id != "A" or old_login.native_session_id != a.native_session_id
            or old_login.observation_ref != a.native_request_id
            or old_login.observed_world_tick != a.native_world_time
            or (old_login.world_id, old_login.branch_id, old_login.paper_session_id, old_login.world_epoch)
            != (a.world_id, a.branch_id, a.paper_session_id, a.world_epoch)
            or old_probe.kind != "probe" or old_probe.session_id != a.native_session_id
            or old_probe.request_id != a.native_request_id
            or old_probe.seq != a.native_sequence
            or old_probe.provenance.reference != a.native_source_ref
            or scope_a[0] <= prior_scope[0]
            or scope_a[1] == a.native_session_id
            or scope_a[2] != world.epoch
            or scope_b != (b.resident_epoch, b.native_session_id, b.world_epoch)
            or a.native_session_id not in bridge.forbidden_native_sessions
            or logout.self_id != "A" or logout.world_epoch != world.epoch
            or logout.native_session_id != prior_scope[1]
            or not logout.source_ref.startswith("original-issuer:")
            or logout.persisted_cognition_ref != f"cognition-file:{oa.files.cognition_file}"
            or not all((
                logout.physical_issuer_revoked, logout.no_physical_inflight,
                logout.physical_wal_clear, logout.native_terminated,
                logout.stale_gpu_fenced, logout.peer_transport_drained,
            )) or logout.action_issue_authorized
            or login_a.self_id != "A" or login_a.native_session_id != scope_a[1]
            or login_a.world_id != world.world_id or login_a.branch_id != world.branch_id
            or login_a.paper_session_id != world.paper_session_id
            or login_a.world_epoch != world.epoch
            or login_a.observation_ref == a.native_request_id
            or login_b.self_id != "B" or login_b.native_session_id != b.native_session_id
            or login_b.observation_ref != b.native_request_id
            or login_b.observed_world_tick != b.native_world_time
            or probe_b.seq != b.native_sequence
            or probe_b.provenance.reference != b.native_source_ref
            or sa.started.session_id != scope_a[1] or sb.started.session_id != scope_b[1]
            or bridge.physical.current_native_sessions["A"] != scope_a[1]
            or bridge.physical.current_native_sessions["B"] != scope_b[1]
            or probe_a is not oa.current_worldbody_observation
            or probe_a.session_id != scope_a[1]
            or probe_a.request_id != login_a.observation_ref
            or probe_b.session_id != scope_b[1]
            or probe_b.request_id != login_b.observation_ref):
        raise OwnerBoundRejoinHold("foreign, unretired or stale Native lifecycle")
    native = read_rejoined_native_revision(bridge=bridge, self_id="A")
    if (type(native) is not NativeRevision or native.resident_epoch != scope_a[0]
            or native.native_session_id != scope_a[1]
            or native.native_request_id != probe_a.request_id):
        raise OwnerBoundRejoinHold("rejoined Native revision is not current")
    b_native = read_continuing_b_native_revision(
        bridge=bridge, initial_receipt=b,
    )
    if (type(b_native) is not NativeRevision or b_native.self_id != "B"
            or b_native.resident_epoch != scope_b[0]
            or b_native.native_session_id != scope_b[1]
            or b_native.native_sequence < probe_b.seq
            or b_native.native_world_time < b.native_world_time):
        raise OwnerBoundRejoinHold("B original session / fresh Native adoption invalid")
    paper = bridge.paper
    process = paper._assert_owned()
    if process.pid != a.paper_pid:
        raise OwnerBoundRejoinHold("owned Paper process changed")
    # Identity checks in the final readback use object identity, not only equal field values.
    return (
        world, oa, ob, sa, sb, scope_a, scope_b, login_a, login_b, probe_a,
        probe_b, logout, prior_scope, native, paper, process, old_login, old_probe,
    )


def build_owner_bound_rejoin_paper(
    *, bridge: OwnedResidentPhysicalBridge,
    initial_receipts: tuple[InitialSourceReceipt, ...],
) -> OwnerBoundRejoinPaperEvidence:
    """Join the actual Bridge retirement/relogin to its owned Paper stream.

    Callers cannot provide an arbitrary logout proof, login proof, or Paper tick.
    This is a read-only qualification, not a new source authority.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise OwnerBoundRejoinHold("original resident Bridge required")
    try:
        originals = _initials(initial_receipts)
        resident = bridge.cognitive_work
        with resident.lock:
            before = _owner_snapshot(bridge, originals)
            before_b_native = read_continuing_b_native_revision(
                bridge=bridge, initial_receipt=originals["B"],
            )
        (world, _oa, _ob, _sa, _sb, scope_a, _scope_b, login_a, _login_b,
         _probe_a, _probe_b, logout, prior_scope, native, paper, process,
         _old_login, _old_probe) = before
        tick = paper.tick_readback(world.paper_session_id)
        log = paper.read_owned_log(world.paper_session_id)
        source = verify_rejoin_paper(
            log=log, world=world, tick=tick,
            paper_boot_id=originals["A"].paper_boot_id,
            presence_boot_id=originals["A"].presence_boot_id,
            a_name=bridge.configs["A"].username, b_name=bridge.configs["B"].username,
            a_actor=originals["A"].paper_actor_uuid,
            b_actor=originals["B"].paper_actor_uuid,
            a_logout=logout, a_relogin=login_a,
            original_b_native=originals["B"].native_session_id,
            surviving_b_native=_scope_b_native(before),
            historical_log_sha256=originals["A"].paper_log_sha256,
            historical_tick=originals["A"].paper_tick,
        )
        with resident.lock:
            after = _owner_snapshot(bridge, originals)
            after_b_native = read_continuing_b_native_revision(
                bridge=bridge, initial_receipt=originals["B"],
            )
            if (after_b_native != before_b_native
                    or any(after[i] is not before[i]
                    for i in (1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17))
                    or any(after[i] != before[i] for i in (0, 5, 6, 12, 13))
                    or paper._assert_owned() is not process
                    or paper.read_owned_log(world.paper_session_id) != log):
                raise OwnerBoundRejoinHold("Native or Paper changed during verification")
        return OwnerBoundRejoinPaperEvidence(
            self_id="A", world_id=world.world_id, branch_id=world.branch_id,
            world_epoch=world.epoch, old_resident_epoch=prior_scope[0],
            resident_epoch=scope_a[0],
            old_native_session_id=logout.native_session_id,
            native_session_id=native.native_session_id,
            native_revision=native.native_revision,
            b_native_revision=before_b_native.native_revision,
            old_logout_source_ref=logout.source_ref,
            historical_initial_ref=_revision(asdict(originals["A"])),
            paper_session_id=world.paper_session_id,
            paper_pid=process.pid, paper_boot_id=originals["A"].paper_boot_id,
            paper_actor_uuid=originals["A"].paper_actor_uuid,
            paper_tick=tick.tick, paper_tick_ref=tick.source_ref,
            paper_log_sha256=source.log_sha256, paper_evidence=source,
        )
    except OwnerBoundRejoinHold:
        raise
    except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise OwnerBoundRejoinHold("owner-bound rejoin Paper source unavailable") from exc


def _scope_b_native(snapshot) -> str:
    return snapshot[6][1]
