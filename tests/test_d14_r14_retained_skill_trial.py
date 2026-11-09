"""R14 cross-World retained candidate / original S49 outcome shadow tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import bug0_d14_r14_retained_skill_trial as r14
from tools.bug0_d14_r13_action_catalog import action_catalog, shadow_compile


def _program() -> dict:
    return {
        "name": "hunger defensive steps",
        "cue": "zombie close, then safe inventory food",
        "steps": [
            {
                "action": "ATTACK", "guard": "STABLE_CLOSE_ZOMBIE",
                "binding": "NATIVE_STABLE_ZOMBIE_ID", "repeat": 1,
                "if_unavailable": "SKIP",
            },
            {
                "action": "EAT", "guard": "S51_SAFE_EAT_CANDIDATE",
                "binding": "S51_OBSERVED_EAT_CHOICE", "repeat": 1,
                "if_unavailable": "STOP",
            },
            {
                "action": "WAIT", "guard": "ALWAYS", "binding": "NONE",
                "repeat": 1, "if_unavailable": "STOP",
            },
        ],
        "max_actions": 3, "stop_condition": "GOAL_OR_SOURCE_CHANGE",
        "on_failure": "ESCALATE",
    }


def _projection(world: str, session: str, events: list) -> dict:
    return {
        "classification": "DEV_R12_AUDITED_NATURAL_EXPERIENCE_VIEW",
        "source_sha256": {"report": world, "journal": session},
        "s49_actions": 0, "skill_installs": 0,
        "l2_context": {
            "world_uuid": world, "native_session_id": session,
            "world_is_terminated": True,
            "action_authority": "NONE_POST_WORLD_READ_ONLY",
            "experience_events": events,
            "omitted_older_events": 0,
        },
    }


def _event(world: str, session: str, kind: str, index: int,
           obs: dict) -> dict:
    return {
        "event_kind": kind,
        "experience_id": f"r12:{world}:{session}:{kind}:{index}",
        "epistemic_status": (
            "S49_S16_OUTCOME_NOT_PHYSICAL_GOAL_PROOF"
            if kind == "LIFE_ACTION" else "NATIVE_SELF_VIEW_NOT_PAPER_GLOBAL"
        ),
        "observation": obs,
    }


def _later_events() -> list:
    return [
        _event("worldB", "sessionB", "LIFE_DECISION", 1,
               {"selected": "DEFER", "native_seq": 9}),
        _event("worldB", "sessionB", "LIFE_ACTION", 2, {
            "kind": "ATTACK", "action_id": "s49-att-1",
            "terminal": "outcome", "native_target_entity_id": 87,
            "native_target_hurt_event_seen": True,
        }),
        _event("worldB", "sessionB", "LIFE_ACTION", 3, {
            "kind": "EAT", "action_id": "s49-eat-2", "terminal": "outcome",
            "original_s51_food_before": 10,
            "original_s51_food_after": 13,
            "original_s51_inventory_before": 2,
            "original_s51_inventory_after": 1,
        }),
        _event("worldB", "sessionB", "LIFE_DECISION", 4,
               {"selected": "WAIT", "native_seq": 45}),
    ]


def _replay(program: dict | None = None) -> dict:
    if program is None:
        program = _program()
    catalog = action_catalog()
    return {
        "classification": "DEV_R12_SHADOW_CANDIDATE_REPLAY_READ_ONLY",
        "original_world_uuid": "worldA",
        "original_native_session_id": "sessionA",
        "authority": "NONE", "s49_actions": 0, "skill_installs": 0,
        "owner_catalog_sha256": catalog["catalog_sha256"],
        "shadow_skill": program,
        "shadow_compilation": shadow_compile(program, catalog),
    }


def test_later_s49_outcomes_match_only_as_observed_not_skill_causal() -> None:
    prior = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", _later_events())
    result = r14.evaluate_shadow_reuse(
        prior=prior, later=later, replay=_replay(),
    )
    assert result["full_declared_sequence_observed"] is True
    assert result["skill_steps_observationally_matched"] == 3
    assert result["original_s49_outcomes_observationally_matched"] == 2
    assert result["passive_decisions_observationally_matched"] == 1
    assert result["s49_actions_issued_by_this_module"] == 0
    assert result["l1_reuse_verified"] is False
    assert result["skill_installs"] == 0
    assert all(not item["skill_causal_action_selection_proven"]
               for item in result["trial_readouts"])
    assert result["trial_readouts"][0]["observed_effect"] == (
        "NATIVE_HURT_EVENT_NOT_PAPER_DAMAGE_OR_KILL"
    )
    assert result["trial_readouts"][1]["observed_effect"] == (
        "S51_OBSERVED_FOOD_GAIN_AND_INVENTORY_DECREMENT"
    )


def test_nonmatch_does_not_claim_missing_guard_is_false() -> None:
    prior = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", [
        _event("worldB", "sessionB", "LIFE_ACTION", 1, {
            "kind": "MOVE_AWAY", "terminal": "outcome",
            "action_id": "s49-move-1",
        }),
        _event("worldB", "sessionB", "LIFE_DECISION", 2, {
            "selected": "WAIT",
        }),
    ])
    result = r14.evaluate_shadow_reuse(prior=prior, later=later, replay=_replay())
    assert result["full_declared_sequence_observed"] is False
    assert result["trial_readouts"] == []
    assert result["later_world_original_actions_in_window"] == 1
    assert "UNMATCHED_GUARDS_ARE_UNKNOWN_NOT_FALSE" in result["inference_limit"]


def test_attacks_without_s16_outcome_never_match() -> None:
    prior = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", [
        _event("worldB", "sessionB", "LIFE_ACTION", 1, {
            "kind": "ATTACK", "terminal": "unknown",
            "action_id": "unclosed",
        }),
    ])
    result = r14.evaluate_shadow_reuse(prior=prior, later=later, replay=_replay())
    assert result["original_s49_outcomes_observationally_matched"] == 0
    assert result["full_declared_sequence_observed"] is False


def test_abstention_is_valid_and_does_not_invent_a_skill() -> None:
    prior = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", _later_events())
    replay = _replay()
    replay["shadow_skill"] = None
    replay["shadow_compilation"] = None
    result = r14.evaluate_shadow_reuse(prior=prior, later=later, replay=replay)
    assert result["candidate_status"] == "L2_ABSTAINED_NO_SKILL_TO_REUSE"
    assert result["trial_readouts"] == []
    assert result["full_declared_sequence_observed"] is False


@pytest.mark.parametrize(("prior_world", "prior_session", "later_world",
                          "later_session"), [
    ("a", "a", "a", "b"),
    ("a", "a", "b", "a"),
])
def test_same_world_or_session_replay_rejected(
    prior_world: str, prior_session: str, later_world: str,
    later_session: str,
) -> None:
    first = _projection(prior_world, prior_session, [])
    next_world = _projection(later_world, later_session, [])
    replay = _replay()
    replay["original_world_uuid"] = prior_world
    replay["original_native_session_id"] = prior_session
    with pytest.raises(r14.R14Rejected, match="DIFFERENT_WORLD_AND_SESSION"):
        r14.evaluate_shadow_reuse(prior=first, later=next_world, replay=replay)


def test_prior_session_binding_not_transferable() -> None:
    first = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", [])
    replay = _replay()
    replay["original_native_session_id"] = "forged"
    with pytest.raises(r14.R14Rejected, match="UNQUALIFIED_PRIOR_L2"):
        r14.evaluate_shadow_reuse(prior=first, later=later, replay=replay)


def test_catalog_drift_rejects_shadow_reuse() -> None:
    first = _projection("worldA", "sessionA", [])
    later = _projection("worldB", "sessionB", [])
    replay = _replay()
    replay["owner_catalog_sha256"] = "0" * 64
    with pytest.raises(r14.R14Rejected, match="UNQUALIFIED_PRIOR_L2"):
        r14.evaluate_shadow_reuse(prior=first, later=later, replay=replay)


def test_provenance_duplicate_rejected() -> None:
    prior = _projection("worldA", "sessionA", [])
    row = _later_events()[1]
    later = _projection("worldB", "sessionB", [row, row])
    with pytest.raises(r14.R14Rejected, match="DUPLICATE_EXPERIENCE"):
        r14.evaluate_shadow_reuse(prior=prior, later=later, replay=_replay())


def test_only_audited_projection_is_allowed_from_world_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = tmp_path / "source"
    folder.mkdir()
    for key, name in r14.SOURCE_FILES:
        (folder / name).write_text(key)
    monkeypatch.setattr(r14, "project_r11", lambda **kwargs: _projection(
        "a", "b", [],
    ))
    result = r14._read_world(folder)
    assert result["l2_context"]["world_uuid"] == "a"
    assert (folder / "report.json").read_text() == "report"
    (folder / "original_s49_motion_fence.json").unlink()
    with pytest.raises(r14.R14Rejected, match="EVIDENCE_FILES_REQUIRED"):
        r14._read_world(folder)


def test_project_trial_reaudits_both_worlds_and_replays_original_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior = tmp_path / "prior"
    later = tmp_path / "later"
    raw = tmp_path / "raw"
    for directory in (prior, later, raw):
        directory.mkdir()
    visits = []
    def fake_read(path):
        visits.append(path)
        if path == prior:
            return _projection("worldA", "sessionA", [])
        return _projection("worldB", "sessionB", _later_events())
    def fake_replay(projection, record_dir):
        assert record_dir == raw
        assert projection["l2_context"]["world_uuid"] == "worldA"
        visits.append(record_dir)
        return _replay()
    monkeypatch.setattr(r14, "_read_world", fake_read)
    monkeypatch.setattr(r14, "replay_retained_shadow", fake_replay)
    result = r14.project_retained_trial(prior, raw, later)
    assert visits == [prior, later, raw]
    assert result["original_s49_outcomes_observationally_matched"] == 2


def test_separate_provenance_roots_required(
    tmp_path: Path,
) -> None:
    prior = tmp_path / "prior"
    later = tmp_path / "later"
    prior.mkdir()
    later.mkdir()
    with pytest.raises(r14.R14Rejected, match="MUST_BE_SEPARATE"):
        r14.project_retained_trial(prior, prior, later)


def test_retained_trial_is_json_serializable() -> None:
    result = r14.evaluate_shadow_reuse(
        prior=_projection("worldA", "sessionA", []),
        later=_projection("worldB", "sessionB", _later_events()),
        replay=_replay(),
    )
    assert json.loads(json.dumps(result))["classification"] == (
        "DEV_R14_RETAINED_CROSSWORLD_S49_SHADOW_REUSE"
    )
