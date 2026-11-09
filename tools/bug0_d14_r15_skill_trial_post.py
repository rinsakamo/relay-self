"""Independent read-only R15 Skill→original S49 trial readout.

Accepts an already audited R11 original S49 World result; never upgrades
the original outcome, claims independent Paper skill success or issues Actions.
"""
from __future__ import annotations

import json
from typing import Any


class R15PostRejected(ValueError):
    """The R15 sidecar is not original S49 source-bound evidence."""


def inspect_r15_trial(report: dict[str, Any], active: dict[str, Any],
                      original_sidecar: str,
                      prior: dict[str, Any]) -> dict[str, Any]:
    if (
        active.get("status") != "PASS_DEV"
        or report.get("status") != "PASS_DEV"
        or report.get("r15_trial_opt_in") is not True
        or active.get("r11_natural_day_opt_in") is not True
        or report.get("s49_physical_issuer")
        != "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR"
        or report.get("r15_trial_new_issuer_count") != 0
        or any(report.get(name) != 0 for name in (
            "model_posts", "skill_installs", "learning_updates",
            "c1_intent_experiences", "r15_skill_installs",
            "r15_learning_updates", "r15_memory_owner_writes",
        ))
        or report.get("original_s49_session_id")
        != report.get("native_session_id")
        or report.get("original_s49_session_id")
        == prior["prior_native_session_id"]
        or active.get("world_uuid") == prior["prior_world_uuid"]
        or report.get("r15_source") != {
            k: v for k, v in prior.items() if k != "program"
        }
    ):
        raise R15PostRejected("R15_PRIOR_SKILL_ORIGINAL_S49_SOURCE_UNQUALIFIED")
    try:
        sidecar = [json.loads(row) for row in original_sidecar.splitlines()]
    except (ValueError, TypeError) as exc:
        raise R15PostRejected("BROKEN_R15_APPEND_ONLY_SIDECAR") from exc
    if sidecar != report.get("r15_trial_steps"):
        raise R15PostRejected("R15_SIDECAR_AND_ORIGINAL_REPORT_DIFFER")
    decisions = {
        row["native_seq"]: row
        for row in report.get("life_decisions", [])
    }
    if len(decisions) != len(report.get("life_decisions", [])):
        raise R15PostRejected("R15_ORIGINAL_NATIVE_DECISION_SEQUENCE_DUPLICATE")
    outcomes = {a["action_id"]: a for a in report.get("life_action_outcomes", [])}
    if len(outcomes) != len(report.get("life_action_outcomes", [])):
        raise R15PostRejected("R15_ORIGINAL_S49_ACTION_REPLAY")
    program = prior["program"]
    previous_step_index = -1
    previous_repeat_ordinal = 0
    seen_actions: set[str] = set()
    last_seq = -1
    physically_matched = 0
    passive_matched = 0
    changed = 0
    for row in sidecar:
        step_index = row.get("step_index")
        repeat = row.get("repeat_ordinal")
        seq = row.get("native_seq")
        if (type(step_index) is not int
                or not 0 <= step_index < len(program["steps"])
                or type(repeat) is not int
                or not 1 <= repeat <= program["steps"][step_index]["repeat"]
                or type(seq) is not int or seq <= last_seq
                or (previous_step_index > step_index)
                or (step_index == previous_step_index
                    and repeat != previous_repeat_ordinal + 1)
                or (step_index > previous_step_index and repeat != 1)
                or row.get("candidate_program_sha256")
                != prior["program_sha256"]
                or row.get("action_granted_by_skill") is not False):
            raise R15PostRejected("R15_SKILL_STEP_BUDGET_OR_LINEAGE_MISMATCH")
        step = program["steps"][step_index]
        decision = decisions.get(seq)
        if (decision is None
                or decision.get("r15_skill_trial_hint") != row.get("action")
                or decision.get("r15_hint_is_not_authority") is not True
                or decision.get("selected") != row.get("original_l0_selected")
                or decision.get("preferred") != row.get("original_l0_preferred")
                or decision.get("fallback") != row.get("original_l0_fallback")
                or row.get("native_request_id")
                != decision.get("native_request_id")
                or row.get("action") != step["action"]
                or row.get("guard") != step["guard"]
                or row.get("binding") != step["binding"]):
            raise R15PostRejected("R15_ORIGINAL_S49_NATIVE_HINT_NOT_ATTESTED")
        physical = step["action"] in ("MOVE_AWAY", "ATTACK", "EAT")
        action_id = row.get("original_s49_action_id")
        matched = row.get("s49_original_issuer_matched")
        if physical and matched is True:
            action = outcomes.get(action_id)
            if (not isinstance(action_id, str) or action_id in seen_actions
                    or action is None
                    or action.get("kind") != step["action"]
                    or action.get("terminal") != "outcome"
                    or action.get("native_admitted_seq") != seq
                    or row.get("original_s49_outcome") != "outcome"
                    or row.get("nonphysical_skill_choice_applied") is not False):
                raise R15PostRejected("R15_PHYSICAL_STEP_NOT_ORIGINAL_S49_OUTCOME")
            physically_matched += 1
            seen_actions.add(action_id)
        elif not physical and row.get("nonphysical_skill_choice_applied") is True:
            if (action_id is not None
                    or row.get("original_s49_outcome") is not None
                    or matched is not False):
                raise R15PostRejected("R15_PASSIVE_SKILL_STEP_CLAIMED_ACTION")
            passive_matched += 1
        else:
            if (matched is not False
                    or row.get("nonphysical_skill_choice_applied") is not False
                    or action_id is not None):
                raise R15PostRejected("R15_REJECTED_SKILL_STEP_UPGRADED")
        if row.get("skill_effectiveness_or_goal_success_proven") is not False:
            raise R15PostRejected("R15_GOAL_SUCCESS_INVENTED")
        changed += row.get("skill_selection_differs_from_old_r11") is True
        previous_step_index, previous_repeat_ordinal = step_index, repeat
        last_seq = seq
    if report.get("r15_trial_physical_s49_issued") != physically_matched:
        raise R15PostRejected("R15_SKILL_MATCH_COUNT_NOT_ORIGINAL_ACTIONS")
    return {
        "classification": "DEV_R15_SKILL_HINT_TO_ORIGINAL_S49_OUTCOME_AUDITED",
        "status": "PASS_DEV",
        "world_uuid": active["world_uuid"],
        "native_session_id": report["native_session_id"],
        "prior_world_uuid": prior["prior_world_uuid"],
        "prior_native_session_id": prior["prior_native_session_id"],
        "program_sha256": prior["program_sha256"],
        "catalog_sha256": prior["catalog_sha256"],
        "matched_original_s49_physical_actions": physically_matched,
        "matched_nonphysical_skill_choices": passive_matched,
        "skill_choice_differed_from_unmodified_r11_count": changed,
        "trial_source_records": len(sidecar),
        "new_action_issuer_count": 0,
        "new_model_posts": 0,
        "memory_owner_writes": 0,
        "learning_updates": 0,
        "skill_installs": 0,
        "same_world_goal_success_proven": False,
        "later_epoch_l1_reuse_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }
