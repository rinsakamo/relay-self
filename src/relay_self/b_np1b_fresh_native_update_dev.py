"""Same-session native observation update; Paper qualification remains historical."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerObservation,
)
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.world_resident_lifecycle_dev import Presence


class FreshNativeHold(RuntimeError):
    """Current native source could not be safely updated."""


@dataclass(frozen=True, slots=True)
class NativeRevision:
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
    native_revision: str


def _snapshot(bridge, sid):
    resident = bridge.cognitive_work
    owner = bridge.owners[sid]
    world = bridge.lifecycle.world
    session = bridge.sessions[sid]
    evidence = bridge.last_login_evidence[sid]
    initial = bridge.last_login_observations[sid]
    scope = resident.current_scope(sid)
    current = owner.current_worldbody_observation
    bridge._check_world()
    if (resident.owners[sid] is not owner or owner.cohort is not resident
            or owner.self_id != sid or owner.retained.identity.self_id != sid
            or bridge.lifecycle.view(sid).status is not Presence.ONLINE
            or sid in bridge._pending_login or sid in bridge.retired
            or session.process_returncode is not None
            or type(session.owned_child_pid) is not int or session.owned_child_pid <= 0
            or scope[2] != world.epoch or scope[1] != session.started.session_id
            or bridge.physical.current_native_sessions[sid] != scope[1]
            or owner.native_session_id != scope[1]
            or evidence.self_id != sid or evidence.native_session_id != scope[1]
            or (evidence.world_id, evidence.branch_id, evidence.paper_session_id, evidence.world_epoch)
            != (world.world_id, world.branch_id, world.paper_session_id, world.epoch)
            or not evidence.new_native_source_verified or not evidence.physical_wal_clear
            or evidence.action_issue_authorized or initial.session_id != scope[1]
            or initial.request_id != evidence.observation_ref
            or not isinstance(current, MineflayerObservation) or current.kind != 'probe'
            or current.session_id != scope[1] or current.snapshot.time is None
            or current.snapshot.time.day * 24000 + current.snapshot.time.time_of_day
            != owner.last_observed_tick or owner.fresh_native_observation_required):
        raise FreshNativeHold('original resident/native scope unavailable')
    return (owner, world, session, evidence, initial, scope, current, owner.last_observed_tick,
            session.owned_child_pid)


async def update_fresh_native(*, bridge: OwnedResidentPhysicalBridge, self_id: str,
                              initial_receipt: InitialSourceReceipt) -> NativeRevision:
    """Receive one correlated probe on the original session and adopt under its lock.

    This receipt qualifies Native only. It does not qualify a current Paper source.
    Callers must own the existing session's receiver for the duration of this operation.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise FreshNativeHold('original bridge required')
    resident = bridge.cognitive_work
    claim = None
    try:
        with resident.lock:
            snap = _snapshot(bridge, self_id)
            owner, world, session, evidence, initial, scope, current, old_tick, pid = snap
            if (type(initial_receipt) is not InitialSourceReceipt
                    or (initial_receipt.self_id, initial_receipt.owner_identity,
                        initial_receipt.resident_epoch, initial_receipt.world_id,
                        initial_receipt.branch_id, initial_receipt.world_epoch,
                        initial_receipt.native_session_id, initial_receipt.native_request_id,
                        initial_receipt.native_sequence, initial_receipt.native_source_ref,
                        initial_receipt.native_world_time)
                    != (self_id, str(owner.files.self_root), scope[0], world.world_id,
                        world.branch_id, world.epoch, scope[1], initial.request_id,
                        initial.seq, initial.provenance.reference, evidence.observed_world_tick)):
                raise FreshNativeHold('initial receipt does not bind original session')
            bound_initial = getattr(bridge, '_fresh_native_initial', {}).get(self_id)
            if bound_initial is not None and bound_initial != initial_receipt:
                raise FreshNativeHold('initial receipt changed')
            previous = getattr(bridge, '_fresh_native_current', {}).get(self_id)
            if ((previous is None and current is not initial)
                    or (previous is not None and (previous[0] is not current
                                                 or previous[1].resident_epoch != scope[0]))):
                raise FreshNativeHold('current native observation has no update provenance')
            pending = getattr(bridge, '_fresh_native_pending', None)
            if pending is None:
                pending = bridge._fresh_native_pending = {}
            if self_id in pending:
                raise FreshNativeHold('native update already receiving')
            claim = object()
            pending[self_id] = claim
        request = 'p0d-update-' + uuid.uuid4().hex
        deadline = asyncio.get_running_loop().time() + bridge.probe_timeout_s
        await asyncio.wait_for(session.send_observe(request), bridge.probe_timeout_s)
        probe = None
        for _ in range(256):
            left = deadline - asyncio.get_running_loop().time()
            if left <= 0:
                raise FreshNativeHold('native probe timed out')
            item = await asyncio.wait_for(session.receive(), left)
            if item.session_id != scope[1] or isinstance(item, (
                    MineflayerConnectionEnd, MineflayerAdapterErrorMessage, MineflayerCommandError)):
                raise FreshNativeHold('native stream failure')
            if isinstance(item, MineflayerObservation) and item.kind == 'probe':
                probe = item
                break
        if (probe is None or probe.request_id != request or probe.seq <= current.seq
                or probe.snapshot.time is None):
            raise FreshNativeHold('unmatched or stale native probe')
        native_time = probe.snapshot.time
        tick = native_time.day * 24000 + native_time.time_of_day
        if type(tick) is not int or tick < old_tick:
            raise FreshNativeHold('native World clock regressed')
        data = dict(self_id=self_id, owner_identity=str(owner.files.self_root),
                    resident_epoch=scope[0], world_id=world.world_id, branch_id=world.branch_id,
                    world_epoch=world.epoch, native_session_id=scope[1],
                    native_request_id=request, native_sequence=probe.seq,
                    native_source_ref=probe.provenance.reference, native_world_time=tick)
        revision = NativeRevision(**data, native_revision=_revision(data))
        with resident.lock:
            after = _snapshot(bridge, self_id)
            if (any(after[i] is not snap[i] for i in (0, 2, 3, 4, 6))
                    or after[1] != world or after[5] != scope or after[7] != old_tick
                    or after[8] != pid):
                raise FreshNativeHold('resident source changed during native I/O')
            try:
                owner.observe_world_tick(session_id=scope[1], world_tick=tick)
                owner.accept_rejoined_worldbody(probe, request_id=request)
                if owner.current_worldbody_observation is not probe or owner.last_observed_tick != tick:
                    raise FreshNativeHold('native adoption readback failed')
                if not hasattr(bridge, '_fresh_native_current'):
                    bridge._fresh_native_current = {}
                bridge._fresh_native_current[self_id] = (probe, revision)
                if not hasattr(bridge, '_fresh_native_initial'):
                    bridge._fresh_native_initial = {}
                bridge._fresh_native_initial[self_id] = initial_receipt
            except BaseException:
                resident.fence_self(self_id)
                raise
        return revision
    except FreshNativeHold:
        raise
    except Exception as exc:
        raise FreshNativeHold('native update unavailable') from exc
    finally:
        if claim is not None:
            with resident.lock:
                if bridge._fresh_native_pending.get(self_id) is claim:
                    del bridge._fresh_native_pending[self_id]


