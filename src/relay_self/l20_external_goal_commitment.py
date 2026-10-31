"""L20: externally authored session-agnostic Goal commitment, read-only.

Actual S49 IDs only exist after the World begins. This contract fixes Goal
geometry before the run WITHOUT pretending to create an L14 session-bound
pre-Action original or independent Goal observation. No signing, IO or learning.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

from adapters.mineflayer.l16_first_action_goal_originals import (
    L16FirstActionWindow,
    L16GoalPlan,
)
from relay_self.l14_original_bridge_goal_window import _json

COMMITMENT_SCHEMA = "L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1"
SESSION_SCOPE = "UNKNOWN_UNTIL_S49_SESSION_START"
ACTION_SCOPE = "FIRST_S49_PHYSICAL_ACTION_ONLY"
KEYS = frozenset({
    "schema", "criterion_id", "external_goal_owner_ref", "experiment_ref",
    "session_scope", "action_scope", "target_x", "target_z",
    "tolerance_m", "stable_probe_delta_max_m",
    "independent_goal_observed", "authorizes_learning",
})
SHA = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{3,127}\Z")
MAX_ORIGINAL = 4096


class L20GoalCommitmentRejected(ValueError):
    """Never accept a retrospective or incorrectly bound Goal criterion."""


@dataclass(frozen=True, slots=True)
class L20ExternalPreflight:
    schema: str
    criterion_id: str
    external_goal_owner_ref: str
    experiment_ref: str
    original_sha256: str
    matched_operator_plan: bool
    candidate_first_action_only: bool = True
    authenticated_external_owner: bool = False
    externally_attested_before_world: bool = False
    independent_goal_observed: bool = False
    learning_authority: bool = False
    qualified_real_l10_pairs: int = 0


@dataclass(frozen=True, slots=True)
class L20PostSourceBinding:
    schema: str
    criterion_sha256: str
    session_id: str
    first_action_id: str
    received_original_sha256: str
    sent_original_sha256: str
    source_goal_diagnostic: str
    criterion_matches_original_s49_plan: bool = True
    independent_goal_result_original_present: bool = False
    external_owner_authenticated: bool = False
    pre_world_time_independently_attested: bool = False
    no_intervention_physical_proven: bool = False
    qualified_real_l10_pairs: int = 0
    s10_updates: int = 0
    s11_grants: int = 0


def review_external_pre_world_criterion(
    *, original: bytes, admitted_sha256: str,
    operator_plan: L16GoalPlan,
) -> L20ExternalPreflight:
    """Check separately provided original, never mint one from the operator.

    Hash membership is not a signature or proof this was filed before World.
    A reviewer must preserve independent evidence of author & chronology.
    """
    if (
        not isinstance(original, bytes)
        or not 0 < len(original) <= MAX_ORIGINAL
        or not original.endswith(b"\n")
        or original.count(b"\n") != 1
        or not isinstance(admitted_sha256, str)
        or SHA.fullmatch(admitted_sha256) is None
        or not isinstance(operator_plan, L16GoalPlan)
        or hashlib.sha256(original).hexdigest() != admitted_sha256
    ):
        raise L20GoalCommitmentRejected("missing exact external original/SHA/plan")
    try:
        data = _json(original)
    except (UnicodeError, ValueError) as exc:
        raise L20GoalCommitmentRejected("external original malformed/duplicate") from exc
    if (
        set(data) != KEYS
        or data.get("schema") != COMMITMENT_SCHEMA
        or data.get("session_scope") != SESSION_SCOPE
        or data.get("action_scope") != ACTION_SCOPE
        or data.get("independent_goal_observed") is not False
        or data.get("authorizes_learning") is not False
        or any(
            not isinstance(data.get(k), str) or IDENT.fullmatch(data[k]) is None
            for k in ("criterion_id", "external_goal_owner_ref", "experiment_ref")
        )
    ):
        raise L20GoalCommitmentRejected("pre-world scope/owner/fields are not exact")
    # Require one unambiguous canonical UTF-8 JSONL original. Neither canonical
    # formatting nor correct SHA establishes physical origin or pre-World time.
    if original != (
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8"):
        raise L20GoalCommitmentRejected("external original must be canonical JSONL")
    for field, expected in (
        ("target_x", operator_plan.target_x),
        ("target_z", operator_plan.target_z),
        ("tolerance_m", operator_plan.tolerance_m),
        ("stable_probe_delta_max_m", operator_plan.stable_probe_delta_max_m),
    ):
        actual = data.get(field)
        if (
            type(actual) not in (int, float)
            or not math.isfinite(actual)
            or actual != expected
        ):
            raise L20GoalCommitmentRejected("pre-world Goal differs from operator plan")
    return L20ExternalPreflight(
        schema="L20_EXTERNAL_GOAL_PREWORLD_PREFLIGHT_V1",
        criterion_id=data["criterion_id"],
        external_goal_owner_ref=data["external_goal_owner_ref"],
        experiment_ref=data["experiment_ref"],
        original_sha256=admitted_sha256,
        matched_operator_plan=True,
    )


def review_l20_post_s49_source(
    *, preflight: L20ExternalPreflight,
    window: L16FirstActionWindow,
    operator_plan: L16GoalPlan,
) -> L20PostSourceBinding:
    """Link predeclared geometry to a L16-verified first Action (not reward)."""
    if (
        not isinstance(preflight, L20ExternalPreflight)
        or not isinstance(window, L16FirstActionWindow)
        or not isinstance(operator_plan, L16GoalPlan)
        or not preflight.matched_operator_plan
        or not preflight.candidate_first_action_only
        or preflight.authenticated_external_owner
        or preflight.externally_attested_before_world
        or preflight.independent_goal_observed
        or preflight.learning_authority
        or preflight.qualified_real_l10_pairs != 0
        or window.plan_sha256 != hashlib.sha256(
            operator_plan.original_bytes()
        ).hexdigest()
        or not window.complete_single_action_captured_prefix
        or window.independent_external_goal_authenticated
        or window.physical_no_intervention_proven
        or window.qualified_real_l10_pairs != 0
        or window.l10_adoptions != 0 or window.s10_updates != 0
        or window.s11_habit_grants != 0
        or not isinstance(window.session_id, str) or not window.session_id
        or not isinstance(window.action_id, str) or not window.action_id
        or window.observed_goal_status not in (
            "REACHED", "NOT_REACHED", "UNDETERMINED",
        )
    ):
        raise L20GoalCommitmentRejected("first-Action source not a bounded L16 review")
    return L20PostSourceBinding(
        schema="L20_EXTERNAL_GOAL_FIRST_ACTION_READONLY_BINDING_V1",
        criterion_sha256=preflight.original_sha256,
        session_id=window.session_id,
        first_action_id=window.action_id,
        received_original_sha256=window.received_sha256,
        sent_original_sha256=window.sent_sha256,
        source_goal_diagnostic=window.observed_goal_status,
    )
