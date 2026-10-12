"""L Lane L2: action-conditioned hypotheses vs independently admitted observation.

Existing PRD owns deterministic transition, S16 owns physical observation, and
PersistentCognition owns all retention. This is not a World oracle, model,
causal estimator, Action issuer, S10 learning authority or S11 Habit promoter.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.experience_bridge import (
    QualifiedEpisode,
    ReuseQuery,
    ReuseStatus,
    retrieve_experience,
)
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.prediction import (
    PredictionResult,
    PredictionStatus,
    StateVariable,
    predict_transition,
)
from relay_self.provenance import Provenance

FORECAST_SCHEMA = "L2_ACTION_FORECAST_V1"
EVALUATION_SCHEMA = "L2_OBSERVED_COMPARISON_V1"
_TOKEN = re.compile(r"[A-Za-z0-9_.:/-]+")
_SHA = re.compile(r"[0-9a-f]{64}")


class ForecastRejected(ValueError):
    """Fail closed when source provenance or typed forecast scope is unsuitable."""


class ContrastStatus(str, Enum):
    MATCH = "match"
    SURPRISE = "surprise"
    NOT_OBSERVED = "counterfactual_not_observed"
    UNKNOWN = "unknown"
    UNVERIFIED = "unverified"
    STALE = "stale"


def _token(label: str, value: object) -> None:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ForecastRejected(f"{label} must be an exact nonempty token")


def _digest(value: object) -> None:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ForecastRejected("lowercase source SHA256 required")


def _revision(value: object) -> None:
    if type(value) is not int or value < 0:
        raise ForecastRejected("nonnegative source sequence required")


def _tags(tags: object) -> None:
    if (
        not isinstance(tags, tuple)
        or not tags
        or any(not isinstance(x, str) or _TOKEN.fullmatch(x) is None for x in tags)
        or tags != tuple(sorted(set(tags)))
    ):
        raise ForecastRejected("sorted unique nonempty cue tags required")


@dataclass(frozen=True, slots=True)
class ActionForecast:
    """A prospective hypothesis for ONE alternative, not an observed fact."""

    forecast_id: str
    session_id: str
    source_revision: int
    source_sha256: str
    action_ref: str
    cue_tags: tuple[str, ...]
    prediction: PredictionResult
    source_provenance: Provenance

    def __post_init__(self) -> None:
        for label in ("forecast_id", "session_id", "action_ref"):
            _token(label, getattr(self, label))
        _revision(self.source_revision)
        _digest(self.source_sha256)
        _tags(self.cue_tags)
        if not isinstance(self.source_provenance, Provenance):
            raise ForecastRejected("original source provenance required")
        if not isinstance(self.prediction, PredictionResult):
            raise ForecastRejected("existing PRD PredictionResult required")
        if self.prediction != predict_transition(
            self.prediction.source_state, self.prediction.rule
        ):
            raise ForecastRejected("forged PRD PredictionResult")
        if (
            self.prediction.source_state.variable("action_ref")
            != StateVariable("action_ref", self.action_ref)
            or StateVariable("action_ref", self.action_ref)
            not in self.prediction.rule.preconditions
        ):
            raise ForecastRejected("PRD rule must condition explicitly on action_ref")

    @property
    def memory_id(self) -> str:
        return f"l2:forecast:{self.session_id}:{self.forecast_id}"


@dataclass(frozen=True, slots=True)
class AdmittedObservation:
    """An S-owned projection; L cannot independently authenticate its content."""

    qualified: QualifiedEpisode
    variables: tuple[StateVariable, ...]
    projection_provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.qualified, QualifiedEpisode):
            raise ForecastRejected("original L1 typed qualified episode required")
        if (
            not isinstance(self.variables, tuple)
            or not self.variables
            or not all(isinstance(x, StateVariable) for x in self.variables)
            or len({x.key for x in self.variables}) != len(self.variables)
        ):
            raise ForecastRejected("unique observed StateVariable tuple required")
        if (
            not isinstance(self.projection_provenance, Provenance)
            or self.projection_provenance.source
            == "relay_self.prediction.predict_transition"
        ):
            raise ForecastRejected("independent S observation projection required")


@dataclass(frozen=True, slots=True)
class ForecastContrast:
    """Evidence-only result, with no implied Action or S10/S11 authority."""

    status: ContrastStatus
    forecast_memory_id: str
    observation_memory_id: str | None = None
    comparison_keys: tuple[str, ...] = ()
    mismatched_keys: tuple[str, ...] = ()
    reason: str = ""


def _forecast_content(forecast: ActionForecast) -> str:
    return json.dumps({
        "schema": FORECAST_SCHEMA,
        "forecast_id": forecast.forecast_id,
        "session_id": forecast.session_id,
        "source_revision": forecast.source_revision,
        "source_sha256": forecast.source_sha256,
        "action_ref": forecast.action_ref,
        "cue_tags": list(forecast.cue_tags),
        "prd_rule_id": forecast.prediction.rule.rule_id,
        "prediction_status": forecast.prediction.status.value,
        "hypothesized_assignments": (
            {x.key: x.value for x in forecast.prediction.rule.assignments}
            if forecast.prediction.status is PredictionStatus.PREDICTED else None
        ),
        "observed_world_fact": False,
        "executed_alternative": False,
        "s10_learning_authorized": False,
    }, sort_keys=True, separators=(",", ":"))


def retain_forecast(
    owner: PersistentCognition,
    forecast: ActionForecast,
    *,
    integration_provenance: Provenance,
) -> PersistentCognition:
    """Only the existing Memory owner stores a prediction-shaped memory."""
    if not isinstance(owner, PersistentCognition):
        raise ForecastRejected("existing PersistentCognition owner required")
    if not isinstance(forecast, ActionForecast):
        raise ForecastRejected("typed forecast required")
    if not isinstance(integration_provenance, Provenance):
        raise ForecastRejected("integration provenance required")
    return owner.retain_memory(Memory(
        forecast.memory_id, _forecast_content(forecast),
        forecast.source_provenance, integration_provenance,
    ))


def compare_forecast(
    forecast: ActionForecast,
    observation: AdmittedObservation | None,
    *,
    admitted_source_sha256: frozenset[str],
    max_source_lag: int = 64,
) -> ForecastContrast:
    """Evaluate ONLY the executed alternative against S-owned observed keys.

    This function never performs a physical observation, computes a competing
    counterfactual outcome or generates LearningFeedback.
    """
    if not isinstance(forecast, ActionForecast):
        raise ForecastRejected("typed forecast required")
    if (
        not isinstance(admitted_source_sha256, frozenset)
        or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
               for x in admitted_source_sha256)
    ):
        raise ForecastRejected("S-owned admitted digest set required")
    _revision(max_source_lag)
    base = forecast.memory_id
    if observation is None:
        return ForecastContrast(
            ContrastStatus.NOT_OBSERVED, base, reason="alternative_not_executed",
        )
    if not isinstance(observation, AdmittedObservation):
        raise ForecastRejected("typed S-owned observation required")
    e = observation.qualified.episode
    if e.session_id != forecast.session_id:
        raise ForecastRejected("foreign World session")
    if e.action_ref != forecast.action_ref:
        return ForecastContrast(
            ContrastStatus.NOT_OBSERVED, base, reason="different_action_executed",
        )
    if e.world_revision <= forecast.source_revision:
        return ForecastContrast(
            ContrastStatus.STALE, base, reason="observation_not_after_forecast",
        )
    if e.world_revision - forecast.source_revision > max_source_lag:
        return ForecastContrast(
            ContrastStatus.STALE, base, reason="source_sequence_outside_lag",
        )
    if (
        forecast.source_sha256 not in admitted_source_sha256
        or e.evidence_sha256 not in admitted_source_sha256
    ):
        return ForecastContrast(
            ContrastStatus.UNVERIFIED, base, reason="source_digest_not_admitted",
        )
    if (
        e.disposition is not ActionOutcomeDisposition.OUTCOME
        or e.source_status != "executed"
        or e.reason_code != "observed_execution"
        or forecast.prediction.status is not PredictionStatus.PREDICTED
    ):
        return ForecastContrast(
            ContrastStatus.UNKNOWN, base, reason="non_comparable_world_or_prediction",
        )
    assert forecast.prediction.predicted_state is not None
    predicted = {
        v.key: forecast.prediction.predicted_state.variable(v.key)
        for v in forecast.prediction.rule.assignments
    }
    observed = {v.key: v for v in observation.variables}
    keys = tuple(sorted(predicted))
    if any(key not in observed for key in keys):
        return ForecastContrast(
            ContrastStatus.UNKNOWN, base,
            reason="observed_projection_missing_predicted_key",
        )
    mismatch = tuple(
        key for key in keys
        if (
            type(predicted[key].value), predicted[key].value
        ) != (type(observed[key].value), observed[key].value)
    )
    return ForecastContrast(
        ContrastStatus.SURPRISE if mismatch else ContrastStatus.MATCH,
        base, e.memory_id, keys, mismatch,
        "independently_projected_observed_keys_not_goal_success",
    )


def retain_comparison(
    owner: PersistentCognition,
    forecast: ActionForecast,
    observation: AdmittedObservation,
    *,
    admitted_source_sha256: frozenset[str],
    integration_provenance: Provenance,
) -> tuple[PersistentCognition, ForecastContrast]:
    """Retain comparison only if BOTH original Memory records are present."""
    if not isinstance(owner, PersistentCognition):
        raise ForecastRejected("existing Memory owner required")
    if not isinstance(integration_provenance, Provenance):
        raise ForecastRejected("integration provenance required")
    stored = next((m for m in owner.memories if m.memory_id == forecast.memory_id), None)
    if (
        stored is None or stored.content != _forecast_content(forecast)
        or stored.source_provenance != forecast.source_provenance
    ):
        raise ForecastRejected("exact retained prospective forecast absent or altered")
    contrast = compare_forecast(
        forecast, observation, admitted_source_sha256=admitted_source_sha256,
    )
    if contrast.status not in (ContrastStatus.MATCH, ContrastStatus.SURPRISE):
        return owner, contrast
    e = observation.qualified.episode
    matching = retrieve_experience(owner, ReuseQuery(
        e.session_id, e.world_revision, e.cue_tags,
        frozenset({e.evidence_sha256}), max_revision_lag=0,
    ))
    if (
        matching.status is not ReuseStatus.RECALL
        or e.memory_id not in matching.memory_ids
        or e.action_ref not in matching.observed_action_refs
    ):
        raise ForecastRejected("original L1 observed Memory not qualified")
    contents = json.dumps({
        "schema": EVALUATION_SCHEMA,
        "forecast_memory_id": contrast.forecast_memory_id,
        "observation_memory_id": contrast.observation_memory_id,
        "session_id": e.session_id,
        "world_revision": e.world_revision,
        "action_ref": e.action_ref,
        "evidence_sha256": e.evidence_sha256,
        "cue_tags": list(e.cue_tags),
        "status": contrast.status.value,
        "comparison_keys": list(contrast.comparison_keys),
        "mismatched_keys": list(contrast.mismatched_keys),
        "learning_authorized": False,
        "goal_success_attested": False,
    }, sort_keys=True, separators=(",", ":"))
    updated = owner.retain_memory(Memory(
        f"l2:comparison:{e.memory_id}:{forecast.forecast_id}",
        contents, e.source_provenance, integration_provenance,
    ))
    return updated, contrast


def _validate_comparison_links(
    review: Memory,
    record: dict,
    by_id: dict[str, Memory],
    admitted: frozenset[str],
) -> None:
    """A derived review must never stand alone as purported World evidence."""
    try:
        f = by_id[record["forecast_memory_id"]]
        o = by_id[record["observation_memory_id"]]
        prospective = json.loads(f.content)
        observed = json.loads(o.content)
        if (
            not isinstance(prospective, dict)
            or not isinstance(observed, dict)
            or prospective.get("schema") != FORECAST_SCHEMA
            or observed.get("schema") != "L1_SOURCE_EPISODE_V1"
            or prospective.get("session_id") != record["session_id"]
            or observed.get("session_id") != record["session_id"]
            or prospective.get("action_ref") != record["action_ref"]
            or observed.get("action_ref") != record["action_ref"]
            or prospective.get("observed_world_fact") is not False
            or prospective.get("executed_alternative") is not False
            or observed.get("disposition") != "outcome"
            or observed.get("source_status") != "executed"
            or observed.get("reason_code") != "observed_execution"
            or observed.get("world_revision") != record["world_revision"]
            or observed.get("evidence_sha256") != record["evidence_sha256"]
            or observed.get("cue_tags") != record["cue_tags"]
            or review.source_provenance != o.source_provenance
            or prospective.get("source_sha256") not in admitted
            or observed.get("evidence_sha256") not in admitted
            or record["status"] not in {
                ContrastStatus.MATCH.value, ContrastStatus.SURPRISE.value,
            }
            or not isinstance(record["comparison_keys"], list)
            or not isinstance(record["mismatched_keys"], list)
            or not record["comparison_keys"]
            or not set(record["mismatched_keys"]).issubset(record["comparison_keys"])
            or (record["status"] == ContrastStatus.MATCH.value
                and bool(record["mismatched_keys"]))
            or (record["status"] == ContrastStatus.SURPRISE.value
                and not record["mismatched_keys"])
        ):
            raise ForecastRejected("derived comparison links are not original evidence")
    except (KeyError, ValueError, TypeError) as exc:
        raise ForecastRejected("missing or forged original forecast/observation Memory") from exc


def read_surprise_candidates(
    owner: PersistentCognition,
    *,
    session_id: str,
    cue_tags: tuple[str, ...],
    world_revision: int,
    admitted_evidence_sha256: frozenset[str],
    max_source_lag: int = 64,
) -> tuple[str, ...]:
    """Only review IDs, NOT next Action or control/learning authority."""
    if not isinstance(owner, PersistentCognition):
        raise ForecastRejected("existing owner required")
    _token("session_id", session_id)
    _tags(cue_tags)
    _revision(world_revision)
    _revision(max_source_lag)
    if (
        not isinstance(admitted_evidence_sha256, frozenset)
        or any(not isinstance(x, str) or _SHA.fullmatch(x) is None
               for x in admitted_evidence_sha256)
    ):
        raise ForecastRejected("admitted S digest set required")
    found = []
    by_id = {m.memory_id: m for m in owner.memories}
    for item in owner.memories:
        if not item.memory_id.startswith("l2:comparison:"):
            continue
        try:
            value = json.loads(item.content)
            if (
                not isinstance(value, dict)
                or set(value) != {
                    "schema", "forecast_memory_id", "observation_memory_id",
                    "session_id", "world_revision", "action_ref", "evidence_sha256",
                    "cue_tags", "status", "comparison_keys", "mismatched_keys",
                    "learning_authorized", "goal_success_attested",
                }
                or value["schema"] != EVALUATION_SCHEMA
                or value["learning_authorized"] is not False
                or value["goal_success_attested"] is not False
            ):
                raise ForecastRejected("malformed comparison Memory")
        except (ValueError, TypeError) as exc:
            raise ForecastRejected("untrusted comparison Memory") from exc
        if value["session_id"] != session_id:
            continue
        _validate_comparison_links(
            item, value, by_id, admitted_evidence_sha256,
        )
        if (
            value["status"] != ContrastStatus.SURPRISE.value
            or tuple(value["cue_tags"]) != cue_tags
            or value["evidence_sha256"] not in admitted_evidence_sha256
        ):
            continue
        src = value["world_revision"]
        if type(src) is not int or src > world_revision or src < 0:
            raise ForecastRejected("invalid or future comparison revision")
        if world_revision - src <= max_source_lag:
            found.append(item.memory_id)
    return tuple(sorted(found))


def cheap_rule_comparator(forecast: ActionForecast) -> PredictionResult:
    """Strongest cheap null uses exactly the SAME PRD state/rule and evidence."""
    return predict_transition(forecast.prediction.source_state, forecast.prediction.rule)
