"""M #616: S49's *already completed* original S16 owner receipts, not B0/L8.

This adds a source-bound typed Action evidence readout to an already-accepted
S49OriginalCompletedBatch. It never executes an Action, calls a model, reads
Minecraft, creates an S42 DecisionEpochResult, or manufactures B0/L8 owners.
The S49 callback currently exports only L0Step/probe/S16 receipt originals:
S14/S42's local epoch and B0/L8 owner results are NOT exported by this path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_s49_owner_admission import (
    S49MAdmissionReadout,
    admit_original_s49_batch,
)

ResultStatus = Literal["DISABLED", "RECORDED", "DEFERRED"]
_OWNER_ABSENT = "NOT_SUPPLIED_BY_ORIGINAL_S49_COMPLETION_CALLBACK"


@dataclass(frozen=True, slots=True)
class S49MOriginalActionReceipt:
    """References exact S49 Python original objects, NOT copied receipts."""

    original_step: object
    original_probe: object
    original_s16: object
    action_id: str
    event_seq: int
    probe_seq: int
    before_seq: int
    dispatch_seq: int
    clear_seq: int
    after_seq: int
    movement_m: float


@dataclass(frozen=True, slots=True)
class S49MOwnerReceiptReadout:
    status: ResultStatus
    reason: str
    session_id: str | None = None
    wait_count: int = 0
    outcome_count: int = 0
    original_actions: tuple[S49MOriginalActionReceipt, ...] = ()
    s42_owner_receipt: str = _OWNER_ABSENT
    b0_owner_receipt: str = _OWNER_ABSENT
    l8_owner_receipt: str = _OWNER_ABSENT
    source_attested: bool = False
    action_authority: bool = False
    native_reads: int = 0
    model_calls: int = 0
    action_issues: int = 0
    energy_debits: int = 0
    learning_updates: int = 0


def observe_original_s49_s16_receipts(
    *,
    enabled: bool = False,
    batch: object,
    original_admission: object,
) -> S49MOwnerReceiptReadout:
    """Source-check originals *after* S49 owner returned & M admitted them.

    Any missing/foreign/UNKNOWN S16 source results in atomic DEFERRED with
    no partial Action readout; observer never vetoes or reissues S49 Action.
    """
    if type(enabled) is not bool or not enabled:
        return S49MOwnerReceiptReadout("DISABLED", "not_enabled")
    try:
        from adapters.mineflayer.s49_completed_decision_bridge import (
            S49OriginalCompletedBatch,
        )
        from adapters.mineflayer.self_action_evidence import (
            capture_native_action_evidence,
        )

        if (
            not isinstance(batch, S49OriginalCompletedBatch)
            or not isinstance(original_admission, S49MAdmissionReadout)
            or original_admission.status != "RECORDED"
            or original_admission.reason != "s49_original_completed_only"
            or original_admission.source_attested
            or original_admission.action_authority
            or original_admission.admission is None
            or original_admission.admission.kind != "ORIGINAL_PYTHON_BATCH"
        ):
            raise ValueError("missing original typed owner admission")
        fresh = admit_original_s49_batch(batch)
        admitted = original_admission.admission
        if (
            fresh != admitted or fresh.session_id != batch.session_id
            or len(fresh.decisions) != len(batch.steps)
        ):
            raise ValueError("original batch/admission mismatch")
        actions: list[S49MOriginalActionReceipt] = []
        last_after = -1
        for source, decision in zip(batch.steps, fresh.decisions):
            step, probe, receipt = (
                source.step, source.probe, source.action_receipt,
            )
            if (
                step.event_seq != decision.event_seq
                or probe.seq != decision.probe_seq
                or probe.request_id != decision.request_id
                or (last_after >= 0 and decision.event_seq <= last_after)
            ):
                raise ValueError("nonmonotonic or foreign source")
            if decision.choice == "WAIT":
                if receipt is not None:
                    raise ValueError("WAIT may not receive S16")
                continue
            if receipt is None:
                raise ValueError("MOVE without original S16 receipt")
            consequence = receipt.consequence
            # Original S49 verifier checks decoded original before/after
            # position, exact dispatch/clear effects and source continuity.
            # It only reads existing frozen objects, never a native socket.
            native = capture_native_action_evidence(consequence)
            b = native["before_observation"]["seq"]
            d = native["dispatch_receipt"]["seq"]
            c = native["cleanup_receipt"]["seq"]
            a = native["after_observation"]["seq"]
            if not (
                probe.seq < b < d < c < a
                and receipt.terminal.action_id == decision.action_id
                and receipt.terminal.state.value == "outcome"
                and native["action_id"] == decision.action_id
                and native["session_id"] == batch.session_id
                and source.probe is probe
                and source.action_receipt is receipt
            ):
                raise ValueError("original S15/S16 closure not bound to decision")
            last_after = a
            actions.append(S49MOriginalActionReceipt(
                original_step=step,
                original_probe=probe,
                original_s16=receipt,
                action_id=decision.action_id,
                event_seq=decision.event_seq,
                probe_seq=decision.probe_seq,
                before_seq=b,
                dispatch_seq=d,
                clear_seq=c,
                after_seq=a,
                movement_m=consequence.movement_distance,
            ))
        if len(actions) != fresh.outcome_count:
            raise ValueError("partial original S49 owner receipts")
        return S49MOwnerReceiptReadout(
            "RECORDED", "original_s49_s16_source_bound",
            session_id=batch.session_id,
            wait_count=fresh.wait_count,
            outcome_count=fresh.outcome_count,
            original_actions=tuple(actions),
        )
    except Exception:
        # Passive diagnostic must fail closed, without propagating errors
        # into the original S49 execution or exposing the source snapshot.
        return S49MOwnerReceiptReadout("DEFERRED", "original_s49_s16_rejected")


def bounded_original_s49_owner_receipt_row(
    result: S49MOwnerReceiptReadout,
) -> dict[str, object]:
    """Minimal diagnostics, never the original Python objects or snapshots."""
    allowed_reasons = {
        "DISABLED": "not_enabled",
        "RECORDED": "original_s49_s16_source_bound",
        "DEFERRED": "original_s49_s16_rejected",
    }
    if (
        not isinstance(result, S49MOwnerReceiptReadout)
        or result.reason != allowed_reasons.get(result.status)
        or any(
            getattr(result, k) != _OWNER_ABSENT
            for k in ("s42_owner_receipt", "b0_owner_receipt", "l8_owner_receipt")
        )
        or result.source_attested or result.action_authority
        or any(type(getattr(result, k)) is not int or getattr(result, k) != 0
               for k in ("native_reads", "model_calls", "action_issues",
                         "energy_debits", "learning_updates"))
    ):
        raise ValueError("M owner receipts cannot claim S42/B0/L8 or authority")
    accepted = result.status == "RECORDED"
    if accepted:
        if (
            type(result.session_id) is not str or not result.session_id
            or type(result.wait_count) is not int
            or type(result.outcome_count) is not int
            or result.wait_count < 0
            or not 1 <= result.outcome_count <= 8
            or len(result.original_actions) != result.outcome_count
            or any(not isinstance(x, S49MOriginalActionReceipt)
                   for x in result.original_actions)
        ):
            raise ValueError("invalid accepted original Action receipts")
    elif (
        result.session_id is not None or result.wait_count != 0
        or result.outcome_count != 0 or result.original_actions
    ):
        raise ValueError("unadmitted owner source cannot expose original IDs")
    return {
        "schema": "M_S49_ORIGINAL_S16_OWNER_RECEIPTS_DEV_V1",
        "status": result.status,
        "reason": result.reason,
        "session_id": result.session_id,
        "wait_count": result.wait_count if accepted else None,
        "outcome_count": result.outcome_count if accepted else None,
        "actions": [
            {
                "action_id": a.action_id,
                "event_seq": a.event_seq,
                "probe_seq": a.probe_seq,
                "s16_before_seq": a.before_seq,
                "s16_dispatch_seq": a.dispatch_seq,
                "s15_clear_seq": a.clear_seq,
                "s16_after_seq": a.after_seq,
                "movement_m": a.movement_m,
            }
            for a in result.original_actions
        ],
        "s42_owner_receipt": _OWNER_ABSENT,
        "b0_owner_receipt": _OWNER_ABSENT,
        "l8_owner_receipt": _OWNER_ABSENT,
        "source_attested": False,
        "action_authority": False,
        "provider_calls": None,
        "input_tokens": None,
        "output_tokens": None,
        "wall_ns": None,
        "cpu_ns": None,
        "gpu_ns": None,
        "metabolic_energy": "UNKNOWN_NO_B0_OWNER",
        "l8_learning": "UNKNOWN_NO_L8_OWNER",
        "native_reads": 0,
        "model_calls": 0,
        "action_issues": 0,
        "energy_debits": 0,
        "learning_updates": 0,
    }
