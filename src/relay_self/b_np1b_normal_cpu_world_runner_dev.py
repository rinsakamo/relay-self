"""Source-bound original A/B CPU Present integration for the owned World runner.

DEV-only opt-in. All Native observations must enter through the original
Bridge/Owner and current Paper bytes through the original owned process.
No new Owner, physical issue, GPU, fictional restored source, or L1 run.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from relay_self.b_np1b_current_composite_source_dev import (
    CompositeSourceReceipt,
    build_current_composite_source,
)
from relay_self.b_np1b_fresh_native_update_dev import (
    NativeRevision,
    update_fresh_native,
)
from relay_self.b_np1b_initial_source_dev import (
    InitialSourceReceipt,
    build_initial_source_receipts,
)
from relay_self.b_np1b_normal_present_scheduler_dev import (
    NormalCpuScheduleHold,
    NormalResidentPresentCpuScheduler,
    ScheduledPresentCpu,
)
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinedCompositeSourceReceipt,
    build_rejoined_composite_source,
)
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.world_resident_lifecycle_dev import Presence


class OriginalNormalCpuWorldHold(RuntimeError):
    """Original owned World/Native/Paper CPU path is not source-qualified."""


@dataclass(frozen=True, slots=True)
class NormalCpuOriginalHistory:
    initial: tuple[InitialSourceReceipt, ...]
    a_native_after_initial: NativeRevision
    a_historical_composite: CompositeSourceReceipt


@dataclass(frozen=True, slots=True)
class NormalCpuWorldReadback:
    first_a: ScheduledPresentCpu
    first_b: ScheduledPresentCpu
    later_a: ScheduledPresentCpu
    later_b: ScheduledPresentCpu
    updated_b_native: NativeRevision


def capture_original_initial_cpu_sources(
    *, bridge: OwnedResidentPhysicalBridge,
) -> tuple[InitialSourceReceipt, ...]:
    """Read the original A/B Paper ACK while both original Native probes are adopted."""
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise OriginalNormalCpuWorldHold("original cognitive Bridge required")
    try:
        with bridge.cognitive_work.lock:
            session = bridge.lifecycle.world.paper_session_id
            tick = bridge.paper.tick_readback(session)
            receipts = build_initial_source_receipts(bridge=bridge, tick=tick)
            if (
                type(receipts) is not tuple or len(receipts) != 2
                or any(type(r) is not InitialSourceReceipt for r in receipts)
                or tuple(r.self_id for r in receipts) != ("A", "B")
            ):
                raise OriginalNormalCpuWorldHold("original initial A/B receipts unavailable")
            return receipts
    except OriginalNormalCpuWorldHold:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise OriginalNormalCpuWorldHold("original initial Native/Paper not qualified") from exc


async def capture_original_historical_cpu_source(
    *, bridge: OwnedResidentPhysicalBridge,
    initial_receipts: tuple[InitialSourceReceipt, ...],
) -> NormalCpuOriginalHistory:
    """After an independently later Paper heartbeat, adopt new A Native and Paper.

    Call ONLY before the first original A logout. The original Native receiver
    must not be simultaneously consumed by another caller.
    """
    try:
        if (
            type(initial_receipts) is not tuple or len(initial_receipts) != 2
            or tuple(r.self_id for r in initial_receipts) != ("A", "B")
        ):
            raise OriginalNormalCpuWorldHold("original initial A/B order invalid")
        new_a = await update_fresh_native(
            bridge=bridge, self_id="A", initial_receipt=initial_receipts[0],
        )
        history = build_current_composite_source(
            bridge=bridge, self_id="A", native_revision=new_a,
            initial_receipts=initial_receipts,
        )
        if (
            type(history) is not CompositeSourceReceipt
            or history.native_revision != new_a.native_revision
            or history.native_session_id != initial_receipts[0].native_session_id
            or history.paper_tick <= initial_receipts[0].paper_tick
        ):
            raise OriginalNormalCpuWorldHold("new historical A Composite invalid")
        return NormalCpuOriginalHistory(initial_receipts, new_a, history)
    except OriginalNormalCpuWorldHold:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise OriginalNormalCpuWorldHold("original historical A Composite unavailable") from exc


async def update_original_b_after_a_logout(
    *, bridge: OwnedResidentPhysicalBridge,
    history: NormalCpuOriginalHistory,
) -> NativeRevision:
    """Adopt B's actual uninterrupted Native probe after A original logout."""
    if type(history) is not NormalCpuOriginalHistory:
        raise OriginalNormalCpuWorldHold("original immutable history missing")
    if not isinstance(bridge, OwnedResidentPhysicalBridge) or bridge.cognitive_work is None:
        raise OriginalNormalCpuWorldHold("original resident unavailable")
    try:
        with bridge.cognitive_work.lock:
            retired = bridge._b_np1b_retired_login.get("A")
            if (
                bridge.lifecycle.view("A").status is not Presence.OFFLINE
                or bridge.lifecycle.view("B").status is not Presence.ONLINE
                or "A" in bridge.sessions
                or "A" in bridge.last_login_evidence
                or type(retired) is not tuple or len(retired) != 5
                or retired[0].native_session_id != history.initial[0].native_session_id
                or retired[1] != (
                    history.initial[0].resident_epoch,
                    history.initial[0].native_session_id,
                    history.initial[0].world_epoch,
                )
                or "A" in getattr(bridge, "_fresh_native_pending", {})
                or bridge.physical.active_action_ids
            ):
                raise OriginalNormalCpuWorldHold(
                    "B continuation must follow original verified A logout"
                )
        b = await update_fresh_native(
            bridge=bridge, self_id="B", initial_receipt=history.initial[1],
        )
        with bridge.cognitive_work.lock:
            if (
                bridge.lifecycle.view("A").status is not Presence.OFFLINE
                or bridge.lifecycle.view("B").status is not Presence.ONLINE
                or bridge._b_np1b_retired_login.get("A") != retired
                or b.native_session_id != history.initial[1].native_session_id
                or b.native_revision == history.initial[1].native_revision
                or b.native_sequence <= history.initial[1].native_sequence
            ):
                raise OriginalNormalCpuWorldHold(
                    "B Native advanced outside original A logout window"
                )
        return b
    except OriginalNormalCpuWorldHold:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise OriginalNormalCpuWorldHold("B continuous Native after A logout unqualified") from exc


