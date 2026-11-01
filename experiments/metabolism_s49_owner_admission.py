"""M #616: read-only S49 original completion admission, not S42/B0/L8.

Two non-equivalent DEV inputs:
* ORIGINAL_PYTHON_BATCH: existing owner-returned S49 batch, with exact Python
  object identity and terminal Action revalidated via original S49 code.
* SAVED_REPORT_JSON: bounded S49 report verified for internal consistency,
  including its original decoded S15/S16 movement evidence. Cannot recover
  Python object identity or independently attest the World/source.

Never adapt either to S42's SLMDevTapResult or mint model/energy cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

Kind = Literal["ORIGINAL_PYTHON_BATCH", "SAVED_REPORT_JSON"]
Status = Literal["DISABLED", "RECORDED", "DEFERRED"]
_FIELDS = frozenset({
    "schema", "session_id", "step_count", "wait_count", "outcome_count",
    "decisions", "real_s42_epoch_supplied", "real_b0_decision_supplied",
    "real_l8_epoch_supplied", "source_attested", "action_authority",
    "new_native_reads", "new_model_calls", "new_action_issues",
    "learning_updates", "energy_debits",
})
_DEC_FIELDS = frozenset({
    "event_seq", "probe_seq", "request_id", "choice", "action_id", "s16_terminal",
})


class S49MAdmissionRejected(ValueError):
    """Foreign, incomplete, replayed or unqualified owner evidence."""


@dataclass(frozen=True, slots=True)
class S49MDecision:
    event_seq: int
    probe_seq: int
    request_id: str
    choice: Literal["WAIT", "MOVE_AWAY"]
    action_id: str | None
    s16_terminal: str | None


@dataclass(frozen=True, slots=True)
class S49MAdmission:
    kind: Kind
    session_id: str
    decisions: tuple[S49MDecision, ...]
    wait_count: int
    outcome_count: int
    source_attested: bool = False
    action_authority: bool = False
    real_s42_epoch_supplied: bool = False
    real_b0_decision_supplied: bool = False
    real_l8_epoch_supplied: bool = False
    model_usage: str = "UNKNOWN_NO_MODEL_METER"
    metabolic_energy: str = "UNKNOWN_NO_B0_OWNER"
    l8_learning: str = "UNKNOWN_NO_L8_OWNER"
    new_native_reads: int = 0
    new_model_calls: int = 0
    new_action_issues: int = 0
    learning_updates: int = 0
    energy_debits: int = 0


@dataclass(frozen=True, slots=True)
class S49MAdmissionReadout:
    status: Status
    reason: str
    admission: S49MAdmission | None = None
    source_attested: bool = False
    action_authority: bool = False


def _identifier(value: object) -> bool:
    return type(value) is str and 1 <= len(value) <= 192 and value.isprintable()


def _row_to_admission(row: Mapping[str, object], kind: Kind) -> S49MAdmission:
    if not isinstance(row, Mapping) or frozenset(row) != _FIELDS:
        raise S49MAdmissionRejected("exact original S49 completion row required")
    if (
        row["schema"] != "S49_ORIGINAL_COMPLETION_DEV_V1"
        or not _identifier(row["session_id"])
        or type(row["step_count"]) is not int
        or not 1 <= row["step_count"] <= 8
        or type(row["wait_count"]) is not int
        or type(row["outcome_count"]) is not int
        or any(row[k] is not False for k in (
            "real_s42_epoch_supplied", "real_b0_decision_supplied",
            "real_l8_epoch_supplied", "source_attested", "action_authority",
        ))
        or any(type(row[k]) is not int or row[k] != 0 for k in (
            "new_native_reads", "new_model_calls", "new_action_issues",
            "learning_updates", "energy_debits",
        ))
        or type(row["decisions"]) is not list
        or len(row["decisions"]) != row["step_count"]
    ):
        raise S49MAdmissionRejected("forged S49 source or synthetic B0/L8/LLM")
    seen_events: set[int] = set()
    seen_probes: set[int] = set()
    seen_requests: set[str] = set()
    seen_actions: set[str] = set()
    last_event = -1
    last_probe = -1
    decisions: list[S49MDecision] = []
    for raw in row["decisions"]:
        if not isinstance(raw, Mapping) or frozenset(raw) != _DEC_FIELDS:
            raise S49MAdmissionRejected("exact original S49 decision fields required")
        event, probe, request = raw["event_seq"], raw["probe_seq"], raw["request_id"]
        choice, action, terminal = raw["choice"], raw["action_id"], raw["s16_terminal"]
        if (
            type(event) is not int or type(probe) is not int
            or event < 0 or probe <= event
            or event <= last_event or probe <= last_probe
            or event in seen_events or probe in seen_probes
            or not _identifier(request) or request in seen_requests
            or request != f"s49-actual:{row['session_id']}:event-{event}"
            or choice not in ("WAIT", "MOVE_AWAY")
            or (choice == "WAIT" and (action is not None or terminal is not None))
            or (choice == "MOVE_AWAY" and (
                not _identifier(action) or action != f"s49-native-move-{event}"
                or terminal != "outcome" or action in seen_actions
            ))
        ):
            raise S49MAdmissionRejected("S49 source/Action/outcome mismatch")
        seen_events.add(event)
        seen_probes.add(probe)
        seen_requests.add(request)
        if choice == "MOVE_AWAY":
            seen_actions.add(action)
        last_event, last_probe = event, probe
        decisions.append(S49MDecision(event, probe, request, choice, action, terminal))
    waits = sum(d.choice == "WAIT" for d in decisions)
    outcomes = len(decisions) - waits
    if row["wait_count"] != waits or row["outcome_count"] != outcomes:
        raise S49MAdmissionRejected("original WAIT/S16 accounting mismatch")
    return S49MAdmission(kind, row["session_id"], tuple(decisions), waits, outcomes)


def admit_original_s49_batch(batch: object) -> S49MAdmission:
    """Accept actual original typed owner objects, never cast to S42."""
    from adapters.mineflayer.s49_completed_decision_bridge import (
        S49OriginalCompletedBatch,
        bounded_original_s49_completion_row,
        read_original_s49_completions,
    )

    if not isinstance(batch, S49OriginalCompletedBatch):
        raise S49MAdmissionRejected("original S49 typed batch required")
    if any(
        item.source_scope != "S49_ORIGINAL_L0_STEP_WITH_OPTIONAL_S16_NOT_S42_EPOCH"
        or item.source_attested is not False
        or item.action_authority is not False
        for item in batch.steps
    ):
        raise S49MAdmissionRejected("forged S49 step authority or source scope")
    original = tuple(item.step for item in batch.steps)
    probes = {item.probe.seq: item.probe for item in batch.steps}
    receipts = {
        item.step.action_request_id: item.action_receipt
        for item in batch.steps if item.action_receipt is not None
    }
    try:
        reconstructed = read_original_s49_completions(original, probes, receipts)
        if (
            batch.session_id != reconstructed.session_id
            or len(batch.steps) != len(reconstructed.steps)
            or any(
                a.step is not b.step or a.probe is not b.probe
                or a.action_receipt is not b.action_receipt
                for a, b in zip(batch.steps, reconstructed.steps)
            )
        ):
            raise S49MAdmissionRejected("original S49 object identity mismatch")
        row = bounded_original_s49_completion_row(batch)
        return _row_to_admission(row, "ORIGINAL_PYTHON_BATCH")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise S49MAdmissionRejected("original owner return rejected") from exc


def admit_saved_s49_report(report: object) -> S49MAdmission:
    """Check internal source/effect consistency of an immutable saved report.

    The report is ONE declared producer. Comparing fields and decoded frames
    does NOT independently authenticate its Minecraft origin, Python identity
    or model costs. Do not call this "source attestation".
    """
    from adapters.mineflayer.self_action_evidence import verify_native_action_evidence

    if not isinstance(report, Mapping) or (
        report.get("status") != "PASS"
        or report.get("original_completion_observer") != "CALLBACK_RETURNED"
        or type(report.get("node_exit")) is not int
        or report["node_exit"] != 0
        or type(report.get("server_exit")) is not int
        or report["server_exit"] != 0
    ):
        raise S49MAdmissionRejected("completed, cleaned-up original S49 report required")
    admission = _row_to_admission(
        report.get("original_completion_readback"), "SAVED_REPORT_JSON",
    )
    if (
        report.get("session_id") != admission.session_id
        or type(report.get("decisions")) is not list
        or type(report.get("source_pair_trace")) is not list
        or type(report.get("actual_native_actions")) is not list
        or len(report["decisions"]) != len(admission.decisions)
        or len(report["source_pair_trace"]) != len(admission.decisions)
        or len(report["actual_native_actions"]) != admission.outcome_count
    ):
        raise S49MAdmissionRejected("saved S49 owner report counts mismatch")
    actual_actions = report["actual_native_actions"]
    movement_idx = 0
    for d, owner, pair in zip(
        admission.decisions, report["decisions"], report["source_pair_trace"],
    ):
        if (
            not isinstance(owner, Mapping) or not isinstance(pair, Mapping)
            or owner.get("event_seq") != d.event_seq
            or owner.get("probe_seq") != d.probe_seq
            or owner.get("selected") != d.choice
            or owner.get("issued") is not (d.choice == "MOVE_AWAY")
            or pair.get("event_seq") != d.event_seq
            or pair.get("probe_seq") != d.probe_seq
        ):
            raise S49MAdmissionRejected("saved original L0 decision/probe mismatch")
        if d.choice == "WAIT":
            continue
        action = actual_actions[movement_idx]
        movement_idx += 1
        if (
            not isinstance(action, Mapping)
            or action.get("event_seq") != d.event_seq
            or action.get("probe_seq") != d.probe_seq
            or action.get("action") != d.action_id
            or action.get("terminal") != "outcome"
            or action.get("source") != admission.session_id
            or type(action.get("movement_m")) not in (float, int)
        ):
            raise S49MAdmissionRejected("saved original Action/S16 mismatch")
        try:
            verify_native_action_evidence(
                action.get("execution_evidence"),
                action_id=d.action_id,
                session_id=admission.session_id,
                movement_m=action["movement_m"],
            )
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise S49MAdmissionRejected("saved S15/S16 decoded frame mismatch") from exc
    return admission


class S49MAdmissionLease:
    """Default-OFF passive owner admission; one S49 session per lease."""

    def __init__(self, *, enabled: bool = False, max_batches: int = 8) -> None:
        if type(enabled) is not bool or type(max_batches) is not int or not 1 <= max_batches <= 8:
            raise ValueError("explicit bounded DEV admission lease required")
        self.enabled = enabled
        self.max_batches = max_batches
        self._session: str | None = None
        self._last_event = -1
        self._seen_sources: set[tuple[str, int, int, str]] = set()
        self._admitted = 0

    def _accept(self, candidate: S49MAdmission) -> S49MAdmissionReadout:
        sources = tuple(
            (candidate.session_id, d.event_seq, d.probe_seq, d.request_id)
            for d in candidate.decisions
        )
        if (
            self._admitted >= self.max_batches
            or (self._session is not None and self._session != candidate.session_id)
            or candidate.decisions[0].event_seq <= self._last_event
            or any(s in self._seen_sources for s in sources)
        ):
            return S49MAdmissionReadout("DEFERRED", "replay_or_session_budget")
        self._session = candidate.session_id
        self._last_event = candidate.decisions[-1].event_seq
        self._seen_sources.update(sources)
        self._admitted += 1
        return S49MAdmissionReadout("RECORDED", "s49_original_completed_only", candidate)

    def admit_batch(self, batch: object) -> S49MAdmissionReadout:
        if not self.enabled:
            return S49MAdmissionReadout("DISABLED", "not_enabled")
        try:
            return self._accept(admit_original_s49_batch(batch))
        except (ValueError, TypeError, KeyError, AttributeError):
            return S49MAdmissionReadout("DEFERRED", "invalid_s49_owner")

    def admit_report(self, report: object) -> S49MAdmissionReadout:
        if not self.enabled:
            return S49MAdmissionReadout("DISABLED", "not_enabled")
        try:
            return self._accept(admit_saved_s49_report(report))
        except (ValueError, TypeError, KeyError, AttributeError):
            return S49MAdmissionReadout("DEFERRED", "invalid_s49_owner")


def bounded_s49_m_admission_row(value: S49MAdmissionReadout) -> dict[str, object]:
    """Small M audit with no source snapshots, raw LLM text, or energy truth."""
    if (
        not isinstance(value, S49MAdmissionReadout)
        or value.source_attested or value.action_authority
        or value.reason not in {
            "DISABLED": ("not_enabled",),
            "RECORDED": ("s49_original_completed_only",),
            "DEFERRED": ("invalid_s49_owner", "replay_or_session_budget"),
        }.get(value.status, ())
        or ((value.status == "RECORDED") != (value.admission is not None))
    ):
        raise S49MAdmissionRejected("forged M source admission or authority")
    admission = value.admission
    if admission is not None and (
        not isinstance(admission, S49MAdmission)
        or admission.source_attested or admission.action_authority
        or admission.real_s42_epoch_supplied
        or admission.real_b0_decision_supplied or admission.real_l8_epoch_supplied
        or admission.model_usage != "UNKNOWN_NO_MODEL_METER"
        or admission.metabolic_energy != "UNKNOWN_NO_B0_OWNER"
        or admission.l8_learning != "UNKNOWN_NO_L8_OWNER"
        or any(type(getattr(admission, key)) is not int or getattr(admission, key) != 0
               for key in ("new_native_reads", "new_model_calls", "new_action_issues",
                           "learning_updates", "energy_debits"))
        or len(admission.decisions) != admission.wait_count + admission.outcome_count
    ):
        raise S49MAdmissionRejected("M cannot forge S42/B0/L8 or measured resource use")
    return {
        "schema": "M_S49_ORIGINAL_COMPLETION_DEV_V1",
        "status": value.status,
        "reason": value.reason,
        "kind": admission.kind if admission else None,
        "session_id": admission.session_id if admission else None,
        "step_count": len(admission.decisions) if admission else None,
        "wait_count": admission.wait_count if admission else None,
        "outcome_count": admission.outcome_count if admission else None,
        "real_s42_epoch_supplied": False,
        "real_b0_decision_supplied": False,
        "real_l8_epoch_supplied": False,
        "model_usage": "UNKNOWN_NO_MODEL_METER",
        "provider_calls": None,
        "input_tokens": None,
        "output_tokens": None,
        "wall_ns": None,
        "cpu_ns": None,
        "gpu_ns": None,
        "metabolic_energy": "UNKNOWN_NO_B0_OWNER",
        "l8_learning": "UNKNOWN_NO_L8_OWNER",
        "source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_model_calls": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
    }
