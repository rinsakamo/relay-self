"""#904 resident MOVE: one original selected Action → fsynced WAL → native pulse.

No new Goal/Intent/Skill policy, target solver, navigation trajectory or sender.
The already-selected PhysicalActionPort proposal is the only Action parent.
A valid STOP is an exact child of the original parent MOVE, and is allowed
by the original issuer even when that Self has become QUARANTINED.
Native outcome is NOT independent Paper Action causation or Skill success.
"""
from __future__ import annotations

import asyncio
import math
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_source_window,
    finish_physical_issue_dev,
    mark_ambiguous_physical_dev,
)
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalActionProposalReceipt
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class PhysicalMoveRefusal(ValueError):
    """Original MOVE native child or source-qualified settled readback missing."""


@dataclass(frozen=True, slots=True)
class ResidentMoveDevReceipt:
    terminal: ActionLifecycle
    start_ack: MineflayerEffectResult
    stop_ack: MineflayerEffectResult
    initial_stop_probe: MineflayerObservation
    first_stable_probe: MineflayerObservation
    settled_probe: MineflayerObservation
    displacement_m: float
    journal_sha256: str
    # EVERY native STOP verification probe, including intermediate drift
    # samples, not only the three probes used for terminal admission.
    all_stop_probes: tuple[MineflayerObservation, ...] = ()
    skill_success_attested: bool = False
    paper_causal_attribution: bool = False
    native_start_dispatch_monotonic_ns: int = 0


