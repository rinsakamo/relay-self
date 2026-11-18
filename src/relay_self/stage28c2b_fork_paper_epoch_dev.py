"""Stage28c2b: bound *new Paper process* clock distinct from saved W221.

Old typed owner cuts and saved World tick are archive-local. The next Paper
main-thread tick starts in another boot, and must never be compared to W221
or synthetically offset to look continuous. This gate observes a real owned
Paper process and its original tick ACK/log reader; no native issue or L1.
"""
from __future__ import annotations

import re

from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.stage28_cognitive_recovery_gate_dev import Stage28ForkPaperEpoch
from relay_self.stage28c2b_execution_copy_dev import ExecutionCopy
from relay_self.world_resident_lifecycle_dev import WorldLifetime


class Stage28ForkEpochHold(RuntimeError):
    """New Paper process source is not linked to this verified restored fork."""


_TICK_SOURCE = re.compile(
    r"^paper-main-thread:p0d:([0-9a-zA-Z-]+):"
    r"([0-9a-zA-Z-]+):sha256:([a-f0-9]{64})$"
)


def observe_new_fork_paper_epoch(
    prepared: ExecutionCopy, paper: OwnedPaperWorld, *,
    historical_native_sessions: tuple[str, ...],
    new_world_epoch: int = 1,
) -> tuple[WorldLifetime, Stage28ForkPaperEpoch]:
    """Call *after* a fresh owned Paper boot, *before* first native JOIN.

    Tick reader has to obtain and correlate the main-thread nonce ACK with
    this Paper Popen's log. This function checks the original log again.
    Supplying a forged dataclass without a real readback is not real attestation.
    """
    if not isinstance(prepared, ExecutionCopy) or not isinstance(paper, OwnedPaperWorld):
        raise Stage28ForkEpochHold("actual original execution copy and Paper owner required")
    if type(new_world_epoch) is not int or new_world_epoch < 1:
        raise Stage28ForkEpochHold("fresh World process epoch required")
    plan = prepared.recovered.plan
    source = prepared.recovered.receipt
    physical = prepared.recovered.physical
    if (
        tuple(sorted(prepared.recovered.owners)) != ("A", "B")
        or not physical.observation_only or not physical.all_residents_offline
        or plan.roster != ("A", "B")
        or source.generation_id != plan.generation_id
        or source.source_world_id != plan.source_world_id
        or source.fork_branch_id != plan.fork_branch_id
        or paper.world_id != plan.source_world_id
        or paper.branch_id != plan.fork_branch_id
        or paper.world_dir != (prepared.directory / "world").resolve()
        or paper.server_dir != prepared.directory.resolve()
        or type(historical_native_sessions) is not tuple
        or len(historical_native_sessions) < len(plan.roster)
        or any(type(s) is not str or not s for s in historical_native_sessions)
        or len(set(historical_native_sessions)) != len(historical_native_sessions)
        or not set(dict(plan.old_native_sessions).values()).issubset(
            historical_native_sessions
        )
    ):
        raise Stage28ForkEpochHold("source, fork, owner or native history incomplete")
    session = paper.owned_session_id
    if type(session) is not str or not session.startswith("paper-owned-"):
        raise Stage28ForkEpochHold("Paper not started from new owned process")
    try:
        # Checks the actual owned Popen and its matching stdout, rather
        # than a foreign disk log or an arbitrary claimed tick.
        tick = paper.tick_readback(session)
        raw_log = paper.read_owned_log(session)
        proc = paper._assert_owned()
    except (OSError, ValueError, RuntimeError) as exc:
        raise Stage28ForkEpochHold("owned Paper main-thread tick unavailable") from exc
    if (
        not isinstance(tick, PaperTickReceipt)
        or tick.server_session_id != session
        or type(tick.tick) is not int or tick.tick < 0
        or type(tick.source_ref) is not str
    ):
        raise Stage28ForkEpochHold("foreign or invalid Paper boot-local tick receipt")
    match = _TICK_SOURCE.fullmatch(tick.source_ref)
    if match is None:
        raise Stage28ForkEpochHold("Paper tick witness does not identify boot and nonce")
    boot, nonce, _ = match.groups()
    marker = (
        f"P0D_TICK_ACK nonce={nonce} boot={boot} session={session} "
        f"world={paper.world_id} tick={tick.tick} source=PAPER_MAIN_THREAD"
    )
    ready = f"P0D_TICK_READY boot={boot} source=PAPER_MAIN_THREAD"
    lines = raw_log.decode("utf-8", errors="replace").splitlines()
    if (
        not isinstance(proc.pid, int) or proc.pid <= 0
        or not any(ready in line for line in lines)
        or not any(marker in line for line in lines)
        or next((i for i, s in enumerate(lines) if ready in s), len(lines))
        >= max((i for i, s in enumerate(lines) if marker in s), default=-1)
    ):
        raise Stage28ForkEpochHold("Paper tick ACK not witnessed by its owned process")
    world = WorldLifetime(
        plan.source_world_id, plan.fork_branch_id, session,
        new_world_epoch, tick.tick,
    )
    evidence = Stage28ForkPaperEpoch(
        plan.generation_id, plan.source_world_id, plan.source_branch_id,
        plan.declared_world_tick, plan.fork_branch_id,
        source.source_committed_sha256,
        session, boot, new_world_epoch, tick.tick, tick.source_ref,
        proc.pid, tuple(sorted(historical_native_sessions)),
    )
    return world, evidence
