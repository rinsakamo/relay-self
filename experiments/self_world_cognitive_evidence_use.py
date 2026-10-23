"""Source-only W4 cognitive evidence-use adapter (DEV; never calls a model).

Host owns source qualification. A GoalSpec is *not* source evidence, and a
BoundedChoiceRequest is *not* an Action, Memory or learning authority.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

from experiments import self_world_host_two_axis as host
from experiments.self_world_metadata_ablation import digest
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
)

SCOPE = "DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN"
CHOICES = (
    "USE_CURRENT_POSITIVE",
    "USE_MATCHED_FORECAST_SCOPE",
    "REQUEST_MORE_EVIDENCE",
    "WITHHOLD_UNSUPPORTED_CLAIM",
)
REVIEW_STATES = frozenset(("NO_REVIEW", "MATCH", "MISMATCH", "UNDETERMINED"))
GOAL_KINDS = frozenset(("EXPLAIN_OBSERVED", "ASSESS_FORECAST"))
PSEUDO = Provenance("DEV-only-cognitive-goal-not-World-evidence", "fixed-interface-v0")
DESCRIPTIONS = {
    "USE_CURRENT_POSITIVE": "Use only currently selected positive observation.",
    "USE_MATCHED_FORECAST_SCOPE": "Use only the host-matched target/property comparison.",
    "REQUEST_MORE_EVIDENCE": "Suggest further evidence gathering, not a World action.",
    "WITHHOLD_UNSUPPORTED_CLAIM": "Withhold unsupported claims without discarding positives.",
}


class EvidenceUseBlocked(ValueError):
    """Untrusted source, invalid goal, or unqualified cognitive choice."""


@dataclass(frozen=True, slots=True)
class GoalSpec:
    """Independent cognitive goal; importance is a priority, not a truth value."""

    kind: Literal["EXPLAIN_OBSERVED", "ASSESS_FORECAST"]
    importance: int
    max_additional_cost: float

    def __post_init__(self):
        if (
            type(self.kind) is not str
            or self.kind not in GOAL_KINDS
            or type(self.importance) is not int
            or not 1 <= self.importance <= 3
            or type(self.max_additional_cost) not in (int, float)
            or not math.isfinite(self.max_additional_cost)
            or self.max_additional_cost < 0
        ):
            raise EvidenceUseBlocked("invalid goal or cognitive cost bound")


@dataclass(frozen=True, slots=True)
class EvidenceUseCandidates:
    """Frozen gate envelope; custody dict is host-private, not a capability."""

    request: BoundedChoiceRequest | None
    admissible: tuple[str, ...]
    available: tuple[str, ...]
    custody_manifest: dict
    status: Literal["READY", "DEFER"]
    request_sha256: str | None
    scope: str = SCOPE
    model_calls: int = 0
    world_actions: int = 0
    memory_writes: int = 0
    s10_updates: int = 0


def _checked_record(record: dict, expected_source_digest: str) -> None:
    """Recheck full source binding and both axis digests before redaction."""
    if type(record) is not dict or set(record) != {
        "scope", "binding", "observation", "prediction",
    } or record["scope"] != host.SCOPE:
        raise EvidenceUseBlocked("unexpected host record shape")
    b, o, p = (record[k] for k in ("binding", "observation", "prediction"))
    if (
        type(b) is not dict
        or set(b) != {
            "source_receipt_sha256", "case_id", "source_class", "epoch",
            "self_id", "session_id", "epoch_id",
        }
        or b["source_receipt_sha256"] != expected_source_digest
        or b["case_id"] not in host.probe.CASE_IDS
        or b["epoch"] not in ("prior", "following")
        or any(not isinstance(b[k], str) or not b[k] for k in b)
        or type(o) is not dict
        or type(p) is not dict
    ):
        raise EvidenceUseBlocked("foreign binding or source receipt")
    observation = dict(o)
    prediction = dict(p)
    observed_digest = observation.pop("source_bound_digest", None)
    reviewed_digest = prediction.pop("source_bound_review_digest", None)
    if (
        type(observed_digest) is not str
        or type(reviewed_digest) is not str
        or observed_digest != digest({"binding": b, "observation": observation})
        or reviewed_digest != digest({"binding": b, "prediction": prediction})
    ):
        raise EvidenceUseBlocked("host-axis digest mismatch")
    if (
        set(observation) != {
            "source_verification_status", "source_verified",
            "positive_selected_count", "selected_positive_observations",
            "observation_provenance", "observation_source", "attention",
            "coverage_truncated", "world_absence_established",
            "world_safety_established",
        }
        or set(prediction) != {
            "forecast_present_in_view", "prior_forecast_present",
            "review_status", "predicted_value", "observed_value",
            "compared_property", "review", "prior_forecasts",
            "prior_observation", "action_success", "reward",
        }
        or observation["source_verified"] is not True
        or observation["source_verification_status"] != "VERIFIED_FIXED_DEV_SOURCE"
        or observation["observation_source"]["observer_id"] != b["self_id"]
        or observation["observation_source"]["session_id"] != b["session_id"]
        or observation["world_absence_established"] is not False
        or observation["world_safety_established"] is not False
        or prediction["action_success"] is not None
        or prediction["reward"] is not None
        or type(observation["coverage_truncated"]) is not bool
        or prediction["review_status"] not in REVIEW_STATES
    ):
        raise EvidenceUseBlocked("unallowlisted or uncertified host semantics")
    positives = observation["selected_positive_observations"]
    if (
        type(positives) is not list
        or type(observation["positive_selected_count"]) is not int
        or observation["positive_selected_count"] != len(positives)
        or any(
            type(e) is not dict
            or set(e) != {
                "entity_ref", "label", "position", "distance_m",
                "visible_action", "origin",
            }
            or e["origin"] != "observed"
            for e in positives
        )
    ):
        raise EvidenceUseBlocked("forecast or invented source became observed")
    review = prediction["review"]
    status = prediction["review_status"]
    if status == "NO_REVIEW":
        if review is not None or any(
            prediction[k] is not None for k in (
                "predicted_value", "observed_value", "compared_property",
            )
        ):
            raise EvidenceUseBlocked("NO_REVIEW has injected review")
    elif (
        type(review) is not dict
        or review.get("status") != status.lower()
        or review.get("variable_key") != prediction["compared_property"]
        or review.get("predicted_value") != prediction["predicted_value"]
        or review.get("observed_value") != prediction["observed_value"]
        or review.get("self_id") != b["self_id"]
        or review.get("session_id") != b["session_id"]
        or review.get("later_epoch_id") != b["epoch_id"]
        or review.get("later_observation_ref")
        != (
            "present:"
            + str(observation["observation_source"]["session_id"])
            + ":" + str(observation["observation_source"]["native_seq"])
            + ":" + str(observation["observation_source"]["request_id"])
        )
        or review.get("observation_provenance")
        != observation["observation_provenance"]
    ):
        raise EvidenceUseBlocked("unbound review")


def _matched_scope(record: dict) -> dict | None:
    """MATCH is support for the same positively seen target/property ONLY."""
    prediction, observed = record["prediction"], record["observation"]
    if prediction["review_status"] != "MATCH":
        return None
    review = prediction["review"]
    matches = tuple(
        p for p in observed["selected_positive_observations"]
        if p["entity_ref"] == review["target_ref"]
    )
    prop = review["variable_key"]
    projection = {"entity_label": "label", "visible_action": "visible_action"}
    if prop == "entity_visible":
        value = True if matches else None
    elif prop in projection:
        value = matches[0][projection[prop]] if len(matches) == 1 else None
    else:
        value = None
    if (
        len(matches) != 1
        or value is None
        or value != review["observed_value"]
        or value != review["predicted_value"]
    ):
        raise EvidenceUseBlocked("MATCH scope not bound to positive target/property")
    return {"property": prop, "supported_value": value, "scope": "observed_target_only"}


def prepare_evidence_use(
    source_root, *, case_id: str, epoch: str,
    expected_source_digest: str, goal: GoalSpec | None,
    claimed_record: dict | None = None,
) -> EvidenceUseCandidates:
    """Read pinned source FRESH. Optional claimed record must match byte-for-byte.

    The caller cannot supply source truth by forging digest fields or an old row.
    No provider, RelayEngine, Action or persistence is invoked.
    """
    if goal is not None and type(goal) is not GoalSpec:
        raise EvidenceUseBlocked("goal must be typed and independent of source")
    if (
        case_id not in host.probe.CASE_IDS or epoch not in ("prior", "following")
        or type(expected_source_digest) is not str
        or len(expected_source_digest) != 64
    ):
        raise EvidenceUseBlocked("foreign source request")
    record = host.read_epoch(
        source_root, case_id=case_id, epoch=epoch,
        expected_source_digest=expected_source_digest,
    )
    _checked_record(record, expected_source_digest)
    if claimed_record is not None and (
        claimed_record != record or digest(claimed_record) != digest(record)
    ):
        raise EvidenceUseBlocked("supplied record differs from freshly verified source")
    observed, prediction = record["observation"], record["prediction"]
    matched = _matched_scope(record)
    eligible = {
        "USE_CURRENT_POSITIVE": observed["positive_selected_count"] > 0,
        "USE_MATCHED_FORECAST_SCOPE": matched is not None,
        "REQUEST_MORE_EVIDENCE": True,
        "WITHHOLD_UNSUPPORTED_CLAIM": True,
    }
    admissible = tuple(k for k in CHOICES if eligible[k])
    # Information acquisition is not free. It is *cognitive proposal cost*,
    # never an M0/P1 debit or automatic sensor/World action.
    costs = {
        "USE_CURRENT_POSITIVE": 0.0,
        "USE_MATCHED_FORECAST_SCOPE": 0.0,
        "REQUEST_MORE_EVIDENCE": 0.5,
        "WITHHOLD_UNSUPPORTED_CLAIM": 0.0,
    }
    available = tuple(
        k for k in admissible
        if goal is not None and costs[k] <= goal.max_additional_cost
    )
    custody = {
        "binding": record["binding"],
        "source_digest": expected_source_digest,
        "observation_digest": observed["source_bound_digest"],
        "prediction_digest": prediction["source_bound_review_digest"],
        "raw_source_verified": True,
        "admissible": admissible,
        "available": available,
    }
    if len(available) < 2:
        return EvidenceUseCandidates(
            request=None, admissible=admissible, available=available,
            custody_manifest=custody, status="DEFER", request_sha256=None,
        )
    # The only model-facing observations are sanitized positive attributes.
    # No entity_ref, self/session/epoch ID, provenance, receipt or host digest.
    positives = [
        {k: item[k] for k in (
            "label", "position", "distance_m", "visible_action",
        )}
        for item in observed["selected_positive_observations"]
    ]
    evidence = {
        "positive_selected_count": len(positives),
        "current_positive": positives,
        "coverage_truncated": observed["coverage_truncated"],
        "review_status": prediction["review_status"],
        "prior_forecast_present": prediction["prior_forecast_present"],
        "forecast_present_in_view": prediction["forecast_present_in_view"],
        "matched_scope": matched,
        "unobserved": "UNKNOWN_not_world_absence",
        "action_success": None,
        "candidate_costs": {k: costs[k] for k in available},
    }
    assert goal is not None
    instruction = (
        "Choose a cognitive evidence-use strategy for the stated goal. "
        "Host eligibility is fixed and may not be overturned. "
        "Current positives are observations; matched forecasts are supported "
        "only for the specified target/property. Unobserved is UNKNOWN. "
        "Do not issue World actions, update Memory/S10, or infer reward."
    )
    request = BoundedChoiceRequest(
        request_id=(
            f"w4-coguse-{host.probe.CASE_IDS.index(case_id)}-{epoch}-"
            f"{goal.kind.lower()}-{goal.importance}-{goal.max_additional_cost:g}"
        ),
        instruction=instruction, intent_id=None, focus="DEV-evidence-use-only",
        choices=tuple(BoundedChoice(k, DESCRIPTIONS[k]) for k in available),
        context=(
            CognitionDatum.from_value(
                "dev_cognitive_goal",
                {"kind": goal.kind, "importance": goal.importance,
                 "max_additional_cost": goal.max_additional_cost}, PSEUDO,
            ),
            CognitionDatum.from_value("dev_host_evidence_allowlist", evidence, PSEUDO),
        ),
        think_allowed=False,
    )
    return EvidenceUseCandidates(
        request=request, admissible=admissible, available=available,
        custody_manifest=custody, status="READY",
        request_sha256=digest(asdict(request)),
    )


def validate_selected_strategy(
    prepared: EvidenceUseCandidates, *, choice_id: str, request_sha256: str,
    source_root, case_id: str, epoch: str, expected_source_digest: str,
    goal: GoalSpec | None,
) -> str:
    """Re-read original host evidence before accepting a choice ID.

    A caller-controlled dataclass (even one with matching forged hashes) is not
    host authority. Nor is this a one-time consumption lease: an identical
    response to an identical static offline request cannot be distinguished
    without the separately owned future request/response lifecycle.
    """
    if type(prepared) is not EvidenceUseCandidates:
        raise EvidenceUseBlocked("untyped candidate set")
    fresh = prepare_evidence_use(
        source_root, case_id=case_id, epoch=epoch,
        expected_source_digest=expected_source_digest, goal=goal,
    )
    if (
        fresh != prepared
        or fresh.status != "READY"
        or fresh.request is None
        or type(choice_id) is not str
        or choice_id not in fresh.available
        or choice_id not in tuple(c.choice_id for c in fresh.request.choices)
        or request_sha256 != fresh.request_sha256
        or request_sha256 != digest(asdict(fresh.request))
    ):
        raise EvidenceUseBlocked("ineligible choice or substituted request")
    return choice_id
