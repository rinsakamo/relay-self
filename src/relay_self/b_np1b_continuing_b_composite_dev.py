"""B's continuing current composite after A's original logout/reJOIN.

This requalifies the original B session's latest adopted Native observation:
initial probe or a verified same-session update. It separately requires a new
post-A-reJOIN owned Paper PRESENT. B's initial receipt remains history.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from relay_self.b_np1b_current_composite_source_dev import CompositeSourceReceipt
from relay_self.b_np1b_fresh_native_update_dev import read_continuing_b_native_revision
from relay_self.b_np1b_initial_source_dev import InitialSourceReceipt, _revision
from relay_self.b_np1b_owner_bound_rejoin_dev import _initials, _owner_snapshot
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinedCompositeSourceReceipt,
    build_rejoined_composite_source,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.resident_paper_presence_join_dev import parse_owned_paper_resident_trace


class ContinuingCompositeHold(RuntimeError):
    """B's current independent Native/Paper presence cannot be qualified."""


@dataclass(frozen=True, slots=True)
class ContinuingCompositeSourceReceipt(CompositeSourceReceipt):
    """B identity and current Paper presence, bound to original A reJOIN proof."""

    owner_identity: str
    a_rejoin_composite_ref: str
    b_continuity_revision: str
    b_post_rejoin_present_line: int
    b_post_rejoin_present_tick: int


