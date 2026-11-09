"""D14 R14: source-qualified cross-World retained Skill shadow observation.

Read prior R11 World + genuine R12/R13 L2 raw Skill; independently audit a
different R11 World and match its ORIGINAL S49 observed outcomes against the
retained program. This never issues a World Action, reinterprets missing
guards as false, claims Skill caused an Action, or writes owner Memory/Habit.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.bug0_d14_r12_l2_shadow import (
    R12Rejected,
    project_r11,
    replay_retained_shadow,
)
from tools.bug0_d14_r13_action_catalog import (
    action_catalog,
    validate_skill_program,
)

SOURCE_FILES = (
    ("report", "report.json"),
    ("paper", "paper_original.log"),
    ("journal", "d14_natural_events.jsonl"),
    ("nonmotion", "original_s49_nonmotion_fence.json"),
    ("motion", "original_s49_motion_fence.json"),
)
PHYSICAL = frozenset(("MOVE_AWAY", "ATTACK", "EAT"))
NONPHYSICAL = frozenset(("REST", "WAIT"))


class R14Rejected(ValueError):
    """Never promote unaudited or same-World evidence into Skill reuse."""


def _read_world(directory: Path) -> dict[str, Any]:
    """Read each physical original ONCE and audit those exact bytes."""
    paths = {key: directory / filename for key, filename in SOURCE_FILES}
    if (not directory.is_dir() or directory.is_symlink()
            or any(not p.is_file() or p.is_symlink() for p in paths.values())):
        raise R14Rejected("R11_ORIGINAL_EVIDENCE_FILES_REQUIRED")
    originals = {key: path.read_bytes() for key, path in paths.items()}
    try:
        projection = project_r11(
            report_bytes=originals["report"],
            paper_bytes=originals["paper"],
            journal_bytes=originals["journal"],
            nonmotion_path=paths["nonmotion"],
            motion_path=paths["motion"],
        )
    except (ValueError, TypeError, OSError, KeyError) as exc:
        raise R14Rejected("R11_INDEPENDENT_ORIGINAL_AUDIT_REJECTED") from exc
    if any(path.read_bytes() != originals[key]
           for key, path in paths.items()):
        raise R14Rejected("R11_ORIGINAL_SOURCE_CHANGED_AFTER_AUDIT")
    context = projection["l2_context"]
    if (context.get("world_is_terminated") is not True
            or context.get("action_authority")
            != "NONE_POST_WORLD_READ_ONLY"
            or projection.get("s49_actions") != 0
            or projection.get("skill_installs") != 0):
        raise R14Rejected("UNQUALIFIED_READ_ONLY_PROJECTION")
    return projection


def _effect(action: str, observation: dict[str, Any]) -> str:
    """Describe only native evidence included in original R11 projection."""
    if action == "ATTACK":
        if (type(observation.get("native_target_entity_id")) is not int
                or type(observation.get("native_target_hurt_event_seen"))
                is not bool):
            return "S16_ONLY_ATTACK_EFFECT_UNKNOWN"
        return (
            "NATIVE_HURT_EVENT_NOT_PAPER_DAMAGE_OR_KILL"
            if observation["native_target_hurt_event_seen"]
            else "NATIVE_HURT_NOT_OBSERVED"
        )
    if action == "EAT":
        before, after = (
            observation.get("original_s51_food_before"),
            observation.get("original_s51_food_after"),
        )
        invbefore, invafter = (
            observation.get("original_s51_inventory_before"),
            observation.get("original_s51_inventory_after"),
        )
        if (type(before) in (int, float) and type(after) in (int, float)
                and type(invbefore) is int and type(invafter) is int
                and after > before and invafter == invbefore - 1):
            return "S51_OBSERVED_FOOD_GAIN_AND_INVENTORY_DECREMENT"
        return "S16_ONLY_EAT_PHYSICAL_EFFECT_UNPROVEN"
    if action == "MOVE_AWAY":
        # R12's currently projected LIFE_ACTION omits displacement; do not
        # backfill a motion metric from a Paper-global or unrelated source.
        return "S16_ONLY_MOVEMENT_AND_EFFECTIVE_STOP_UNATTESTED"
    return "NON_PHYSICAL_CHOICE_NOT_WORLD_OUTCOME"


def evaluate_shadow_reuse(
    *, prior: dict[str, Any], later: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    """Bounded ordered matching. Never infer missing guard availability."""
    first = prior["l2_context"]
    next_context = later["l2_context"]
    if (first["world_uuid"] == next_context["world_uuid"]
            or first["native_session_id"] == next_context["native_session_id"]):
        raise R14Rejected("SKILL_REUSE_REQUIRES_DIFFERENT_WORLD_AND_SESSION")
    if (replay.get("classification")
            != "DEV_R12_SHADOW_CANDIDATE_REPLAY_READ_ONLY"
            or replay.get("original_world_uuid") != first["world_uuid"]
            or replay.get("original_native_session_id")
            != first["native_session_id"]
            or replay.get("authority") != "NONE"
            or replay.get("s49_actions") != 0
            or replay.get("skill_installs") != 0
            or replay.get("owner_catalog_sha256")
            != action_catalog()["catalog_sha256"]):
        raise R14Rejected("UNQUALIFIED_PRIOR_L2_SHADOW_CANDIDATE")
    program = replay.get("shadow_skill")
    if program is None:
        steps = []
        candidate_status = "L2_ABSTAINED_NO_SKILL_TO_REUSE"
        program_sha = None
    else:
        validate_skill_program(program, action_catalog())
        compiled = replay.get("shadow_compilation")
        if (not isinstance(compiled, dict)
                or compiled.get("authority") != "NONE"
                or compiled.get("physical_actions_issued") != 0
                or compiled.get("skill_installs") != 0
                or compiled.get("catalog_sha256")
                != action_catalog()["catalog_sha256"]):
            raise R14Rejected("CANDIDATE_COMPILATION_NOT_SOURCE_VERIFIED")
        steps = program["steps"]
        candidate_status = "RETAINED_SHADOW_CANDIDATE_REFERENCED"
        program_sha = compiled["program_sha256"]

    step_index = 0
    repeats = 0
    matched_physical = 0
    matched_passive = 0
    events: list[dict[str, Any]] = []
    source_events = next_context["experience_events"]
    original_action_count = sum(
        e["event_kind"] == "LIFE_ACTION" for e in source_events
    )
    if len({e["experience_id"] for e in source_events}) != len(source_events):
        raise R14Rejected("LATER_WORLD_DUPLICATE_EXPERIENCE")
    for event in source_events:
        if step_index >= len(steps):
            break
        step = steps[step_index]
        kind = step["action"]
        item_kind = event["event_kind"]
        obs = event["observation"]
        if kind in PHYSICAL:
            if (item_kind != "LIFE_ACTION"
                    or obs.get("kind") != kind
                    or obs.get("terminal") != "outcome"
                    or type(obs.get("action_id")) is not str
                    or not obs["action_id"]):
                continue
            # The R11 independent auditor already checked each LIFE_ACTION
            # against the original S49 durable fence and S16 terminal.
            matched_physical += 1
            outcome_kind = "ORIGINAL_S49_OUTCOME_SHADOW_MATCH"
            effect = _effect(kind, obs)
        elif kind in NONPHYSICAL:
            if (item_kind != "LIFE_DECISION"
                    or obs.get("selected") != kind):
                continue
            matched_passive += 1
            outcome_kind = "NON_PHYSICAL_DECISION_SHADOW_MATCH"
            effect = "INTENT_OR_NON_ACTION_ONLY_NO_PHYSICAL_PROOF"
        else:
            raise R14Rejected("SKILL_ACTION_NOT_IN_OWNER_CATALOG")
        repeats += 1
        events.append({
            "skill_step_index": step_index,
            "step_repeat_ordinal": repeats,
            "event_id": event["experience_id"],
            "action": kind,
            "guard_source": step["guard"],
            "binding_source": step["binding"],
            "observed_original_action_id": (
                obs["action_id"] if kind in PHYSICAL else None
            ),
            "source_outcome_class": outcome_kind,
            "observed_effect": effect,
            "skill_causal_action_selection_proven": False,
        })
        if repeats >= step["repeat"]:
            step_index += 1
            repeats = 0
    matched = step_index == len(steps) and len(steps) > 0
    return {
        "classification": "DEV_R14_RETAINED_CROSSWORLD_S49_SHADOW_REUSE",
        "candidate_status": candidate_status,
        "source": {
            "prior_world_uuid": first["world_uuid"],
            "prior_session_id": first["native_session_id"],
            "later_world_uuid": next_context["world_uuid"],
            "later_session_id": next_context["native_session_id"],
            "prior_physical_source_sha256": prior["source_sha256"],
            "later_physical_source_sha256": later["source_sha256"],
            "candidate_program_sha256": program_sha,
            "catalog_sha256": action_catalog()["catalog_sha256"],
        },
        "source_events_examined": len(source_events),
        "later_world_original_actions_in_window": original_action_count,
        "later_world_older_events_omitted":
            next_context["omitted_older_events"],
        "skill_steps_observationally_matched": len(events),
        "original_s49_outcomes_observationally_matched": matched_physical,
        "passive_decisions_observationally_matched": matched_passive,
        "full_declared_sequence_observed": matched,
        "trial_readouts": events,
        "inference_limit": (
            "SHADOW_CORRELATION_ONLY_NO_SKILL_DRIVEN_ACTION_OR_LEARNING; "
            "UNMATCHED_GUARDS_ARE_UNKNOWN_NOT_FALSE; "
            "ONLY_LAST_48_NATIVE_EVENTS_EXAMINED"
        ),
        "s49_actions_issued_by_this_module": 0,
        "new_model_posts": 0,
        "memory_owner_writes": 0,
        "habit_updates": 0,
        "learning_updates": 0,
        "skill_installs": 0,
        "l1_reuse_verified": False,
        "l0_promotion_verified": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def project_retained_trial(
    prior_directory: Path, prior_l2_record_directory: Path,
    later_directory: Path,
) -> dict[str, Any]:
    """Reaudit both R11 physical Worlds + raw prior Gemma response."""
    roots = (prior_directory.resolve(), prior_l2_record_directory.resolve(),
             later_directory.resolve())
    if (len(set(roots)) != 3
            or any(a in b.parents or b in a.parents
                   for i, a in enumerate(roots)
                   for b in roots[i + 1:])
            or prior_l2_record_directory.is_symlink()
            or not prior_l2_record_directory.is_dir()):
        raise R14Rejected("ORIGINAL_WORLDS_AND_L2_RAW_MUST_BE_SEPARATE")
    previous = _read_world(prior_directory)
    later = _read_world(later_directory)
    try:
        replay = replay_retained_shadow(previous, prior_l2_record_directory)
    except (R12Rejected, ValueError, TypeError, OSError, KeyError) as exc:
        raise R14Rejected("PRIOR_R12_RAW_L2_CANDIDATE_REPLAY_REJECTED") from exc
    return evaluate_shadow_reuse(prior=previous, later=later, replay=replay)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-world-evidence", required=True, type=Path)
    p.add_argument("--prior-l2-raw", required=True, type=Path)
    p.add_argument("--later-world-evidence", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    source_roots = (
        args.prior_world_evidence.resolve(),
        args.prior_l2_raw.resolve(),
        args.later_world_evidence.resolve(),
    )
    if (args.out.exists() or args.out.is_symlink()
            or any(args.out.resolve(strict=False) == root
                   or root in args.out.resolve(strict=False).parents
                   for root in source_roots)):
        raise R14Rejected("OUTPUT_MUST_NOT_OVERWRITE_ORIGINAL_EVIDENCE")
    result = project_retained_trial(
        args.prior_world_evidence, args.prior_l2_raw,
        args.later_world_evidence,
    )
    if not args.out.parent.is_dir() or args.out.parent.is_symlink():
        raise R14Rejected("NEW_OUT_PARENT_MUST_ALREADY_EXIST")
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True,
                  indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(result["classification"],
          "observed_orig_s49_matches=", result[
              "original_s49_outcomes_observationally_matched"
          ])


if __name__ == "__main__":
    main()