def start_original_normal_cpu_runtime(
    *, bridge: OwnedResidentPhysicalBridge,
    history: NormalCpuOriginalHistory,
    interval_s: float = 0.05,
) -> NormalResidentPresentCpuScheduler:
    """Start on the existing World runner after the *verified first* A reJOIN.

    No implied second/further reJOIN qualification. Source history is bound
    once; tasks are registered with the original per-Self Owner.
    """
    if type(history) is not NormalCpuOriginalHistory:
        raise OriginalNormalCpuWorldHold("historical source is not typed")
    if type(interval_s) not in (int, float) or not 0.01 <= interval_s <= 30.0:
        raise OriginalNormalCpuWorldHold("bounded original CPU poll interval required")
    try:
        asyncio.get_running_loop()
        qualified = build_rejoined_composite_source(
            bridge=bridge, initial_receipts=history.initial,
            historical_composite=history.a_historical_composite,
        )
        if (
            type(qualified) is not RejoinedCompositeSourceReceipt
            or qualified.old_native_session_id != history.initial[0].native_session_id
            or qualified.native_session_id == history.initial[0].native_session_id
        ):
            raise OriginalNormalCpuWorldHold("original A reJOIN source unavailable")
        bridge.bind_normal_rejoin_present_cpu(
            initial_receipts=history.initial,
            historical_composite=history.a_historical_composite,
        )
        return bridge.start_normal_present_cpu_schedule(interval_s=interval_s)
    except OriginalNormalCpuWorldHold:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        raise OriginalNormalCpuWorldHold("original CPU scheduler source not current") from exc


async def read_original_normal_cpu_pair(
    *, bridge: OwnedResidentPhysicalBridge, timeout_s: float,
    not_pair_revision: str | None = None,
    after_a: int = 0, after_b: int = 0,
) -> tuple[ScheduledPresentCpu, ScheduledPresentCpu]:
    """Bounded wait for BOTH separately scheduled tasks and one common current cut.

    No sleep-based claim of simultaneity: each returned source is requalified
    by the original Bridge immediately before this readout is accepted.
    """
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise OriginalNormalCpuWorldHold("bounded CPU read deadline required")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        try:
            with bridge.cognitive_work.lock:
                a = bridge.require_scheduled_present_cpu("A")
                b = bridge.require_scheduled_present_cpu("B")
                if (
                    a.poll == b.poll
                    and a.source_pair_revision == b.source_pair_revision
                    and a.iteration > after_a and b.iteration > after_b
                    and (not_pair_revision is None
                         or a.source_pair_revision != not_pair_revision)
                ):
                    return a, b
        except (NormalCpuScheduleHold, RuntimeError, ValueError, TypeError, AttributeError):
            pass
        await asyncio.sleep(0.02)
    raise OriginalNormalCpuWorldHold("no jointly current original A/B CPU Present before deadline")


async def exercise_original_normal_cpu_runtime(
    *, bridge: OwnedResidentPhysicalBridge,
    history: NormalCpuOriginalHistory,
    interval_s: float = 0.05,
    timeout_s: float = 3.0,
) -> NormalCpuWorldReadback:
    """Real runner opt-in: two periodic pair reads across an actual B Native update.

    Owns the scheduler's local stop on every exit. Original Bridge logout
    remains the only retirement authority, controlled by the parent runner.
    """
    scheduler = start_original_normal_cpu_runtime(
        bridge=bridge, history=history, interval_s=interval_s,
    )
    try:
        a, b = await read_original_normal_cpu_pair(
            bridge=bridge, timeout_s=timeout_s,
        )
        native = await update_fresh_native(
            bridge=bridge, self_id="B", initial_receipt=history.initial[1],
        )
        later_a, later_b = await read_original_normal_cpu_pair(
            bridge=bridge, timeout_s=timeout_s,
            not_pair_revision=a.source_pair_revision,
            after_a=a.iteration, after_b=b.iteration,
        )
        if (
            later_b.poll.b_present.source.composite_receipt.native_revision
            != native.native_revision
            or later_a.poll.a_present.source.composite_receipt.native_session_id
            != a.poll.a_present.source.composite_receipt.native_session_id
            or later_b.poll.b_present.source.composite_receipt.native_session_id
            != history.initial[1].native_session_id
        ):
            raise OriginalNormalCpuWorldHold("B Native update did not reach A/B CPU Present")
        return NormalCpuWorldReadback(a, b, later_a, later_b, native)
    finally:
        await scheduler.stop()