def build_continuing_b_composite_source(
    *, bridge: OwnedResidentPhysicalBridge,
    initial_receipts: tuple[InitialSourceReceipt, ...],
    historical_composite: CompositeSourceReceipt,
) -> ContinuingCompositeSourceReceipt:
    """Original-lock, read-only source. Requires an actual post-reJOIN B PRESENT.

    The original owner-bound A verifier must pass first. B uses its *current*
    Owner-adopted original or later same-session probe, never a detached
    caller-supplied revision. Paper and Native clocks remain independent.
    """
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise ContinuingCompositeHold("original Bridge and resident required")
    try:
        resident = bridge.cognitive_work
        with resident.lock:
            originals = _initials(initial_receipts)
            initial_b = originals["B"]
            a = build_rejoined_composite_source(
                bridge=bridge, initial_receipts=initial_receipts,
                historical_composite=historical_composite,
            )
            if type(a) is not RejoinedCompositeSourceReceipt:
                raise ContinuingCompositeHold("original A reJOIN not current")
            snap = _owner_snapshot(bridge, originals)
            b_native = read_continuing_b_native_revision(
                bridge=bridge, initial_receipt=initial_b,
            )
            world, _, owner_b, _, session_b, _, scope_b, _, login_b, _, probe_b, (
                _logout
            ), _, _, paper, process, _, _ = snap
            if (
                scope_b != (initial_b.resident_epoch, initial_b.native_session_id,
                            initial_b.world_epoch)
                or login_b.observation_ref != initial_b.native_request_id
                or login_b.observed_world_tick != initial_b.native_world_time
                or probe_b.session_id != initial_b.native_session_id
                or probe_b.request_id != initial_b.native_request_id
                or probe_b.seq != initial_b.native_sequence
                or probe_b.provenance.reference != initial_b.native_source_ref
                or b_native.native_session_id != scope_b[1]
                or b_native.native_sequence < probe_b.seq
                or session_b._decoder.next_seq != b_native.native_sequence + 1
                or owner_b.last_observed_tick != b_native.native_world_time
                or str(owner_b.files.self_root) != initial_b.owner_identity
                or initial_b.native_revision != _revision({
                    key: getattr(initial_b, key) for key in (
                        "self_id", "owner_identity", "resident_epoch", "world_id",
                        "branch_id", "world_epoch", "native_session_id",
                        "native_request_id", "native_sequence", "native_source_ref",
                        "native_world_time",
                    )
                })
            ):
                raise ContinuingCompositeHold("B Native was replaced or updated without proof")
            log = paper.read_owned_log(world.paper_session_id)
            if (hashlib.sha256(log).hexdigest() != a.paper_log_sha256
                    or paper._assert_owned() is not process
                    or process.pid != a.paper_pid):
                raise ContinuingCompositeHold("Paper changed after A reJOIN attestation")
            # A recent Paper ACK is the cut boundary for *both* Selves.
            # A growing log without a newer ACK must not silently promote B.
            match = re.fullmatch(
                r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
                a.paper_tick_ref,
            )
            if match is None or not log.splitlines():
                raise ContinuingCompositeHold("current Paper tick source absent")
            ack = (
                f"P0D_TICK_ACK nonce={match.group(2)} boot={match.group(1)} "
                f"session={a.paper_session_id} world={world.world_id} "
                f"tick={a.paper_tick} source=PAPER_MAIN_THREAD"
            ).encode()
            if ack not in log.splitlines()[-1]:
                raise ContinuingCompositeHold("Paper log grew after current main-thread ACK")
            trace = parse_owned_paper_resident_trace(
                owned_paper_session_id=world.paper_session_id,
                expected_world_uuid=world.world_id,
                owned_paper_log=log,
                log_ref="owned-paper-sha256:" + a.paper_log_sha256,
            )
            b_events = [e for e in trace.events if e.name == bridge.configs["B"].username]
            after_rejoin = [
                e for e in b_events
                if e.event in ("PRESENT", "MOVE") and e.line > a.paper_rejoin_line
                and e.tick <= a.paper_tick
            ]
            if (
                trace.boot_id != initial_b.presence_boot_id
                or not after_rejoin
                or any(e.actor_uuid != initial_b.paper_actor_uuid for e in b_events)
                or any(e.event == "QUIT" for e in b_events)
                or len([e for e in b_events if e.event == "JOIN"]) != 1
                or b_events[0].event != "JOIN"
                or after_rejoin[-1].line <= a.paper_rejoin_line
            ):
                raise ContinuingCompositeHold("no new owned B Paper PRESENT after A reJOIN")
            present_b = after_rejoin[-1]
            native_revision = b_native.native_revision
            paper_data = dict(
                paper_session_id=a.paper_session_id,
                paper_boot_id=a.paper_boot_id,
                paper_pid=a.paper_pid,
                paper_actor_uuid=initial_b.paper_actor_uuid,
                paper_tick=a.paper_tick,
                paper_tick_ref=a.paper_tick_ref,
                paper_log_sha256=a.paper_log_sha256,
            )
            paper_revision = _revision(paper_data)
            a_ref = _revision(asdict(a))
            initial_ref = _revision(asdict(initial_b))
            composite_revision = _revision(dict(
                native_revision=native_revision,
                paper_revision=paper_revision,
                initial_receipt_ref=initial_ref,
                a_rejoin_composite_ref=a_ref,
                b_continuity_revision=a.b_continuity_revision,
                b_post_rejoin_present_line=present_b.line,
                b_post_rejoin_present_tick=present_b.tick,
            ))
            # Fully requalify A and both owner scopes, then compare the original
            # owned bytes one more time within the same Resident lock.
            after = _owner_snapshot(bridge, originals)
            if (
                any(after[i] is not snap[i] for i in (
                    1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17,
                ))
                or any(after[i] != snap[i] for i in (0, 5, 6, 12, 13))
                or build_rejoined_composite_source(
                    bridge=bridge, initial_receipts=initial_receipts,
                    historical_composite=historical_composite,
                ) != a
                or paper.read_owned_log(world.paper_session_id) != log
                or paper._assert_owned() is not process
            ):
                raise ContinuingCompositeHold("original B/A sources changed during verification")
            return ContinuingCompositeSourceReceipt(
                self_id="B", owner_identity=initial_b.owner_identity,
                world_id=world.world_id, branch_id=world.branch_id,
                world_epoch=world.epoch, resident_epoch=scope_b[0],
                native_session_id=scope_b[1], native_request_id=b_native.native_request_id,
                native_sequence=b_native.native_sequence,
                native_source_ref=b_native.native_source_ref,
                native_world_time=b_native.native_world_time,
                native_revision=native_revision, **paper_data,
                paper_revision=paper_revision, composite_revision=composite_revision,
                initial_receipt_ref=initial_ref, a_rejoin_composite_ref=a_ref,
                b_continuity_revision=a.b_continuity_revision,
                b_post_rejoin_present_line=present_b.line,
                b_post_rejoin_present_tick=present_b.tick,
            )
    except ContinuingCompositeHold:
        raise
    except (ValueError, RuntimeError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise ContinuingCompositeHold("B continuing current composite unavailable") from exc
