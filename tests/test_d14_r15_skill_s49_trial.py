"""R15 retained Skill one-World original S49 hint boundary offline tests."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from tools import bug0_d14_r15_skill_s49_trial as r15
from tools.bug0_d14_natural_life import NaturalLifeLoop
from tools.bug0_d14_r13_action_catalog import action_catalog, shadow_compile
from tools.bug0_d14_r15_skill_trial_post import (
    R15PostRejected,
    inspect_r15_trial,
)


def _step(action: str, guard: str, binding: str,
          *, unavailable: str = "STOP", repeat: int = 1) -> dict:
    return {
        "action": action, "guard": guard, "binding": binding,
        "repeat": repeat, "if_unavailable": unavailable,
    }


def _program(*steps: dict) -> dict:
    return {
        "name": "conditional owner-backed survival",
        "cue": "real native situation change",
        "steps": list(steps),
        "max_actions": sum(step["repeat"] for step in steps),
        "stop_condition": "GOAL_OR_SOURCE_CHANGE",
        "on_failure": "ESCALATE",
    }


def _prior(program: dict) -> dict:
    catalog = action_catalog()
    return {
        "prior_world_uuid": "prior-world",
        "prior_native_session_id": "prior-session",
        "prior_source_sha256": {"report": "sha-a"},
        "catalog_sha256": catalog["catalog_sha256"],
        "program_sha256": shadow_compile(program, catalog)["program_sha256"],
        "program": program,
        "origin": "INDEPENDENT_PRIOR_R11_AND_RAW_R12_L2_REPLAY",
        "action_granted": False,
        "skill_installed": False,
    }


def _obs(seq: int, zombies=(), food: int = 10,
         oxygen: int | None = 20) -> NS:
    return NS(
        session_id="new-session",
        seq=seq, request_id=f"native-{seq}",
        snapshot=NS(
            nearby_entities_coverage=NS(truncated=False),
            nearby_entities=list(zombies),
            health=20, food=food, oxygen_level=oxygen,
        ),
    )


def _owner(candidate=None) -> NS:
    return NS(
        owner=NS(_post_move_settling_unqualified=False),
        motion=NS(current_candidate=lambda probe: candidate),
        combat_first=True,
        policy=NS(food=NS(_last_decision=NS(choice=object()))),
    )


def _choice(selected: str, preferred=None, fallback=None) -> NS:
    return NS(selected=selected, preferred=preferred, fallback=fallback)


def test_default_r11_owner_extension_point_never_changes_action() -> None:
    dummy = NaturalLifeLoop.__new__(NaturalLifeLoop)
    assert dummy._skill_trial_choice(None, None, None) is None


def test_retained_skill_wait_instead_of_l0_attack_is_behavioral_only() -> None:
    program = _program(_step("WAIT", "ALWAYS", "NONE"))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    choice = cursor.consider(_obs(4), _obs(5), _choice(
        "DEFER", "MOVE_AWAY", "ATTACK",
    ), _owner())
    assert choice == "WAIT"
    result = cursor.finish_hint([])
    assert result["nonphysical_skill_choice_applied"] is True
    assert result["s49_original_issuer_matched"] is False
    assert result["skill_hint_differs_from_l0_recommendation"] is True
    assert result["skill_selection_differs_from_old_r11"] is False
    assert cursor.stopped is True
    assert cursor.physical_outcomes == 0


def test_skill_original_move_owner_only_and_stop_on_unknown() -> None:
    program = _program(_step(
        "MOVE_AWAY", "S49_NATIVE_MOVE_CANDIDATE", "NATIVE_S49_MOVE_SOURCE",
    ))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    zombie = NS(name="zombie", distance=3.0)
    # Native event candidate exists, but only an already-bounded S49 owner
    # may later turn this hint into a physical Action.
    suggested = cursor.consider(_obs(4, [zombie]), _obs(5, [zombie]),
                                _choice("DEFER", "MOVE_AWAY", "ATTACK"),
                                _owner(candidate=object()))
    assert suggested == "MOVE_AWAY"
    done = cursor.finish_hint([{
        "kind": "MOVE_AWAY", "terminal": "outcome",
        "session_id": "new-session", "action_id": "real-s49-move-1",
    }])
    assert done["s49_original_issuer_matched"] is True
    assert done["original_s49_action_id"] == "real-s49-move-1"
    assert done["skill_selection_differs_from_old_r11"] is True
    assert done["skill_effectiveness_or_goal_success_proven"] is False
    assert cursor.physical_outcomes == 1


def test_refused_owner_does_not_reissue() -> None:
    program = _program(_step(
        "MOVE_AWAY", "S49_NATIVE_MOVE_CANDIDATE", "NATIVE_S49_MOVE_SOURCE",
    ))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    zombie = NS(name="zombie", distance=3.0)
    assert cursor.consider(
        _obs(10, [zombie]), _obs(11, [zombie]),
        _choice("DEFER", "MOVE_AWAY", "ATTACK"),
        _owner(candidate=object()),
    ) == "MOVE_AWAY"
    result = cursor.finish_hint([])
    assert result["s49_original_issuer_matched"] is False
    assert result["source_bound_skill_experience"] == (
        "UNRESOLVED_OR_OWNER_REFUSED_NO_RETRY"
    )
    assert cursor.stopped
    assert cursor.consider(_obs(20), _obs(21), _choice("WAIT"),
                           _owner()) is None


def test_unavailable_guard_skips_to_wait_but_unknown_stays_unknown() -> None:
    program = _program(
        _step("ATTACK", "STABLE_CLOSE_ZOMBIE", "NATIVE_STABLE_ZOMBIE_ID",
              unavailable="SKIP"),
        _step("WAIT", "ALWAYS", "NONE"),
    )
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    assert cursor.consider(_obs(4), _obs(5),
                           _choice("WAIT"), _owner()) == "WAIT"
    assert cursor.step_index == 1
    cursor.finish_hint([])
    assert cursor.stop_reason == "R15_SKILL_PROGRAM_COMPLETE"

    program = _program(_step(
        "ATTACK", "STABLE_CLOSE_ZOMBIE", "NATIVE_STABLE_ZOMBIE_ID",
        unavailable="SKIP",
    ))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    zombie = NS(name="zombie", distance=2.5)
    assert cursor.consider(
        _obs(4, [zombie]), _obs(5, [zombie]),
        _choice("WAIT"), _owner(),
    ) is None
    assert cursor.step_index == 0
    assert cursor.stopped is False


def test_stale_current_native_source_mints_no_skill_hint() -> None:
    program = _program(_step("WAIT", "ALWAYS", "NONE"))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    assert cursor.consider(_obs(5), _obs(4),
                           _choice("WAIT"), _owner()) is None
    assert cursor.stopped is True
    assert cursor.pending is None


def test_prior_r11_raw_source_required_before_world(
    tmp_path: Path,
) -> None:
    env = {
        r15.R15_GRANT: "1",
        "D14_R11_NATURAL_DAY_ONEWORLD_ONLY": "1",
        "D14_R9_COMBAT_FIRST_ONEWORLD_ONLY": "1",
        "D14_R6_NATURAL_MOTION_ONEWORLD_ONLY": "1",
        r15.R15_ORIGINAL_DIR: str(tmp_path / "missing"),
        r15.R15_MODEL_DIR: str(tmp_path / "missing-model"),
    }
    with pytest.raises(r15.R15Rejected, match="MUST_BE_SEPARATE"):
        r15.verified_prior_skill(env)
    assert not (tmp_path / "missing").exists()


def test_verified_prior_skill_is_not_an_action_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior = tmp_path / "prior"
    raw = tmp_path / "raw"
    prior.mkdir()
    raw.mkdir()
    program = _program(_step("WAIT", "ALWAYS", "NONE"))
    projection = {
        "source_sha256": {"report": "sha"},
        "l2_context": {
            "world_uuid": "prior-world", "native_session_id": "prior-session",
        },
    }
    replay = {
        "shadow_skill": program,
        "shadow_compilation": shadow_compile(program, action_catalog()),
        "original_world_uuid": "prior-world",
        "original_native_session_id": "prior-session",
        "owner_catalog_sha256": action_catalog()["catalog_sha256"],
        "authority": "NONE",
    }
    monkeypatch.setattr(r15, "_read_world", lambda directory: projection)
    monkeypatch.setattr(r15, "replay_retained_shadow", lambda *args: replay)
    env = {
        r15.R15_GRANT: "1",
        "D14_R11_NATURAL_DAY_ONEWORLD_ONLY": "1",
        "D14_R9_COMBAT_FIRST_ONEWORLD_ONLY": "1",
        "D14_R6_NATURAL_MOTION_ONEWORLD_ONLY": "1",
        r15.R15_ORIGINAL_DIR: str(prior),
        r15.R15_MODEL_DIR: str(raw),
    }
    qualified = r15.verified_prior_skill(env)
    assert qualified["action_granted"] is False
    assert qualified["skill_installed"] is False
    assert qualified["program_sha256"] == replay[
        "shadow_compilation"
    ]["program_sha256"]


def _auditor_fixture() -> tuple[dict, dict, dict, str]:
    program = _program(_step(
        "MOVE_AWAY", "S49_NATIVE_MOVE_CANDIDATE", "NATIVE_S49_MOVE_SOURCE",
    ))
    prior = _prior(program)
    cursor = r15.S49SkillTrialCursor(prior, "new-session")
    zombie = NS(name="zombie", distance=3.0)
    assert cursor.consider(
        _obs(3, [zombie]), _obs(4, [zombie]),
        _choice("DEFER", "MOVE_AWAY", "ATTACK"),
        _owner(candidate=object()),
    ) == "MOVE_AWAY"
    row = cursor.finish_hint([{
        "kind": "MOVE_AWAY", "terminal": "outcome",
        "session_id": "new-session", "action_id": "original-s49-1",
    }])
    report = {
        "status": "PASS_DEV", "r15_trial_opt_in": True,
        "s49_physical_issuer": "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR",
        "r15_trial_new_issuer_count": 0,
        "model_posts": 0, "skill_installs": 0, "learning_updates": 0,
        "c1_intent_experiences": 0, "r15_skill_installs": 0,
        "r15_learning_updates": 0, "r15_memory_owner_writes": 0,
        "original_s49_session_id": "new-session",
        "native_session_id": "new-session",
        "r15_source": {k: v for k, v in prior.items() if k != "program"},
        "r15_trial_steps": [row], "r15_trial_physical_s49_issued": 1,
        "life_decisions": [{
            "native_seq": 4, "native_request_id": "native-4",
            "r15_skill_trial_hint": "MOVE_AWAY",
            "r15_hint_is_not_authority": True,
            "selected": "DEFER", "preferred": "MOVE_AWAY",
            "fallback": "ATTACK",
        }],
        "life_action_outcomes": [{
            "kind": "MOVE_AWAY", "terminal": "outcome",
            "native_admitted_seq": 4,
            "session_id": "new-session", "action_id": "original-s49-1",
        }],
    }
    active = {
        "status": "PASS_DEV", "r11_natural_day_opt_in": True,
        "world_uuid": "new-world",
    }
    return report, active, prior, json.dumps(row) + "\n"


def test_independent_r15_post_audit_original_s49_correlation() -> None:
    report, active, prior, sidecar = _auditor_fixture()
    readout = inspect_r15_trial(report, active, sidecar, prior)
    assert readout["status"] == "PASS_DEV"
    assert readout["matched_original_s49_physical_actions"] == 1
    assert readout["skill_choice_differed_from_unmodified_r11_count"] == 1
    assert readout["new_action_issuer_count"] == 0
    assert readout["learning_updates"] == 0


@pytest.mark.parametrize("tamper", [
    "action-id", "session", "program-sha", "sidecar", "world",
])
def test_independent_post_rejects_forged_outcome(tamper: str) -> None:
    report, active, prior, sidecar = _auditor_fixture()
    if tamper == "action-id":
        report["life_action_outcomes"][0]["action_id"] = "invented"
    elif tamper == "session":
        report["native_session_id"] = "another-session"
    elif tamper == "program-sha":
        prior["program_sha256"] = "forged"
    elif tamper == "sidecar":
        sidecar = json.dumps({"action": "EAT"}) + "\n"
    else:
        active["world_uuid"] = prior["prior_world_uuid"]
    with pytest.raises(R15PostRejected):
        inspect_r15_trial(report, active, sidecar, prior)


def test_unknown_oxygen_never_yields_live_skill_hint() -> None:
    program = _program(_step(
        "MOVE_AWAY", "S49_NATIVE_MOVE_CANDIDATE", "NATIVE_S49_MOVE_SOURCE",
    ))
    cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
    zombie = NS(name="zombie", distance=3.0)
    for previous, current in [
        (_obs(4, [zombie], oxygen=None), _obs(5, [zombie])),
        (_obs(4, [zombie]), _obs(5, [zombie], oxygen=None)),
        (_obs(4, [zombie]), _obs(5, [zombie], oxygen=0)),
    ]:
        cursor = r15.S49SkillTrialCursor(_prior(program), "new-session")
        assert cursor.consider(
            previous, current,
            _choice("DEFER", "MOVE_AWAY", "ATTACK"),
            _owner(candidate=object()),
        ) is None
        assert cursor.pending is None
        assert cursor.physical_outcomes == 0
