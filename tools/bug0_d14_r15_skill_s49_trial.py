"""D14 R15 DEV opt-in retained L2 Skill consideration inside original S49 World.

Only the previous R11 and R12/R13 raw evidence may define a candidate.
The Skill chooses a conditional hint, NOT a physical grant: original
NaturalLifeLoop, NormalSessionActionExecutor, S14/S15/S16 and persistent fences
remain the sole issuer. No Memory/Habit write or automated L0 promotion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from tools.bug0_d14_natural_life import (
    NaturalLifeLoop,
    admissible_natural_attack,
)
from tools.bug0_d14_r12_l2_shadow import replay_retained_shadow
from tools.bug0_d14_r13_action_catalog import (
    action_catalog,
    shadow_compile,
    validate_skill_program,
)
from tools.bug0_d14_r14_retained_skill_trial import _read_world

R15_GRANT = "D14_R15_SKILL_TRIAL_ONEWORLD_ONLY"
R15_ORIGINAL_DIR = "D14_R15_PRIOR_WORLD_EVIDENCE"
R15_MODEL_DIR = "D14_R15_PRIOR_L2_RAW"
MAX_PHYSICAL_HINTS = 10


class R15Rejected(RuntimeError):
    """The prior Skill, live native source or owner boundary was unqualified."""


def verified_prior_skill(environment: Mapping[str, str]) -> dict[str, Any]:
    """Qualify the raw prior L2 candidate BEFORE a new World can start."""
    if environment.get(R15_GRANT) != "1":
        raise R15Rejected("R15_EXPLICIT_ONEWORLD_GRANT_REQUIRED")
    if (environment.get("D14_R11_NATURAL_DAY_ONEWORLD_ONLY") != "1"
            or environment.get("D14_R9_COMBAT_FIRST_ONEWORLD_ONLY") != "1"
            or environment.get("D14_R6_NATURAL_MOTION_ONEWORLD_ONLY") != "1"):
        raise R15Rejected("R15_REQUIRES_R11_R9_R6_EXISTING_S49")
    root = Path(environment.get(R15_ORIGINAL_DIR, ""))
    raw = Path(environment.get(R15_MODEL_DIR, ""))
    if (not root.is_absolute() or not raw.is_absolute()
            or not root.is_dir() or not raw.is_dir()
            or root.is_symlink() or raw.is_symlink()
            or root.resolve() == raw.resolve()
            or root.resolve() in raw.resolve().parents
            or raw.resolve() in root.resolve().parents):
        raise R15Rejected("R15_PRIOR_ORIGINAL_AND_L2_RAW_MUST_BE_SEPARATE")
    try:
        prior = _read_world(root)
        replay = replay_retained_shadow(prior, raw)
        program = replay["shadow_skill"]
        catalog = action_catalog()
        if program is None:
            raise R15Rejected("L2_ABSTAINED_NO_SKILL_TO_TRY")
        validate_skill_program(program, catalog)
        if (replay["owner_catalog_sha256"] != catalog["catalog_sha256"]
                or replay["shadow_compilation"] != shadow_compile(
                    program, catalog,
                )
                or replay["original_world_uuid"]
                != prior["l2_context"]["world_uuid"]
                or replay["original_native_session_id"]
                != prior["l2_context"]["native_session_id"]
                or replay["authority"] != "NONE"):
            raise R15Rejected("R15_PRIOR_SKILL_RAW_AND_OWNER_CATALOG_MISMATCH")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise R15Rejected("R15_PRIOR_SKILL_PROVENANCE_NOT_QUALIFIED") from exc
    return {
        "prior_world_uuid": prior["l2_context"]["world_uuid"],
        "prior_native_session_id": prior["l2_context"]["native_session_id"],
        "prior_source_sha256": prior["source_sha256"],
        "catalog_sha256": catalog["catalog_sha256"],
        "program_sha256": replay["shadow_compilation"]["program_sha256"],
        "program": program,
        "origin": "INDEPENDENT_PRIOR_R11_AND_RAW_R12_L2_REPLAY",
        "action_granted": False,
        "skill_installed": False,
    }


class S49SkillTrialCursor:
    """Bounded, source-bound Skill hints with explicit outcome feedback.

    An S49 rejection or unknown effect stops this trial, never reissues.
    Original S49 may continue under its pre-existing DEV grant independently.
    """

    def __init__(self, prior: dict[str, Any], session_id: str) -> None:
        if (session_id == prior["prior_native_session_id"]
                or prior["action_granted"] is not False
                or prior["skill_installed"] is not False):
            raise R15Rejected("R15_SAME_SESSION_OR_FORGED_PERMISSION")
        self.session_id = session_id
        self.steps = prior["program"]["steps"]
        self.budget = min(prior["program"]["max_actions"], MAX_PHYSICAL_HINTS)
        self.program_sha256 = prior["program_sha256"]
        self.step_index = 0
        self.repeat_index = 0
        self.physical_outcomes = 0
        self.last_seq = -1
        self.stopped = False
        self.stop_reason: str | None = None
        self.pending: dict[str, Any] | None = None

    def _guard(self, action: str, previous: Any, current: Any,
               decision: Any, owner: NaturalLifeLoop) -> str:
        coverage = current.snapshot.nearby_entities_coverage
        if (
            coverage.truncated
            or current.snapshot.health <= 0
            or previous.snapshot.oxygen_level is None
            or current.snapshot.oxygen_level is None
            or previous.snapshot.oxygen_level <= 0
            or current.snapshot.oxygen_level <= 0
        ):
            return "UNKNOWN"
        zombies = [
            entity for entity in current.snapshot.nearby_entities
            if entity.name == "zombie"
        ]
        if action == "ATTACK":
            if (decision.selected == "DEFER"
                    and decision.fallback == "ATTACK"
                    and owner.combat_first
                    and not owner.owner._post_move_settling_unqualified
                    and admissible_natural_attack(previous, current)
                    is not None):
                return "AVAILABLE"
            return "UNAVAILABLE" if not zombies else "UNKNOWN"
        if action == "MOVE_AWAY":
            if (decision.selected == "DEFER"
                    and decision.preferred == "MOVE_AWAY"
                    and owner.motion is not None
                    and not owner.owner._post_move_settling_unqualified
                    and owner.motion.current_candidate(current) is not None):
                return "AVAILABLE"
            return "UNAVAILABLE" if not zombies else "UNKNOWN"
        if action == "EAT":
            if (decision.selected == "EAT"
                    and not owner.owner._post_move_settling_unqualified
                    and owner.policy.food._last_decision is not None
                    and owner.policy.food._last_decision.choice is not None):
                return "AVAILABLE"
            # Hunger not present is an observed non-opportunity, but
            # food availability under incomplete risk stays UNKNOWN.
            if current.snapshot.food > 14 and not zombies:
                return "UNAVAILABLE"
            return "UNKNOWN"
        if action == "REST":
            return "AVAILABLE" if decision.selected == "REST" else "UNKNOWN"
        if action == "WAIT":
            return "AVAILABLE"
        raise R15Rejected("SKILL_ACTION_OUTSIDE_CATALOG")

    def consider(self, previous: Any, current: Any, decision: Any,
                 owner: NaturalLifeLoop) -> str | None:
        if self.stopped:
            return None
        if self.pending is not None:
            self.stopped = True
            self.stop_reason = "R15_PREVIOUS_SKILL_HINT_UNRESOLVED"
            return None
        if (current.session_id != self.session_id
                or previous.session_id != self.session_id
                or current.seq <= previous.seq
                or current.seq <= self.last_seq
                or current.request_id == previous.request_id):
            self.stopped = True
            self.stop_reason = "R15_STALE_OR_OTHER_NATIVE_SESSION"
            return None
        self.last_seq = current.seq
        if self.physical_outcomes >= self.budget:
            self.stopped = True
            self.stop_reason = "R15_SKILL_PHYSICAL_BUDGET_USED"
            return None
        while self.step_index < len(self.steps):
            step = self.steps[self.step_index]
            action = step["action"]
            state = self._guard(action, previous, current, decision, owner)
            if state == "UNAVAILABLE":
                if step["if_unavailable"] == "SKIP":
                    self.step_index += 1
                    self.repeat_index = 0
                    continue
                self.stopped = True
                self.stop_reason = "R15_GUARD_NOT_AVAILABLE_STOP"
                return None
            if state == "UNKNOWN":
                return None
            self.pending = {
                "step_index": self.step_index,
                "repeat_ordinal": self.repeat_index + 1,
                "action": action,
                "guard": step["guard"],
                "binding": step["binding"],
                "native_seq": current.seq,
                "native_request_id": current.request_id,
                "candidate_program_sha256": self.program_sha256,
                "original_l0_selected": decision.selected,
                "original_l0_preferred": decision.preferred,
                "original_l0_fallback": decision.fallback,
                "action_granted_by_skill": False,
            }
            return action
        self.stopped = True
        self.stop_reason = "R15_SKILL_PROGRAM_COMPLETE"
        return None

    def finish_hint(self, outcomes: list[dict[str, Any]],
                    *, interrupted: bool = False) -> dict[str, Any]:
        pending = self.pending
        if pending is None:
            raise R15Rejected("R15_NO_PENDING_SKILL_HINT")
        action = pending["action"]
        physical = action in ("ATTACK", "EAT", "MOVE_AWAY")
        matched = (
            not interrupted and (
                (len(outcomes) == 1
                 and outcomes[0].get("kind") == action
                 and outcomes[0].get("terminal") == "outcome"
                 and outcomes[0].get("session_id") == self.session_id
                 and type(outcomes[0].get("action_id")) is str
                 and bool(outcomes[0]["action_id"]))
                if physical else not outcomes
            )
        )
        result = {
            **pending,
            "original_s49_action_id": (
                outcomes[0]["action_id"] if matched and physical else None
            ),
            "original_s49_outcome": (
                outcomes[0]["terminal"] if matched and physical else None
            ),
            "s49_original_issuer_matched": matched and physical,
            "nonphysical_skill_choice_applied": matched and not physical,
            # L0 surface disagreement is not necessarily a difference in
            # physical Action: R9 may also WAIT if its own admission fails.
            "skill_hint_differs_from_l0_recommendation": (
                matched and action != pending["original_l0_selected"]
            ),
            "skill_selection_differs_from_old_r11": (
                matched and physical and action == "MOVE_AWAY"
                # R11 combat-first never selects this R6 MOVE branch.
            ),
            "skill_effectiveness_or_goal_success_proven": False,
            "source_bound_skill_experience": (
                "OBSERVED_ACTUAL_S49_OUTCOME_NOT_GOAL_SUCCESS"
                if matched and physical else
                "NONPHYSICAL_BEHAVIOR_ONLY" if matched else
                "UNRESOLVED_OR_OWNER_REFUSED_NO_RETRY"
            ),
        }
        self.pending = None
        if not matched:
            self.stopped = True
            self.stop_reason = "R15_OWNER_REFUSED_OR_UNRESOLVED_NO_REISSUE"
            return result
        if physical:
            self.physical_outcomes += 1
        self.repeat_index += 1
        if self.repeat_index >= self.steps[self.step_index]["repeat"]:
            self.step_index += 1
            self.repeat_index = 0
        if self.step_index >= len(self.steps):
            self.stopped = True
            self.stop_reason = "R15_SKILL_PROGRAM_COMPLETE"
        return result


class R15NaturalLifeLoop(NaturalLifeLoop):
    """Original single S49 issuer, with separately opted-in Skill hints."""

    def __init__(self, session: Any, evidence_dir: Path,
                 report: dict[str, Any]) -> None:
        if os.environ.get(R15_GRANT) != "1":
            raise R15Rejected("R15_TRIAL_REQUIRES_EXPLICIT_GRANT")
        # Recheck source even if the outer LocalCodex preflight succeeded.
        prior = verified_prior_skill(os.environ)
        super().__init__(session, evidence_dir, report)
        self.skill_trial = S49SkillTrialCursor(prior, self.sid)
        self.trial_path = evidence_dir / "r15_skill_s49_trial.jsonl"
        with self.trial_path.open("x", encoding="utf-8") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        self.report.update({
            "r15_trial_opt_in": True,
            "r15_source": {k: v for k, v in prior.items() if k != "program"},
            "r15_trial_steps": [],
            "r15_trial_kind": "ORIGINAL_S49_ISSUER_SKILL_HINTED_DEV",
            "r15_trial_physical_s49_issued": 0,
            "r15_trial_new_issuer_count": 0,
            "r15_skill_installs": 0,
            "r15_memory_owner_writes": 0,
            "r15_learning_updates": 0,
        })

    def _skill_trial_choice(self, previous: Any, current: Any,
                            decision: Any) -> str | None:
        return self.skill_trial.consider(previous, current, decision, self)

    async def step(self, save: Any) -> None:
        before = len(self.report["life_action_outcomes"])
        interrupted = False
        try:
            await super().step(save)
        except BaseException:
            interrupted = True
            raise
        finally:
            if self.skill_trial.pending is not None:
                outcomes = self.report["life_action_outcomes"][before:]
                entry = self.skill_trial.finish_hint(
                    outcomes, interrupted=interrupted,
                )
                self.report["r15_trial_steps"].append(entry)
                if entry["s49_original_issuer_matched"]:
                    self.report["r15_trial_physical_s49_issued"] += 1
                with self.trial_path.open("a", encoding="utf-8") as stream:
                    json.dump(entry, stream, ensure_ascii=False,
                              sort_keys=True, allow_nan=False)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())

    def final_audit_fields(self) -> None:
        super().final_audit_fields()
        self.report["r15_trial_stop_reason"] = self.skill_trial.stop_reason
        self.report["r15_skill_program_completed"] = (
            self.skill_trial.step_index >= len(self.skill_trial.steps)
        )