def read_rejoined_native_revision(*, bridge: OwnedResidentPhysicalBridge,
                                  self_id: str) -> NativeRevision:
    """Read the currently adopted login probe without qualifying any Paper source."""
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise FreshNativeHold('original bridge required')
    try:
        with bridge.cognitive_work.lock:
            owner, world, _, evidence, initial, scope, current, tick, _ = _snapshot(bridge, self_id)
            if (scope[0] <= 1 or current is not initial
                    or self_id in getattr(bridge, '_fresh_native_pending', {})
                    or self_id in getattr(bridge, '_fresh_native_current', {})
                    or initial.request_id != evidence.observation_ref):
                raise FreshNativeHold('rejoined login probe unavailable')
            data = dict(self_id=self_id, owner_identity=str(owner.files.self_root),
                        resident_epoch=scope[0], world_id=world.world_id,
                        branch_id=world.branch_id, world_epoch=world.epoch,
                        native_session_id=scope[1], native_request_id=initial.request_id,
                        native_sequence=initial.seq, native_source_ref=initial.provenance.reference,
                        native_world_time=tick)
            return NativeRevision(**data, native_revision=_revision(data))
    except FreshNativeHold:
        raise
    except (KeyError, AttributeError, RuntimeError, ValueError, TypeError) as exc:
        raise FreshNativeHold('rejoined native source unavailable') from exc


def read_continuing_b_native_revision(
    *, bridge: OwnedResidentPhysicalBridge,
    initial_receipt: InitialSourceReceipt,
) -> NativeRevision:
    """Read original B's unchanged session and latest proven Owner-adopted probe.

    B may have received new Native observations through update_fresh_native,
    but must retain its original login, original issuer, Owner and session.
    A caller's detached NativeRevision is never a current source credential.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise FreshNativeHold("original resident bridge required for B")
    try:
        with bridge.cognitive_work.lock:
            owner, world, session, evidence, initial, scope, current, tick, _ = (
                _snapshot(bridge, "B")
            )
            data_initial = dict(
                self_id="B", owner_identity=str(owner.files.self_root),
                resident_epoch=scope[0], world_id=world.world_id,
                branch_id=world.branch_id, world_epoch=world.epoch,
                native_session_id=scope[1],
                native_request_id=initial.request_id, native_sequence=initial.seq,
                native_source_ref=initial.provenance.reference,
                native_world_time=evidence.observed_world_tick,
            )
            if (
                type(initial_receipt) is not InitialSourceReceipt
                or any(getattr(initial_receipt, key) != value
                       for key, value in data_initial.items())
                or initial_receipt.native_revision != _revision(data_initial)
                or initial.kind != "probe"
                or initial.session_id != scope[1]
                or evidence.observation_ref != initial.request_id
                or scope[0] != initial_receipt.resident_epoch
                or "B" in getattr(bridge, "_fresh_native_pending", {})
            ):
                raise FreshNativeHold("original B Native history not owned")
            current_record = getattr(bridge, "_fresh_native_current", {}).get("B")
            bound_initial = getattr(bridge, "_fresh_native_initial", {}).get("B")
            if current is initial:
                if (
                    current_record is not None or bound_initial is not None
                    or tick != initial_receipt.native_world_time
                    or session._decoder.next_seq != initial.seq + 1
                ):
                    raise FreshNativeHold("B initial Native source is not current")
                return NativeRevision(**data_initial,
                                      native_revision=initial_receipt.native_revision)
            if (
                type(current_record) is not tuple or len(current_record) != 2
                or current_record[0] is not current
                or type(current_record[1]) is not NativeRevision
                or bound_initial != initial_receipt
                or current.request_id == initial.request_id
                or not current.request_id.startswith("p0d-update-")
                or current.seq <= initial.seq
                or session._decoder.next_seq != current.seq + 1
                or current.snapshot.time is None
                or tick < initial_receipt.native_world_time
            ):
                raise FreshNativeHold("B fresh Native update provenance missing")
            adopted = current_record[1]
            data = dict(
                self_id="B", owner_identity=str(owner.files.self_root),
                resident_epoch=scope[0], world_id=world.world_id,
                branch_id=world.branch_id, world_epoch=world.epoch,
                native_session_id=scope[1],
                native_request_id=current.request_id, native_sequence=current.seq,
                native_source_ref=current.provenance.reference,
                native_world_time=tick,
            )
            if adopted != NativeRevision(**data, native_revision=_revision(data)):
                raise FreshNativeHold("B update differs from adopted original Owner source")
            return adopted
    except FreshNativeHold:
        raise
    except (KeyError, AttributeError, RuntimeError, ValueError, TypeError) as exc:
        raise FreshNativeHold("original B Native update unavailable") from exc
