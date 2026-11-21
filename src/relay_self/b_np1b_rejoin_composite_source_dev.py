"""Current, immutable composite source after the ORIGINAL A logout/reJOIN.

The initial and pre-logout composite receipts are history, never current authority.
Only the original resident/Bridge and an independently re-read owned Paper stream
can issue this CPU/offline DEV receipt. Native and Paper clocks stay separate.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from relay_self.b_np1b_current_composite_source_dev import CompositeSourceReceipt
from relay_self.b_np1b_fresh_native_update_dev import (
    NativeRevision,
    read_continuing_b_native_revision,
    read_rejoined_native_revision,
)
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.b_np1b_owner_bound_rejoin_dev import (
    OwnerBoundRejoinPaperEvidence,
    _initials,
    _owner_snapshot,
    build_owner_bound_rejoin_paper,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28c2b_native_paper_body_link_dev import paper_tick_ack_matches


class RejoinCompositeHold(RuntimeError):
    """A fresh post-reJOIN current source is not independently qualified."""


@dataclass(frozen=True, slots=True)
class RejoinedCompositeSourceReceipt(CompositeSourceReceipt):
    """Same canonical source fields, with distinct logout/reJOIN provenance."""

    owner_identity: str
    old_resident_epoch: int
    old_native_session_id: str
    old_logout_source_ref: str
    historical_composite_ref: str
    rejoin_paper_revision: str
    b_continuity_revision: str
    paper_quit_line: int
    paper_rejoin_line: int
    paper_present_line: int
    b_present_line: int


def _historical_composite(old: CompositeSourceReceipt, initial: InitialSourceReceipt,
                          log: bytes) -> str:
    """Validate historical consistency, not authenticate a prior caller's receipt."""
    if type(old) is not CompositeSourceReceipt or type(initial) is not InitialSourceReceipt:
        raise RejoinCompositeHold("historical composite/initial types required")
    fields = asdict(old)
    native = dict(
        self_id=old.self_id, owner_identity=initial.owner_identity,
        resident_epoch=old.resident_epoch, world_id=old.world_id,
        branch_id=old.branch_id, world_epoch=old.world_epoch,
        native_session_id=old.native_session_id,
        native_request_id=old.native_request_id, native_sequence=old.native_sequence,
        native_source_ref=old.native_source_ref, native_world_time=old.native_world_time,
    )
    paper_keys = (
        "paper_session_id", "paper_boot_id", "paper_pid", "paper_actor_uuid",
        "paper_tick", "paper_tick_ref", "paper_log_sha256",
    )
    paper = {key: fields[key] for key in paper_keys}
    initial_ref = _revision(asdict(initial))
    if (
        old.self_id != initial.self_id
        or (old.world_id, old.branch_id, old.world_epoch, old.resident_epoch,
            old.native_session_id, old.paper_session_id, old.paper_pid,
            old.paper_boot_id, old.paper_actor_uuid)
        != (initial.world_id, initial.branch_id, initial.world_epoch,
            initial.resident_epoch, initial.native_session_id,
            initial.paper_session_id, initial.paper_pid, initial.paper_boot_id,
            initial.paper_actor_uuid)
        or old.native_sequence <= initial.native_sequence
        or old.native_request_id == initial.native_request_id
        or old.native_world_time < initial.native_world_time
        or old.paper_tick <= initial.paper_tick
        or old.initial_receipt_ref != initial_ref
        or old.native_revision != _revision(native)
        or old.paper_revision != _revision(paper)
        or old.composite_revision != _revision(dict(
            native_revision=old.native_revision, paper_revision=old.paper_revision,
            initial_receipt_ref=initial_ref,
        ))
    ):
        raise RejoinCompositeHold("old composite history is inconsistent")
    lines = log.splitlines(keepends=True)
    prefix = b""
    historical_log = None
    for line in lines:
        prefix += line
        if hashlib.sha256(prefix).hexdigest() == old.paper_log_sha256:
            if historical_log is not None:
                raise RejoinCompositeHold("historical Paper prefix ambiguous")
            historical_log = prefix
    if historical_log is None or not paper_tick_ack_matches(
        source_ref=old.paper_tick_ref, boot_id=old.paper_boot_id,
        session_id=old.paper_session_id, world_id=old.world_id,
        tick=old.paper_tick, log=historical_log,
    ):
        raise RejoinCompositeHold("old Paper receipt is not in owned history")
    return _revision(fields)


