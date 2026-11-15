"""Read-only result-consistency audit for #850 controlled semantic DEV trials.

Verifies *reported typed records*, not raw Mineflayer/Paper authenticity.
It never starts World/Gemma, edits a WAL, certifies fsync, or awards QUAL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class SemanticEvidenceAuditError(ValueError):
    """A required typed, mutually consistent result field is missing or wrong."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SemanticEvidenceAuditError(message)


def _obj(value: object, name: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{name} must be object")
    return value


def _native_obs(entry: object, name: str) -> dict[str, Any]:
    document = _obj(entry, name)
    _require(
        document.get("evidence_format") == "TYPED_DECODED_MINEFLAYER_OBSERVATION_V1"
        and document.get("native_source") == "mineflayer",
        f"{name} must be typed decoded Mineflayer provenance",
    )
    obs = _obj(document.get("observation"), f"{name}.observation")
    _require(
        type(obs.get("seq")) is int
        and document.get("native_source_ref")
        == f"{obs.get('session_id')}:{obs.get('seq')}",
        f"{name} source reference must match session/seq",
    )
    return obs


def audit_trial(document: dict[str, Any], *, expected: str) -> dict[str, str]:
    """Require one single-parent real-shaped semantic result, read-only audit."""
    _require(expected in {"EAT_GOAL_DONE", "EAT_GOAL_ACTIVE", "ATTACK_GOAL_ACTIVE"},
             "unsupported semantic trial role")
    data = _obj(document, "result")
    eat = expected.startswith("EAT")
    capability = "EAT" if eat else "ATTACK"
    goal = "HUNGER_RELIEF" if eat else "DEFEND_SELF"
    terminal_status = "NATIVE_EAT_OUTCOME" if eat else "NATIVE_ATTACK_HURT_OBSERVED"
    physical_status = (
        "NATIVE_EAT_OUTCOME_DEV_ONLY" if eat
        else "NATIVE_ATTACK_HURT_OBSERVED_DEV_ONLY"
    )
    _require(
        data.get("evidence_class") == "REAL_LLM_AND_NATIVE_WORLD_DEV_ATTEMPT"
        and data.get("status") == physical_status
        and data.get("semantic_eval_dev_selected") is True
        and data.get("semantic_apply_dev_selected") is True
        and data.get("l0_skill_ir_dev_selected") is True
        and data.get("physical_eat_dev_selected") is eat
        and data.get("physical_attack_dev_selected") is (not eat)
        and data.get("l1_choice_id") == "1"
        and data.get("action_outcome_count") == 1
        and data.get("physical_journal_unresolved") is False
        and data.get("semantic_evaluation_error") is None
        and data.get("semantic_evaluation_memory_published") is False,
        "trial is not one explicit successful physical+semantic DEV route",
    )
    selected = _obj(data.get("selected"), "selected")
    assessment = _obj(data.get("semantic_assessment"), "semantic_assessment")
    application = _obj(data.get("semantic_application"), "semantic_application")
    _require(
        selected.get("skill_id") == capability and selected.get("skill_version") == 1
        and selected.get("goal_id") == goal
        and assessment.get("skill_id") == capability
        and assessment.get("goal_id") == goal
        and assessment.get("target_ref") == selected.get("target_ref")
        and assessment.get("skill_evidence") == "SUPPORTED"
        and assessment.get("independent_paper_damage_attested") is False
        and application.get("skill_state") == "succeeded"
        and application.get("skill_transition_applied") is True
        and application.get("memory_published") is False
        and data.get("skill_final_state") == "succeeded",
        "selected Skill/evaluation/local success identity mismatch",
    )
    statuses = [x.get("status") for x in data.get("l0_skill_ir_trace", [])]
    _require(
        statuses == [
            "PROPOSE_ACTION", "AWAIT_ACTION", "ADVANCED", "TERMINAL_CANDIDATE",
        ],
        "one canonical L0 action trace required",
    )
    records = data.get("physical_journal_records")
    _require(type(records) is list and len(records) == 1,
             "one terminal physical WAL parent record required")
    row = _obj(records[0], "physical_journal_records[0]")
    parent_key = "physical_eat_parent_action_id" if eat else "physical_attack_parent_action_id"
    action_id = data.get(parent_key)
    _require(
        type(action_id) is str and bool(action_id)
        and row.get("action_id") == action_id
        and row.get("capability") == capability
        and row.get("status") == terminal_status
        and row.get("target_ref") == selected.get("target_ref")
        and assessment.get("action_id") == action_id
        and assessment.get("intent_id") == row.get("intent_id")
        and assessment.get("skill_execution_id") == row.get("skill_execution_id")
        and row.get("session_id") == data.get("world_session")
        and assessment.get("session_id") == data.get("world_session"),
        "physical parent/WAL/semantic source identity mismatch",
    )
    _require(
        data.get("native_actions") == [{"action_id": action_id, "state": "outcome"}],
        "exactly one supervised native OUTCOME required",
    )
    start = _native_obs(data.get("initial_native_observation"), "initial")
    final = _native_obs(data.get("semantic_evaluation_probe"), "semantic")
    _require(
        start.get("session_id") == final.get("session_id") == data.get("world_session")
        and final.get("kind") == "probe"
        and bool(final.get("request_id"))
        and final["seq"] == assessment.get("evaluation_probe_seq")
        and assessment.get("evaluation_source_ref")
        == f"{final['session_id']}:{final['seq']}"
        and assessment.get("evaluation_request_id") == final.get("request_id")
        and type(row.get("after_seq")) is int
        and row["after_seq"] < final["seq"],
        "fresh source-qualified post-Action semantic observation required",
    )
    if eat:
        threshold = data.get("scenario_inputs", {}).get("food_threshold")
        food_before = row.get("food_before")
        food_after = row.get("food_after")
        current_food = _obj(final.get("snapshot"), "semantic.snapshot").get("food")
        _require(
            type(threshold) in (int, float)
            and type(food_before) is int and type(food_after) is int
            and type(current_food) in (int, float)
            and food_before < food_after
            and selected.get("target_ref", "").startswith("inventory:")
            and data.get("native_eat_consequence_attested") is True,
            "EAT food/inventory native consequence absent",
        )
        satisfied = expected == "EAT_GOAL_DONE"
        _require(
            ((current_food > threshold) is satisfied)
            and assessment.get("goal_evidence")
            == ("SATISFIED" if satisfied else "ACTIVE")
            and application.get("intent_transition_applied") is satisfied
            and application.get("intent_state")
            == ("completed" if satisfied else "committed")
            and data.get("intent_final_state")
            == ("completed" if satisfied else "committed"),
            "HUNGER_RELIEF incorrectly conflated with local EAT success",
        )
    else:
        hit = _obj(data.get("attack_hurt_evidence"), "attack_hurt_evidence")
        _require(
            selected.get("target_ref") == f"entity:{hit.get('target_entity_id')}"
            and hit.get("source_entity_id") is not None
            and hit.get("source_entity_id") == hit.get("actor_entity_id")
            and hit.get("hurt_seq") == row.get("hurt_seq")
            and assessment.get("goal_evidence") == "ACTIVE"
            and application.get("intent_transition_applied") is False
            and application.get("intent_state") == "committed"
            and data.get("intent_final_state") == "committed",
            "ATTACK hit cannot auto-complete DEFEND_SELF",
        )
        entities = _obj(final.get("snapshot"), "semantic.snapshot").get(
            "nearby_entities"
        )
        _require(
            type(entities) is list
            and any(type(ent) is dict and ent.get("name") == "zombie"
                    for ent in entities),
            "expected active Zombie must remain native-observed",
        )
    return {
        "role": expected, "session_id": str(data["world_session"]),
        "self_id": str(assessment["self_id"]),
        "action_id": action_id, "wal_path": str(data.get("physical_journal_path")),
        "skill": "succeeded", "intent": str(data["intent_final_state"]),
    }


def audit_three_trials(
    eat_done: dict[str, Any], eat_active: dict[str, Any],
    attack_active: dict[str, Any],
) -> dict[str, Any]:
    trials = (
        audit_trial(eat_done, expected="EAT_GOAL_DONE"),
        audit_trial(eat_active, expected="EAT_GOAL_ACTIVE"),
        audit_trial(attack_active, expected="ATTACK_GOAL_ACTIVE"),
    )
    for key in ("session_id", "self_id", "action_id", "wal_path"):
        vals = [t[key] for t in trials]
        _require(len(set(vals)) == len(vals), f"distinct trial {key} required")
    return {
        "classification": "TYPED_RESULT_CONSISTENCY_PASS_NOT_WORLD_AUTHENTICATION",
        "trial_count": len(trials), "trials": list(trials),
        "raw_native_verified": False, "paper_damage_attributed": False,
        "qual": "NO_GO", "science": "NOT_RUN",
    }


def _load(path: str) -> tuple[dict[str, Any], str]:
    payload = Path(path).read_bytes()
    data = json.loads(payload)
    return _obj(data, path), hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eat-done", required=True)
    parser.add_argument("--eat-active", required=True)
    parser.add_argument("--attack-active", required=True)
    args = parser.parse_args()
    try:
        documents = [_load(p) for p in (
            args.eat_done, args.eat_active, args.attack_active,
        )]
        summary = audit_three_trials(*(item[0] for item in documents))
        summary["result_json_sha256"] = [item[1] for item in documents]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"SEMANTIC_RESULT_AUDIT_REJECTED: {exc}\n")
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