async def _native(
    session: MineflayerProcessSession, *,
    session_id: str, after_seq: int,
    action_id: str | None, effect: str | None,
    request_id: str | None, timeout_s: float,
) -> MineflayerEffectResult | MineflayerObservation:
    """Source-strict command ACK/probe; passive move events do not grant IO."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    for _ in range(512):
        left = deadline - loop.time()
        if left <= 0:
            break
        try:
            entry = await asyncio.wait_for(session.receive(), timeout=left)
        except (TimeoutError, EOFError, OSError) as exc:
            raise PhysicalMoveRefusal("MOVE native readback timeout/disconnect") from exc
        if (
            entry.session_id != session_id
            or isinstance(
                entry, (
                    MineflayerConnectionEnd, MineflayerAdapterErrorMessage,
                    MineflayerCommandError,
                ),
            )
        ):
            raise PhysicalMoveRefusal("MOVE wrong/ended native source")
        if isinstance(entry, MineflayerEffectResult):
            if (
                action_id is not None and entry.seq > after_seq
                and entry.action_id == action_id and entry.effect == effect
                and entry.result == "applied"
            ):
                return entry
            raise PhysicalMoveRefusal("MOVE unexpected/failed native child ACK")
        if isinstance(entry, MineflayerObservation) and entry.kind == "probe":
            if (
                request_id is not None and entry.seq > after_seq
                and entry.request_id == request_id
                and entry.snapshot.time is not None
                and entry.snapshot.health > 0
            ):
                return entry
            raise PhysicalMoveRefusal("MOVE uncorrelated native probe")
        # Passive movement/health/time/inventory observations may interleave.
    raise PhysicalMoveRefusal("MOVE source horizon exhausted")


def _tick(observation: MineflayerObservation) -> int:
    time = observation.snapshot.time
    if time is None:
        raise PhysicalMoveRefusal("MOVE World clock unavailable")
    # Server world age advances independently of doDaylightCycle; daylight
    # time can stay frozen while physics ticks continue. Legacy source samples
    # have no age and keep their original (less strong) interpretation.
    if time.world_age_ticks is not None:
        return time.world_age_ticks
    return time.day * 24000 + time.time_of_day


async def _probe(
    session: MineflayerProcessSession, *,
    native: str, after_seq: int, timeout_s: float,
) -> MineflayerObservation:
    req = "p0d-move-stop-" + uuid.uuid4().hex
    await session.send_observe(req)
    item = await _native(
        session, session_id=native, after_seq=after_seq,
        action_id=None, effect=None, request_id=req, timeout_s=timeout_s,
    )
    assert isinstance(item, MineflayerObservation)
    return item


async def _settled(
    session: MineflayerProcessSession, *,
    native: str, stop_seq: int, timeout_s: float,
    max_probe_requests: int | None = None,
) -> tuple[
    MineflayerObservation,
    MineflayerObservation,
    MineflayerObservation,
    tuple[MineflayerObservation, ...],
]:
    """First eight World ticks of settling, then eight stable World ticks.

    A drifting body shifts only its reference, never commits without a
    stable 8-tick window. This STOP tolerance is not a target accuracy.
    """
    if max_probe_requests is not None and (
        type(max_probe_requests) is not int or not 3 <= max_probe_requests <= 4096
    ):
        raise PhysicalMoveRefusal("invalid bounded STOP probe request limit")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    initial = await _probe(
        session, native=native, after_seq=stop_seq, timeout_s=timeout_s,
    )
    first = initial
    last = initial
    all_probes = [initial]
    reached_first = False
    assert initial.snapshot.time is not None
    using_world_age = initial.snapshot.time.world_age_ticks is not None
    # A bounded Q4 reservation may have only 24 probes. Mineflayer time/age
    # arrives on server update_time packets, not every observe request;
    # pacing avoids spending the entire reservation between clock updates.
    # The same deadline, 8+8 ticks and 0.06m stability remain mandatory.
    probe_interval_s = 0.15 if max_probe_requests is not None else 0.05
    while loop.time() < deadline:
        if max_probe_requests is not None and len(all_probes) >= max_probe_requests:
            raise PhysicalMoveRefusal("MOVE STOP probe reservation exhausted")
        await asyncio.sleep(probe_interval_s)
        later = await _probe(
            session, native=native, after_seq=last.seq,
            timeout_s=max(0.001, deadline - loop.time()),
        )
        last = later
        all_probes.append(later)
        if (later.snapshot.time is None
                or (later.snapshot.time.world_age_ticks is not None)
                != using_world_age):
            raise PhysicalMoveRefusal("MOVE STOP World clock source changed")
        if _tick(later) < _tick(initial) or _tick(later) - _tick(initial) > 200:
            raise PhysicalMoveRefusal("MOVE STOP World clock regression/horizon")
        if not reached_first:
            if _tick(later) - _tick(initial) >= 8:
                first = later
                reached_first = True
            continue
        if _tick(later) - _tick(first) < 8:
            continue
        a, b = first.snapshot.position, later.snapshot.position
        movement = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
        if math.isfinite(movement) and movement <= 0.06:
            return (initial, first, later, tuple(all_probes))
        first = later
    raise PhysicalMoveRefusal("MOVE STOP not stable after 8+8 World ticks")


async def issue_selected_move_dev(
    session: MineflayerProcessSession,
    *, proposal: PhysicalActionProposalReceipt,
    previous_probe: MineflayerObservation,
    current_probe: MineflayerObservation,
    propose_grant: PhysicalDevGrant,
    issue_grant: PhysicalDevGrant,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    journal: PhysicalActionJournal,
    at_ns: int,
    provenance: Provenance,
    grant_real_world: bool,
    acknowledge_dev_unverified_principal: bool,
    evidence_timeout_s: float = 15.0,
    pulse_seconds: float = 0.35,
    bind_native_children: Callable[[str], None] | None = None,
) -> ResidentMoveDevReceipt:
    """One finite Self-selected relative MOVE, no automatic retry on unknown.

    The original PhysicalIssueAdmission.issue_move wrapper MUST own the final
    native effect admission; this callable does not create its own grant.
    """
    if (
        type(pulse_seconds) not in (int, float)
        or not math.isfinite(pulse_seconds) or not 0.15 <= pulse_seconds <= 0.75
    ):
        raise PhysicalMoveRefusal("bounded native MOVE pulse duration required")
    check_dev_issuer_preflight(
        session, proposal, intent_owner=intent_owner,
        skill_execution=skill_execution, supervisor=supervisor, journal=journal,
        at_ns=at_ns, provenance=provenance, grant_real_world=grant_real_world,
        acknowledge_dev_unverified_principal=acknowledge_dev_unverified_principal,
        evidence_timeout_s=evidence_timeout_s, refusal=PhysicalMoveRefusal,
    )
    check_physical_source_window(
        proposal, previous_probe, current_probe,
        capability="MOVE", target_kind="RELATIVE", refusal=PhysicalMoveRefusal,
    )
    binding = proposal.binding
    control = binding.target_ref.removeprefix("relative:")
    if (
        binding.target_ref not in {
            "relative:forward", "relative:back",
            "relative:left", "relative:right",
        }
        or current_probe.snapshot.time is None  # technical STOP evidence clock
    ):
        raise PhysicalMoveRefusal("selected MOVE direction/body no longer available")
    begin_physical_issue_dev(
        session, capability="MOVE", proposal=proposal,
        current_probe=current_probe, propose_grant=propose_grant,
        issue_grant=issue_grant, intent_owner=intent_owner,
        skill_execution=skill_execution, supervisor=supervisor,
        journal=journal, at_ns=at_ns, refusal=PhysicalMoveRefusal,
    )
    parent = binding.action_id
    start_id, stop_id = parent + "-start", parent + "-stop"
    attempted_stop = False
    try:
        # The canonical fsynced PREPARED exists; now final-stdin child binding.
        if bind_native_children is None:
            raise PhysicalMoveRefusal("original MOVE issuer child binding absent")
        bind_native_children(parent)
        native_start_dispatch_ns = time.monotonic_ns()
        await session.send_set_control(start_id, control=control, state=True)
        start = await _native(
            session, session_id=current_probe.session_id,
            after_seq=current_probe.seq,
            action_id=start_id, effect="set_control", request_id=None,
            timeout_s=evidence_timeout_s,
        )
        assert isinstance(start, MineflayerEffectResult)
        await asyncio.sleep(pulse_seconds)
        attempted_stop = True
        await session.send_clear_controls(stop_id)
        stop = await _native(
            session, session_id=current_probe.session_id,
            after_seq=start.seq,
            action_id=stop_id, effect="clear_controls", request_id=None,
            timeout_s=evidence_timeout_s,
        )
        assert isinstance(stop, MineflayerEffectResult)
        initial, first, settled, all_stop_probes = await _settled(
            session, native=current_probe.session_id,
            stop_seq=stop.seq, timeout_s=evidence_timeout_s,
        )
        terminal = finish_physical_issue_dev(
            action_id=parent, after=settled, supervisor=supervisor,
            journal=journal, at_ns=at_ns,
            close=lambda t: journal.close_move(
                binding, current_probe, start, stop,
                initial, first, settled, t, supervisor,
            ),
        )
        before, after = current_probe.snapshot.position, settled.snapshot.position
        displacement = math.dist(
            (before.x, before.y, before.z),
            (after.x, after.y, after.z),
        )
        return ResidentMoveDevReceipt(
            terminal, start, stop, initial, first, settled,
            displacement, journal.digest, all_stop_probes,
            native_start_dispatch_monotonic_ns=native_start_dispatch_ns,
        )
    except BaseException:
        if not attempted_stop:
            # Exactly one best-effort safe STOP on uncertainty. A subsequent
            # failed/ambiguous STOP must NOT be retried. Its source remains
            # PREPARED_UNRESOLVED for operator reconciliation.
            try:
                await session.send_clear_controls(stop_id)
            except BaseException:
                pass
        try:
            mark_ambiguous_physical_dev(
                action_id=parent, supervisor=supervisor,
                probe=current_probe, at_ns=at_ns,
            )
        except BaseException:
            pass  # no fabricated terminal; canonical WAL remains unresolved
        raise