def build_rejoined_composite_source(
    *, bridge: OwnedResidentPhysicalBridge,
    initial_receipts: tuple[InitialSourceReceipt, ...],
    historical_composite: CompositeSourceReceipt,
) -> RejoinedCompositeSourceReceipt:
    """Re-derive current Native and Paper evidence, finalizing under resident lock.

    No externally supplied logout witness, Paper evidence, Native revision or
    source hash is accepted. History is only a reference, not current admission.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise RejoinCompositeHold("original A/B resident Bridge required")
    try:
        # An out-of-lock read is never a final admission. Detect changes by
        # comparing it with a second complete verifier inside the original lock.
        provisional = build_owner_bound_rejoin_paper(
            bridge=bridge, initial_receipts=initial_receipts,
        )
        if type(provisional) is not OwnerBoundRejoinPaperEvidence:
            raise RejoinCompositeHold("original reJOIN verifier unavailable")
        resident = bridge.cognitive_work
        with resident.lock:
            originals = _initials(initial_receipts)
            before = _owner_snapshot(bridge, originals)
            if provisional.self_id != "A" or historical_composite.self_id != "A":
                raise RejoinCompositeHold("only the rejoined original A is qualified")
            native = read_rejoined_native_revision(bridge=bridge, self_id="A")
            b_native = read_continuing_b_native_revision(
                bridge=bridge, initial_receipt=originals["B"],
            )
            if type(native) is not NativeRevision or type(b_native) is not NativeRevision:
                raise RejoinCompositeHold("new Native revision unavailable")
            # No stale caller-provided evidence may substitute for this call.
            verified = build_owner_bound_rejoin_paper(
                bridge=bridge, initial_receipts=initial_receipts,
            )
            if (provisional != verified or verified.native_revision != native.native_revision
                    or verified.b_native_revision != b_native.native_revision):
                raise RejoinCompositeHold("reJOIN source changed across verification")
            world, owner_a, owner_b, _, _, scope_a, scope_b, login_a, login_b, (
                probe_a
            ), probe_b, logout, prior_scope, _, paper, process, _, _ = before
            if (native.self_id != "A" or native.owner_identity != str(owner_a.files.self_root)
                    or (native.world_id, native.branch_id, native.world_epoch,
                        native.resident_epoch, native.native_session_id)
                    != (world.world_id, world.branch_id, world.epoch,
                        scope_a[0], scope_a[1])
                    or native.native_request_id != login_a.observation_ref
                    or native.native_request_id != probe_a.request_id
                    or native.native_sequence != probe_a.seq
                    or bridge.sessions["A"]._decoder.next_seq != probe_a.seq + 1
                    or bridge.sessions["B"]._decoder.next_seq != b_native.native_sequence + 1
                    or native.native_source_ref != probe_a.provenance.reference
                    or native.native_world_time != owner_a.last_observed_tick
                    or native.native_revision != _revision({
                        key: value for key, value in asdict(native).items()
                        if key != "native_revision"
                    })
                    or scope_a[0] != prior_scope[0] + 2
                    or scope_b != (originals["B"].resident_epoch,
                                   originals["B"].native_session_id,
                                   originals["B"].world_epoch)
                    or login_b.observation_ref != probe_b.request_id
                    or old_session_active(bridge, originals["A"].native_session_id)
                    or logout.source_ref != verified.old_logout_source_ref
                    or prior_scope[0] != verified.old_resident_epoch):
                raise RejoinCompositeHold("current Native scope or retired history invalid")

            # Read owned Paper bytes a third time under the lock, and require
            # the original verifier's exact stream hash, not a free-standing SHA.
            log = paper.read_owned_log(world.paper_session_id)
            if (hashlib.sha256(log).hexdigest() != verified.paper_log_sha256
                    or paper._assert_owned() is not process
                    or process.pid != verified.paper_pid):
                raise RejoinCompositeHold("owned Paper log/process changed")
            old_ref = _historical_composite(historical_composite, originals["A"], log)
            if historical_composite.paper_tick >= verified.paper_tick:
                raise RejoinCompositeHold("Paper tick has no post-logout progression")
            paper_data = dict(
                paper_session_id=verified.paper_session_id,
                paper_boot_id=verified.paper_boot_id,
                paper_pid=verified.paper_pid,
                paper_actor_uuid=verified.paper_actor_uuid,
                paper_tick=verified.paper_tick,
                paper_tick_ref=verified.paper_tick_ref,
                paper_log_sha256=verified.paper_log_sha256,
            )
            paper_revision = _revision(paper_data)
            rejoin_revision = _revision(asdict(verified))
            b_continuity = _revision(dict(
                self_id="B", owner_identity=str(owner_b.files.self_root),
                resident_epoch=scope_b[0], native_session_id=scope_b[1],
                native_request_id=b_native.native_request_id,
                native_sequence=b_native.native_sequence,
                native_source_ref=b_native.native_source_ref,
                native_world_time=b_native.native_world_time,
                native_revision=b_native.native_revision,
                historical_initial_ref=_revision(asdict(originals["B"])),
                paper_actor_uuid=originals["B"].paper_actor_uuid,
                paper_present_line=verified.paper_evidence.b_present_line,
                paper_log_sha256=verified.paper_log_sha256,
            ))
            initial_ref = verified.historical_initial_ref
            composite_revision = _revision(dict(
                native_revision=native.native_revision,
                paper_revision=paper_revision,
                initial_receipt_ref=initial_ref,
                historical_composite_ref=old_ref,
                old_resident_epoch=verified.old_resident_epoch,
                old_native_session_id=verified.old_native_session_id,
                old_logout_source_ref=verified.old_logout_source_ref,
                rejoin_paper_revision=rejoin_revision,
                b_continuity_revision=b_continuity,
            ))
            after = _owner_snapshot(bridge, originals)
            if (any(after[i] is not before[i] for i in (
                    1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17))
                    or any(after[i] != before[i] for i in (0, 5, 6, 12, 13))
                    or read_rejoined_native_revision(bridge=bridge, self_id="A") != native
                    or read_continuing_b_native_revision(
                        bridge=bridge, initial_receipt=originals["B"],
                    ) != b_native
                    or paper.read_owned_log(world.paper_session_id) != log
                    or paper._assert_owned() is not process
                    or process.pid != verified.paper_pid):
                raise RejoinCompositeHold("Owner/Native/Paper changed before return")
            return RejoinedCompositeSourceReceipt(
                self_id="A", owner_identity=native.owner_identity,
                world_id=world.world_id, branch_id=world.branch_id,
                world_epoch=world.epoch, resident_epoch=native.resident_epoch,
                native_session_id=native.native_session_id,
                native_request_id=native.native_request_id,
                native_sequence=native.native_sequence,
                native_source_ref=native.native_source_ref,
                native_world_time=native.native_world_time,
                native_revision=native.native_revision,
                **paper_data, paper_revision=paper_revision,
                composite_revision=composite_revision,
                initial_receipt_ref=initial_ref,
                old_resident_epoch=verified.old_resident_epoch,
                old_native_session_id=verified.old_native_session_id,
                old_logout_source_ref=verified.old_logout_source_ref,
                historical_composite_ref=old_ref,
                rejoin_paper_revision=rejoin_revision,
                b_continuity_revision=b_continuity,
                paper_quit_line=verified.paper_evidence.a_quit_line,
                paper_rejoin_line=verified.paper_evidence.a_join_line,
                paper_present_line=verified.paper_evidence.a_present_line,
                b_present_line=verified.paper_evidence.b_present_line,
            )
    except RejoinCompositeHold:
        raise
    except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise RejoinCompositeHold("current reJOIN composite source unavailable") from exc


def old_session_active(bridge: OwnedResidentPhysicalBridge, old_session: str) -> bool:
    """Retired session must be forbidden, absent from all active issuer scopes."""
    return (old_session not in bridge.forbidden_native_sessions
            or any(s.started.session_id == old_session for s in bridge.sessions.values())
            or old_session in bridge.physical.current_native_sessions.values())
