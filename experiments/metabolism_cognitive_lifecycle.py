"""M-only read-only longitudinal DEV cognition cost accounting.

Consumes the existing S/L8/M bounded audit row AFTER the owner epoch.
An S/L8/M row does not prove L2 calls; a separately supplied meter is needed.
Never converts cognition time/tokens into B0 Energy or P1 fatigue.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

Phase = Literal["EXPLORE", "FAMILIAR", "SHIFT", "RECOVER"]
Level = Literal["L0", "L1", "L2", "UNKNOWN"]
Outcome = Literal["SUCCEEDED", "FAILED", "UNKNOWN"]
Metric = Literal[
    "provider_calls", "input_tokens", "output_tokens", "wall_ns",
    "cpu_ns", "gpu_ns",
]
_METRICS: tuple[Metric, ...] = (
    "provider_calls", "input_tokens", "output_tokens", "wall_ns", "cpu_ns", "gpu_ns",
)
_PHASES: tuple[Phase, ...] = ("EXPLORE", "FAMILIAR", "SHIFT", "RECOVER")
_AUDIT_FIELDS = frozenset({
    "schema", "status", "reason", "session_id", "probe_seq", "request_id",
    "s_choice", "l1_candidate", "l1_status", "m_model_tension",
    "l1_model_status", "source_scope", "native_source_attested",
    "action_authority", "new_native_reads", "new_cognition_calls",
    "action_issues", "learning_updates", "habit_grants", "food_credits",
})
_SCOPE = "DEV_OPTIONAL_S_L_M_AUDIT_NOT_ACTION_INPUT"


def _id(value: object) -> bool:
    return type(value) is str and 1 <= len(value) <= 192 and value.isprintable()


@dataclass(frozen=True, slots=True)
class CognitiveWorkReceipt:
    """Caller-supplied, source-referenced DEV meter; None != measured zero."""

    session_id: str
    request_id: str
    probe_seq: int
    receipt_id: str
    level: Level
    provider_calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    wall_ns: int | None = None
    cpu_ns: int | None = None
    gpu_ns: int | None = None
    measurement_scope: str = "DECLARED_DEV_NOT_SOURCE_ATTESTED"


@dataclass(frozen=True, slots=True)
class CognitionCostSample:
    """One original, completed S epoch and optionally an independent meter."""

    epoch_id: str
    task_id: str
    condition_id: str
    phase: Phase  # external label, not an inferred learning stage
    outcome: Outcome  # external annotation, not physical Goal admission
    audit_row: Mapping[str, object]
    usage: CognitiveWorkReceipt | None = None


@dataclass(frozen=True, slots=True)
class MetricCoverage:
    name: Metric
    measured_count: int
    missing_count: int
    observed_sum: int | None
    complete_total: int | None


@dataclass(frozen=True, slots=True)
class PhaseCostSummary:
    phase: Phase
    epochs: int
    usage_receipts: int
    success_labels: int
    failure_labels: int
    unknown_labels: int
    levels: tuple[tuple[Level, int], ...]
    conditions: tuple[str, ...]
    metrics: tuple[MetricCoverage, ...]


@dataclass(frozen=True, slots=True)
class CognitiveLifecycleSummary:
    session_id: str
    task_id: str
    epoch_count: int
    phases: tuple[PhaseCostSummary, ...]
    interpretation: str = "DESCRIPTIVE_DEV_ONLY_NOT_LEARNING_OR_CAUSAL_PROOF"
    source_attested: bool = False
    action_authority: bool = False
    cognition_budget_authority: bool = False
    energy_debits: int = 0
    learning_updates: int = 0
    habit_grants: int = 0


class CognitiveLifecycleRejected(ValueError):
    """Unbounded, mixed, forged or unsupported M observation."""


def _check_audit(row: Mapping[str, object]) -> tuple[str, int, str]:
    # Exact allowlist from bounded_s_l_m_audit_row. Structural match
    # does NOT independently certify native source.
    if not isinstance(row, Mapping) or frozenset(row) != _AUDIT_FIELDS:
        raise CognitiveLifecycleRejected("exact bounded S/L8/M audit row required")
    if (
        row["schema"] != "SLM_PASSIVE_DEV_AUDIT_V1"
        or row["status"] != "RECORDED" or row["reason"] != "complete"
        or row["source_scope"] != _SCOPE
        or row["native_source_attested"] is not False
        or row["action_authority"] is not False
        or any(type(row[k]) is not int or row[k] != 0 for k in (
            "new_native_reads", "new_cognition_calls", "action_issues",
            "learning_updates", "habit_grants", "food_credits",
        ))
        or not _id(row["session_id"])
        or type(row["probe_seq"]) is not int or row["probe_seq"] < 0
        or not _id(row["request_id"])
        or row["s_choice"] not in ("WAIT", "MOVE_AWAY")
        or row["l1_candidate"] not in (None, "WAIT", "MOVE_AWAY")
        or row["l1_status"] not in (
            None, "retention_off", "no_admissible_l1_proposal",
            "l1_agrees_with_s", "l1_shadow_differs_from_s",
            "cheap_memory_rule_differs_from_s",
        )
        or row["m_model_tension"] not in (
            "MOVE_MODEL_INSUFFICIENT", "MOVE_MODEL_AMBIGUOUS",
            "MOVE_MODEL_UNKNOWN", "WAIT_MODEL_INSUFFICIENT",
            "WAIT_MODEL_AMBIGUOUS", "WAIT_MODEL_UNKNOWN", "NO_MODEL_TENSION",
        )
        or row["l1_model_status"] not in (
            None, "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT",
            "MODEL_AMBIGUOUS", "UNKNOWN", "NO_ADMISSIBLE_L1_CANDIDATE",
        )
    ):
        raise CognitiveLifecycleRejected("unauthorized or malformed audit row")
    status = row["l1_status"]
    candidate = row["l1_candidate"]
    model = row["l1_model_status"]
    choice = row["s_choice"]
    if (status is None and (candidate is not None or model is not None)) or (
        status in ("retention_off", "no_admissible_l1_proposal")
        and (candidate is not None or model != "NO_ADMISSIBLE_L1_CANDIDATE")
    ) or (
        status in ("l1_agrees_with_s", "l1_shadow_differs_from_s",
                   "cheap_memory_rule_differs_from_s")
        and (candidate is None or model not in (
            "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT", "MODEL_AMBIGUOUS", "UNKNOWN",
        ) or ((candidate == choice) != (status == "l1_agrees_with_s")))
    ) or (
        choice == "WAIT" and str(row["m_model_tension"]).startswith("MOVE_")
    ) or (
        choice == "MOVE_AWAY" and str(row["m_model_tension"]).startswith("WAIT_")
    ):
        raise CognitiveLifecycleRejected("inconsistent original M audit result")
    return row["session_id"], row["probe_seq"], row["request_id"]


def _check_usage(
    usage: CognitiveWorkReceipt, source: tuple[str, int, str],
    seen_receipts: set[str],
) -> None:
    if (
        not isinstance(usage, CognitiveWorkReceipt)
        or type(usage.session_id) is not str
        or (usage.session_id, usage.probe_seq, usage.request_id) != source
        or not _id(usage.receipt_id) or usage.receipt_id in seen_receipts
        or usage.level not in ("L0", "L1", "L2", "UNKNOWN")
        or usage.measurement_scope != "DECLARED_DEV_NOT_SOURCE_ATTESTED"
    ):
        raise CognitiveLifecycleRejected("foreign, duplicate or forged cognition meter")
    if all(getattr(usage, metric) is None for metric in _METRICS):
        raise CognitiveLifecycleRejected("empty meter must be absent, not zero")
    for metric in _METRICS:
        value = getattr(usage, metric)
        if value is not None and (type(value) is not int or value < 0):
            raise CognitiveLifecycleRejected("invalid cognitive metric")
    if usage.provider_calls == 0 and (
        (usage.input_tokens is not None and usage.input_tokens > 0)
        or (usage.output_tokens is not None and usage.output_tokens > 0)
    ):
        raise CognitiveLifecycleRejected("nonzero tokens contradict zero calls")
    seen_receipts.add(usage.receipt_id)


def summarize_cognitive_lifecycle(
    samples: tuple[CognitionCostSample, ...], *, max_epochs: int = 64,
) -> CognitiveLifecycleSummary:
    """Count actual supplied metrics, never infer or declare a learning gain."""
    if (
        type(max_epochs) is not int or not 1 <= max_epochs <= 64
        or type(samples) is not tuple or not 1 <= len(samples) <= max_epochs
    ):
        raise CognitiveLifecycleRejected("bounded nonempty tuple required")
    seen_epochs: set[str] = set()
    seen_requests: set[str] = set()
    seen_receipts: set[str] = set()
    session: str | None = None
    task: str | None = None
    last_seq = -1
    groups: dict[Phase, list[CognitionCostSample]] = {p: [] for p in _PHASES}
    for sample in samples:
        if (
            not isinstance(sample, CognitionCostSample)
            or not _id(sample.epoch_id) or sample.epoch_id in seen_epochs
            or not _id(sample.task_id) or not _id(sample.condition_id)
            or sample.phase not in _PHASES
            or sample.outcome not in ("SUCCEEDED", "FAILED", "UNKNOWN")
        ):
            raise CognitiveLifecycleRejected("invalid phase, task or repeated epoch")
        source = _check_audit(sample.audit_row)
        sess, seq, request = source
        if (
            (session is not None and sess != session)
            or (task is not None and task != sample.task_id)
            or seq <= last_seq or request in seen_requests
        ):
            raise CognitiveLifecycleRejected("mixed World, task, replay or reordered probe")
        if sample.usage is not None:
            _check_usage(sample.usage, source, seen_receipts)
        session = sess
        task = sample.task_id
        last_seq = seq
        seen_epochs.add(sample.epoch_id)
        seen_requests.add(request)
        groups[sample.phase].append(sample)
    summaries = []
    for phase in _PHASES:
        group = groups[phase]
        if not group:
            continue
        metrics = []
        for metric in _METRICS:
            known = [
                getattr(item.usage, metric)
                for item in group if item.usage is not None
                and getattr(item.usage, metric) is not None
            ]
            missing = len(group) - len(known)
            measured = sum(known) if known else None
            metrics.append(MetricCoverage(
                metric, len(known), missing, measured,
                measured if missing == 0 else None,
            ))
        levels = tuple(
            (level, sum(item.usage is not None and item.usage.level == level
                        for item in group))
            for level in ("L0", "L1", "L2", "UNKNOWN")
        )
        summaries.append(PhaseCostSummary(
            phase=phase, epochs=len(group),
            usage_receipts=sum(item.usage is not None for item in group),
            success_labels=sum(item.outcome == "SUCCEEDED" for item in group),
            failure_labels=sum(item.outcome == "FAILED" for item in group),
            unknown_labels=sum(item.outcome == "UNKNOWN" for item in group),
            levels=levels,
            conditions=tuple(sorted({item.condition_id for item in group})),
            metrics=tuple(metrics),
        ))
    assert session is not None and task is not None
    return CognitiveLifecycleSummary(session, task, len(samples), tuple(summaries))
