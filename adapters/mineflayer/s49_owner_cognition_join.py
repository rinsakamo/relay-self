"""S #537: bounded, read-only post-S49 cognition source join (DEV).

Consumes an already completed original S49 batch; no World, Action, model,
ledger, learning or authority operations. Missing owner data remains UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adapters.mineflayer.s49_completed_decision_bridge import (
    S49OriginalCompletedBatch,
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)

Status = Literal["DISABLED", "RECORDED", "DEFERRED"]
NOT_SUPPLIED = "NOT_SUPPLIED"


@dataclass(frozen=True, slots=True)
class S49CognitionJoinedReadout:
    status: Status
    reason: str
    session_id: str | None = None
    decisions: tuple[tuple[int, int, str, str | None], ...] = ()
    m_status: str = NOT_SUPPLIED
    wb_status: str = NOT_SUPPLIED
    wb_source_probe_seq: int | None = None
    source_attested: bool = False
    action_authority: bool = False
    model_usage: str = "UNKNOWN_NOT_METERED"
    s42_owner: str = NOT_SUPPLIED
    b0_owner: str = NOT_SUPPLIED
    l8_owner: str = NOT_SUPPLIED
    new_native_reads: int = 0
    new_model_calls: int = 0
    new_action_issues: int = 0
    learning_updates: int = 0
    energy_debits: int = 0


def _original(batch: object) -> tuple[S49OriginalCompletedBatch, dict[str, object]]:
    if not isinstance(batch, S49OriginalCompletedBatch):
        raise ValueError("original S49 postowner batch required")
    sources = batch.steps
    if type(sources) is not tuple or not 1 <= len(sources) <= 8:
        raise ValueError("bounded original S49 steps required")
    steps = tuple(s.step for s in sources)
    probes = {s.probe.seq: s.probe for s in sources}
    receipts = {
        s.step.action_request_id: s.action_receipt
        for s in sources if s.action_receipt is not None
    }
    if len(probes) != len(sources) or len(receipts) != sum(
        s.action_receipt is not None for s in sources
    ):
        raise ValueError("duplicate original probe or Action")
    validated = read_original_s49_completions(steps, probes, receipts)
    if (
        validated.session_id != batch.session_id
        or any(
            a.step is not b.step
            or a.probe is not b.probe
            or a.action_receipt is not b.action_receipt
            for a, b in zip(validated.steps, sources)
        )
    ):
        raise ValueError("original Python object references changed")
    return batch, bounded_original_s49_completion_row(batch)


def _m_status(batch: S49OriginalCompletedBatch, supplied: object) -> str:
    # Never vendor or simulate the M owner. Import only if it is installed in
    # this SAME process, and re-check the original typed admission.
    from experiments.metabolism_s49_owner_admission import (
        S49MAdmissionReadout,
        admit_original_s49_batch,
    )

    if (
        not isinstance(supplied, S49MAdmissionReadout)
        or supplied.status != "RECORDED"
        or supplied.reason != "s49_original_completed_only"
        or supplied.source_attested or supplied.action_authority
        or supplied.admission is None
        or supplied.admission.kind != "ORIGINAL_PYTHON_BATCH"
        or supplied.admission != admit_original_s49_batch(batch)
    ):
        raise ValueError("M admission must match original typed S49 batch")
    return "ORIGINAL_PYTHON_BATCH_RECORDED"


def _wb_status(
    batch: S49OriginalCompletedBatch, supplied: object,
) -> tuple[str, int]:
    from relay_self.wb_l2_read_port import WBL2UncertaintyRead

    if not isinstance(supplied, WBL2UncertaintyRead):
        raise ValueError("typed WB port required")
    native_seq = supplied.source_world_seq
    last = supplied.latest_world_seq
    if (
        supplied.source_attested
        or supplied.authority != "READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT"
        or supplied.origin != "L2_GENERATED_UNCERTAINTY_NOT_WORLD_FACT"
        or supplied.session_id != batch.session_id
        or type(native_seq) is not int
        or native_seq not in {s.probe.seq for s in batch.steps}
        or type(last) is not int
        or last != batch.steps[-1].probe.seq
        or not isinstance(supplied.source_ref, str)
        or not supplied.source_ref.startswith(
            f"present:{batch.session_id}:{native_seq}:"
        )
    ):
        raise ValueError("WB native source not in S49 original probe history")
    if supplied.state == "CURRENT_EPOCH_READ_ONLY":
        if (
            last != native_seq or not supplied.current_uncertainty
            or supplied.past_review_candidate is not None
        ):
            raise ValueError("stale WB is not current")
    elif supplied.state == "PAST_EPOCH_REVIEW_ONLY":
        if (
            last <= native_seq or not supplied.past_review_candidate
            or supplied.current_uncertainty is not None
        ):
            raise ValueError("old WB cannot act as current source")
    else:
        raise ValueError("only admitted WB read states can join")
    return supplied.state, native_seq


def join_completed_s49_cognition(
    *,
    enabled: bool = False,
    batch: object,
    m_admission: object | None = None,
    wb_read: object | None = None,
) -> S49CognitionJoinedReadout:
    """Never retroactively veto an executed S49 Action on observer failure.

    RECORDED with NOT_SUPPLIED companions is S49 source-only, NOT S1 integration.
    """
    if enabled is not True:
        return S49CognitionJoinedReadout("DISABLED", "default_off")
    try:
        original, row = _original(batch)
        ms = NOT_SUPPLIED if m_admission is None else _m_status(original, m_admission)
        ws, wb_seq = (
            (NOT_SUPPLIED, None) if wb_read is None
            else _wb_status(original, wb_read)
        )
        decisions = tuple(
            (d["event_seq"], d["probe_seq"], d["request_id"], d["action_id"])
            for d in row["decisions"]
        )
    except (ValueError, AttributeError, ImportError, TypeError, KeyError):
        return S49CognitionJoinedReadout(
            "DEFERRED", "unqualified_source_or_missing_owner"
        )
    return S49CognitionJoinedReadout(
        "RECORDED", "read_only_original_s49_postowner",
        original.session_id, decisions, ms, ws, wb_seq,
    )


def bounded_s49_cognition_join_row(
    value: S49CognitionJoinedReadout,
) -> dict[str, object]:
    """Allowlisted IDs and qualifiers only; never raw World, Body or L2 text."""
    if not isinstance(value, S49CognitionJoinedReadout):
        raise ValueError("typed bounded S49 join required")
    return {
        "schema": "S49_S_COGNITION_JOIN_DEV_V1",
        "status": value.status,
        "reason": value.reason,
        "session_id": value.session_id,
        "decision_count": len(value.decisions),
        "decision_source_ids": [
            {"event_seq": e, "probe_seq": p, "request_id": r, "action_id": a}
            for e, p, r, a in value.decisions
        ],
        "m_status": value.m_status,
        "wb_status": value.wb_status,
        "wb_source_probe_seq": value.wb_source_probe_seq,
        "model_usage": value.model_usage,
        "s42_owner": value.s42_owner,
        "b0_owner": value.b0_owner,
        "l8_owner": value.l8_owner,
        "source_attested": value.source_attested,
        "action_authority": value.action_authority,
        "new_native_reads": value.new_native_reads,
        "new_model_calls": value.new_model_calls,
        "new_action_issues": value.new_action_issues,
        "learning_updates": value.learning_updates,
        "energy_debits": value.energy_debits,
    }
