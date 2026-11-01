"""L-BCG H8: offline audit of *available* original owners at S49 decision time.

Operator-local spatial plan is NOT independently source-qualified Goal.
Provisional B0/P1 owner exports are NOT present in the archived H5 pre-action
native source. Never infer energy from food, gait from direction, hazards
from hostile sightings, or cross-World chronology from operator revision.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from relay_self.l_bcg_dev_proxy import DevProxyRejected
from relay_self.l_bcg_h7_preaction import H7PreActionAudit, audit_h7_pre_action

_REQUIRED = (
    "goal_remaining_m", "goal_tolerance_m", "selected_gait",
    "p1_fatigue_high", "m_energy_low", "verified_obstacle",
    "world_revision", "verified_post_clear_training",
)


@dataclass(frozen=True, slots=True)
class H8OwnerStatus:
    feature: str
    owner: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class H8SourceAvailability:
    session_id: str
    paper_world_id: str
    pre_action_seq: int
    operator_goal_plan_sha256: str
    operator_plan_horizontal_distance_m: float
    operator_plan_tolerance_m: float
    operator_plan_qualifies_goal: bool
    features: tuple[H8OwnerStatus, ...]
    missing_required: tuple[str, ...]
    pre_action_source_qualified: bool = False
    source_qualified_training_worlds: int = 0
    original_l0_choice_modified: bool = False
    action_issues: int = 0
    learning_commits: int = 0
    learned_l1_attention: str = "DEFER_UNKNOWN"
    qualification: str = "NO_GO"
    science: str = "NOT_RUN"


def _check(ok: bool, why: str) -> None:
    if not ok:
        raise DevProxyRejected(why)


def inspect_h8_owner_sources(
    *, host_report_original: bytes, independent_audit_original: bytes,
    s16_original: bytes, s7_received_prefix_original: bytes,
    paper_server_original: bytes, operator_goal_plan_original: bytes,
    audit_classification: str = "DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED",
) -> H8SourceAvailability:
    """Use H7 byte-gated actual H5 receipt, then classify the operator plan.

    Returns observed owner availability, not a new Goal or Action proposal.
    """
    h7: H7PreActionAudit = audit_h7_pre_action(
        host_report_original=host_report_original,
        independent_audit_original=independent_audit_original,
        s16_original=s16_original,
        s7_received_prefix_original=s7_received_prefix_original,
        paper_server_original=paper_server_original,
        audit_classification=audit_classification,
    )
    _check(
        type(operator_goal_plan_original) is bytes
        and 0 < len(operator_goal_plan_original) <= 4096,
        "bounded operator-plan original required",
    )
    try:
        plan = json.loads(operator_goal_plan_original)
        report = json.loads(host_report_original)
        audit = json.loads(independent_audit_original)
    except (ValueError, UnicodeError) as exc:
        raise DevProxyRejected("malformed operator plan or archived source") from exc
    _check(isinstance(plan, dict), "typed operator-plan JSON required")
    digest = hashlib.sha256(operator_goal_plan_original).hexdigest()
    _check(
        audit["original_sha256"].get("capture/l16_pre_world_goal_plan.json") == digest
        and report["l16_capture"]["external_goal_owner_independent"] is False
        and report["l16_capture"]["l18_s16_owner_source"][
            "independent_external_goal_original"
        ] is False
        and plan.get("schema") == "L16_PRE_WORLD_OPERATOR_SPATIAL_GOAL_V1"
        and plan.get("authorizes_learning") is False
        and plan.get("independent_external_goal_owner") is False,
        "unbound or falsely promoted operator-only Goal plan",
    )
    for field in ("target_x", "target_z", "tolerance_m"):
        value = plan.get(field)
        _check(
            type(value) in (int, float) and math.isfinite(value),
            "invalid operator-only spatial number",
        )
    _check(plan["tolerance_m"] >= 0, "negative tolerance")
    body = {cue.name: cue for cue in h7.pre_action_observed}
    _check(
        body["position_x"].native_seq == body["position_z"].native_seq
        == h7.original_choice_probe_seq
        and h7.missing_bcg_conditions == _REQUIRED,
        "future/native or unknown-feature source crossover",
    )
    horizontal = math.hypot(
        body["position_x"].value - plan["target_x"],
        body["position_z"].value - plan["target_z"],
    )
    _check(math.isfinite(horizontal), "non-finite operator geometry")
    _check(
        report["actual_native_actions"][0]["execution_evidence"][
            "action_ref"
        ] == "MOVE_BACKWARD"
        and report["l_bcg_shadow"]["conditional"] is None
        and report["l_bcg_shadow"]["advice"] == "DEFER_UNKNOWN"
        and report["l_bcg_shadow"]["used_physical_training_worlds"] == 0,
        "H5 source or original Action changed",
    )
    # IMPORTANT: These are reasons THIS H5 archived action cannot be promoted.
    # They are not assertions that independent owners never existed elsewhere.
    statuses = (
        H8OwnerStatus(
            "goal_remaining_m", "Goal/S49 external",
            "OPERATOR_GEOMETRY_ONLY_NOT_GOAL",
            "L16 plan is operator-local, target is not independent Goal owner",
        ),
        H8OwnerStatus(
            "goal_tolerance_m", "Goal/S49 external",
            "OPERATOR_TOLERANCE_ONLY_NOT_GOAL",
            "tolerance is stated but no independent Goal-owner admission",
        ),
        H8OwnerStatus(
            "selected_gait", "G4/S49 gait",
            "NO_PRE_ACTION_GAIT_RECEIPT",
            "MOVE_BACKWARD direction is not WALK/JOG/RUN/DASH gait",
        ),
        H8OwnerStatus(
            "p1_fatigue_high", "P1/SelfBody",
            "NO_CORRELATED_P1_SENSOR_RECEIPT",
            "P1 owner handoff needs native seq, owner tick and source; missing here",
        ),
        H8OwnerStatus(
            "m_energy_low", "M0/SelfBody",
            "NO_CORRELATED_M0_SENSOR_RECEIPT",
            "Minecraft food is not M0 interoception or true energy",
        ),
        H8OwnerStatus(
            "verified_obstacle", "SelfWorld/G4",
            "NO_OBSTACLE_GEOMETRY_OWNER",
            "bounded zombie registry cannot attest voxel obstacle state",
        ),
        H8OwnerStatus(
            "world_revision", "S/R World source",
            "NO_CROSS_WORLD_SOURCE_ORDER",
            "S16 operator source_revision is not global training chronology",
        ),
        H8OwnerStatus(
            "verified_post_clear_training", "S7/S16/Paper",
            "NO_EFFECTIVE_CLEAR_ATTESTATION",
            "sampled reported-input OFF is not physical post-clear stability",
        ),
    )
    return H8SourceAvailability(
        session_id=h7.episode.session_id,
        paper_world_id=h7.episode.paper_world_id,
        pre_action_seq=h7.original_choice_probe_seq,
        operator_goal_plan_sha256=digest,
        operator_plan_horizontal_distance_m=horizontal,
        operator_plan_tolerance_m=float(plan["tolerance_m"]),
        operator_plan_qualifies_goal=False,
        features=statuses,
        missing_required=_REQUIRED,
    )
